#!/usr/bin/env python3
"""
Data loader for Token-level GFM Classifier.

Loads FASTA sequences + labels TSV and splits into train/val.
Uses the SAME split logic as all previous baselines (train_test_split, stratified, seed=42).
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from typing import Dict, List, Set, Tuple


def load_fasta(fasta_path: str) -> Tuple[List[str], List[str]]:
    """Load sequences from FASTA file. Returns (seq_ids, sequences)."""
    seq_ids, sequences = [], []
    current_id, current_seq = None, []

    with open(fasta_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if current_id is not None and current_seq:
                    seq_ids.append(current_id)
                    sequences.append("".join(current_seq))
                current_id = line[1:]  # full header without >
                current_seq = []
            else:
                current_seq.append(line.upper())
        # last record
        if current_id is not None and current_seq:
            seq_ids.append(current_id)
            sequences.append("".join(current_seq))

    return seq_ids, sequences


def load_data(
    fasta_path: str,
    labels_path: str,
    val_ratio: float = 0.1,
    seed: int = 42,
    task: str = "genus",
) -> Dict:
    """
    Load FASTA sequences and labels, split into train/val.

    Uses train_test_split with stratify + random_state=42 for consistency
    with all previous NT embedding experiments.

    Args:
        fasta_path: Path to reads_500k.fa
        labels_path: Path to labels_500k.tsv
        val_ratio: Validation ratio (default 0.1)
        seed: Random seed (default 42)
        task: "genus" or "species"

    Returns:
        Dict with train/val data + metadata
    """
    print(f"Loading data from:\n  FASTA:  {fasta_path}\n  Labels: {labels_path}")

    # ---- Read labels TSV ----
    labels_df = pd.read_csv(labels_path, sep="\t")
    print(f"  Labels TSV columns: {list(labels_df.columns)}")
    print(f"  Total rows in TSV: {len(labels_df):,}")

    # Build seq_id → row mapping
    seq_id_to_row = {}
    for i, row in labels_df.iterrows():
        seq_id_to_row[row["seq_id"]] = row

    # ---- Read FASTA and match labels ----
    fasta_ids, fasta_seqs = load_fasta(fasta_path)
    print(f"  Total sequences in FASTA: {len(fasta_seqs):,}")

    # Match in FASTA order (preserves ordering for reproducibility)
    sequences, genus_names_list, species_names_list = [], [], []
    for sid, seq in zip(fasta_ids, fasta_seqs):
        if sid in seq_id_to_row:
            row = seq_id_to_row[sid]
            sequences.append(seq)
            genus_names_list.append(row["genus_name"])
            species_names_list.append(row["species_name"])

    sequences = np.array(sequences)
    print(f"  Matched sequences: {len(sequences):,}")

    # ---- Create label encodings (sorted unique → id) ----
    unique_genera = sorted(set(genus_names_list))
    unique_species = sorted(set(species_names_list))
    genus2id = {g: i for i, g in enumerate(unique_genera)}
    species2id = {s: i for i, s in enumerate(unique_species)}

    genus_labels = np.array([genus2id[g] for g in genus_names_list], dtype=np.int64)
    species_labels = np.array([species2id[s] for s in species_names_list], dtype=np.int64)

    print(f"  Genera: {len(unique_genera)}, Species: {len(unique_species)}")

    # ---- Build genus <-> species mappings ----
    _g2s_sets: Dict[int, Set[int]] = {}
    for gn, sn in zip(genus_names_list, species_names_list):
        gid, sid = genus2id[gn], species2id[sn]
        _g2s_sets.setdefault(gid, set()).add(sid)
    genus_to_species: Dict[int, List[int]] = {
        g: sorted(s) for g, s in _g2s_sets.items()
    }
    species_to_genus: Dict[int, int] = {}
    for gid, sids in genus_to_species.items():
        for sid in sids:
            species_to_genus[sid] = gid
    avg_sp = np.mean([len(v) for v in genus_to_species.values()])
    print(f"  Genus->Species map: {len(genus_to_species)} genera, "
          f"avg {avg_sp:.1f} species/genus")

    # ---- Train/Val split ----
    # Always stratify by genus labels — safe even for species task
    # (avoids crash on rare species and keeps genus distribution matched)
    train_idx, val_idx = train_test_split(
        np.arange(len(sequences)),
        test_size=val_ratio,
        stratify=genus_labels,
        random_state=seed,
    )

    print(f"  Train: {len(train_idx):,}, Val: {len(val_idx):,}")

    return {
        "train_sequences": sequences[train_idx],
        "train_genus_labels": genus_labels[train_idx],
        "train_species_labels": species_labels[train_idx],
        "val_sequences": sequences[val_idx],
        "val_genus_labels": genus_labels[val_idx],
        "val_species_labels": species_labels[val_idx],
        "genus2id": genus2id,
        "species2id": species2id,
        "id2genus": {v: k for k, v in genus2id.items()},
        "id2species": {v: k for k, v in species2id.items()},
        "num_genera": len(unique_genera),
        "num_species": len(unique_species),
        "genus_to_species": genus_to_species,
        "species_to_genus": species_to_genus,
    }

