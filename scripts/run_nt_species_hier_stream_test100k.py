#!/usr/bin/env python3
"""
Streaming NT-Species hierarchical inference on the independent 100K test set.

Loads species + genus models, applies topk=1 genus logit masking per batch,
accumulates only argmax predictions.  Peak memory O(batch) not O(N × C).

Output: eval_hier_stream_test100k/predictions.npz  (preds + labels)
"""

import argparse
import json
import numpy as np
import pandas as pd
import torch
from pathlib import Path
from torch.utils.data import DataLoader
from tqdm import tqdm
from transformers import AutoTokenizer

REPO = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(REPO / "scripts"))

from utils import load_config
from dataset import TokenLevelReadDataset
from model import create_model


def load_fasta(path):
    ids, seqs = [], []
    current_id, current_seq = None, []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if current_id is not None:
                    ids.append(current_id)
                    seqs.append("".join(current_seq))
                current_id = line[1:]
                current_seq = []
            elif line:
                current_seq.append(line)
    if current_id is not None:
        ids.append(current_id)
        seqs.append("".join(current_seq))
    return ids, seqs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sp_config",     required=True)
    parser.add_argument("--sp_checkpoint", required=True)
    parser.add_argument("--gn_config",     required=True)
    parser.add_argument("--gn_checkpoint", required=True)
    parser.add_argument("--test_fasta",    required=True)
    parser.add_argument("--test_labels",   required=True)
    parser.add_argument("--train_labels",  required=True,
                        help="50M labels TSV to reconstruct training class encodings")
    parser.add_argument("--output_dir",    required=True)
    parser.add_argument("--batch_size",    type=int, default=512)
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # ── Load configs ──────────────────────────────────────────────────────────
    sp_cfg = load_config(args.sp_config)
    gn_cfg = load_config(args.gn_config)

    # ── Reconstruct training class encodings from 50M labels TSV ─────────────
    print(f"Loading train labels: {args.train_labels}")
    train_df = pd.read_csv(args.train_labels, sep="\t")
    species_names = sorted(train_df["species_name"].unique())
    genus_names   = sorted(train_df["genus_name"].unique())
    sp2id = {n: i for i, n in enumerate(species_names)}
    gn2id = {n: i for i, n in enumerate(genus_names)}
    n_species = len(species_names)
    n_genus   = len(genus_names)
    print(f"  Species: {n_species}  |  Genera: {n_genus}")

    # Build genus→species mask
    genus_to_species = {}
    for sp_name, gn_name in zip(train_df["species_name"], train_df["genus_name"]):
        sp_id = sp2id.get(sp_name)
        gn_id = gn2id.get(gn_name)
        if sp_id is not None and gn_id is not None:
            genus_to_species.setdefault(gn_id, set()).add(sp_id)

    mask_cpu = torch.zeros(n_genus, n_species, dtype=torch.bool)
    for gn_id, sp_set in genus_to_species.items():
        for sp_id in sp_set:
            mask_cpu[gn_id, sp_id] = True
    mask_gpu = mask_cpu.to(device)
    print(f"  Genus→species mask: {mask_gpu.shape}, {mask_gpu.sum().item()} valid entries")

    # ── Load 100K test data ───────────────────────────────────────────────────
    print(f"\nLoading test FASTA: {args.test_fasta}")
    test_df = pd.read_csv(args.test_labels, sep="\t")
    sid_to_sp = dict(zip(test_df["seq_id"], test_df["species_name"]))

    fasta_ids, fasta_seqs = load_fasta(args.test_fasta)
    print(f"  FASTA reads: {len(fasta_seqs):,}")

    sequences, labels = [], []
    missing = 0
    for sid, seq in zip(fasta_ids, fasta_seqs):
        sp = sid_to_sp.get(sid)
        if sp is None or sp not in sp2id:
            missing += 1
            continue
        sequences.append(seq)
        labels.append(sp2id[sp])
    print(f"  Matched: {len(sequences):,}  |  missing: {missing}")

    # ── Build DataLoader ──────────────────────────────────────────────────────
    backbone_name = sp_cfg["model"]["backbone"]
    print(f"\nLoading tokenizer: {backbone_name}")
    tokenizer = AutoTokenizer.from_pretrained(
        backbone_name, trust_remote_code=True
    )

    sp_max_len = sp_cfg["data"].get("max_token_length", 32)
    kmer_pre   = sp_cfg["data"].get("kmer_preprocess", None)

    dataset = TokenLevelReadDataset(
        sequences, np.array(labels, dtype=np.int64),
        tokenizer=tokenizer,
        max_length=sp_max_len, rc_augment=False,
        kmer_preprocess=kmer_pre,
    )
    loader = DataLoader(
        dataset, batch_size=args.batch_size,
        shuffle=False, num_workers=4, pin_memory=True, drop_last=False,
    )

    # ── Load species model ────────────────────────────────────────────────────
    print("\nLoading NT-Species model...")
    sp_model_cfg = dict(sp_cfg["model"])
    sp_model_cfg["gradient_checkpointing"] = False
    sp_model = create_model(sp_model_cfg, n_species).to(device)
    sp_ckpt = torch.load(args.sp_checkpoint, map_location=device, weights_only=False)
    sp_model.load_state_dict(sp_ckpt["model_state_dict"])
    sp_model.eval()
    print(f"  Loaded epoch {sp_ckpt.get('epoch', '?')}")

    # ── Load genus model ──────────────────────────────────────────────────────
    print("Loading NT-Genus model...")
    gn_model_cfg = dict(gn_cfg["model"])
    gn_model_cfg["gradient_checkpointing"] = False
    gn_model = create_model(gn_model_cfg, n_genus).to(device)
    gn_ckpt = torch.load(args.gn_checkpoint, map_location=device, weights_only=False)
    gn_model.load_state_dict(gn_ckpt["model_state_dict"])
    gn_model.eval()
    print(f"  Loaded epoch {gn_ckpt.get('epoch', '?')}")

    # ── Streaming inference ───────────────────────────────────────────────────
    all_preds  = []
    all_labels_out = []
    use_amp = device.type == "cuda"

    with torch.no_grad():
        for batch in tqdm(loader, desc="Hier streaming (100K test)"):
            input_ids, attention_mask, sp_labels_batch = batch
            input_ids      = input_ids.to(device)
            attention_mask = attention_mask.to(device)

            with torch.autocast(device_type="cuda", enabled=use_amp):
                sp_logits = sp_model(input_ids, attention_mask)  # (B, n_species)
                gn_logits = gn_model(input_ids, attention_mask)  # (B, n_genus)

            gn_pred    = gn_logits.argmax(dim=-1)               # (B,)
            valid_mask = mask_gpu[gn_pred]                       # (B, n_species)
            sp_logits  = sp_logits.masked_fill(~valid_mask, float("-inf"))
            preds      = sp_logits.argmax(dim=-1).cpu().numpy()

            all_preds.append(preds)
            all_labels_out.append(sp_labels_batch.numpy())

    all_preds      = np.concatenate(all_preds)
    all_labels_out = np.concatenate(all_labels_out)

    accuracy = (all_preds == all_labels_out).mean()
    print(f"\nHierarchical species accuracy (100K test, topk=1): {accuracy*100:.2f}%")
    print(f"Total reads: {len(all_preds):,}")

    # ── Save ──────────────────────────────────────────────────────────────────
    out_path = out_dir / "predictions.npz"
    np.savez_compressed(str(out_path), preds=all_preds, labels=all_labels_out)
    print(f"Saved: {out_path}")

    summary = {"mode": "nt_species_hier_streaming_test100k",
               "accuracy": float(accuracy), "n_reads": int(len(all_preds))}
    with open(out_dir / "accuracy.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved: {out_dir}/accuracy.json")


if __name__ == "__main__":
    main()
