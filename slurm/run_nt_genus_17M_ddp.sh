#!/bin/bash
#SBATCH -A MST114414
#SBATCH -J nt_genus_17M
#SBATCH -p 8gpus
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=8
#SBATCH --gres=gpu:8
#SBATCH --cpus-per-task=8
#SBATCH --mem=0
#SBATCH -t 24:00:00
#SBATCH -o /work/ymj1123ntu/logs/nt_genus_17M-%j.out
#SBATCH -e /work/ymj1123ntu/logs/nt_genus_17M-%j.err

# ============================================================
# NT-v2 Genus, 17.64M — genus-balanced vs species-balanced.
#   Usage: sbatch run_nt_genus_17M_ddp.sh <gbal|sbal>
# 1 node × 8 H200 (effective batch 2048). From scratch, identical
# config except the balance axis. Auto-resume from last.pt.
# Index must be prebuilt by run_subsample_17M.sh (single process).
# ============================================================
set -uo pipefail

MODE="${1:?usage: sbatch run_nt_genus_17M_ddp.sh <gbal|sbal>}"
REPO=/work/ymj1123ntu/gfm-classifier
SCRIPTS=${REPO}/scripts

case "${MODE}" in
  gbal) CONFIG=${REPO}/configs/nt_token_genus_gbal_17M.yaml
        CKPT_DIR=/work/ymj1123ntu/checkpoints/nt_token_genus_gbal_17M
        IDX=/work/ymj1123ntu/data/balanced_genus_17M/reads.idx.npy ;;
  sbal) CONFIG=${REPO}/configs/nt_token_genus_sbal_17M.yaml
        CKPT_DIR=/work/ymj1123ntu/checkpoints/nt_token_genus_sbal_17M
        IDX=/work/ymj1123ntu/data/balanced_species_17M/reads.idx.npy ;;
  *) echo "MODE must be gbal|sbal"; exit 1 ;;
esac

mkdir -p ${CKPT_DIR} /work/ymj1123ntu/logs

echo "================================================================"
echo "NT-v2 Genus 17.64M  mode=${MODE}  Job ${SLURM_JOB_ID}"
echo "Nodes: $SLURM_NNODES  Config: ${CONFIG}  Start: $(date)"
echo "================================================================"

module load miniconda3/26.1.1
source $(conda info --base)/etc/profile.d/conda.sh
conda activate gfm
export HF_HOME=/work/ymj1123ntu/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface
export TRANSFORMERS_CACHE=/work/ymj1123ntu/.cache/huggingface
export OMP_NUM_THREADS=8
export PYTHONUNBUFFERED=1
export NCCL_DEBUG=WARN

if [ ! -f "${IDX}" ]; then
    echo "ERROR: ${IDX} missing. Run run_subsample_17M.sh ${MODE/gbal/genus} first."; exit 1
fi
echo "Index present: $(ls -la ${IDX})"

export MASTER_ADDR=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -1)
export MASTER_PORT=29501
echo "Master: ${MASTER_ADDR}:${MASTER_PORT}  World size: $((SLURM_NNODES * 8))"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1

cd ${SCRIPTS}
LAST_PT=${CKPT_DIR}/last.pt
if [ -f "${LAST_PT}" ]; then
    EPOCH=$(python3 -c "import torch;c=torch.load('${LAST_PT}',map_location='cpu',weights_only=False);print(c.get('epoch',0))" 2>/dev/null || echo 0)
    echo "=== Resuming from ${LAST_PT} (epoch ${EPOCH}) ==="
    RESUME_FLAG="--resume ${LAST_PT}"
else
    echo "=== Starting from scratch ==="
    RESUME_FLAG=""
fi

srun python train_ddp.py --config ${CONFIG} ${RESUME_FLAG} --time_limit_sec 82800 2>&1

echo ""
echo "Job done: $(date)"
if [ -f "${CKPT_DIR}/training_history.csv" ]; then
    tail -1 "${CKPT_DIR}/training_history.csv" | awk -F',' '{print "Final: epoch "$1"  val_acc="$5}'
fi
