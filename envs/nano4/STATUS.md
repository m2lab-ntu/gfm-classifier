# Nano4 — Status

**Last updated**: 2026-06-17
**Host**: `nano4.nchc.org.tw`
**GPU**: H200
**Service**: Free 1-month trial (target: cover 6/2026 thesis-finalisation + paper-prep)

## Migration checklist

- [ ] SSH access verified (`ssh ymj1123ntu@nano4.nchc.org.tw`)
- [ ] `conda` available, create `gfm` env
- [ ] `git clone` this repo
- [ ] Install Python deps (torch, transformers, peft, etc.)
- [ ] Upload full 1,535-species source (258.7M reads, 47GB) from local CrucialX9 to `/work/ymj1123ntu/data/labeled_multi_level_1535sp/reads.fa` — then subsample on Nano4
- [ ] Sync existing `reads_50M.fa`, `labels_50M.tsv` from TWCC if needed for quick resume
- [ ] Sync test data (`reads_100K.fa`, `labels_100K.tsv`, `in_db_mask.npy`)
- [ ] Sync NT-v2 model checkpoints (best.pt for genus v9, species sp_v4)
- [ ] Sync DNABERT-2 50M `last.pt` (to resume training)
- [ ] Sync MT models (from Taiwana-2 — for speed benchmark)
- [ ] Verify SLURM commands (may differ from Nano5)
- [ ] Test one short job (eval on 100K test) to confirm pipeline works

## Paths (placeholder — fill in after first ssh)

| Purpose | Path |
|---|---|
| Repo clone | `/work/ymj1123ntu/gfm-classifier/` (TBD) |
| 1,535-sp source pool | `/work/ymj1123ntu/data/labeled_multi_level_1535sp/reads.fa` (uploading from CrucialX9) |
| HF cache | TBD |

## Planned tasks (when migration complete)

1. **DNABERT-2 50M resume** — ~36 hr H200, finish epochs 18-30
2. **Speed/memory unified benchmark** — all models on H200, batch=512, throughput/latency/peak GPU
3. **HMP mock community real-dataset inference** — NT-v2 sp_v4 on real metagenomic reads (~3 hr)
4. **(Optional) NT-v2 258M training, genus only** — ~4.5 days, if advisor wants extrapolation validation

## Notes

- H200 has 141 GB HBM3e (vs H100's 80 GB) → can fit larger batches; consider increasing eval_batch_size
- Free 1-month → use aggressively, deprioritize TWCC budget
