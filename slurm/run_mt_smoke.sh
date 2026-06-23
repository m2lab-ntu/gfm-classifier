#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J mt_smoke
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH -t 00:30:00
#SBATCH -o /work/ymj1123ntu/logs/mt_smoke-%j.out
#SBATCH -e /work/ymj1123ntu/logs/mt_smoke-%j.err

# Smoke test: does MetaTransformer training run end-to-end on Nano4?
# 13-mer stride1 genus recipe, tiny data (~180k/20k), 60 steps, eval@30.
set -uo pipefail
MT_SRC=/work/ymj1123ntu/MetaTransformer/src

module load miniconda3/26.1.1
source $(conda info --base)/etc/profile.d/conda.sh
conda activate gfm
export PYTHONUNBUFFERED=1

echo "=== MT smoke  Job $SLURM_JOB_ID  $(date)  $(hostname) ==="
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1

cd ${MT_SRC}
PYTHONPATH=${MT_SRC} python3 train.py \
    experiment_name=mt_smoke \
    experiment_base_dir=/work/ymj1123ntu/mt_250M/experiments \
    cfg_path=/work/ymj1123ntu/mt_250M/config/config_13mer_s1_genus_smoke.yaml \
    data_path_root=/work/ymj1123ntu/ \
    resume_dir= 2>&1

echo "=== smoke exit=$?  $(date) ==="
