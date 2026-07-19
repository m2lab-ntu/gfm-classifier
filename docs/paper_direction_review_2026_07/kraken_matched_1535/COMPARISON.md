# Kraken2 matched-reference (1,535) vs NT/MT — TWCC 100K

## Full pool (100,000 reads) — fair after GCF included

| Model | Classified | Read acc | Pearson r | Bray–Curtis |
|---|---:|---:|---:|---:|
| Kraken2_raw | 80.0% | 80.0% | 0.832 | 0.111 |
| MT_13mer | 100.0% | 94.3% | 1.000 | 0.015 |
| MT_6mer | 100.0% | 48.8% | 0.984 | 0.166 |
| NT_v2 | 100.0% | 67.4% | 0.994 | 0.091 |

**Kraken2+Bracken (full report):** r=1.000, BC=0.004

## Legacy coverage-matched subset (85,819; old DB in-set only)

| Model | Classified | Read acc | Pearson r | Bray–Curtis |
|---|---:|---:|---:|---:|
| Kraken2_raw | 77.2% | 77.2% | 0.824 | 0.128 |
| MT_13mer | 100.0% | 94.9% | 1.000 | 0.015 |
| MT_6mer | 100.0% | 51.5% | 0.987 | 0.152 |
| NT_v2 | 100.0% | 69.7% | 0.995 | 0.089 |

## Species-level Kraken2 (for reference)

| DB | Species in DB | Classified | Top-1 (all) | Top-1 (classified) |
|---|---:|---:|---:|---:|
| Old (1,316; no GCF) | 1,316 | 70.0% | 66.2% | 94.6% |
| New (1,535; matched) | 1,535 | 80.0% | 79.5% | 99.4% |

## Takeaways

- New DB removes the GCF hole: full-pool genus read acc rises to **80.0%** (raw Kraken2).
- On the legacy 85,819 subset, raw Kraken2 stays ~**77.2%** / r≈**0.824** (paper was 77.7% / 0.823).
- With matched reference, **Kraken2+Bracken** abundance on the full 100K report is essentially perfect (r=1.000, BC=0.004).
- MT 13-mer remains strongest on read accuracy (full **94.3%**; legacy **94.9%**).
- NT-v2 (RC-TTA) full-pool genus acc **67.4%** (legacy subset **69.7%**).

Artifacts: `/nas2/hierachical_test/kraken2_db_1535/eval_twcc100k`
