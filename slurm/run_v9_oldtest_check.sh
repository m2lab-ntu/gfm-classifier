#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J v9_oldtest_check
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH -t 01:00:00
#SBATCH -o /work/ymj1123ntu/logs/v9_oldtest_check-%j.out
#SBATCH -e /work/ymj1123ntu/logs/v9_oldtest_check-%j.err
set -uo pipefail
REPO=/work/ymj1123ntu/gfm-classifier
module load miniconda3/26.1.1
source "$(conda info --base)/etc/profile.d/conda.sh"; conda activate gfm
export PYTHONUNBUFFERED=1
cd ${REPO}/scripts
echo "### v9 on OLD leaky 100K test (expect ~66.6% if eval script is correct) ###"
python -u run_nt_genus_test100k.py \
  --config       ${REPO}/configs/nt_token_genus_v9_50M.yaml \
  --checkpoint   /work/ymj1123ntu/checkpoints/nt_token_genus_v9_50M_best.pt \
  --test_fasta   /work/ymj1123ntu/data/reads_100K.fa \
  --test_labels  /work/ymj1123ntu/data/labels_100K.tsv \
  --train_labels /work/ymj1123ntu/data/labels_50M.tsv \
  --out_dir      /work/ymj1123ntu/checkpoints/v9_oldtest_check \
  --batch_size   512 2>&1
echo "=== Done $(date) ==="
