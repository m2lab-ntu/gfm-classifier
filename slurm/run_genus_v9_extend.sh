#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J v9_ext30
#SBATCH -p normal
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=128G
#SBATCH -t 48:00:00
#SBATCH -o slurm-v9_extend-%j.out
#SBATCH -e slurm-v9_extend-%j.err

# ============================================================
# v9 Genus EXTENDED: Resume training from epoch 10 → up to 30
#   - Config num_epochs changed from 10 → 30
#   - Fresh cosine LR schedule for remaining 20 epochs
#   - Early stopping patience=5 will terminate if plateaued
#   - ~6.75h/epoch → 48hr limit ≈ 7 epochs per SLURM job
#   - If not done, submit this script again to continue
# ============================================================

set -euo pipefail

REPO_DIR="/work/ymj1123ntu/token_level_gfm_classifier"
cd "${REPO_DIR}"

source /home/ymj1123ntu/miniconda/etc/profile.d/conda.sh
conda activate gfm

export HF_HOME=/work/ymj1123ntu/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface
export TRANSFORMERS_CACHE=/work/ymj1123ntu/.cache/huggingface
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export OMP_NUM_THREADS=4
export PYTHONUNBUFFERED=1

CONFIG="${REPO_DIR}/configs/nt_token_genus_v9_50M.yaml"
RESULTS="${REPO_DIR}/results/nt_token_genus_lora_v9_50M"
LAST_CKPT="${RESULTS}/last.pt"

echo "========================================="
echo "v9 Genus EXTENDED — epochs 10→30"
echo "Resume from: ${LAST_CKPT}"
echo "Start time: $(date)"
echo "========================================="

nvidia-smi || true
echo ""

cd scripts

# ===== Step 1: Resume training =====
echo "===== Step 1: Resume training (extended to 30 epochs) ====="
python -u train.py \
  --config "${CONFIG}" \
  --resume "${LAST_CKPT}" \
  2>&1

echo ""
echo "Training done at: $(date)"
echo ""

# ===== Step 2: Evaluation (forward-only) =====
echo "===== Step 2: Evaluation (forward-only) ====="
python -u evaluate.py \
  --config "${CONFIG}" \
  --checkpoint "${RESULTS}/best.pt" \
  --output_dir "${RESULTS}/eval" \
  --benchmark_speed \
  2>&1

echo ""

# ===== Step 3: Evaluation (RC TTA) =====
echo "===== Step 3: Evaluation (RC TTA) ====="
python -u evaluate.py \
  --config "${CONFIG}" \
  --checkpoint "${RESULTS}/best.pt" \
  --output_dir "${RESULTS}/eval_rc_tta" \
  --rc_tta \
  2>&1

echo ""
echo "========================================="
echo "v9 Genus EXTENDED completed at: $(date)"
echo "========================================="
