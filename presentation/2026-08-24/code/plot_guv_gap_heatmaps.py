#!/usr/bin/env python
"""Cohort x age heatmaps of the GAP between the fitted distributions and GKOS (2022).

plot_guv_comparison.py collapses the same comparison to line plots -- averaged over
ages, or over cohorts -- which shows the level of the disagreement but hides where in
the (cohort, age) plane it sits. This script keeps every cell: the same functionals,
the same sel0 screen, the same PCE deflator, plotted on the birth-cohort (x) by age (y)
grid used by the rest of the cross-section figures, so a calendar year is an
anti-diagonal and one cohort's life-cycle path reads straight up a column.

Data side: the GKSW/GKOS cohort x age files in raw_data/guv_quantiles (sel0; see
plot_guv_comparison.py for the full provenance and the conventions those files fix).
Their `cohort` is the year the person turns 25 -- converted here to BIRTH year, so these
figures line up with the repo's other cohort x age heatmaps rather than with the GKSW
line figures.

Model side: cell_functionals() from plot_guv_comparison -- log-moments by quadrature on
the fitted log-density, quantiles by root-finding on the CDF, conditional on
X >= Ymin(t) = 260 x nominal minwage (the sel0 screen), deflated to real 2013 dollars.

Gap: model minus data, POSITIVE = model above data throughout. The colormap is diverging
and centered on zero -- a signed gap read on a sequential scale hides the sign, which is
the one thing this figure exists to show. One figure per functional, men and women side
by side on ONE shared symmetric color scale (limits at the 98th percentile of |gap|,
robust to a few runaway cells), so the two sexes are directly comparable within a figure.

TWO UNIT SYSTEMS, both written by default (--units picks one). They answer different
questions and neither dominates:

  absolute   -- each functional's own units: real 2013 dollars for the quantiles, log
                units for meanlog and sdlog, dimensionless for skewness and kurtosis.
                Says how many dollars the fit is off by. But real earnings rise across
                the window, so a constant PROPORTIONAL error grows in dollars and the
                color limits end up set by the later, richer cells -- early cohorts look
                quiet even where the relative miss is large.
  logpoints  -- 100 x (log model - log data) for the LEVEL functionals, which puts every
                year on the same footing and makes the early cohorts readable. Covers
                meanlog and the six quantiles only (see LOGPT): sd/skewness/kurtosis of
                logs are already scale-free, so their absolute figure IS their
                relative figure and no _logpoints duplicate is written for them.

Read either one alongside the other: a cell can be a large dollar miss and a small
relative one, or the reverse, and the pair is what separates the two.

Read the level gaps with the concept wedge in mind: GKSW measure W-2 wage and salary
income of commerce-and-industry workers, EPUF measures covered earnings of all covered
workers, so the dollar/meanlog panels carry a systematic offset (largest in the early
decades, shrinking as coverage expands) that is NOT model misfit. The shape functionals
-- sdlog, skewlog, kurtlog -- and the CURVATURE of the quantile gaps across the plane
are the parts that speak to fit.

Cells right of the dashed line use post-2006 EXTRAPOLATED parameters (stage 2), not
fitted ones.

This script and its figures live next to the report they belong to rather than under
code/ + output/, so presentation/2026-08-24/ is self-contained. It is still run FROM THE
PROJECT ROOT: it reads the shared parameter surface and imports plot_guv_comparison.

  python presentation/2026-08-24/code/plot_guv_gap_heatmaps.py
        [--params CSV] [--tag T] [--reuse] [--units absolute|logpoints|both]
    -> presentation/2026-08-24/figures/guv_gap_<functional>[_logpoints][_T].pdf (+ .png),
       one per functional in meanlog, sdlog, skewlog, kurtlog, p10, p25, p50, p75,
       p90, p98
    -> output/cross_sections/guv_gap_cells[_T].csv   (per-cell model and data values --
       a regenerable cache, not report content, so it stays under output/)

--reuse skips the quadrature/root-finding and replots from that CSV.
"""
import argparse
import sys
from pathlib import Path

sys.path[:0] = ["code/cross_sections", "code/cross_sections/plots"]   # run from project root
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# The GKSW targets, the stable Normal-Laplace pdf/cdf, and the model-side functionals all
# live in cross_sections/guv_targets.py, so nothing has to import a plot module for them.
from guv_targets import (BASE_YEAR, FUNCTIONALS, QCOLS, cell_functionals,
                         _check_stable_vs_original, load_deflator, load_guv, min_wage)

PARAMS   = Path("output/cross_sections/cross_section_params_extrapolated.csv")
OUT_DIR  = Path("output/cross_sections")            # the per-cell CSV: regenerable cache
PLOT_DIR = Path("presentation/2026-08-24/figures")       # the figures: content of the report
LAST_FIT_YEAR = 2006            # beyond this the parameters are extrapolated, not fitted
SUFFIX = {"absolute": "", "logpoints": "_logpoints"}

LABEL = {"meanlog": "mean log earnings", "sdlog": "sd log earnings",
         "skewlog": "skewness of log earnings", "kurtlog": "kurtosis of log earnings",
         **{q: f"{q} of earnings" for q in QCOLS}}
# the gap's units: dollar quantiles in real dollars, the rest in the moment's own units
UNIT = {**{q: f"real {BASE_YEAR} dollars" for q in QCOLS},
        "meanlog": "log units", "sdlog": "log units",
        "skewlog": "", "kurtlog": ""}
# The log-point version covers only the LEVEL functionals -- mean log earnings and the
# dollar quantiles. sd/skewness/kurtosis of logs are already scale-free, so there is
# nothing to convert: their absolute figure IS their relative figure. (Skewness also
# changes sign in these data, which rules out a ratio outright.)
LOGPT = ["meanlog"] + QCOLS
SEXNAME = {1: "men", 2: "women"}

# minimal theme, matching plot_censored_share.py
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


# ---------------------------------------------------------------- per-cell gaps
def build_cells(params):
    """One row per (year, sex, age) guv cell: data value, model value, gap."""
    _check_stable_vs_original()
    guv = load_guv()
    par = pd.read_csv(params).set_index(["year", "sex", "age"])
    defl = load_deflator()

    cells = guv[["year", "sex", "age"]].drop_duplicates()
    rows, missing = [], 0
    for i, (_, c) in enumerate(cells.iterrows()):
        key = (c["year"], c["sex"], c["age"])
        if key not in par.index:
            missing += 1
            continue
        prow = par.loc[key].copy()
        prow["sex"] = c["sex"]
        fac = defl[c["year"]]
        f = cell_functionals(prow, x_min=260.0 * min_wage(c["year"]))
        rec = {"year": c["year"], "sex": c["sex"], "age": c["age"],
               "meanlog_mod": f["meanlog"] + np.log(fac), "sdlog_mod": f["sdlog"],
               "skewlog_mod": f["skewlog"], "kurtlog_mod": f["kurtlog"]}
        rec.update({f"{q}_mod": f[q] * fac for q in QCOLS})
        rows.append(rec)
        if (i + 1) % 500 == 0:
            print(f"  ... {i + 1}/{len(cells)} cells")
    if missing:
        print(f"WARNING: {missing} guv cells had no parameters and were dropped")

    d = guv.rename(columns={c: f"{c}_dat" for c in FUNCTIONALS}).merge(
        pd.DataFrame(rows), on=["year", "sex", "age"], how="inner")
    d["yob"] = d["year"] - d["age"]                 # BIRTH cohort, repo convention
    return d


def add_gaps(d, units):
    """Gap, model minus data, under one unit system. Derived here and not stored in the
    cells CSV, so --reuse can never replot a stale gap definition against a changed one.

    "absolute"   -- each functional's own units (real dollars, log units, dimensionless).
    "logpoints"  -- 100 x (log model - log data) for the level functionals, which puts
                    every year on the same footing; the shape moments are already
                    scale-free and pass through unchanged (see LOGPT)."""
    for c in FUNCTIONALS:
        mod, dat = d[f"{c}_mod"], d[f"{c}_dat"]
        if units == "absolute" or c not in LOGPT:
            d[f"{c}_gap"] = mod - dat
        elif c == "meanlog":            # already a log: differencing gives log points
            d[f"{c}_gap"] = 100.0 * (mod - dat)
        else:                           # dollar quantiles: log ratio
            d[f"{c}_gap"] = 100.0 * (np.log(mod) - np.log(dat))
    return d


# ---------------------------------------------------------------- drawing
def _panel(ax, piv, vmax, xlim, ylim):
    """One cohort(x) x age(y) mesh of a signed gap, diverging and centered on zero."""
    cmap = matplotlib.colormaps["RdBu_r"].copy()
    cmap.set_bad("white")
    mesh = ax.pcolormesh(piv.columns.to_numpy(dtype=float),
                         piv.index.to_numpy(dtype=float),
                         np.ma.masked_invalid(piv.to_numpy(dtype=float)),
                         cmap=cmap, shading="nearest", vmin=-vmax, vmax=vmax)
    # everything right of this anti-diagonal is year > LAST_FIT_YEAR: extrapolated params
    xs = np.array(xlim, dtype=float)
    ax.plot(xs, LAST_FIT_YEAR - xs, color="0.25", lw=0.6, ls=(0, (3, 2)))
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    return mesh


def _lims(d, cols):
    """Symmetric color limit, robust to a handful of runaway cells."""
    v = np.abs(pd.concat([d[f"{c}_gap"] for c in cols]).to_numpy(dtype=float))
    v = v[np.isfinite(v)]
    return float(np.percentile(v, 98)) if v.size else 1.0


def _grid(d, cols):
    """Pivots keyed by (sex, functional), on one shared cohort x age frame."""
    xlim = (d["yob"].min() - 0.5, d["yob"].max() + 0.5)
    ylim = (d["age"].min() - 0.5, d["age"].max() + 0.5)
    pivs = {(sex, c): g.pivot(index="age", columns="yob", values=f"{c}_gap")
            for sex, g in d.groupby("sex") for c in cols}
    return pivs, xlim, ylim


def plot_functional(d, c, units, tag):
    """One figure per functional: men | women, one shared symmetric color scale so the
    two sexes are directly comparable (the panels are otherwise unreadable against each
    other -- that comparison is the point of putting them side by side)."""
    pivs, xlim, ylim = _grid(d, [c])
    vmax = _lims(d, [c])
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.0), sharex=True, sharey=True)
    for ax, sex in zip(axes, (1, 2)):
        mesh = _panel(ax, pivs[(sex, c)], vmax, xlim, ylim)
        ax.set_title(SEXNAME[sex].capitalize())
        ax.set_xlabel("Birth cohort")
    axes[0].set_ylabel("Age")

    u = "log points" if (units == "logpoints" and c in LOGPT) else UNIT[c]
    cb = fig.colorbar(mesh, ax=axes, fraction=0.030, pad=0.02)
    cb.set_label(f"{LABEL[c]}: model \u2212 data" + (f", {u}" if u else ""))
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=2.5, width=0.5, color="0.35")
    _save(fig, f"guv_gap_{c}{SUFFIX[units]}{tag}")


def _save(fig, stem):
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOT_DIR / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(PLOT_DIR / f"{stem}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {PLOT_DIR}/{stem}.pdf (+ .png)")


def main(params=PARAMS, tag="", reuse=False, unit_systems=("absolute", "logpoints")):
    cells_csv = OUT_DIR / f"guv_gap_cells{tag}.csv"
    if reuse:
        d = pd.read_csv(cells_csv)
        print(f"reusing {cells_csv} ({len(d)} cells)")
    else:
        d = build_cells(params)
        d.to_csv(cells_csv, index=False)
        print(f"wrote {cells_csv} ({len(d)} cells)")

    print(f"{len(d)} cells, cohorts {int(d['yob'].min())}-{int(d['yob'].max())}, "
          "ages 25-55")
    for units in unit_systems:
        add_gaps(d, units)
        print(f"median signed gap (model - data), {units}:")
        for c in FUNCTIONALS:
            if units == "logpoints" and c not in LOGPT:
                continue                  # scale-free already: would duplicate the
            med = d.groupby("sex")[f"{c}_gap"].median()   # absolute figure byte for byte
            u = "log points" if units == "logpoints" else UNIT[c]
            print(f"    {c:9s} men {med[1]:+10.3f}   women {med[2]:+10.3f}   {u}")
            plot_functional(d, c, units, tag)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--params", type=Path, default=PARAMS)
    p.add_argument("--tag", default="")
    p.add_argument("--reuse", action="store_true",
                   help="replot from an existing guv_gap_cells CSV instead of refitting")
    p.add_argument("--units", choices=("absolute", "logpoints", "both"), default="both")
    a = p.parse_args()
    systems = ("absolute", "logpoints") if a.units == "both" else (a.units,)
    main(a.params, ("_" + a.tag.lstrip("_")) if a.tag else "", a.reuse, systems)
