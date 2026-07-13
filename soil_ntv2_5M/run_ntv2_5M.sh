#!/bin/bash
# NT-v2 soil 5M — train + eval on test_final (Taiwania2). Adjust SBATCH + paths.
#SBATCH --job-name=ntv2_soil_5M
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --time=12:00:00
#SBATCH --output=ntv2_soil_5M_%j.log
set -euo pipefail

# ---- EDIT THESE ----
PKG=/work/ymj1123ntu/gfm-classifier/soil_ntv2_5M      # where you pulled the repo
BASE=/work/ymj1123ntu/mt5m_soil                       # data root (shared with MT-5M)
PYTHON=python                                         # conda env python w/ torch+transformers+peft+sklearn
CONDA_ENV=""                                          # e.g. "ntv2"; leave "" if PYTHON is already correct
# --------------------

[ -n "$CONDA_ENV" ] && source "$(conda info --base)/etc/profile.d/conda.sh" && conda activate "$CONDA_ENV"
cd "$PKG/scripts"
export PYTHONPATH="$PKG/scripts:${PYTHONPATH:-}"
mkdir -p "$BASE/ntv2_data" "$BASE/results"

echo "==== [1/3] prep NT-v2 fasta+TSV from the SAME shards as MT-5M ===="
# train (from mt5m_soil/data/train shards), test_final (from data/test_final shards)
$PYTHON prep_ntv2_from_shards.py --shards_dir "$BASE/data/train" \
  --out_fa "$BASE/ntv2_data/nt_soil_train_5M.fa" \
  --out_tsv "$BASE/ntv2_data/nt_soil_train_5M_labels.tsv" --idx2name "$PKG/idx2name.json"
$PYTHON prep_ntv2_from_shards.py --shards_dir "$BASE/data/test_final" \
  --out_fa "$BASE/ntv2_data/nt_soil_test.fa" \
  --out_tsv "$BASE/ntv2_data/nt_soil_test_labels.tsv" --idx2name "$PKG/idx2name.json"

echo "==== [2/3] train NT-v2 5M ===="
$PYTHON train.py --config "$PKG/config/nt_soil_genus_5M_twcc.yaml"

echo "==== [3/3] eval best.pt on test_final (RC-TTA) ===="
$PYTHON run_genus_rctta.py \
  --config       "$PKG/config/nt_soil_genus_5M_twcc.yaml" \
  --checkpoint   "$BASE/results/nt_soil_genus_5M/best.pt" \
  --test_fasta   "$BASE/ntv2_data/nt_soil_test.fa" \
  --test_labels  "$BASE/ntv2_data/nt_soil_test_labels.tsv" \
  --train_labels "$BASE/ntv2_data/nt_soil_train_5M_labels.tsv" \
  --out_dir      "$BASE/results/nt_soil_genus_5M/eval_test_final" \
  --batch_size   512
echo "==== DONE — see results/nt_soil_genus_5M/eval_test_final/rctta.npz (fwd/rc/tta Top-1) ===="
