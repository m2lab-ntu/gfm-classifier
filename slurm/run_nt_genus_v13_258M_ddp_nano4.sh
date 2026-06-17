#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J nt_genus_v13_258M
#SBATCH -p 64gpus
#SBATCH --nodes=8
#SBATCH --ntasks-per-node=8
#SBATCH --gres=gpu:8
#SBATCH --cpus-per-task=8
#SBATCH --mem=0
#SBATCH -t 24:00:00
#SBATCH --exclude=25a-hgpn125
#SBATCH -o /work/ymj1123ntu/logs/nt_genus_v13_258M-%j.out
#SBATCH -e /work/ymj1123ntu/logs/nt_genus_v13_258M-%j.err

# ============================================================
# NT-v2 Genus 258M — Nano4 H200 DDP (normal partition)
#
# 8 nodes × 8 H200 = 64 GPUs
# Effective batch = 128 × 64 = 8192
# Estimated: ~5-7 hr for 15 epochs (vs 84+ hr single-GPU)
#
# Pre-requisites:
#   1. reads_258M.fa  at /work/ymj1123ntu/data/reads_258M.fa
#   2. labels_258M.tsv at /work/ymj1123ntu/data/labels_258M.tsv
#      (generate via: python scripts/generate_labels_258M.py)
#   3. FASTA index (.idx.npy) — built on first run, ~3-5 min
#   4. v9 best.pt at /work/ymj1123ntu/checkpoints/nt_token_genus_v9_50M_best.pt
#      (for --init_from warm start)
#   5. conda env gfm with all deps
#
# Auto-resume: add --resume last.pt if continuing from checkpoint
# ============================================================

set -uo pipefail

REPO=/work/ymj1123ntu/gfm-classifier
SCRIPTS=${REPO}/scripts
CONFIG=${REPO}/configs/nt_token_genus_v13_258M_scratch.yaml
CKPT_DIR=/work/ymj1123ntu/checkpoints/nt_token_genus_v13_258M_scratch
V9_BEST=""  # v13: force from-scratch, no warm-start
LOG_DIR=/work/ymj1123ntu/logs

mkdir -p ${CKPT_DIR} ${LOG_DIR}

echo "================================================================"
echo "NT-v2 Genus 258M DDP — Nano4 H200 (normal partition)"
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
    echo "=== Resuming from ${LAST_PT} (epoch ${EPOCH}/15) ==="
    RESUME_FLAG="--resume ${LAST_PT}"
elif [ -f "${V9_BEST}" ]; then
    echo "=== Warm start from v9 best.pt (epoch resets to 0) ==="
    RESUME_FLAG="--init_from ${V9_BEST}"
else
    echo "=== Starting from scratch (no init checkpoint found) ==="
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
    echo "Progress: epoch ${FINAL_EPOCH}/15  val_acc=${FINAL_ACC}"
    if [ "${FINAL_EPOCH}" -ge "15" ]; then
        echo ">>> Training COMPLETE — run eval next"
        echo ">>> python scripts/evaluate.py --config ${CONFIG}"
    else
        echo ">>> Resubmit: sbatch slurm/run_nt_genus_v13_258M_ddp_nano4.sh"
    fi
fi
echo "================================================================"
