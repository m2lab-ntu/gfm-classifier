#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J dnabert2_genus_50M
#SBATCH -p normal
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=256G
#SBATCH -t 48:00:00
#SBATCH -o slurm-dnabert2_genus_50M-%j.out
#SBATCH -e slurm-dnabert2_genus_50M-%j.err

# ============================================================
# DNABERT-2 (BPE) — Genus @ 50M (scale-matched to NT-v2 v9)
# May need resume if 48h runs out.
# ============================================================

set -euo pipefail

REPO_DIR="/work/ymj1123ntu/token_level_gfm_classifier"
cd "${REPO_DIR}"

echo "========================================="
echo "DNABERT-2 — Genus (50M balanced reads)"
echo "Start time: $(date)"
echo "========================================="

echo "GPU status:"
nvidia-smi || echo "nvidia-smi not available"
echo ""

source /home/ymj1123ntu/miniconda/etc/profile.d/conda.sh
conda activate gfm

export HF_HOME=/work/ymj1123ntu/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface
export TRANSFORMERS_CACHE=/work/ymj1123ntu/.cache/huggingface

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export OMP_NUM_THREADS=4
export PYTHONUNBUFFERED=1

CONFIG="${REPO_DIR}/configs/dnabert2_token_genus_50M.yaml"
RESULT_DIR="${REPO_DIR}/results/dnabert2_token_genus_50M"

cd scripts

# ===== Train (auto-resume if last.pt exists) =====
if [ -f "${RESULT_DIR}/last.pt" ]; then
    echo "Resuming from ${RESULT_DIR}/last.pt"
    python -u train.py --config "${CONFIG}" --resume "${RESULT_DIR}/last.pt" 2>&1
else
    python -u train.py --config "${CONFIG}" 2>&1
fi

echo ""

# ===== Evaluate (forward only) =====
echo "Running forward-only evaluation..."
python -u evaluate.py \
  --config "${CONFIG}" \
  --benchmark_speed \
  2>&1

echo ""

# ===== Evaluate with RC TTA =====
echo "Running RC TTA evaluation..."
python -u evaluate.py \
  --config "${CONFIG}" \
  --rc_tta \
  --output_dir "${RESULT_DIR}/eval_rc_tta" \
  2>&1

echo ""
echo "DNABERT-2 50M training + eval completed at: $(date)"
