#!/bin/bash
#SBATCH -A MST114414
#SBATCH -J subsample_250M
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH -t 04:00:00
#SBATCH -o /work/ymj1123ntu/logs/subsample_250M-%j.out
#SBATCH -e /work/ymj1123ntu/logs/subsample_250M-%j.err

# ============================================================
# 250M species-balanced subsample from the 1535-species source.
#
# NOTE: job 118820 OOM-killed (reservoir held all reads in RAM,
# 250M reads ≈ 100+ GB >> 32G). subsample_balanced.py Pass 2 was
# rewritten to a memory-light streaming writer (~260 MB masks);
# 64G here is generous headroom. GPU requested only to satisfy
# the dev-partition QOSMinGRES rule — the job is CPU/IO bound.
# ============================================================

set -euo pipefail

REPO=/work/ymj1123ntu/gfm-classifier
SRC=/work/ymj1123ntu/data/labeled_multi_level_1535sp/reads.fa
OUT_DIR=/work/ymj1123ntu/data/balanced_250M

mkdir -p "${OUT_DIR}" /work/ymj1123ntu/logs

module load miniconda3/26.1.1 2>/dev/null || true
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate gfm

export PYTHONUNBUFFERED=1

echo "================================================================"
echo "250M balanced subsample"
echo "Job ID: $SLURM_JOB_ID  Node: $(hostname)  Start: $(date)"
echo "================================================================"

cd "${REPO}/scripts"
python -u subsample_balanced.py \
    --input        "${SRC}" \
    --output_fasta "${OUT_DIR}/reads_250M.fa" \
    --output_labels "${OUT_DIR}/labels_250M.tsv" \
    --total_reads  250000000 \
    --balance_by   species \
    --seed         42

echo "================================================================"
echo "Done: $(date)"
echo "FASTA:  $(du -sh ${OUT_DIR}/reads_250M.fa 2>/dev/null | cut -f1)"
echo "Labels: $(wc -l < ${OUT_DIR}/labels_250M.tsv 2>/dev/null) lines"
echo "================================================================"
