#!/bin/bash
#SBATCH -A MST114414
#SBATCH -J prebuild_idx_250M
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH -t 03:00:00
#SBATCH -o /work/ymj1123ntu/logs/prebuild_idx_250M-%j.out
#SBATCH -e /work/ymj1123ntu/logs/prebuild_idx_250M-%j.err

# ============================================================
# Pre-build the LazyFASTADataset index for balanced_250M.
#
# Why a separate job: train_ddp instantiates the dataset on all
# 64 ranks concurrently; for a brand-new index that races on the
# same .idx.npy write. Build it once here (single process) so the
# DDP job loads it from cache. v14 is submitted with
# --dependency=afterok on this job.
# ============================================================

set -euo pipefail

REPO=/work/ymj1123ntu/gfm-classifier
FASTA=/work/ymj1123ntu/data/balanced_250M/reads_250M.fa
IDX=/work/ymj1123ntu/data/balanced_250M/reads_250M.idx.npy

mkdir -p /work/ymj1123ntu/logs

module load miniconda3/26.1.1 2>/dev/null || true
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate gfm
export PYTHONUNBUFFERED=1

echo "=== Pre-building index: $(date) on $(hostname) ==="
cd "${REPO}/scripts"
python -c "
from dataset_lazy import LazyFASTADataset
from pathlib import Path
LazyFASTADataset._build_index('${FASTA}', Path('${IDX}'))
"
echo "=== Done: $(date) ==="
ls -la "${IDX}"
