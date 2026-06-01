# TWCC (Nano5) — Status

**Last updated**: 2026-06-01
**Host**: `nano5.nchc.org.tw`
**GPU**: H100 (single-GPU jobs in `normal` partition, 48 hr max)
**Conda env**: `gfm` at `~/miniconda/envs/gfm`

## Paths

| Purpose | Path |
|---|---|
| Repo clone (new) | `/work/ymj1123ntu/gfm-classifier/` |
| Old working dir | `/work/ymj1123ntu/token_level_gfm_classifier/` (data stash) |
| Training data | `/work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M/` |
| HF cache | `/work/ymj1123ntu/.cache/huggingface/` |
| Thesis (separate repo) | `/work/ymj1123ntu/thesis/` |

## Budget

- iService wallet: **-802.521 points** (exhausted on 2026-05-30)
- Status: Cannot `sbatch` new jobs until top-up

## Last job state

- 216281 (DNABERT-2 50M): TIMEOUT @ 48 hr, 17/30 epochs, val_acc 59.22%, `last.pt` saved
- 216282 (DNABERT-1 50M): TIMEOUT @ 48 hr, 4/30 epochs, val_acc 59.50% — recommend cancel
- 218570 (NT-Genus 100K test): COMPLETED, 66.61% in eval_test100k/

## Notes

- DNABERT-2 50M can be resumed via auto-resume in `slurm/run_dnabert2_genus_50M.sh` (loads `last.pt` if exists)
- Speed/memory benchmark planned but blocked on (a) budget, (b) MT model migration from Taiwana-2
