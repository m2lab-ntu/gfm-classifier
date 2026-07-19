#!/usr/bin/env python3
"""
Enhanced mock-community metrics on existing (or new) predictions.

Adds what the original eval_mock_abundance.py omitted:
  - Spearman rho
  - Pearson on abundance-filtered taxa (expected >= 0.5% / 1% before renorm)
  - Detection sensitivity only among taxa with expected >= threshold
  - Bootstrap 95% CI for Pearson r (resample genera)
  - Per-genus expected vs predicted table
  - Optional Clostridioides->Clostridium remap sensitivity check
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr


def bray_curtis(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    d = (x + y).sum()
    return float(np.abs(x - y).sum() / d) if d > 0 else float("nan")


def bootstrap_pearson(x, y, n_boot=5000, seed=42):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    n = len(x)
    if n < 3:
        return float("nan"), float("nan"), float("nan")
    rs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        if np.std(x[idx]) == 0 or np.std(y[idx]) == 0:
            continue
        rs.append(pearsonr(x[idx], y[idx])[0])
    if not rs:
        return float("nan"), float("nan"), float("nan")
    rs = np.asarray(rs)
    return float(np.mean(rs)), float(np.quantile(rs, 0.025)), float(np.quantile(rs, 0.975))


def load_pred_vector(genus_map, preds_npz=None, pred_csv=None):
    gm = pd.read_csv(genus_map, sep="\t").drop_duplicates("genus_class")
    n_genera = int(gm["genus_class"].max()) + 1
    name2class = {str(n).strip(): int(c) for n, c in zip(gm["genus_name"], gm["genus_class"])}
    class2name = {int(c): str(n).strip() for n, c in zip(gm["genus_name"], gm["genus_class"])}
    pred = np.zeros(n_genera)
    if preds_npz:
        p = np.load(preds_npz)["preds"].astype(np.int64)
        p = p[p >= 0]
        pred = np.bincount(p, minlength=n_genera).astype(float)
        pred = pred / pred.sum() if pred.sum() > 0 else pred
        n_reads = int(len(p))
        classified_frac = 1.0
    else:
        pa = pd.read_csv(pred_csv)
        for nm, fr in zip(pa["genus_name"].astype(str), pa["pred_fraction"].astype(float)):
            if nm.strip() in name2class:
                pred[name2class[nm.strip()]] += fr
        # Bracken CSV is already fractions among assigned reads
        n_reads = None
        classified_frac = None
    return pred, name2class, class2name, n_reads, classified_frac


def evaluate(comp_df, pred, name2class, class2name, detect_thr=0.01, remap_clostridioides=False):
    comp = comp_df.copy()
    comp["genus_name"] = comp["genus_name"].astype(str).str.strip()
    comp["expected_fraction"] = comp["expected_fraction"].astype(float)

    if remap_clostridioides and "Clostridioides" in set(comp["genus_name"]):
        # fold Clostridioides expected mass into Clostridium if present
        cdiff = float(comp.loc[comp["genus_name"] == "Clostridioides", "expected_fraction"].sum())
        comp = comp[comp["genus_name"] != "Clostridioides"].copy()
        if "Clostridium" in set(comp["genus_name"]):
            comp.loc[comp["genus_name"] == "Clostridium", "expected_fraction"] += cdiff
        else:
            comp = pd.concat(
                [comp, pd.DataFrame([{"genus_name": "Clostridium", "expected_fraction": cdiff}])],
                ignore_index=True,
            )

    in_set = comp[comp["genus_name"].isin(name2class)].copy()
    out_set_frac = float(comp.loc[~comp["genus_name"].isin(name2class), "expected_fraction"].sum())

    names = in_set["genus_name"].tolist()
    idx = [name2class[n] for n in names]
    exp = in_set["expected_fraction"].to_numpy(float)
    obs = pred[idx].astype(float)

    # renormalise both over in-set
    exp_n = exp / exp.sum() if exp.sum() > 0 else exp
    obs_n = obs / obs.sum() if obs.sum() > 0 else obs

    r = float(pearsonr(obs_n, exp_n)[0]) if len(exp_n) > 1 else float("nan")
    rho = float(spearmanr(obs_n, exp_n).correlation) if len(exp_n) > 1 else float("nan")
    bc = bray_curtis(obs_n, exp_n)
    r_mean, r_lo, r_hi = bootstrap_pearson(obs_n, exp_n)

    # filtered Pearson (by *raw* expected % before renorm; composition uses percent units)
    # composition.csv stores percentages (sum≈100); treat >=0.5 and >=1.0 accordingly
    # If values look like fractions (sum≈1), scale thresholds.
    unit = 1.0 if exp.sum() > 2 else 0.01
    thr05 = 0.5 * unit
    thr1 = 1.0 * unit

    def filtered_metrics(min_raw):
        mask = exp >= min_raw
        if mask.sum() < 2:
            return {"n": int(mask.sum()), "pearson_r": float("nan"), "spearman_rho": float("nan"),
                    "bray_curtis": float("nan")}
        e = exp[mask]
        o = obs[mask]
        e = e / e.sum()
        o = o / o.sum() if o.sum() > 0 else o
        return {
            "n": int(mask.sum()),
            "pearson_r": float(pearsonr(o, e)[0]),
            "spearman_rho": float(spearmanr(o, e).correlation),
            "bray_curtis": bray_curtis(o, e),
            "genera": [names[i] for i, m in enumerate(mask) if m],
        }

    # detection: only taxa whose *renormalised* expected >= detect_thr (or raw >= 1%)
    present_fixed = exp >= thr1  # expected >= 1% in composition units
    detected = obs_n >= detect_thr
    # map obs_n detection onto raw-present taxa
    sens_fixed = float((detected & present_fixed).sum() / max(present_fixed.sum(), 1))
    # original (flawed) definition for comparison
    present_old = exp_n > 0
    sens_old = float((detected & present_old).sum() / max(present_old.sum(), 1))

    # false positives among 120 classes not in composition, pred >= thr
    fp_mask = pred >= detect_thr
    for i in idx:
        fp_mask[i] = False
    fp_names = [class2name[i] for i in np.where(fp_mask)[0] if i in class2name]

    per_genus = []
    for n, e_raw, e_n, o_raw, o_n in zip(names, exp, exp_n, obs, obs_n):
        per_genus.append({
            "genus_name": n,
            "expected_raw": float(e_raw),
            "expected_renorm": float(e_n),
            "pred_raw_slice": float(o_raw),
            "pred_renorm": float(o_n),
            "abs_err_renorm": float(abs(o_n - e_n)),
        })

    return {
        "n_in_set_genera": int(len(names)),
        "out_of_set_expected_fraction": out_set_frac,
        "pearson_r_in_set": r,
        "pearson_r_bootstrap_mean": r_mean,
        "pearson_r_bootstrap_ci95": [r_lo, r_hi],
        "spearman_rho_in_set": rho,
        "bray_curtis_in_set": bc,
        "filtered_ge_0.5pct": filtered_metrics(thr05),
        "filtered_ge_1pct": filtered_metrics(thr1),
        "detection_sensitivity_legacy_all_present": sens_old,
        "detection_sensitivity_expected_ge_1pct": sens_fixed,
        "n_expected_ge_1pct": int(present_fixed.sum()),
        "detect_threshold": detect_thr,
        "false_positive_genera": int(fp_mask.sum()),
        "false_positive_names": fp_names,
        "per_genus": per_genus,
        "remap_clostridioides": remap_clostridioides,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genus_map", required=True)
    ap.add_argument("--composition", required=True)
    ap.add_argument("--preds_npz")
    ap.add_argument("--pred_abundance_csv")
    ap.add_argument("--exp_name", default="model")
    ap.add_argument("--detect_threshold", type=float, default=0.01)
    ap.add_argument("--out", required=True)
    ap.add_argument("--also_remap_clostridioides", action="store_true")
    args = ap.parse_args()

    pred, name2class, class2name, n_reads, clf = load_pred_vector(
        args.genus_map, args.preds_npz, args.pred_abundance_csv
    )
    comp = pd.read_csv(args.composition)
    res = evaluate(comp, pred, name2class, class2name, args.detect_threshold, False)
    res["exp_name"] = args.exp_name
    res["n_reads"] = n_reads
    out = {"primary": res}
    if args.also_remap_clostridioides:
        out["clostridioides_as_clostridium"] = evaluate(
            comp, pred, name2class, class2name, args.detect_threshold, True
        )
        out["clostridioides_as_clostridium"]["exp_name"] = args.exp_name + " (C.diff->Clostridium)"

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)

    p = res
    print(f"[{args.exp_name}]")
    print(f"  Pearson r={p['pearson_r_in_set']:.4f}  "
          f"boot95%[{p['pearson_r_bootstrap_ci95'][0]:.3f},{p['pearson_r_bootstrap_ci95'][1]:.3f}]  "
          f"Spearman={p['spearman_rho_in_set']:.4f}  BC={p['bray_curtis_in_set']:.4f}")
    f1 = p["filtered_ge_1pct"]
    print(f"  filtered >=1% (n={f1['n']}): r={f1['pearson_r']:.4f}  rho={f1['spearman_rho']:.4f}  BC={f1['bray_curtis']:.4f}")
    print(f"  sens@1% legacy={p['detection_sensitivity_legacy_all_present']:.3f}  "
          f"sens among expected>=1%={p['detection_sensitivity_expected_ge_1pct']:.3f} "
          f"(n={p['n_expected_ge_1pct']})  FP={p['false_positive_genera']}")
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
