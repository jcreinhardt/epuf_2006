#!/usr/bin/env python
"""Overlay two years' fitted dPlN densities on their (near-identical) male
earnings histograms, for a few ages -- the 1956-vs-1957 diagnostic.

1956 and 1957 have almost the same male cross-section (same $4,200 cap, ~57%
censored), yet the pipeline fits land in different basins of the weakly-
identified upper tail: 1956 at alpha~29, 1957 at alpha~0.67, for every age
(the warm start carries the first age's basin across the whole year). This
script shows what that does to the fitted density near the cap, and prints each
fit's implied mean taxable E[min(w, taxmax)] against the empirical mean -- the
quantity whose year total was off.

Uses the STORED params from cross_section_params.csv (the fits that produced the
aggregate), not a fresh refit. Histograms are density over all log-earnings, so
the tall bar at the cap is the censored spike; the y-limit focuses on the body.

  python code/cross_sections/compare_year_fits.py [yearA yearB] [ages...]
    defaults: 1956 1957, ages 30 40 50 (men only -- the dPlN is the male model).
    -> output/cross_sections/compare_men_<yearA>_<yearB>.pdf (+ .png)
"""
import sys
from pathlib import Path

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

import crosssec_fit as cf
from plot_aggregate_taxable import model_mean_taxable

PARAMS = Path("output/cross_sections/cross_section_params.csv")
SEX = 1                                       # dPlN is the male model
COL = {"a": "C0", "b": "C3"}                  # yearA blue, yearB red


def cell(df, year, age):
    r = df[(df.sex == SEX) & (df.year == year) & (df.age == age)]
    if r.empty:
        sys.exit(f"no fitted male cell for year {year}, age {age} (below MIN_N?)")
    return r.iloc[0]


def dpln_density(yy, row):
    d = np.exp(cf.nl_logpdf(yy, row["alpha"], row["beta"], row["nu"], row["tau"]))
    # the Normal-Laplace pdf overflows to +inf deep in the (negligible) lower tail
    return np.nan_to_num(d, nan=0.0, posinf=0.0, neginf=0.0)


def panel(ax, df, yearA, yearB, age):
    rA, rB = cell(df, yearA, age), cell(df, yearB, age)
    taxmax = float(rA["highc"]) + cf.HIGH_MARGIN          # same cap in both years
    hi = taxmax - cf.HIGH_MARGIN
    xA = cf.load_earnings(yearA, SEX, age=age)
    xB = cf.load_earnings(yearB, SEX, age=age)

    bins = np.linspace(np.log(120), np.log(taxmax * 1.08), 80)
    yy = np.linspace(bins[0], bins[-1], 800)
    dA, dB = dpln_density(yy, rA), dpln_density(yy, rB)

    # near-identical data: thin step outlines to show they overlap
    ax.hist(np.log(xA), bins=bins, density=True, histtype="step",
            color=COL["a"], alpha=0.45, lw=0.8)
    ax.hist(np.log(xB), bins=bins, density=True, histtype="step",
            color=COL["b"], alpha=0.45, lw=0.8)
    ax.plot(yy, dA, color=COL["a"], lw=2.2, label=f"{yearA}  (α={rA['alpha']:.1f})")
    ax.plot(yy, dB, color=COL["b"], lw=2.2, ls="--", label=f"{yearB}  (α={rB['alpha']:.2f})")
    for t in (np.log(cf.LOWC), np.log(hi), np.log(taxmax)):
        ax.axvline(t, color="0.55", lw=0.9, ls=":")

    ax.set_ylim(0, 1.25 * max(dA.max(), dB.max()))
    # implied vs empirical mean taxable -- the aggregate-driving number
    mA = model_mean_taxable(rA, taxmax); mB = model_mean_taxable(rB, taxmax)
    eA = np.minimum(xA, taxmax).mean();  eB = np.minimum(xB, taxmax).mean()
    txt = (f"E[min(w,cap)]:\n"
           f"{yearA}: model ${mA:,.0f} / emp ${eA:,.0f}  ({mA/eA:.1%})\n"
           f"{yearB}: model ${mB:,.0f} / emp ${eB:,.0f}  ({mB/eB:.1%})")
    ax.text(0.03, 0.97, txt, transform=ax.transAxes, va="top", ha="left",
            fontsize=7.5, family="monospace",
            bbox=dict(boxstyle="round", fc="white", ec="0.7", alpha=0.9))

    ax.annotate("cap", xy=(np.log(taxmax), ax.get_ylim()[1] * 0.5),
                fontsize=7, color="0.4", rotation=90, va="center", ha="right")
    ticks = [t for t in (200, 500, 1000, 2000, 4200) if t <= taxmax * 1.05]
    ax.set_xticks(np.log(ticks))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${np.exp(v):,.0f}"))
    ax.set_title(f"men, age {age}", fontsize=10)
    ax.set_xlabel("annual earnings (log scale)", fontsize=8)
    ax.legend(frameon=False, fontsize=8, loc="center left")


def main(yearA, yearB, ages):
    df = pd.read_csv(PARAMS)
    fig, axes = plt.subplots(1, len(ages), figsize=(5.0 * len(ages), 4.8), squeeze=False)
    for ax, age in zip(axes.ravel(), ages):
        panel(ax, df, yearA, yearB, age)
    axes[0, 0].set_ylabel("density (per unit log earnings)", fontsize=8)
    fig.suptitle(f"Men's dPlN fit, {yearA} vs {yearB}: near-identical data, "
                 f"different basin of the weakly-identified upper tail",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = f"output/cross_sections/compare_men_{yearA}_{yearB}.pdf"
    fig.savefig(out)
    fig.savefig(out[:-4] + ".png", dpi=150)
    plt.close(fig)
    print(f"wrote {out} and .png")


if __name__ == "__main__":
    args = sys.argv[1:]
    yearA, yearB = 1956, 1957
    ages = [30, 40, 50]
    nums = [int(a) for a in args]
    if len(nums) >= 2:
        yearA, yearB = nums[0], nums[1]
        if len(nums) > 2:
            ages = nums[2:]
    main(yearA, yearB, ages)
