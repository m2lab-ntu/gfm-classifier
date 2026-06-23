#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J train_speed
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=200G
#SBATCH -t 01:00:00
#SBATCH -o /work/ymj1123ntu/logs/train_speed-%j.out
#SBATCH -e /work/ymj1123ntu/logs/train_speed-%j.err

# ============================================================
# Controlled TRAINING-throughput probe — same 7 models as the
# inference benchmark (benchmark_summary.csv). 1x H200, fixed
# batch, fwd+bwd loop timed internally (warmup excluded).
# ============================================================
set -uo pipefail

REPO=/work/ymj1123ntu/gfm-classifier
SCRIPTS=${REPO}/scripts
CONF=${REPO}/configs
MT_SRC=/work/ymj1123ntu/MetaTransformer/src
MT_ROOT=/work/ymj1123ntu/mt_models
VOCAB_13=/work/ymj1123ntu/MetaTransformer/vocab_file/vocab_13mer.txt
VOCAB_6=/work/ymj1123ntu/gfm-classifier/small_predictions/vocab_6mer.txt
OUT=/work/ymj1123ntu/benchmark_results/compute_speed_summary.csv
CKPT=/work/ymj1123ntu/checkpoints

BATCH=128
STEPS=30
WARMUP=8

rm -f ${OUT}

echo "========================================================"
echo "TRAIN-speed probe | Node: $(hostname) | Start: $(date)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo "========================================================"

module load miniconda3/26.1.1
source $(conda info --base)/etc/profile.d/conda.sh
conda activate gfm
export HF_HOME=/work/ymj1123ntu/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface
export PYTHONUNBUFFERED=1

VOCAB_13_N=$(wc -l < ${VOCAB_13})
VOCAB_6_N=$(wc -l < ${VOCAB_6})
echo "vocab_13 lines=${VOCAB_13_N}  vocab_6 lines=${VOCAB_6_N}"

# ── NT-family (create_model from config) ──────────────────────────────────────
nt() {  # label  config  num_classes
    echo ""; echo "──────── ${1} ────────"
    python ${SCRIPTS}/probe_train_speed.py \
        --config "${2}" --num_classes "${3}" --label "${1}" \
        --batch ${BATCH} --steps ${STEPS} --warmup ${WARMUP} --csv ${OUT} \
        || echo "  ⚠ ${1} FAILED"
}

nt "NT-v2_v9_genus"      "${CONF}/nt_token_genus_v9_50M.yaml"    120
nt "NT-v2_sp_v4_species" "${CONF}/nt_token_species_v4_50M.yaml"  1535

# ── MetaTransformer (instantiate from exp_dir config) ─────────────────────────
mt() {  # label  exp_dir  vocab_dim  seqlen_tokens
    echo ""; echo "──────── ${1} ────────"
    ( cd ${MT_SRC} && PYTHONPATH=${MT_SRC} python probe_train_speed_mt.py \
        --exp_dir "${2}" --vocab_dim "${3}" --seqlen_tokens "${4}" --label "${1}" \
        --batch ${BATCH} --steps ${STEPS} --warmup ${WARMUP} --csv ${OUT} ) \
        || echo "  ⚠ ${1} FAILED"
}

# 150 bp token counts: kmer s1 -> 150-k+1 ; stride s -> (150-k)//s + 1
mt "MT_13mer_stride1_species"  "${MT_ROOT}/mt_13mer_stride1_species_895688"  ${VOCAB_13_N} 138
mt "MT_13mer_stride1_genus"    "${MT_ROOT}/mt_13mer_stride1_genus_895686"    ${VOCAB_13_N} 138
mt "MT_6mer_stride1_species"   "${MT_ROOT}/mt_6mer_stride1_species_894641"   ${VOCAB_6_N}  145
mt "MT_6mer_stride6_species"   "${MT_ROOT}/mt_6mer_stride6_species_894640"   ${VOCAB_6_N}  25
mt "MT_13mer_stride13_genus"   "${MT_ROOT}/mt_13mer_stride13_genus_895685"   ${VOCAB_13_N} 11

echo ""
echo "========================================================"
echo "TRAIN-speed SUMMARY (batch=${BATCH}, steps=${STEPS}, warmup=${WARMUP})"
echo "========================================================"
column -t -s ',' ${OUT} 2>/dev/null || cat ${OUT}
echo "Done: $(date)"
