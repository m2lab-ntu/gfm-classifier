#!/usr/bin/env python3
"""
Run NT-Species inference on the independent 100K test set and save predictions.

The NT-Species model was trained with a species2id encoding derived from the
sorted unique species names in the 50M balanced dataset.  To evaluate on the
100K independent test set we must reconstruct that SAME encoding (from the 50M
labels TSV, without loading the 50M FASTA) and then run inference.

Usage:
    python scripts/run_nt_species_test100k.py \
        --config     configs/nt_token_species_v4_50M.yaml \
        --checkpoint results/nt_token_species_v4_50M/best.pt \
        --test_fasta /work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M/reads_100K.fa \
        --test_labels /work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M/labels_100K.tsv \
        --train_labels /work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M/labels_50M.tsv \
        --out_dir    results/nt_token_species_v4_50M/eval_test100k
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm
from transformers import AutoTokenizer

sys.path.insert(0, str(Path(__file__).parent))
from dataset import TokenLevelReadDataset
from model import create_model
from utils import load_config, save_json


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
    ap = argparse.ArgumentParser()
    ap.add_argument("--config",       required=True)
    ap.add_argument("--checkpoint",   default=None)
    ap.add_argument("--test_fasta",   required=True)
    ap.add_argument("--test_labels",  required=True)
    ap.add_argument("--train_labels", required=True,
                    help="50M labels TSV used to reconstruct training species2id")
    ap.add_argument("--out_dir",      required=True)
    ap.add_argument("--batch_size",   type=int, default=512)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    cfg = load_config(args.config)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint_path = args.checkpoint or os.path.join(cfg["output"]["dir"], "best.pt")

    print(f"Device: {device}")
    if torch.cuda.is_available():
        print(f"GPU:    {torch.cuda.get_device_name(0)}")

    # ── Step 1: Reconstruct training species2id from 50M labels TSV ──────────
    print(f"\nLoading train labels for species2id: {args.train_labels}")
    train_df = pd.read_csv(args.train_labels, sep="\t")
    unique_species = sorted(train_df["species_name"].unique())
    species2id = {s: i for i, s in enumerate(unique_species)}
    num_classes = len(unique_species)
    print(f"  Training vocab: {num_classes} species")

    # ── Step 2: Load 100K test data ───────────────────────────────────────────
    print(f"\nLoading test data: {args.test_fasta}")
    test_df = pd.read_csv(args.test_labels, sep="\t")
    seq_id_to_species = dict(zip(test_df["seq_id"], test_df["species_name"]))

    fasta_ids, fasta_seqs = load_fasta(args.test_fasta)
    print(f"  FASTA reads: {len(fasta_seqs):,}")

    sequences, labels = [], []
    missing = 0
    for sid, seq in zip(fasta_ids, fasta_seqs):
        sp = seq_id_to_species.get(sid)
        if sp is None or sp not in species2id:
            missing += 1
            continue
        sequences.append(seq)
        labels.append(species2id[sp])

    labels = np.array(labels, dtype=np.int64)
    print(f"  Matched: {len(sequences):,}  |  missing/unknown: {missing}")
    print(f"  Unique species in test: {len(set(labels))}")

    # ── Step 3: Build DataLoader ──────────────────────────────────────────────
    backbone_name = cfg["model"]["backbone"]
    trust_remote_code = cfg["model"].get("trust_remote_code", True)
    tokenizer = AutoTokenizer.from_pretrained(
        backbone_name, trust_remote_code=trust_remote_code
    )
    max_token_length = cfg["data"].get("max_token_length", 32)
    kmer_preprocess = cfg["data"].get("kmer_preprocess", None)

    dataset = TokenLevelReadDataset(
        sequences, labels,
        tokenizer=tokenizer,
        max_length=max_token_length,
        rc_augment=False,
        kmer_preprocess=kmer_preprocess,
    )
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
    )

    # ── Step 4: Load model ────────────────────────────────────────────────────
    model_cfg = dict(cfg["model"])
    model_cfg["gradient_checkpointing"] = False
    model = create_model(model_cfg, num_classes).to(device)

    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    print(f"\n✅ Loaded checkpoint (epoch {ckpt.get('epoch', '?')}): {checkpoint_path}")

    # ── Step 5: Run inference ─────────────────────────────────────────────────
    use_amp = cfg["training"].get("amp", True)
    all_preds, all_labels_out = [], []

    with torch.no_grad():
        for batch in tqdm(loader, desc="Inference"):
            input_ids, attention_mask, batch_labels = batch
            input_ids = input_ids.to(device)
            attention_mask = attention_mask.to(device)

            with torch.cuda.amp.autocast(enabled=use_amp):
                logits = model(input_ids=input_ids, attention_mask=attention_mask)

            preds = logits.argmax(dim=-1).cpu().numpy()
            all_preds.append(preds)
            all_labels_out.append(batch_labels.numpy())

    all_preds = np.concatenate(all_preds)
    all_labels_out = np.concatenate(all_labels_out)

    # ── Step 6: Save predictions ──────────────────────────────────────────────
    out_npz = os.path.join(args.out_dir, "predictions.npz")
    np.savez_compressed(out_npz, preds=all_preds, labels=all_labels_out)
    print(f"\nSaved: {out_npz}  ({len(all_preds):,} reads)")

    acc = (all_preds == all_labels_out).mean()
    print(f"Read accuracy: {acc:.4f} ({acc*100:.2f}%)")

    save_json({"num_reads": int(len(all_preds)),
               "num_classes": num_classes,
               "read_accuracy": float(acc),
               "checkpoint": checkpoint_path},
              os.path.join(args.out_dir, "inference_summary.json"))
    print(f"Done. Results in: {args.out_dir}")


if __name__ == "__main__":
    main()
