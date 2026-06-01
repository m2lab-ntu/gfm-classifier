# Training Data Manifest

## Balanced 50M dataset

Stratified subsample from full HGR-UMGS pool (258M reads), used for all 50M-scale training.

| File | Size | Description |
|---|---|---|
| `reads_50M.fa` | ~11 GB | 50,000,000 reads × 150bp paired-end, ART Illumina simulation |
| `labels_50M.tsv` | ~5 GB | seq_id, species_class, genus_class, species_name, genus_name |
| `reads_100K.fa` | 19 MB | Independent 100K test set (1,535 species, pure UMGS+HGR) |
| `labels_100K.tsv` | 7.5 MB | Labels for 100K test |

### Location (TWCC / Nano5)

- `/work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M/`

### How to sync to Nano4

```bash
mkdir -p /work/ymj1123ntu/data/balanced_50M
rsync -avhP \
    ymj1123ntu@nano5.nchc.org.tw:/work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M/ \
    /work/ymj1123ntu/data/balanced_50M/
```

## Full HGR-UMGS pool (258M reads)

| File | Size | Description |
|---|---|---|
| `reads.fa` | ~58 GB | 258M reads from 2,505 genomes |
| `labels.tsv` | ~26 GB | Labels |

### Location

- `/work/ymj1123ntu/gfm_embedding_classification/data/labeled_multi_level_generated/`

### Notes

- Probably NOT needed for current Nano4 work (50M is already at log-fit saturation)
- Sync only if doing 258M extrapolation experiment
