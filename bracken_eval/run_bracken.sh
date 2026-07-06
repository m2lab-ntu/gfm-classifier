#!/usr/bin/env bash
# Run Bracken on the existing Kraken 2 report (TWCC / nano5, where the custom DB lives).
# Usage: bash run_bracken.sh <KRAKEN2_DB_DIR> [READLEN=150] [THREADS=8]
set -euo pipefail

KRAKEN2_DB="${1:?path to the custom Kraken2 DB (the one used for reads_100K.kraken2.report)}"
READLEN="${2:-150}"
THREADS="${3:-8}"
KMER=35            # must match how the Kraken2 DB was built (metadata: kraken2_k=35)

REPORT="${REPORT:-reads_100K.kraken2.report}"   # copy from gfm-classifier/small_predictions/
if [[ ! -f "$REPORT" ]]; then
  echo "ERROR: $REPORT not found. Copy it from gfm-classifier/small_predictions/." >&2
  exit 1
fi

command -v bracken       >/dev/null || { echo "install bracken: conda install -c bioconda bracken" >&2; exit 1; }
command -v bracken-build >/dev/null || { echo "bracken-build not on PATH (comes with bracken)"     >&2; exit 1; }

echo "== Step 1: bracken-build (one-time; builds databaseXmers.kmer_distrib) =="
# Needs kraken2 on PATH and the DB's library/ + taxonomy/ still present.
# If it errors that the library was cleaned, rebuild the Kraken2 DB first:
#   kraken2-build --build --db "$KRAKEN2_DB" --threads "$THREADS"   (needs the original library)
if [[ ! -f "$KRAKEN2_DB/database${READLEN}mers.kmer_distrib" ]]; then
  bracken-build -d "$KRAKEN2_DB" -t "$THREADS" -k "$KMER" -l "$READLEN"
else
  echo "  kmer_distrib for l=$READLEN already exists; skipping build."
fi

echo "== Step 2: bracken at SPECIES level on the report =="
# The custom DB taxonomy is flat (root -> species, no genus node), so run at -l S
# and aggregate species -> genus afterwards with eval_bracken.py + the crosswalk.
bracken -d "$KRAKEN2_DB" \
        -i "$REPORT" \
        -o reads_100K.bracken.species.tsv \
        -w reads_100K.bracken.species.report \
        -r "$READLEN" -l S -t 1

echo "== Done =="
echo "  -> reads_100K.bracken.species.tsv   (feed to eval_bracken.py)"
echo "  -> reads_100K.bracken.species.report"
