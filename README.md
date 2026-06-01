# Token-Level Genomic Foundation Model Classifier

Master's thesis project: token-level fine-tuning of NT-v2 (Nucleotide Transformer v2)
for metagenomic short-read taxonomic classification, with controlled comparisons
against MetaTransformer (from-scratch), DNABERT-1/-2, and Kraken2 (ehBmer baseline).

## What's in this repo

- **`configs/`** — YAML configs for each model (NT-v2 genus/species, DNABERT-1/2, MT)
- **`scripts/`** — Training, evaluation, sample-level analysis, prediction extraction
- **`slurm/`** — SLURM batch scripts (cluster-specific entries inside)
- **`docs/`** — Meeting notes, advisor alignment docs, slide decks
- **`envs/`** — Per-environment status: `twcc/`, `taiwana2/`, `nano4/`, `local/`
- **`data_manifest/`** — Pointers to large files (training data, model weights, predictions) NOT in this repo
- **`results_summary/`** — `metrics.json` for each trained model (no full predictions)
- **`small_predictions/`** — Small `.npz` / `.tsv` artefacts used for downstream analysis

## Quick start (on any environment)

```bash
git clone <repo-url> && cd gfm-classifier

# Set up Python env
conda create -n gfm python=3.11 -y
conda activate gfm
pip install torch transformers peft pandas scikit-learn matplotlib python-pptx scipy tqdm

# Set paths (per environment — edit envs/<your-env>/STATUS.md)
export HF_HOME=/path/to/cache/huggingface
export DATA_DIR=/path/to/balanced_50M

# Run a training (NT-Genus 50M as example)
python scripts/train.py --config configs/nt_token_genus_v9_50M.yaml
```

## Current status

See [`PROGRESS.md`](./PROGRESS.md) for the latest project state.

For environment-specific status (what's installed, what's running, budget, etc.):
- [`envs/twcc/STATUS.md`](./envs/twcc/STATUS.md) — TWCC Nano5 H100 cluster
- [`envs/taiwana2/STATUS.md`](./envs/taiwana2/STATUS.md) — Taiwana-2 V100 cluster (MT models)
- [`envs/nano4/STATUS.md`](./envs/nano4/STATUS.md) — Nano4 H200 (1-month free)
- [`envs/local/STATUS.md`](./envs/local/STATUS.md) — local machine (Kraken2 etc.)

## Data location

Large files (model checkpoints, training reads, large predictions) live on cluster filesystems
and are not in this repo. See [`data_manifest/`](./data_manifest/) for paths + sync instructions.

## License

(TBD)

## Author

楊明儒 (Ming-Ju Yang) · 國立臺灣大學生醫電資所碩二
