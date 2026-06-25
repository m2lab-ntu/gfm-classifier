#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J mt250m_6mer
#SBATCH -p 8gpus
#SBATCH --nodes=1 --ntasks-per-node=1 --gres=gpu:1 --cpus-per-task=16 --mem=128G
#SBATCH -t 2-00:00:00
#SBATCH -o /work/ymj1123ntu/logs/mt250m_6mer-%j.out
#SBATCH -e /work/ymj1123ntu/logs/mt250m_6mer-%j.err
# Control: MetaTransformer arch fixed (= 13-mer 250M run), only tokenizer -> 6-mer.
#   Usage: sbatch run_mt250m_6mer_train.sh <1|6>   (kmer stride)
set -uo pipefail
ST="${1:?usage: sbatch run_mt250m_6mer_train.sh <1|6>}"
MT_SRC=/work/ymj1123ntu/MetaTransformer/src
EXP_BASE=/work/ymj1123ntu/mt_250M/experiments
NAME=mt_6mer_s${ST}_genus_250M
CFG=/work/ymj1123ntu/mt_250M/config/config_6mer_s${ST}_genus_250M.yaml
module load miniconda3/26.1.1; source $(conda info --base)/etc/profile.d/conda.sh; conda activate gfm
export PYTHONUNBUFFERED=1
echo "=== MT-250M 6-mer s${ST}  Job $SLURM_JOB_ID  $(date)  $(hostname) ==="
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1
cd ${MT_SRC}
EXISTING=$(ls -dt ${EXP_BASE}/${NAME}_* 2>/dev/null | head -1 || true)
if [ -n "${EXISTING:-}" ] && compgen -G "${EXISTING}/checkpoints/*.pt" >/dev/null; then
    echo "=== Resuming from ${EXISTING} ==="
    PYTHONPATH=${MT_SRC} python3 train.py resume_dir=${EXISTING} 2>&1
else
    echo "=== Fresh start ==="
    PYTHONPATH=${MT_SRC} python3 train.py experiment_name=${NAME} \
        experiment_base_dir=${EXP_BASE} cfg_path=${CFG} \
        data_path_root=/work/ymj1123ntu/ resume_dir= 2>&1
fi
echo "=== exit=$?  $(date) ==="
