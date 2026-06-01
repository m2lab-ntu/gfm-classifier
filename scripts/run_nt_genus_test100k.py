#!/usr/bin/env python3
"""NT-Genus v9 inference on the independent 100K test set (parallels run_nt_species_test100k.py)."""

import argparse, os, sys
from pathlib import Path
import numpy as np, pandas as pd, torch
from torch.utils.data import DataLoader
from tqdm import tqdm
from transformers import AutoTokenizer

sys.path.insert(0, str(Path(__file__).parent))
from dataset import TokenLevelReadDataset
from model import create_model
from utils import load_config, save_json


def load_fasta(path):
    ids, seqs = [], []
    cur_id, cur_seq = None, []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if cur_id is not None:
                    ids.append(cur_id); seqs.append("".join(cur_seq))
                cur_id = line[1:]; cur_seq = []
            elif line:
                cur_seq.append(line)
    if cur_id is not None:
        ids.append(cur_id); seqs.append("".join(cur_seq))
    return ids, seqs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config",       required=True)
    ap.add_argument("--checkpoint",   default=None)
    ap.add_argument("--test_fasta",   required=True)
    ap.add_argument("--test_labels",  required=True)
    ap.add_argument("--train_labels", required=True)
    ap.add_argument("--out_dir",      required=True)
    ap.add_argument("--batch_size",   type=int, default=512)
    ap.add_argument("--rc_tta",       action="store_true")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    cfg = load_config(args.config)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt_path = args.checkpoint or os.path.join(cfg["output"]["dir"], "best.pt")

    # Reconstruct training genus2id
    train_df = pd.read_csv(args.train_labels, sep="\t")
    genus_names = sorted(train_df["genus_name"].unique())
    genus2id = {g: i for i, g in enumerate(genus_names)}
    n_classes = len(genus_names)
    print(f"Training genera: {n_classes}")

    # Load 100K test data
    test_df = pd.read_csv(args.test_labels, sep="\t")
    sid_to_genus = dict(zip(test_df["seq_id"], test_df["genus_name"]))
    fasta_ids, fasta_seqs = load_fasta(args.test_fasta)

    sequences, labels = [], []
    missing = 0
    for sid, seq in zip(fasta_ids, fasta_seqs):
        gn = sid_to_genus.get(sid)
        if gn is None or gn not in genus2id:
            missing += 1; continue
        sequences.append(seq); labels.append(genus2id[gn])
    labels = np.array(labels, dtype=np.int64)
    print(f"Matched: {len(sequences):,}, missing: {missing}")

    # Build dataset / loader
    backbone = cfg["model"]["backbone"]
    tokenizer = AutoTokenizer.from_pretrained(backbone, trust_remote_code=True)
    max_len = cfg["data"].get("max_token_length", 32)
    kmer_pre = cfg["data"].get("kmer_preprocess", None)
    ds = TokenLevelReadDataset(sequences, labels, tokenizer=tokenizer,
                                max_length=max_len, rc_augment=False, kmer_preprocess=kmer_pre)
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=False,
                        num_workers=4, pin_memory=True)

    # Load model
    model_cfg = dict(cfg["model"]); model_cfg["gradient_checkpointing"] = False
    model = create_model(model_cfg, n_classes).to(device)
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    print(f"Loaded epoch {ckpt.get('epoch','?')}: {ckpt_path}")

    # Inference
    all_preds, all_labels = [], []
    use_amp = cfg["training"].get("amp", True)
    with torch.no_grad():
        for batch in tqdm(loader, desc="Inference"):
            input_ids, attn, lbls = batch
            input_ids = input_ids.to(device); attn = attn.to(device)
            with torch.cuda.amp.autocast(enabled=use_amp):
                logits = model(input_ids=input_ids, attention_mask=attn)
                if args.rc_tta:
                    # Reverse-complement input
                    rc_input = torch.flip(input_ids, dims=[1])  # simple flip; tokenizer-aware RC ideally
                    logits_rc = model(input_ids=rc_input, attention_mask=attn)
                    logits = logits + logits_rc
            preds = logits.argmax(-1).cpu().numpy()
            all_preds.append(preds); all_labels.append(lbls.numpy())

    all_preds = np.concatenate(all_preds); all_labels = np.concatenate(all_labels)
    out_npz = os.path.join(args.out_dir, "predictions.npz")
    np.savez_compressed(out_npz, preds=all_preds, labels=all_labels)
    acc = (all_preds == all_labels).mean()
    print(f"\nGenus Top-1 on 100K test: {acc*100:.2f}%")
    save_json({"num_reads": int(len(all_preds)), "num_classes": n_classes,
               "read_accuracy": float(acc), "checkpoint": ckpt_path},
              os.path.join(args.out_dir, "inference_summary.json"))


if __name__ == "__main__":
    main()
