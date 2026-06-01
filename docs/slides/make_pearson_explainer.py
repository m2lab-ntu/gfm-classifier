#!/usr/bin/env python3
"""
Figure: How Pearson r is computed for sample-level abundance estimation.
Two-row layout:
  Row 1 — Per-sample computation (reads → abundance vectors → scatter → r)
  Row 2 — Aggregation over N samples (r_1 … r_N → mean ± std)
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.gridspec import GridSpec
from scipy.stats import pearsonr
from pathlib import Path

RNG  = np.random.default_rng(42)
OUT  = Path("/work/ymj1123ntu/token_level_gfm_classifier/docs/figures_0519/pearson_explainer.png")
THESIS_OUT = Path("/work/ymj1123ntu/thesis/figures/pearson_explainer.pdf")

# ── Colour palette ────────────────────────────────────────────────────────────
C_BLUE  = "#1a6faf"
C_GREEN = "#2a7f2a"
C_RED   = "#c0392b"
C_GRAY  = "#555555"
C_LGRAY = "#cccccc"
C_GOLD  = "#c07800"

# ── Synthetic data parameters (genus-level flavour) ───────────────────────────
# Species-level balanced dataset: each species equally likely.
# Genus true abundance = (# species in genus) / 1535.
# We generate a realistic species-per-genus distribution.
N_TAXA      = 120     # number of genera
N_SPECIES   = 1535    # total species
READ_ACC    = 0.671   # NT-Genus accuracy
N_READS     = 50_000  # reads per sample
N_SAMPLES   = 100     # total samples (partition)

# Draw species counts per genus from a discretised log-normal to get variance
raw = np.exp(RNG.normal(2.5, 0.6, N_TAXA))          # log-normal
sp_per_genus = np.round(raw / raw.sum() * N_SPECIES).astype(int)
sp_per_genus = np.clip(sp_per_genus, 1, None)
# Adjust to sum exactly to N_SPECIES
diff = N_SPECIES - sp_per_genus.sum()
for i in range(abs(diff)):
    sp_per_genus[i % N_TAXA] += int(np.sign(diff))
sp_per_genus = np.clip(sp_per_genus, 1, None)

true_abund = sp_per_genus / sp_per_genus.sum()  # sums to 1

def simulate_sample(true_abund, read_acc, n_reads, rng):
    """Simulate per-taxon predicted counts given true abundance and read accuracy."""
    n_taxa = len(true_abund)
    true_counts = rng.multinomial(n_reads, true_abund)
    pred_counts = np.zeros(n_taxa, dtype=float)
    for c, cnt in enumerate(true_counts):
        if cnt == 0:
            continue
        correct = rng.binomial(cnt, read_acc)
        wrong   = cnt - correct
        pred_counts[c] += correct
        if wrong > 0:
            targets = rng.choice(n_taxa, size=wrong)
            np.add.at(pred_counts, targets, 1)
    return true_counts / n_reads, pred_counts / n_reads

# ── Simulate N_SAMPLES and collect per-sample r ───────────────────────────────
per_sample_r = []
sample_true_list = []
sample_pred_list = []

for _ in range(N_SAMPLES):
    t, p = simulate_sample(true_abund, READ_ACC, N_READS, RNG)
    r, _ = pearsonr(t, p)
    per_sample_r.append(r)
    sample_true_list.append(t)
    sample_pred_list.append(p)

per_sample_r = np.array(per_sample_r)
mean_r = per_sample_r.mean()
std_r  = per_sample_r.std()

# Pick a representative sample (closest to median r) for Row 1
med_idx = int(np.argmin(np.abs(per_sample_r - np.median(per_sample_r))))
t_rep   = sample_true_list[med_idx]
p_rep   = sample_pred_list[med_idx]
r_rep   = per_sample_r[med_idx]

print(f"Simulated:  mean r = {mean_r:.4f} ± {std_r:.4f}  (target ≈ 0.993)")

# ─────────────────────────────────────────────────────────────────────────────
# Layout: 2 rows
#   Row 1: [reads schematic | arrow | abundance bars | arrow | scatter + r]
#   Row 2: [N scatter minis | arrow | r distribution + mean±std]
# ─────────────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 9))
gs  = GridSpec(2, 5, figure=fig,
               left=0.04, right=0.98, top=0.93, bottom=0.06,
               wspace=0.45, hspace=0.55,
               width_ratios=[1.6, 0.3, 1.8, 0.3, 2.2])

ax_reads  = fig.add_subplot(gs[0, 0])
ax_arr1   = fig.add_subplot(gs[0, 1])
ax_bars   = fig.add_subplot(gs[0, 2])
ax_arr2   = fig.add_subplot(gs[0, 3])
ax_scat   = fig.add_subplot(gs[0, 4])

ax_minis  = fig.add_subplot(gs[1, 0:3])
ax_arr3   = fig.add_subplot(gs[1, 3])
ax_dist   = fig.add_subplot(gs[1, 4])

for ax in [ax_reads, ax_arr1, ax_arr2, ax_arr3]:
    ax.axis("off")

# ── Row 1, Panel A: reads schematic ──────────────────────────────────────────
ax_reads.set_xlim(0, 1); ax_reads.set_ylim(0, 1)
ax_reads.set_title("Sample $s$\n(reads drawn from pool)", fontsize=10,
                   fontweight="bold", color=C_BLUE, pad=4)

# Draw 8 read "bars" with predicted labels
read_colors = [C_BLUE, C_GREEN, C_BLUE, C_RED, C_GREEN,
               C_BLUE, C_GOLD, C_BLUE]
read_labels_txt = ["g₁₂", "g₄₇", "g₁₂", "g₈₃", "g₄₇",
                   "g₁₂", "g₉₁", "g₁₂"]
y_positions = np.linspace(0.88, 0.08, 8)
for i, (y, col, lbl) in enumerate(zip(y_positions, read_colors, read_labels_txt)):
    ax_reads.add_patch(mpatches.FancyBboxPatch(
        (0.08, y - 0.045), 0.84, 0.07,
        boxstyle="round,pad=0.01", fc=col, ec="white", alpha=0.85, lw=0.5))
    ax_reads.text(0.50, y, lbl, ha="center", va="center",
                  fontsize=9, color="white", fontweight="bold")

# Vdots
ax_reads.text(0.50, -0.01, "⋮", ha="center", va="bottom", fontsize=12, color=C_GRAY)
ax_reads.text(0.50, -0.06, f"{N_READS:,} reads", ha="center", va="top",
              fontsize=8, color=C_GRAY, style="italic")
ax_reads.set_axis_off()

# ── Row 1, arrows ─────────────────────────────────────────────────────────────
def draw_arrow(ax, label=""):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.annotate("", xy=(0.9, 0.5), xytext=(0.1, 0.5),
                arrowprops=dict(arrowstyle="-|>", color=C_GRAY, lw=2))
    if label:
        ax.text(0.5, 0.65, label, ha="center", va="bottom",
                fontsize=8, color=C_GRAY, style="italic")
    ax.axis("off")

draw_arrow(ax_arr1, "count\n& normalise")
draw_arrow(ax_arr2, "scatter\nplot")

# ── Row 1, Panel B: abundance bars ────────────────────────────────────────────
# Show top-8 genera (sorted by true abundance — all equal, but show as bars)
show_n  = 8
t_show  = t_rep[:show_n]
p_show  = p_rep[:show_n]
x_show  = np.arange(show_n)
w = 0.35

bars_t = ax_bars.bar(x_show - w/2, t_show * 100, width=w,
                     color=C_BLUE, alpha=0.8, label="True", edgecolor="white")
bars_p = ax_bars.bar(x_show + w/2, p_show * 100, width=w,
                     color=C_GREEN, alpha=0.8, label="Predicted", edgecolor="white")

ax_bars.set_xticks(x_show)
ax_bars.set_xticklabels([f"g{i+1}" for i in range(show_n)], fontsize=8)
ax_bars.set_ylabel("Relative abundance (%)", fontsize=9)
ax_bars.set_title(f"Abundance vectors\n(showing {show_n} of {N_TAXA} genera)",
                  fontsize=10, fontweight="bold", color=C_BLUE)
ax_bars.legend(fontsize=8, loc="upper right", framealpha=0.7)
ax_bars.set_ylim(0, max(max(t_show), max(p_show)) * 100 * 1.35)
ax_bars.text(show_n - 0.5, ax_bars.get_ylim()[1] * 0.95, "⋯",
             ha="right", va="top", fontsize=14, color=C_GRAY)
ax_bars.spines["top"].set_visible(False)
ax_bars.spines["right"].set_visible(False)
ax_bars.tick_params(axis="both", labelsize=8)

# ── Row 1, Panel C: representative scatter ────────────────────────────────────
ax_scat.scatter(t_rep * 100, p_rep * 100,
                s=18, alpha=0.55, color=C_BLUE, edgecolors="none")

lim_max = max(t_rep.max(), p_rep.max()) * 100 * 1.15
ax_scat.plot([0, lim_max], [0, lim_max], "--", color=C_LGRAY, lw=1.2, label="$y=x$")
ax_scat.set_xlim(-0.01, lim_max)
ax_scat.set_ylim(-0.01, lim_max)
ax_scat.set_xlabel("True relative abundance (%)", fontsize=9)
ax_scat.set_ylabel("Predicted relative abundance (%)", fontsize=9)
ax_scat.set_title(f"Scatter: predicted vs true\n(1 point = 1 genus, all {N_TAXA} genera)",
                  fontsize=10, fontweight="bold", color=C_BLUE)
ax_scat.text(0.97, 0.08, f"$r_s = {r_rep:.4f}$",
             transform=ax_scat.transAxes, ha="right", va="bottom",
             fontsize=13, color=C_RED, fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=C_RED, alpha=0.9))
formula = r"$r_s = \frac{\sum_c (\hat{a}_c - \bar{\hat{a}})(a_c - \bar{a})}{\sqrt{\sum_c(\hat{a}_c-\bar{\hat{a}})^2 \sum_c(a_c-\bar{a})^2}}$"
ax_scat.text(0.03, 0.97, formula,
             transform=ax_scat.transAxes, ha="left", va="top",
             fontsize=9.5, color=C_GRAY,
             bbox=dict(boxstyle="round,pad=0.3", fc="#f8f8f8", ec=C_LGRAY, alpha=0.9))
ax_scat.spines["top"].set_visible(False)
ax_scat.spines["right"].set_visible(False)
ax_scat.tick_params(axis="both", labelsize=8)
ax_scat.legend(fontsize=8, loc="upper left")

# ── Row 2, Panel: N mini-scatters ────────────────────────────────────────────
ax_minis.set_xlim(0, 1); ax_minis.set_ylim(0, 1)
ax_minis.axis("off")
ax_minis.set_title(f"Repeat over $N = {N_SAMPLES}$ independent partition samples",
                   fontsize=10, fontweight="bold", color=C_GOLD, pad=4)

show_minis = 6
mini_w = 0.13
mini_h = 0.72
mini_gap = (1.0 - show_minis * mini_w) / (show_minis + 1)

for i in range(show_minis):
    left = mini_gap + i * (mini_w + mini_gap)
    bottom = 0.14
    ax_m = fig.add_axes([
        ax_minis.get_position().x0 + left * ax_minis.get_position().width,
        ax_minis.get_position().y0 + bottom * ax_minis.get_position().height,
        mini_w * ax_minis.get_position().width,
        mini_h * ax_minis.get_position().height,
    ])
    t_m = sample_true_list[i]
    p_m = sample_pred_list[i]
    lm  = max(t_m.max(), p_m.max()) * 100 * 1.1
    ax_m.scatter(t_m * 100, p_m * 100, s=2.5, alpha=0.4, color=C_BLUE, edgecolors="none")
    ax_m.plot([0, lm], [0, lm], "--", color=C_LGRAY, lw=0.8)
    ax_m.set_xlim(-0.005, lm); ax_m.set_ylim(-0.005, lm)
    ax_m.set_xticks([]); ax_m.set_yticks([])
    ax_m.set_title(f"$s_{{{i+1}}}$", fontsize=8, pad=2)
    ax_m.text(0.97, 0.07, f"$r={per_sample_r[i]:.3f}$",
              transform=ax_m.transAxes, ha="right", va="bottom",
              fontsize=7, color=C_RED, fontweight="bold")
    for sp in ["top", "right", "bottom", "left"]:
        ax_m.spines[sp].set_linewidth(0.6)
        ax_m.spines[sp].set_color(C_LGRAY)

# Ellipsis between minis and final panel
ax_minis.text(0.88, 0.45, "···", ha="center", va="center",
              fontsize=22, color=C_GRAY, transform=ax_minis.transAxes)
ax_minis.text(0.97, 0.45, f"$s_{{100}}$", ha="center", va="center",
              fontsize=9, color=C_GRAY, transform=ax_minis.transAxes)

# ── Row 2, arrow ─────────────────────────────────────────────────────────────
draw_arrow(ax_arr3, "aggregate")

# ── Row 2, Panel: r distribution ─────────────────────────────────────────────
ax_dist.hist(per_sample_r, bins=20, color=C_BLUE, alpha=0.75, edgecolor="white", linewidth=0.5)
ax_dist.axvline(mean_r, color=C_RED, lw=2.5, linestyle="-",  label=f"mean $r$ = {mean_r:.4f}")
ax_dist.axvline(mean_r - std_r, color=C_RED, lw=1.5, linestyle="--", alpha=0.7)
ax_dist.axvline(mean_r + std_r, color=C_RED, lw=1.5, linestyle="--", alpha=0.7,
                label=f"±std = {std_r:.4f}")
ax_dist.set_xlabel("Pearson $r$ per sample", fontsize=9)
ax_dist.set_ylabel("Count (out of 100 samples)", fontsize=9)
ax_dist.set_title(f"Distribution of per-sample $r$\nFinal metric: $\\bar{{r}} \\pm \\sigma$",
                  fontsize=10, fontweight="bold", color=C_GOLD)
ax_dist.text(0.04, 0.92,
             f"$\\bar{{r}} = {mean_r:.4f} \\pm {std_r:.4f}$",
             transform=ax_dist.transAxes, ha="left", va="top",
             fontsize=12, color=C_RED, fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=C_RED, alpha=0.9))
ax_dist.legend(fontsize=8, loc="lower left")
ax_dist.spines["top"].set_visible(False)
ax_dist.spines["right"].set_visible(False)
ax_dist.tick_params(axis="both", labelsize=8)

# ── Row labels ────────────────────────────────────────────────────────────────
fig.text(0.01, 0.96, "(a)", fontsize=13, fontweight="bold", color=C_GRAY, va="top")
fig.text(0.01, 0.48, "(b)", fontsize=13, fontweight="bold", color=C_GRAY, va="top")

fig.suptitle(
    "Sample-Level Pearson $r$: Computation Pipeline",
    fontsize=14, fontweight="bold", y=0.99,
)

OUT.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(OUT, dpi=180, bbox_inches="tight")
print(f"Saved PNG: {OUT}")

THESIS_OUT.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(THESIS_OUT, bbox_inches="tight")
print(f"Saved PDF: {THESIS_OUT}")
plt.close()
