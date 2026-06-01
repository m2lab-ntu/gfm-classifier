#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J sp_v4_res
#SBATCH -p normal
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=128G
#SBATCH -t 48:00:00
#SBATCH -o slurm-sp_v4_50M_resume-%j.out
#SBATCH -e slurm-sp_v4_50M_resume-%j.err

# ============================================================
# Species v4 RESUME: Continue training from last checkpoint
#   - Resumes from results/nt_token_species_v4_50M/last.pt
#   - Config num_epochs extended to 30
#   - ~6.9h/epoch → 48hr limit ≈ 6-7 epochs per SLURM job
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

CONFIG="${REPO_DIR}/configs/nt_token_species_v4_50M.yaml"
RESULTS="${REPO_DIR}/results/nt_token_species_v4_50M"
LAST_CKPT="${RESULTS}/last.pt"

echo "========================================="
echo "Species v4 RESUME — 50M balanced"
echo "Resume from: ${LAST_CKPT}"
echo "Start time: $(date)"
echo "========================================="

nvidia-smi || true
echo ""

cd scripts

# ===== Step 1: Resume training =====
echo "===== Step 1: Resume training ====="
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
echo "Species v4 50M RESUME completed at: $(date)"
echo "========================================="
