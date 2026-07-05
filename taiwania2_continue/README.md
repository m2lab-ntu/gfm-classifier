# Taiwania-2 Continuation — Agent Handoff

**Why.** Nano4 free credits are exhausted (new submissions blocked). Remaining GPU
training moves to Taiwania-2 (TWCC). This repo (`git pull`) already carries the configs +
scripts + slurms; only the **1535sp data + one checkpoint** must be transferred from Nano4.

> Real-world / new-genome evaluation does **NOT** belong here — that's local-4090 (see
> `local_realworld_eval/`). This folder is only for the remaining **HPC training**.

## Adapt to Taiwania-2
The slurms in `slurm/` use Nano4's account/partition (`-A MST114550`, `-p 8gpus`/`dev`,
`--gres=gpu:8`). **Change `-A`, `-p`, node/gpu counts, and `--cpus-per-task` to Taiwania-2's**
(the Taiwania-2 agent knows the valid values). Paths assume `/work/ymj1123ntu/…`; keep or
remap consistently.

---

## 傳輸檔案(從 Nano4 執行)
⚠️ **本 repo 未記錄 Taiwania-2 登入位址**(Nano4 known_hosts 只有 `nano5.nchc.org.tw`)。
把 `<T2_HOST>` 換成你的 Taiwania-2 登入節點、`<T2_PATH>` 換成目標根目錄(下方假設沿用 `/work/ymj1123ntu`)。

```bash
# Job 1 (ov6mer) — 約 7GB:checkpoint + 17M 資料
rsync -avhP /work/ymj1123ntu/checkpoints/nt_token_genus_ov6mer_17M/last.pt \
      <T2_HOST>:<T2_PATH>/checkpoints/nt_token_genus_ov6mer_17M/
rsync -avhP /work/ymj1123ntu/data/balanced_species_17M/ \
      <T2_HOST>:<T2_PATH>/data/balanced_species_17M/
```
**若 Nano4 ↔ Taiwania-2 無法直接 SSH**(歷史上常見:Taiwania-2 未 mount TWCC/Nano4 的 /work):
先 `rsync` 到本機,再從本機上傳到 Taiwania-2(兩段 rsync)。

傳完後,依下方 Job 對應的 slurm(改 `-A`/`-p` 為 Taiwania-2 值)提交。

---

## Job 1 — ov6mer full convergence (LOW value / confirmatory; cheap)
NT-v2 + overlapping-6mer. On Nano4 it reached **ep15, val 61.3% and still rising** but is
tracking *below* non-overlap (v9 was 64.3% at ep14) → expected to plateau **≤67%** (confirms
the 6-mer ceiling; overlap doesn't rescue it). Finish it only if you want the converged number.

**Transfer from Nano4 (~7 GB):**
| file | Nano4 path | size |
|---|---|---|
| resume checkpoint | `checkpoints/nt_token_genus_ov6mer_17M/last.pt` | 2.0 GB |
| 17.6M data | `data/balanced_species_17M/{reads.fa, labels.tsv, reads.idx.npy}` | 4.7 GB + 0.28 GB idx |

**Run:** `sbatch slurm/run_nt_genus_ov6mer.sh` (config `configs/nt_token_genus_ov6mer_17M.yaml`;
auto-resumes from `last.pt` if present). Remove the Nano4 `-p 16gpus`/`--requeue` lines as needed.

## Job 2 — NT-v2 species @250M (MEDIUM value; HEAVY transfer)
Does the NT-v2 6-mer *species* task also saturate at 250M? (Expected yes, mirroring genus.)
Config ready: **`configs/nt_token_species_250M_balanced.yaml`** (task=species, 1535 classes,
`data/balanced_250M`). Prebuild the index first (see `slurm/run_prebuild_index_250M.sh` pattern),
then multi-GPU DDP like v14/v15 (`slurm/run_nt_genus_v14_250M_ddp_nano4.sh` as a template — swap
config → the species one, adjust account/partition).

**Transfer from Nano4 (~67 GB — heavy):**
| file | Nano4 path | size |
|---|---|---|
| 250M data | `data/balanced_250M/{reads_250M.fa, labels_250M.tsv, reads_250M.idx.npy}` | 67 GB |

*(Alternatively, Taiwania-2 can re-subsample 250M from the 1535sp source
`data/labeled_multi_level_1535sp/reads.fa` (47 GB) via `slurm/run_subsample_250M_balanced.sh` —
but note Taiwania-2's own HGR data is 2505sp, NOT the 1535sp used here, so the 1535sp source
must come from Nano4 either way.)*

## Job 3 — DNABERT-2 @50M clean finish (MEDIUM value; cheap transfer)
Another tokenizer data point: DNABERT-2 uses **BPE** (variable-length, ~4k vocab, not a
long near-unique-k-mer key) → expected to cap *below* NT-v2 6-mer, strengthening the
tokenization story. On Nano4 it reached **ep17, val_acc ~59.2% and plateauing** but never
finished cleanly.

**Root cause it "looped on Epoch 18" (already diagnosed — NOT a code bug):** Nano4's 4h
per-job walltime ≈ one epoch (~3.3h) + 50M-read load, a checkpoint-persistence **race** —
a job finished an epoch but was killed before writing `last.pt`, so the next job re-ran it.
Verified the epoch bookkeeping is correct (`last.pt.epoch` == completed-epoch count; resume
advances properly; `history` is reloaded on resume). **Fix is operational: run one long job.**

**Run:** `sbatch slurm/run_dnabert2_genus_50M.twcc.sh` — a **single 2-day job**, no resume
chain, resumes from the existing `last.pt` @ep17. Set `-A`/`-p`/`-t` to Taiwania-2 values.
Expect early-stop ~ep22-25, val ~60%. Then eval on `clean_common` like the other settings.

**Transfer from Nano4 (~13 GB):**
| file | Nano4 path | size |
|---|---|---|
| resume checkpoint | `checkpoints/dnabert2_token_genus_50M/{last.pt, best.pt}` | 0.5 GB ×2 |
| 50M data | `data/reads_50M.fa` + `data/labels_50M.tsv` | 9.0 + 3.7 GB |

*(The 50M data is shared with NT-v2 50M runs — Taiwania-2 may already have it from the
original thesis training; transfer only if absent.)*

## Already done (do NOT re-run)
7 genus settings (v9/v14/v15/gbal/sbal/MT-50M/MT-250M) + MT 6-mer s1/s6 @250M + MT species
@250M (val ~0.84, qualitative). Numbers in `THESIS_NUMBERS.md` (this repo's
`local_realworld_eval/` + `benchmark_results/` on Nano4).

## Priority call
- **Job 1 (ov6mer)** — cheap (~7 GB), nearly done → finish it.
- **Job 3 (DNABERT-2 @50M)** — cheap (~13 GB), one clean long job → worth it for the extra
  BPE-tokenizer data point (expected ~60%, below NT-v2 6-mer).
- **Job 2 (NT-v2 species @250M)** — 67 GB transfer for an expected-saturate result → **only if
  you want the symmetric species number**; otherwise skip.

The high-value next step remains the **local real-world eval** (`local_realworld_eval/`), not more
HPC training. All three jobs above are confirmatory — they sharpen the tokenization table but
don't change the locked main conclusions.
