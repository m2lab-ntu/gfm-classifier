#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J mt_250M_train
#SBATCH -p 8gpus
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH -t 2-00:00:00
#SBATCH -o /work/ymj1123ntu/logs/mt_250M_train-%j.out
#SBATCH -e /work/ymj1123ntu/logs/mt_250M_train-%j.err

# MetaTransformer 13-mer stride1 GENUS on the correct 250M (single GPU, no DDP).
# max_steps=1.5M (~12 epochs over 250M); early-stopping is the real governor.
# Resume-capable: on resubmit, continues from the existing experiment dir.
set -uo pipefail
MT_SRC=/work/ymj1123ntu/MetaTransformer/src
EXP_BASE=/work/ymj1123ntu/mt_250M/experiments
NAME=mt_13mer_s1_genus_250M
CFG=/work/ymj1123ntu/mt_250M/config/config_13mer_s1_genus_250M.yaml

module load miniconda3/26.1.1
source $(conda info --base)/etc/profile.d/conda.sh; conda activate gfm
export PYTHONUNBUFFERED=1

echo "=== MT-250M train  Job $SLURM_JOB_ID  $(date)  $(hostname) ==="
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1
cd ${MT_SRC}

# Auto-resume: reuse the newest existing experiment dir that has a checkpoint.
EXISTING=$(ls -dt ${EXP_BASE}/${NAME}_* 2>/dev/null | head -1 || true)
if [ -n "${EXISTING:-}" ] && compgen -G "${EXISTING}/checkpoints/*.pt" >/dev/null; then
    echo "=== Resuming from ${EXISTING} ==="
    PYTHONPATH=${MT_SRC} python3 train.py resume_dir=${EXISTING} 2>&1
else
    echo "=== Fresh start ==="
    PYTHONPATH=${MT_SRC} python3 train.py \
        experiment_name=${NAME} \
        experiment_base_dir=${EXP_BASE} \
        cfg_path=${CFG} \
        data_path_root=/work/ymj1123ntu/ \
        resume_dir= 2>&1
fi
echo "=== exit=$?  $(date) ==="
