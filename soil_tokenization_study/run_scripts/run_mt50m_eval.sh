#!/bin/bash
#SBATCH --account=MST114414
#SBATCH --job-name=mt50m_eval
#SBATCH --partition=gp2d
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=90G
#SBATCH --gres=gpu:1
#SBATCH --time=2:00:00
#SBATCH --output=/work/ymj1123ntu/mt50m_soil/logs/mt50m_eval_%j.out
#SBATCH --error=/work/ymj1123ntu/mt50m_soil/logs/mt50m_eval_%j.err

# Eval MT-50M best.pt on the SAME fixed test_final (5M) as MT-5M / NT-v2. fwd-only Top-1.
source /home/ymj1123ntu/.bashrc; eval "$(conda shell.bash hook)"; conda activate MetaTransformer

EXP=$(ls -td /work/ymj1123ntu/mt50m_soil/experiments/genus_50M_soil_* 2>/dev/null | head -1)
if [ -z "${EXP}" ]; then echo "ERROR: no genus_50M_soil experiment dir found"; exit 1; fi
echo "Evaluating experiment: ${EXP}"

cd /home/ymj1123ntu/MetaTransformer/src
python3 /work/ymj1123ntu/mt5m_soil/eval_test_final.py \
    --ckpt "${EXP}/checkpoints/classification_transformer_ckpt_best.pt" \
    --val  /work/ymj1123ntu/mt5m_soil/data/test_final \
    --cfg  "${EXP}/config.yaml" \
    --out  /work/ymj1123ntu/mt50m_soil/results/eval_test_final/mt50m_test_final.npz \
    --gpu 0 --batch-size 2048 --max-batches 3000
