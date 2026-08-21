#!/usr/bin/env python
"""Cohort x age heatmap of the share of workers censored at the taxable maximum.

Every fit in the cross-section pipeline is doubly Type-I censored: earnings at or
above HIGHC = taxmax(year) - $1000 enter the likelihood only as "somewhere above the
cap". This figure shows how much of each cell that is -- the share n_high / n -- laid
out on a birth-cohort (x) by age (y) grid, so a calendar year is an anti-diagonal and
one cohort's life-cycle path reads straight up a column.

Read it as the map of where the data carry information about the upper tail and where
they do not: the dark 1950s-60s block (cohorts born ~1900-1930 at prime age) is the
tight-cap era where three quarters of men's earnings are at the cap and the tail is
identified only through the aggregate constraint, not the cell's own observations.

The share is the empirical one actually used in estimation, not the model's
P(at cap), and the cells are exactly the estimation sample (>= MIN_N = 1000
observations); cells outside it are blank.

  python code/cross_sections/plot_censored_share.py [csv]
    -> output/cross_sections/plots/censored_share_cohort_age.pdf (+ .png)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PARAMS = Path("output/cross_sections/cross_section_params.csv")
OUTDIR = Path("output/cross_sections/plots")
SEXLABEL = {1: "Men", 2: "Women"}

# minimal theme: thin hairline frame, no grid, no bold, sans throughout
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 9,
    "axes.linewidth": 0.5,
    "axes.edgecolor": "0.5",
    "axes.titlesize": 10,
    "axes.titleweight": "normal",
    "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "xtick.major.width": 0.5, "ytick.major.width": 0.5,
    "xtick.color": "0.35", "ytick.color": "0.35",
    "figure.facecolor": "white",
})


def panel(ax, piv, vmax):
    """One cohort(x) x age(y) mesh. Missing cells are left white -- the estimation
    sample's own outline, not a value to be read."""
    Z = np.ma.masked_invalid(piv.to_numpy(dtype=float))
    cmap = matplotlib.colormaps["viridis"].copy()
    cmap.set_bad("white")
    mesh = ax.pcolormesh(piv.columns.to_numpy(dtype=float),
                         piv.index.to_numpy(dtype=float),
                         Z, cmap=cmap, shading="nearest", vmin=0.0, vmax=vmax)
    ax.set_xlabel("Birth cohort")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    return mesh


def main(params=PARAMS):
    df = pd.read_csv(params)
    df["cohort"] = df["year"] - df["age"]
    df["share"] = df["n_high"] / df["n"]

    pivs = {s: df[df["sex"] == s].pivot(index="age", columns="cohort", values="share")
            for s in (1, 2)}
    # one scale across both panels: men vs women censoring is the comparison to preserve
    vmax = float(df["share"].max())

    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.0), sharex=True, sharey=True)
    for ax, sex in zip(axes, (1, 2)):
        mesh = panel(ax, pivs[sex], vmax)
        ax.set_title(SEXLABEL[sex])
    axes[0].set_ylabel("Age")

    cb = fig.colorbar(mesh, ax=axes, fraction=0.030, pad=0.02,
                      ticks=np.arange(0, vmax + 1e-9, 0.2))
    cb.set_label("Share censored at the taxable maximum")
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=2.5, width=0.5, color="0.35")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    pdf = OUTDIR / "censored_share_cohort_age.pdf"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(OUTDIR / "censored_share_cohort_age.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {pdf} and .png   (max share {vmax:.3f}, {len(df)} cells)")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else PARAMS)
