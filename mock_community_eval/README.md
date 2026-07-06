# Mock-community validation — local (RTX 4090) handoff

**Why.** Every headline number is on ART-simulated reads from the same genomes
used to build the reference (closed-set). A reviewer will ask for **real reads**.
A defined mock community gives real Illumina error profiles + a **known
composition** (ground-truth abundance) + realistic database-coverage gaps — so it
tests exactly what simulation cannot. No per-read labels are needed: we evaluate
**sample-level abundance** (predicted genus fractions vs the known composition).

**This is inference only — runs on one RTX 4090; no training, no HPC.** It reuses
the existing inference scripts; only the evaluation differs (compare to a known
composition instead of per-read labels).

> Read `local_realworld_eval/README.md` first (Sections 1–3, 6) for the env,
> the checkpoints to copy, and the exact inference commands. This package is the
> concrete "Track B" it refers to.

## 1. Choose a mock community (pick one)
The 120 classes are **human-gut genera**, so use a gut-relevant mock:
- **ZymoBIOMICS Gut Microbiome Standard (D6331)** — ~21 strains incl. gut genera
  (*Bacteroides*, *Faecalibacterium*, *Prevotella*, *Roseburia*, ...). Real
  Illumina runs are on SRA/ENA; the vendor sheet gives theoretical composition.
  Best in-set overlap with the 120 genera.
- **CAMI II human-gut** toy/low-complexity dataset — community-level ground truth,
  widely cited (already referenced in the manuscript).
- (ZymoBIOMICS D6300 "standard" is mostly non-gut → low in-set overlap; avoid.)

Download real reads (example, ENA/SRA):
```bash
# example: fetch a ZymoBIOMICS D6331 gut-standard Illumina run
prefetch <SRR/ERR accession> && fasterq-dump --split-files <accession>
# -> mock_R1.fastq mock_R2.fastq   (quality-trim optional: fastp)
```
Record the vendor/expected composition as `composition.csv` with columns
`genus_name,expected_fraction` (genomic or 16S theoretical fractions; note which).

## 2. Build the genus crosswalk (mock taxon -> the 120 genera)
The mock's taxa must be mapped to the 120 training genera. Genera in the mock but
NOT among the 120 are **out-of-set**: they can never be classified correctly and
form a hard ceiling — report their summed expected fraction as the "out-of-set
fraction". Use the genus names in `/work/ymj1123ntu/data/labels_100K.tsv`
(`genus_name`) as the canonical 120-genus vocabulary.

## 3. Run inference on the mock reads
Convert reads to the single-line FASTA the pipeline expects (headers can carry a
placeholder label; only predictions are used). Then, exactly as in
`local_realworld_eval/README.md` §6:
```bash
# NT-v2 6-mer (genus)
python scripts/run_genus_rctta.py --config configs/nt_token_genus_v9_50M.yaml \
  --checkpoint assets/nt_token_genus_v9_50M_best.pt \
  --test_fasta mock.fa --test_labels dummy_labels.tsv --train_labels labels.tsv \
  --out_dir out/mock_ntv2 --batch_size 256
# MT 13-mer (genus)
PYTHONPATH=<MetaTransformer>/src python scripts/extract_mt_predictions.py \
  --exp_dir <mt_13mer_exp_dir> --val_dir <dir_with_only mock.fa> \
  --vocab assets/vocab_13mer.txt --out out/mock_mt13/preds.npz \
  --class_indices 3 --batch_size 1024
```
(Each writes `preds.npz`; the `labels` array is a placeholder and is ignored.)

Optionally also run Kraken 2 (+ Bracken) on the mock reads with a standard gut DB
and export a genus abundance CSV `genus_name,pred_fraction` for the same comparison.

## 4. Evaluate abundance vs known composition
```bash
python eval_mock_abundance.py \
    --preds_npz out/mock_mt13/preds.npz \
    --genus_map /work/ymj1123ntu/data/labels_100K.tsv \
    --composition composition.csv \
    --exp_name "MT 13-mer" \
    --detect_threshold 0.01 \
    --out out/mock_mt13/mock_metrics.json
# repeat with --preds_npz out/mock_ntv2/rctta.npz for NT-v2
# for Kraken2/Bracken use --pred_abundance_csv instead of --preds_npz
```
Reports, restricted to in-set genera: Pearson r and Bray–Curtis (predicted vs
known genus fractions), detection sensitivity/false positives at the threshold,
and the out-of-set fraction (unresolvable ceiling).

## 5. What to send back
The `mock_metrics.json` for each model (NT-v2, MT 13-mer, and Kraken2/Bracken if
run) plus `composition.csv` and the mock accession/version. I will add a
"real mock community" paragraph + a small table to §6, promote the sample-level
claim from "controlled synthetic compositions" to include real-community
evidence, and update the cover letter.

## Interpreting (both outcomes publishable)
- Neural abundance holding up on a real mock → strong support for deployment.
- A drop on the mock (expected, from real error profiles + DB gaps + out-of-set
  taxa) → honest real-world bound; still the first real-data check the current
  paper lacks. Report the in-set fraction and out-of-set ceiling explicitly.

## Caveats
- **Genus only** (`class_indices=3`); species indices don't align across
  datasets (see `local_realworld_eval/README.md` §8).
- State whether the expected composition is genomic or 16S-rRNA based; 16S vs WGS
  abundance differ by genome copy number — compare like with like.
- Match read length where possible; real reads may differ from 150 bp (report it).
