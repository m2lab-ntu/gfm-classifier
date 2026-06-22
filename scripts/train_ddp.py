#!/usr/bin/env python3
"""
DDP training script for Token-level GFM Classifier — 258M full dataset.

Launch with torchrun (see SLURM script):
  torchrun --nproc_per_node=8 --nnodes=8 \\
      --node_rank=$SLURM_NODEID \\
      --master_addr=$(scontrol show hostnames $SLURM_JOB_NODELIST | head -1) \\
      --master_port=29500 \\
      train_ddp.py --config configs/nt_token_genus_v10_258M.yaml

Key differences from train.py:
  - Uses LazyFASTADataset (dataset_lazy.py) → no full-FASTA in RAM
  - DistributedSampler partitions data across ranks
  - Model wrapped with DDP
  - Metrics all-reduced across ranks before logging
  - Checkpointing and logging on rank 0 only
  - Phase 1 (head-only) is skipped in DDP mode (start directly with LoRA+head)
"""

import argparse
import datetime
import gc
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.distributed as dist
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader
from torch.utils.data.distributed import DistributedSampler
from sklearn.utils.class_weight import compute_class_weight
from transformers import AutoTokenizer, get_cosine_schedule_with_warmup

from dataset_lazy import LazyFASTADataset
from model import create_model
from resource_monitor import ResourceMonitor
from utils import load_config, save_config, save_json, AverageMeter, EarlyStopping


# ── DDP helpers ──────────────────────────────────────────────────────────────

def setup_ddp():
    # Support both srun-python (SLURM_*) and torchrun (LOCAL_RANK) launches
    rank        = int(os.environ.get("SLURM_PROCID",   os.environ.get("RANK",        "0")))
    world_size  = int(os.environ.get("SLURM_NTASKS",   os.environ.get("WORLD_SIZE",  "1")))
    slurm_local = int(os.environ.get("SLURM_LOCALID",  os.environ.get("LOCAL_RANK",  "0")))
    os.environ["RANK"]       = str(rank)
    os.environ["WORLD_SIZE"] = str(world_size)
    # If Slurm assigns 1 GPU per task, CUDA_VISIBLE_DEVICES is a single device
    # (e.g. "3") → cuda:0 is the only visible device; otherwise use SLURM_LOCALID.
    cvd = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if cvd and "," not in cvd and cvd not in ("-1", "NoDevFiles", ""):
        local_rank = 0  # exactly 1 GPU assigned to this task
    else:
        local_rank = slurm_local
    torch.cuda.set_device(local_rank)
    dist.init_process_group(
        "nccl",
        device_id=torch.device(f"cuda:{local_rank}"),
        timeout=datetime.timedelta(hours=4),
    )
    return local_rank, rank, world_size


def cleanup_ddp():
    dist.destroy_process_group()


def all_reduce_mean(tensor: torch.Tensor) -> float:
    dist.all_reduce(tensor, op=dist.ReduceOp.SUM)
    return (tensor / dist.get_world_size()).item()


def all_reduce_sum(tensor: torch.Tensor) -> float:
    dist.all_reduce(tensor, op=dist.ReduceOp.SUM)
    return tensor.item()


# ── AMP dtype ────────────────────────────────────────────────────────────────

def _get_amp_dtype(use_amp):
    if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
        return torch.bfloat16
    return torch.float16


# ── Training helpers ──────────────────────────────────────────────────────────

def train_epoch(model, loader, criterion, optimizer, scheduler, scaler,
                device, grad_accum, max_grad_norm, use_amp, amp_dtype,
                log_prior=None, rc_consistency=False, lambda_kl=0.0,
                is_main=True, time_limit_sec=None, job_start=None,
                periodic_save_fn=None, periodic_save_interval=5000):
    model.train()
    loss_meter = AverageMeter()
    correct = 0
    total   = 0
    nan_count = 0

    optimizer.zero_grad()
    for step, batch in enumerate(loader):
        # Time-limit check
        if time_limit_sec and job_start and (time.time() - job_start) >= time_limit_sec:
            if is_main:
                print(f"\n⏰ Time limit reached at step {step}.")
            if periodic_save_fn:
                periodic_save_fn(step)
            return loss_meter.avg, correct / max(total, 1), True  # True = timed out

        input_ids, attention_mask, labels = [b.to(device) for b in batch]

        with torch.amp.autocast("cuda", enabled=use_amp, dtype=amp_dtype):
            logits = model(input_ids, attention_mask)
            logits_for_loss = logits + log_prior if log_prior is not None else logits
            loss = criterion(logits_for_loss, labels) / grad_accum

        if torch.isnan(loss) or torch.isinf(loss):
            nan_count += 1
            optimizer.zero_grad()
            continue

        scaler.scale(loss).backward()
        if (step + 1) % grad_accum == 0:
            scaler.unscale_(optimizer)
            grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
            if torch.isnan(grad_norm) or torch.isinf(grad_norm):
                nan_count += 1
                optimizer.zero_grad()
            else:
                scaler.step(optimizer)
                scaler.update()
                if scheduler is not None:
                    scheduler.step()
                optimizer.zero_grad()

        with torch.no_grad():
            preds = logits.argmax(dim=-1)
            correct += (preds == labels).sum().item()
            total   += labels.size(0)
        loss_meter.update(loss.item() * grad_accum, labels.size(0))

        if periodic_save_fn and step > 0 and step % periodic_save_interval == 0:
            periodic_save_fn(step)

    if nan_count > 0 and is_main:
        print(f"\n  ⚠️  NaN/Inf events this epoch: {nan_count}")

    return loss_meter.avg, correct / max(total, 1), False


def validate(model, loader, criterion, device, use_amp, amp_dtype, world_size):
    """Run validation and aggregate metrics across all DDP ranks."""
    model.eval()
    correct_t = torch.zeros(1, device=device)
    total_t   = torch.zeros(1, device=device)
    loss_sum  = torch.zeros(1, device=device)
    loss_cnt  = torch.zeros(1, device=device)

    with torch.no_grad():
        for batch in loader:
            input_ids, attention_mask, labels = [b.to(device) for b in batch]
            with torch.amp.autocast("cuda", enabled=use_amp, dtype=amp_dtype):
                logits = model(input_ids, attention_mask)
                loss   = criterion(logits, labels)
            preds = logits.argmax(dim=-1)
            correct_t += (preds == labels).sum()
            total_t   += labels.size(0)
            loss_sum  += loss * labels.size(0)
            loss_cnt  += labels.size(0)

    # Aggregate across ranks
    dist.all_reduce(correct_t, op=dist.ReduceOp.SUM)
    dist.all_reduce(total_t,   op=dist.ReduceOp.SUM)
    dist.all_reduce(loss_sum,  op=dist.ReduceOp.SUM)
    dist.all_reduce(loss_cnt,  op=dist.ReduceOp.SUM)

    val_loss = (loss_sum / loss_cnt).item()
    val_acc  = (correct_t / total_t).item()
    return val_loss, val_acc


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config",  type=str, required=True)
    parser.add_argument("--resume",  type=str, default=None)
    parser.add_argument("--init_from", type=str, default=None)
    parser.add_argument("--time_limit_sec", type=int, default=None)
    args = parser.parse_args()

    # ── DDP init ──────────────────────────────────────────────────────────────
    local_rank, rank, world_size = setup_ddp()
    device   = torch.device(f"cuda:{local_rank}")
    is_main  = (rank == 0)
    job_start = time.time()

    cfg = load_config(args.config)

    if is_main:
        print("=" * 70)
        print(f"Token-level GFM — DDP Training  [world_size={world_size}]")
        print(f"Config: {args.config}")
        print(f"Rank:   {rank}/{world_size}  |  local_rank: {local_rank}")
        print(f"GPU:    {torch.cuda.get_device_name(local_rank)}")
        print(f"VRAM:   {torch.cuda.get_device_properties(local_rank).total_memory/1e9:.1f} GB")
        print("=" * 70)

    output_dir = Path(cfg["output"]["dir"])
    if is_main:
        output_dir.mkdir(parents=True, exist_ok=True)
        save_config(cfg, str(output_dir))

    dist.barrier(device_ids=[local_rank])

    # ── Resource monitor (rank 0 only) ────────────────────────────────────────
    monitor = None
    if is_main:
        monitor = ResourceMonitor(device=str(device), sample_interval=60.0)
        monitor.start()

    # ── Load datasets ─────────────────────────────────────────────────────────
    backbone_name    = cfg["model"]["backbone"]
    trust_remote     = cfg["model"].get("trust_remote_code", True)
    max_token_length = cfg["data"].get("max_token_length", 32)
    rc_augment       = cfg["data"].get("rc_augment", True)
    kmer_preprocess  = cfg["data"].get("kmer_preprocess", None)
    val_ratio        = cfg["data"].get("val_ratio", 0.05)   # use 5% val for 258M

    if is_main:
        print(f"\nLoading tokenizer: {backbone_name}")
    tokenizer = AutoTokenizer.from_pretrained(backbone_name, trust_remote_code=trust_remote)

    # Each rank instantiates its own LazyFASTADataset.
    # The index file (.idx.npy) is built once then shared via the filesystem.
    # All ranks build it concurrently on first run, then load from cache.
    if is_main:
        print(f"\nBuilding train/val datasets (lazy loading)...")

    train_dataset = LazyFASTADataset(
        fasta_path=cfg["data"]["fasta_path"],
        labels_path=cfg["data"]["labels_path"],
        tokenizer=tokenizer,
        max_length=max_token_length,
        split="train",
        val_ratio=val_ratio,
        seed=42,
        rc_augment=rc_augment,
        kmer_preprocess=kmer_preprocess,
    )
    val_dataset = LazyFASTADataset(
        fasta_path=cfg["data"]["fasta_path"],
        labels_path=cfg["data"]["labels_path"],
        tokenizer=tokenizer,
        max_length=max_token_length,
        split="val",
        val_ratio=val_ratio,
        seed=42,
        rc_augment=False,
        kmer_preprocess=kmer_preprocess,
    )
    num_classes = train_dataset.num_genera

    if is_main:
        print(f"\nTask: genus  |  Classes: {num_classes}")
        print(f"Train: {len(train_dataset):,}  Val: {len(val_dataset):,}")
        print(f"Effective train per rank: {len(train_dataset) // world_size:,}")

    # ── Samplers + DataLoaders ────────────────────────────────────────────────
    train_cfg    = cfg["training"]
    batch_size   = train_cfg["batch_size"]         # per-GPU batch size
    num_workers  = train_cfg.get("num_workers", 4)

    train_sampler = DistributedSampler(
        train_dataset, num_replicas=world_size, rank=rank, shuffle=True, drop_last=True
    )
    val_sampler = DistributedSampler(
        val_dataset, num_replicas=world_size, rank=rank, shuffle=False
    )

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, sampler=train_sampler,
        num_workers=num_workers, pin_memory=True, drop_last=True,
        persistent_workers=(num_workers > 0),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=train_cfg.get("eval_batch_size", batch_size * 2),
        sampler=val_sampler,
        num_workers=0, pin_memory=True,
    )

    # ── Model ─────────────────────────────────────────────────────────────────
    if is_main:
        print("\nCreating model...")
    model_cfg = cfg["model"]
    model = create_model(model_cfg, num_classes).to(device)

    if args.resume:
        if is_main:
            print(f"\n--- Resuming from: {args.resume} ---")
        ckpt = torch.load(args.resume, map_location=device, weights_only=False)
        _sd = ckpt["model_state_dict"]
        _remapped = {}
        for _k, _v in _sd.items():
            _parts = _k.split(".")
            if len(_parts) >= 2 and _parts[-1] in ("weight", "bias") and _parts[-2] in ("query","key","value"):
                _remapped[".".join(_parts[:-1]) + ".base_layer." + _parts[-1]] = _v
            else:
                _remapped[_k] = _v
        model.load_state_dict(_remapped, strict=False)
        resume_epoch = ckpt.get("epoch", 0)
        if is_main:
            print(f"  Loaded from epoch {resume_epoch}  val_acc={ckpt.get('val_acc','N/A')}")
    elif args.init_from:
        if is_main:
            print(f"\n--- Warm start from: {args.init_from} (epoch resets to 0) ---")
        ckpt = torch.load(args.init_from, map_location=device, weights_only=False)
        _sd = ckpt["model_state_dict"]
        _remapped = {}
        for _k, _v in _sd.items():
            _parts = _k.split(".")
            if len(_parts) >= 2 and _parts[-1] in ("weight", "bias") and _parts[-2] in ("query","key","value"):
                _remapped[".".join(_parts[:-1]) + ".base_layer." + _parts[-1]] = _v
            else:
                _remapped[_k] = _v
        model.load_state_dict(_remapped, strict=False)
        resume_epoch = 0
        if is_main:
            print(f"  Warm-start weights loaded  val_acc={ckpt.get('val_acc','N/A')}")
    else:
        resume_epoch = 0

    # Wrap with DDP after loading checkpoint (load on raw model, then wrap)
    model = DDP(model, device_ids=[local_rank], find_unused_parameters=False)

    # ── Loss ──────────────────────────────────────────────────────────────────
    use_class_weights = train_cfg.get("class_weights", True)
    label_smoothing   = train_cfg.get("label_smoothing", 0.0)
    if use_class_weights:
        train_genus_labels = train_dataset.get_genus_labels()
        cw = compute_class_weight("balanced",
                                  classes=np.unique(train_genus_labels),
                                  y=train_genus_labels)
        max_weight = train_cfg.get("max_class_weight", 10.0)
        cw = np.clip(cw, a_min=None, a_max=max_weight)
        class_weights = torch.from_numpy(cw).float().to(device)
        criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=label_smoothing)
        if is_main:
            print(f"\nClass weights: min={cw.min():.4f} max={cw.max():.4f} (clamped≤{max_weight})")
    else:
        criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

    # ── Logit Adjustment ──────────────────────────────────────────────────────
    use_logit_adj = train_cfg.get("logit_adjustment", False)
    log_prior = None
    if use_logit_adj:
        tau = train_cfg.get("logit_adjustment_tau", 1.0)
        train_genus_labels = train_dataset.get_genus_labels()
        unique_cls, counts_cls = np.unique(train_genus_labels, return_counts=True)
        class_prior = np.zeros(num_classes, dtype=np.float64)
        class_prior[unique_cls] = counts_cls / counts_cls.sum()
        class_prior = np.clip(class_prior, 1e-8, None)
        log_prior = torch.from_numpy(tau * np.log(class_prior)).float().to(device)

    # ── Optimiser ─────────────────────────────────────────────────────────────
    lr       = train_cfg.get("learning_rate", 5e-4)
    bb_lr    = train_cfg.get("backbone_lr", 3e-5)
    wd       = train_cfg.get("weight_decay", 0.01)
    num_epochs    = train_cfg["num_epochs"]
    warmup_ratio  = train_cfg.get("warmup_ratio", 0.05)
    grad_accum    = train_cfg.get("gradient_accumulation_steps", 1)
    max_grad_norm = train_cfg.get("max_grad_norm", 1.0)
    patience      = train_cfg.get("early_stopping_patience", 5)
    use_amp       = train_cfg.get("amp", True)
    amp_dtype     = _get_amp_dtype(use_amp)
    use_scaler    = use_amp and (amp_dtype == torch.float16)

    # Differential LR: backbone vs head
    backbone_params = [p for n, p in model.named_parameters()
                       if "classifier_head" not in n and p.requires_grad]
    head_params     = [p for n, p in model.named_parameters()
                       if "classifier_head" in n and p.requires_grad]
    optimizer = torch.optim.AdamW(
        [{"params": backbone_params, "lr": bb_lr},
         {"params": head_params,     "lr": lr}],
        weight_decay=wd,
    )

    total_steps   = (len(train_loader) // grad_accum) * num_epochs
    warmup_steps  = int(total_steps * warmup_ratio)
    scheduler     = get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps)
    scaler        = torch.amp.GradScaler("cuda", enabled=use_scaler)
    early_stop    = EarlyStopping(patience=patience, mode="max")

    if is_main:
        n_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        n_total     = sum(p.numel() for p in model.parameters())
        print(f"\nTrainable: {n_trainable:,} / {n_total:,} params ({100*n_trainable/n_total:.2f}%)")
        print(f"Effective batch: {batch_size * grad_accum * world_size} "
              f"({batch_size}/GPU × {grad_accum} accum × {world_size} GPUs)")
        print(f"Total steps: {total_steps:,}  warmup: {warmup_steps:,}")

    # Restore optimiser/scheduler if resuming
    if args.resume and "optimizer_state_dict" in ckpt:
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        scheduler.load_state_dict(ckpt["scheduler_state_dict"])
        if is_main:
            print("  Optimiser + scheduler state restored.")

    best_val_acc   = 0.0
    patience_count = 0

    # ── Training loop ─────────────────────────────────────────────────────────
    for epoch in range(resume_epoch, num_epochs):
        train_sampler.set_epoch(epoch)   # critical for proper shuffling in DDP

        t0 = time.time()

        def _periodic_save(step):
            if not is_main:
                return
            ckpt_data = {
                "model_state_dict":     model.module.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "scheduler_state_dict": scheduler.state_dict(),
                "epoch": epoch,
                "val_acc": best_val_acc,
                "best_val_acc": best_val_acc,
                "patience_counter": patience_count,
                "config": cfg,
            }
            torch.save(ckpt_data, output_dir / "last.pt")

        train_loss, train_acc, timed_out = train_epoch(
            model, train_loader, criterion, optimizer, scheduler, scaler,
            device, grad_accum, max_grad_norm, use_amp, amp_dtype,
            log_prior=log_prior, is_main=is_main,
            time_limit_sec=args.time_limit_sec, job_start=job_start,
            periodic_save_fn=_periodic_save,
        )

        val_loss, val_acc = validate(
            model, val_loader, criterion, device, use_amp, amp_dtype, world_size
        )

        elapsed = time.time() - t0

        if is_main:
            print(f"\nEpoch {epoch+1:02d}/{num_epochs} | "
                  f"train_loss={train_loss:.4f} train_acc={train_acc:.4f} | "
                  f"val_loss={val_loss:.4f} val_acc={val_acc:.4f} | "
                  f"time={elapsed/60:.1f}m")

            # Save last checkpoint
            ckpt_data = {
                "model_state_dict":     model.module.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "scheduler_state_dict": scheduler.state_dict(),
                "epoch": epoch + 1,
                "val_acc": val_acc,
                "best_val_acc": max(best_val_acc, val_acc),
                "patience_counter": patience_count,
                "config": cfg,
            }
            torch.save(ckpt_data, output_dir / "last.pt")

            # Save best checkpoint
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                torch.save(ckpt_data, output_dir / "best.pt")
                print(f"  *** New best: {best_val_acc:.4f} ***")
                patience_count = 0
            else:
                patience_count += 1

            # Append to training history CSV
            history_path = output_dir / "training_history.csv"
            header_needed = not history_path.exists()
            with open(history_path, "a") as hf:
                if header_needed:
                    hf.write("epoch,train_loss,train_acc,val_loss,val_acc\n")
                hf.write(f"{epoch+1},{train_loss:.6f},{train_acc:.6f},"
                         f"{val_loss:.6f},{val_acc:.6f}\n")

        if timed_out:
            if is_main:
                print(f"\n⏰ Time limit hit. last.pt saved. Resubmit job to continue.")
            break

        # Broadcast patience_count so all ranks agree on early stopping
        patience_t = torch.tensor(patience_count, device=device)
        dist.broadcast(patience_t, src=0)
        patience_count = int(patience_t.item())

        if patience_count >= patience:
            if is_main:
                print(f"\nEarly stopping at epoch {epoch+1} (patience={patience})")
            break

        torch.cuda.empty_cache()
        gc.collect()

    if is_main:
        print(f"\n{'='*70}")
        print(f"Training complete. Best val_acc = {best_val_acc:.4f}")
        print(f"Checkpoints: {output_dir}/best.pt  (and last.pt)")
        print(f"{'='*70}")
        if monitor:
            monitor.stop()

    cleanup_ddp()


if __name__ == "__main__":
    main()
