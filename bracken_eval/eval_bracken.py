#!/usr/bin/env python3
"""
Evaluate Kraken2 + Bracken genus abundance vs truth, and vs RAW Kraken2.

Bracken output is at DB `species_N` level; we aggregate to the model's 120
genera with the crosswalk, then compare against the TRUE genus abundance and the
RAW Kraken2 genus abundance (both from predictions_kraken2_twcc_genus.npz).

Abundance convention matches the paper: predicted fraction = reads / n_total,
where n_total includes unclassified reads (so abstention deflation is reflected
for both raw Kraken2 and Bracken).

Metrics: Pearson r and Bray-Curtis over the 120-genus abundance vectors.
"""
import argparse, json
import numpy as np
import pandas as pd
from scipy.stats import pearsonr


def bray_curtis(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    denom = (x + y).sum()
    return float(np.abs(x - y).sum() / denom) if denom > 0 else float("nan")


def load_npz(path):
    d = np.load(path)
    return d["preds"].astype(np.int64), d["labels"].astype(np.int64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bracken_species", required=True, help="reads_100K.bracken.species.tsv")
    ap.add_argument("--crosswalk", required=True, help="species_N -> genus_class tsv (build_crosswalk.py)")
    ap.add_argument("--true_genus_npz", required=True, help="predictions_kraken2_twcc_genus.npz (preds,labels)")
    ap.add_argument("--n_total", type=int, default=100000)
    ap.add_argument("--out", default="bracken_metrics.json")
    args = ap.parse_args()

    # crosswalk species_N -> genus_class
    cw = pd.read_csv(args.crosswalk, sep="\t")
    N2g = dict(zip(cw["species_N"].astype(int), cw["genus_class"].astype(int)))

    # Bracken species table: name="species_N", new_est_reads
    br = pd.read_csv(args.bracken_species, sep="\t")
    name_col = "name" if "name" in br.columns else br.columns[0]
    reads_col = "new_est_reads" if "new_est_reads" in br.columns else br.columns[-2]
    n_genera = int(cw["genus_class"].max()) + 1
    bracken_genus = np.zeros(n_genera)
    missing = 0
    for name, reads in zip(br[name_col].astype(str), br[reads_col].astype(float)):
        try:
            N = int(str(name).split("_")[-1])
        except ValueError:
            continue
        g = N2g.get(N)
        if g is None:
            missing += reads; continue
        bracken_genus[g] += reads

    # truth + raw Kraken2 from the genus npz
    kr_preds, kr_labels = load_npz(args.true_genus_npz)
    n_genera = max(n_genera, int(kr_labels.max()) + 1)
    bracken_genus = np.pad(bracken_genus, (0, n_genera - len(bracken_genus)))
    true_ab = np.bincount(kr_labels, minlength=n_genera).astype(float) / args.n_total
    raw_ab  = np.bincount(kr_preds[kr_preds >= 0], minlength=n_genera).astype(float) / args.n_total
    brk_ab  = bracken_genus / args.n_total

    res = {
        "n_total": args.n_total,
        "bracken_reads_assigned": float(bracken_genus.sum()),
        "bracken_reads_unmapped_to_genus": float(missing),
        "genus": {
            "kraken2_raw":     {"pearson_r": float(pearsonr(raw_ab, true_ab)[0]),
                                "bray_curtis": bray_curtis(raw_ab, true_ab)},
            "kraken2_bracken": {"pearson_r": float(pearsonr(brk_ab, true_ab)[0]),
                                "bray_curtis": bray_curtis(brk_ab, true_ab)},
        },
    }
    print(json.dumps(res, indent=2))
    print("\n== genus abundance (120 genera, full 100K pool) ==")
    print(f"  raw Kraken2      : r={res['genus']['kraken2_raw']['pearson_r']:.4f}  "
          f"BC={res['genus']['kraken2_raw']['bray_curtis']:.4f}   "
          f"(should reproduce the paper's ~0.823 genus r)")
    print(f"  Kraken2 + Bracken: r={res['genus']['kraken2_bracken']['pearson_r']:.4f}  "
          f"BC={res['genus']['kraken2_bracken']['bray_curtis']:.4f}")
    with open(args.out, "w") as f:
        json.dump(res, f, indent=2)
    print(f"\nsaved {args.out}")


if __name__ == "__main__":
    main()
