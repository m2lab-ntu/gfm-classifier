#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J mt250m_preds
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1 --ntasks-per-node=1 --cpus-per-task=8 --mem=96G
#SBATCH -t 02:00:00
#SBATCH -o /work/ymj1123ntu/logs/mt250m_preds-%j.out
#SBATCH -e /work/ymj1123ntu/logs/mt250m_preds-%j.err
# MT-250M (13-mer s1 genus, trained to convergence) predictions on BOTH pools.
set -uo pipefail
SC=/work/ymj1123ntu/gfm-classifier/scripts
EXP=/work/ymj1123ntu/mt_250M/experiments/mt_13mer_s1_genus_250M_147918
VOCAB=/work/ymj1123ntu/MetaTransformer/vocab_file/vocab_13mer.txt
module load miniconda3/26.1.1; source $(conda info --base)/etc/profile.d/conda.sh; conda activate gfm
export PYTHONUNBUFFERED=1
cd /work/ymj1123ntu/MetaTransformer/src
run(){ # name val_dir outdir
  echo "## $1"; mkdir -p "$3"
  PYTHONPATH=/work/ymj1123ntu/MetaTransformer/src python ${SC}/extract_mt_predictions.py \
    --exp_dir ${EXP} --val_dir "$2" --vocab ${VOCAB} --out "$3/preds.npz" \
    --class_indices 3 --batch_size 1024 || echo "  FAIL $1"
}
run leftover  /work/ymj1123ntu/data/clean_pool_5M       /work/ymj1123ntu/benchmark_results/sample_pool_preds/MT250M
run common    /work/ymj1123ntu/data/clean_common_mtdir  /work/ymj1123ntu/benchmark_results/common_preds/MT250M
echo "=== done $(date) ==="; ls -la /work/ymj1123ntu/benchmark_results/*/MT250M/preds.npz 2>/dev/null
