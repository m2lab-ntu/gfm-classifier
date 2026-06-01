#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J mt_species_sample_eval
#SBATCH -p normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=1
#SBATCH --mem=32G
#SBATCH -t 01:00:00
#SBATCH -o slurm-mt_species_sample_eval-%j.out
#SBATCH -e slurm-mt_species_sample_eval-%j.err

# Exp D/E and 6-mer variants: sample-level species abundance eval on 100K test set.
# Pool = 100K reads → reads_per_sample=1000, n_partition_samples=100, genera_present=50

set -euo pipefail
cd /work/ymj1123ntu/token_level_gfm_classifier

source ~/miniconda/etc/profile.d/conda.sh
conda activate gfm

EVAL="python scripts/evaluate_sample.py"
ARGS="--reads_per_sample 1000 --n_partition_samples 100 --n_sparse_samples 200 --genera_present 50"

echo "=== MT Species Sample-Level Evaluation (100K test set) ==="
echo "Date: $(date) | Host: $(hostname)"
echo "Note: 100K pool → reads_per_sample=1000, n_partition=100, genera_present=50"
echo ""

echo "[1/4] MT 13-mer species flat (49.74%) ..."
$EVAL --predictions results/mt_species_flat/mt_species_flat_preds_100K.npz \
      --out_dir     results/mt_species_flat/eval_sample_level_100K $ARGS

echo "[2/4] MT 13-mer hierarchical (50.86%) ..."
$EVAL --predictions results/mt_hierarchical/mt_hierarchical_preds_100K.npz \
      --out_dir     results/mt_hierarchical/eval_sample_level_100K $ARGS

echo "[3/4] MT 6-mer species flat (9.22%) ..."
$EVAL --predictions results/mt_6mer_species_flat/mt_6mer_species_flat_preds_100K.npz \
      --out_dir     results/mt_6mer_species_flat/eval_sample_level_100K $ARGS

echo "[4/4] MT 6-mer hierarchical (6.41%) ..."
$EVAL --predictions results/mt_6mer_hierarchical/mt_6mer_hierarchical_preds_100K.npz \
      --out_dir     results/mt_6mer_hierarchical/eval_sample_level_100K $ARGS

echo ""
echo "=== Done: $(date) ==="
