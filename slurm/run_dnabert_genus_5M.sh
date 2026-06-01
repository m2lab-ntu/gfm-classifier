#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J dnabert_genus_5M
#SBATCH -p normal
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=128G
#SBATCH -t 48:00:00
#SBATCH -o slurm-dnabert_genus_5M-%j.out
#SBATCH -e slurm-dnabert_genus_5M-%j.err

# ============================================================
# DNABERT (overlapping 6-mer, stride=1) — Genus classification
# Direct tokenization comparison vs NT-v2 (non-overlapping 6-mer, stride=6).
# Same k=6, only stride differs — isolates the effect of overlapping tokens.
# ============================================================

set -euo pipefail

REPO_DIR="/work/ymj1123ntu/token_level_gfm_classifier"
cd "${REPO_DIR}"

echo "========================================="
echo "DNABERT — Genus (5M balanced reads)"
echo "Start time: $(date)"
echo "Working dir: $(pwd)"
echo "========================================="

echo "SLURM job info:"
echo "  Job ID:   ${SLURM_JOB_ID:-N/A}"
echo "  Node(s):  ${SLURM_JOB_NODELIST:-N/A}"
echo ""

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

echo "Python: $(which python)"
echo "PyTorch: $(python -c 'import torch; print(torch.__version__)')"
echo ""

CONFIG="${REPO_DIR}/configs/dnabert_token_genus_5M.yaml"
RESULT_DIR="${REPO_DIR}/results/dnabert_token_genus_5M"

cd scripts

# ===== Phase 1: Train =====
python -u train.py --config "${CONFIG}" 2>&1

echo ""

# ===== Phase 2: Evaluate (forward only) =====
echo "Running forward-only evaluation..."
python -u evaluate.py \
  --config "${CONFIG}" \
  --benchmark_speed \
  2>&1

echo ""

# ===== Phase 3: Evaluate with RC TTA =====
echo "Running RC TTA evaluation..."
python -u evaluate.py \
  --config "${CONFIG}" \
  --rc_tta \
  --output_dir "${RESULT_DIR}/eval_rc_tta" \
  2>&1

echo ""
echo "========================================="
echo "DNABERT training + evaluation completed at: $(date)"
echo "========================================="
