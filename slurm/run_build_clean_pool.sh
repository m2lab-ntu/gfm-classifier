#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J build_clean_pool
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH -t 04:00:00
#SBATCH -o /work/ymj1123ntu/logs/build_clean_pool-%j.out
#SBATCH -e /work/ymj1123ntu/logs/build_clean_pool-%j.err
# Common clean ~6M pool for cross-setting sample-level abundance tests.
# Excludes the UNION of reads_50M + balanced_250M training seq_ids. GPU only
# for the dev QOSMinGRES rule (CPU/IO job).
set -euo pipefail
module load miniconda3/26.1.1 2>/dev/null || true
source "$(conda info --base)/etc/profile.d/conda.sh"; conda activate gfm
export PYTHONUNBUFFERED=1
echo "=== build clean pool  Job $SLURM_JOB_ID  $(date) ==="
python3 /work/ymj1123ntu/gfm-classifier/scripts/build_clean_pool.py \
    --source_fa     /work/ymj1123ntu/data/labeled_multi_level_1535sp/reads.fa \
    --train_labels  /work/ymj1123ntu/data/labels_50M.tsv,/work/ymj1123ntu/data/balanced_250M/labels_250M.tsv \
    --out_dir       /work/ymj1123ntu/data/clean_pool_5M \
    --n_pool 6000000 --seed 1234
echo "=== done $(date) ==="
du -sh /work/ymj1123ntu/data/clean_pool_5M/reads.fa 2>/dev/null
wc -l /work/ymj1123ntu/data/clean_pool_5M/labels.tsv 2>/dev/null
