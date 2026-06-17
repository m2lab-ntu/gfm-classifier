# Nano4 — Status

**Last updated**: 2026-06-17 (rsync of 1535sp source complete)
**Host**: `25a-lgn04` (login node), compute nodes: `25a-hgpn*`
**Service**: Free 1-month trial (target: cover 6/2026 thesis-finalisation + paper-prep)

## Hardware

| Component | Detail |
|---|---|
| Login node GPU | NVIDIA H100 NVL, 95830 MiB |
| Compute node GPU | NVIDIA H200, 143771 MiB HBM3e |
| CUDA (available) | 12.6 / 13.0 via module |
| Driver | 580.65.06 |

## Slurm

| Field | Value |
|---|---|
| Account | MST114550 |
| Partition: dev | max 1h, H200 |
| Partition: normal | max 12h, min 64 GPUs, H200 |

## Environment

| Purpose | Path |
|---|---|
| Repo clone | `/work/ymj1123ntu/gfm-classifier` |
| Conda env | `gfm` (Python 3.11) |
| PyTorch | 2.5.1+cu121 |
| transformers | 4.46.3 |
| peft | 0.19.1 |
| Data path | `/work/ymj1123ntu/data/` |
| Checkpoint path | `/work/ymj1123ntu/checkpoints/` |
| HF cache | `/work/ymj1123ntu/.cache/huggingface` |

**Note**: `transformers==4.46.3` + `peft==0.19.1` are pinned. A key-compat fix was applied to the cached HF model (`modeling_esm.py`) so that `find_pruneable_heads_and_indices` is no longer imported from `transformers.pytorch_utils`.

## Migration checklist

- [x] SSH access verified (`ssh ymj1123ntu@nano4.nchc.org.tw`)
- [x] `conda` available, `gfm` env created (Python 3.11)
- [x] `git clone` this repo
- [x] Install Python deps (torch 2.5.1+cu121, transformers, peft, etc.)
- [x] Sync training data (`reads_50M.fa`, `labels_50M.tsv`) from Nano5 via `sync_from_nano5.sh`
- [x] Sync test data (`reads_100K.fa`, `labels_100K.tsv`, `in_db_mask.npy`)
- [x] Sync NT-v2 model checkpoints (`nt_token_species_v4_50M_best.pt`)
- [x] Upload full 1,535-species source (258.7M reads, 47GB) from local CrucialX9 to `/work/ymj1123ntu/data/labeled_multi_level_1535sp/reads.fa` — then subsample on Nano4
- [ ] Sync DNABERT-2 50M `last.pt` (to resume training)
- [ ] Sync MT models (from Taiwana-2 — for speed benchmark)
- [x] Verify SLURM commands — `slurm/sanity_check_nano4.sh` ready
- [x] Test one short job (eval on 100K test) to confirm pipeline works — **PASSED** (Job 71907)

## Data sync status

| File | Status | Size |
|---|---|---|
| `reads_100K.fa` | present | 19 MB |
| `labels_100K.tsv` | present | 7.2 MB |
| `labels_50M.tsv` | present | 3.7 GB |
| `nt_token_species_v4_50M_best.pt` | present | 1.9 GB |

## Sanity check

### Job 71907 (2026-06-03) — PASSED

| Field | Value |
|---|---|
| Slurm job | 71907 |
| Node | 25a-hgpn135 |
| GPU | NVIDIA H200, 143771 MiB |
| Start time | Wed Jun  3 00:35:46 CST 2026 |
| End time | Wed Jun  3 00:37:18 CST 2026 |
| Elapsed | ~1 min 32 s |
| batch_size | 1024 |
| num_reads | 100,000 |
| num_classes | 1,535 |
| read_accuracy | 0.17828 (17.83%) |
| TWCC baseline | 0.17827 (17.83%) |
| Diff from baseline | 0.00001 — MATCH |
| Verdict | PASSED — NT-Species sp_v4 matches TWCC baseline |

Results saved to: `/work/ymj1123ntu/gfm-classifier/results/sanity_check_nano4/`

## Planned tasks (when migration complete)

1. **DNABERT-2 50M resume** — ~36 hr H200, finish epochs 18-30
2. **Speed/memory unified benchmark** — all models on H200, batch=512, throughput/latency/peak GPU
3. **HMP mock community real-dataset inference** — NT-v2 sp_v4 on real metagenomic reads (~3 hr)
4. **(Optional) NT-v2 258M training, genus only** — ~4.5 days, if advisor wants extrapolation validation

## Notes

- nano5.nchc.org.tw requires MFA for SSH; direct `rsync` is blocked — use `sync_from_nano5.sh`
- H200 has 143 GB HBM3e (vs H100 NVL 95 GB on login node) — increase `eval_batch_size` accordingly
- Free 1-month trial — use aggressively, deprioritize TWCC budget
- **Setup date**: 2026-06-02
