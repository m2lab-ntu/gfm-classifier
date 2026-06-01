# Data Manifest

Big files (training data, model weights, large predictions) are **not** stored in this Git repo.
They live on cluster filesystems. This directory documents:

- What files exist
- Where they live (which cluster, which path)
- How to sync them to a new environment

## Files

- [`reference_genomes.md`](./reference_genomes.md) — 2,505 UMGS+HGR + 219 GCF reference assemblies
- [`training_data.md`](./training_data.md) — `reads_50M.fa`, `labels_50M.tsv`, etc.
- [`checkpoints.md`](./checkpoints.md) — NT-v2, MT, DNABERT model weights
- [`predictions.md`](./predictions.md) — Large prediction .npz files

## Sync strategy

For migrating to a new environment (e.g., Nano4), use `rsync` over SSH:

```bash
# On the new environment
rsync -avhP \
    ymj1123ntu@nano5.nchc.org.tw:/work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M/ \
    /work/ymj1123ntu/data/balanced_50M/
```

(NCHC intra-cluster network ~10 Gbps — 11 GB `reads_50M.fa` takes ~15-30 min.)
