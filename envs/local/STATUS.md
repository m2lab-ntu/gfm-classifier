# Local Machine — Status

**Last updated**: 2026-06-01
**Role**: Kraken2 baseline (no GPU needed)

## What ran here

- Kraken2 custom DB build (`k=35`, minimizer `l=31`) from 2,505 UMGS+HGR genomes (1,316 in DB; 219 GCF excluded due to missing local FASTA)
- Kraken2 classification on TWCC's reads_100K.fa
- Generated `in_db_mask.npy` and `missing_species.tsv`
- Generated `predictions_kraken2_twcc.npz` and `predictions_kraken2_twcc_genus.npz`

## Paths (on local machine)

| Purpose | Path |
|---|---|
| Kraken2 DB | TBD (filled in by user) |
| Reference genomes | TBD |

## Notes

- All Kraken2 outputs already scp'd to TWCC at `/work/ymj1123ntu/token_level_gfm_classifier/local_predictions/`
- No pending tasks here unless we want to (a) extend DB with the missing 219 GCF species or (b) benchmark Kraken2 CPU throughput
