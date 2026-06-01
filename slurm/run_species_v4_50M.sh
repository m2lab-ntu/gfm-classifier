#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J sp_v4_50M
#SBATCH -p normal
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=128G
#SBATCH -t 48:00:00
#SBATCH -o slurm-sp_v4_50M-%j.out
#SBATCH -e slurm-sp_v4_50M-%j.err

# ============================================================
# Species v4: Species classification on 50M balanced reads
#   - Same data as genus v9 (50M balanced, already generated)
#   - Init from genus v9 best.pt (backbone LoRA weights)
#     Head will be partially loaded (genus→species dim mismatch
#     handled by --init_from partial loading)
#   - 1535 species classes
#   - batch_size=256
#   - Estimated: ~7h/epoch × 10 epochs = ~70h → may need resume
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
V9_CKPT="${REPO_DIR}/results/nt_token_genus_lora_v9_50M/best.pt"

echo "========================================="
echo "Species v4 — 50M balanced (1535 classes)"
echo "Init from: genus v9 best.pt"
echo "Start time: $(date)"
echo "========================================="

nvidia-smi || true
echo ""

cd scripts

# ===== Step 1: Training (init from genus v9) =====
echo "===== Step 1: Training (init from genus v9 best.pt) ====="
python -u train.py \
  --config "${CONFIG}" \
  --init_from "${V9_CKPT}" \
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
echo "Species v4 50M completed at: $(date)"
echo "========================================="
