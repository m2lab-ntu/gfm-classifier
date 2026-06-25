#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J common_preds
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1 --ntasks-per-node=1 --cpus-per-task=8 --mem=96G
#SBATCH -t 02:00:00
#SBATCH -o /work/ymj1123ntu/logs/common_preds-%j.out
#SBATCH -e /work/ymj1123ntu/logs/common_preds-%j.err
# Predictions on the FRIENDLY natural pool clean_common (99,742, strict
# train-disjoint) for all settings -> npz for sample-level eval.
set -uo pipefail
REPO=/work/ymj1123ntu/gfm-classifier; SC=${REPO}/scripts; CK=/work/ymj1123ntu/checkpoints
FA=/work/ymj1123ntu/taiwania2_testset/reads_clean_common.fa
LB=/work/ymj1123ntu/taiwania2_testset/labels_clean_common.tsv
OUT=/work/ymj1123ntu/benchmark_results/common_preds
mkdir -p ${OUT}
module load miniconda3/26.1.1; source $(conda info --base)/etc/profile.d/conda.sh; conda activate gfm
export HF_HOME=/work/ymj1123ntu/.cache/huggingface HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface PYTHONUNBUFFERED=1
cd ${SC}
nt(){ echo "## $1"; python run_genus_rctta.py --config "$2" --checkpoint "$3" --test_fasta ${FA} --test_labels ${LB} --train_labels "$4" --out_dir ${OUT}/$1 --batch_size 512 || echo "  FAIL $1"; }
nt v9   ${REPO}/configs/nt_token_genus_v9_50M.yaml            ${CK}/nt_token_genus_v9_50M_best.pt              /work/ymj1123ntu/data/labels_50M.tsv
nt v14  ${REPO}/configs/nt_token_genus_v14_250M_balanced.yaml ${CK}/nt_token_genus_v14_250M_balanced/best.pt   /work/ymj1123ntu/data/balanced_250M/labels_250M.tsv
nt v15  ${REPO}/configs/nt_token_genus_v15_250M_warmstart.yaml ${CK}/nt_token_genus_v15_250M_warmstart/best.pt /work/ymj1123ntu/data/balanced_250M/labels_250M.tsv
nt gbal ${REPO}/configs/nt_token_genus_gbal_17M.yaml          ${CK}/nt_token_genus_gbal_17M/best.pt            /work/ymj1123ntu/data/balanced_genus_17M/labels.tsv
nt sbal ${REPO}/configs/nt_token_genus_sbal_17M.yaml          ${CK}/nt_token_genus_sbal_17M/best.pt            /work/ymj1123ntu/data/balanced_species_17M/labels.tsv
echo "## MT50M"
cd /work/ymj1123ntu/MetaTransformer/src
PYTHONPATH=/work/ymj1123ntu/MetaTransformer/src python ${SC}/extract_mt_predictions.py \
  --exp_dir /work/ymj1123ntu/mt_models/mt_13mer_stride1_genus_895686 \
  --val_dir /work/ymj1123ntu/data/clean_common_mtdir \
  --vocab /work/ymj1123ntu/MetaTransformer/vocab_file/vocab_13mer.txt \
  --out ${OUT}/MT50M/preds.npz --class_indices 3 --batch_size 1024 || echo "  FAIL MT50M"
echo "=== done $(date) ==="; ls -la ${OUT}/*/rctta.npz ${OUT}/*/preds.npz 2>/dev/null | awk '{print $5,$NF}'
