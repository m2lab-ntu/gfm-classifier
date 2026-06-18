#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J verify_dnabert2_leak
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH -t 02:00:00
#SBATCH -o /work/ymj1123ntu/logs/verify_dnabert2_leak-%j.out
#SBATCH -e /work/ymj1123ntu/logs/verify_dnabert2_leak-%j.err

# Recompute Nano4 val split (seed=42) and score epoch-17 best.pt on it.
# val_acc ≈ 59.22% → split consistent, resume safe.
# val_acc >> 59.22% → leakage, must retrain.
set -euo pipefail

REPO=/work/ymj1123ntu/gfm-classifier
DATA=/work/ymj1123ntu/data
CKPT=/work/ymj1123ntu/checkpoints/dnabert2_token_genus_50M/best.pt
CONFIG=${REPO}/configs/dnabert2_token_genus_50M.yaml

echo "Start: $(date) | Host: $(hostname)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1

module load miniconda3/26.1.1
source $(conda info --base)/etc/profile.d/conda.sh
conda activate gfm

export HF_HOME=/work/ymj1123ntu/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface
export TRANSFORMERS_CACHE=/work/ymj1123ntu/.cache/huggingface
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1

cd ${REPO}/scripts
python -u verify_dnabert2_split_leakage.py \
    --config     ${CONFIG} \
    --checkpoint ${CKPT} \
    --fasta      ${DATA}/reads_50M.fa \
    --labels     ${DATA}/labels_50M.tsv \
    --max_val    0 \
    --expected_acc 0.5922

echo "Done: $(date)"
