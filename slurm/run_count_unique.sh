#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J count_uniq
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1 --ntasks-per-node=1 --cpus-per-task=8 --mem=96G
#SBATCH -t 04:00:00
#SBATCH -o /work/ymj1123ntu/logs/count_uniq-%j.out
#SBATCH -e /work/ymj1123ntu/logs/count_uniq-%j.err
set -euo pipefail
module load miniconda3/26.1.1 2>/dev/null || true
source "$(conda info --base)/etc/profile.d/conda.sh"; conda activate gfm
export PYTHONUNBUFFERED=1
echo "=== count unique seq_ids  Job $SLURM_JOB_ID  $(date) ==="
python3 /work/ymj1123ntu/gfm-classifier/scripts/count_unique_seqids.py \
    /work/ymj1123ntu/data/labels_50M.tsv \
    /work/ymj1123ntu/data/balanced_250M/labels_250M.tsv \
    /work/ymj1123ntu/data/labeled_multi_level_1535sp/reads.fa
echo "=== done $(date) ==="
