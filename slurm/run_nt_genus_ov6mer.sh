#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J nt_ov6mer
#SBATCH -p 16gpus
#SBATCH --nodes=1 --ntasks-per-node=8 --gres=gpu:8 --cpus-per-task=8 --mem=0
#SBATCH --requeue
#SBATCH -t 2-00:00:00
#SBATCH -o /work/ymj1123ntu/logs/nt_ov6mer-%j.out
#SBATCH -e /work/ymj1123ntu/logs/nt_ov6mer-%j.err
# NT-v2 + LoRA + OVERLAPPING 6-mer (kmer_preprocess s=1) on 17.6M species-bal data.
# Control: does feeding overlapping 6-mers to NT-v2's pretrained embeddings break
# the ~67% 6-mer ceiling? (vs sbal non-overlap, same data). Auto-resume.
set -uo pipefail
REPO=/work/ymj1123ntu/gfm-classifier; SCRIPTS=${REPO}/scripts
CONFIG=${REPO}/configs/nt_token_genus_ov6mer_17M.yaml
CKPT_DIR=/work/ymj1123ntu/checkpoints/nt_token_genus_ov6mer_17M
IDX=/work/ymj1123ntu/data/balanced_species_17M/reads.idx.npy
mkdir -p ${CKPT_DIR}
module load miniconda3/26.1.1; source $(conda info --base)/etc/profile.d/conda.sh; conda activate gfm
export HF_HOME=/work/ymj1123ntu/.cache/huggingface HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface
export OMP_NUM_THREADS=8 PYTHONUNBUFFERED=1 NCCL_DEBUG=WARN
echo "=== NT-v2 overlap-6mer  Job $SLURM_JOB_ID  $(date) ==="
[ -f "${IDX}" ] || { echo "ERROR: idx ${IDX} missing"; exit 1; }
export MASTER_ADDR=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -1); export MASTER_PORT=29503
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1
cd ${SCRIPTS}
LAST=${CKPT_DIR}/last.pt
if [ -f "${LAST}" ]; then RES="--resume ${LAST}"; echo "resume"; else RES=""; echo "fresh"; fi
srun python train_ddp.py --config ${CONFIG} ${RES} --time_limit_sec 82800 2>&1
echo "=== done $(date) ==="; tail -1 ${CKPT_DIR}/training_history.csv 2>/dev/null
