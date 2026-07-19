#!/bin/bash
# NT-v2 soil 5M — train + eval on test_final (Taiwania2).
#SBATCH --account=MST114414
#SBATCH --job-name=ntv2_soil_5M
#SBATCH --partition=gp2d
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4          # gp2d caps at 4 CPU/GPU for a 1-GPU alloc (learned from MT run)
#SBATCH --mem=90G
#SBATCH --gres=gpu:1
#SBATCH --time=2-00:00:00          # 6 epochs of NT-v2-500M on a V100 may exceed 12h; early_stopping may cut short
#SBATCH --output=/work/ymj1123ntu/mt5m_soil/logs/ntv2_soil_5M_%j.out
#SBATCH --error=/work/ymj1123ntu/mt5m_soil/logs/ntv2_soil_5M_%j.err
set -euo pipefail

# ---- paths / env ----
PKG=/work/ymj1123ntu/gfm-classifier/soil_ntv2_5M
BASE=/work/ymj1123ntu/mt5m_soil
PYTHON=/home/ymj1123ntu/.conda/envs/gfm/bin/python   # gfm env: torch2.3+cu121, transformers4.42.4, peft0.11.1 (verified loads NT-v2 offline)

# ---- HF offline cache (compute nodes have NO internet; backbone is pre-cached here) ----
export HF_HOME=/work/ymj1123ntu/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface
export TRANSFORMERS_CACHE=/work/ymj1123ntu/.cache/huggingface
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=4
export PYTHONUNBUFFERED=1

cd "$PKG/scripts"
export PYTHONPATH="$PKG/scripts:${PYTHONPATH:-}"
mkdir -p "$BASE/ntv2_data" "$BASE/results" "$BASE/logs"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1

echo "==== [1/3] prep NT-v2 fasta+TSV from the SAME shards as MT-5M ===="
# already run on the login node; only (re)build if missing so we don't burn GPU walltime on CPU prep
if [ ! -s "$BASE/ntv2_data/nt_soil_train_5M.fa" ] || [ ! -s "$BASE/ntv2_data/nt_soil_train_5M_labels.tsv" ]; then
  $PYTHON prep_ntv2_from_shards.py --shards_dir "$BASE/data/train" \
    --out_fa "$BASE/ntv2_data/nt_soil_train_5M.fa" \
    --out_tsv "$BASE/ntv2_data/nt_soil_train_5M_labels.tsv" --idx2name "$PKG/idx2name.json"
else echo "  train fasta/tsv present, skipping"; fi
if [ ! -s "$BASE/ntv2_data/nt_soil_test.fa" ] || [ ! -s "$BASE/ntv2_data/nt_soil_test_labels.tsv" ]; then
  $PYTHON prep_ntv2_from_shards.py --shards_dir "$BASE/data/test_final" \
    --out_fa "$BASE/ntv2_data/nt_soil_test.fa" \
    --out_tsv "$BASE/ntv2_data/nt_soil_test_labels.tsv" --idx2name "$PKG/idx2name.json"
else echo "  test fasta/tsv present, skipping"; fi

echo "==== [2/3] train NT-v2 5M ===="
LAST="$BASE/results/nt_soil_genus_5M/last.pt"
if [ -f "$LAST" ]; then RES="--resume $LAST"; echo "  resuming from $LAST"; else RES=""; echo "  fresh start"; fi
$PYTHON train.py --config "$PKG/config/nt_soil_genus_5M_twcc.yaml" $RES

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
