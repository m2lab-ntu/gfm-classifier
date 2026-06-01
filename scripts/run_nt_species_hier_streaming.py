#!/usr/bin/env python3
"""
Streaming NT-Species hierarchical inference.

Runs genus model and species model simultaneously per batch,
applies topk=1 genus logit masking on-the-fly, and accumulates
ONLY the final argmax predictions (not logits).  Peak memory is
O(batch_size) instead of O(N_reads * N_classes).

Output: results/nt_token_species_v4_50M/eval_topk_1_stream/predictions.npz
        (preds [N] int64, labels [N] int64)
"""

import argparse
import json
import numpy as np
import torch
from pathlib import Path
from torch.utils.data import DataLoader
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(REPO / "scripts"))

from utils import load_config
from dataset import TokenLevelReadDataset
from model import create_model


def load_data_split(cfg):
    """Return val sequences/labels without loading full FASTA into one list."""
    import pandas as pd
    from sklearn.model_selection import train_test_split

    labels_path = cfg["data"]["labels_path"]
    val_ratio   = cfg["data"].get("val_ratio", 0.1)
    seed        = cfg["data"].get("seed", 42)

    df = pd.read_csv(labels_path, sep="\t")
    # Build label maps
    species_names = sorted(df["species_name"].unique())
    genus_names   = sorted(df["genus_name"].unique())
    sp2id = {n: i for i, n in enumerate(species_names)}
    gn2id = {n: i for i, n in enumerate(genus_names)}
    sp2gn = {}

    seq_ids     = df["seq_id"].tolist()
    sp_labels   = df["species_name"].map(sp2id).tolist()
    gn_labels   = df["genus_name"].map(gn2id).tolist()

    for sp, gn in zip(sp_labels, gn_labels):
        sp2gn[sp] = gn

    # genus → species mask (1535 × 120 → inverted: genus_id → set of species_ids)
    genus_to_species = {}
    for sp_id, gn_id in sp2gn.items():
        genus_to_species.setdefault(gn_id, []).append(sp_id)

    idx = list(range(len(seq_ids)))
    _, val_idx = train_test_split(idx, test_size=val_ratio, random_state=seed)

    # Read FASTA sequences for val split only
    fasta_path = cfg["data"]["fasta_path"]
    print(f"  Reading FASTA sequences for {len(val_idx):,} val reads...")
    seq_id_set = {seq_ids[i] for i in val_idx}

    sequences = {}
    current_id = None
    with open(fasta_path) as f:
        for line in f:
            line = line.rstrip()
            if line.startswith(">"):
                current_id = line[1:].split()[0]
            else:
                if current_id in seq_id_set:
                    sequences[current_id] = line
    print(f"  Loaded {len(sequences):,} sequences")

    val_seqs   = [sequences[seq_ids[i]] for i in val_idx]
    val_sp     = [sp_labels[i] for i in val_idx]
    val_gn     = [gn_labels[i] for i in val_idx]

    return val_seqs, val_sp, val_gn, sp2gn, genus_to_species, len(species_names), len(genus_names)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sp_config",     required=True)
    parser.add_argument("--sp_checkpoint", required=True)
    parser.add_argument("--gn_config",     required=True)
    parser.add_argument("--gn_checkpoint", required=True)
    parser.add_argument("--output_dir",    required=True)
    parser.add_argument("--batch_size",    type=int, default=512)
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # ── Load configs ─────────────────────────────────────────────────────────
    sp_cfg = load_config(args.sp_config)
    gn_cfg = load_config(args.gn_config)

    # ── Load data (val split only) ───────────────────────────────────────────
    print("Loading val data...")
    val_seqs, val_sp, val_gn, sp2gn, genus_to_species, n_species, n_genus = \
        load_data_split(sp_cfg)
    print(f"  Val reads: {len(val_seqs):,}  |  Species: {n_species}  |  Genera: {n_genus}")

    # ── Build genus→species mask tensor (on CPU) ─────────────────────────────
    # mask[g, s] = True  iff species s belongs to genus g
    mask_cpu = torch.zeros(n_genus, n_species, dtype=torch.bool)
    for gn_id, sp_list in genus_to_species.items():
        for sp_id in sp_list:
            mask_cpu[gn_id, sp_id] = True
    mask_gpu = mask_cpu.to(device)  # (n_genus, n_species)
    print(f"  Genus→species mask: {mask_gpu.shape}, {mask_gpu.sum().item()} valid entries")

    # ── Load tokenizer (shared backbone) ────────────────────────────────────
    from transformers import AutoTokenizer
    backbone_name = sp_cfg["model"]["backbone"]
    print(f"Loading tokenizer: {backbone_name}")
    tokenizer = AutoTokenizer.from_pretrained(
        backbone_name, trust_remote_code=True,
        cache_dir=str(Path.home() / ".cache/huggingface")
    )

    # ── Build dataset & loader ───────────────────────────────────────────────
    sp_max_len = sp_cfg["data"].get("max_token_length", 32)
    kmer_pre   = sp_cfg["data"].get("kmer_preprocess", None)

    # Dataset expects genus labels as well — use species dataset with genus labels
    # We'll use two parallel arrays: sp_labels for model output, gn_labels for routing
    dataset = TokenLevelReadDataset(
        val_seqs, val_sp, tokenizer=tokenizer,
        max_length=sp_max_len, rc_augment=False,
        kmer_preprocess=kmer_pre,
    )
    loader = DataLoader(
        dataset, batch_size=args.batch_size,
        shuffle=False, num_workers=4, pin_memory=True,
        drop_last=False,
    )

    # Also need genus labels per read for routing
    val_gn_arr = np.array(val_gn, dtype=np.int64)

    # ── Load species model ───────────────────────────────────────────────────
    print("Loading NT-Species model...")
    sp_model_cfg = dict(sp_cfg["model"])
    sp_model_cfg["gradient_checkpointing"] = False
    sp_model = create_model(sp_model_cfg, n_species).to(device)
    sp_ckpt = torch.load(args.sp_checkpoint, map_location=device, weights_only=False)
    sp_model.load_state_dict(sp_ckpt["model_state_dict"])
    sp_model.eval()
    print(f"  Loaded epoch {sp_ckpt.get('epoch', '?')}")

    # ── Load genus model ─────────────────────────────────────────────────────
    print("Loading NT-Genus model...")
    gn_model_cfg = dict(gn_cfg["model"])
    gn_model_cfg["gradient_checkpointing"] = False
    gn_model = create_model(gn_model_cfg, n_genus).to(device)
    gn_ckpt = torch.load(args.gn_checkpoint, map_location=device, weights_only=False)
    gn_model.load_state_dict(gn_ckpt["model_state_dict"])
    gn_model.eval()
    print(f"  Loaded epoch {gn_ckpt.get('epoch', '?')}")

    # ── Streaming inference ──────────────────────────────────────────────────
    all_preds  = []
    all_labels = []
    use_amp = device.type == "cuda"

    with torch.no_grad():
        for batch_idx, batch in enumerate(tqdm(loader, desc="Hier inference")):
            input_ids, attention_mask, sp_labels_batch = batch
            input_ids      = input_ids.to(device)
            attention_mask = attention_mask.to(device)

            with torch.autocast(device_type="cuda", enabled=use_amp):
                sp_logits = sp_model(input_ids, attention_mask)   # (B, n_species)
                gn_logits = gn_model(input_ids, attention_mask)   # (B, n_genus)

            # topk=1 genus prediction per read
            gn_pred = gn_logits.argmax(dim=-1)  # (B,)

            # Apply mask: set species logits to -inf for species outside predicted genus
            # mask_gpu[gn_pred] → (B, n_species) boolean
            valid_mask = mask_gpu[gn_pred]           # (B, n_species)
            sp_logits = sp_logits.masked_fill(~valid_mask, float("-inf"))

            preds = sp_logits.argmax(dim=-1).cpu().numpy()
            all_preds.append(preds)
            all_labels.append(sp_labels_batch.numpy())

    all_preds  = np.concatenate(all_preds)
    all_labels = np.concatenate(all_labels)

    accuracy = (all_preds == all_labels).mean()
    print(f"\nHierarchical species accuracy (topk=1): {accuracy*100:.2f}%")
    print(f"Total reads: {len(all_preds):,}")

    # ── Save predictions ─────────────────────────────────────────────────────
    out_path = out_dir / "predictions.npz"
    np.savez_compressed(str(out_path), preds=all_preds, labels=all_labels)
    print(f"Saved: {out_path}")

    acc_dict = {"mode": "nt_species_hier_streaming", "accuracy": float(accuracy),
                "n_reads": int(len(all_preds))}
    with open(out_dir / "accuracy.json", "w") as f:
        json.dump(acc_dict, f, indent=2)
    print(f"Saved: {out_dir}/accuracy.json")


if __name__ == "__main__":
    main()
