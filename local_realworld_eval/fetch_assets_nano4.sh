#!/bin/bash
# ================================================================
# Fetch large inference assets from Nano4 → assets dir.
# Run this script on the LOCAL machine after 2FA.
#
# Usage:
#   bash local_realworld_eval/fetch_assets_nano4.sh
#
# Override asset destination (default /nas2/gfm-classifier/track_a/assets):
#   DATA_ROOT=/some/other/path bash local_realworld_eval/fetch_assets_nano4.sh
#
# The script opens ONE SSH master connection (single 2FA prompt),
# then uses it for all subsequent rsync/scp calls.
# ================================================================

set -euo pipefail

NANO4="ymj1123ntu@nano4.nchc.org.tw"
CTRL="/tmp/nano4-pull-ctrl"
SSHOPT="-o ControlPath=${CTRL} -o ControlMaster=auto -o ControlPersist=600 -o ServerAliveInterval=60"
N4WORK="/work/ymj1123ntu"
DATA_ROOT="${DATA_ROOT:-/nas2/gfm-classifier/track_a}"
HERE="${DATA_ROOT}/assets"

echo "================================================================"
echo "  Fetch inference assets from Nano4 → ${HERE}"
echo "================================================================"
echo ""
echo "[0] Opening SSH master connection (2FA prompt here)…"
ssh -fNM ${SSHOPT} ${NANO4}
echo "    Connection open."

rsync_n4() {
    rsync -avhP --no-relative -e "ssh ${SSHOPT}" "${NANO4}:${N4WORK}/$1" "$2"
}

# ── 1. MT 13-mer 250M checkpoint (8.6 GB stripped, inference-only) ──
echo ""
echo "[1/6] MT 13-mer 250M weights (8.6 GB) …"
mkdir -p "${HERE}/mt_13mer_250M/checkpoints"
rsync_n4 \
  "mt_250M/experiments/mt_13mer_s1_genus_250M_147918/checkpoints/classification_transformer_ckpt_best_inference.pt" \
  "${HERE}/mt_13mer_250M/checkpoints/classification_transformer_ckpt_best_inference.pt"

echo "[1b] MT 13-mer 250M config …"
rsync_n4 \
  "mt_250M/experiments/mt_13mer_s1_genus_250M_147918/config.yaml" \
  "${HERE}/mt_13mer_250M/config.yaml"

# ── 2. MT 13-mer 50M checkpoint (8.6 GB stripped) ───────────────────
echo ""
echo "[2/6] MT 13-mer 50M weights (8.6 GB) …"
mkdir -p "${HERE}/mt_13mer_50M/checkpoints"
rsync_n4 \
  "mt_models/mt_13mer_stride1_genus_895686/checkpoints/classification_transformer_ckpt_best_inference.pt" \
  "${HERE}/mt_13mer_50M/checkpoints/classification_transformer_ckpt_best_inference.pt"

echo "[2b] MT 13-mer 50M config …"
rsync_n4 \
  "mt_models/mt_13mer_stride1_genus_895686/config.yaml" \
  "${HERE}/mt_13mer_50M/config.yaml"

# ── 3. NT-v2 genus v9 checkpoint (~2 GB) ────────────────────────────
echo ""
echo "[3/6] NT-v2 genus v9 checkpoint (~2 GB) …"
mkdir -p "${HERE}/nt_v9"
rsync_n4 \
  "checkpoints/nt_token_genus_v9_50M_best.pt" \
  "${HERE}/nt_v9/nt_token_genus_v9_50M_best.pt"

# ── 4. 13-mer vocab (470 MB) ────────────────────────────────────────
echo ""
echo "[4/6] 13-mer vocab (470 MB) …"
rsync_n4 \
  "MetaTransformer/vocab_file/vocab_13mer.txt" \
  "${HERE}/vocab_13mer.txt"

# ── 5. MetaTransformer/src (small, pure Python) ─────────────────────
echo ""
echo "[5/6] MetaTransformer/src/ …"
mkdir -p "${HERE}/MetaTransformer_src"
rsync -avhP -e "ssh ${SSHOPT}" \
  "${NANO4}:${N4WORK}/MetaTransformer/src/" \
  "${HERE}/MetaTransformer_src/"

# ── 6. Genus label map (derive remotely; do not transfer 19 GB labels) ─
echo ""
echo "[6/6] Genus label map …"
printf "genus_name\tgenus_class\n" > "${HERE}/genus_map.tsv"
ssh ${SSHOPT} ${NANO4} \
  "awk -F '\t' 'NR > 1 {print \$5}' '${N4WORK}/data/balanced_250M/labels_250M.tsv' | sort -u" \
  | awk '{print $0 "\t" NR-1}' >> "${HERE}/genus_map.tsv"

# ── Post-transfer: create required symlinks ──────────────────────────
echo ""
echo "[post] Creating classification_transformer_ckpt_best.pt symlinks …"
(cd "${HERE}/mt_13mer_250M/checkpoints" && \
  ln -sf classification_transformer_ckpt_best_inference.pt \
         classification_transformer_ckpt_best.pt)
(cd "${HERE}/mt_13mer_50M/checkpoints" && \
  ln -sf classification_transformer_ckpt_best_inference.pt \
         classification_transformer_ckpt_best.pt)

ssh -O exit ${SSHOPT} ${NANO4} 2>/dev/null || true

echo ""
echo ""
echo "================================================================"
echo "  All assets fetched → ${HERE}"
echo ""
echo "  ls -lh ${HERE}/"
echo "  ls -lh ${HERE}/mt_13mer_250M/checkpoints/"
echo "  ls -lh ${HERE}/mt_13mer_50M/checkpoints/"
echo ""
echo "  Next step (no 2FA needed):"
echo "    conda activate gfm-local"
echo "    bash local_realworld_eval/run_track_a.sh"
echo "================================================================"
