# Nano4 — Status

**Last updated**: 2026-06-02
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
| Data path | `/work/ymj1123ntu/data/` |
| Checkpoint path | `/work/ymj1123ntu/checkpoints/` |
| HF cache | `/work/ymj1123ntu/.cache/huggingface` |

## Migration checklist

- [x] SSH access verified (`ssh ymj1123ntu@nano4.nchc.org.tw`)
- [x] `conda` available, `gfm` env created (Python 3.11)
- [x] `git clone` this repo
- [x] Install Python deps (torch 2.5.1+cu121, transformers, peft, etc.)
- [ ] Sync training data (`reads_50M.fa`, `labels_50M.tsv`) from Nano5 via `sync_from_nano5.sh`
- [ ] Sync test data (`reads_100K.fa`, `labels_100K.tsv`, `in_db_mask.npy`)
- [ ] Sync NT-v2 model checkpoints (`nt_token_species_v4_50M_best.pt`)
- [ ] Sync DNABERT-2 50M `last.pt` (to resume training)
- [ ] Sync MT models (from Taiwana-2 — for speed benchmark)
- [x] Verify SLURM commands — `slurm/sanity_check_nano4.sh` ready
- [ ] Test one short job (eval on 100K test) to confirm pipeline works

## Data sync status

| File | Status |
|---|---|
| `reads_100K.fa` | missing |
| `labels_100K.tsv` | missing |
| `labels_50M.tsv` | missing |
| `nt_token_species_v4_50M_best.pt` | missing |

## Sanity check

**Status**: pending (data sync required)

Slurm script: `slurm/sanity_check_nano4.sh`

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
