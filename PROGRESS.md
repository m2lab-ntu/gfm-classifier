# Project Progress

**Last updated**: 2026-06-01

## Thesis state

- **Page count**: 139 (compiled `main.pdf` in separate thesis repo)
- **Core findings**: 4 contributions complete
  1. Tokenisation > pre-training (controlled ablation +18/+20/+32 pp)
  2. Species-level noise floor + 40–50% utility threshold
  3. Router quality threshold (monotonic across 3 routers)
  4. Same-DB Kraken2 + fair-restricted comparison (in-DB Table 4.30)

## Completed experiments

### NT-v2 (Nucleotide Transformer v2 + LoRA)
- Genus v9 50M: 64.45% (66.05% RC TTA) ✓
- Species sp_v4 50M: 17.55% read, 0.135 Pearson r ✓
- Per-genus pipeline (predicted/oracle): 14.7% / 27.6% ✓
- Backbone ablations (shallow no-PT, subgenus K-means) ✓

### MetaTransformer (from-scratch)
- MT 13-mer flat species @ 50M: 53.7% (aligned, 100K test) ✓
- MT 6-mer flat / hier @ 50M: 9.0% / 6.4% ✓
- MT 13-mer / 6-mer genus @ 50M: 94.25% / 48.76% ✓
- **MT 13-mer hier species checkpoint corrupted** (Taiwana-2, val_loss=9.29 @ batch 10K) ✗

### DNABERT-1 / DNABERT-2
- 5M (LoRA, RC TTA): 61.78% / 58.88% ✓
- 50M: DNABERT-2 17/30 epochs (TIMEOUT); DNABERT-1 4/30 epochs (very slow, 11.7 hr/epoch)

### Kraken2 baseline (custom DB, 1316/1535 species)
- Species 100K test: 66.23% (in-DB 77.18%) ✓
- Genus 100K test: 69.50% (in-DB 77.68%) ✓
- OOD (219 missing species, deployment coverage gap): 0% ✓

## Major findings

1. **Species/genus inversion** (in-DB fair-restricted): Kraken2 dominates species (77 vs MT 52), but MT 13-mer dominates genus (95 vs Kraken2 78). Driven by 30% commit-rate × task cardinality.
2. **OOD framing corrected**: The 14,181 reads from 219 GCF species are in-distribution for neural models (training data includes them). Asymmetry is deployment-coverage, not generalisation OOD.

## Outstanding / blocked

| Task | Where | Status |
|---|---|---|
| DNABERT-2 50M resubmit | TWCC | Blocked — iService budget -802.5 |
| Speed/memory unified benchmark | TWCC (needs MT migration) | Blocked — budget + MT scp |
| Per-genus 13-mer Exp F | Taiwana-2 | Running (60/81 genera done) |
| MT 13-mer hier retraining | Taiwana-2 | Pending advisor decision |
| HMP real-dataset validation | TBD | Pending — paper submission prep |
| Migration to Nano4 (H200, free 1 month) | Nano4 | Planning phase |

## Active decisions (advisor pending)

- Q1: TWCC budget top-up vs accept DNABERT-2 17/30 partial?
- Q2: DNABERT-1 50M cancel (confirmed recommendation)?
- Q3: MT 13-mer hier retraining on Taiwana-2 (V100, ~1-2 days)?

## Timeline (target)

- **6/15**: Thesis defense
- **6/30**: Thesis final version
- **7-8/2026**: Rewrite Chapter 4 → Bioinformatics journal manuscript
- **8/31/2026**: Submission target
- **2027 Q1**: First review / revision
