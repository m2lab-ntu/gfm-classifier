#!/bin/bash
#SBATCH -A MST114414
#SBATCH -J debug_cuda
#SBATCH -p 8gpus
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=8
#SBATCH --gres=gpu:8
#SBATCH --cpus-per-task=8
#SBATCH --mem=0
#SBATCH -t 00:05:00
#SBATCH -o /work/ymj1123ntu/logs/debug_cuda-%j.out
#SBATCH -e /work/ymj1123ntu/logs/debug_cuda-%j.err

module load miniconda3/26.1.1
source $(conda info --base)/etc/profile.d/conda.sh
conda activate gfm

export MASTER_ADDR=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -1)
export MASTER_PORT=29500

srun python -c "
import os, torch
rank   = int(os.environ.get('SLURM_PROCID', '?'))
local  = int(os.environ.get('SLURM_LOCALID', '?'))
cvd    = os.environ.get('CUDA_VISIBLE_DEVICES', 'NOT_SET')
host   = os.uname().nodename
ndev   = torch.cuda.device_count()
print(f'host={host} rank={rank} local={local} CVD={cvd} device_count={ndev}', flush=True)
torch.cuda.set_device(local if ndev > 1 else 0)
dev = torch.cuda.current_device()
print(f'  -> set_device OK, current={dev}, name={torch.cuda.get_device_name(dev)}', flush=True)
"
