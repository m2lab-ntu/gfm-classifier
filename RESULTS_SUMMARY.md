# GFM Classifier — consolidated results

All genus-level unless noted. "closed-set" = same reference genomes as training;
"new-genome/out-of-genome" = unseen accessions of the same genera; "real mock" =
real Illumina reads of a defined community.

> **Paper direction review (2026-07):** full experiment pack + decision checklist →
> [`docs/paper_direction_review_2026_07/README.md`](docs/paper_direction_review_2026_07/README.md)
> (matched-reference Kraken 1,535, D6331 two-rep mock, Track A OOD).

## A. Closed-set Top-1 (same-genome)

| Model | Gut (120 genera) | Soil (309 genera) |
|---|---|---|
| MT 13-mer (full data) | 98.7% (250M) · 87.5% (50M) | **0.830** (best_genus_model, embed64, test_final) |
| MT 6-mer | 48.9% (50M) · 50.6% (250M) | — |
| NT-v2 v9 + LoRA | 67.1% (RC-TTA) | NT-v2 1M **0.294** · 5M **0.320** (test_final) |

Soil MT-5M(embed64)/MT-50M training on Taiwania2; NT-v2 5M val 0.308 → test_final 0.320.

## B. Out-of-genome generalization (Track A, gut, contamination-cleaned)

580,000 reads / 116 genera (3 training-overlap genomes removed).

| Model | closed-set | new-genome | drop |
|---|---|---|---|
| MT 13-mer 250M | 98.7% | **32.67%** | −66.0 pt |
| MT 13-mer 50M | 87.5% | **27.05%** | −60.5 pt |
| NT-v2 v9 | 67.1% | **25.81%** | −41.3 pt |

Sample-level abundance from this uniform pool (r≈0) is a sampling artefact — not reported.

## C. Real mock-community abundance — ZymoBIOMICS D6331 (gut)

SRR33710519, 3M reads (~135 bp). In-set = 11/17 genera (81.5% of DNA); 18.5% out-of-set ceiling.

| Method | Tokenization | Pearson r | Bray-Curtis | detection @≥1% | FP genera |
|---|---|---|---|---|---|
| Kraken2 + Bracken | — | **0.580** | 0.437 | 54.5% | 4 |
| MT 13-mer 250M | 13-mer | **0.545** | 0.344 | 72.7% | 7 |
| NT-v2 + LoRA | 6-mer | **0.420** | 0.376 | 72.7% | 7 |
| MT 6-mer 50M | 6-mer | **0.065**◆ | 0.409 | 72.7% | 10 |

◆ MT 6-mer single-rep; 2-rep mean = 0.057 — an artefact (see note). **Report the CLEAN table below instead.**

### C-clean. RECOMMENDED for the paper — restricted to expected ≥1% (9 genera)

Excludes the two trace in-set genera (Clostridium 0.0001%, Enterococcus 0.001%) that make the
11-genus r numerically unstable. This is the metric the paper already argues for
("we do not rank by r"; "restricting to ≥1% … tighter band"). `d6331_clean_ge1pct_metrics.json`.

| Method | Pearson r | Bray-Curtis | note |
|---|---|---|---|
| Kraken2 + Bracken | **0.620** | 0.419 | rep1 |
| MT 13-mer 250M | **0.610** | 0.312 | rep1 |
| NT-v2 6-mer | **0.569** | 0.334 | rep1 |
| MT 6-mer 50M | **0.500** | 0.338 | 2-rep mean (rep1 0.497 / rep2 0.502) |

All 0.50–0.62 → **no clear winner** (matches abstract). MT 6-mer is NOT collapsed once the
trace-genus artefact is removed. (rep2 = SRR33710518; MT6 confirmed rep-consistent.)

Note: detection sensitivity is coarse in the 11-genus table (all hit the same 8/11 → 72.7%). ⚠️ The MT 6-mer
r=0.065 is LARGELY A METRIC ARTEFACT — D6331's in-set includes Clostridium (trace, 0.0001%),
and all three models dump ~20–30% of reads into Clostridium (a shared false attractor); on
D6331 that spike lands *inside* the in-set correlation and tanks r. On the Kim mock (§E),
where Clostridium is NOT in the composition, the same spike becomes a false positive and MT
6-mer's r is normal (0.526). **Do not use D6331's 6-mer collapse as evidence that 13-mer > 6-mer.**

## D. Kraken2 / Bracken baselines (100K balanced_50M / TWCC test)

### D1. Old custom DB (1,316 genomes; 219 GCF missing)

- Kraken2 classification: species **66.2%** all / **94.6%** classified
- Genus abundance (full 100K report): raw r=**0.845** (BC 0.177) → **Kraken2+Bracken r=0.997** (BC 0.060)
- Paper table used **coverage-matched 85,819** reads: genus raw **77.7%**, r=**0.823**; Bracken r=**0.997**

### D2. Matched-reference DB (1,535 genomes; CrucialX9 FASTAs) — 2026-07

DB: `/nas2/hierachical_test/kraken2_db_1535/` · metrics: `docs/paper_direction_review_2026_07/kraken_matched_1535/`

| Setting | Kraken raw genus acc | raw r | Bracken r |
|---|---:|---:|---:|
| Full 100K (fair) | **80.0%** | 0.832 | **1.000** (BC 0.004) |
| Legacy 85,819 subset | 77.2% | 0.824 | (full-report Bracken only) |

Species top-1 all: **79.5%** (was 66.2%). Vs neural on full 100K: MT 13-mer **94.3%**, NT-v2 RC-TTA **67.4%**, MT 6-mer **48.8%**.

## E. Kim gut mock (DDBJ PRJDB10817, DRR466867) — real, high-overlap

**16/18 genera in-set (96.8% of DNA)**, only Methanobrevibacter (archaeon) out — vs D6331's
11/17. 16 correlation points, cell-even composition (read-expected ∝ genome length).
3M reads @150 bp (MT 13-mer on 1.5M due to RAM).

| Model | Tokenization | Pearson r | Bray-Curtis | detection @≥1% | FP genera |
|---|---|---|---|---|---|
| MT 6-mer 50M | 6-mer | **0.526** | 0.370 | 87.5% (14/16) | 5 |
| NT-v2 + LoRA | 6-mer | **0.458** | **0.308** | 87.5% (14/16) | 6 |
| MT 13-mer 250M | 13-mer | **0.347** | 0.360 | 75.0% (12/16) | 4 |

**Ranking FLIPS vs D6331** (there MT13>NT>MT6; here MT6>NT>MT13) → on real gut abundance the
three are **comparable and all mediocre (r 0.35–0.53)**; tokenization does not cleanly separate
them. Shared failure modes on both mocks: (a) ~20–30% of reads dumped into a false **Clostridium**
attractor, (b) severe under-prediction of dominant genera (Parabacteroides, Anaerostipes,
Akkermansia, Roseburia, Eubacterium, Faecalibacterium). The dramatic D6331 6-mer collapse was
a metric artefact (see §C). Deliverables: `mock_community_eval/kim/`.

## Pending
- Soil MT-5M / MT-50M (Taiwania2), soil NT-v2 5M (Taiwania2 handoff)
- CAMI2 human-gut — assessed as LOW marginal value (simulated; low in-set coverage vs 120 genera);
  skip unless a reviewer asks. A 3rd *real* mock (NIBSC/Tourlousse) would be better if more
  robustness is wanted.
