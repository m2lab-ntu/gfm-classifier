#!/bin/bash
#SBATCH --job-name=gfm_sanity
#SBATCH --account=MST114550
#SBATCH --partition=dev
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --time=00:45:00
#SBATCH --output=/work/ymj1123ntu/gfm-classifier/logs/sanity_%j.out
#SBATCH --error=/work/ymj1123ntu/gfm-classifier/logs/sanity_%j.err

echo "=== Sanity Check Start ==="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURMD_NODENAME"
date

module load miniconda3/26.1.1
module load cuda/12.6
source $(conda info --base)/etc/profile.d/conda.sh
conda activate gfm

export HF_HOME=/work/ymj1123ntu/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface
export TRANSFORMERS_CACHE=/work/ymj1123ntu/.cache/huggingface

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
python -c "import torch; print('CUDA:', torch.cuda.is_available(), torch.cuda.get_device_name(0))"

cd /work/ymj1123ntu/gfm-classifier

python scripts/run_nt_species_test100k.py \
    --config        configs/nt_token_species_v4_50M.yaml \
    --checkpoint    /work/ymj1123ntu/checkpoints/nt_token_species_v4_50M_best.pt \
    --test_fasta    /work/ymj1123ntu/data/reads_100K.fa \
    --test_labels   /work/ymj1123ntu/data/labels_100K.tsv \
    --train_labels  /work/ymj1123ntu/data/labels_50M.tsv \
    --out_dir       /work/ymj1123ntu/gfm-classifier/results/sanity_check_nano4 \
    --batch_size    1024

echo "=== Done ==="
date
