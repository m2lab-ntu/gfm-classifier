#!/bin/bash
# NT-v2 soil 50M — train + eval on test_final. fp16 fix in train.py makes this feasible
# (~0.8 s/it fp16 vs 3.3 s/it bf16 on V100). Reuses the SAME 50M shards as MT-50M.
#SBATCH --account=MST114414
#SBATCH --job-name=ntv2_soil_50M
#SBATCH --partition=gp2d
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=90G
#SBATCH --gres=gpu:1
#SBATCH --time=2-00:00:00
#SBATCH --output=/work/ymj1123ntu/mt5m_soil/logs/ntv2_soil_50M_%j.out
#SBATCH --error=/work/ymj1123ntu/mt5m_soil/logs/ntv2_soil_50M_%j.err
set -euo pipefail

PKG=/work/ymj1123ntu/gfm-classifier/soil_ntv2_5M
BASE=/work/ymj1123ntu/mt5m_soil                       # ntv2_data + results live here (shared)
SHARDS=/work/ymj1123ntu/mt50m_soil/data/train         # the SAME 50M shards MT-50M trains on
PYTHON=/home/ymj1123ntu/.conda/envs/gfm/bin/python

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

echo "==== [1/3] prep NT-v2 fasta+TSV from the 50M shards ===="
if [ ! -s "$BASE/ntv2_data/nt_soil_train_50M.fa" ] || [ ! -s "$BASE/ntv2_data/nt_soil_train_50M_labels.tsv" ]; then
  $PYTHON prep_ntv2_from_shards.py --shards_dir "$SHARDS" \
    --out_fa "$BASE/ntv2_data/nt_soil_train_50M.fa" \
    --out_tsv "$BASE/ntv2_data/nt_soil_train_50M_labels.tsv" --idx2name "$PKG/idx2name.json"
else echo "  50M train fasta/tsv present, skipping"; fi
# test_final fasta already built (shared with 5M run): nt_soil_test.fa / _labels.tsv

echo "==== [2/3] train NT-v2 50M (fp16 fix active) ===="
LAST="$BASE/results/nt_soil_genus_50M/last.pt"
if [ -f "$LAST" ]; then RES="--resume $LAST"; echo "  resuming from $LAST"; else RES=""; echo "  fresh start"; fi
$PYTHON train.py --config "$PKG/config/nt_soil_genus_50M_twcc.yaml" $RES

echo "==== [3/3] eval best.pt on test_final (RC-TTA) ===="
$PYTHON run_genus_rctta.py \
  --config       "$PKG/config/nt_soil_genus_50M_twcc.yaml" \
  --checkpoint   "$BASE/results/nt_soil_genus_50M/best.pt" \
  --test_fasta   "$BASE/ntv2_data/nt_soil_test.fa" \
  --test_labels  "$BASE/ntv2_data/nt_soil_test_labels.tsv" \
  --train_labels "$BASE/ntv2_data/nt_soil_train_50M_labels.tsv" \
  --out_dir      "$BASE/results/nt_soil_genus_50M/eval_test_final" \
  --batch_size   512
echo "==== DONE — results/nt_soil_genus_50M/eval_test_final/rctta.npz ===="
