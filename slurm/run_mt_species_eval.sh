#!/bin/bash
#SBATCH -A MST114550 -p dev --gres=gpu:1 --nodes=1 --ntasks-per-node=1 --cpus-per-task=8 --mem=64G -t 01:00:00
#SBATCH -o /work/ymj1123ntu/logs/mt_species_eval-%j.out
#SBATCH -e /work/ymj1123ntu/logs/mt_species_eval-%j.err
# arg1: exp_dir   arg2: out tag   -> species Top-1 (class_indices=1) on clean_common
set -uo pipefail
EXP="$1"; TAG="$2"; SC=/work/ymj1123ntu/gfm-classifier/scripts
V13=/work/ymj1123ntu/MetaTransformer/vocab_file/vocab_13mer.txt
module load miniconda3/26.1.1; source $(conda info --base)/etc/profile.d/conda.sh; conda activate gfm
export PYTHONUNBUFFERED=1; cd /work/ymj1123ntu/MetaTransformer/src
mkdir -p /work/ymj1123ntu/benchmark_results/common_preds/${TAG}
PYTHONPATH=/work/ymj1123ntu/MetaTransformer/src python ${SC}/extract_mt_predictions.py \
  --exp_dir "$EXP" --val_dir /work/ymj1123ntu/data/clean_common_mtdir --vocab $V13 \
  --out /work/ymj1123ntu/benchmark_results/common_preds/${TAG}/preds.npz \
  --class_indices 1 --batch_size 1024 2>&1 | grep -aiE 'reads|Top-1'
echo "=== ${TAG} done $(date) ==="
