# Paper direction review pack (2026-07)

Local handoff for reviewing **Briefings in Bioinformatics** manuscript direction against all experiments run in the July 2026 session (mock community, out-of-genome Track A, matched-reference Kraken2).

**Repo path:** `docs/paper_direction_review_2026_07/`  
**Related paper repo:** [ymj1123/gfm-metagenomic-benchmark-paper](https://github.com/ymj1123/gfm-metagenomic-benchmark-paper/) (fork; org copy `m2lab-ntu` may lag)

---

## 0. How to use this pack

1. Read this file end-to-end (especially §5 decisions).
2. Open numbers in:
   - `kraken_matched_1535/COMPARISON.md`
   - `mock_d6331/mock_reps_combined_summary.json` + `enhanced_rep1_SUMMARY.md`
   - `track_a_newgenome/metrics_clean.json`
3. Large artifacts stay on NAS (see §6); this pack is metrics + scripts only (~1.5 MB).

---

## 1. Experiment map

| ID | Question | Status | Key result | Folder |
|---|---|---|---|---|
| **A** | Closed-set GFM vs tokenization / pretrain / scale | Done (paper core) | Tokenization ≫ pretrain ≫ scale; MT 13-mer ~98.7% @250M | `small_predictions/`, paper §4–5 |
| **B** | Fair Kraken baseline (same genomes as NT/MT)? | **Done this session** | Rebuilt Kraken on **1,535** genomes (incl. 219 GCF); full-pool genus raw **80%**, Bracken **r≈1.0** | `kraken_matched_1535/` |
| **C** | Real mock community (D6331 × 2 reps) | Done | All methods drop to r≈0.4–0.6; CIs overlap; K2B ≈ MT > NT on mean r | `mock_d6331/` |
| **D** | Out-of-genome (same genera, new accessions) | Done (Track A) | MT 13-mer 98.7% → **~33%**; NT ~26%; memorization exposed | `track_a_newgenome/` |
| **E** | Soil 5M NT/MT | In progress (Taiwania2) | Not in this pack | `soil_reeval/` on NAS |

---

## 2. Matched-reference Kraken2 (Experiment B) — detail

### Why

Old custom DB skipped **219 GCF** (no local FASTA) → forced “coverage-matched” 85,819-read pool. Unfair vs NT/MT trained on all 1,535.

### What we did

- Genome source: `/media/user/CrucialX9/MetaTransformer_data/genomes` (1,535/1,535 found).
- Built DB: `/nas2/hierachical_test/kraken2_db_1535/` (`k=35`, `l=31`, taxid = `species_class + 2`, Bracken 150 bp).
- Scripts: `scripts/build_kraken2_db_1535.py`, `scripts/eval_kraken1535_vs_neural.py` (also copied under repo `scripts/`).
- Evaluated on TWCC 100K pool vs existing MT/NT preds + fresh NT RC-TTA.

### Headline numbers (genus, TWCC 100K)

**Full pool (fair after GCF included)**

| Model | Classified | Read acc | Pearson r | Bray–Curtis |
|---|---:|---:|---:|---:|
| Kraken2 raw | 80.0% | **80.0%** | 0.832 | 0.111 |
| Kraken2+Bracken | — | — | **1.000** | **0.004** |
| MT 13-mer | 100% | **94.3%** | 1.000 | 0.015 |
| NT-v2 RC-TTA | 100% | 67.4% | 0.994 | 0.091 |
| MT 6-mer | 100% | 48.8% | 0.984 | 0.166 |

**Legacy 85,819 subset** (continuity with paper table): Kraken raw 77.2% / r=0.824 (paper 77.7% / 0.823); MT 13-mer 94.9%; NT 69.7%.

**Species-level Kraken:** old DB 66.2% top-1 all → new DB **79.5%**; classified 70% → **80%** (remaining ~20% often LCA→root, not missing genomes).

See `kraken_matched_1535/COMPARISON.md`.

### Implications for the paper

- Main Kraken comparison should move to **full 100K matched-reference**, not only 85K.
- Abundance story strengthens: with matched genomes, **Bracken is essentially perfect** on this simulated pool; neural models have **no abundance advantage**.
- Read-level: MT 13-mer still ahead of Kraken; NT-v2 still behind Kraken raw.
- Old “Kraken weak because of GCF hole” caveat is largely fixed for in-catalogue simulation.

---

## 3. Mock community D6331 (Experiment C)

- Two Illumina replicates; NT-v2, MT 13-mer 250M, Kraken2+Bracken (same gut custom DB at the time — **old 1,316** for mock; optional re-run with 1535 DB later).
- Metrics: Pearson / Spearman / filtered r / Bray–Curtis / fixed detection / bootstrap CI on n=11 genera.
- Mean Rep1/Rep2 (approx.): K2B r≈0.578, MT≈0.538, NT≈0.412; filtered r closer (~0.57–0.62); CIs heavily overlap.
- Narrative already pushed to paper: no bold ranking; systematic errors (e.g. Roseburia / Clostridium); simulated in-DB ≠ real.

Files: `mock_d6331/*`. Live pipelines under `/nas2/gfm-classifier/mock_community/`.

---

## 4. Out-of-genome Track A (Experiment D)

- ART 150 bp from **new** NCBI genomes (same genera), contamination removed → clean N≈580K.
- Clean top-1: MT 250M **32.7%** (was 98.7%), MT 50M ~27%, NT-v2 ~26%.
- Interpretation: closed-set score is largely **genome memorization**; tokenization still helps a bit after the drop, but the paper’s 98.7% cannot be sold as novel-genome generalization.

Files: `track_a_newgenome/metrics_clean.json` (+ per-model sample metrics). Full preds on NAS `track_a/out/`.

---

## 5. Paper direction — suggested decision checklist

Use this when summarizing locally:

### Keep (strong, already in draft)

1. **Tokenization dominates** (13-mer vs 6-mer; train-fit / k-mer baselines showing “not pure lookup”).
2. **Pre-training helps at fixed 6-mer** (~+13 pp) but does not break the 6-mer ceiling.
3. **Dual evaluation** (read vs sample) + Bracken vs raw Kraken lesson.
4. **Honest limitations**: closed-set; mock is preliminary; need out-of-genome in main text or clear pointer.

### Update with this session’s results

5. **Kraken matched-reference (1,535)** → revise §6 / table / recommendations so primary comparison is full-pool, not GCF-censored 85K.
6. **Lead with out-of-genome + mock as the “reality check”**, not only closed-set 98.7%. Option:
   - **A (safer):** Frame 98.7% as closed-set / known-genome capacity; foreground Track A drop + mock as the deployment message.
   - **B (aggressive):** Make Track A a main figure; retitle contribution around “when GFMs beat / lose to Kraken”.
7. Recommendations: keep “in-database simulated → Kraken+Bracken”; “real/incomplete → no single winner”.

### Still open (blockers / P0)

8. Re-run **mock Kraken with 1535 DB** (optional consistency).
9. Soil / multi-community / Centrifuge (listed in paper §8).
10. Author metadata / Data DOI / cover letter still placeholders if not filled.

### Risks if unchanged

- Reviewer: “98.7% is k-mer lookup / same genomes” → Track A is the answer; must be prominent.
- Reviewer: “Kraken comparison unfair (missing GCF)” → Experiment B answers; update numbers.
- Reviewer: “mock n=11, overlapping CI” → already hedged; don’t overclaim ranking.

---

## 6. NAS paths (not in git)

| Artifact | Path |
|---|---|
| Kraken DB 1535 (~9 GB) | `/nas2/hierachical_test/kraken2_db_1535/` |
| Eval working dir | `/nas2/hierachical_test/kraken2_db_1535/eval_twcc100k/` |
| Genome FASTAs | `/media/user/CrucialX9/MetaTransformer_data/genomes/` |
| Mock full outs | `/nas2/gfm-classifier/mock_community/` |
| Track A preds | `/nas2/gfm-classifier/track_a/out/` |
| Old Kraken DB | `/nas2/hierachical_test/kraken2_db/` |
| Paper LaTeX | `/nas2/gfm-metagenomic-benchmark-paper/` |

Rebuild DB (if needed):

```bash
python scripts/build_kraken2_db_1535.py \
  --labels  /nas2/hierachical_test/data/val_100K/labels_100K_val.tsv \
  --genomes /media/user/CrucialX9/MetaTransformer_data/genomes \
  --db_dir  /nas2/hierachical_test/kraken2_db_1535 \
  --threads 16 --force_prepare
# then bracken-build -d ... -k 35 -l 150
```

---

## 7. File index

```
docs/paper_direction_review_2026_07/
  README.md                          ← this file
  kraken_matched_1535/               ← COMPARISON + JSON + reports + crosswalk
  mock_d6331/                        ← two-rep enhanced metrics
  track_a_newgenome/                 ← clean OOD metrics
  artifacts/                         ← kraken/NT prediction npz for re-plots
  scripts/                           ← snapshot of build/eval/mock scripts
scripts/build_kraken2_db_1535.py     ← also at repo root scripts/
scripts/eval_kraken1535_vs_neural.py
```

---

## 8. Suggested local summary outline

1. One paragraph: what the paper claims today vs what Experiments B–D force us to say.
2. Table: closed-set / matched-Kraken / OOD / mock — four columns, three methods.
3. Decision: Option A vs B in §5.
4. Edit list for paper repo (sections + figures).
5. Experiments still to run before submission.
