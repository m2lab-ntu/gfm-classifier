#!/usr/bin/env python3
"""
Speed/memory comparison of GFM classifier methods.
Source: benchmark_summary.csv (Nano4 H200, 100K reads, batch_size=1024, Job 87581, 2026-06-09).
Outputs: speed_benchmark.png / .pdf
"""
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": "white", "savefig.dpi": 200})

NAVY, TEAL, GREEN, PURPLE, GOLD, GRAY = \
    "#0A2540", "#1E6091", "#2E7D32", "#6A1B9A", "#B8860B", "#5A6068"

# pretty name, family color, task, params(M), accuracy note
META = {
    "MT_6mer_stride6_species":  ("MT 6-mer s6",     GREEN,  "species", "~5M",  None),
    "MT_6mer_stride1_species":  ("MT 6-mer s1",     GREEN,  "species", "~5M",  None),
    "MT_13mer_stride13_genus":  ("MT 13-mer s13",   PURPLE, "genus",   "~5M",  None),
    "MT_13mer_stride1_genus":   ("MT 13-mer s1",    PURPLE, "genus",   "~5M",  "87.4% genus"),
    "MT_13mer_stride1_species": ("MT 13-mer s1",    PURPLE, "species", "~5M",  None),
    "NT-v2_v9_genus":           ("NT-v2 + LoRA",    TEAL,   "genus",   "498M", "67% genus"),
    "NT-v2_sp_v4_species":      ("NT-v2 + LoRA",    TEAL,   "species", "498M", None),
}

rows = []
with open(HERE / "benchmark_summary.csv") as f:
    for r in csv.DictReader(f):
        m = r["model"]
        name, color, task, params, note = META.get(m, (m, GRAY, "?", "?", None))
        rows.append(dict(key=m, name=name, color=color, task=task, params=params,
                         note=note,
                         rps=float(r["reads_per_sec"]),
                         ms=float(r["ms_per_read"]),
                         elapsed=float(r["elapsed_sec"]),
                         gpu=float(r["peak_gpu_mib"])))

rows.sort(key=lambda d: d["rps"])  # ascending → fastest on top of barh
labels = [f"{d['name']}\n({d['task']}, {d['params']})" for d in rows]
colors = [d["color"] for d in rows]
y = np.arange(len(rows))

fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.0))
fig.suptitle("GFM Classifier End-to-End Cost — Nano4 H200, 100K reads, cold start",
             fontsize=14, fontweight="bold", color=NAVY, y=0.99)

# ── Left: end-to-end throughput (wall-clock incl. load + tokenise) ──
ax = axes[0]
bars = ax.barh(y, [d["rps"] for d in rows], color=colors, edgecolor="white", height=0.7)
for d, yi in zip(rows, y):
    ax.text(d["rps"] + 40, yi, f"{d['rps']:,.0f} r/s  ·  {d['elapsed']:.0f}s total",
            va="center", fontsize=9, color=NAVY)
    if d["note"]:
        ax.text(d["rps"] - 40, yi, d["note"], va="center", ha="right",
                fontsize=8, color="white", fontweight="bold")
ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=8.5)
ax.set_xlabel("End-to-end throughput (reads/sec) — total time for 100K\nincl. model+vocab load + tokenisation  ·  higher = faster")
ax.set_xlim(0, 3700)
ax.set_title("End-to-End Wall-Clock (cold start, 100K)", fontsize=12, fontweight="bold", color=NAVY)

# ── Right: peak GPU memory ──
ax2 = axes[1]
ax2.barh(y, [d["gpu"] for d in rows], color=colors, edgecolor="white", height=0.7)
for d, yi in zip(rows, y):
    ax2.text(d["gpu"] + 100, yi, f"{d['gpu']:,.0f} MiB", va="center", fontsize=9, color=NAVY)
ax2.set_yticks(y); ax2.set_yticklabels([])
ax2.set_xlabel("Peak GPU memory (MiB)  ·  lower = leaner")
ax2.set_xlim(0, 11000)
ax2.set_title("Peak GPU Memory", fontsize=12, fontweight="bold", color=NAVY)

# legend (family colors)
from matplotlib.patches import Patch
handles = [Patch(color=GREEN, label="MetaTransformer 6-mer (~5M)"),
           Patch(color=PURPLE, label="MetaTransformer 13-mer (~5M)"),
           Patch(color=TEAL,  label="NT-v2 + LoRA (498M)")]
axes[0].legend(handles=handles, loc="lower right", fontsize=8.5, framealpha=0.9)

fig.text(0.5, 0.02,
         "Total wall-clock to classify 100K reads from cold start (model+vocab load + tokenisation + inference). "
         "This is the practical 'submit a sample, wait for the result' cost — and it is where MT 13-mer's overlapping-"
         "13-mer tokenisation (138 k-mers/read over a 33M-row vocab) shows up: 1,066 r/s, below NT-v2's 1,221 despite "
         "100x fewer params. Pure model compute is far faster (see compute_speed); the gap is load+tokenise.",
         ha="center", fontsize=8.0, color=GRAY, wrap=True)
fig.text(0.5, 0.052,
         "Caveat: load is a ONE-TIME cost amortised over only 100K reads here; for larger samples per-read throughput rises toward the tokenisation-bound rate.",
         ha="center", fontsize=7.6, color=RED, wrap=True)

plt.tight_layout(rect=[0, 0.04, 1, 0.97])
plt.savefig(HERE / "speed_benchmark.png", bbox_inches="tight")
plt.savefig(HERE / "speed_benchmark.pdf", bbox_inches="tight")
plt.close()
print("Saved speed_benchmark.png / .pdf")
