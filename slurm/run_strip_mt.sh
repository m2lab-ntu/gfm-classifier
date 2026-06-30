#!/bin/bash
#SBATCH -A MST114550 -p dev --gres=gpu:1 --nodes=1 --ntasks-per-node=1 --cpus-per-task=4 --mem=128G -t 02:00:00
#SBATCH -o /work/ymj1123ntu/logs/strip_mt-%j.out
#SBATCH -e /work/ymj1123ntu/logs/strip_mt-%j.err
set -uo pipefail
module load miniconda3/26.1.1; source $(conda info --base)/etc/profile.d/conda.sh; conda activate gfm
export PYTHONUNBUFFERED=1; cd /work/ymj1123ntu
for SRC in \
  mt_250M/experiments/mt_13mer_s1_genus_250M_147918/checkpoints/classification_transformer_ckpt_best.pt \
  mt_models/mt_13mer_stride1_genus_895686/checkpoints/classification_transformer_ckpt_best.pt ; do
  echo "### strip $SRC ###"
  python /work/ymj1123ntu/gfm-classifier/scripts/strip_mt_ckpt.py "$SRC" "${SRC%_best.pt}_best_inference.pt" 2>&1
done
echo "=== sizes ==="; find mt_250M mt_models -name '*_best_inference.pt' -exec ls -la {} \; 2>/dev/null | awk '{printf "%.1f GB  %s\n",$5/1e9,$NF}'
