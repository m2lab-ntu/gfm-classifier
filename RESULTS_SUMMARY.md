# GFM Classifier — consolidated results

All genus-level unless noted. "closed-set" = same reference genomes as training;
"new-genome/out-of-genome" = unseen accessions of the same genera; "real mock" =
real Illumina reads of a defined community.

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
| MT 6-mer 50M | 6-mer | **0.065** | 0.409 | 72.7% | 10 |

Note: detection sensitivity is coarse here (all hit the same 8/11 → 72.7%, incl. a false
Clostridium spike). Pearson r / Bray-Curtis are the discriminating metrics. MT 6-mer
collapses (r=0.065): from-scratch 6-mer embedding fails on real error profiles; NT-v2's
pretrained-backbone 6-mer (0.420) rescues it — a tokenization × pretraining finding.

## D. Kraken2 / Bracken baselines (100K balanced_50M test)

- Kraken2 classification: species **66.2%** all / **94.6%** classified · genus **69.5%** / **99.3%**
- Genus abundance: raw Kraken2 r=**0.845** (BC 0.177) → **Kraken2+Bracken r=0.997** (BC 0.060)
  (Bracken redistributes the 19,508 reads Kraken2 strands at the flat-taxonomy root.)

## E. Kim gut mock (DDBJ PRJDB10817, DRR466867) — IN PROGRESS

Higher-overlap real gut mock: **16/18 genera in-set (96.8% of DNA)**, only Methanobrevibacter
(archaeon) out-of-set — vs D6331's 11/17. 16 correlation points (not 11), even-ish
composition covering Faecalibacterium/Roseburia/Prevotella/Akkermansia/Blautia/Ruminococcus…
3M reads truncated to 150 bp. Running MT 13-mer / MT 6-mer / NT-v2; abundance eval pending.

## Pending
- Kim mock 3-model abundance eval
- Soil MT-5M / MT-50M (Taiwania2), soil NT-v2 5M (Taiwania2 handoff)
- CAMI2 human-gut (not started)
