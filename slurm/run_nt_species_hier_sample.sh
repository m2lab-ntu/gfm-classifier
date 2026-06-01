#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J nt_sp_hier
#SBATCH -p normal
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=256G
#SBATCH -t 06:00:00
#SBATCH -o slurm-nt_sp_hier-%j.out
#SBATCH -e slurm-nt_sp_hier-%j.err

# NT-Species hierarchical: NT-Genus (66.1%) as genus router → topk=1 logit masking
# Step 1: GPU inference on 5M val split (same pool as NT-Species flat)
# Step 2: sample-level eval (1K reads/sample, matches flat condition)

set -euo pipefail

REPO=/work/ymj1123ntu/token_level_gfm_classifier
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
echo "NT-Species Hierarchical Evaluation"
echo "Router: NT-Genus (66.1%), topk=1"
echo "Start: $(date) | Host: $(hostname)"
echo "========================================"
nvidia-smi || true
echo ""

cd ${REPO}/scripts

# ── Step 1: GPU inference with NT-Genus topk=1 routing ───────────────────────
echo "=== Step 1: Hierarchical inference (topk=1) ==="
python -u evaluate.py \
  --config      ${REPO}/configs/nt_token_species_v4_50M.yaml \
  --checkpoint  ${SP_RESULTS}/best.pt \
  --topk_genus_routing 1 \
  --genus_config      ${REPO}/configs/nt_token_genus_v9_50M.yaml \
  --genus_checkpoint  ${REPO}/results/nt_token_genus_lora_v9_50M/best.pt \
  --output_dir  ${SP_RESULTS}/eval_topk_1 \
  --skip_save_logits
echo ""

# ── Step 2: Sample-level evaluation ──────────────────────────────────────────
echo "=== Step 2: Sample-level eval (1K reads/sample) ==="
python -u evaluate_sample.py \
  --predictions ${SP_RESULTS}/eval_topk_1/predictions.npz \
  --out_dir     ${SP_RESULTS}/eval_sample_level_hier_1K \
  --reads_per_sample    1000 \
  --n_partition_samples 100 \
  --n_sparse_samples    200 \
  --genera_present       50
echo ""

echo "========================================"
echo "Done: $(date)"
echo "Results: ${SP_RESULTS}/eval_sample_level_hier_1K/sample_metrics.json"
echo "========================================"
