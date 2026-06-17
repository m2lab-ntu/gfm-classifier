#!/bin/bash
#SBATCH -A MST114414
#SBATCH -J nt_genus_v14_250M
#SBATCH -p 64gpus
#SBATCH --nodes=8
#SBATCH --ntasks-per-node=8
#SBATCH --gres=gpu:8
#SBATCH --cpus-per-task=8
#SBATCH --mem=0
#SBATCH -t 24:00:00
#SBATCH --exclude=25a-hgpn125
#SBATCH -o /work/ymj1123ntu/logs/nt_genus_v14_250M-%j.out
#SBATCH -e /work/ymj1123ntu/logs/nt_genus_v14_250M-%j.err

# ============================================================
# NT-v2 Genus 250M BALANCED — Nano4 H200 DDP (v14)
#
# 8 nodes × 8 H200 = 64 GPUs · effective batch 8192
# Data: 250M species-balanced from CORRECT 1535sp source.
# From scratch, class_weights=false (v9 recipe at 5× scale).
#
# Pre-requisite: reads_250M.idx.npy must exist (built by
# run_prebuild_index_250M.sh). Submit with:
#   IDXJOB=$(sbatch --parsable slurm/run_prebuild_index_250M.sh)
#   sbatch --dependency=afterok:${IDXJOB} slurm/run_nt_genus_v14_250M_ddp_nano4.sh
#
# Auto-resume from last.pt on resubmit.
# ============================================================

set -uo pipefail

REPO=/work/ymj1123ntu/gfm-classifier
SCRIPTS=${REPO}/scripts
CONFIG=${REPO}/configs/nt_token_genus_v14_250M_balanced.yaml
CKPT_DIR=/work/ymj1123ntu/checkpoints/nt_token_genus_v14_250M_balanced
LOG_DIR=/work/ymj1123ntu/logs

mkdir -p ${CKPT_DIR} ${LOG_DIR}

echo "================================================================"
echo "NT-v2 Genus 250M BALANCED DDP — Nano4 H200 (v14)"
echo "Job ID:   $SLURM_JOB_ID"
echo "Nodes:    $SLURM_NNODES  ($(scontrol show hostnames $SLURM_JOB_NODELIST | tr '\n' ' '))"
echo "Start:    $(date)"
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

cd ${SCRIPTS}

# ── Sanity: index must be pre-built (avoid 64-rank build race) ───────────────
IDX=/work/ymj1123ntu/data/balanced_250M/reads_250M.idx.npy
if [ ! -f "${IDX}" ]; then
    echo "ERROR: ${IDX} missing. Run slurm/run_prebuild_index_250M.sh first."
    exit 1
fi
echo "Index present: $(ls -la ${IDX})"

# ── Determine master node ────────────────────────────────────────────────────
export MASTER_ADDR=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -1)
export MASTER_PORT=29500

echo "Master: ${MASTER_ADDR}:${MASTER_PORT}"
echo "World size: $((SLURM_NNODES * 8)) (${SLURM_NNODES} nodes × 8 GPUs)"
echo ""
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1
echo ""

# ── Determine resume vs fresh start ─────────────────────────────────────────
LAST_PT=${CKPT_DIR}/last.pt
if [ -f "${LAST_PT}" ]; then
    EPOCH=$(python3 -c "import torch; c=torch.load('${LAST_PT}',map_location='cpu',weights_only=False); print(c.get('epoch',0))" 2>/dev/null || echo "0")
    echo "=== Resuming from ${LAST_PT} (epoch ${EPOCH}/25) ==="
    RESUME_FLAG="--resume ${LAST_PT}"
else
    echo "=== Starting from scratch (v9 balanced recipe) ==="
    RESUME_FLAG=""
fi

# ── Launch DDP training ──────────────────────────────────────────────────────
srun python train_ddp.py \
        --config ${CONFIG} \
        ${RESUME_FLAG} \
        --time_limit_sec 82800 \
    2>&1

# ── Post-training report ─────────────────────────────────────────────────────
echo ""
echo "================================================================"
echo "Job done: $(date)"
if [ -f "${CKPT_DIR}/training_history.csv" ]; then
    FINAL_EPOCH=$(tail -1 "${CKPT_DIR}/training_history.csv" | cut -d',' -f1)
    FINAL_ACC=$(tail  -1 "${CKPT_DIR}/training_history.csv" | cut -d',' -f5)
    echo "Progress: epoch ${FINAL_EPOCH}/25  val_acc=${FINAL_ACC}"
    if [ "${FINAL_EPOCH}" -ge "25" ]; then
        echo ">>> Training COMPLETE — run eval next"
    else
        echo ">>> Resubmit: sbatch slurm/run_nt_genus_v14_250M_ddp_nano4.sh"
    fi
fi
echo "================================================================"
