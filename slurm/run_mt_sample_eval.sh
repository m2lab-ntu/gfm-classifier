#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J mt_sample_eval
#SBATCH -p normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --mem=64G
#SBATCH -t 01:00:00
#SBATCH -o slurm-mt_sample_eval-%j.out
#SBATCH -e slurm-mt_sample_eval-%j.err

# ============================================================
# Sample-level evaluation for MetaTransformer genus predictions.
# Runs evaluate_sample.py on 13-mer (87.43%) and 6-mer stride=1 (48.82%).
# Expected runtime: ~20 minutes total (CPU-only, no GPU needed).
# ============================================================

set -euo pipefail
cd /work/ymj1123ntu/token_level_gfm_classifier

source ~/miniconda/etc/profile.d/conda.sh
conda activate gfm

echo "=== MT Sample-Level Evaluation ==="
echo "Date: $(date)"
echo "Host: $(hostname)"
echo ""

# ── 13-mer (87.43%) ───────────────────────────────────────────
echo "[1/2] MT 13-mer stride=1 (87.43%) ..."
python scripts/evaluate_sample.py \
    --predictions results/mt_genus_13mer/mt_genus_13mer_predictions.npz \
    --out_dir     results/mt_genus_13mer/eval_sample_level \
    --n_partition_samples 100 --reads_per_sample 50000 \
    --n_sparse_samples 200  --genera_present 60

echo ""

# ── 6-mer stride=1 (48.82%) ───────────────────────────────────
echo "[2/2] MT 6-mer stride=1 (48.82%) ..."
python scripts/evaluate_sample.py \
    --predictions results/mt_genus_6mer_s1/mt_genus_6mer_s1_predictions.npz \
    --out_dir     results/mt_genus_6mer_s1/eval_sample_level \
    --n_partition_samples 100 --reads_per_sample 50000 \
    --n_sparse_samples 200  --genera_present 60

echo ""
echo "=== Done: $(date) ==="
echo ""
echo "Results:"
echo "  results/mt_genus_13mer/eval_sample_level/sample_metrics.json"
echo "  results/mt_genus_6mer_s1/eval_sample_level/sample_metrics.json"
