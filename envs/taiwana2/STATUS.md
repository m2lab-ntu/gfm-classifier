# Taiwana-2 — Status

**Last updated**: 2026-06-01
**GPU**: V100
**Role**: MetaTransformer training + inference (PyTorch Lightning)

## Paths

| Purpose | Path |
|---|---|
| MetaTransformer code | `/home/ymj1123ntu/MetaTransformer/` |
| MT model checkpoints | `/work/ymj1123ntu/MetaTransformer_experiments/` |
| MT data (MT-format val_dir) | (was) `/work/ymj1123ntu/data_50M/metatransformer_format/` — may be cleaned up |
| Vocab files | `/home/ymj1123ntu/MetaTransformer/vocab_file/vocab_{6,13}mer.txt` |

## Available MT models

| Model | exp_dir name (verify) | Notes |
|---|---|---|
| MT 13-mer flat species | `mt_13mer_species_flat` | 53.7% on 100K test (aligned) ✓ |
| MT 13-mer hier species | `mt_13mer_hierarchical` | **Checkpoint corrupted** (val_loss=9.29 @ batch 10K) ✗ |
| MT 6-mer flat species | `mt_6mer_species_flat` | 9.0% ✓ |
| MT 6-mer hier species | `mt_6mer_hierarchical` | 6.4% ✓ |
| MT 13-mer genus | `mt_13mer_genus_50M` | 94.25% ✓ |
| MT 6-mer genus s=1 | `mt_6mer_genus_s1` | 48.76% ✓ |

## Budget

- Recently topped up (as of 5/30 user said available)

## Running / pending

- Per-genus 13-mer species (Exp F): 60/81 genera complete; remaining ~21 genera in queue
- MT 13-mer hier species retraining: pending advisor decision (Q3)

## How to use (from TWCC / Nano4)

```bash
# scp predictions from Taiwana-2 → TWCC (or Nano4)
scp ymj1123ntu@<taiwana2-host>:/path/to/preds.npz \
    ymj1123ntu@nano5.nchc.org.tw:/work/ymj1123ntu/gfm-classifier/small_predictions/
```
