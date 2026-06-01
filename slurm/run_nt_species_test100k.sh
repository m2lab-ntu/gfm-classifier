#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J nt_sp_test100k
#SBATCH -p normal
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH -t 02:00:00
#SBATCH -o slurm-nt_species_test100k-%j.out
#SBATCH -e slurm-nt_species_test100k-%j.err

# NT-Species inference on the independent 100K test set (Option B).
# Step 1: GPU inference → predictions.npz
# Step 2: sample-level evaluation (CPU only, reads_per_sample=1000)

set -euo pipefail

REPO="/work/ymj1123ntu/token_level_gfm_classifier"
DATA="/work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M"
SP_RESULTS="${REPO}/results/nt_token_species_v4_50M"

source ~/miniconda/etc/profile.d/conda.sh
conda activate gfm

export HF_HOME=/work/ymj1123ntu/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface
export TRANSFORMERS_CACHE=/work/ymj1123ntu/.cache/huggingface
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export OMP_NUM_THREADS=4
export PYTHONUNBUFFERED=1

echo "========================================"
echo "NT-Species Option B: 100K test set eval"
echo "Start: $(date) | Host: $(hostname)"
echo "========================================"
nvidia-smi || true
echo ""

cd "${REPO}/scripts"

# ── Step 1: GPU inference on 100K test set ────────────────────────────────────
echo "=== Step 1: NT-Species inference on 100K test set ==="
python -u run_nt_species_test100k.py \
  --config      "${REPO}/configs/nt_token_species_v4_50M.yaml" \
  --checkpoint  "${SP_RESULTS}/best.pt" \
  --test_fasta  "${DATA}/reads_100K.fa" \
  --test_labels "${DATA}/labels_100K.tsv" \
  --train_labels "${DATA}/labels_50M.tsv" \
  --out_dir     "${SP_RESULTS}/eval_test100k" \
  --batch_size  512
echo ""

# ── Step 2: Sample-level evaluation ──────────────────────────────────────────
echo "=== Step 2: Sample-level evaluation (100K pool, 1K reads/sample) ==="
python -u evaluate_sample.py \
  --predictions "${SP_RESULTS}/eval_test100k/predictions.npz" \
  --out_dir     "${SP_RESULTS}/eval_sample_level_test100k" \
  --reads_per_sample   1000 \
  --n_partition_samples 100 \
  --n_sparse_samples   200 \
  --genera_present      50
echo ""

echo "========================================"
echo "Done: $(date)"
echo "========================================"
