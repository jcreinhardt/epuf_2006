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

Gap definition, chosen so a single color scale means one thing:
  meanlog, p10-p98  ->  100 x (log model - log data), i.e. LOG POINTS, since dollar
                        quantiles span an order of magnitude across the sample and a
                        raw dollar gap would just re-plot the price level;
  sdlog/skew/kurt   ->  model - data in native units (already scale-free).
Sign convention throughout: POSITIVE = model above data. The colormap is diverging and
centered on zero -- a signed gap read on a sequential scale hides the sign, which is
the one thing this figure exists to show.

Read the level gaps with the concept wedge in mind: GKSW measure W-2 wage and salary
income of commerce-and-industry workers, EPUF measures covered earnings of all covered
workers, so the dollar/meanlog panels carry a systematic offset (largest in the early
decades, shrinking as coverage expands) that is NOT model misfit. The shape functionals
-- sdlog, skewlog, kurtlog -- and the CURVATURE of the quantile gaps across the plane
are the parts that speak to fit.

Cells right of the dashed line use post-2006 EXTRAPOLATED parameters (stage 2), not
fitted ones.

  python code/cross_sections/plot_guv_gap_heatmaps.py [--params CSV] [--tag T] [--reuse]
    -> output/cross_sections/plots/guv_gap_moments_{men,women}[_T].pdf   (+ .png)
    -> output/cross_sections/plots/guv_gap_quantiles_{men,women}[_T].pdf (+ .png)
    -> output/cross_sections/guv_gap_cells[_T].csv    (per-cell model, data and gap)

--reuse skips the ~1 min of quadrature/root-finding and replots from that CSV.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from plot_guv_comparison import (BASE_YEAR, FUNCTIONALS, MCOLS, QCOLS,
                                 _check_stable_vs_original, cell_functionals,
                                 load_deflator, load_guv, min_wage)

PARAMS   = Path("output/cross_sections/cross_section_params_extrapolated.csv")
OUT_DIR  = Path("output/cross_sections")
PLOT_DIR = Path("output/cross_sections/plots")
LAST_FIT_YEAR = 2006            # beyond this the parameters are extrapolated, not fitted

# log-point functionals: gap = 100 * (log model - log data). meanlog is already a log,
# so it joins the dollar quantiles rather than the shape moments.
LOGPT = ["meanlog"] + QCOLS
LABEL = {"meanlog": "mean log earnings", "sdlog": "sd log earnings",
         "skewlog": "skewness of log earnings", "kurtlog": "kurtosis of log earnings",
         **{q: f"{q} of earnings" for q in QCOLS}}
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
    for c in FUNCTIONALS:
        mod, dat = d[f"{c}_mod"], d[f"{c}_dat"]
        if c == "meanlog":                          # already a log: differencing is enough
            d[f"{c}_gap"] = 100.0 * (mod - dat)
        elif c in LOGPT:                            # dollar quantiles: log ratio
            d[f"{c}_gap"] = 100.0 * (np.log(mod) - np.log(dat))
        else:
            d[f"{c}_gap"] = mod - dat
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
    xlim = (d["yob"].min() - 0.5, d["yob"].max() + 0.5)
    ylim = (d["age"].min() - 0.5, d["age"].max() + 0.5)
    return {c: d.pivot(index="age", columns="yob", values=f"{c}_gap") for c in cols}, xlim, ylim


def plot_moments(d, sex, tag):
    """Four shape/level moments; each has its own units, so each gets its own scale."""
    sub = d[d["sex"] == sex]
    pivs, xlim, ylim = _grid(sub, MCOLS)
    fig, axes = plt.subplots(1, 4, figsize=(15.5, 3.9), sharey=True)
    for ax, c in zip(axes, MCOLS):
        vmax = _lims(sub, [c])
        mesh = _panel(ax, pivs[c], vmax, xlim, ylim)
        unit = "log points" if c in LOGPT else "model \u2212 data"
        ax.set_title(f"{LABEL[c]}\n({unit})")     # unit in the title: a colorbar label
        ax.set_xlabel("Birth cohort")             # here reads as the next panel's y-label
        cb = fig.colorbar(mesh, ax=ax, fraction=0.046, pad=0.03)
        cb.outline.set_visible(False)
        cb.ax.tick_params(length=2.5, width=0.5, color="0.35", labelsize=8)
    axes[0].set_ylabel("Age")
    _save(fig, f"guv_gap_moments_{SEXNAME[sex]}{tag}")


def plot_quantiles(d, sex, tag):
    """Six quantiles on ONE shared scale -- whether the model misses more in the tails
    than in the middle is the comparison this figure has to preserve."""
    sub = d[d["sex"] == sex]
    pivs, xlim, ylim = _grid(sub, QCOLS)
    vmax = _lims(sub, QCOLS)
    fig, axes = plt.subplots(2, 3, figsize=(12.5, 6.6), sharex=True, sharey=True)
    for ax, c in zip(axes.flat, QCOLS):
        mesh = _panel(ax, pivs[c], vmax, xlim, ylim)
        ax.set_title(LABEL[c])
    for ax in axes[1]:
        ax.set_xlabel("Birth cohort")
    for ax in axes[:, 0]:
        ax.set_ylabel("Age")
    cb = fig.colorbar(mesh, ax=axes, fraction=0.030, pad=0.02)
    cb.set_label(f"model \u2212 data, log points (real {BASE_YEAR} dollars)")
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=2.5, width=0.5, color="0.35")
    _save(fig, f"guv_gap_quantiles_{SEXNAME[sex]}{tag}")


def _save(fig, stem):
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOT_DIR / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(PLOT_DIR / f"{stem}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {PLOT_DIR}/{stem}.pdf (+ .png)")


def main(params=PARAMS, tag="", reuse=False):
    cells_csv = OUT_DIR / f"guv_gap_cells{tag}.csv"
    if reuse:
        d = pd.read_csv(cells_csv)
        print(f"reusing {cells_csv} ({len(d)} cells)")
    else:
        d = build_cells(params)
        d.to_csv(cells_csv, index=False)
        print(f"wrote {cells_csv} ({len(d)} cells)")

    for sex in (1, 2):
        sub = d[d["sex"] == sex]
        print(f"{SEXNAME[sex]}: {len(sub)} cells, cohorts "
              f"{int(sub['yob'].min())}-{int(sub['yob'].max())}, median signed gap")
        for c in FUNCTIONALS:
            unit = "lp" if c in LOGPT else ""
            print(f"    {c:9s} {sub[f'{c}_gap'].median():+8.3f}{unit}"
                  f"   (mean abs {sub[f'{c}_gap'].abs().mean():.3f})")
        plot_moments(d, sex, tag)
        plot_quantiles(d, sex, tag)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--params", type=Path, default=PARAMS)
    p.add_argument("--tag", default="")
    p.add_argument("--reuse", action="store_true",
                   help="replot from an existing guv_gap_cells CSV instead of refitting")
    a = p.parse_args()
    main(a.params, ("_" + a.tag.lstrip("_")) if a.tag else "", a.reuse)
