#!/bin/bash
#SBATCH -A MST114414
#SBATCH -J nt_genus_v10_eval
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH -t 00:30:00
#SBATCH -o /work/ymj1123ntu/logs/nt_genus_v10_eval-%j.out
#SBATCH -e /work/ymj1123ntu/logs/nt_genus_v10_eval-%j.err

set -euo pipefail

REPO=/work/ymj1123ntu/gfm-classifier
DATA=/work/ymj1123ntu/data
CKPT=/work/ymj1123ntu/checkpoints/nt_token_genus_v10_258M/best.pt
OUT=/work/ymj1123ntu/checkpoints/nt_token_genus_v10_258M/eval_test100k

module load miniconda3/26.1.1
source $(conda info --base)/etc/profile.d/conda.sh
conda activate gfm

export HF_HOME=/work/ymj1123ntu/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface
export TRANSFORMERS_CACHE=/work/ymj1123ntu/.cache/huggingface
export OMP_NUM_THREADS=4
export PYTHONUNBUFFERED=1

echo "Start: $(date) | Host: $(hostname)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1

cd ${REPO}/scripts

python -u run_nt_genus_test100k.py \
  --config       ${REPO}/configs/nt_token_genus_v10_258M.yaml \
  --checkpoint   ${CKPT} \
  --test_fasta   ${DATA}/reads_100K.fa \
  --test_labels  ${DATA}/labels_100K.tsv \
  --train_labels ${DATA}/labels_50M.tsv \
  --out_dir      ${OUT} \
  --batch_size   512

echo "Done: $(date)"
