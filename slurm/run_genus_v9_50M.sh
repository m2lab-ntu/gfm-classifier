#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J v9_50M
#SBATCH -p normal
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=128G
#SBATCH -t 48:00:00
#SBATCH -o slurm-v9_50M-%j.out
#SBATCH -e slurm-v9_50M-%j.err

# ============================================================
# v9 50M: Genus classification on 50M balanced reads
#   - Subsample 50M from full 258M FASTA (species-balanced)
#   - Resume from v8 best.pt (63.05% RC TTA on 5M)
#   - batch_size=256 for better GPU utilization
#   - Resource monitoring enabled
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
V8_CKPT="${REPO_DIR}/results/nt_token_genus_lora_v8_5M/best.pt"
DATA_DIR="/work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M"
FULL_FASTA="/work/ymj1123ntu/gfm_embedding_classification/data/labeled_multi_level_generated/reads.fa"

echo "========================================="
echo "v9 50M — Genus Classification (50M balanced)"
echo "Start time: $(date)"
echo "========================================="

nvidia-smi || true
echo ""

# ===== Step 1: Generate 50M balanced subsample =====
if [ ! -f "${DATA_DIR}/reads_50M.fa" ]; then
    echo "===== Step 1: Subsampling 50M reads ====="
    cd scripts
    python -u subsample_balanced.py \
      --input "${FULL_FASTA}" \
      --output_fasta "${DATA_DIR}/reads_50M.fa" \
      --output_labels "${DATA_DIR}/labels_50M.tsv" \
      --total_reads 50000000 \
      --balance_by species \
      --seed 42 \
      2>&1
    echo "Subsampling done at: $(date)"
    echo ""
    cd "${REPO_DIR}"
else
    echo "===== Step 1: 50M data already exists, skipping ====="
    echo ""
fi

# ===== Step 2: Training (resume from v8) =====
echo "===== Step 2: Training (init from v8 best.pt) ====="
cd scripts
python -u train.py \
  --config "${CONFIG}" \
  --init_from "${V8_CKPT}" \
  2>&1

echo ""
echo "Training done at: $(date)"
echo ""

# ===== Step 3: Evaluation (forward-only) =====
echo "===== Step 3: Evaluation (forward-only) ====="
python -u evaluate.py \
  --config "${CONFIG}" \
  --checkpoint "${RESULTS}/best.pt" \
  --output_dir "${RESULTS}/eval" \
  --benchmark_speed \
  2>&1

echo ""

# ===== Step 4: Evaluation (RC TTA) =====
echo "===== Step 4: Evaluation (RC TTA) ====="
python -u evaluate.py \
  --config "${CONFIG}" \
  --checkpoint "${RESULTS}/best.pt" \
  --output_dir "${RESULTS}/eval_rc_tta" \
  --rc_tta \
  2>&1

echo ""
echo "========================================="
echo "v9 50M completed at: $(date)"
echo "========================================="
