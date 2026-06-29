#!/bin/bash
#SBATCH -A MST114550 -p dev --gres=gpu:1 --nodes=1 --ntasks-per-node=1 --cpus-per-task=8 --mem=64G -t 01:30:00
#SBATCH -o /work/ymj1123ntu/logs/mt6mer_complete-%j.out
#SBATCH -e /work/ymj1123ntu/logs/mt6mer_complete-%j.err
set -uo pipefail
SC=/work/ymj1123ntu/gfm-classifier/scripts; V6=/work/ymj1123ntu/gfm-classifier/small_predictions/vocab_6mer.txt
PY=/home/ymj1123ntu/.conda/envs/gfm/bin/python
module load miniconda3/26.1.1; source $(conda info --base)/etc/profile.d/conda.sh; conda activate gfm
export PYTHONUNBUFFERED=1; cd /work/ymj1123ntu/MetaTransformer/src
for tag in s1 s6; do
  EXP=$(ls -dt /work/ymj1123ntu/mt_250M/experiments/mt_6mer_${tag}_genus_250M_* | head -1)
  OUTL=/work/ymj1123ntu/benchmark_results/sample_pool_preds/MT6mer_${tag}; mkdir -p $OUTL
  echo "## leftover Top-1 MT6mer_$tag"
  PYTHONPATH=/work/ymj1123ntu/MetaTransformer/src python ${SC}/extract_mt_predictions.py \
    --exp_dir $EXP --val_dir /work/ymj1123ntu/data/clean_pool_5M --vocab $V6 \
    --out $OUTL/preds.npz --class_indices 3 --batch_size 1024 2>&1 | grep -aiE 'reads|Top-1'
  # sample-level both pools
  $PY ${SC}/evaluate_sample.py --predictions /work/ymj1123ntu/benchmark_results/common_preds/MT6mer_${tag}/preds.npz \
    --out_dir /work/ymj1123ntu/benchmark_results/sample_common_eval/MT6mer_${tag} --exp_name MT6mer_${tag} \
    --n_partition_samples 9 --reads_per_sample 10000 2>&1 | grep -aiE 'Pearson' | sed "s/^/[common $tag] /"
  $PY ${SC}/evaluate_sample.py --predictions $OUTL/preds.npz \
    --out_dir /work/ymj1123ntu/benchmark_results/sample_pool_eval50k/MT6mer_${tag} --exp_name MT6mer_${tag} \
    --n_partition_samples 11 --reads_per_sample 50000 2>&1 | grep -aiE 'Pearson' | sed "s/^/[leftover $tag] /"
done
echo "=== mt6mer complete done $(date) ==="
