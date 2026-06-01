#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J nt_sp_hier_t
#SBATCH -p normal
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH -t 01:00:00
#SBATCH -o /work/ymj1123ntu/token_level_gfm_classifier/slurm-nt_sp_hier_stream_t100k-%j.out
#SBATCH -e /work/ymj1123ntu/token_level_gfm_classifier/slurm-nt_sp_hier_stream_t100k-%j.err

# NT-Species hierarchical streaming inference on the INDEPENDENT 100K test set.
# Produces NT-Species hier numbers on the same pool as Table 4.29 (all other models).
# Step 1: streaming inference → predictions.npz
# Step 2: sample-level eval → sample_metrics.json

set -euo pipefail

REPO=/work/ymj1123ntu/token_level_gfm_classifier
DATA=/work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M
SP_RESULTS=${REPO}/results/nt_token_species_v4_50M

source ~/miniconda/etc/profile.d/conda.sh
conda activate gfm

export HF_HOME=/work/ymj1123ntu/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface
export TRANSFORMERS_CACHE=/work/ymj1123ntu/.cache/huggingface
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export OMP_NUM_THREADS=4
export PYTHONUNBUFFERED=1

echo "========================================"
echo "NT-Species Hier Streaming — 100K test set"
echo "Start: $(date) | Host: $(hostname)"
echo "========================================"
nvidia-smi || true
echo ""

cd ${REPO}/scripts

echo "=== Step 1: Streaming hierarchical inference (100K test, topk=1) ==="
python -u run_nt_species_hier_stream_test100k.py \
  --sp_config      ${REPO}/configs/nt_token_species_v4_50M.yaml \
  --sp_checkpoint  ${SP_RESULTS}/best.pt \
  --gn_config      ${REPO}/configs/nt_token_genus_v9_50M.yaml \
  --gn_checkpoint  ${REPO}/results/nt_token_genus_lora_v9_50M/best.pt \
  --test_fasta     ${DATA}/reads_100K.fa \
  --test_labels    ${DATA}/labels_100K.tsv \
  --train_labels   ${DATA}/labels_50M.tsv \
  --output_dir     ${SP_RESULTS}/eval_hier_stream_test100k \
  --batch_size     512
echo ""

echo "=== Step 2: Sample-level eval (1K reads/sample) ==="
python -u evaluate_sample.py \
  --predictions ${SP_RESULTS}/eval_hier_stream_test100k/predictions.npz \
  --out_dir     ${SP_RESULTS}/eval_sample_level_hier_test100k \
  --reads_per_sample    1000 \
  --n_partition_samples 100 \
  --n_sparse_samples    200 \
  --genera_present       50
echo ""

echo "========================================"
echo "Done: $(date)"
echo "Results: ${SP_RESULTS}/eval_sample_level_hier_test100k/sample_metrics.json"
echo "========================================"
