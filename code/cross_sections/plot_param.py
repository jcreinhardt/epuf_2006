#!/usr/bin/env python
"""Cohort x age heatmaps of every fitted cross-section parameter.

Reads the per-(year, sex, age) fits from cross_section_params.csv and lays each
parameter out on a birth-cohort (x) by age (y) grid -- so a fixed calendar year
is an anti-diagonal, and a single cohort's life-cycle path reads straight up a
column. Smoothly identified parameters (the location/scale of the bulk) show up
as clean gradients; weakly identified ones (the men's censored upper-tail index
alpha, the women's near-empty second mixture component) show up as speckle --
which is the whole point of looking.

Two figures, one per sex, panels ordered well-identified first:
  men   (dPlN)    : nu, tau, alpha, beta, + n, p_high_model
  women (mixture) : mu1, sig1, mu2, sig2, w, + n

Color limits are robust (2nd-98th percentile) so a few runaway cells -- e.g. the
women's phantom component fleeing to mu2 ~ -300 -- don't flatten the scale and
hide the structure everywhere else. Cells below the fit's MIN_N are absent from
the CSV and render blank.

  python code/cross_sections/plot_param.py [men|women|both]
    -> output/cross_sections/param_heatmaps_{men,women}.pdf (+ .png)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PARAMS = Path("output/cross_sections/cross_section_params.csv")
OUTDIR = Path("output/cross_sections")

# per-sex panel plan: (column, human label, colormap, log-color?). Well-identified
# location/scale first, the wandering nuisance params next, diagnostics last.
PANELS = {
    1: [("nu",    "nu  (dPlN log-location)",      "viridis", False),
        ("tau",   "tau  (dPlN log-scale)",        "viridis", False),
        ("alpha", "alpha  (upper-tail index)",    "magma",   True),
        ("beta",  "beta  (lower-tail index)",     "magma",   False),
        ("n",     "n  (cell size)",               "cividis", True),
        ("p_high_model", "P(at cap)  (censored share)", "inferno", False)],
    2: [("mu1",   "mu1  (upper comp log-mean)",   "viridis", False),
        ("sig1",  "sig1  (upper comp log-sd)",    "viridis", False),
        ("mu2",   "mu2  (lower comp log-mean)",   "coolwarm", False),
        ("sig2",  "sig2  (lower comp log-sd)",    "magma",   False),
        ("w",     "w  (weight on upper comp)",    "coolwarm", False),
        ("n",     "n  (cell size)",               "cividis", True)],
}
SEXLABEL  = {1: "men (double Pareto-lognormal)", 2: "women (two-component lognormal mixture)"}
FILETAG   = {1: "men", 2: "women"}


def heatmap(ax, piv, cmap, logcolor):
    """Draw one cohort(x) x age(y) heatmap; robust 2-98 pct color limits."""
    cohorts = piv.columns.to_numpy(dtype=float)
    ages    = piv.index.to_numpy(dtype=float)
    Z = np.ma.masked_invalid(piv.to_numpy(dtype=float))

    finite = Z.compressed()
    if logcolor and finite.size and np.nanmin(finite) > 0:
        norm = matplotlib.colors.LogNorm(vmin=np.nanpercentile(finite, 2),
                                         vmax=np.nanpercentile(finite, 98))
        kw = dict(norm=norm)
    else:
        vmin, vmax = (np.nanpercentile(finite, 2), np.nanpercentile(finite, 98)) \
            if finite.size else (None, None)
        kw = dict(vmin=vmin, vmax=vmax)

    cm = matplotlib.colormaps[cmap].copy()
    cm.set_bad("0.92")                                  # missing/small cells -> light grey
    mesh = ax.pcolormesh(cohorts, ages, Z, cmap=cm, shading="nearest", **kw)
    ax.figure.colorbar(mesh, ax=ax, fraction=0.046, pad=0.03)


def plot_sex(df, sex, suffix=""):
    sub = df[df["sex"] == sex].copy()
    sub["cohort"] = sub["year"] - sub["age"]

    fig, axes = plt.subplots(2, 3, figsize=(16, 8.5))
    for ax, (col, label, cmap, logc) in zip(axes.ravel(), PANELS[sex]):
        piv = sub.pivot(index="age", columns="cohort", values=col)
        heatmap(ax, piv, cmap, logc)
        ax.set_title(label, fontsize=10)
        ax.set_xlabel("birth cohort (yob)", fontsize=8)
        ax.set_ylabel("age", fontsize=8)
        ax.tick_params(labelsize=7)

    kind = "smoothed" if suffix else "fitted"
    fig.suptitle(f"{kind.capitalize()} cross-section parameters by cohort x age -- {SEXLABEL[sex]}\n"
                 "clean gradient = well identified;  speckle = weakly identified "
                 "(color limits clipped to 2-98 pct)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    pdf = OUTDIR / f"param_heatmaps_{FILETAG[sex]}{suffix}.pdf"
    fig.savefig(pdf)
    fig.savefig(OUTDIR / f"param_heatmaps_{FILETAG[sex]}{suffix}.png", dpi=150)
    plt.close(fig)
    print(f"wrote {pdf} and .png")
    return pdf


def main(which="both", params=PARAMS, suffix=""):
    df = pd.read_csv(params)
    sexes = {"men": [1], "women": [2], "both": [1, 2]}[which]
    for sex in sexes:
        plot_sex(df, sex, suffix)


if __name__ == "__main__":
    which = sys.argv[1].lower() if len(sys.argv) > 1 else "both"
    if which not in ("men", "women", "both"):
        sys.exit(f"argument must be men|women|both, got {which!r}")
    params = sys.argv[2] if len(sys.argv) > 2 else PARAMS
    suffix = sys.argv[3] if len(sys.argv) > 3 else ("" if params == PARAMS else "_smoothed")
    main(which, params, suffix)
