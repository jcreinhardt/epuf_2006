#!/usr/bin/env python
"""Presentation cut of the men's parameter heatmaps: nu and tau only, side by side.

The six-panel figures from plot_param.py are for reading the whole fit; on a slide the
panels end up too small to see the thing they exist to show -- the raw fit's speckle and
its absence after the joint solve. This writes the two well-identified location/scale
panels at slide size, once for the raw stage-0 fits and once for the smoothed+constrained
ones.

COLOR LIMITS ARE SHARED across the two figures, per parameter, computed over the union of
both CSVs. With per-figure limits the smoothed panel gets its own (narrower) scale and the
comparison shows nothing but the rescaling.

  python code/cross_sections/plot_nu_tau.py
    -> output/cross_sections/nu_tau_men.pdf (+ .png)          raw stage-0 fits
       output/cross_sections/nu_tau_men_smoothed.pdf (+ .png) after the joint solve
"""
import sys
from pathlib import Path

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from plot_param import heatmap

RAW      = Path("output/cross_sections/cross_section_params.csv")
SMOOTHED = Path("output/cross_sections/cross_section_params_smoothed.csv")
OUTDIR   = Path("output/cross_sections")
SEX      = 1                                # nu/tau are the men's dPlN parameters
PANELS   = [("nu",  r"$\nu$  (log-location)", "viridis"),
            ("tau", r"$\tau$  (log-scale)",   "viridis")]


def load(path):
    df = pd.read_csv(path)
    df = df[df["sex"] == SEX].copy()
    df["cohort"] = df["year"] - df["age"]
    return df


def shared_lims(dfs, col):
    """2-98 pct over BOTH fits pooled -- one color scale for the raw/smoothed pair."""
    v = np.concatenate([d[col].to_numpy(dtype=float) for d in dfs])
    v = v[np.isfinite(v)]
    return (np.nanpercentile(v, 2), np.nanpercentile(v, 98)) if v.size else None


def plot(df, lims, title, out):
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2))
    for ax, (col, label, cmap) in zip(axes, PANELS):
        piv = df.pivot(index="age", columns="cohort", values=col)
        heatmap(ax, piv, cmap, False, lims=lims[col])
        ax.set_title(label, fontsize=12)
        ax.set_xlabel("birth cohort (yob)", fontsize=9)
        ax.set_ylabel("age", fontsize=9)
        ax.tick_params(labelsize=8)
    fig.suptitle(title, fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out.with_suffix(".pdf"))
    fig.savefig(out.with_suffix(".png"), dpi=150)
    plt.close(fig)
    print(f"wrote {out.with_suffix('.pdf')} and .png")


def main():
    raw, sm = load(RAW), load(SMOOTHED)
    lims = {col: shared_lims([raw, sm], col) for col, _, _ in PANELS}
    plot(raw, lims, "Per-cell MLE, unsmoothed and unconstrained",
         OUTDIR / "nu_tau_men")
    plot(sm, lims, "After the joint smoothed-constrained solve",
         OUTDIR / "nu_tau_men_smoothed")


if __name__ == "__main__":
    main()
