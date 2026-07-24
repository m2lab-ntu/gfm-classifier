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
`<T2_HOST>` = 你本機 `~/.ssh/config` 的 `Taiwania2` alias 展開後的 `ymj1123ntu@<IP>`(從 Nano4 跑要用完整 `user@IP`,Nano4 無此 alias)。**登入 IP 不寫進 repo**,見本機 ssh config 或指令記錄。
已驗證:Nano4 可直接連到 Taiwania-2 的 22 埠 → 可直接 rsync,不需經本機中轉。

```bash
# Job 1 (ov6mer) — 約 7GB:checkpoint + 17M 資料
rsync -avhP /work/ymj1123ntu/checkpoints/nt_token_genus_ov6mer_17M/last.pt \
      <T2_HOST>:<T2_PATH>/checkpoints/nt_token_genus_ov6mer_17M/
rsync -avhP /work/ymj1123ntu/data/balanced_species_17M/ \
      <T2_HOST>:<T2_PATH>/data/balanced_species_17M/
```
（`<T2_PATH>` = Taiwania-2 上的目標根目錄,預設沿用 `/work/ymj1123ntu`,請確認實際路徑。）
傳完後依下方 Job 對應的 slurm(改 `-A`/`-p` 為 Taiwania-2 值)提交。

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

## Job 4 — Random-init full-finetune NT-v2 @50M (pretraining ablation; HIGH review value, HIGH compute cost)
Reviewer-requested control to cleanly isolate the contribution of NT-v2's **pretrained
weights** from its **architecture**. Same 29-layer, ~500M-param NT-v2 architecture, same
50M balanced gut reads, same non-overlapping 6-mer tokenizer, same genus (120-class) task as
**v9** (LoRA on pretrained backbone, 67.1% RC-TTA) — the ONLY difference: backbone weights
are **randomly initialized** (not loaded from the pretrained checkpoint) and **all params
are trained** (no LoRA). This is a genuinely new regime for this project — v13/v14's
"scratch" naming means fresh LoRA/head on a *pretrained* backbone, NOT a random-init backbone
(confirmed 2026-07-20: the only backbone-construction path in `scripts/model.py` was always
`AutoModelForMaskedLM.from_pretrained`, no random-init option existed until now).

**Code change (already made, verified end-to-end on CPU, needs GPU-side training run):**
`scripts/model.py` — added a `random_init` flag to `TokenLevelGFMClassifier`/`create_model`.
When `True`, builds the same architecture via `AutoConfig.from_pretrained(...)` +
`AutoModelForMaskedLM.from_config(...)` instead of `.from_pretrained(...)` (random weights,
identical architecture). Raises `ValueError` if `random_init=True` and `use_lora=True`
together (LoRA on a random backbone is meaningless — no pretrained knowledge to adapt).
CPU smoke test passed: 29 layers, hidden_size 1024, 495,772,745 trainable params (100%),
forward pass produces correct `[batch, 120]` logits.

**Config ready:** `configs/nt_token_genus_randominit_50M.yaml` (`use_lora: false,
random_init: true`, data → `data/reads_50M.fa` + `labels_50M.tsv`).

**★ Hyperparameters are BEST-EFFORT ESTIMATES, not validated** — `backbone_lr: 1.0e-4`
(vs v9's 3.0e-5 — LoRA-appropriate tiny LR would badly undertrain a random-init backbone),
`num_epochs: 40` (vs v9's 30 — from-scratch convergence likely slower), `max_grad_norm: 1.0`
(tighter than v9's 5.0 — random-init deep transformers spike more early on),
`early_stopping_patience: 8`. **Watch the first few epochs' loss curve and adjust** — there
is no prior run of this exact regime to calibrate against.

**★ Memory — do NOT assume v9's profiled numbers apply.** v9's profiled peak
(`benchmark_results/train_speed_summary.csv`, 8.8GB) is for **LoRA** (~1-2% of params
trainable). Full-parameter fp32 optimizer state alone (weights + grad + Adam m + Adam v) for
~496M trainable params ≈ **7.9GB before activations**. Start `batch_size: 128` (already
conservative in the config) and watch for OOM before raising it — especially on V100
(16/32GB, no BF16; see Job 3's DNABERT-2 caveats for the same V100 constraints).

**Rough wall-time (compute-only reference, NOT validated for this regime):** using the
existing NT-v2 throughput profile (~1800 reads/sec/GPU, forward/backward FLOPs are similar
between LoRA and full fine-tune since it's the same architecture) — 8×H200 ≈ 58 min/epoch →
**~29–39 hours for 30–40 epochs on Nano4 H200s** (moot until Nano4 credits are restored).
On Taiwania-2 V100 (no BF16, ~1/3–1/5 the raw throughput of H200, likely smaller batch due
to memory): rough estimate **3–5× longer, i.e. multi-day**. This is a much heavier compute
ask than any other Job in this handoff — **consider whether it's worth waiting for Nano4
credits to be restored instead of running the full multi-day job on V100.**

**Transfer from Nano4 (if not already present on Taiwania-2 — check first, v9's OLD data
path `/work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M/` no longer exists on
Nano4, so don't assume Taiwania-2 has a stale copy either):**
| file | Nano4 path | size |
|---|---|---|
| 50M reads | `data/reads_50M.fa` | 9.6 GB |
| 50M labels | `data/labels_50M.tsv` | 3.9 GB |

**Run:** once data is confirmed present at `/work/ymj1123ntu/data/` on Taiwania-2, adapt a
DDP slurm script (use `slurm/run_nt_genus_v14_250M_ddp_nano4.sh` as a template — swap config
to `configs/nt_token_genus_randominit_50M.yaml`, output dir to
`checkpoints/nt_token_genus_randominit_50M`, adjust `-A`/`-p`/node-GPU count to Taiwania-2,
and note the index-prebuild step in that template is 250M-specific — not needed for 50M).

**Target output:** genus Top-1 (RC-TTA) on `clean_common` (99,742 reads), same protocol as
v9/v14/etc (`scripts/run_genus_rctta.py`), plus the training curve
(`training_history.csv` → same `replot_v9_curve.py`-style plot). Compare directly against
v9's 67.1% to get the clean pretraining-contribution delta the reviewer asked for.

## Already done (do NOT re-run)
7 genus settings (v9/v14/v15/gbal/sbal/MT-50M/MT-250M) + MT 6-mer s1/s6 @250M + MT species
@250M (val ~0.84, qualitative). Numbers in `THESIS_NUMBERS.md` (this repo's
`local_realworld_eval/` + `benchmark_results/` on Nano4).

## Priority call
- **Job 1 (ov6mer)** — status: stopped at ep15 on Nano4 (62.2%, see
  `benchmark_results/THESIS_NUMBERS.md` §2), sat untouched for ~2 weeks, then a Taiwania-2/V100
  config adaptation landed (batch/partition tuning, no results yet) — so it may now be
  actively resuming there. Check `checkpoints/nt_token_genus_ov6mer_17M/training_history.csv`
  on Taiwania-2 for current epoch before assuming either "done" or "abandoned".
- **Job 4 (random-init pretraining ablation)** — directly answers a **reviewer request**
  (unlike Jobs 1–3, which are internally-motivated confirmatory controls). Highest review
  value here, but also the **highest compute cost** (multi-day on V100, memory footprint
  untested) — weigh against waiting for Nano4 credits to restore (H200, ~29–39h estimate)
  before committing V100 wall-time.
- **Job 3 (DNABERT-2 @50M)** — cheap (~13 GB), one clean long job → worth it for the extra
  BPE-tokenizer data point (expected ~60%, below NT-v2 6-mer).
- **Job 2 (NT-v2 species @250M)** — 67 GB transfer for an expected-saturate result → **only if
  you want the symmetric species number**; otherwise skip.

The other high-value non-HPC track is **local real-world eval** (`local_realworld_eval/`).
Jobs 1–3 are confirmatory — they sharpen the tokenization table but
don't change the locked main conclusions.
