#!/bin/bash
#SBATCH --job-name=gfm_sanity
#SBATCH --account=MST114550
#SBATCH --partition=dev
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --output=/work/ymj1123ntu/gfm-classifier/logs/sanity_%j.out
#SBATCH --error=/work/ymj1123ntu/gfm-classifier/logs/sanity_%j.err

echo "=== Sanity Check Start ==="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURMD_NODENAME"
date

# Load modules
module load miniconda3/26.1.1
module load cuda/12.6
source $(conda info --base)/etc/profile.d/conda.sh
conda activate gfm

# Env vars
export HF_HOME=/work/ymj1123ntu/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface

# Check GPU
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
python -c "import torch; print('CUDA:', torch.cuda.is_available(), torch.cuda.get_device_name(0))"

# Run inference
cd /work/ymj1123ntu/gfm-classifier

NANO4_DATA=/work/ymj1123ntu/data
NANO4_CKPT=/work/ymj1123ntu/checkpoints

if [ ! -f "$NANO4_DATA/reads_100K.fa" ]; then
    echo "ERROR: reads_100K.fa not found at $NANO4_DATA/"
    echo "Please run: bash /work/ymj1123ntu/sync_from_nano5.sh"
    exit 1
fi

if [ ! -f "$NANO4_CKPT/nt_token_species_v4_50M_best.pt" ]; then
    echo "ERROR: checkpoint not found at $NANO4_CKPT/"
    exit 1
fi

python scripts/run_nt_species_test100k.py \
    --config        configs/nt_token_species_v4_50M.yaml \
    --checkpoint    $NANO4_CKPT/nt_token_species_v4_50M_best.pt \
    --test_fasta    $NANO4_DATA/reads_100K.fa \
    --test_labels   $NANO4_DATA/labels_100K.tsv \
    --train_labels  $NANO4_DATA/labels_50M.tsv \
    --out_dir       /work/ymj1123ntu/gfm-classifier/results/sanity_check_nano4 \
    --batch_size    512

echo "=== Done ==="
date
