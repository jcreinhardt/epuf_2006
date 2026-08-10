#!/usr/bin/env python
"""In-sample check of the aggregate-mean constraint: the model's implied UNCAPPED mean
earnings per covered worker vs the published ASS average, 1951-2006, for BOTH the
unconstrained per-cell MLE and the joint smoothed-constrained solve.

This is the exact quantity stage 3 of estimate_cross_sections.py drives with eta -- same
cells (the fitted cells, ages 15-77), same weights (each cell's share of the year's positive
earners, from the `n` column), same analytic uncapped cell means (dpln_mean / mix_mean):

    S(y) = SUM_cells  n_c / SUM n  x  E[X_c]        vs      aggearn_tot(y) / num_wrk(y)

so it reads the constraint directly rather than re-deriving it through the extrapolated
parameters and TR worker counts (that end-to-end view is the bottom row of
agg_tax_total_visualization.py, which also covers the off-sample years).

Two fits are compared against the same benchmark:

  * UNCONSTRAINED -- cross_section_params.csv, the stage-0 multi-start MLE each cell reaches
    on its own data alone: no roughness penalty, no mean constraint (eta = 0 throughout).
    This is what the constraint is worth. It is written by the same run of
    estimate_cross_sections.py that writes the smoothed fits, so the two are the same data,
    the same cells and the same starts -- refitting it separately would only reproduce it.
  * CONSTRAINED -- cross_section_params_smoothed.csv, the joint solve.

The unconstrained line is NOT simply "the same thing, noisier". Under a tight taxable maximum
the dPlN upper tail is unidentified above the cap and the MLE parks alpha at or below 1, where
E[X] is INFINITE: 374 of 3326 men's cells, up to ~8% of a year's workers in the early 1950s.
Those cells are dropped and the remaining weights renormalized, so wherever the shaded share
is positive the unconstrained line is a LOWER BOUND on a mean that is really infinite -- and
it still overshoots the benchmark roughly twofold. That is the failure the aggregate constraint
exists to fix, not a cosmetic difference.

eta >= 0 is thinning only, so the constraint is one-sided by construction: a year whose model
mean already sits BELOW the benchmark is left alone (eta = 0) and lands under 1.0. Those years
are marked.

  python code/cross_sections/plot_uncapped_mean_vs_ass.py
    -> output/cross_sections/uncapped_mean_vs_ass.pdf (+ .png)
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

RAW      = Path("output/cross_sections/cross_section_params.csv")           # stage-0 MLE
SMOOTHED = Path("output/cross_sections/cross_section_params_smoothed.csv")  # joint solve
ASS_XLSX = Path("raw_data/annual_statistical_supplement.xlsx")
OUT      = Path("output/cross_sections/uncapped_mean_vs_ass")
MATCH_AGES = (15, 77)       # must match estimate_cross_sections.MATCH_AGES


def ass_uncapped_target():
    """ASS average uncapped earnings per covered worker ($/worker), wage + self-employed."""
    d = pd.read_excel(ASS_XLSX, sheet_name="data")
    tot = d["aggearn_tot_wage"].fillna(0) + d["aggearn_tot_se"].fillna(0)      # $M
    return {int(y): float(t) * 1e6 / (float(nw) * 1e3)
            for y, t, nw in zip(d["year"], tot, d["num_wrk"])
            if t > 0 and pd.notna(nw) and nw > 0}


def cell_mean(r):
    """Analytic uncapped E[X] for one cell; np.inf for a men's cell fit with alpha <= 1."""
    if int(r["sex"]) == 1:
        return cf.dpln_mean(r["alpha"], r["beta"], r["nu"], r["tau"])
    return cf.mix_mean(r["mu1"], r["mu2"], r["sig1"], r["sig2"], r["w"])


def year_means(params):
    """Per-year (weighted uncapped mean, infinite-mean worker share, eta) over the constraint
    window. The mean renormalizes over the finite cells, so it is a lower bound wherever the
    infinite share is positive."""
    d = pd.read_csv(params)
    lo, hi = MATCH_AGES
    d = d[(d["age"] >= lo) & (d["age"] <= hi)].copy()
    d["mean"] = [cell_mean(r) for r in d.to_dict("records")]
    out = {}
    for y, g in d.groupby("year"):
        w = g["n"] / g["n"].sum()
        fin = np.isfinite(g["mean"])
        out[int(y)] = (float((w[fin] * g["mean"][fin]).sum() / w[fin].sum()),
                       float(w[~fin].sum()),
                       float(g["eta_year"].iloc[0]))
    return out


def main():
    ass = ass_uncapped_target()
    con = year_means(SMOOTHED)
    unc = year_means(RAW)
    years = sorted(set(con) & set(unc) & set(ass))
    yr = np.array(years)
    a  = np.array([ass[y] for y in years])
    mc = np.array([con[y][0] for y in years])
    mu = np.array([unc[y][0] for y in years])
    inf_sh = np.array([unc[y][1] for y in years])
    eta = np.array([con[y][2] for y in years])
    rc, ru = mc / a, mu / a
    free = eta <= 0                       # constraint inactive: model already under benchmark

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.8))

    ax1.plot(yr, a, color="k", lw=2.2, label="ASS: aggearn_tot / num_wrk")
    ax1.plot(yr, mu, color="C1", lw=1.6, ls="-.",
             label="unconstrained per-cell MLE (finite α>1 cells)")
    ax1.plot(yr, mc, color="C3", lw=1.8, ls=":", label="smoothed + mean-constrained")
    ax1.set_yscale("log")
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax1.set_xlabel("year"); ax1.set_ylabel("mean earnings per worker ($)")
    ax1.set_title("Uncapped mean earnings per worker")
    ax1.legend(frameon=False, fontsize=8.5, loc="upper left")

    ax2.axhline(1.0, color="k", lw=1.0)
    ax2.plot(yr, ru, color="C1", lw=1.6, ls="-.", label="unconstrained MLE / ASS")
    ax2.plot(yr, rc, color="C3", lw=1.8, label="constrained / ASS")
    ax2.plot(yr[free], rc[free], "o", ms=4.5, color="C0",
             label="η = 0 (constraint slack: model already below)")
    ax2.set_yscale("log")
    ax2.minorticks_off()        # else the log locator adds its own unlabelled decade ticks
    ax2.set_yticks([0.9, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 3.5])
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax2.set_ylim(0.85, max(2.6, ru.max() * 1.1))
    ax2.set_xlabel("year"); ax2.set_ylabel("model / ASS  (log scale)")
    ax2.set_title("Ratio to benchmark (1.0 = exact match)")

    # the unconstrained line drops the alpha<=1 cells, so it is a lower bound on an infinite
    # mean wherever this share is positive -- plot it so the reader can see where.
    ax2b = ax2.twinx()
    ax2b.fill_between(yr, inf_sh * 100, 0, color="grey", alpha=0.18, lw=0)
    ax2b.set_ylim(0, max(25.0, inf_sh.max() * 100 * 3))
    ax2b.set_ylabel("% of workers in infinite-mean (α≤1) cells", fontsize=8.5, color="0.4")
    ax2b.tick_params(labelsize=8, colors="0.4")
    h1, l1 = ax2.get_legend_handles_labels()
    ax2.legend(h1 + [plt.Rectangle((0, 0), 1, 1, fc="grey", alpha=0.18)],
               l1 + ["% workers in α≤1 cells (right axis)"],
               frameon=False, fontsize=8.5, loc="upper right")

    fig.suptitle("In-sample uncapped mean vs ASS: unconstrained MLE vs the "
                 f"constrained solve, {years[0]}–{years[-1]}", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(str(OUT) + ".pdf"); fig.savefig(str(OUT) + ".png", dpi=150)
    plt.close(fig)

    print(f"{'year':>4} {'ASS $/wk':>10} | {'unconstr':>10} {'ratio':>7} {'inf%':>6} | "
          f"{'constr':>10} {'ratio':>7} {'eta':>8}")
    for i, y in enumerate(years):
        print(f"{y:>4} {a[i]:>10,.0f} | {mu[i]:>10,.0f} {ru[i]:>7.3f} {inf_sh[i]*100:>5.1f}% | "
              f"{mc[i]:>10,.0f} {rc[i]:>7.4f} {eta[i]:>8.4f}")
    print(f"\nunconstrained: mean ratio {ru.mean():.3f} [{ru.min():.3f}–{ru.max():.3f}]; "
          f"infinite-mean cells in {(inf_sh > 0).sum()}/{len(years)} years "
          f"(max {inf_sh.max()*100:.1f}% of workers)")
    print(f"constrained:   mean ratio {rc.mean():.4f} [{rc.min():.4f}–{rc.max():.4f}]; "
          f"within 0.1% in {(np.abs(rc-1) < 1e-3).sum()}/{len(years)} years; "
          f"eta=0 in {int(free.sum())}")
    print(f"wrote {OUT}.pdf and .png")


if __name__ == "__main__":
    main()
