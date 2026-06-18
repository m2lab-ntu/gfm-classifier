#!/bin/bash
#SBATCH -A MST114414
#SBATCH -J nt_genus_v15_250M
#SBATCH -p 64gpus
#SBATCH --nodes=8
#SBATCH --ntasks-per-node=8
#SBATCH --gres=gpu:8
#SBATCH --cpus-per-task=8
#SBATCH --mem=0
#SBATCH -t 24:00:00
#SBATCH --exclude=25a-hgpn125
#SBATCH -o /work/ymj1123ntu/logs/nt_genus_v15_250M-%j.out
#SBATCH -e /work/ymj1123ntu/logs/nt_genus_v15_250M-%j.err

# ============================================================
# NT-v2 Genus 250M BALANCED — Nano4 H200 DDP (v15)
# Warm-start from v9 best.pt (66.60% on 50M)
#
# 8 nodes × 8 H200 = 64 GPUs · effective batch 8192
# Data: same balanced_250M as v14 (correct 1535sp source)
# LR: 3e-5/2e-6 (10× lower than v14) — v12 proved 3e-4 collapses
#
# Pre-requisite: reads_250M.idx.npy must exist (built by
# run_prebuild_index_250M.sh). Index already built for v14.
#
# Auto-resume from last.pt on resubmit;
# init_from v9 only on first run.
# ============================================================

set -uo pipefail

REPO=/work/ymj1123ntu/gfm-classifier
SCRIPTS=${REPO}/scripts
CONFIG=${REPO}/configs/nt_token_genus_v15_250M_warmstart.yaml
CKPT_DIR=/work/ymj1123ntu/checkpoints/nt_token_genus_v15_250M_warmstart
V9_BEST=/work/ymj1123ntu/checkpoints/nt_token_genus_v9_50M_best.pt
LOG_DIR=/work/ymj1123ntu/logs

mkdir -p ${CKPT_DIR} ${LOG_DIR}

echo "================================================================"
echo "NT-v2 Genus 250M BALANCED DDP — Nano4 H200 (v15, warm-start)"
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

# ── Sanity: index must be pre-built ──────────────────────────────────────────
IDX=/work/ymj1123ntu/data/balanced_250M/reads_250M.idx.npy
if [ ! -f "${IDX}" ]; then
    echo "ERROR: ${IDX} missing. Run slurm/run_prebuild_index_250M.sh first."
    exit 1
fi
echo "Index present: $(ls -la ${IDX})"

# ── Determine master node ────────────────────────────────────────────────────
export MASTER_ADDR=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -1)
export MASTER_PORT=29501

echo "Master: ${MASTER_ADDR}:${MASTER_PORT}"
echo "World size: $((SLURM_NNODES * 8)) (${SLURM_NNODES} nodes × 8 GPUs)"
echo ""
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1
echo ""

# ── Determine resume vs warm-start vs scratch ────────────────────────────────
LAST_PT=${CKPT_DIR}/last.pt
if [ -f "${LAST_PT}" ]; then
    EPOCH=$(python3 -c "import torch; c=torch.load('${LAST_PT}',map_location='cpu',weights_only=False); print(c.get('epoch',0))" 2>/dev/null || echo "0")
    echo "=== Resuming from ${LAST_PT} (epoch ${EPOCH}/15) ==="
    RESUME_FLAG="--resume ${LAST_PT}"
elif [ -f "${V9_BEST}" ]; then
    echo "=== Warm start from v9 best.pt (LR=3e-5/2e-6, epoch resets to 0) ==="
    RESUME_FLAG="--init_from ${V9_BEST}"
else
    echo "ERROR: v9 best.pt not found at ${V9_BEST}"
    exit 1
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
    echo "Progress: epoch ${FINAL_EPOCH}/15  val_acc=${FINAL_ACC}"
    if [ "${FINAL_EPOCH}" -ge "15" ]; then
        echo ">>> Training COMPLETE — run eval next"
    else
        echo ">>> Resubmit: sbatch slurm/run_nt_genus_v15_250M_ddp_nano4.sh"
    fi
fi
echo "================================================================"
