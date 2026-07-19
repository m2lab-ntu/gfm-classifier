#!/usr/bin/env python3
"""
Train vs inference speed/memory comparison (pure compute).
Source: compute_speed_summary.csv (probe_train_speed*.py, Nano4 1x H200,
batch 128, fwd+bwd vs forward-only, synthetic reads, warmup excluded).
Cross-reference: benchmark_summary.csv (end-to-end inference, incl. tokenisation).
Outputs: compute_speed.png / .pdf
"""
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = Path(__file__).parent
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": "white", "savefig.dpi": 200})
NAVY, TEAL, GREEN, PURPLE, GOLD, GRAY = \
    "#0A2540", "#1E6091", "#2E7D32", "#6A1B9A", "#B8860B", "#5A6068"

PRETTY = {
    "NT-v2_v9_genus":           ("NT-v2 + LoRA (genus, 498M)",   TEAL),
    "NT-v2_sp_v4_species":      ("NT-v2 + LoRA (species, 498M)", TEAL),
    "MT_13mer_stride1_genus":   ("MT 13-mer s1 (genus, ~5M)",    PURPLE),
    "MT_13mer_stride13_genus":  ("MT 13-mer s13 (genus, ~5M)",   PURPLE),
    "MT_13mer_stride1_species": ("MT 13-mer s1 (species, ~5M)",  PURPLE),
    "MT_6mer_stride1_species":  ("MT 6-mer s1 (species, ~5M)",   GREEN),
    "MT_6mer_stride6_species":  ("MT 6-mer s6 (species, ~5M)",   GREEN),
}

# ── load pure-compute results ──
data = {}
with open(HERE / "compute_speed_summary.csv") as f:
    for r in csv.DictReader(f):
        data.setdefault(r["model"], {})[r["phase"]] = dict(
            rps=float(r["reads_per_sec"]), mib=float(r["peak_gpu_mib"]))

# ── load end-to-end inference (for the bottleneck callout) ──
e2e = {}
try:
    with open(HERE / "benchmark_summary.csv") as f:
        for r in csv.DictReader(f):
            try:
                e2e[r["model"]] = float(r["reads_per_sec"])
            except ValueError:
                pass
except FileNotFoundError:
    pass

order = [m for m in PRETTY if m in data]
order.sort(key=lambda m: data[m]["train"]["rps"])
labels = [PRETTY[m][0] for m in order]
colors = [PRETTY[m][1] for m in order]
y = np.arange(len(order))
h = 0.38

fig, axes = plt.subplots(1, 2, figsize=(14, 6.2))
fig.suptitle("Training vs Inference — Pure Compute (Nano4 H200, batch 128, AMP)",
             fontsize=14, fontweight="bold", color=NAVY, y=0.99)

# ── Panel 1: throughput (log) ──
ax = axes[0]
for m, yi, c in zip(order, y, colors):
    inf = data[m]["infer"]["rps"]; tr = data[m]["train"]["rps"]
    ax.barh(yi + h/2, inf, h, color=c, alpha=0.45)
    ax.barh(yi - h/2, tr,  h, color=c)
    ax.text(inf*1.1, yi + h/2, f"{inf:,.0f}", va="center", fontsize=8, color=GRAY)
    ax.text(tr*1.1,  yi - h/2, f"{tr:,.0f}",  va="center", fontsize=8, color=NAVY, fontweight="bold")
ax.set_xscale("log")
ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9)
ax.set_xlabel("Throughput (reads / sec, log)  ·  higher = faster")
ax.set_xlim(1e3, 1e6)
ax.set_title("Throughput", fontsize=12, fontweight="bold", color=NAVY)
ax.legend(handles=[Patch(color=GRAY, alpha=0.45, label="inference (forward only)"),
                   Patch(color=GRAY, label="training (fwd + bwd)")],
          loc="lower right", fontsize=8.5, framealpha=0.9)

# ── Panel 2: peak GPU memory ──
ax2 = axes[1]
for m, yi, c in zip(order, y, colors):
    im = data[m]["infer"]["mib"]; tm = data[m]["train"]["mib"]
    ax2.barh(yi + h/2, im, h, color=c, alpha=0.45)
    ax2.barh(yi - h/2, tm, h, color=c)
    ax2.text(im + 250, yi + h/2, f"{im:,.0f}", va="center", fontsize=8, color=GRAY)
    ax2.text(tm + 250, yi - h/2, f"{tm:,.0f}", va="center", fontsize=8, color=NAVY, fontweight="bold")
ax2.set_yticks(y); ax2.set_yticklabels([])
ax2.set_xlabel("Peak GPU memory (MiB)  ·  lower = leaner")
ax2.set_xlim(0, 19000)
ax2.set_title("Peak GPU Memory", fontsize=12, fontweight="bold", color=NAVY)

# ── family legend + bottleneck callout ──
fam = [Patch(color=TEAL, label="NT-v2 + LoRA (498M)"),
       Patch(color=PURPLE, label="MT 13-mer (~5M)"),
       Patch(color=GREEN, label="MT 6-mer (~5M)")]
axes[0].legend(handles=fam + [Patch(color=GRAY, alpha=0.45, label="inference (fwd)"),
                              Patch(color=GRAY, label="training (fwd+bwd)")],
               loc="lower right", fontsize=8, framealpha=0.9)

note = ("Pure-compute inference favours the tiny MT models by ~44x (197k vs 4.4k r/s). "
        "But end-to-end (with tokenisation + I/O, benchmark_summary.csv) MT 13-mer s1 drops to "
        f"{e2e.get('MT_13mer_stride1_genus', float('nan')):,.0f} r/s — below NT-v2's "
        f"{e2e.get('NT-v2_v9_genus', float('nan')):,.0f} — so its real bottleneck is overlapping-13-mer "
        "tokenisation over a 33M-row vocab, not the model. MT 13-mer training is also memory-bound "
        "(16.5 GB) from the dense embedding gradient.")
fig.text(0.5, 0.015, note, ha="center", fontsize=8.4, color=GRAY, wrap=True)

plt.tight_layout(rect=[0, 0.06, 1, 0.96])
plt.savefig(HERE / "compute_speed.png", bbox_inches="tight")
plt.savefig(HERE / "compute_speed.pdf", bbox_inches="tight")
plt.close()
print("Saved compute_speed.png / .pdf")
