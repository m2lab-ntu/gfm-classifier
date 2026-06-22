#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J 3way_cleanval
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH -t 02:00:00
#SBATCH -o /work/ymj1123ntu/logs/3way_cleanval-%j.out
#SBATCH -e /work/ymj1123ntu/logs/3way_cleanval-%j.err
set -uo pipefail
R=/work/ymj1123ntu/gfm-classifier
T=/work/ymj1123ntu/taiwania2_testset
TF=$T/reads_clean_common.fa
TL=$T/labels_clean_common.tsv
BAL=/work/ymj1123ntu/data/balanced_250M/labels_250M.tsv
module load miniconda3/26.1.1
source "$(conda info --base)/etc/profile.d/conda.sh"; conda activate gfm
export PYTHONUNBUFFERED=1
cd $R/scripts
run(){ echo "########## $1 ##########"; python -u run_nt_genus_test100k.py --config "$2" --checkpoint "$3" --test_fasta "$TF" --test_labels "$TL" --train_labels "$4" --out_dir "$T/cleanval_$1" 2>&1; }
run v9  $R/configs/nt_token_genus_v9_50M.yaml          /work/ymj1123ntu/checkpoints/nt_token_genus_v9_50M_best.pt              $T/train_labels_compact.tsv
run v14 $R/configs/nt_token_genus_v14_250M_balanced.yaml /work/ymj1123ntu/checkpoints/nt_token_genus_v14_250M_balanced/best.pt  $BAL
run v15 $R/configs/nt_token_genus_v15_250M_warmstart.yaml /work/ymj1123ntu/checkpoints/nt_token_genus_v15_250M_warmstart/best.pt $BAL
echo "=== Done $(date) ==="
