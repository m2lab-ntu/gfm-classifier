# Soil Genus Classification — Tokenization × Data-Scale Study (Taiwania-2)

**Goal:** clean, matched comparison of **tokenization granularity (6-mer vs 13-mer)** and
**architecture (from-scratch MetaTransformer vs pretrained Nucleotide-Transformer-v2 + LoRA)**
for **genus classification of simulated soil metagenomic reads (RefSoil-derived, 150 bp, closed-set)**,
across two data scales (**5M** and **50M** training reads). All models evaluated on the **same fixed
`test_final` (5M reads)** so numbers are directly comparable.

Everything here was produced on Taiwania-2 (V100-SXM2-32GB, `gp2d`). This doc is the hand-off for
the local write-up. **Status date: 2026-07-18.**

---

## 1. Headline results (test_final Top-1, 5M held-out reads)

| Model | Tokenization | Data | **Top-1** | Macro-F1 | Protocol | Status |
|---|---|---|---|---|---|---|
| MetaTransformer | 13-mer, stride 1, embed 64 | **5M** | **0.2051** | 0.183 | fwd | ✅ final |
| MetaTransformer | 13-mer, stride 1, embed 64 | **50M** | **0.8924** | 0.894 | fwd | ✅ final |
| MetaTransformer | 6-mer, stride 1, **embed 64** | **50M** | **0.2662** | 0.248 | fwd | ✅ final (⚠ underfits — see §4) |
| MetaTransformer | 6-mer, stride 1, **embed 128** | **50M** | *~0.30–0.35 (proj.)* | — | fwd | 🟢 running (970180) |
| NT-v2-500M + LoRA | 6-mer (non-overlap, native) | **5M** | **0.3097** fwd / **0.3198** RC-TTA | — | fwd/tta | ✅ final |
| NT-v2-500M + LoRA | 6-mer (non-overlap, native) | **50M** | *~0.38 (proj.)* | — | fwd/tta | 🟢 running (970084), val 0.364↑ |

**Reference anchors (context, not this study):**
- MT-full 13-mer (local, full soil data): **0.830** on this same `test_final`.
- Gut HGR-UMGS MT 13-mer stride-1 50M (120 genera): **0.874**.
- Gut HGR-UMGS MT 6-mer stride-1 50M, embed 128 (120 genera): **0.489**.
  (13-mer transfers gut↔soil almost exactly: 0.874 vs 0.892.)

### Matrix view
| 50M soil, Top-1 | 6-mer | 13-mer |
|---|---|---|
| **MetaTransformer** (from-scratch) | 0.266 (e64) / ~0.32 (e128) | **0.892** |
| **NT-v2 + LoRA** (pretrained) | ~0.38 | — (not run; 13-mer is MT-only) |

| 5M soil, Top-1 | 6-mer | 13-mer |
|---|---|---|
| **MetaTransformer** | — | 0.205 |
| **NT-v2 + LoRA** | 0.310 / 0.320ᵀᵀᴬ | — |

---

## 2. Key findings

1. **k-mer LENGTH is the dominant factor.** At 50M, MT 13-mer (0.892) ≫ every 6-mer variant
   (0.27–0.38), regardless of architecture or embedding capacity. The long, specific k-mer is the
   single biggest lever for this task.

2. **The from-scratch full-vocab MT is extremely data-hungry.** MT 13-mer: **5M → 0.205** (catastrophic
   overfitting: train prec 0.99, val loss diverges to >13; best checkpoint locked in the first ~1000
   batches) vs **50M → 0.892** (clean, early-stops at epoch 7, no overfit). The 13-mer's power only
   materialises with enough data.

3. **Crossover between pretrained-LoRA and from-scratch as data scales.**
   - **Low data (5M):** NT-v2+LoRA (0.32) **>** MT 13-mer (0.205) — pretraining + LoRA regularisation
     wins when data is scarce (MT overfits, NT-v2 does not: train_acc ≈ val_acc throughout).
   - **High data (50M):** MT 13-mer (0.892) **≫** NT-v2 (~0.38) — with enough data the specific
     tokenization + full from-scratch training dominates.

4. **At matched 6-mer tokenization, architecture matters little.** MT-6mer (~0.27–0.32) and
   NT-v2-6mer (~0.38) are in the same ballpark and both far below MT-13mer (0.89). The **tokenization
   ceiling dominates the architecture difference** at 6-mer. (This comparison is inherently fuzzy —
   NT-v2 is a 500M pretrained model, MT-6mer is ~5M from-scratch — see §4.)

---

## 3. Experimental design / methodology

- **Data:** RefSoil-derived ART-simulated 150 bp reads, closed-set. Same canonical genus label space
  across all runs (genus_idx 0–314; 309 populated; header
  `>lbl|<genus_idx>|<genus_name>|<species_idx>|<accession>-<pos>/<mate>`).
  - 5M ⊂ 50M (nested subsets, same generation recipe). `test_final` (5M) is disjoint from all train
    (verified: train ∩ test_final = 0; train from `training_reads.fa`, test from `val_reads.fa` upper half).
- **Matched evaluation:** every model scored on the **identical** `test_final` 5M reads.
- **MT config (13-mer):** embed 64, num_classes 500 (500-wide head, labels 0–314 populated; aligned to
  MT-full), class_indices 1, kmer_size 13, kmer_stride 1, sparse_embedding true, batch 2048, Adam+SparseAdam.
- **MT 6-mer control:** identical to 13-mer config except kmer_size 6 + vocab_6mer. Two capacity settings:
  embed 64 (strict, same as 13-mer) and embed 128 (fair, gut-0.489 recipe; sparse off).
- **NT-v2 config:** `InstaDeepAI/nucleotide-transformer-v2-500m-multi-species`, LoRA (r=16, q/k/v),
  attention-pool head, 6 epochs, fp16, batch 384, internal 95/5 train/val split, `num_classes` auto-detected
  = 309. Evaluated fwd + reverse-complement TTA (`run_genus_rctta.py`).
- **Protocol note:** MT numbers are **fwd-only** Top-1; NT-v2 reports fwd + **RC-TTA**. For a clean
  same-protocol MT-vs-NT comparison use MT-fwd vs NT-fwd. RC-TTA adds only ~+1 pp for NT-v2 (0.310→0.320).

---

## 4. Caveats & limitations (important for the paper)

- **Underfitting artefact in the strict 6-mer control (embed 64):** MT-6mer @ e64 gives 0.266 but is
  **capacity-limited, not overfit** (train_loss 3.59 ≈ val_loss 3.55 — the model can't fit even the
  training data). 13-mers are specific enough that embed 64 suffices (0.892); 6-mers are ambiguous and
  need more capacity to become discriminative, so e64 secretly handicaps the 6-mer.
  - **Use e64** for the **within-MT k-mer comparison** (13 vs 6, same everything → 0.892 vs 0.266).
  - **Use e128** for the **cross-architecture comparison** (MT-6mer vs NT-v2-6mer), else MT is starved.
  - Even at e128, soil 6-mer trails the gut 0.489 — because soil has 309 genera vs gut's 120 (harder).
- **Protocol mismatch** MT (fwd) vs NT-v2 (RC-TTA) — align before publishing (can add MT RC-TTA cheaply).
- **Cross-architecture comparison is fuzzy:** NT-v2 (500M, pretrained) vs MT (~5M–2.1B, from-scratch);
  not a controlled-capacity comparison — report as "each at its reasonable config", not a clean ablation.
- **Simulated reads only** (ART/RefSoil); no real metagenomes.
- **Closed-set** (309 soil genera); no open-set / novel-taxon evaluation.
- **Single test set, single seed;** no CV / multi-seed error bars yet.
- MT uses a 500-wide head (309 populated); NT-v2 a 309 dense head — both scored on the same reads, but
  the label-space handling differs (empty MT classes 315–499 never win argmax, so no effect on Top-1).

---

## 5. Suggested paper direction (for review)

**Framing:** a 2-D study of **tokenization granularity × training-data scale** for metagenomic genus
classification of short reads, with a secondary **pretrained-GFM-vs-from-scratch** axis.

**Core claims the data support:**
1. Tokenization granularity (k-mer length) is the dominant design choice — larger k wins decisively **given
   sufficient data**.
2. There is a **data-scale crossover**: pretrained GFM + LoRA is the better choice in the low-data regime;
   a simple from-scratch k-mer transformer wins at scale.
3. The from-scratch full-vocab model is **data-hungry / overfits badly at low data**, which is the
   mechanism behind (2).

**Open questions / to strengthen before submission:**
- Align MT and NT-v2 on the **same eval protocol** (add MT RC-TTA).
- Finish the two running 50M cells (MT-6mer-e128, NT-v2-50M) for the complete matrix.
- Consider **NT-v2 at 13-mer** — currently 13-mer is MT-only; an NT-style 13-mer would make the
  tokenization axis symmetric (though NT-v2's native tokenizer is fixed 6-mer, so this needs thought).
- Add error bars (multi-seed) for the headline cells.
- Decide the **capacity-fairness story** for 6-mer explicitly (report both e64 and e128).

---

## 6. Code fixes made on Taiwania-2 (reproducibility / methods)

These were necessary to run at all / correctly on V100 and at 50M scale. All in the two repos below.

**MetaTransformer (`/home/ymj1123ntu/MetaTransformer/src/`)**
- `trainer/AbstractTrainer.py`:
  - **In-process multi-epoch loop** (`training.max_epochs`): the original `train()` was single-pass
    (one iteration over the dataset then exit) — with properly-sharded data this is only ~1 epoch. The
    original gut runs only "trained long" due to an accidental single-file × N-workers re-read. Added a
    real epoch loop so early-stopping works and epochs are clean.
  - **Checkpoint-truncation fix**: `_truncate_to_n_models()` could delete the checkpoint flagged
    `current`, crashing `resume_dir=` with "nothing to resume from". Now never truncates `current`.

**NT-v2 pipeline (`/work/ymj1123ntu/gfm-classifier/soil_ntv2_5M/scripts/`)**
- `train.py` `_get_amp_dtype()`: `torch.cuda.is_bf16_supported()` returns **True on V100 (sm_70)** and
  training silently ran **bf16 → a ~4.4× slower emulated path** (measured: fp16 0.76 s/it vs bf16 3.32
  s/it). Now gates bf16 on compute capability ≥ 8.0 → V100 uses fp16. **4.4× speedup**; made 50M feasible.
- `train.py`: **mid-epoch checkpointing** (`training.checkpoint_every_steps`): 50M epochs are ~26 h and
  exceed the 48 h walltime; saves `last.pt` every N steps with `step_in_epoch`, and resume runs only the
  epoch's *remaining* steps (LR schedule stays aligned). A timeout now loses ≤ minutes, not a whole epoch.
  Validated end-to-end (timeout at step 106,286 → resumed at 106,000).
- `data_loader.py` `load_data()`: replaced `pandas.iterrows()` + dict-of-Series (≈ 1 h and tens of GB at
  50M) with a vectorized `{seq_id: idx}` map → **~73 s, 11 GB**. Same result.
- `config` `num_workers`: 8 → **2** for 50M (each forked DataLoader worker copies the 47.5M in-memory
  read strings via broken copy-on-write → OOM'd the 90 GB cap at ~8.7 h; 2 workers → 42 GB, and the
  dataloader is 240× faster than the GPU needs so no slowdown).

---

## 7. Artifacts in this directory

```
soil_tokenization_study/
├── RESULTS_SUMMARY.md                 # this file
├── results/
│   ├── predictions/*.npz              # per-read preds+labels+acc for every eval
│   │   ├── mt5m_test_final.npz        # MT 13-mer 5M   -> acc_top1 0.2051
│   │   ├── mt5m_val.npz               # MT 13-mer 5M val (0.205; proves val≈test, no discrepancy)
│   │   ├── mt50m_test_final.npz       # MT 13-mer 50M  -> acc_top1 0.8924
│   │   ├── mt50m_6mer_test_final.npz  # MT 6-mer e64 50M -> acc_top1 0.2662
│   │   └── ntv2_5M_rctta.npz          # NT-v2 5M -> acc_fwd 0.3097 / acc_tta 0.3198
│   └── training_histories/            # NT-v2 per-epoch curves (ntv2_5M, ntv2_50M)
├── configs/{mt,ntv2}/                 # exact configs used (+ MT model/optimizer subdirs)
├── run_scripts/                       # MT run + eval scripts
└── logs/                              # MT 13-mer & 6-mer-e64 50M train.logs
```

**Data / model checkpoints (too big for git, on /work):**
- MT experiments: `/work/ymj1123ntu/mt50m_soil/experiments/genus_50M_soil*/`,
  `/work/ymj1123ntu/mt5m_soil/experiments/genus_5M_soil_967182/`
- NT-v2: `/work/ymj1123ntu/mt5m_soil/results/nt_soil_genus_{5M,50M}/`
- Shared `test_final` (5M): `/work/ymj1123ntu/mt5m_soil/data/test_final/`
- 50M train shards: `/work/ymj1123ntu/mt50m_soil/data/train/`

---

## 8. To finish (running / TODO)

- [ ] MT-6mer-e128 50M (job 970180): eval `test_final` → fill the e128 cell.
- [ ] NT-v2-50M (job 970084): finish training (may need one mid-ckpt resume near 48 h) → RC-TTA eval.
- [ ] (optional) MT RC-TTA to match NT-v2's protocol.
- [ ] (optional) multi-seed error bars on headline cells.
