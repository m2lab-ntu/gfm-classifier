# Soil NT-v2 5M — Taiwania2 handoff

Train **NT-v2-500M + LoRA** genus classifier on the **same 5M soil reads** as the
MT-5M run, and evaluate on the **same `test_final`** — the clean **6-mer (NT-v2)
vs 13-mer (MT)** tokenization comparison at matched training data.

This package is **self-contained**: it bundles the exact training + eval code that
produced the local result (so there is no `model.py` version drift).

## Local reference result (already run on the RTX 4090)
Reproduce this ballpark on Taiwania2 to confirm the pipeline:

| run | val Top-1 | test_final Top-1 (RC-TTA) |
|---|---|---|
| NT-v2 1M | 0.281 | 0.294 |
| **NT-v2 5M** | **0.308** | **0.320** |

(For context: MT-full 13-mer = 0.830 on test_final; MT-5M is training separately.)

## Prerequisites on Taiwania2
1. **Data already there** (shared with MT-5M) under `/work/ymj1123ntu/mt5m_soil/data/`:
   `train/` (16 shards, 5M), `val/` (8 shards, 200K), `test_final/` (16 shards, 5M).
   NT-v2 rebuilds its `fasta+labels.tsv` from these SAME shards (see run script), so
   NT-v2 and MT train/eval on identical reads.
2. **Conda env** with: `torch` (cu121), `transformers==4.46.3`, `peft`, `scikit-learn`,
   `pandas`, `numpy`, `scipy`, `pyyaml`, `tqdm`, `einops`, `accelerate`.
   (Locally: torch 2.5.1 / transformers 4.46.3 / peft 0.19.1 — training creates fresh
   LoRA so peft version is flexible, but **use the same env for train and eval**.)
3. **⚠️ NT-v2 backbone** `InstaDeepAI/nucleotide-transformer-v2-500m-multi-species`
   must be reachable. **TWCC compute nodes usually have NO internet** → pre-download on a
   login node (or `huggingface-cli download ...`) and set `HF_HOME`/`TRANSFORMERS_CACHE`
   so the compute node reads from cache. This is the most likely blocker.

## Run
```bash
cd /work/ymj1123ntu/gfm-classifier/soil_ntv2_5M      # after git pull
# edit run_ntv2_5M.sh: PKG, BASE, PYTHON/CONDA_ENV, SBATCH partition
sbatch run_ntv2_5M.sh            # or: bash run_ntv2_5M.sh  on an interactive GPU node
```
It does 3 steps: (1) build NT-v2 `fasta+tsv` from the shared shards, (2) train,
(3) eval best.pt on `test_final` (prints fwd/rc/**tta** Top-1).

## Notes / knobs
- `num_classes` is **auto-detected** from the data (sorted unique genus_names = 309).
  No need to set 315/500 here — that 500-vs-315 issue is an MT-only thing.
- `class_indices` / header parsing: NT-v2's `load_data` is **name-keyed** (seq_id →
  genus_name via the TSV), so the soil header field order is handled by the prep script,
  not by a class-index. Genus names come from `idx2name.json` (canonical; Candidatus
  idx 40–44 → `Candidatus_NN`).
- **GPU**: A100 → raise `batch_size` to 512–768. V100 32GB → keep 384. NT-v2+LoRA peak
  was ~21 GB at batch 384 locally; fits 32 GB.
- `run_genus_rctta.py` loads the checkpoint directly (its `.base_layer` rename is a
  no-op for peft≥0.19 checkpoints — already handled).
- Runtime: locally 5M×6ep ≈ 8–9 h on a 4090 (~2000 reads/s, tokenizer-bound). A100
  should be faster; `early_stopping_patience=2` may stop before 6 epochs.

## Send back
`results/nt_soil_genus_5M/eval_test_final/rctta.npz` (has `preds`,`labels`,`acc_tta`)
+ the training_history.csv, so we can slot NT-v2-5M next to MT-5M in the comparison table.
