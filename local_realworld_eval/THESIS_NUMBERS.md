# Thesis Numbers — single-page reference (2026-06-26)

All numbers verified this session unless marked. **Metric note:** NT-v2 settings = RC-TTA per-read; MT settings = forward-only Top-1 (extract_mt_predictions, no RC-TTA). Genus = 120 classes.
✅ = locked  ⏳ = pending

---

## 1. Genus per-read accuracy, by evaluation pool (both strict train-disjoint)
| setting | train | **clean_common** (natural, friendly) | **leftover** (strict, harder) |
|---|---|---|---|
| MT 13-mer 250M | 250M | ✅ **98.7%** | ✅ 98.5% |
| MT 13-mer 50M | 50M | ✅ 87.5% | ✅ 83.0% |
| NT-v2 250M warm (v15) | 250M | ✅ 67.3% | ✅ 58.3% |
| NT-v2 50M (v9) | 50M | ✅ 67.1% | ✅ 58.1% |
| NT-v2 250M scratch (v14) | 250M | ✅ 64.8% | ✅ 55.5% |
| NT-v2 17.6M species-bal (sbal) | 17.6M | ✅ 60.4% | ✅ 50.2% |
| NT-v2 17.6M genus-bal (gbal) | 17.6M | ✅ 37.2% | ✅ 35.9% |

clean_common = Taiwania2 100K val, 99,742 reads, disjoint from 50M∪250M. Report clean_common as primary; leftover as conservative lower bound.

## 2. Tokenization × scaling (Top-1, from-scratch unless noted)  ← core table
| tokenizer | model | 50M | 250M |
|---|---|---|---|
| **13-mer overlap (s1)** | MT | ✅ 87.42% (thesis) | ✅ **98.7%** (scales!) |
| 12-mer overlap (s1) | MT | ✅ 78.83% (thesis) | — |
| 6-mer overlap (s1) | MT | ✅ 48.87% (thesis) | ✅ 50.6% |
| 6-mer non-overlap (s6) | MT | ✅ 47.00% (thesis) | ✅ 45.0% |
| 6-mer non-overlap | NT-v2 (pretrained) | ✅ 67.07% | ✅ 67.3% (saturates) |
| 6-mer overlap | NT-v2 (pretrained) | — | ⏳ job 152862 |
**Takeaway:** 6-mer caps 45–67% (NT-v2 67% = best, via pretraining); only 13-mer reaches 87→98.7%. Tokenization governs both **ceiling** and **scalability**.

## 3. Train-fit ceiling (strongest tokenization evidence) ✅
| model | train_acc | val_acc |
|---|---|---|
| NT-v2 250M scratch (v14) | **63.2%** | 64.1% |
| NT-v2 250M warm (v15) | **65.8%** | 66.6% |
| MT 13-mer 250M | **98.9%** | 97.5% |
6-mer can't even *fit* training past ~66% (train≈val); 13-mer fits to 99%. → bottleneck is input representation, not capacity/data/optimization/generalization.

## 4. Data scaling — NT-v2 6-mer (RC-TTA) ✅
500K **55.29%** → 5M **63.05%** → 50M **67.07%** → 250M **67.29%**. Saturates at 50M.
Underlying **unique** reads: 50M=17.8M, 250M=41.9M (≈ source ceiling 42.6M). x-axis should say "training reads (incl. repeats)".

## 5. Pre-training advantage ✅
+13.19 pp (NT-v2 67.07 vs shallow 1-layer random 53.88, RC-TTA) ·  +19.29 pp (NT-v2 66.29 vs MT 6-mer scratch 47.00, forward).

## 6. Sample-level abundance — Pearson r (friendly pool clean_common, 9×10K) ✅
| setting | Pearson r | Bray-Curtis |
|---|---|---|
| MT 13-mer 250M | 1.000 | 0.005 |
| MT 13-mer 50M | 0.999 | 0.032 |
| NT-v2 v9 / v15 / v14 / sbal | 0.993 | 0.098–0.139 |
| NT-v2 gbal (genus-bal) | 0.862 | 0.420 |
**Pool-dependent**: leftover pool gives NT-v2 0.928, MT-50M 0.990, gbal 0.625. Don't report a single 0.993. Each setting has a scatter at `sample_common_eval/<tag>/abundance_scatter.png`; comparison `sample_common_eval/cross_setting_comparison.png`. v9 0.993 reproduces the prior thesis value.

## 7. Genus-balance ablation (17.6M, same data, only balance axis) ✅
| | per-read (clean_common) | per-genus flat | sample-level r |
|---|---|---|---|
| species-bal (sbal) | 60.4% | 33.1% | 0.993 |
| genus-bal (gbal) | 37.2% | 43.5% | 0.862 |
Genus-balancing lifts macro/flat (+10pp) but tanks per-read (−23pp) and real abundance (r 0.993→0.862). The 42–43% flat ceiling holds even when balanced → mostly intrinsic 150bp difficulty, not a fixable imbalance artifact. Counterproductive for real metagenomics.

## 8. Read duplication structure ✅
source reads.fa 258.67M total / **42.64M unique** (6.07×) · balanced_250M 41.94M unique · reads_50M 17.76M unique. (Source-level duplication, not just balancing.)

## 9. Efficiency ✅ + correction
MT 13-mer "~5M params" is misleading: **embedding alone = 2.1B** (33.5M-row 13-mer vocab × 64). Speed: `benchmark_results/` (speed_benchmark / compute_speed).

---

## Honest caveats to state in-text
- MT 98.7% / r=1.000 = **closed-set near-complete 13-mer coverage of the 1,535 known genomes** (near-lookup), NOT novel-genome generalization.
- sample-level r is pool-dependent (0.928–0.993); report as a range.
- NT-v2 numbers are RC-TTA, MT numbers are forward-only (asymmetry; RC-TTA ≈ +0.7pp for NT).

## ⏳ Pending
- NT-v2 overlap-6mer (job 152862, 8gpus, ETA ~6/27): the 4th cell in §2; expected ~67% or lower (OOD).
- Then: final 4-way 6-mer table + MT-250M added to sample-level (already in §1/§6).
