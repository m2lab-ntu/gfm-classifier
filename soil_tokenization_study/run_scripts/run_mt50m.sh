#!/bin/bash
#SBATCH --account=MST114414
#SBATCH --job-name=mt50m_soil_genus
#SBATCH --partition=gp2d
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=90G
#SBATCH --gres=gpu:1
#SBATCH --time=2-00:00:00
#SBATCH --output=/work/ymj1123ntu/mt50m_soil/logs/%x_%j.out
#SBATCH --error=/work/ymj1123ntu/mt50m_soil/logs/%x_%j.err

# MT 50M soil genus — clean data-volume scale-up of MT-5M.
# Multi-epoch is handled IN-PROCESS by the patched AbstractTrainer.train() via
# training.max_epochs, so no external resume-loop is needed and early-stopping
# works normally. --resume last.pt is kept only for timeout recovery.

source /home/ymj1123ntu/.bashrc
eval "$(conda shell.bash hook)"
conda activate MetaTransformer

# ~9-10h expected on V100 (gut 50M stride-1 anchor: 9h18m). Fits one 48h window.

cd /home/ymj1123ntu/MetaTransformer/src
EXP_BASE=/work/ymj1123ntu/mt50m_soil/experiments
LAST=$(ls -td ${EXP_BASE}/genus_50M_soil_*/checkpoints/*_ckpt_bt_*.pt 2>/dev/null | head -1)
RESUME_DIR=""
if [ -n "${LAST}" ]; then
    RESUME_DIR=$(dirname "$(dirname "${LAST}")")
    echo "Found prior checkpoint, will resume experiment dir: ${RESUME_DIR}"
fi

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1
echo "MT-50M soil genus training started at: $(date)"

if [ -n "${RESUME_DIR}" ]; then
    python3 -u train.py resume_dir=${RESUME_DIR}
else
    python3 -u train.py \
        experiment_name=genus_50M_soil \
        experiment_base_dir=${EXP_BASE} \
        cfg_path=/work/ymj1123ntu/mt50m_soil/config/config_genus_50M_soil.yaml \
        data_path_root=/work/ymj1123ntu/mt50m_soil \
        resume_dir=
fi

echo "MT-50M soil genus training finished at: $(date)"
