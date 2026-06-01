# CLAUDE.md

This is the **clean repo** for the token-level GFM classifier project.
Old working directory: `/work/ymj1123ntu/token_level_gfm_classifier` (kept as data stash, not source of truth).

## Environment

- **TWCC (Nano5)**: H100 cluster, `nano5.nchc.org.tw`, budget exhausted as of 5/30
- **Taiwana-2**: V100 cluster, hosts MetaTransformer training (`/work/ymj1123ntu/MetaTransformer_experiments/`)
- **Nano4**: H200, free 1-month service (target migration destination)
- **Local**: personal machine (ran Kraken2 baseline, no GPU)

Python: Miniconda `gfm` env (`conda activate gfm`).

## Layout

```
gfm-classifier/
├── configs/            YAML configs for each model
├── scripts/            Training, evaluation, analysis Python scripts
├── slurm/              SLURM batch scripts (env-specific entries inside)
├── docs/               Meeting notes, slide decks, plans
├── envs/<env>/STATUS.md     Per-environment state (paths, budget, progress)
├── data_manifest/      Pointers to big files (not in repo)
├── results_summary/    metrics.json per model (no predictions.npz)
└── small_predictions/  Small .npz / .tsv used by downstream analysis
```

## Key commands

```bash
# Train
python scripts/train.py --config configs/nt_token_genus_v9_50M.yaml

# Evaluate forward-only
python scripts/evaluate.py --config configs/nt_token_genus_v9_50M.yaml

# Evaluate with RC TTA
python scripts/evaluate.py --config configs/nt_token_genus_v9_50M.yaml --rc_tta

# Sample-level eval
python scripts/evaluate_sample.py --predictions <preds.npz> --out_dir <dir> \
    --reads_per_sample 1000 --n_partition_samples 100 \
    --n_sparse_samples 200 --genera_present 50
```

See [`PROGRESS.md`](./PROGRESS.md) for current project state.
