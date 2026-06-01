# Predictions Manifest

## Small predictions (in repo, `small_predictions/`)

These are < 1 MB each, kept in Git for downstream analysis:

| File | Description |
|---|---|
| `in_db_mask.npy` | bool (100000,) — True = read's species in Kraken2 DB |
| `missing_species.tsv` | 219 GCF species not in custom Kraken2 DB |
| `predictions_kraken2_twcc.npz` | Kraken2 species predictions on 100K test, with -1 unclassified |
| `predictions_kraken2_twcc_genus.npz` | Kraken2 genus predictions (remapped from species) |
| `mt_species_flat_preds_100K_twcc.npz` | MT 13-mer flat species (aligned to reads_100K.fa) |
| `mt_6mer_species_flat_preds_100K_twcc.npz` | MT 6-mer flat species (aligned) |
| `mt_6mer_hierarchical_preds_100K_twcc.npz` | MT 6-mer hier species (aligned) |
| `mt_genus_13mer_preds_100K_twcc.npz` | MT 13-mer genus (aligned) |
| `mt_genus_6mer_preds_100K_twcc.npz` | MT 6-mer genus (aligned) |

## Large predictions (NOT in repo)

| File | Size | Location | Use |
|---|---|---|---|
| `predictions_predicted.npz` | 48 MB | TWCC: `local_predictions/` | NT-v2 per-genus pipeline (predicted router) |
| `predictions_oracle.npz` | 53 MB | TWCC: `local_predictions/` | NT-v2 per-genus pipeline (oracle router) |
| `predictions.npz` (5M val pool) | various | TWCC: `results/<model>/eval/` | Original full val-pool predictions for each model |
| Predictions on 5M val pool | 30-50 MB each | TWCC: `results/<model>/eval_rc_tta/` | RC TTA predictions for each model |

## Sync (small predictions follow with repo; large via rsync)

```bash
# Large predictions for downstream sample-level eval
rsync -avhP \
    ymj1123ntu@nano5.nchc.org.tw:/work/ymj1123ntu/token_level_gfm_classifier/local_predictions/predictions_*.npz \
    /work/ymj1123ntu/data/predictions/
```
