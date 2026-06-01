# Taiwana-2 — Status

**Last updated**: 2026-06-01
**GPU**: 2× Tesla V100-SXM2 32GB
**Role**: MetaTransformer training + inference (PyTorch Lightning)
**SLURM account**: MST114414  **Partition**: gp2d

## Paths

| Purpose | Path |
|---|---|
| MetaTransformer code | `/home/ymj1123ntu/MetaTransformer/` |
| Inference script | `/home/ymj1123ntu/MetaTransformer/extract_mt_predictions.py` |
| MT experiments base | `/work/ymj1123ntu/mt_50M/experiments/` |
| Vocab 6-mer | `/work/ymj1123ntu/vocab_file/vocab_6mer.txt` |
| Vocab 13-mer | `/work/ymj1123ntu/vocab_file/vocab_13mer.txt` |
| Per-genus split data | `/work/ymj1123ntu/per_genus_split/` |
| Per-genus models | `/work/ymj1123ntu/per_genus_13mer_models/` |
| Per-genus pred slices | `/work/ymj1123ntu/per_genus_13mer_preds/` |
| 100K aligned val dir | `/work/ymj1123ntu/mt_test100k_val_dir/reads_100K.fa` |
| 100K aligned preds | `/work/ymj1123ntu/mt_preds_100K_twcc/` |
| Disk usage | 1.6T / ~2.5T quota |

## Available MT models

All under `/work/ymj1123ntu/mt_50M/experiments/`

| Model | exp_dir | class_indices | Acc (100K aligned, no RC TTA) |
|---|---|---|---|
| MT 13-mer flat species (stride=1) | `mt_13mer_stride1_species_895688` | 1 | 53.70% |
| MT 13-mer hier species (stride=13) | `mt_13mer_stride13_species_895687` | 1 | **0.53% — checkpoint corrupted** (best saved at batch 10K, val_loss=9.29) ✗ |
| MT 6-mer flat species (stride=1) | `mt_6mer_stride1_species_894641` | 1 | 9.04% |
| MT 6-mer hier species (stride=6) | `mt_6mer_stride6_species_894640` | 1 | 6.40% |
| MT 13-mer genus (stride=1) | `mt_13mer_stride1_genus_895686` | 3 | 94.25% |
| MT 6-mer genus s=1 | `mt_6mer_stride1_50M_887333` | 3 | 48.76% |

> Accuracies measured on `reads_100K.fa` (TWCC-provided, single-file val_dir → correct read ordering).
> RC TTA not applied. Original RC TTA benchmarks from TWCC differ slightly.

## Completed experiments

### Exp F — Per-genus 13-mer species classifier
- **Status**: COMPLETE ✓ — 81/81 genera trained + inferred (2026-06-01)
- **Merged result**: `/work/ymj1123ntu/mt_per_genus_13mer_preds_100K.npz`
  - Top-1 accuracy: **57.20%** (97,767/100,000 valid, 2,233 unrouted)
  - Sent to TWCC: `/work/ymj1123ntu/token_level_gfm_classifier/local_predictions/mt_per_genus_13mer_preds_100K.npz`
- SLURM script: `/work/ymj1123ntu/run_per_genus_13mer_array.sh`
- Training script: `/home/ymj1123ntu/MetaTransformer/train_infer_per_genus_13mer.py`
- Genus list: `/work/ymj1123ntu/per_genus_list.txt` (81 lines)
- Dynamic max_steps: n_species ≤5 → 5000, ≤15 → 10000, else → 20000

### MT 100K aligned inference (V100 backup)
- **Status**: COMPLETE ✓ (5/6 models; hier species unusable)
- Output: `/work/ymj1123ntu/mt_preds_100K_twcc/*.npz`
- Sent to TWCC: `/work/ymj1123ntu/token_level_gfm_classifier/local_predictions/`
- Timing logs: `/work/ymj1123ntu/mt_preds_100K_twcc/logs/`

## Running / Pending

- **No jobs currently running**
- MT 13-mer hier species: checkpoint corrupted on Taiwana-2; needs retraining or import from TWCC H100 run

## Budget

- Account MST114414 depleted ~2026-05-25 (−27.7 credits), restored ~2026-05-30
- Current status: check HPC portal

## How to run inference

```bash
PYTHON=/home/ymj1123ntu/.conda/envs/MetaTransformer/bin/python3
PYTHONPATH=/home/ymj1123ntu/MetaTransformer/src \
$PYTHON /home/ymj1123ntu/MetaTransformer/extract_mt_predictions.py \
    --exp_dir  /work/ymj1123ntu/mt_50M/experiments/<exp_dir_name> \
    --val_dir  /work/ymj1123ntu/mt_test100k_val_dir \
    --out      /path/to/output.npz \
    --class_indices <1=species|3=genus> \
    --batch_size 1024
```
