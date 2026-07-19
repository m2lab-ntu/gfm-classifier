#!/bin/bash
#SBATCH --account=MST114414
#SBATCH --job-name=mt50m_soil_6mer_e128
#SBATCH --partition=gp2d
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=90G
#SBATCH --gres=gpu:1
#SBATCH --time=1-00:00:00
#SBATCH --output=/work/ymj1123ntu/mt50m_soil/logs/%x_%j.out
#SBATCH --error=/work/ymj1123ntu/mt50m_soil/logs/%x_%j.err

# MT 6-mer soil 50M — tokenization CONTROL for MT-13mer-50M (0.892).
# Identical config except kmer_size=6 (+ vocab_6mer). Same 50M shards, stride 1,
# embed 64, num_classes 500, class_indices 1, sparse_embedding true.
# Tiny 6-mer vocab -> fast; completes in a few hours (early-stop), well within 24h.

source /home/ymj1123ntu/.bashrc
eval "$(conda shell.bash hook)"
conda activate MetaTransformer

cd /home/ymj1123ntu/MetaTransformer/src
EXP_BASE=/work/ymj1123ntu/mt50m_soil/experiments
# resume glob is 6mer-specific so it never picks up the 13mer experiment's checkpoints
LAST=$(ls -td ${EXP_BASE}/genus_50M_soil_6mer_e128_*/checkpoints/*_ckpt_bt_*.pt 2>/dev/null | head -1)
RESUME_DIR=""
if [ -n "${LAST}" ]; then RESUME_DIR=$(dirname "$(dirname "${LAST}")"); echo "Resuming: ${RESUME_DIR}"; fi

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1
echo "MT-50M-6mer soil genus training started at: $(date)"

if [ -n "${RESUME_DIR}" ]; then
    python3 -u train.py resume_dir=${RESUME_DIR}
else
    python3 -u train.py \
        experiment_name=genus_50M_soil_6mer_e128 \
        experiment_base_dir=${EXP_BASE} \
        cfg_path=/work/ymj1123ntu/mt50m_soil/config/config_genus_50M_soil_6mer_e128.yaml \
        data_path_root=/work/ymj1123ntu/mt50m_soil \
        resume_dir=
fi
echo "MT-50M-6mer soil genus training finished at: $(date)"
