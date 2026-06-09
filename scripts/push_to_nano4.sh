#!/bin/bash
# ================================================================
# Run this script ON NANO5 / TWCC after your single 2FA login.
# It pushes all 258M data + checkpoint to Nano4, then
# SSHes to Nano4 to git pull and submit the training job.
#
# Usage:
#   bash push_to_nano4.sh
# ================================================================

set -euo pipefail

NANO4="ymj1123ntu@nano4.nchc.org.tw"
CTRL="/tmp/nano4-push-ctrl"
SSHOPT="-o ControlPath=${CTRL} -o ControlMaster=auto -o ControlPersist=600"
NANO4_DATA="/work/ymj1123ntu/data"
NANO4_CKPT="/work/ymj1123ntu/checkpoints"

echo "========================================================"
echo "Pushing 258M data + checkpoint to Nano4"
echo "========================================================"

# ── 0. Establish master connection (single MFA prompt) ────────
echo ""
echo "[0] Opening SSH master connection to Nano4 (one-time MFA)..."
ssh -fNM ${SSHOPT} ${NANO4}
echo "    Master connection established. All subsequent steps reuse it."

# ── 1. reads_258M.fa (~47 GB) ─────────────────────────────────
echo ""
echo "[1/3] reads_258M.fa (~47 GB)..."
ssh ${SSHOPT} ${NANO4} "mkdir -p ${NANO4_DATA} ${NANO4_CKPT}"
rsync -avhP -e "ssh ${SSHOPT}" \
    /work/ymj1123ntu/gfm_embedding_classification/data/labeled_multi_level_generated/reads.fa \
    ${NANO4}:${NANO4_DATA}/reads_258M.fa

# ── 2. labels_258M.tsv (~21 GB) ───────────────────────────────
echo ""
echo "[2/3] labels_258M.tsv (~21 GB)..."
rsync -avhP -e "ssh ${SSHOPT}" \
    /work/ymj1123ntu/data/labels_258M.tsv \
    ${NANO4}:${NANO4_DATA}/labels_258M.tsv

# ── 3. v9 best.pt warm-start checkpoint (~1.9 GB) ─────────────
echo ""
echo "[3/3] nt_token_genus_v9 best.pt (~1.9 GB)..."
rsync -avhP -e "ssh ${SSHOPT}" \
    /work/ymj1123ntu/token_level_gfm_classifier/results/nt_token_genus_lora_v9_50M/best.pt \
    ${NANO4}:${NANO4_CKPT}/nt_token_genus_v9_50M_best.pt

# ── 4. Verify + git pull + sbatch on Nano4 ────────────────────
echo ""
echo "========================================================"
echo "Verifying files and submitting job on Nano4..."
echo "========================================================"
ssh ${SSHOPT} ${NANO4} bash << 'REMOTE'
set -e
echo "--- File sizes ---"
ls -lh /work/ymj1123ntu/data/reads_258M.fa \
        /work/ymj1123ntu/data/labels_258M.tsv \
        /work/ymj1123ntu/checkpoints/nt_token_genus_v9_50M_best.pt

echo ""
echo "--- git pull ---"
cd /work/ymj1123ntu/gfm-classifier && git pull

echo ""
echo "--- sbatch ---"
sbatch slurm/run_nt_genus_258M_ddp_nano4.sh
REMOTE

# ── 5. Close master connection ────────────────────────────────
ssh -O exit ${SSHOPT} ${NANO4} 2>/dev/null || true

echo ""
echo "Done. Monitor with: ssh nano4 'squeue --me'"
