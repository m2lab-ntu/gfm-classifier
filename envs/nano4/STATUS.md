# Nano4 — Status

**Last updated**: 2026-06-02 (sanity check run x2, both FAILED — see below)
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
- [x] Sync training data (`reads_50M.fa`, `labels_50M.tsv`) from Nano5 via `sync_from_nano5.sh`
- [x] Sync test data (`reads_100K.fa`, `labels_100K.tsv`, `in_db_mask.npy`)
- [x] Sync NT-v2 model checkpoints (`nt_token_species_v4_50M_best.pt`)
- [ ] Sync DNABERT-2 50M `last.pt` (to resume training)
- [ ] Sync MT models (from Taiwana-2 — for speed benchmark)
- [x] Verify SLURM commands — `slurm/sanity_check_nano4.sh` ready
- [ ] Test one short job (eval on 100K test) to confirm pipeline works — **BLOCKED** (see Sanity check below, 2 attempts failed)

## Data sync status

| File | Status | Size |
|---|---|---|
| `reads_100K.fa` | present | 19 MB |
| `labels_100K.tsv` | present | 7.2 MB |
| `labels_50M.tsv` | present | 3.7 GB |
| `nt_token_species_v4_50M_best.pt` | present | 1.9 GB |

## Sanity check

### Attempt 2 — Job 69428 (2026-06-02)

**Status**: FAILED — `ImportError: cannot import name 'find_pruneable_heads_and_indices'`

| Field | Value |
|---|---|
| Slurm job | 69428 |
| Node | 25a-hgpn030 |
| GPU | NVIDIA H200, 143771 MiB |
| Start time | Tue Jun  2 11:15:57 CST 2026 |
| End time | Tue Jun  2 11:17:16 CST 2026 |
| Elapsed | ~1 min 20 s (crashed during model load) |
| batch_size | 1024 |
| read_accuracy | N/A — inference did not run |
| TWCC baseline | 17.83% (0.17827) |
| Diff from baseline | N/A |
| Verdict | BLOCKED — fix `transformers` version incompatibility |

**Error (stderr)**:
```
File ".../modeling_esm.py", line 37, in <module>
    from transformers.pytorch_utils import find_pruneable_heads_and_indices, prune_linear_layer
ImportError: cannot import name 'find_pruneable_heads_and_indices' from 'transformers.pytorch_utils'
```

**Root cause**: The HuggingFace model's custom `modeling_esm.py` (cached revision `06615c1`) imports `find_pruneable_heads_and_indices` from `transformers.pytorch_utils`, but this function was removed in `transformers >= 4.36`. The `gfm` conda env has a newer `transformers` version that dropped it.

**Fix needed** (pick one):
1. Downgrade `transformers` in the `gfm` env: `pip install transformers==4.35.2`
2. Or delete the cached model revision and pin to an older commit that uses a compatible `modeling_esm.py`.

---

### Attempt 1 — Job 69367 (2026-06-02)

**Status**: FAILED — `ModuleNotFoundError: No module named 'heads'`

| Field | Value |
|---|---|
| Slurm job | 69367 |
| Node | 25a-hgpn071 |
| GPU | NVIDIA H200, 143771 MiB |
| Start time | Tue Jun  2 10:54:37 CST 2026 |
| End time | Tue Jun  2 10:54:56 CST 2026 |
| Elapsed | ~19 s (crashed at import) |
| read_accuracy | N/A — inference did not run |
| TWCC baseline | 17.83% (0.17827) |
| Diff from baseline | N/A |
| Verdict | BLOCKED — fix import error first |

**Error (stderr)**:
```
File "/work/ymj1123ntu/gfm-classifier/scripts/run_nt_species_test100k.py", line 34, in <module>
    from model import create_model
  File "/work/ymj1123ntu/gfm-classifier/scripts/model.py", line 25, in <module>
    from heads import create_head
ModuleNotFoundError: No module named 'heads'
```

**Root cause**: `heads.py` is not on `sys.path` when the job runs on the compute node. The script imports `heads` as a bare module name but the working directory or `PYTHONPATH` does not include the `scripts/` directory.

**Fix applied**: Added `sys.path.insert(0, os.path.dirname(__file__))` at the top of `scripts/model.py` (fixed before attempt 2, but attempt 2 hit the `transformers` version issue).

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
