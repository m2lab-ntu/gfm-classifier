#!/bin/bash
#SBATCH -A MST114550
#SBATCH -J mt_benchmark
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=200G
#SBATCH -t 01:00:00
#SBATCH -o /work/ymj1123ntu/logs/mt_benchmark-%j.out
#SBATCH -e /work/ymj1123ntu/logs/mt_benchmark-%j.err

# ============================================================
# Speed / memory benchmark — all GFM and MT models on H200
# Reports: throughput (reads/sec), latency (ms/read), peak GPU (MiB)
# ============================================================

set -uo pipefail

REPO=/work/ymj1123ntu/gfm-classifier
SCRIPTS=${REPO}/scripts
DATA=/work/ymj1123ntu/data
MT_ROOT=/work/ymj1123ntu/mt_models
MT_SRC=/work/ymj1123ntu/MetaTransformer/src
VOCAB_13=/work/ymj1123ntu/MetaTransformer/vocab_file/vocab_13mer.txt
VOCAB_6=/work/ymj1123ntu/gfm-classifier/small_predictions/vocab_6mer.txt
VAL_DIR=/work/ymj1123ntu/benchmark_data
OUT_ROOT=/work/ymj1123ntu/benchmark_results
LOG_DIR=/work/ymj1123ntu/logs
N_READS=100000
BATCH=1024

mkdir -p ${OUT_ROOT} ${LOG_DIR}

echo "========================================================"
echo "MT Speed/Memory Benchmark — Nano4 H200"
echo "Node: $(hostname) | Start: $(date)"
echo "========================================================"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
echo ""

module load miniconda3/26.1.1
source $(conda info --base)/etc/profile.d/conda.sh
conda activate gfm

export HF_HOME=/work/ymj1123ntu/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/work/ymj1123ntu/.cache/huggingface
export PYTHONUNBUFFERED=1

# ── timing helper ─────────────────────────────────────────────────────────────
RESULTS_CSV=${OUT_ROOT}/benchmark_summary.csv
echo "model,n_reads,elapsed_sec,reads_per_sec,ms_per_read,peak_gpu_mib" > ${RESULTS_CSV}

run_benchmark() {
    local MODEL_NAME="$1"
    local CMD="$2"

    echo ""
    echo "──────────────────────────────────────────"
    echo "MODEL: ${MODEL_NAME}"
    echo "CMD:   ${CMD}"
    echo "──────────────────────────────────────────"

    # Export PYTHONPATH for MetaTransformer (must be set before eval, not inline)
    export PYTHONPATH="${MT_SRC}"

    # Start background GPU monitor (sample every 2s)
    GPU_LOG=/tmp/gpu_monitor_$$.log
    ( while true; do
          nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits >> ${GPU_LOG}
          sleep 2
      done ) &
    MONITOR_PID=$!

    T_START=$(date +%s%N)
    eval "${CMD}" 2>&1
    STATUS=$?
    T_END=$(date +%s%N)

    kill ${MONITOR_PID} 2>/dev/null || true
    ELAPSED_SEC=$(python3 -c "print(f'{($T_END - $T_START) / 1e9:.2f}')")
    READS_PER_SEC=$(python3 -c "print(f'{${N_READS} / (($T_END - $T_START) / 1e9):.1f}')")
    MS_PER_READ=$(python3 -c "print(f'{($T_END - $T_START) / 1e6 / ${N_READS}:.4f}')")
    PEAK_GPU=$(sort -n ${GPU_LOG} 2>/dev/null | tail -1 || echo "N/A")
    rm -f ${GPU_LOG}

    if [ ${STATUS} -ne 0 ]; then
        echo "  ⚠ FAILED (exit ${STATUS})"
        echo "${MODEL_NAME},${N_READS},FAILED,FAILED,FAILED,FAILED" >> ${RESULTS_CSV}
        return
    fi

    echo ""
    echo "  Elapsed:     ${ELAPSED_SEC} s"
    echo "  Throughput:  ${READS_PER_SEC} reads/sec"
    echo "  Latency:     ${MS_PER_READ} ms/read"
    echo "  Peak GPU:    ${PEAK_GPU} MiB"
    echo "${MODEL_NAME},${N_READS},${ELAPSED_SEC},${READS_PER_SEC},${MS_PER_READ},${PEAK_GPU}" >> ${RESULTS_CSV}
}

# ── 1. NT-v2 sp_v4 (species, LoRA fine-tuned) ────────────────────────────────
run_benchmark "NT-v2_sp_v4_species" \
    "python ${SCRIPTS}/run_nt_species_test100k.py \
        --config        ${REPO}/configs/nt_token_species_v4_50M.yaml \
        --checkpoint    ${DATA}/../checkpoints/nt_token_species_v4_50M_best.pt \
        --test_fasta    ${DATA}/reads_100K.fa \
        --test_labels   ${DATA}/labels_100K.tsv \
        --train_labels  ${DATA}/labels_50M.tsv \
        --out_dir       ${OUT_ROOT}/nt_sp_v4 \
        --batch_size    ${BATCH}"

# ── 2. MT 13mer stride1 species ──────────────────────────────────────────────
run_benchmark "MT_13mer_stride1_species" \
    "python ${SCRIPTS}/extract_mt_predictions.py \
        --exp_dir       ${MT_ROOT}/mt_13mer_stride1_species_895688 \
        --val_dir       ${VAL_DIR} \
        --vocab         ${VOCAB_13} \
        --out           ${OUT_ROOT}/mt_13mer_stride1_species.npz \
        --class_indices 1 \
        --batch_size    ${BATCH}"

# ── 3. MT 13mer stride1 genus ─────────────────────────────────────────────────
run_benchmark "MT_13mer_stride1_genus" \
    "python ${SCRIPTS}/extract_mt_predictions.py \
        --exp_dir       ${MT_ROOT}/mt_13mer_stride1_genus_895686 \
        --val_dir       ${VAL_DIR} \
        --vocab         ${VOCAB_13} \
        --out           ${OUT_ROOT}/mt_13mer_stride1_genus.npz \
        --class_indices 3 \
        --batch_size    ${BATCH}"

# ── 4. MT 6mer stride1 species ───────────────────────────────────────────────
run_benchmark "MT_6mer_stride1_species" \
    "python ${SCRIPTS}/extract_mt_predictions.py \
        --exp_dir       ${MT_ROOT}/mt_6mer_stride1_species_894641 \
        --val_dir       ${VAL_DIR} \
        --vocab         ${VOCAB_6} \
        --out           ${OUT_ROOT}/mt_6mer_stride1_species.npz \
        --class_indices 1 \
        --batch_size    ${BATCH}"

# ── 5. MT 6mer stride6 species ───────────────────────────────────────────────
run_benchmark "MT_6mer_stride6_species" \
    "python ${SCRIPTS}/extract_mt_predictions.py \
        --exp_dir       ${MT_ROOT}/mt_6mer_stride6_species_894640 \
        --val_dir       ${VAL_DIR} \
        --vocab         ${VOCAB_6} \
        --out           ${OUT_ROOT}/mt_6mer_stride6_species.npz \
        --class_indices 1 \
        --batch_size    ${BATCH}"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "========================================================"
echo "BENCHMARK SUMMARY"
echo "========================================================"
column -t -s ',' ${RESULTS_CSV}
echo ""
echo "Full results: ${RESULTS_CSV}"
echo "Done: $(date)"
