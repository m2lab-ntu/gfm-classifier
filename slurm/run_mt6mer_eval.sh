#!/bin/bash
#SBATCH -A MST114550 -p dev --gres=gpu:1 --nodes=1 --ntasks-per-node=1 --cpus-per-task=8 --mem=64G -t 01:00:00
#SBATCH -o /work/ymj1123ntu/logs/mt6mer_eval-%j.out
#SBATCH -e /work/ymj1123ntu/logs/mt6mer_eval-%j.err
set -uo pipefail
SC=/work/ymj1123ntu/gfm-classifier/scripts; V6=/work/ymj1123ntu/gfm-classifier/small_predictions/vocab_6mer.txt
module load miniconda3/26.1.1; source $(conda info --base)/etc/profile.d/conda.sh; conda activate gfm
export PYTHONUNBUFFERED=1; cd /work/ymj1123ntu/MetaTransformer/src
for tag in s1 s6; do
  EXP=$(ls -dt /work/ymj1123ntu/mt_250M/experiments/mt_6mer_${tag}_genus_250M_* | head -1)
  echo "## MT 6-mer $tag  exp=$EXP"
  PYTHONPATH=/work/ymj1123ntu/MetaTransformer/src python ${SC}/extract_mt_predictions.py     --exp_dir $EXP --val_dir /work/ymj1123ntu/data/clean_common_mtdir --vocab $V6     --out /work/ymj1123ntu/benchmark_results/common_preds/MT6mer_${tag}/preds.npz     --class_indices 3 --batch_size 1024 2>&1 | grep -aiE 'reads|Top-1|accuracy|Error' | head -4
done
echo "=== done $(date) ==="
