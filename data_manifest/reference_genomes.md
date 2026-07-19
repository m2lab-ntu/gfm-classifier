# Reference Genomes Manifest

## Inventory

- **Total target species**: 1,535
  - UMGS: 1,179 (uncultured metagenome-assembled genomes)
  - HGR: 137 (Human Gut Reference)
  - GCF/RefSeq: 219 (well-characterised RefSeq assemblies)

## Total reference genomes used

- **Training (NT-v2 / MT / DNABERT)**: same 1,535 species catalogue (reads simulated from genomes)
- **Kraken2 custom DB (legacy)**: 1,316 species (UMGS + HGR only; GCF FASTAs were missing at first build)
- **Kraken2 matched-reference DB (2026-07)**: **1,535 species** (UMGS + HGR + GCF) — fair vs NT/MT

## Location

- CrucialX9 (authoritative FASTAs for 1,535): `/media/user/CrucialX9/MetaTransformer_data/genomes/`
  (~2,505 `.fa.gz` stems; labels use 1,535 of them)
- Taxonomy / maps: `/media/user/CrucialX9/MetaTransformer_data/taxonomy_files/`
- TWCC (legacy): `/work/ymj1123ntu/gfm_embedding_classification/data/labeled_multi_level_generated/genomes/`
- Local Kraken2 DBs:
  - Legacy (1,316): `/nas2/hierachical_test/kraken2_db/`
  - Matched (1,535): `/nas2/hierachical_test/kraken2_db_1535/` (~9 GB; `k=35`, Bracken 150‑mer)
- Build script: `scripts/build_kraken2_db_1535.py`
- Eval pack: `docs/paper_direction_review_2026_07/kraken_matched_1535/`

## Notes

- Legacy missing GCF list: `small_predictions/missing_species.tsv` (also under the review pack)
- Those GCF species **are** in NT/MT training; the old Kraken comparison was a **DB-coverage asymmetry**, fixed by the 1,535 rebuild
- Taxid convention: `taxid = species_class + 2` (matches `convert_kraken2_preds*.py`)
