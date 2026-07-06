# Bracken abundance baseline — TWCC handoff

**Why.** The manuscript compares neural sample-level abundance against **raw**
Kraken 2 report counts (genus Pearson r = 0.823), and a reviewer will rightly
ask: raw Kraken 2 abundance is deflated by its ~30% abstention; **Bracken** is
the standard tool that re-estimates abundance from a Kraken 2 report, so it is
the fair abundance baseline. This package adds Kraken 2 **+ Bracken** to the
abundance comparison (Table 3 / trade-off figure).

## ⚠️ Must run on TWCC / nano5 (NOT Nano4)
Bracken needs two things that only exist where Kraken 2 was originally run:
1. the **custom Kraken 2 DB** built from the 1,535 gut genomes (the one that
   produced `small_predictions/reads_100K.kraken2.report`, with synthetic
   `species_N` taxids, `k=35`);
2. the **DB `species_N` → model genus crosswalk** that was used to convert the
   Kraken 2 predictions into `predictions_kraken2_twcc.npz` (the DB uses its own
   `species_N` numbering 0–2503, *not* the model's `species_class` 0–1534).

Nano4 has neither `kraken2`/`bracken` installed nor the DB, so this cannot be run
there.

## Inputs already available (copy these to the TWCC working dir)
- `reads_100K.kraken2.report` — the existing Kraken 2 report (in
  `gfm-classifier/small_predictions/`). This is the Bracken input; **no need to
  re-run Kraken 2.**
- `predictions_kraken2_twcc_genus.npz` — for the TRUE genus labels and the
  raw-Kraken 2 reference (keys `preds`, `labels`, genus space 0–119).
- `/work/ymj1123ntu/data/labels_100K.tsv` — model `species_class`↔`genus_class`
  and `species_name` (accession) ↔ genus, used to build the crosswalk.

## Steps

### 1. Build the Bracken k-mer distribution (one-time, needs the DB library)
```bash
KRAKEN2_DB=/path/to/custom_kraken2_db     # the DB used for reads_100K.kraken2.report
bash run_bracken.sh "$KRAKEN2_DB" 150
```
`run_bracken.sh` runs `bracken-build -k 35 -l 150` then `bracken -l S` on the
report, producing `reads_100K.bracken.species.tsv`.
If `bracken-build` complains that the DB library/intermediate files were removed,
the custom DB must be rebuilt first (`kraken2-build`); see notes in
`run_bracken.sh`.

### 2. Build the DB→genus crosswalk (one-time)
The DB assigns each of the 1,535 genomes a synthetic taxid; `species_N` has
`N = taxid - 2` (metadata `taxid_offset: 2`). You need `species_N → genus_class`.
```bash
# seqid2taxid.map lives inside the Kraken2 DB dir (accession -> taxid)
python build_crosswalk.py \
    --seqid2taxid "$KRAKEN2_DB/seqid2taxid.map" \
    --labels /work/ymj1123ntu/data/labels_100K.tsv \
    --taxid_offset 2 \
    --out species_N_to_genus.tsv
```
This joins the DB's accession→taxid with the labels' accession→genus. If the
accession strings don't match cleanly (GCF_* vs UMGS* vs internal ids), see the
"crosswalk" note below — the same mapping that produced
`predictions_kraken2_twcc.npz` is authoritative; reuse it if you still have it.

### 3. Evaluate Bracken abundance vs truth (and vs raw Kraken 2)
```bash
python eval_bracken.py \
    --bracken_species reads_100K.bracken.species.tsv \
    --crosswalk species_N_to_genus.tsv \
    --true_genus_npz predictions_kraken2_twcc_genus.npz \
    --n_total 100000 \
    --out bracken_metrics.json
```
Prints and saves genus- and species-level Pearson r and Bray–Curtis for
**Kraken 2 + Bracken**, alongside the **raw Kraken 2** reference recomputed from
the npz (should reproduce ~0.823 genus, confirming the pipeline).

## What to send back to me
`bracken_metrics.json` (and `reads_100K.bracken.species.tsv`). I will:
- add a **Kraken 2 + Bracken** row to Table 3 and the abundance/trade-off figure;
- update the §6.2 text and abstract (currently "raw Kraken 2 … Bracken remains an
  important baseline") to state the measured Bracken number;
- update the Box 2 decision guide.

## Interpreting the result (either way is publishable)
- If **Bracken r stays well below the neural model** → strengthens the paper: even
  the abundance-corrected pipeline is limited by Kraken 2's abstention on this
  coverage-matched pool.
- If **Bracken r improves markedly (approaches the neural model)** → we soften the
  claim to "a mid-accuracy neural model matches Kraken 2 + Bracken on abundance
  while Kraken 2 + Bracken remains the stronger detector" — still a clean,
  balanced practical recommendation.

## Crosswalk note (if `build_crosswalk.py` can't match accessions)
`predictions_kraken2_twcc.npz` is already in **model `species_class`** space, i.e.
someone already applied a `DB species_N → species_class` map when converting the
Kraken 2 output. That exact map (a script/notebook on TWCC/nano5) is the ground
truth — reuse it to emit `species_N \t genus_class` (join its `species_class`
with `labels_100K.tsv`'s `genus_class`) and pass it to `eval_bracken.py` via
`--crosswalk`.
