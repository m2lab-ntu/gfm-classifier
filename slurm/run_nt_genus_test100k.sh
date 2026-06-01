#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J nt_genus_test100k
#SBATCH -p normal
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH -t 00:30:00
#SBATCH -o /work/ymj1123ntu/token_level_gfm_classifier/slurm-nt_genus_test100k-%j.out
#SBATCH -e /work/ymj1123ntu/token_level_gfm_classifier/slurm-nt_genus_test100k-%j.err

set -euo pipefail

REPO=/work/ymj1123ntu/token_level_gfm_classifier
DATA=/work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M
GN_RESULTS=${REPO}/results/nt_token_genus_lora_v9_50M

source ~/miniconda/etc/profile.d/conda.sh
conda activate gfm

export HF_HOME=/work/ymj1123ntu/.cache/huggingface
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export OMP_NUM_THREADS=4
export PYTHONUNBUFFERED=1

echo "Start: $(date) | Host: $(hostname)"
nvidia-smi || true

cd ${REPO}/scripts

python -u run_nt_genus_test100k.py \
  --config       ${REPO}/configs/nt_token_genus_v9_50M.yaml \
  --checkpoint   ${GN_RESULTS}/best.pt \
  --test_fasta   ${DATA}/reads_100K.fa \
  --test_labels  ${DATA}/labels_100K.tsv \
  --train_labels ${DATA}/labels_50M.tsv \
  --out_dir      ${GN_RESULTS}/eval_test100k \
  --batch_size   512

echo "Done: $(date)"
