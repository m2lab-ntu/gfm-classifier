#!/bin/bash
#SBATCH -A MST114414
#SBATCH -J subsample_17M
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH -t 04:00:00
#SBATCH -o /work/ymj1123ntu/logs/subsample_17M-%j.out
#SBATCH -e /work/ymj1123ntu/logs/subsample_17M-%j.err

# ============================================================
# Build a 17.64M genus- OR species-balanced dataset (+ index)
# for the genus-balance-vs-species-balance experiment.
#
#   Usage:  sbatch run_subsample_17M.sh genus
#           sbatch run_subsample_17M.sh species
#
# Source = species-balanced 250M (correct 1535sp). 17.64M is the
# largest TRUE genus balance with NO upsampling: rarest genus
# (Cellulomonas) has 147,102 reads, so target = 147,000/genus.
# The species control uses the SAME total (11,491/species) so the
# ONLY difference vs the genus run is the balance axis.
# GPU requested only for the dev-partition QOSMinGRES rule (CPU/IO job).
# ============================================================
set -euo pipefail

MODE="${1:?usage: sbatch run_subsample_17M.sh <genus|species>}"
REPO=/work/ymj1123ntu/gfm-classifier
SRC=/work/ymj1123ntu/data/balanced_250M/reads_250M.fa
TOTAL=17640000

case "${MODE}" in
  genus)   OUT_DIR=/work/ymj1123ntu/data/balanced_genus_17M ;;
  species) OUT_DIR=/work/ymj1123ntu/data/balanced_species_17M ;;
  *) echo "MODE must be genus|species"; exit 1 ;;
esac
FASTA=${OUT_DIR}/reads.fa
LABELS=${OUT_DIR}/labels.tsv
IDX=${OUT_DIR}/reads.idx.npy

mkdir -p "${OUT_DIR}" /work/ymj1123ntu/logs
module load miniconda3/26.1.1 2>/dev/null || true
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate gfm
export PYTHONUNBUFFERED=1

echo "================================================================"
echo "Subsample 17.64M  mode=${MODE}  Job ${SLURM_JOB_ID}  $(date)"
echo "  src=${SRC}"
echo "  out=${OUT_DIR}"
echo "================================================================"

cd "${REPO}/scripts"
python -u subsample_balanced.py \
    --input         "${SRC}" \
    --output_fasta  "${FASTA}" \
    --output_labels "${LABELS}" \
    --total_reads   ${TOTAL} \
    --balance_by    "${MODE}" \
    --seed          42

echo ""
echo "=== Building lazy-dataset index: $(date) ==="
# byte-offset scan (C-speed) -> offset,genus,species -> structured npy.
# header: >lbl|<species>|<name>|<genus>|<genus_name>-<read>
# after `grep -ab`, -F'[:|]' gives $1=offset $3=species $5=genus.
grep -ab '^>' "${FASTA}" \
  | awk -F'[:|]' '{print $1"\t"$5"\t"$3}' \
  | python -c "
import sys, numpy as np, pandas as pd
df = pd.read_csv(sys.stdin, sep='\t', header=None,
                 names=['offset','genus','species'], dtype=np.int64)
dt = np.dtype([('offset', np.int64), ('genus', np.int32), ('species', np.int32)])
a = np.empty(len(df), dtype=dt)
a['offset']=df['offset'].to_numpy(); a['genus']=df['genus'].to_numpy(); a['species']=df['species'].to_numpy()
np.save('${IDX}', a)
print(f'Index: {len(a):,} reads, genera={np.unique(a[\"genus\"]).size}, species={np.unique(a[\"species\"]).size}')
"
echo "================================================================"
echo "Done: $(date)"
echo "FASTA:  $(du -sh ${FASTA} | cut -f1)   Labels: $(wc -l < ${LABELS}) lines   Index: $(ls -la ${IDX} | awk '{print $5}') B"
echo "================================================================"
