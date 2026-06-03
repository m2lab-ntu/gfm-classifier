#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J dnabert2_50M
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH -t 01:00:00
#SBATCH -o /work/ymj1123ntu/logs/dnabert2_50M-%j.out
#SBATCH -e /work/ymj1123ntu/logs/dnabert2_50M-%j.err

# ============================================================
# DNABERT-2 Genus 50M — Nano4 H200 (dev partition, 1-hr cap)
#
# Auto-resume pattern: each job resumes from last.pt; resubmit
# via: sbatch slurm/run_dnabert2_genus_50M.nano4.sh
# until training_history.csv shows epoch 30.
#
# Starting from epoch 17, val_acc ~59.2% (TWCC checkpoint).
# ~13 more epochs × ~2.8 hr/epoch H100 → ~5 hr H200 total
# → ~5-6 dev resubmits needed (H200 faster, estimate ~0.8-1 hr/epoch)
# ============================================================

set -euo pipefail

REPO=/work/ymj1123ntu/gfm-classifier
DATA=/work/ymj1123ntu/data
CKPT_DIR=/work/ymj1123ntu/checkpoints/dnabert2_token_genus_50M
CONFIG=${REPO}/configs/dnabert2_token_genus_50M.yaml
LOG_DIR=/work/ymj1123ntu/logs

mkdir -p ${LOG_DIR} ${CKPT_DIR}

echo "========================================"
echo "DNABERT-2 Genus 50M — Nano4 H200 (dev)"
echo "Start: $(date) | Host: $(hostname)"
echo "========================================"
nvidia-smi || true
echo ""

module load miniconda3/26.1.1
source $(conda info --base)/etc/profile.d/conda.sh
conda activate gfm

export HF_HOME=/work/ymj1123ntu/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface
export TRANSFORMERS_CACHE=/work/ymj1123ntu/.cache/huggingface
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export OMP_NUM_THREADS=8
export PYTHONUNBUFFERED=1

# Check current epoch before starting
HISTORY=${CKPT_DIR}/training_history.csv
if [ -f "$HISTORY" ]; then
    LAST_EPOCH=$(tail -1 "$HISTORY" | cut -d',' -f1)
    echo "Resuming from epoch ${LAST_EPOCH}/30 (checkpoint: ${CKPT_DIR}/last.pt)"
else
    LAST_EPOCH=0
    echo "No history found — starting fresh or first epoch"
fi

# ── Override config paths for Nano4 filesystem ───────────────────────────
# The yaml points to TWCC paths; override via --config_override or patch yaml
# Simplest: write a Nano4-specific config overlay
cat > /tmp/dnabert2_nano4_overlay.yaml << YAML_EOF
data:
  fasta_path: "${DATA}/reads_50M.fa"
  labels_path: "${DATA}/labels_50M.tsv"

output:
  dir: "${CKPT_DIR}"
YAML_EOF

# Merge base config with overlay (train.py supports --resume pointing to last.pt)
# If train.py doesn't support overlay, we patch the yaml directly in a temp copy
cp ${CONFIG} /tmp/dnabert2_nano4.yaml
# Patch paths
sed -i "s|/work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M/reads_50M.fa|${DATA}/reads_50M.fa|g" /tmp/dnabert2_nano4.yaml
sed -i "s|/work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M/labels_50M.tsv|${DATA}/labels_50M.tsv|g" /tmp/dnabert2_nano4.yaml
sed -i "s|dir: .*dnabert2_token_genus_50M|dir: ${CKPT_DIR}|g" /tmp/dnabert2_nano4.yaml

cd ${REPO}/scripts

# ── Train (auto-resume from last.pt if exists) ─────────────────────────
if [ -f "${CKPT_DIR}/last.pt" ]; then
    echo "=== Resuming training from ${CKPT_DIR}/last.pt ==="
    python -u train.py \
        --config /tmp/dnabert2_nano4.yaml \
        --resume "${CKPT_DIR}/last.pt" \
        2>&1
else
    echo "=== Starting training from scratch ==="
    python -u train.py --config /tmp/dnabert2_nano4.yaml 2>&1
fi

echo ""
echo "========================================"
echo "Epoch done. Done: $(date)"
# Print latest epoch for convenience
if [ -f "$HISTORY" ]; then
    CURRENT_EPOCH=$(tail -1 "$HISTORY" | cut -d',' -f1)
    echo "Progress: epoch ${CURRENT_EPOCH}/30"
    if [ "$CURRENT_EPOCH" -ge "30" ]; then
        echo ">>> Training COMPLETE (30 epochs). Run eval next."
    else
        echo ">>> Resubmit: sbatch slurm/run_dnabert2_genus_50M.nano4.sh"
    fi
fi
echo "========================================"
