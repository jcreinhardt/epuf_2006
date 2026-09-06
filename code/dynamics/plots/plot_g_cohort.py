#!/usr/bin/env python
"""Coefficient paths of the cohort x sex profile g(t): g0..g3 by cohort, men and women.

Reads any number of the section's CSVs -- estimation output from any --mode, or an
_extrapolated file -- and overlays them, one line per file.  For an extrapolated file the
estimated cohorts are drawn as open markers and the two extrapolated tails as lines, kept
apart so nothing falsely bridges the backward and forward anchors.  The shaded band marks
the cohorts observed over the full 25-55 span, outside which any fitted polynomial is
extrapolating.

Remember the level caveat: --mode ols sits ~0.36 log points above the SMM modes in g0 (it
absorbs E[u | .]); the slopes are the comparable rows.

Run from the project root:
    python code/dynamics/plots/plot_g_cohort.py output/dynamics/g_cohort_smm_mean.csv \
        output/dynamics/g_cohort_smm_mean_extrapolated.csv [--out NAME]
Output: output/dynamics/plots/<NAME>.{pdf,png}   (default NAME: g_cohort)
"""
import argparse
import os

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "output/dynamics/plots"
COEFS = ["g0", "g1", "g2", "g3"]
TITLES = {"g0": "$g_0$ (level at age 40)", "g1": "$g_1$ (slope)",
          "g2": "$g_2$ (curvature)", "g3": "$g_3$ (cubic)"}
COLORS = ["#1f6fb4", "#d1642f", "#3a9d5d", "#7a5195", "#555555"]


def draw(ax, d, k, color, label):
    if "source" in d:
        for blk in ("extrap_back", "extrap_fwd"):
            m = d["source"] == blk
            ax.plot(d.loc[m, "cohort"], d.loc[m, k], color=color, lw=1.2)
        m = d["source"] == "fit"
        ax.plot(d.loc[m, "cohort"], d.loc[m, k], ls="none", marker="o", ms=3.5, mfc="none",
                color=color, label=label)
    else:
        ax.plot(d["cohort"], d[k], color=color, lw=1.3, marker="o", ms=2.5, label=label)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csvs", nargs="+")
    ap.add_argument("--out", default="g_cohort")
    ap.add_argument("--outdir", default=OUT)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    tabs = [(os.path.splitext(os.path.basename(p))[0], pd.read_csv(p)) for p in args.csvs]
    fit = [d[d["source"] == "fit"] if "source" in d else d for _, d in tabs]
    lo = min(int(d["cohort"].min()) for d in fit)
    hi = max(int(d["cohort"].max()) for d in fit)

    fig, axes = plt.subplots(4, 2, figsize=(9.5, 10.0), sharex=True)
    for j, sex in enumerate(("male", "female")):
        for i, k in enumerate(COEFS):
            ax = axes[i, j]
            for (name, d), color in zip(tabs, COLORS):
                draw(ax, d[d["sex"] == sex], k, color, name)
            ax.axvspan(lo, hi, color="0.92", zorder=0)
            ax.axhline(0, color="0.7", lw=0.6)
            if i == 0:
                ax.set_title(sex, fontsize=10)
            if j == 0:
                ax.set_ylabel(TITLES[k], fontsize=9)
            if i == 3:
                ax.set_xlabel("cohort (year at age 25)", fontsize=9)
            ax.tick_params(labelsize=8)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
    axes[0, 0].legend(fontsize=7, frameon=False, loc="best")
    fig.tight_layout()
    path = os.path.join(args.outdir, args.out)
    for ext in ("pdf", "png"):
        fig.savefig(f"{path}.{ext}", dpi=200, bbox_inches="tight")
    print(f"wrote {path}.pdf/.png")


if __name__ == "__main__":
    main()
