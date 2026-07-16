# Track A: unseen-reference genome generalization

Track A evaluates genus classification on ART-simulated 150 bp reads from
RefSeq assemblies that are absent from the training reference set. The genera
remain in-distribution; the genome accessions do not. This is therefore an
**unseen-reference generalization test**, not a real-read or mock-community
experiment.

## Contamination audit

The original downloader did not enforce accession exclusion. A comparison
against the 1,535-reference training inventory found four overlapping GCF base
accessions in the 230-genome download pool. Three entered the final test FASTA:

| Accession | Genus | Reads removed |
|---|---|---:|
| `GCF_000312005` | Cellulomonas | 5,000 |
| `GCF_000010185` | Finegoldia | 5,000 |
| `GCF_000158275` | Fusobacterium | 5,000 |

`GCF_000162235` was also present in the download pool but was not selected for
the test FASTA. Removing the 15,000 overlapping reads leaves **580,000 reads
from 116 genera**. The three affected genera have no reads left in this clean
subset, so the result should be described as a 116-genus evaluation.

## Per-read Top-1 accuracy

| Model | Closed set (same references) | Unseen references (clean) | Drop |
|---|---:|---:|---:|
| MT 13-mer 250M | 98.7% | **32.6714%** (189,494/580,000) | 66.03 pp |
| MT 13-mer 50M | 87.5% | **27.0540%** (156,913/580,000) | 60.45 pp |
| NT-v2 v9 50M, RC-TTA | 67.1% | **25.8114%** (149,706/580,000) | 41.29 pp |

All models remain above the 120-class random baseline (0.83%), but the large
closed-to-unseen drops show that same-reference evaluation substantially
overstates genome-level generalization. The ordering remains MT-250M >
MT-50M > NT-v2, although the margin between MT-50M and NT-v2 is small.

## Interpretation limits

- This is a useful robustness result, but **not a clean tokenization
  ablation**: model size, training volume, architecture, and tokenization differ
  between rows.
- Reads are simulated with ART. Real-read abundance validation is reported
  separately using the ZymoBIOMICS D6331 mock community.
- Post-hoc filtering removes three complete genera. For a publication-quality
  primary benchmark, rebuild those genera with verified non-training
  accessions and rerun inference so all 119 available genera remain represented.
- Sample-level abundance correlations from this uniformly sampled pool are not
  interpretable and must not be reported.

## Reproduce the filtered metrics

```bash
python local_realworld_eval/track_a_06_clean_metrics.py \
  --test-fasta /nas2/gfm-classifier/track_a/test_data/newgenome_test.fa \
  --exclude-accessions local_realworld_eval/track_a_training_gcf_accessions.txt \
  --prediction mt_250M=/nas2/gfm-classifier/track_a/out/mt_250M/preds.npz \
  --prediction mt_50M=/nas2/gfm-classifier/track_a/out/mt_50M/preds.npz \
  --prediction nt_v9=/nas2/gfm-classifier/track_a/out/nt_v9/preds.npz \
  --output /nas2/gfm-classifier/track_a/out/metrics_clean.json
```

The machine-readable result is stored locally at
`/nas2/gfm-classifier/track_a/out/metrics_clean.json`; large prediction files
and logs are intentionally excluded from Git.
