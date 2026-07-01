#!/bin/bash
#SBATCH -A <TWCC_ACCOUNT>            # <-- Taiwania-2 計畫編號 (TWCC 帳號)
#SBATCH -J dnabert2_50M
#SBATCH -p <TWCC_GPU_PARTITION>      # <-- Taiwania-2 GPU partition (e.g. gp4d)
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH -t 2-00:00:00               # 2-day walltime: enough for the whole tail in ONE job
#SBATCH -o /work/ymj1123ntu/logs/dnabert2_50M_twcc-%j.out
#SBATCH -e /work/ymj1123ntu/logs/dnabert2_50M_twcc-%j.err

# ============================================================
# DNABERT-2 Genus 50M — Taiwania-2 (SINGLE LONG JOB, no resume chain)
#
# WHY single long job:
#   On Nano4 the per-job walltime (4h) ≈ one epoch (~3.3h) + 50M-read load.
#   That created a checkpoint-persistence RACE: a job could finish an epoch
#   (write training_history.csv) yet be killed by Slurm before persisting
#   last.pt, so the next job re-ran the SAME epoch → looked stuck on "Epoch 18".
#   The epoch bookkeeping in train.py is CORRECT (verified: last.pt.epoch ==
#   completed-epoch count; resume advances properly). The fix is purely
#   operational: give the job enough walltime to bank many end-of-epoch saves.
#
# STARTING POINT: resumes from last.pt @ epoch 17, val_acc ~59.2% (already
#   plateauing +0.1pp/epoch). Expect early-stop around ep22-25, val ~60%.
#
# time_limit_sec set BELOW walltime so it exits gracefully (banks last.pt) if
# it ever needs a 2nd submission — but 2 days should reach early-stop first.
# Adjust -A / -p / -t to Taiwania-2's valid values before submitting.
# ============================================================

set -euo pipefail

REPO=/work/ymj1123ntu/gfm-classifier
DATA=/work/ymj1123ntu/data
CKPT_DIR=/work/ymj1123ntu/checkpoints/dnabert2_token_genus_50M
CONFIG=${REPO}/configs/dnabert2_token_genus_50M.yaml
LOG_DIR=/work/ymj1123ntu/logs

mkdir -p ${LOG_DIR} ${CKPT_DIR}

echo "========================================"
echo "DNABERT-2 Genus 50M — Taiwania-2 (single long job)"
echo "Start: $(date) | Host: $(hostname)"
echo "========================================"
nvidia-smi || true
echo ""

# --- environment (adjust module name to Taiwania-2's conda module) ---
module load miniconda3 2>/dev/null || module load miniconda3/26.1.1 2>/dev/null || true
source $(conda info --base)/etc/profile.d/conda.sh
conda activate gfm

export HF_HOME=/work/ymj1123ntu/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface
export TRANSFORMERS_CACHE=/work/ymj1123ntu/.cache/huggingface
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export OMP_NUM_THREADS=8
export PYTHONUNBUFFERED=1

HISTORY=${CKPT_DIR}/training_history.csv
if [ -f "$HISTORY" ]; then
    LAST_EPOCH=$(tail -1 "$HISTORY" | cut -d',' -f1)
    echo "Resuming from epoch ${LAST_EPOCH}/30 (checkpoint: ${CKPT_DIR}/last.pt)"
fi

# --- config: patch data + output paths for the target filesystem ---
cp ${CONFIG} /tmp/dnabert2_twcc.yaml
sed -i "s|/work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M/reads_50M.fa|${DATA}/reads_50M.fa|g" /tmp/dnabert2_twcc.yaml
sed -i "s|/work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M/labels_50M.tsv|${DATA}/labels_50M.tsv|g" /tmp/dnabert2_twcc.yaml
sed -i "s|dir: .*dnabert2_token_genus_50M|dir: ${CKPT_DIR}|g" /tmp/dnabert2_twcc.yaml

cd ${REPO}/scripts

# time_limit_sec = walltime(2d=172800s) - 2h margin for the final save
TLIMIT=165600

if [ -f "${CKPT_DIR}/last.pt" ]; then
    echo "=== Resuming training from ${CKPT_DIR}/last.pt (one long job) ==="
    python -u train.py --config /tmp/dnabert2_twcc.yaml \
        --resume "${CKPT_DIR}/last.pt" --time_limit_sec ${TLIMIT} 2>&1
else
    echo "=== Starting training from scratch ==="
    python -u train.py --config /tmp/dnabert2_twcc.yaml \
        --time_limit_sec ${TLIMIT} 2>&1
fi

echo ""
echo "========================================"
echo "Done: $(date)"
if [ -f "$HISTORY" ]; then
    CURRENT_EPOCH=$(tail -1 "$HISTORY" | cut -d',' -f1)
    echo "Progress: epoch ${CURRENT_EPOCH}/30"
    if [ "$CURRENT_EPOCH" -ge "30" ]; then
        echo ">>> COMPLETE (or early-stopped). Run genus eval next (see taiwania2_continue/README.md)."
    else
        echo ">>> Not done — resubmit this same script; it resumes cleanly from last.pt."
    fi
fi
echo "========================================"
