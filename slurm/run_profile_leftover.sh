#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J profile_leftover
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH -t 02:00:00
#SBATCH -o /work/ymj1123ntu/logs/profile_leftover-%j.out
#SBATCH -e /work/ymj1123ntu/logs/profile_leftover-%j.err

# Quantify how many source reads remain unused per class after balanced_250M,
# to decide whether a clean held-out test set can be sampled from the leftovers.
set -euo pipefail

SRC=/work/ymj1123ntu/data/labeled_multi_level_1535sp/reads.fa
IDX=/work/ymj1123ntu/data/balanced_250M/reads_250M.idx.npy
OUTDIR=/work/ymj1123ntu/data/leftover_coverage
REPO=/work/ymj1123ntu/gfm-classifier

mkdir -p "${OUTDIR}"

echo "=== Start: $(date) on $(hostname) ==="

module load miniconda3/26.1.1
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate gfm
export PYTHONUNBUFFERED=1

# ── Pass 1: per-(genus,species) source totals via single awk pass ───────────
# header = >lbl|<sp_class>|<sp_name>|<gen_class>|<gen_name>-<n>
#   split by '|':  $2=species_class  $4=genus_class
# awk associative array holds only ~1535 keys → tiny memory, one sequential scan.
SRCCOUNTS="${OUTDIR}/src_counts.tsv"
echo "--- counting source headers ($(date)) ---"
awk -F'|' '/^>/{c[$4"\t"$2]++} END{for(k in c) print k"\t"c[k]}' "${SRC}" > "${SRCCOUNTS}"
echo "source (genus,species) pairs: $(wc -l < "${SRCCOUNTS}")"

# ── Pass 2: merge with 250M usage, compute leftover, summarise ──────────────
echo "--- profiling leftover ($(date)) ---"
cd "${REPO}/scripts"
python -u profile_leftover_coverage.py \
    --src_counts "${SRCCOUNTS}" \
    --idx        "${IDX}" \
    --out_prefix "${OUTDIR}/coverage"

echo "=== Done: $(date) ==="
ls -la "${OUTDIR}"
