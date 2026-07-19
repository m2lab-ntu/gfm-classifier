#!/usr/bin/env bash
# Full D6331 Replicate-2 (SRR33710518) mock pipeline — all I/O on /nas2.
set -euo pipefail

source /home/user/anaconda3/etc/profile.d/conda.sh
conda activate gfm-local

REPO=/home/user/projects/gfm-classifier
BASE=/nas2/gfm-classifier
ASSETS=$BASE/track_a/assets
MOCK=$BASE/mock_community
REP2=$MOCK/rep2
DB=/nas2/hierachical_test/kraken2_db
ACC=SRR33710518
NREADS=3000000
THREADS=16

NT_PYTHON=/home/user/anaconda3/envs/gfm-local/bin/python
MT_PYTHON=/home/user/anaconda3/envs/MetaTransformer/bin/python
GM=$ASSETS/genus_map.tsv
COMP=$MOCK/composition.csv
CROSSWALK=$REPO/bracken_eval/species_N_to_genus.tsv

mkdir -p "$REP2"/{sra,reads,logs,test_data,out/mock_ntv2,out/mock_mt13,out/mock_kraken2bracken,out/enhanced}

log() { echo "[$(date '+%F %T')] $*"; }

# ---------- 1. wait for / extract SRA ----------
SRA_FILE=$(find "$REP2/sra" -name "${ACC}.sra" 2>/dev/null | head -1 || true)
if [[ -z "${SRA_FILE}" ]]; then
  log "Waiting for prefetch of ${ACC} ..."
  while [[ ! -f "$REP2/sra/${ACC}/${ACC}.sra" && ! -f "$REP2/sra/${ACC}.sra" ]]; do
    if ! pgrep -f "prefetch ${ACC}" >/dev/null 2>&1; then
      # maybe finished into unexpected path
      SRA_FILE=$(find "$REP2/sra" -name "${ACC}.sra" 2>/dev/null | head -1 || true)
      [[ -n "${SRA_FILE}" ]] && break
      log "prefetch not running and no .sra — attempting prefetch"
      prefetch "$ACC" -O "$REP2/sra" >>"$REP2/logs/prefetch.log" 2>&1 || true
      break
    fi
    du -sh "$REP2/sra"/* 2>/dev/null | tail -1 || true
    sleep 30
  done
  SRA_FILE=$(find "$REP2/sra" -name "${ACC}.sra" 2>/dev/null | head -1)
fi
log "SRA file: $SRA_FILE"
ls -lh "$SRA_FILE"

if [[ ! -f "$REP2/reads/${ACC}_1.fastq" ]]; then
  log "fasterq-dump (split-files) ..."
  fasterq-dump "$SRA_FILE" -O "$REP2/reads" --split-files -e "$THREADS" \
    --temp "$REP2/fasterq_tmp" -p >>"$REP2/logs/fasterq.log" 2>&1
fi
ls -lh "$REP2/reads/${ACC}"_*.fastq

# ---------- 2. prep FASTA ----------
if [[ ! -f "$REP2/test_data/mock.fa" ]]; then
  log "prep_reads (subsample ${NREADS}) ..."
  $NT_PYTHON "$MOCK/prep_reads.py" \
    --fastq "$REP2/reads/${ACC}_1.fastq" \
    --out_fa "$REP2/test_data/mock.fa" \
    --out_labels "$REP2/test_data/dummy_labels.tsv" \
    --max_reads "$NREADS" | tee "$REP2/logs/prep.log"
  mkdir -p "$REP2/test_data/val_dir"
  # MT val_dir must contain ONLY the fasta
  ln -sfn "$REP2/test_data/mock.fa" "$REP2/test_data/val_dir/mock.fa"
fi

# ---------- 3. NT-v2 ----------
if [[ ! -f "$REP2/out/mock_ntv2/rctta.npz" ]]; then
  log "NT-v2 RC-TTA inference ..."
  $NT_PYTHON "$REPO/scripts/run_genus_rctta.py" \
    --config "$REPO/configs/nt_token_genus_v9_50M.yaml" \
    --checkpoint "$ASSETS/nt_v9/nt_token_genus_v9_50M_best.pt" \
    --test_fasta "$REP2/test_data/mock.fa" \
    --test_labels "$REP2/test_data/dummy_labels.tsv" \
    --train_labels "$GM" \
    --out_dir "$REP2/out/mock_ntv2" \
    --batch_size 256 \
    2>&1 | tee "$REP2/logs/ntv2.log"
fi

# ---------- 4. MT 13-mer ----------
if [[ ! -f "$REP2/out/mock_mt13/preds.npz" ]]; then
  log "MT 13-mer 250M inference ..."
  PYTHONPATH="$ASSETS/MetaTransformer_src" $MT_PYTHON "$REPO/scripts/extract_mt_predictions.py" \
    --exp_dir "$ASSETS/mt_13mer_250M" \
    --val_dir "$REP2/test_data/val_dir" \
    --vocab "$ASSETS/vocab_13mer.txt" \
    --out "$REP2/out/mock_mt13/preds.npz" \
    --class_indices 3 \
    --batch_size 1024 \
    2>&1 | tee "$REP2/logs/mt13.log"
fi

# ---------- 5. Kraken2 + Bracken ----------
KDIR=$REP2/out/mock_kraken2bracken
if [[ ! -f "$KDIR/mock.kreport" ]]; then
  log "Kraken2 classify ..."
  kraken2 --db "$DB" --threads "$THREADS" \
    --output "$KDIR/mock.kraken.out" \
    --report "$KDIR/mock.kreport" \
    "$REP2/test_data/mock.fa" \
    2>&1 | tee "$REP2/logs/kraken2.log"
fi
if [[ ! -f "$KDIR/mock.bracken.species.tsv" ]]; then
  log "Bracken (read len 135, level S) ..."
  bracken -d "$DB" -i "$KDIR/mock.kreport" \
    -o "$KDIR/mock.bracken.species.tsv" \
    -w "$KDIR/mock.bracken.report" \
    -r 150 -l S \
    2>&1 | tee "$REP2/logs/bracken.log"
fi
if [[ ! -f "$KDIR/kraken2_bracken_mock_genus.csv" ]]; then
  log "aggregate Bracken -> genus CSV ..."
  $NT_PYTHON - <<'PY'
import pandas as pd
from pathlib import Path
rep2 = Path("/nas2/gfm-classifier/mock_community/rep2/out/mock_kraken2bracken")
cw = pd.read_csv("/home/user/projects/gfm-classifier/bracken_eval/species_N_to_genus.tsv", sep="\t")
br = pd.read_csv(rep2 / "mock.bracken.species.tsv", sep="\t")
br["species_N"] = br["name"].astype(str).str.replace("species_", "", regex=False).astype(int)
m = br.merge(cw[["species_N", "genus_name"]], on="species_N", how="left")
assert m["genus_name"].notna().all()
g = m.groupby("genus_name", as_index=False)["fraction_total_reads"].sum()
g = g.rename(columns={"fraction_total_reads": "pred_fraction"}).sort_values("pred_fraction", ascending=False)
g.to_csv(rep2 / "kraken2_bracken_mock_genus.csv", index=False)
print(g.head(10).to_string(index=False))
print("sum", g.pred_fraction.sum())
PY
fi

# ---------- 6. enhanced eval ----------
log "enhanced eval ..."

$NT_PYTHON "$MOCK/reeval_enhanced.py" \
  --genus_map "$GM" --composition "$COMP" \
  --preds_npz "$REP2/out/mock_ntv2/rctta.npz" \
  --exp_name "NT-v2 v9 (RC-TTA) Rep2" \
  --also_remap_clostridioides \
  --out "$REP2/out/enhanced/ntv2.json"

$NT_PYTHON "$MOCK/reeval_enhanced.py" \
  --genus_map "$GM" --composition "$COMP" \
  --preds_npz "$REP2/out/mock_mt13/preds.npz" \
  --exp_name "MT 13-mer 250M Rep2" \
  --also_remap_clostridioides \
  --out "$REP2/out/enhanced/mt13.json"

$NT_PYTHON "$MOCK/reeval_enhanced.py" \
  --genus_map "$GM" --composition "$COMP" \
  --pred_abundance_csv "$KDIR/kraken2_bracken_mock_genus.csv" \
  --exp_name "Kraken2+Bracken Rep2" \
  --also_remap_clostridioides \
  --out "$REP2/out/enhanced/kraken2bracken.json"

# ---------- 7. combined summary ----------
$NT_PYTHON - <<'PY'
import json
from pathlib import Path

def load(p):
    return json.load(open(p))["primary"]

rep1 = Path("/nas2/gfm-classifier/mock_community/out/enhanced_rep1")
rep2 = Path("/nas2/gfm-classifier/mock_community/rep2/out/enhanced")
keys = [
    ("NT-v2 v9 (RC-TTA)", "ntv2.json"),
    ("MT 13-mer 250M", "mt13.json"),
    ("Kraken2+Bracken", "kraken2bracken.json"),
]
summary = {
    "mock_community": "ZymoBIOMICS Gut Microbiome Standard (D6331)",
    "composition_reference": "Genomic DNA %",
    "replicates": {
        "rep1": {"accession": "SRR33710519", "reads": "3M R1"},
        "rep2": {"accession": "SRR33710518", "reads": "3M R1"},
    },
    "models": {},
}
for name, fn in keys:
    a = load(rep1 / fn)
    b = load(rep2 / fn)
    summary["models"][name] = {
        "rep1": {
            "pearson_r": a["pearson_r_in_set"],
            "pearson_ci95": a["pearson_r_bootstrap_ci95"],
            "spearman_rho": a["spearman_rho_in_set"],
            "bray_curtis": a["bray_curtis_in_set"],
            "pearson_r_filtered_ge_1pct": a["filtered_ge_1pct"]["pearson_r"],
            "sens_expected_ge_1pct": a["detection_sensitivity_expected_ge_1pct"],
            "fp_genera": a["false_positive_genera"],
        },
        "rep2": {
            "pearson_r": b["pearson_r_in_set"],
            "pearson_ci95": b["pearson_r_bootstrap_ci95"],
            "spearman_rho": b["spearman_rho_in_set"],
            "bray_curtis": b["bray_curtis_in_set"],
            "pearson_r_filtered_ge_1pct": b["filtered_ge_1pct"]["pearson_r"],
            "sens_expected_ge_1pct": b["detection_sensitivity_expected_ge_1pct"],
            "fp_genera": b["false_positive_genera"],
        },
        "mean_r": (a["pearson_r_in_set"] + b["pearson_r_in_set"]) / 2,
        "mean_bc": (a["bray_curtis_in_set"] + b["bray_curtis_in_set"]) / 2,
        "mean_rho": (a["spearman_rho_in_set"] + b["spearman_rho_in_set"]) / 2,
        "mean_r_filtered_1pct": (
            a["filtered_ge_1pct"]["pearson_r"] + b["filtered_ge_1pct"]["pearson_r"]
        ) / 2,
    }

outp = Path("/nas2/gfm-classifier/mock_community/out/mock_reps_combined_summary.json")
json.dump(summary, open(outp, "w"), indent=2)
print(json.dumps(summary, indent=2))
print("saved", outp)
PY

log "ALL DONE"
