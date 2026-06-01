# Species-Level Abundance Evaluation Plan
> Requested after 0512 meeting. Last updated: 2026-05-14.

## Goal

Add species-level relative abundance comparisons across four pipelines, analogous to the genus-level comparison in §4.13:

| Experiment | Router | Species classifier | Status |
|---|---|---|---|
| A  sp_v4 flat          | —              | NT-v2 sp_v4 (50M) flat    | ⬜ TWCC |
| B  Per-genus predicted | v9 (66.1%)     | per-genus NT-v2 (50M)     | ⬜ TWCC |
| C  Per-genus oracle    | true genus     | per-genus NT-v2 (50M)     | ⬜ TWCC |
| D  MT species flat     | —              | MT 13-mer species (50M)   | ⬜ Taiwania2→TWCC |
| E  MT hierarchical     | MT genus (87%) | MT species (mask by genus)| ⬜ Taiwania2 |
| F  MT genus → per-genus| MT genus (87%) | per-genus NT-v2 (50M)     | ⬜ TWCC (after Taiwania2) |

Experiment F is the most scientifically interesting: it isolates the contribution of the genus router by keeping species classifiers fixed and replacing v9 (66.1%) with MT genus (87.4%).

---

## Environment Summary

| Environment | Key assets | Role |
|---|---|---|
| Local | code editor, git | code changes, testing, plotting |
| TWCC (`/work/ymj1123ntu/`) | NT-v2 all models, per-genus 81 classifiers, evaluate_sample.py | run exps A/B/C/F; run sample eval on all npz |
| Taiwania2 (`/work/ymj1123ntu/`) | MT models (genus + species), MetaTransformer code | run exps D/E; extract npz; scp to TWCC |

---

## File locations

```
TWCC:
  /work/ymj1123ntu/token_level_gfm_classifier/
    scripts/evaluate_per_genus.py          ← modified to save npz (done)
    scripts/evaluate_sample.py             ← unchanged, works for species too
    scripts/extract_mt_predictions.py      ← for MT inference on Taiwania2
    results/
      nt_token_species_v4_50M/eval/predictions.npz   ← sp_v4 flat preds (check exists)
      per_genus_eval/                                 ← output of evaluate_per_genus.py
        predictions_predicted.npz                    ← Exp B
        predictions_oracle.npz                       ← Exp C
      mt_species_flat/                               ← transfer from Taiwania2 (Exp D)
      mt_hierarchical/                               ← transfer from Taiwania2 (Exp E)
      mt_genus_for_routing/                          ← transfer from Taiwania2 (Exp F)

Taiwania2:
  /work/ymj1123ntu/MetaTransformer_experiments/
    genus_50M_<timestamp>/checkpoints/    ← MT genus 13-mer model
    species_50M_<timestamp>/checkpoints/  ← MT species model
  /work/ymj1123ntu/data_50M/metatransformer_format/val/   ← MT val set
```

---

## Task Checklist

### LOCAL — code changes (do first)

- [x] **L1**: `evaluate_per_genus.py` saves `predictions_predicted.npz` + `predictions_oracle.npz`
  - Note: local agent's version also saves `probs` (softmax matrix [N, n_species]) in each npz.
    If TWCC copy is older, re-pull from GitHub after local pushes.
- [ ] **L2**: Verify `results/nt_token_species_v4_50M/eval/predictions.npz` exists on TWCC:
  ```bash
  ls /work/ymj1123ntu/token_level_gfm_classifier/results/nt_token_species_v4_50M/eval/
  ```
  If missing: re-run `python scripts/evaluate.py --config configs/nt_token_species_v4_50M.yaml`
  (saves predictions.npz automatically)
- [x] **L3**: `scripts/extract_mt_hierarchical_predictions.py` written (Exp E — MT genus mask → MT species)
- [x] **L4**: `scripts/evaluate_per_genus_mt_router.py` written (Exp F — MT genus npz as router)

> **ACTION NEEDED**: sync scripts from the local working copy to TWCC (main project dir) and Taiwania2.
> The local copy lives at `/nas2/hierachical_test/token_level_gfm_classifier/scripts/` (no git repo there).
>
> ```bash
> # ── Copy to TWCC main project dir (same NAS, may be a local cp) ──────────
> TWCC=ymj1123ntu@<TWCC_HOST>
> TWCC_ROOT=/work/ymj1123ntu/token_level_gfm_classifier/scripts
>
> scp /nas2/hierachical_test/token_level_gfm_classifier/scripts/extract_mt_predictions.py          $TWCC:$TWCC_ROOT/
> scp /nas2/hierachical_test/token_level_gfm_classifier/scripts/extract_mt_hierarchical_predictions.py $TWCC:$TWCC_ROOT/
> scp /nas2/hierachical_test/token_level_gfm_classifier/scripts/evaluate_per_genus_mt_router.py   $TWCC:$TWCC_ROOT/
> scp /nas2/hierachical_test/token_level_gfm_classifier/scripts/evaluate_per_genus.py             $TWCC:$TWCC_ROOT/
>
> # ── Copy to Taiwania2 (L3 script runs there) ──────────────────────────────
> T2=ymj1123ntu@t2.nchc.org.tw
> T2_ROOT=/home/ymj1123ntu/MetaTransformer
>
> scp /nas2/hierachical_test/token_level_gfm_classifier/scripts/extract_mt_predictions.py          $T2:$T2_ROOT/
> scp /nas2/hierachical_test/token_level_gfm_classifier/scripts/extract_mt_hierarchical_predictions.py $T2:$T2_ROOT/
> ```

---

### TWCC — experiments A / B / C

**Exp A: sp_v4 flat species abundance**
```bash
conda activate gfm
cd /work/ymj1123ntu/token_level_gfm_classifier

# Check if predictions.npz exists (5M val reads, species labels)
ls results/nt_token_species_v4_50M/eval/predictions.npz

python scripts/evaluate_sample.py \
    --predictions results/nt_token_species_v4_50M/eval/predictions.npz \
    --out_dir     results/nt_token_species_v4_50M/eval_sample_level \
    --n_partition_samples 100 --reads_per_sample 50000 \
    --n_sparse_samples 200   --genera_present 200
```

**Exp B + C: Per-genus pipeline species abundance**
```bash
# Re-run evaluate_per_genus.py (now saves npz — L1 already applied)
python scripts/evaluate_per_genus.py \
    --test_fasta  /nas2/hierachical_test/data/reads_100K.fa \
    --test_labels /nas2/hierachical_test/data/labels_100K.tsv \
    --genus_config     configs/nt_token_genus_v9_50M.yaml \
    --genus_checkpoint results/nt_token_genus_lora_v9_50M/best.pt \
    --per_genus_dir    results/per_genus \
    --output_dir       results/per_genus_eval

# Then run sample eval on both routing modes
python scripts/evaluate_sample.py \
    --predictions results/per_genus_eval/predictions_predicted.npz \
    --out_dir     results/per_genus_eval/eval_sample_level_predicted \
    --n_partition_samples 100 --reads_per_sample 50000 \
    --n_sparse_samples 200   --genera_present 200

python scripts/evaluate_sample.py \
    --predictions results/per_genus_eval/predictions_oracle.npz \
    --out_dir     results/per_genus_eval/eval_sample_level_oracle \
    --n_partition_samples 100 --reads_per_sample 50000 \
    --n_sparse_samples 200   --genera_present 200
```

Note: B/C run on the 100K independent test set (not 5M val set). For fair comparison with
A and D/E, we may also want to run evaluate_per_genus.py on the 5M val set. TBD.

**Exp F: MT genus router → per-genus NT-v2 (after Taiwania2 delivers mt_genus_for_routing.npz)**
```bash
# Requires: scripts/evaluate_per_genus_mt_router.py (L4) + mt_genus_for_routing.npz
python scripts/evaluate_per_genus_mt_router.py \
    --test_fasta        /nas2/hierachical_test/data/reads_100K.fa \
    --test_labels       /nas2/hierachical_test/data/labels_100K.tsv \
    --genus_predictions results/mt_genus_for_routing/mt_genus_preds_100K.npz \
    --per_genus_dir     results/per_genus \
    --output_dir        results/mt_genus_per_genus_eval

python scripts/evaluate_sample.py \
    --predictions results/mt_genus_per_genus_eval/predictions_predicted.npz \
    --out_dir     results/mt_genus_per_genus_eval/eval_sample_level \
    --n_partition_samples 100 --reads_per_sample 50000 \
    --n_sparse_samples 200   --genera_present 200
```

---

### TAIWANIA2 — experiments D / E + genus predictions for F

SSH: `ssh ymj1123ntu@t2.nchc.org.tw`  (or equivalent)
MT root: `/home/ymj1123ntu/MetaTransformer/`
conda env: `MetaTransformer`
Experiments dir: `/work/ymj1123ntu/MetaTransformer_experiments/`

**Step T0: Find checkpoint paths**
```bash
ls /work/ymj1123ntu/MetaTransformer_experiments/
# Note the full dir names for genus_50M and species_50M experiments
GENUS_EXP=/work/ymj1123ntu/MetaTransformer_experiments/genus_50M_<timestamp>
SPECIES_EXP=/work/ymj1123ntu/MetaTransformer_experiments/species_50M_<timestamp>
```

**Exp D: MT species flat predictions (for sample-level eval)**
```bash
cd /home/ymj1123ntu/MetaTransformer
conda activate MetaTransformer

python /path/to/token_level_gfm_classifier/scripts/extract_mt_predictions.py \
    --exp_dir    $SPECIES_EXP \
    --val_dir    /work/ymj1123ntu/data_50M/metatransformer_format/val \
    --vocab      /home/ymj1123ntu/MetaTransformer/vocab_file/vocab_13mer.txt \
    --out        /work/ymj1123ntu/mt_species_flat_preds.npz \
    --class_indices 1 \
    --batch_size 1024
# class_indices=1 → species class from FASTA header (>lbl|species_id|...)
```

Transfer to TWCC:
```bash
scp /work/ymj1123ntu/mt_species_flat_preds.npz \
    ymj1123ntu@<TWCC_HOST>:/work/ymj1123ntu/token_level_gfm_classifier/results/mt_species_flat/mt_species_flat_preds.npz
```

**Exp E: MT hierarchical (MT genus mask → MT species)**

Requires `extract_mt_hierarchical_predictions.py` (L3 — sync from local via the scp block above).

```bash
# After scp completes, the script is at /home/ymj1123ntu/MetaTransformer/
cd /home/ymj1123ntu/MetaTransformer
python extract_mt_hierarchical_predictions.py \
    --genus_exp_dir   $GENUS_EXP \
    --species_exp_dir $SPECIES_EXP \
    --val_dir         /work/ymj1123ntu/data_50M/metatransformer_format/val \
    --vocab           vocab_file/vocab_13mer.txt \
    --genus_class_indices   3 \
    --species_class_indices 1 \
    --out             /work/ymj1123ntu/mt_hierarchical_preds.npz \
    --batch_size 512
```

Transfer to TWCC:
```bash
scp /work/ymj1123ntu/mt_hierarchical_preds.npz \
    ymj1123ntu@<TWCC_HOST>:/work/ymj1123ntu/token_level_gfm_classifier/results/mt_hierarchical/mt_hierarchical_preds.npz
```

**Exp F prep: MT genus predictions on the 100K independent test set**
```bash
# Need to run MT genus model on the independent test set reads (reads_100K.fa)
# Extract the 100K FASTA from Taiwania2 data or scp from TWCC
scp ymj1123ntu@<TWCC_HOST>:/nas2/hierachical_test/data/reads_100K.fa \
    /work/ymj1123ntu/reads_100K.fa

# Prepare single-file val dir for MT inference
mkdir -p /work/ymj1123ntu/mt_inference_100K
cp /work/ymj1123ntu/reads_100K.fa /work/ymj1123ntu/mt_inference_100K/

python /home/ymj1123ntu/MetaTransformer/token_level_gfm_classifier/scripts/extract_mt_predictions.py \
    --exp_dir    $GENUS_EXP \
    --val_dir    /work/ymj1123ntu/mt_inference_100K \
    --vocab      vocab_file/vocab_13mer.txt \
    --out        /work/ymj1123ntu/mt_genus_preds_100K.npz \
    --class_indices 3 \
    --batch_size 1024
```

Transfer to TWCC:
```bash
scp /work/ymj1123ntu/mt_genus_preds_100K.npz \
    ymj1123ntu@<TWCC_HOST>:/work/ymj1123ntu/token_level_gfm_classifier/results/mt_genus_for_routing/mt_genus_preds_100K.npz
```

---

### TWCC — final sample eval after transfers (Exp D/E)

```bash
# Exp D: MT species flat
python scripts/evaluate_sample.py \
    --predictions results/mt_species_flat/mt_species_flat_preds.npz \
    --out_dir     results/mt_species_flat/eval_sample_level \
    --n_partition_samples 100 --reads_per_sample 50000 \
    --n_sparse_samples 200   --genera_present 200

# Exp E: MT hierarchical
python scripts/evaluate_sample.py \
    --predictions results/mt_hierarchical/mt_hierarchical_preds.npz \
    --out_dir     results/mt_hierarchical/eval_sample_level \
    --n_partition_samples 100 --reads_per_sample 50000 \
    --n_sparse_samples 200   --genera_present 200
```

---

## Script Design Specs

### L3: extract_mt_hierarchical_predictions.py

Logic:
1. Load MT genus model → forward pass on val set → genus logits [N, 120]
2. Load MT species model → forward pass on val set → species logits [N, 1535]
3. Load genus→species mapping (from FASTA headers: species_class_indices=1, genus_class_indices=3)
   - Build dict: genus_id → list of species_ids
4. For each read i:
   - predicted_genus = argmax(genus_logits[i])
   - valid_species = genus2species[predicted_genus]
   - masked_logits = species_logits[i, valid_species]
   - predicted_species = valid_species[argmax(masked_logits)]
5. Save preds=predicted_species, labels=true_species as npz

Key: the genus→species mapping must use the same class ID space as the MT model's class_indices.
(In FASTA header: field 3 = genus class 0–119, field 1 = species class 0–1534)

### L4: evaluate_per_genus_mt_router.py (for Exp F)

Copy evaluate_per_genus.py, remove genus model loading and inference, replace with:
```python
# Load pre-computed MT genus predictions (from Taiwania2)
genus_npz = np.load(args.genus_predictions)
mt_genus_preds = genus_npz["preds"]   # [N] genus class IDs in MT's class space
mt_genus_acc   = (genus_npz["preds"] == genus_npz["labels"]).mean()
```

Important: MT genus IDs may not match evaluate_per_genus.py's local genus IDs (which are
sorted alphabetically). Need to verify the mapping before running Exp F.

To check: compare MT's genus_mapping.tab with the `genus2id` dict built in load_test_data().

---

## Expected Results Table

(Fill in as experiments complete)

| Pipeline | Router | Species Top-1 | Pearson r | Bray-Curtis | ROC AUC |
|---|---|---|---|---|---|
| sp_v4 flat (NT-v2)       | —            | 15.9%  | ?     | ?     | ?     |
| Per-genus predicted      | v9 (66.1%)   | 14.7%  | ?     | ?     | ?     |
| Per-genus oracle         | true genus   | 27.8%  | ?     | ?     | ?     |
| MT species flat          | —            | 49.62% | ?     | ?     | ?     |
| MT hierarchical          | MT (87.4%)   | ?      | ?     | ?     | ?     |
| Per-genus + MT router    | MT (87.4%)   | ?      | ?     | ?     | ?     |

Note: Top-1 % from existing classification eval; abundance metrics are new.
Per-genus and MT hierarchical are evaluated on the independent 100K test set.
sp_v4 and MT species are evaluated on the 5M val set.
→ Sample-level results are not directly cross-comparable unless both use the same set.
Recommendation: also run per-genus on 5M val set for fair comparison, OR note the difference.

---

## Important: Class ID Spaces

| Model | Genus IDs | Species IDs |
|---|---|---|
| NT-v2 (evaluate_per_genus.py) | 0–119 sorted alphabetically by genus_name | 0–1534 sorted alphabetically |
| MT genus model | from FASTA header field 3 (integer, 0–119?) | — |
| MT species model | — | from FASTA header field 1 (integer, 0–1534?) |

**Must verify before running Exp F**: print both genus2id mappings and confirm they are identical.
If not, apply the mapping table when loading MT genus predictions.
