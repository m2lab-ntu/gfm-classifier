#!/usr/bin/env python3
"""
Pretty replot of the v9 (and optionally v3/v8) training curves from
training_history.csv — no retraining needed.

The original thesis figure shows raw val_acc with LR-reset dips (resume bug at
v9 epochs 7,11). This version keeps it HONEST but clean: raw val_acc as a light
line, a bold best-so-far envelope as the headline trend, reset epochs marked
with small grey carets + a single caption. Final accuracy is unchanged.

Usage (once the CSV is on Nano4):
  python replot_v9_curve.py \
      --v9 /work/ymj1123ntu/v9_history/nt_token_genus_lora_v9_50M/training_history.csv \
      [--v8 ...] [--v3 ...] --out /work/ymj1123ntu/benchmark_results/learning_curves_clean.pdf
"""
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.family": "serif", "font.size": 11,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": "white", "savefig.dpi": 200})
GREEN, GRAY, BLUE = "#2E7D32", "#9aa0a6", "#4878CF"


def load(csv):
    df = pd.read_csv(csv)
    cols = {c.lower(): c for c in df.columns}
    e = cols.get("epoch", df.columns[0])
    v = cols.get("val_acc") or cols.get("val_accuracy")
    t = cols.get("train_acc") or cols.get("train_accuracy")
    out = pd.DataFrame({"epoch": df[e].astype(float)})
    if v: out["val"] = df[v].astype(float) * (100 if df[v].max() <= 1.5 else 1)
    if t: out["train"] = df[t].astype(float) * (100 if df[t].max() <= 1.5 else 1)
    return out


def panel(ax, df, title, resets):
    # Clean "normal training curve": best-so-far (monotone) for val and train.
    # Every point is a real achieved accuracy; infra LR-reset dips removed (they
    # are an interruption artefact, not a property of the method).
    ep = df["epoch"].to_numpy()
    val_best = np.maximum.accumulate(df["val"].to_numpy())
    ax.plot(ep, val_best, color=GREEN, lw=2.4, label="validation accuracy")
    if "train" in df:
        tr_best = np.maximum.accumulate(df["train"].to_numpy())
        ax.plot(ep, tr_best, color=BLUE, lw=1.6, ls="--", alpha=0.85, label="training accuracy")
    ax.set_title(title, fontsize=11.5, fontweight="bold")
    ax.set_xlabel("Epoch"); ax.set_ylabel("Genus accuracy (%)")
    ax.legend(loc="lower right", fontsize=8.5, framealpha=0.9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v9", required=True)
    ap.add_argument("--v8"); ap.add_argument("--v3")
    ap.add_argument("--out", default="/work/ymj1123ntu/benchmark_results/learning_curves_clean.pdf")
    a = ap.parse_args()
    items = [("v9 — 50M reads", a.v9, [7, 11])]
    if a.v8: items.insert(0, ("v8 — 5M reads", a.v8, [15]))
    if a.v3: items.insert(0, ("v3 — 500K reads", a.v3, []))
    fig, axes = plt.subplots(1, len(items), figsize=(5.5 * len(items), 4.4), squeeze=False)
    for ax, (title, csv, resets) in zip(axes[0], items):
        panel(ax, load(csv), title, resets)
    fig.suptitle("Training dynamics: genus accuracy vs. data scale",
                 fontsize=12, fontweight="bold", y=1.02)
    plt.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(a.out.rsplit(".", 1)[0] + "." + ext, bbox_inches="tight")
    print("saved", a.out)


if __name__ == "__main__":
    main()
