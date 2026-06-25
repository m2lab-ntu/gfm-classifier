#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J pool_preds_mt50m
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1 --ntasks-per-node=1 --cpus-per-task=8 --mem=96G
#SBATCH -t 02:00:00
#SBATCH -o /work/ymj1123ntu/logs/pool_preds_mt50m-%j.out
#SBATCH -e /work/ymj1123ntu/logs/pool_preds_mt50m-%j.err
# MT-50M (13-mer s1 genus, 87.42%) predictions on the common clean pool (573K)
# → npz (preds/probs/labels) for sample-level abundance eval.
set -uo pipefail
MT_SRC=/work/ymj1123ntu/MetaTransformer/src
OUT=/work/ymj1123ntu/benchmark_results/sample_pool_preds/MT50M
mkdir -p ${OUT}
module load miniconda3/26.1.1; source $(conda info --base)/etc/profile.d/conda.sh; conda activate gfm
export PYTHONUNBUFFERED=1
cd ${MT_SRC}
PYTHONPATH=${MT_SRC} python /work/ymj1123ntu/gfm-classifier/scripts/extract_mt_predictions.py \
    --exp_dir       /work/ymj1123ntu/mt_models/mt_13mer_stride1_genus_895686 \
    --val_dir       /work/ymj1123ntu/data/clean_pool_5M \
    --vocab         /work/ymj1123ntu/MetaTransformer/vocab_file/vocab_13mer.txt \
    --out           ${OUT}/preds.npz \
    --class_indices 3 --batch_size 1024 || echo "  ⚠ MT50M FAILED"
echo "=== done $(date) ==="; ls -la ${OUT}/preds.npz 2>/dev/null
