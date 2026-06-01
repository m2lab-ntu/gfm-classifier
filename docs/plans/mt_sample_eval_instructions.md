# MetaTransformer Sample-Level Evaluation Instructions

Runs the same abundance estimation + binary detection evaluation (Slides 10/11)
on MetaTransformer 13-mer predictions for comparison with NT-v2 v9.

---

## Step 1 — On Taiwania-2: run inference and save predictions

```bash
cd /home/ymj1123ntu/MetaTransformer

# Find the experiment directory (genus 13-mer 50M model)
ls /work/ymj1123ntu/MetaTransformer_experiments/

# Run inference — replace <timestamp> with the actual dir name
python /path/to/token_level_gfm_classifier/scripts/extract_mt_predictions.py \
    --exp_dir /work/ymj1123ntu/MetaTransformer_experiments/genus_50M_<timestamp> \
    --val_dir /work/ymj1123ntu/data_50M/metatransformer_format/val \
    --vocab   /home/ymj1123ntu/MetaTransformer/vocab_file/vocab_13mer.txt \
    --out     /work/ymj1123ntu/mt_genus_13mer_predictions.npz \
    --class_indices 3 \
    --batch_size 1024
```

Expected output: `mt_genus_13mer_predictions.npz` (~10 MB, contains `preds` + `labels` arrays).

---

## Step 2 — Transfer to TWCC

```bash
# On Taiwania-2:
scp /work/ymj1123ntu/mt_genus_13mer_predictions.npz \
    ymj1123ntu@<TWCC_HOST>:/work/ymj1123ntu/token_level_gfm_classifier/results/mt_genus_13mer/
```

---

## Step 3 — On TWCC: run evaluate_sample.py

```bash
cd /work/ymj1123ntu/token_level_gfm_classifier
conda activate gfm

python scripts/evaluate_sample.py \
    --predictions results/mt_genus_13mer/mt_genus_13mer_predictions.npz \
    --out_dir     results/mt_genus_13mer/eval_sample_level \
    --n_partition_samples 100 --reads_per_sample 50000 \
    --n_sparse_samples 200  --genera_present 60
```

Results saved to `results/mt_genus_13mer/eval_sample_level/`:
- `sample_metrics.json`      ← Pearson r, Bray-Curtis
- `abundance_scatter.png`
- `sensitivity_by_abundance.png`
- `detection_results.json`

---

## Step 4 — Compare with NT-v2 v9

| Metric | NT-v2 LoRA v9 (67.07%) | MT 13-mer (87.42%) |
|--------|------------------------|---------------------|
| Pearson r (abundance) | 0.993 | ? |
| Bray-Curtis | 0.094 | ? |
| Sensitivity ≥1% | 100% | ? |
| Sensitivity 0.1–1% | 97.6% | ? |

---

## Notes

- The val set label distribution differs between models:
  NT-v2 uses a 90/10 split of 50M balanced reads (5M val reads).
  MT uses its own train/val split from the same 50M dataset.
  Both should produce comparable results since the data is the same.

- If `extract_mt_predictions.py` fails with import errors, check that you are
  running from within `/home/ymj1123ntu/MetaTransformer/` and that `src/` is
  on the Python path.
