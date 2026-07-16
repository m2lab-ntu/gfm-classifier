#!/bin/bash
# ================================================================
# Track A — end-to-end pipeline (new-genome generalization eval)
#
# Run from the repo root:
#   cd /home/user/projects/gfm-classifier
#   bash local_realworld_eval/run_track_a.sh
#
# ── Prerequisites (do ONCE before running this script) ────────
#  1. Transfer assets from Nano4 (2FA needed):
#       bash local_realworld_eval/fetch_assets_nano4.sh
#  2. Conda env (already running in background; check with
#       conda env list | grep gfm-local):
#       conda env create -f local_realworld_eval/environment.yml
#
# ── What this script does ─────────────────────────────────────
#  Step 1  Download 1-3 new genomes per genus, excluding training accessions
#  Step 2  Simulate 10× Illumina reads with ART (150bp, HS25)
#  Step 3  Merge per-genus FASATAs → newgenome_test.fa + labels.tsv
#  Step 4  Inference: MT 250M / MT 50M / NT-v2 v9
#  Step 5  Metrics: per-read Top-1 + sample-level Pearson r
#
# Total expected runtime on 4090: ~3–5 hr
#   (genome download ~30 min, ART ~30 min, inference ~2–3 hr)
# ================================================================

set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO}"

LRE="local_realworld_eval"

# Large data lives on NAS (override with DATA_ROOT=/other/path)
DATA_ROOT="${DATA_ROOT:-/nas2/gfm-classifier/track_a}"
ASSETS="${DATA_ROOT}/assets"
GENOMES="${DATA_ROOT}/genomes"
READS="${DATA_ROOT}/reads"
TEST_DATA="${DATA_ROOT}/test_data"

export DATA_ROOT  # pass down to inference/metrics sub-scripts

# ── Activate conda env ────────────────────────────────────────
conda activate gfm-local 2>/dev/null || \
  source "$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null && \
  conda activate gfm-local 2>/dev/null || true

echo ""
echo "================================================================"
echo " GFM Classifier — Track A: New-Genome Generalization Eval"
echo " $(date)"
echo " DATA_ROOT = ${DATA_ROOT}"
echo "================================================================"
echo ""

# ── Preflight checks ──────────────────────────────────────────
echo "  DATA_ROOT = ${DATA_ROOT}"
fail=0
for f in \
    "${ASSETS}/genus_map.tsv" \
    "${ASSETS}/mt_13mer_250M/checkpoints/classification_transformer_ckpt_best.pt" \
    "${ASSETS}/mt_13mer_50M/checkpoints/classification_transformer_ckpt_best.pt" \
    "${ASSETS}/nt_v9/nt_token_genus_v9_50M_best.pt" \
    "${ASSETS}/vocab_13mer.txt" \
    "${ASSETS}/MetaTransformer_src"; do
    if [[ ! -e "${f}" ]]; then
        echo "  MISSING: ${f}"
        fail=1
    fi
done
if [[ ${fail} -eq 1 ]]; then
    echo ""
    echo "ERROR: Assets missing.  Run first:"
    echo "  bash ${LRE}/fetch_assets_nano4.sh   (needs Nano4 2FA)"
    echo "  (assets will land under DATA_ROOT=${DATA_ROOT}/assets)"
    exit 1
fi
echo "  Preflight: all assets present ✓"
echo ""

# Ensure NAS directories exist
mkdir -p "${ASSETS}" "${GENOMES}" "${READS}" "${TEST_DATA}"

# ── Step 1: Download genomes ──────────────────────────────────
echo "================================================================"
echo " Step 1/5  Download new genomes from NCBI"
echo "================================================================"
python "${LRE}/track_a_01_download_genomes.py" \
    --labels   "${ASSETS}/genus_map.tsv" \
    --out_dir  "${GENOMES}" \
    --max_per_genus 2 \
    --assembly_level "complete,chromosome,scaffold" \
    --exclude_accessions "${LRE}/track_a_training_gcf_accessions.txt" \
    --skip_existing
echo ""

# ── Step 2: Simulate reads ────────────────────────────────────
echo "================================================================"
echo " Step 2/5  Simulate reads with ART (coverage=10×)"
echo "================================================================"
python "${LRE}/track_a_02_simulate_reads.py" \
    --labels      "${ASSETS}/genus_map.tsv" \
    --genome_dir  "${GENOMES}" \
    --out_dir     "${READS}" \
    --coverage    10 \
    --skip_existing
echo ""

# ── Step 3: Build test FASTA ──────────────────────────────────
echo "================================================================"
echo " Step 3/5  Merge reads → newgenome_test.fa"
echo "================================================================"
bash "${LRE}/track_a_03_build_test_fasta.sh" \
    "${READS}" "${TEST_DATA}" 5000
echo ""

# ── Step 4: Inference ─────────────────────────────────────────
echo "================================================================"
echo " Step 4/5  Inference (MT 250M + MT 50M + NT-v2 v9)"
echo "================================================================"
bash "${LRE}/track_a_04_run_inference.sh"
echo ""

# ── Step 5: Metrics ───────────────────────────────────────────
echo "================================================================"
echo " Step 5/5  Compute metrics"
echo "================================================================"
bash "${LRE}/track_a_05_metrics.sh"
echo ""

# ── Step 6: Accession-overlap audit and clean metrics ─────────
python "${LRE}/track_a_06_clean_metrics.py" \
    --test-fasta "${TEST_DATA}/newgenome_test.fa" \
    --exclude-accessions "${LRE}/track_a_training_gcf_accessions.txt" \
    --prediction "mt_250M=${DATA_ROOT}/out/mt_250M/preds.npz" \
    --prediction "mt_50M=${DATA_ROOT}/out/mt_50M/preds.npz" \
    --prediction "nt_v9=${DATA_ROOT}/out/nt_v9/preds.npz" \
    --output "${DATA_ROOT}/out/metrics_clean.json"
echo ""

echo "================================================================"
echo " Track A complete.  $(date)"
echo " Results: ${DATA_ROOT}/out/"
echo "================================================================"
