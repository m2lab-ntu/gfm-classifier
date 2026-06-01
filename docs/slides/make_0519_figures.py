#!/usr/bin/env python3
"""Generate comparison figures for 0519 slides — genus + species sample-level evaluation."""

import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

OUT = Path("/work/ymj1123ntu/token_level_gfm_classifier/docs/figures_0519")
OUT.mkdir(exist_ok=True)

RES = Path("/work/ymj1123ntu/token_level_gfm_classifier/results")

# ─── Load all JSON ───────────────────────────────────────────────────────────
def load(path):
    with open(path) as f:
        return json.load(f)

# Genus models (5M pool, 120 classes)
mt13_genus = load(RES / "mt_genus_13mer/eval_sample_level/sample_metrics.json")
genus_v9   = load(RES / "nt_token_genus_lora_v9_50M/eval_sample_level/sample_metrics.json")
mt6_genus  = load(RES / "mt_genus_6mer_s1/eval_sample_level/sample_metrics.json")

# Species models (100K pool, 1535 classes)
sp_v4      = load(RES / "nt_token_species_v4_50M/eval_sample_level_test100k/sample_metrics.json")
sp_v4_hier = load(RES / "nt_token_species_v4_50M/eval_sample_level_hier_test100k/sample_metrics.json")
mt13_flat  = load(RES / "mt_species_flat/eval_sample_level_100K/sample_metrics.json")
mt13_hier  = load(RES / "mt_hierarchical/eval_sample_level_100K/sample_metrics.json")
mt6_flat   = load(RES / "mt_6mer_species_flat/eval_sample_level_100K/sample_metrics.json")
mt6_hier   = load(RES / "mt_6mer_hierarchical/eval_sample_level_100K/sample_metrics.json")

# ─── Color palette ───────────────────────────────────────────────────────────
C_MT13_GENUS = "#006400"   # dark green   MT 13-mer genus
C_NT_GENUS   = "#1a6faf"   # dark blue    NT-v2 v9 genus
C_MT6_GENUS  = "#8FBC8F"   # light green  MT 6-mer genus
C_NT_GENUS = "#1a6faf"   # dark blue   NT-v2 genus (keep alias for species section)
C_SP_V4    = "#7e9ec4"   # light blue  NT-v2 species flat
C_SP_V4H   = "#4a7eb0"   # darker blue NT-v2 species hier
C_MT13F    = "#d62728"   # red         MT 13-mer flat
C_MT13H    = "#e05a00"   # orange-red  MT 13-mer hierarchical
C_MT6F     = "#bcbd22"   # yellow-green MT 6-mer flat
C_MT6H     = "#8c9c00"   # dark green  MT 6-mer hierarchical

# ─────────────────────────────────────────────────────────────────────────────
# FIG 0: Genus 3-model comparison
# ─────────────────────────────────────────────────────────────────────────────
genus_names  = ["MT 13-mer genus\n(87.4% acc)", "NT-v2 v9 genus\n(67.1% acc)", "MT 6-mer genus\n(48.8% acc)"]
genus_data   = [mt13_genus, genus_v9, mt6_genus]
genus_colors = [C_MT13_GENUS, C_NT_GENUS, C_MT6_GENUS]

g_pearson     = [d["abundance_estimation"]["pearson_r_mean"] for d in genus_data]
g_pearson_std = [d["abundance_estimation"]["pearson_r_std"] for d in genus_data]
g_bc          = [d["abundance_estimation"]["bray_curtis_mean"] for d in genus_data]
g_bc_std      = [d["abundance_estimation"]["bray_curtis_std"] for d in genus_data]
g_spearman    = [d["abundance_estimation"]["spearman_r_mean"] for d in genus_data]
g_roc         = [d["roc_detection"]["auc"] for d in genus_data]
g_acc         = [d["read_level_accuracy"] for d in genus_data]

xg = np.arange(len(genus_names))

fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))

# Pearson r
ax = axes[0]
bars = ax.bar(xg, g_pearson, width=0.55, color=genus_colors, edgecolor="white")
ax.errorbar(xg, g_pearson, yerr=g_pearson_std, fmt="none", color="black", capsize=5, linewidth=1.5)
ax.set_xticks(xg); ax.set_xticklabels(genus_names, fontsize=9)
ax.set_ylim(0.97, 1.002); ax.set_ylabel("Pearson r", fontsize=11)
ax.set_title("Abundance Correlation", fontsize=12, fontweight="bold")
for bar, v in zip(bars, g_pearson):
    ax.text(bar.get_x() + bar.get_width()/2, v + 0.0005, f"{v:.4f}",
            ha="center", va="bottom", fontsize=11, fontweight="bold")
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.grid(axis="y", alpha=0.3)

# Bray-Curtis
ax = axes[1]
bars = ax.bar(xg, g_bc, width=0.55, color=genus_colors, edgecolor="white")
ax.errorbar(xg, g_bc, yerr=g_bc_std, fmt="none", color="black", capsize=5, linewidth=1.5)
ax.set_xticks(xg); ax.set_xticklabels(genus_names, fontsize=9)
ax.set_ylim(0, 0.22); ax.set_ylabel("Bray-Curtis dissimilarity  (↓ better)", fontsize=11)
ax.set_title("Abundance Dissimilarity", fontsize=12, fontweight="bold")
for bar, v in zip(bars, g_bc):
    ax.text(bar.get_x() + bar.get_width()/2, v + 0.003, f"{v:.4f}",
            ha="center", va="bottom", fontsize=11, fontweight="bold")
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.grid(axis="y", alpha=0.3)

# ROC AUC
ax = axes[2]
bars = ax.bar(xg, g_roc, width=0.55, color=genus_colors, edgecolor="white")
ax.set_xticks(xg); ax.set_xticklabels(genus_names, fontsize=9)
ax.set_ylim(0.4, 1.0); ax.set_ylabel("ROC AUC", fontsize=11)
ax.set_title("Genus Detection  (ROC AUC)", fontsize=12, fontweight="bold")
for bar, v in zip(bars, g_roc):
    ax.text(bar.get_x() + bar.get_width()/2, v + 0.005, f"{v:.4f}",
            ha="center", va="bottom", fontsize=11, fontweight="bold")
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.grid(axis="y", alpha=0.3)

fig.suptitle("Genus-Level Sample Evaluation: Effect of Tokenization  (5M pool, 120 genera)",
             fontsize=13, fontweight="bold", y=1.02)
plt.tight_layout()
plt.savefig(OUT / "genus_comparison_3model.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: genus_comparison_3model.png")

# ─────────────────────────────────────────────────────────────────────────────
# Species-level model lists (reused in multiple figures)
# ─────────────────────────────────────────────────────────────────────────────
LABELS = {
    "NT-v2 flat\n(1535 cls, 100K)": C_SP_V4,
    "NT-v2 hier.\n(1535 cls, 100K)": C_SP_V4H,
    "MT 13-mer flat\n(1535 cls, 100K)": C_MT13F,
    "MT 13-mer hier\n(1535 cls, 100K)": C_MT13H,
    "MT 6-mer flat\n(1535 cls, 100K)": C_MT6F,
    "MT 6-mer hier\n(1535 cls, 100K)": C_MT6H,
}

MODELS = list(LABELS.keys())
COLORS = list(LABELS.values())
DATA   = [sp_v4, sp_v4_hier, mt13_flat, mt13_hier, mt6_flat, mt6_hier]

# ─────────────────────────────────────────────────────────────────────────────
# FIG 1: Abundance estimation — Pearson r and Bray-Curtis side by side
# ─────────────────────────────────────────────────────────────────────────────
pearson = [d["abundance_estimation"]["pearson_r_mean"] for d in DATA]
bc      = [d["abundance_estimation"]["bray_curtis_mean"] for d in DATA]
pearson_std = [d["abundance_estimation"]["pearson_r_std"] for d in DATA]
bc_std      = [d["abundance_estimation"]["bray_curtis_std"] for d in DATA]
read_acc    = [d["read_level_accuracy"] for d in DATA]

x = np.arange(len(MODELS))

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Left: Pearson r
ax = axes[0]
bars = ax.bar(x, pearson, width=0.6, color=COLORS, edgecolor="white", linewidth=0.5)
ax.errorbar(x, pearson, yerr=pearson_std, fmt="none", color="black", capsize=4, linewidth=1.2)
ax.set_xticks(x)
ax.set_xticklabels(MODELS, fontsize=8.5)
ax.set_ylabel("Pearson r  (mean ± std, 100 samples)", fontsize=11)
ax.set_title("Abundance Correlation  (Pearson r)", fontsize=12, fontweight="bold")
ax.set_ylim(0, 1.05)
ax.axhline(1.0, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
for bar, val in zip(bars, pearson):
    ax.text(bar.get_x() + bar.get_width()/2, val + 0.02, f"{val:.3f}",
            ha="center", va="bottom", fontsize=9, fontweight="bold")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", alpha=0.3)

# Right: Bray-Curtis
ax = axes[1]
bars = ax.bar(x, bc, width=0.6, color=COLORS, edgecolor="white", linewidth=0.5)
ax.errorbar(x, bc, yerr=bc_std, fmt="none", color="black", capsize=4, linewidth=1.2)
ax.set_xticks(x)
ax.set_xticklabels(MODELS, fontsize=8.5)
ax.set_ylabel("Bray-Curtis dissimilarity  (lower = better)", fontsize=11)
ax.set_title("Abundance Dissimilarity  (Bray-Curtis)", fontsize=12, fontweight="bold")
ax.set_ylim(0, 0.85)
ax.axhline(0.0, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
for bar, val in zip(bars, bc):
    ax.text(bar.get_x() + bar.get_width()/2, val + 0.01, f"{val:.3f}",
            ha="center", va="bottom", fontsize=9, fontweight="bold")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", alpha=0.3)

fig.suptitle("Species-Level Abundance Estimation  (100K independent test set, 1535 species, reads_per_sample=1,000)",
             fontsize=13, fontweight="bold", y=1.02)
plt.tight_layout()
plt.savefig(OUT / "abundance_comparison_bar.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: abundance_comparison_bar.png")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 2: ROC Detection AUC comparison bar
# ─────────────────────────────────────────────────────────────────────────────
roc_auc = [d["roc_detection"]["auc"] for d in DATA]

fig, ax = plt.subplots(figsize=(9, 4.5))
bars = ax.bar(x, roc_auc, width=0.6, color=COLORS, edgecolor="white", linewidth=0.5)
ax.set_xticks(x)
ax.set_xticklabels(MODELS, fontsize=9)
ax.set_ylabel("ROC AUC  (species presence/absence detection)", fontsize=11)
ax.set_title("Species Detection Performance  (ROC AUC)", fontsize=13, fontweight="bold")
ax.set_ylim(0.5, 1.02)
ax.axhline(0.5, color="gray", linestyle=":", linewidth=1, alpha=0.6, label="Random")
for bar, val in zip(bars, roc_auc):
    ax.text(bar.get_x() + bar.get_width()/2, val + 0.005, f"{val:.4f}",
            ha="center", va="bottom", fontsize=10, fontweight="bold")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", alpha=0.3)
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig(OUT / "roc_auc_comparison.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: roc_auc_comparison.png")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 3: ROC operating point curves (sensitivity at fixed specificity)
# ─────────────────────────────────────────────────────────────────────────────
spec_targets = [0.80, 0.90, 0.95, 0.99]
spec_labels  = ["Spec\n80%", "Spec\n90%", "Spec\n95%", "Spec\n99%"]
spec_keys    = ["spec_80pct", "spec_90pct", "spec_95pct", "spec_99pct"]

fig, ax = plt.subplots(figsize=(9, 5))
for d, label, color in zip(DATA, MODELS, COLORS):
    ops = d["roc_detection"]["operating_points"]
    sens = [ops[k]["sensitivity"] for k in spec_keys]
    ax.plot(range(4), sens, "o-", color=color, label=label.replace("\n", " "), linewidth=2, markersize=7)

ax.set_xticks(range(4))
ax.set_xticklabels(spec_labels, fontsize=11)
ax.set_ylabel("Sensitivity  (true positive rate)", fontsize=11)
ax.set_title("Species Detection: Sensitivity at Fixed Specificity", fontsize=12, fontweight="bold")
ax.set_ylim(0, 1.05)
ax.legend(fontsize=8.5, loc="lower left", ncol=2)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(OUT / "roc_operating_points.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: roc_operating_points.png")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 4: Detection threshold curves — sensitivity vs count threshold
# ─────────────────────────────────────────────────────────────────────────────
count_thresholds = [1, 2, 5, 10, 20, 50]
ct_keys = [">=1_reads", ">=2_reads", ">=5_reads", ">=10_reads", ">=20_reads", ">=50_reads"]

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Sensitivity vs count threshold
ax = axes[0]
for d, label, color in zip(DATA, MODELS, COLORS):
    sens = [d["binary_detection_by_count_threshold"][k]["sensitivity"] for k in ct_keys]
    ax.plot(count_thresholds, sens, "o-", color=color, label=label.replace("\n", " "),
            linewidth=2, markersize=6)
ax.set_xscale("log")
ax.set_xlabel("Min predicted reads  (count threshold)", fontsize=11)
ax.set_ylabel("Sensitivity", fontsize=11)
ax.set_title("Sensitivity vs Count Threshold", fontsize=12, fontweight="bold")
ax.set_ylim(0, 1.05)
ax.legend(fontsize=8, ncol=1)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(alpha=0.3)

# Specificity vs count threshold
ax = axes[1]
for d, label, color in zip(DATA, MODELS, COLORS):
    spec = [d["binary_detection_by_count_threshold"][k]["specificity"] for k in ct_keys]
    ax.plot(count_thresholds, spec, "o-", color=color, label=label.replace("\n", " "),
            linewidth=2, markersize=6)
ax.set_xscale("log")
ax.set_xlabel("Min predicted reads  (count threshold)", fontsize=11)
ax.set_ylabel("Specificity", fontsize=11)
ax.set_title("Specificity vs Count Threshold", fontsize=12, fontweight="bold")
ax.set_ylim(0, 1.05)
ax.legend(fontsize=8, ncol=1)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(alpha=0.3)

fig.suptitle("Species Presence/Absence Detection vs Read Count Threshold",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(OUT / "detection_threshold_curves.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: detection_threshold_curves.png")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 5: Read accuracy + Pearson r + Bray-Curtis + ROC AUC summary heatmap-style
# ─────────────────────────────────────────────────────────────────────────────
# Focus: species models only (not NT-v2 genus, different scale)
sp_names  = ["NT-v2\nflat", "NT-v2\nhier.", "MT 13-mer\nflat", "MT 13-mer\nhier.", "MT 6-mer\nflat", "MT 6-mer\nhier."]
sp_data   = [sp_v4, sp_v4_hier, mt13_flat, mt13_hier, mt6_flat, mt6_hier]
sp_colors = [C_SP_V4, C_SP_V4H, C_MT13F, C_MT13H, C_MT6F, C_MT6H]

metrics = {
    "Read-level\nAccuracy": [d["read_level_accuracy"] for d in sp_data],
    "Pearson r\n(abundance)": [d["abundance_estimation"]["pearson_r_mean"] for d in sp_data],
    "1 − Bray-Curtis\n(higher=better)": [1 - d["abundance_estimation"]["bray_curtis_mean"] for d in sp_data],
    "ROC AUC\n(detection)": [d["roc_detection"]["auc"] for d in sp_data],
}

x = np.arange(len(sp_names))
n_metrics = len(metrics)
fig, axes = plt.subplots(1, n_metrics, figsize=(15, 4.5), sharey=False)

for ax, (metric_name, vals) in zip(axes, metrics.items()):
    bars = ax.bar(x, vals, width=0.65, color=sp_colors, edgecolor="white", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(sp_names, fontsize=8.5)
    ax.set_title(metric_name, fontsize=10.5, fontweight="bold")
    ax.set_ylim(0, 1.05)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.02, f"{val:.3f}",
                ha="center", va="bottom", fontsize=9, fontweight="bold", rotation=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)

fig.suptitle("Species-Level Evaluation Summary  (100K test set, 1535 species)",
             fontsize=13, fontweight="bold", y=1.02)
plt.tight_layout()
plt.savefig(OUT / "species_summary_4panel.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: species_summary_4panel.png")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 6: Genus tokenization effect on accuracy — read acc vs Pearson r vs BC scatter
# Shows the "diminishing returns" at genus level
# ─────────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

g_acc_pct = [v * 100 for v in g_acc]

# Left: read acc vs Pearson r
ax = axes[0]
for i, (name, color) in enumerate(zip(genus_names, genus_colors)):
    ax.scatter(g_acc_pct[i], g_pearson[i], color=color, s=180, zorder=5, edgecolors="white", linewidth=1.5)
    ax.annotate(name.replace("\n", " "), (g_acc_pct[i], g_pearson[i]),
                textcoords="offset points", xytext=(0, 10), ha="center", fontsize=9, color=color, fontweight="bold")
ax.set_xlabel("Read-level accuracy (%)", fontsize=11)
ax.set_ylabel("Pearson r", fontsize=11)
ax.set_title("Genus: Read Accuracy vs Abundance Correlation", fontsize=11, fontweight="bold")
ax.set_xlim(40, 95); ax.set_ylim(0.975, 1.002)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.grid(alpha=0.3)

# Right: read acc vs Bray-Curtis
ax = axes[1]
for i, (name, color) in enumerate(zip(genus_names, genus_colors)):
    ax.scatter(g_acc_pct[i], g_bc[i], color=color, s=180, zorder=5, edgecolors="white", linewidth=1.5)
    ax.annotate(name.replace("\n", " "), (g_acc_pct[i], g_bc[i]),
                textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, color=color, fontweight="bold")
ax.set_xlabel("Read-level accuracy (%)", fontsize=11)
ax.set_ylabel("Bray-Curtis dissimilarity  (↓ better)", fontsize=11)
ax.set_title("Genus: Read Accuracy vs BC Dissimilarity", fontsize=11, fontweight="bold")
ax.set_xlim(40, 95); ax.set_ylim(0, 0.20)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.grid(alpha=0.3)

fig.suptitle("Genus-Level: Better Tokenization → Lower BC  (Pearson r saturates near 1.0)",
             fontsize=12, fontweight="bold", y=1.02)
plt.tight_layout()
plt.savefig(OUT / "genus_acc_vs_abundance.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: genus_acc_vs_abundance.png")

# ─────────────────────────────────────────────────────────────────────────────
# FIG 7: MT 13-mer flat vs hierarchical — species detection detail
# ─────────────────────────────────────────────────────────────────────────────
abund_thresholds = ["≥0%", "≥0.01%", "≥0.05%", "≥0.10%", "≥0.50%", "≥1.00%"]
ab_keys = [">=0.00%", ">=0.01%", ">=0.05%", ">=0.10%", ">=0.50%", ">=1.00%"]

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

compared = [
    (mt13_flat, "MT 13-mer flat", C_MT13F),
    (mt13_hier, "MT 13-mer hier.", C_MT13H),
]

# Sensitivity
ax = axes[0]
for d, label, color in compared:
    sens = [d["binary_detection_by_abundance_threshold"][k]["sensitivity"] for k in ab_keys]
    ax.plot(range(6), sens, "o-", color=color, label=label, linewidth=2.5, markersize=8)
ax.set_xticks(range(6))
ax.set_xticklabels(abund_thresholds, fontsize=10)
ax.set_ylabel("Sensitivity", fontsize=11)
ax.set_title("Sensitivity vs Predicted Abundance Threshold", fontsize=12, fontweight="bold")
ax.set_ylim(0, 1.05)
ax.legend(fontsize=11)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(alpha=0.3)

# Specificity
ax = axes[1]
for d, label, color in compared:
    spec = [d["binary_detection_by_abundance_threshold"][k]["specificity"] for k in ab_keys]
    ax.plot(range(6), spec, "o-", color=color, label=label, linewidth=2.5, markersize=8)
ax.set_xticks(range(6))
ax.set_xticklabels(abund_thresholds, fontsize=10)
ax.set_ylabel("Specificity", fontsize=11)
ax.set_title("Specificity vs Predicted Abundance Threshold", fontsize=12, fontweight="bold")
ax.set_ylim(0, 1.05)
ax.legend(fontsize=11)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(alpha=0.3)

fig.suptitle("MT 13-mer: Flat vs Hierarchical Species Detection  (100K test set)",
             fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(OUT / "mt13_flat_vs_hier_detection.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: mt13_flat_vs_hier_detection.png")

print(f"\nAll figures saved to {OUT}")
