#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J eval_17M_bal
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH -t 02:00:00
#SBATCH -o /work/ymj1123ntu/logs/eval_17M_bal-%j.out
#SBATCH -e /work/ymj1123ntu/logs/eval_17M_bal-%j.err

# Clean train-disjoint eval of the genus-balanced vs species-balanced 17.64M
# models, BOTH metrics, vs v9. Same ruler for both.
#   - per-read natural : taiwania2_testset/reads_clean_common.fa (~99,742)
#   - per-genus flat   : data/clean_test_genus/reads.fa (1000/genus)
set -uo pipefail
REPO=/work/ymj1123ntu/gfm-classifier
SCRIPTS=${REPO}/scripts
OUT=/work/ymj1123ntu/benchmark_results/eval_17M_balance
mkdir -p ${OUT}

module load miniconda3/26.1.1
source $(conda info --base)/etc/profile.d/conda.sh; conda activate gfm
export HF_HOME=/work/ymj1123ntu/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface
export PYTHONUNBUFFERED=1
cd ${SCRIPTS}

COMMON_FA=/work/ymj1123ntu/taiwania2_testset/reads_clean_common.fa
COMMON_LB=/work/ymj1123ntu/taiwania2_testset/labels_clean_common.tsv
FLAT_FA=/work/ymj1123ntu/data/clean_test_genus/reads.fa
FLAT_LB=/work/ymj1123ntu/data/clean_test_genus/labels.tsv

run() {  # model_tag  config  ckpt  train_labels
    local TAG=$1 CFG=$2 CKPT=$3 TRLB=$4
    for SET in common flat; do
        if [ "$SET" = common ]; then FA=$COMMON_FA; LB=$COMMON_LB; else FA=$FLAT_FA; LB=$FLAT_LB; fi
        echo ""; echo "######## ${TAG} × ${SET} ########"
        python run_genus_rctta.py \
            --config "$CFG" --checkpoint "$CKPT" \
            --test_fasta "$FA" --test_labels "$LB" --train_labels "$TRLB" \
            --out_dir "${OUT}/${TAG}_${SET}" --batch_size 512 || echo "  ⚠ ${TAG} ${SET} FAILED"
    done
}

run gbal ${REPO}/configs/nt_token_genus_gbal_17M.yaml \
        /work/ymj1123ntu/checkpoints/nt_token_genus_gbal_17M/best.pt \
        /work/ymj1123ntu/data/balanced_genus_17M/labels.tsv
run sbal ${REPO}/configs/nt_token_genus_sbal_17M.yaml \
        /work/ymj1123ntu/checkpoints/nt_token_genus_sbal_17M/best.pt \
        /work/ymj1123ntu/data/balanced_species_17M/labels.tsv

echo ""; echo "==== DONE $(date) — results under ${OUT} ===="
