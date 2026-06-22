#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J clean_test_eval
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH -t 02:00:00
#SBATCH -o /work/ymj1123ntu/logs/clean_test_eval-%j.out
#SBATCH -e /work/ymj1123ntu/logs/clean_test_eval-%j.err

# Evaluate v9 / v14 / v15 on the CLEAN, zero-overlap genus test set.
# v9 is the old 50M label system -> bridged via genus_name (its own train_labels).
# v14/v15 share the balanced_250M system.
set -uo pipefail

REPO=/work/ymj1123ntu/gfm-classifier
SCR=${REPO}/scripts/run_nt_genus_test100k.py
TEST_FA=/work/ymj1123ntu/data/clean_test_genus/reads.fa
TEST_LB=/work/ymj1123ntu/data/clean_test_genus/labels.tsv
BAL_LB=/work/ymj1123ntu/data/balanced_250M/labels_250M.tsv
V50_LB=/work/ymj1123ntu/data/labels_50M.tsv
OUT=/work/ymj1123ntu/checkpoints

echo "=== Start $(date) on $(hostname) ==="
module load miniconda3/26.1.1
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate gfm
export PYTHONUNBUFFERED=1
cd ${REPO}/scripts

run_eval () {  # name config ckpt train_labels outsub
  echo ""
  echo "################ EVAL: $1 ################"
  python -u ${SCR} \
    --config       "$2" \
    --checkpoint   "$3" \
    --test_fasta   "${TEST_FA}" \
    --test_labels  "${TEST_LB}" \
    --train_labels "$4" \
    --out_dir      "${OUT}/$5" \
    --batch_size   512 2>&1
}

run_eval "v9_50M"  ${REPO}/configs/nt_token_genus_v9_50M.yaml \
         /work/ymj1123ntu/checkpoints/nt_token_genus_v9_50M_best.pt \
         ${V50_LB}  cleantest_eval_v9

run_eval "v14_25ep" ${REPO}/configs/nt_token_genus_v14_250M_balanced.yaml \
         /work/ymj1123ntu/checkpoints/nt_token_genus_v14_250M_balanced/best.pt \
         ${BAL_LB}  cleantest_eval_v14

run_eval "v15_warm" ${REPO}/configs/nt_token_genus_v15_250M_warmstart.yaml \
         /work/ymj1123ntu/checkpoints/nt_token_genus_v15_250M_warmstart/best.pt \
         ${BAL_LB}  cleantest_eval_v15

echo ""
echo "=== Done $(date) ==="
echo "--- SUMMARY (clean zero-overlap test, ${TEST_FA}) ---"
for m in v9 v14 v15; do
  f=${OUT}/cleantest_eval_${m}/inference_summary.json
  [ -f "$f" ] && echo -n "${m}: " && cat "$f"
  echo ""
done
