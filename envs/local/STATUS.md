# Local Machine — Status

**Last updated**: 2026-06-01
**Role**: Kraken2 baseline (no GPU needed)

## What ran here

- Kraken2 custom DB build (`k=35`, minimizer `l=31`) from 2,505 UMGS+HGR genomes (1,316 in DB; 219 GCF excluded due to missing local FASTA)
- Kraken2 classification on TWCC's reads_100K.fa
- Generated `in_db_mask.npy` and `missing_species.tsv`
- Generated `predictions_kraken2_twcc.npz` and `predictions_kraken2_twcc_genus.npz`

## Paths (on local machine)

| Purpose | Path | Size |
|---|---|---|
| Kraken2 DB | `/nas2/hierachical_test/kraken2_db/` | 7.2 GB total (hash.k2d 4.1 GB) |
| Reference genomes — UMGS | `/mnt/MetaTransformer_data/UMGS/` | 1.3 GB, 1,952 `.gz` files |
| Reference genomes — HGR | `/mnt/MetaTransformer_data/hgr/` | 562 MB, 553 `.gz` files |
| Genomes in DB (decompressed) | `/nas2/hierachical_test/kraken2_db/library/added/` | 1,316 `.fna` files |
| TWCC test reads | `/nas2/hierachical_test/twcc_test100k/reads_100K.fa` | — |
| TWCC test labels | `/nas2/hierachical_test/twcc_test100k/labels_100K.tsv` | — |
| Local val-100K labels | `/nas2/hierachical_test/data/val_100K/labels_100K_val.tsv` | — |
| Kraken2 raw output | `/nas2/hierachical_test/twcc_test100k/results/reads_100K.kraken2.out` | 6.9 MB |
| Coverage outputs | `/nas2/hierachical_test/twcc_test100k/results/kraken2_coverage/` | — |
| Per-genus NT-v2 models | `/nas2/hierachical_test/token_level_gfm_classifier/results/per_genus_50M/` | — |
| Genus router checkpoint | `/nas2/hierachical_test/token_level_gfm_classifier/results/nt_token_genus_lora_v9_50M/best.pt` | — |

## Environment

| Item | Value |
|---|---|
| OS | Linux 5.15.0-125-generic x86_64 |
| CPU | Intel Xeon W-2255 @ 3.70 GHz, 20 cores |
| Python | 3.11.7 (system, **not** METAGENE conda env) |
| Conda env for Kraken2 scripts | base (system Python) — METAGENE has peft 0.17.1 which breaks NT-v2 LoRA loading |
| Kraken2 version | built from source, k=35, minimizer=31 |

## Notes

- All Kraken2 outputs already scp'd to TWCC at `/work/ymj1123ntu/token_level_gfm_classifier/local_predictions/`
- Small predictions (npz, tsv, npy) are tracked in `small_predictions/` in this repo
- **Do NOT use METAGENE conda env** for NT-v2 inference — peft version mismatch (0.17.1 vs required 0.5.0) causes `.base_layer.weight` KeyError
- No pending tasks unless: (a) extend Kraken2 DB with 219 GCF species, or (b) run CPU throughput benchmark
