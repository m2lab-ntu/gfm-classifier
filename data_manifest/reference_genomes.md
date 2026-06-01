# Reference Genomes Manifest

## Inventory

- **Total target species**: 1,535
  - UMGS: 1,179 (uncultured metagenome-assembled genomes)
  - HGR: 137 (Human Gut Reference)
  - GCF/RefSeq: 219 (well-characterised RefSeq assemblies)

## Total reference genomes used

- **Training (NT-v2 / MT / DNABERT)**: 2,505 genomes (all 1,535 species, multiple strains some species)
- **Kraken2 custom DB**: 1,316 species (UMGS + HGR only; the 219 GCF species had no locally available FASTA)

## Location

- TWCC: `/work/ymj1123ntu/gfm_embedding_classification/data/labeled_multi_level_generated/genomes/` (~10 GB)
- Local machine (Kraken2 only):
  - UMGS source: `/mnt/MetaTransformer_data/UMGS/` (1.3 GB, 1,952 `.gz` files)
  - HGR source: `/mnt/MetaTransformer_data/hgr/` (562 MB, 553 `.gz` files)
  - Kraken2 DB: `/nas2/hierachical_test/kraken2_db/` (7.2 GB, 1,316 species)
  - Decompressed `.fna` in DB: `/nas2/hierachical_test/kraken2_db/library/added/`

## Notes

- The 219 GCF species missing from Kraken2 DB are listed in `small_predictions/missing_species.tsv` (with species_class + n_reads)
- These species ARE in NT-v2 / MT training data (in-distribution for neural models)
- The "OOD vs neural" finding is therefore a Kraken2-DB-coverage asymmetry, not generalisation
