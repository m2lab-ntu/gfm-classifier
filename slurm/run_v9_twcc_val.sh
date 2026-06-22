#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J v9_twcc_val
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH -t 01:00:00
#SBATCH -o /work/ymj1123ntu/logs/v9_twcc_val-%j.out
#SBATCH -e /work/ymj1123ntu/logs/v9_twcc_val-%j.err
set -uo pipefail
REPO=/work/ymj1123ntu/gfm-classifier
T=/work/ymj1123ntu/taiwania2_testset
module load miniconda3/26.1.1
source "$(conda info --base)/etc/profile.d/conda.sh"; conda activate gfm
export PYTHONUNBUFFERED=1
cd ${REPO}/scripts
echo "### v9 on Taiwania2 val (1.12% overlap) — expect ~66% if original number came from here ###"
python -u run_nt_genus_test100k.py \
  --config       ${REPO}/configs/nt_token_genus_v9_50M.yaml \
  --checkpoint   /work/ymj1123ntu/checkpoints/nt_token_genus_v9_50M_best.pt \
  --test_fasta   ${T}/reads_100K_val.fa \
  --test_labels  ${T}/labels_100K_val.tsv \
  --train_labels ${T}/train_labels_compact.tsv \
  --out_dir      ${T}/eval_out 2>&1
echo "=== Done $(date) ==="
