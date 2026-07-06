#!/usr/bin/env python3
"""
Evaluate predicted genus abundance against a mock community's KNOWN composition.

No per-read ground truth is needed. Input is either
  (a) per-read genus predictions (--preds_npz, key 'preds' over the 120 genera), or
  (b) a genus abundance table (--pred_abundance_csv: genus_name,pred_fraction)
      e.g. from Kraken2/Bracken.

Comparison is restricted to IN-SET genera (present in both the composition and the
120 training genera). Genera in the composition but outside the 120 are reported
as an "out-of-set fraction" (an unresolvable ceiling). Metrics: Pearson r and
Bray-Curtis over in-set genus fractions, plus detection at a threshold.
"""
import argparse, json
import numpy as np
import pandas as pd
from scipy.stats import pearsonr


def bray_curtis(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    d = (x + y).sum()
    return float(np.abs(x - y).sum() / d) if d > 0 else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genus_map", required=True, help="labels tsv with genus_class,genus_name")
    ap.add_argument("--composition", required=True, help="csv: genus_name,expected_fraction")
    ap.add_argument("--preds_npz", help="per-read predictions npz (key 'preds', 0..119)")
    ap.add_argument("--pred_abundance_csv", help="alt: genus_name,pred_fraction (Kraken2/Bracken)")
    ap.add_argument("--exp_name", default="model")
    ap.add_argument("--detect_threshold", type=float, default=0.01)
    ap.add_argument("--out", default="mock_metrics.json")
    args = ap.parse_args()

    gm = pd.read_csv(args.genus_map, sep="\t").drop_duplicates("genus_class")
    n_genera = int(gm["genus_class"].max()) + 1
    name2class = {str(n).strip(): int(c) for n, c in zip(gm["genus_name"], gm["genus_class"])}

    # predicted genus fractions over the 120 classes
    pred = np.zeros(n_genera)
    if args.preds_npz:
        p = np.load(args.preds_npz)["preds"].astype(np.int64)
        p = p[p >= 0]
        pred = np.bincount(p, minlength=n_genera).astype(float)
        pred = pred / pred.sum() if pred.sum() > 0 else pred
    elif args.pred_abundance_csv:
        pa = pd.read_csv(args.pred_abundance_csv)
        for nm, fr in zip(pa["genus_name"].astype(str), pa["pred_fraction"].astype(float)):
            if nm.strip() in name2class:
                pred[name2class[nm.strip()]] += fr
    else:
        ap.error("provide --preds_npz or --pred_abundance_csv")

    # known composition
    comp = pd.read_csv(args.composition)
    comp["genus_name"] = comp["genus_name"].astype(str).str.strip()
    in_set = comp[comp["genus_name"].isin(name2class)].copy()
    out_set_frac = float(comp.loc[~comp["genus_name"].isin(name2class), "expected_fraction"].sum())

    idx = [name2class[n] for n in in_set["genus_name"]]
    exp = in_set["expected_fraction"].to_numpy(float)
    obs = pred[idx]
    # renormalise both over the in-set genera for a like-with-like comparison
    exp_n = exp / exp.sum() if exp.sum() > 0 else exp
    obs_n = obs / obs.sum() if obs.sum() > 0 else obs

    r = float(pearsonr(obs_n, exp_n)[0]) if len(exp_n) > 1 else float("nan")
    bc = bray_curtis(obs_n, exp_n)

    thr = args.detect_threshold
    present = exp_n > 0
    detected = obs_n >= thr
    sens = float((detected & present).sum() / max(present.sum(), 1))
    # false positives = 120-genus classes predicted >= thr that are NOT in the composition
    fp_mask = pred >= thr
    fp_mask[idx] = False
    n_fp = int(fp_mask.sum())

    res = {
        "exp_name": args.exp_name,
        "n_in_set_genera": int(len(idx)),
        "out_of_set_expected_fraction": out_set_frac,
        "pearson_r_in_set": r,
        "bray_curtis_in_set": bc,
        "detect_threshold": thr,
        "detection_sensitivity_in_set": sens,
        "false_positive_genera": n_fp,
    }
    print(json.dumps(res, indent=2))
    print(f"\n[{args.exp_name}]  in-set genera={len(idx)}  "
          f"out-of-set expected fraction={out_set_frac:.3f}")
    print(f"  abundance vs known:  Pearson r={r:.4f}   Bray-Curtis={bc:.4f}")
    print(f"  detection @>= {thr:.2%}:  sensitivity={sens:.2%}  false-positive genera={n_fp}")
    with open(args.out, "w") as f:
        json.dump(res, f, indent=2)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
