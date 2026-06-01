# Model Checkpoints Manifest

## NT-v2 + LoRA (genus)

| Model | best.pt size | Location | Performance |
|---|---|---|---|
| NT-Genus v8 (5M) | ~2 GB | TWCC: `results/nt_token_genus_lora_v8_5M/best.pt` | 63.05% RC TTA |
| **NT-Genus v9 (50M)** | ~2 GB | TWCC: `results/nt_token_genus_lora_v9_50M/best.pt` | **66.05% RC TTA** |
| NT-Genus v11 shallow (50M no PT) | ~30 MB | TWCC: `results/nt_token_genus_v11_shallow/best.pt` | 53.88% RC TTA |

## NT-v2 + LoRA (species)

| Model | Location | Performance |
|---|---|---|
| **NT-Species sp_v4 (50M)** | TWCC: `results/nt_token_species_v4_50M/best.pt` | **17.55% read, 0.135 Pearson r** |
| Per-genus species classifiers (81 genera) | TBD — was on Taiwana-2 for Exp F | Oracle 27.62%, predicted 14.26% |

## DNABERT

| Model | Location | Performance |
|---|---|---|
| DNABERT-1 (5M, LoRA) | TWCC: `results/dnabert_token_genus_5M/best.pt` | 61.78% RC TTA |
| DNABERT-2 (5M, LoRA) | TWCC: `results/dnabert2_token_genus_5M/best.pt` | 58.88% RC TTA |
| DNABERT-1 (50M, partial) | TWCC: `results/dnabert_token_genus_50M/last.pt` | 4/30 epochs, 59.50% — recommended cancel |
| DNABERT-2 (50M, partial) | TWCC: `results/dnabert2_token_genus_50M/last.pt` | 17/30 epochs, 59.22% — can resume |

## MetaTransformer (Taiwana-2)

| Model | Location (Taiwana-2) | Performance |
|---|---|---|
| MT 13-mer flat species | `/work/ymj1123ntu/MetaTransformer_experiments/mt_13mer_species_flat/` | 53.7% |
| MT 13-mer hier species | (same path family) — **checkpoint corrupted** | N/A |
| MT 6-mer flat species | `mt_6mer_species_flat/` | 9.0% |
| MT 6-mer hier species | `mt_6mer_hierarchical/` | 6.4% |
| MT 13-mer genus | `mt_13mer_genus_50M/` | 94.25% |
| MT 6-mer genus | `mt_6mer_genus_s1/` | 48.76% |

## Sync to Nano4

Recommended priority (only sync what's needed):

```bash
# P0: NT-v2 50M models (for eval / further inference)
mkdir -p /work/ymj1123ntu/checkpoints
rsync -avhP \
    ymj1123ntu@nano5.nchc.org.tw:/work/ymj1123ntu/token_level_gfm_classifier/results/nt_token_genus_lora_v9_50M/best.pt \
    ymj1123ntu@nano5.nchc.org.tw:/work/ymj1123ntu/token_level_gfm_classifier/results/nt_token_species_v4_50M/best.pt \
    /work/ymj1123ntu/checkpoints/

# P1: DNABERT-2 50M last.pt (for resume)
rsync -avhP \
    ymj1123ntu@nano5.nchc.org.tw:/work/ymj1123ntu/token_level_gfm_classifier/results/dnabert2_token_genus_50M/last.pt \
    /work/ymj1123ntu/checkpoints/dnabert2_50M_last.pt

# P2: MT models (for speed benchmark)
# First scp from Taiwana-2 → TWCC, then TWCC → Nano4
```
