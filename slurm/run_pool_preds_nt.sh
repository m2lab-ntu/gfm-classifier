#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J pool_preds_nt
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1 --ntasks-per-node=1 --cpus-per-task=8 --mem=64G
#SBATCH -t 04:00:00
#SBATCH -o /work/ymj1123ntu/logs/pool_preds_nt-%j.out
#SBATCH -e /work/ymj1123ntu/logs/pool_preds_nt-%j.err
# RC-TTA predictions for the 5 NT settings on the common clean pool (573K),
# saved as rctta.npz for downstream evaluate_sample.py (sample-level abundance).
set -uo pipefail
REPO=/work/ymj1123ntu/gfm-classifier; SC=${REPO}/scripts
POOL_FA=/work/ymj1123ntu/data/clean_pool_5M/reads.fa
POOL_LB=/work/ymj1123ntu/data/clean_pool_5M/labels.tsv
OUT=/work/ymj1123ntu/benchmark_results/sample_pool_preds
mkdir -p ${OUT}
module load miniconda3/26.1.1; source $(conda info --base)/etc/profile.d/conda.sh; conda activate gfm
export HF_HOME=/work/ymj1123ntu/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface
export PYTHONUNBUFFERED=1
cd ${SC}
CK=/work/ymj1123ntu/checkpoints
run(){ # tag config ckpt trainlabels
  echo ""; echo "######## $1 ########"
  python run_genus_rctta.py --config "$2" --checkpoint "$3" \
    --test_fasta ${POOL_FA} --test_labels ${POOL_LB} --train_labels "$4" \
    --out_dir ${OUT}/$1 --batch_size 512 || echo "  ⚠ $1 FAILED"
}
run v9   ${REPO}/configs/nt_token_genus_v9_50M.yaml            ${CK}/nt_token_genus_v9_50M_best.pt              /work/ymj1123ntu/data/labels_50M.tsv
run v14  ${REPO}/configs/nt_token_genus_v14_250M_balanced.yaml ${CK}/nt_token_genus_v14_250M_balanced/best.pt   /work/ymj1123ntu/data/balanced_250M/labels_250M.tsv
run v15  ${REPO}/configs/nt_token_genus_v15_250M_warmstart.yaml ${CK}/nt_token_genus_v15_250M_warmstart/best.pt /work/ymj1123ntu/data/balanced_250M/labels_250M.tsv
run gbal ${REPO}/configs/nt_token_genus_gbal_17M.yaml          ${CK}/nt_token_genus_gbal_17M/best.pt            /work/ymj1123ntu/data/balanced_genus_17M/labels.tsv
run sbal ${REPO}/configs/nt_token_genus_sbal_17M.yaml          ${CK}/nt_token_genus_sbal_17M/best.pt            /work/ymj1123ntu/data/balanced_species_17M/labels.tsv
echo ""; echo "==== DONE $(date) ===="; ls -la ${OUT}/*/rctta.npz 2>/dev/null
