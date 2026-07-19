# D6331 Rep1 enhanced metrics (SRR33710519, 3M R1)
| Method | Pearson r | boot 95% CI | Spearman | Bray–Curtis | r (exp≥1%, n=9) | Sens (exp≥1%) | FP |
|---|---:|---|---:|---:|---:|---:|---:|
| NT-v2 | 0.420 | [-0.36, 0.88] | 0.338 | 0.376 | 0.569 | 0.778 | 7 |
| MT 13-mer | 0.545 | [-0.17, 0.91] | 0.439 | 0.344 | 0.610 | 0.778 | 7 |
| Kraken2+Bracken | 0.580 | [0.08, 0.90] | 0.572 | 0.437 | 0.620 | 0.556 | 4 |

## Clostridioides → Clostridium remap

| Method | r | Spearman | BC |
|---|---:|---:|---:|
| NT-v2 | 0.455 | 0.472 | 0.366 |
| MT 13-mer | 0.569 | 0.582 | 0.333 |
| Kraken2+Bracken | 0.595 | 0.686 | 0.425 |
