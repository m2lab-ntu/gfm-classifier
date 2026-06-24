#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J mt_split_250M
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH -t 04:00:00
#SBATCH -o /work/ymj1123ntu/logs/mt_split_250M-%j.out
#SBATCH -e /work/ymj1123ntu/logs/mt_split_250M-%j.err

# Split the correct species-balanced 250M into MT train/val .fa dirs (90/10,
# single file each), headers already MT-compatible (genus at field 3).
# GPU only for the dev QOSMinGRES rule (CPU/IO job).
set -euo pipefail
module load miniconda3/26.1.1 2>/dev/null || true
source "$(conda info --base)/etc/profile.d/conda.sh"; conda activate gfm
export PYTHONUNBUFFERED=1

echo "=== MT 250M split  Job $SLURM_JOB_ID  $(date) ==="
python3 /work/ymj1123ntu/MetaTransformer/myScript/fasta_split_streaming.py \
    --input    /work/ymj1123ntu/data/balanced_250M/reads_250M.fa \
    --train_out /work/ymj1123ntu/mt_250M_train_genus/train.fa \
    --val_out   /work/ymj1123ntu/mt_250M_val_genus/val.fa \
    --train_ratio 0.9 --seed 42
echo "=== Done $(date) ==="
du -sh /work/ymj1123ntu/mt_250M_train_genus/train.fa /work/ymj1123ntu/mt_250M_val_genus/val.fa
