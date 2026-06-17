#!/bin/bash
#SBATCH -A MST114414
#SBATCH -J prebuild_idx_250M
#SBATCH -p dev
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH -t 02:00:00
#SBATCH -o /work/ymj1123ntu/logs/prebuild_idx_250M-%j.out
#SBATCH -e /work/ymj1123ntu/logs/prebuild_idx_250M-%j.err

# ============================================================
# Pre-build the LazyFASTADataset index for balanced_250M.
#
# Why a separate job: train_ddp instantiates the dataset on all
# 64 ranks concurrently; for a brand-new index that races on the
# same .idx.npy write. Build it once here (single process) so the
# DDP job loads it from cache. v14 is submitted with
# --dependency=afterok on this job.
#
# NOTE: the naive dataset_lazy._build_index (Python line loop +
# 250M-tuple list) OOM-stalls at ~230M reads on a 32G node and is
# NFS-slow. We instead use grep -b (C-speed offset scan) | awk
# (field extract) | pandas (vectorised array build) → ~15-20 min,
# few-GB peak. Output is byte-identical in schema to _build_index:
# structured array [(offset i8, genus i4, species i4)] in file order.
# Header: >lbl|<species>|<name>|<genus>|<genus_name>-<read>  → after
# `grep -b`, fields under -F'[:|]' are $1=offset $3=species $5=genus.
# ============================================================

set -euo pipefail

REPO=/work/ymj1123ntu/gfm-classifier
FASTA=/work/ymj1123ntu/data/balanced_250M/reads_250M.fa
IDX=/work/ymj1123ntu/data/balanced_250M/reads_250M.idx.npy

mkdir -p /work/ymj1123ntu/logs

module load miniconda3/26.1.1 2>/dev/null || true
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate gfm
export PYTHONUNBUFFERED=1

echo "=== Pre-building index (grep|awk|pandas): $(date) on $(hostname) ==="
cd "${REPO}/scripts"

# grep -ab '^>'  → "<byteoffset>:<header>" per read, C-speed sequential scan.
# awk            → emit "offset<TAB>genus<TAB>species" (note: dtype order).
# python/pandas  → vectorised build of the structured npy, file order preserved.
grep -ab '^>' "${FASTA}" \
  | awk -F'[:|]' '{print $1"\t"$5"\t"$3}' \
  | python -c "
import sys, numpy as np, pandas as pd
df = pd.read_csv(sys.stdin, sep='\t', header=None,
                 names=['offset','genus','species'], dtype=np.int64)
dt = np.dtype([('offset', np.int64), ('genus', np.int32), ('species', np.int32)])
a = np.empty(len(df), dtype=dt)
a['offset']  = df['offset'].to_numpy()
a['genus']   = df['genus'].to_numpy()
a['species'] = df['species'].to_numpy()
np.save('${IDX}', a)
print(f'Index saved: {len(a):,} reads, genera={np.unique(a[\"genus\"]).size}, species={np.unique(a[\"species\"]).size}')
"
echo "=== Done: $(date) ==="
ls -la "${IDX}"
