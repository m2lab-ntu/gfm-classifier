#!/usr/bin/env python3
"""
Lazy-loading FASTA dataset for large-scale DDP training.

Stores only file byte-offsets in RAM; reads sequences on demand via seek().
Suitable for 258M-scale datasets where loading all sequences into RAM is infeasible.

Memory usage:
  Index array:  N × 16 bytes  (int64 offset + int32 genus + int32 species)
  For 258M reads: ~4.1 GB per DDP rank

Usage:
  dataset = LazyFASTADataset(
      fasta_path, labels_path, tokenizer, max_length, split="train", val_ratio=0.1, seed=42
  )

The dataset builds (or loads a cached) binary index file `<fasta_path>.idx.npy`
on first instantiation.  Subsequent runs reuse the cache (build time: ~3-5 min).
"""

import hashlib
import os
import threading
import numpy as np
from pathlib import Path
from torch.utils.data import Dataset
import torch
import pandas as pd


class LazyFASTADataset(Dataset):
    """
    Random-access FASTA dataset backed by byte-offset index.

    Each worker thread maintains its own open file handle to avoid contention.
    """

    def __init__(
        self,
        fasta_path: str,
        labels_path: str,
        tokenizer,
        max_length: int = 32,
        split: str = "train",          # "train" or "val"
        val_ratio: float = 0.1,
        seed: int = 42,
        rc_augment: bool = False,
        kmer_preprocess=None,
    ):
        self.fasta_path = str(fasta_path)
        self.tokenizer  = tokenizer
        self.max_length = max_length
        self.rc_augment = rc_augment
        self.kmer_preprocess = kmer_preprocess
        self._local = threading.local()   # per-thread file handle

        # ── 1. Load or build index ──────────────────────────────────────────
        index_path = Path(fasta_path).with_suffix(".idx.npy")
        if index_path.exists():
            print(f"  Loading cached index: {index_path}")
            index = np.load(str(index_path), allow_pickle=False)
        else:
            print(f"  Building FASTA index (one-time, ~3-5 min): {fasta_path}")
            index = self._build_index(fasta_path, index_path)

        # dtype: offset (int64), genus_class (int32), species_class (int32)
        self._index = index  # shape (N, 3)

        # ── 2. Load labels for class-name lookup + consistency check ────────
        df = pd.read_csv(labels_path, sep="\t",
                         dtype={"species_class": int, "genus_class": int})
        self.num_genera  = int(df["genus_class"].nunique())
        self.num_species = int(df["species_class"].nunique())

        # ── 3. Train / val split ────────────────────────────────────────────
        N = len(index)
        rng = np.random.default_rng(seed)
        perm = rng.permutation(N)
        n_val = int(N * val_ratio)

        if split == "val":
            self._idx = perm[:n_val]
        else:
            self._idx = perm[n_val:]

        print(f"  Split={split}: {len(self._idx):,} reads "
              f"(genera={self.num_genera}, species={self.num_species})")

    # ── Index building ──────────────────────────────────────────────────────

    @staticmethod
    def _build_index(fasta_path: str, index_path: Path) -> np.ndarray:
        """Single-pass scan: record (offset, genus_class, species_class) per read."""
        dtype = np.dtype([("offset", np.int64), ("genus", np.int32), ("species", np.int32)])
        records = []
        CHUNK = 1_000_000

        with open(fasta_path, "rb") as f:
            offset = 0
            n = 0
            for raw_line in f:
                if raw_line[0:1] == b">":
                    header = raw_line.decode().rstrip()[1:]
                    parts  = header.split("|")
                    try:
                        sp  = int(parts[1])
                        gn  = int(parts[3])
                    except (IndexError, ValueError):
                        sp, gn = -1, -1
                    records.append((offset, gn, sp))
                    n += 1
                    if n % 5_000_000 == 0:
                        print(f"    indexed {n:,} reads...", flush=True)
                offset += len(raw_line)

        arr = np.array(records, dtype=dtype)
        np.save(str(index_path), arr)
        print(f"  Index saved to {index_path}  ({len(arr):,} reads)")
        return arr

    # ── Dataset interface ───────────────────────────────────────────────────

    def __len__(self):
        return len(self._idx)

    def _get_file(self):
        if not hasattr(self._local, "fh") or self._local.fh.closed:
            self._local.fh = open(self.fasta_path, "rb")
        return self._local.fh

    def _read_seq(self, global_idx: int) -> str:
        rec = self._index[global_idx]
        fh  = self._get_file()
        fh.seek(int(rec["offset"]))
        fh.readline()           # skip header line
        seq_bytes = fh.readline()
        return seq_bytes.decode().strip()

    def _reverse_complement(self, seq: str) -> str:
        comp = {"A": "T", "T": "A", "C": "G", "G": "C",
                "a": "t", "t": "a", "c": "g", "g": "c"}
        return "".join(comp.get(b, "N") for b in reversed(seq))

    def _kmer_split(self, seq: str, k: int, stride: int) -> str:
        kmers = [seq[i:i+k] for i in range(0, len(seq) - k + 1, stride)]
        return " ".join(kmers)

    def __getitem__(self, local_idx: int):
        global_idx  = int(self._idx[local_idx])
        rec         = self._index[global_idx]
        genus_class = int(rec["genus"])
        seq         = self._read_seq(global_idx)

        # Optional RC augmentation
        if self.rc_augment and np.random.random() < 0.5:
            seq = self._reverse_complement(seq)

        # Optional k-mer preprocessing
        if self.kmer_preprocess is not None:
            seq = self._kmer_split(seq, self.kmer_preprocess["k"],
                                   self.kmer_preprocess.get("stride", 1))

        enc = self.tokenizer(
            seq,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        input_ids      = enc["input_ids"].squeeze(0)
        attention_mask = enc["attention_mask"].squeeze(0)
        label          = torch.tensor(genus_class, dtype=torch.long)

        return input_ids, attention_mask, label

    def get_genus_labels(self) -> np.ndarray:
        """Return genus labels for all samples in this split (for class-weight computation)."""
        return self._index[self._idx]["genus"].astype(np.int32)
