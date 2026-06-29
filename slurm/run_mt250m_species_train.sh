#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J mt250m_species
#SBATCH -p 8gpus
#SBATCH --nodes=1 --ntasks-per-node=1 --gres=gpu:1 --cpus-per-task=12 --mem=128G
#SBATCH -t 2-00:00:00 --requeue
#SBATCH -o /work/ymj1123ntu/logs/mt250m_species-%j.out
#SBATCH -e /work/ymj1123ntu/logs/mt250m_species-%j.err
# MT 13-mer s1 SPECIES @250M (single GPU like genus run). Does 13-mer scaling hold at species?
set -uo pipefail
MT_SRC=/work/ymj1123ntu/MetaTransformer/src
EXP_BASE=/work/ymj1123ntu/mt_250M/experiments
NAME=mt_13mer_s1_species_250M
CFG=/work/ymj1123ntu/mt_250M/config/config_13mer_s1_species_250M.yaml
module load miniconda3/26.1.1; source $(conda info --base)/etc/profile.d/conda.sh; conda activate gfm
export PYTHONUNBUFFERED=1
echo "=== MT-250M SPECIES  Job $SLURM_JOB_ID  $(date)  $(hostname) ==="
cd ${MT_SRC}
EXISTING=$(ls -dt ${EXP_BASE}/${NAME}_* 2>/dev/null | head -1 || true)
if [ -n "${EXISTING:-}" ] && compgen -G "${EXISTING}/checkpoints/*.pt" >/dev/null; then
    echo "=== Resuming from ${EXISTING} ==="; PYTHONPATH=${MT_SRC} python3 train.py resume_dir=${EXISTING} 2>&1
else
    echo "=== Fresh ==="; PYTHONPATH=${MT_SRC} python3 train.py experiment_name=${NAME} \
       experiment_base_dir=${EXP_BASE} cfg_path=${CFG} data_path_root=/work/ymj1123ntu/ resume_dir= 2>&1
fi
echo "=== exit=$? $(date) ==="
