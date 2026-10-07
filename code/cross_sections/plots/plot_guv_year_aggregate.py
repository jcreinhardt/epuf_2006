#!/usr/bin/env python
"""Per-YEAR cross-sectional quantiles/moments, EPUF (screened to GKOS's own selection)
vs GKOS aggregated across cohorts -- the third data-vs-data comparison alongside
plot_guv_quantile_validation.py (per cell, cohort-tracked) and plot_guv_gap_signature.py
(per cell, decomposed by quantile x age). This one asks a different question: pool the
WHOLE cross-section (ages 25-55) in a single calendar year, on both sides, and compare
the resulting one number per (year, sex, quantile/moment) -- what a reader actually means
by "the 1980 earnings distribution," rather than a cohort- or cell-level slice of it.

EPUF side, per (year, sex): the exact sel0 screen (guv_targets.sel0_threshold), ages
25-55, empirical quantiles/moments of the POOLED cross-section (all ages together, not
averaged cell quantiles) -- real microdata, no assumption needed.

GKOS side has no such pooled statistic published: the sel0 files are one row per
(cohort, age), i.e. per (year, age) once you read cohort = year - age + 25, and carry no
headcount. Building a year-level number means combining ~31 age-cells (one per cohort
passing through that year) that in general are NOT drawn from the same distribution
(that heterogeneity is the entire point of this investigation), weighted by cell size.
Two things are needed that the file doesn't give directly:

  - WEIGHTS. No cell in the sel0 files carries an n. Per the project instruction, this
    falls back to EPUF: each GKOS (cohort, age) cell is weighted by the number of EPUF
    sel0-survivors of that (year, age, sex) -- the same population the GKOS cell is
    notionally drawn from, just under EPUF's broader earnings concept.
  - A YEAR-LEVEL CDF. Cell MOMENTS combine exactly, with no distributional assumption:
    given weights and each cell's own (meanlog, sdlog, skewlog, kurtlog), the pooled
    mean/variance/3rd/4th central moment of a mixture have closed-form combination
    formulas (law of total variance and its 3rd/4th-moment analogues) -- see
    `combine_moments`. Cell QUANTILES do not combine this way (a mixture's p50 is not
    the weighted average of its components' p50s). This script instead builds each
    cell's CDF by monotone (PCHIP) interpolation through its 6 published quantile
    points in log-earnings space, forms the EPUF-weighted mixture CDF across the cells
    contributing to a year, and inverts it numerically for the year-level quantiles.
    This uses the actual published quantiles rather than a parametric stand-in (e.g.
    assuming each cell is lognormal, which GKOS's own nonzero skewlog/kurtlog rule
    out). Evaluating one cell's CDF at a value far from its own published range (needed
    because a DIFFERENT, far-away cell's quantile can require it) relies on the PCHIP
    interpolant's local cubic extrapolation past its outermost knot, clipped to [0,1];
    `combine_moments`'s exact result is the check that this isn't going far wrong --
    see the printed mean/sd comparison in `main`.

  python code/cross_sections/plots/plot_guv_year_aggregate.py
    -> output/cross_sections/guv_year_aggregate.csv
    -> output/cross_sections/plots/guv_year_aggregate.pdf (+ .png)
"""
import subprocess
import sys
from io import StringIO
from pathlib import Path

sys.path[:0] = ["code/cross_sections", "code/cross_sections/plots"]   # run from project root
import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq
from scipy.stats import norm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import xs_model as xm
from guv_targets import load_guv, load_deflator, sel0_threshold, check_guv_conventions, QUANTS, QCOLS

YEARS = (1957, 2006)      # EPUF in-sample years inside the guv window
AGES  = (25, 55)
OUT_DIR  = Path("output/cross_sections")
PLOT_DIR = Path("output/cross_sections/plots")
SHOW = ["p10", "p25", "p50", "p75"]     # the quantiles plotted; p90/p98 kept in the CSV


def _mw_values():
    return ", ".join(f"({y}, {sel0_threshold(y)})" for y in range(YEARS[0], YEARS[1] + 1))


def epuf_cell_counts():
    """EPUF sel0-survivor headcount per (year, sex, age) -- the weights used for the GKOS
    cohort cells below, since the published GKOS files carry no headcount of their own."""
    q = (f"WITH mw(year, thr) AS (VALUES {_mw_values()}) "
         "SELECT a.year, d.sex, a.year - d.yob AS age, COUNT(*) AS n "
         "FROM annual a JOIN demographic d USING(id) JOIN mw ON mw.year = a.year "
         f"WHERE d.sex IN (1, 2) AND a.year - d.yob BETWEEN {AGES[0]} AND {AGES[1]} "
         "AND a.earnings >= mw.thr GROUP BY 1, 2, 3 ORDER BY 1, 2, 3")
    out = subprocess.run(["duckdb", "-readonly", xm.DB, "-csv", "-c", q],
                         capture_output=True, text=True, check=True).stdout
    return pd.read_csv(StringIO(out))


def epuf_year_quantiles():
    """Pooled (ALL ages 25-55 together) empirical quantiles + log-moments of screened
    EPUF earnings, per (year, sex) -- the whole cross-section, not cell-by-cell. Real
    microdata: no interpolation or distributional assumption needed on this side."""
    qcols = ", ".join(f"quantile_disc(a.earnings, {q}) AS {c}" for q, c in zip(QUANTS, QCOLS))
    q = (f"WITH mw(year, thr) AS (VALUES {_mw_values()}), "
         "cap AS (SELECT year, MAX(earnings) AS taxmax FROM annual GROUP BY year) "
         "SELECT a.year, d.sex, COUNT(*) AS n, ANY_VALUE(cap.taxmax) AS taxmax, "
         "AVG(LN(a.earnings)) AS meanlog, STDDEV_SAMP(LN(a.earnings)) AS sdlog, "
         "SKEWNESS(LN(a.earnings)) AS skewlog, KURTOSIS(LN(a.earnings)) + 3 AS kurtlog, "
         f"{qcols} "
         "FROM annual a JOIN demographic d USING(id) JOIN mw ON mw.year = a.year "
         "JOIN cap ON cap.year = a.year "
         f"WHERE d.sex IN (1, 2) AND a.year - d.yob BETWEEN {AGES[0]} AND {AGES[1]} "
         "AND a.earnings >= mw.thr GROUP BY 1, 2 ORDER BY 1, 2")
    out = subprocess.run(["duckdb", "-readonly", xm.DB, "-csv", "-c", q],
                         capture_output=True, text=True, check=True).stdout
    # DuckDB's kurtosis() is EXCESS kurtosis (verified against a synthetic N(0,1) sample,
    # ~0 not ~3); +3 above puts it on guv_targets' raw-kurtosis convention (m4/m2**2).
    return pd.read_csv(StringIO(out))


# ---------------------------------------------------------- exact moment combination
def combine_moments(meanlog, sdlog, skewlog, kurtlog, w):
    """Closed-form pooled (mean, sd, skew, kurt) of log-earnings for a weighted mixture
    of cells, given only each cell's OWN moments about its OWN mean -- no distributional
    assumption. Derivation: write X_k - mu = Z_k + d_k with d_k = mu_k - mu (mu = pooled
    mean) and Z_k = X_k - mu_k; expand E_k[(Z_k+d_k)^r] using E_k[Z_k]=0, E_k[Z_k^2]=
    sdlog_k**2, E_k[Z_k^3]=skewlog_k*sdlog_k**3, E_k[Z_k^4]=kurtlog_k*sdlog_k**4 (kurtlog
    on the RAW, not excess, convention -- matches guv_targets.cell_functionals)."""
    w = np.asarray(w) / np.sum(w)
    mu = np.sum(w * meanlog)
    d = meanlog - mu
    m3k = skewlog * sdlog**3
    m4k = kurtlog * sdlog**4
    m2 = np.sum(w * (sdlog**2 + d**2))
    m3 = np.sum(w * (m3k + 3 * d * sdlog**2 + d**3))
    m4 = np.sum(w * (m4k + 4 * d * m3k + 6 * d**2 * sdlog**2 + d**4))
    return mu, np.sqrt(m2), m3 / m2**1.5, m4 / m2**2


# ------------------------------------------------------------ per-cell CDF (quantiles)
def cell_cdf(row):
    """Monotone (PCHIP) log-value -> quantile-level map through one GKOS cell's 6
    published points on [log(p10), log(p98)] -- the cell's CDF, interior. A far-away
    cell's CDF must still be evaluable many log-points outside ITS OWN published range,
    because pooling 31 ages within one year means a peak-earnings cell and a young- or
    old-age cell can sit several log points apart. PCHIP's native cubic extrapolation is
    NOT safe there: tried first, it went non-monotonic far from the data (p10_gkos came
    out above p25_gkos), because a cubic segment continued indefinitely can turn over.
    So outside the published range this switches to a Normal(meanlog, sdlog) tail,
    RESCALED to match the interior interpolant's value exactly at the p10/p98 anchor
    (continuous), and monotonic by construction (Phi is monotonic; the anchor factor is
    a positive constant) -- tamed far-field behaviour rather than a raw normal
    assumption in the interior, where the published quantiles are used directly."""
    x = np.log([row[c] for c in QCOLS])
    pc = PchipInterpolator(x, QUANTS, extrapolate=False)
    mu, sd = row["meanlog"], row["sdlog"]
    xlo, xhi = x[0], x[-1]
    k_lo = QUANTS[0] / norm.cdf((xlo - mu) / sd)
    k_hi = (1 - QUANTS[-1]) / norm.sf((xhi - mu) / sd)

    def F(y):
        y = np.asarray(y, dtype=float)
        scalar = y.ndim == 0
        y = np.atleast_1d(y)
        out = np.where(y < xlo, k_lo * norm.cdf((y - mu) / sd),
                       np.where(y > xhi, 1 - k_hi * norm.sf((y - mu) / sd), 0.0))
        mid = (y >= xlo) & (y <= xhi)
        out[mid] = pc(y[mid])
        return out[0] if scalar else out
    return F


def mixture_cdf_fn(cells, w):
    w = np.asarray(w) / np.sum(w)
    fns = [cell_cdf(r) for _, r in cells.iterrows()]
    return lambda y: sum(wk * f(y) for wk, f in zip(w, fns))


def mixture_pdf_grid(cells, w, yg):
    """Mixture density on a grid, via each cell's own closed-form density: PCHIP's
    analytic derivative in the interior, the (rescaled) normal tail density outside --
    avoids differentiating the mixture CDF numerically (np.gradient on a function with a
    kink at each cell's p10/p98 anchor is noisy)."""
    w = np.asarray(w) / np.sum(w)
    total = np.zeros_like(yg)
    for wk, (_, row) in zip(w, cells.iterrows()):
        x = np.log([row[c] for c in QCOLS])
        pc = PchipInterpolator(x, QUANTS, extrapolate=False)
        dpc = pc.derivative()
        mu, sd = row["meanlog"], row["sdlog"]
        xlo, xhi = x[0], x[-1]
        k_lo = QUANTS[0] / norm.cdf((xlo - mu) / sd)
        k_hi = (1 - QUANTS[-1]) / norm.sf((xhi - mu) / sd)
        mid = (yg >= xlo) & (yg <= xhi)
        dens = np.where(yg < xlo, k_lo * norm.pdf((yg - mu) / sd) / sd,
                        np.where(yg > xhi, k_hi * norm.pdf((yg - mu) / sd) / sd, 0.0))
        dens[mid] = dpc(yg[mid])
        total += wk * dens
    return total


def mixture_quantile(F, target, lo, hi):
    lo, hi = lo - 1.5, hi + 1.5
    for _ in range(60):                      # widen until it brackets, cheap safety net
        if (F(lo) - target) * (F(hi) - target) < 0:
            return brentq(lambda y: F(y) - target, lo, hi, xtol=1e-8)
        lo, hi = lo - 1.0, hi + 1.0
    raise RuntimeError("mixture quantile bracket search failed")


def gkos_year_aggregate(guv_all, weights):
    """For each (year, sex) in the window: gather the GKOS cells with cohort+age-25 ==
    year and age in AGES, weight each by the EPUF sel0-survivor count at that same
    (year, age, sex), combine moments exactly, combine quantiles via the interpolated
    mixture CDF."""
    w = weights.set_index(["year", "sex", "age"])["n"]
    recs = []
    for (year, sex), cells in guv_all.groupby(["year", "sex"]):
        if not (YEARS[0] <= year <= YEARS[1]):
            continue
        wt = np.array([w.get((year, sex, a), 0.0) for a in cells["age"]])
        if wt.sum() <= 0:
            continue
        mu, sd, sk, ku = combine_moments(cells["meanlog"].values, cells["sdlog"].values,
                                         cells["skewlog"].values, cells["kurtlog"].values, wt)
        F = mixture_cdf_fn(cells, wt)
        lo, hi = np.log(cells["p10"].min()), np.log(cells["p98"].max())
        rec = {"year": year, "sex": sex, "n_ages": len(cells),
              "meanlog": mu, "sdlog": sd, "skewlog": sk, "kurtlog": ku}
        for q, c in zip(QUANTS, QCOLS):
            rec[c] = np.exp(mixture_quantile(F, q, lo, hi))
        # sanity check: mean/sd of the SAME mixture recovered from its own (closed-form)
        # density on a grid, against the exact combine_moments result above -- two
        # independent routes (moment-combination formulas vs quadrature over the
        # reconstructed mixture) that should agree unless the tail construction is
        # misbehaving.
        yg = np.linspace(lo - 1.5, hi + 1.5, 2001)
        pdf = mixture_pdf_grid(cells, wt, yg)
        pdf = np.clip(pdf, 0, None)
        pdf /= np.trapz(pdf, yg)
        mu_chk = np.trapz(pdf * yg, yg)
        sd_chk = np.sqrt(np.trapz(pdf * (yg - mu_chk)**2, yg))
        rec["meanlog_check"], rec["sdlog_check"] = mu_chk, sd_chk
        recs.append(rec)
    return pd.DataFrame(recs).sort_values(["sex", "year"])


def main():
    check_guv_conventions()
    guv_all = load_guv()
    guv_all = guv_all[(guv_all["age"] >= AGES[0]) & (guv_all["age"] <= AGES[1])]
    weights = epuf_cell_counts()
    ep = epuf_year_quantiles()
    defl = load_deflator()

    for c in QCOLS:
        ep[f"{c}_cens"] = ep[c] >= ep["taxmax"] - xm.HIGH_MARGIN
    fac = ep["year"].map(defl)
    for c in QCOLS:
        ep[c] = ep[c] * fac
    # meanlog/sdlog/skewlog/kurtlog were computed on NOMINAL earnings (the SQL LN(a.earnings)
    # above); only meanlog needs the deflator (log(x*fac) = log(x) + log(fac)) -- sdlog,
    # skewlog, kurtlog are invariant to an affine shift of the log scale. Missing this made
    # EPUF's meanlog look ~2 log points below GKOS's (already-real) meanlog in 1957, shrinking
    # to ~0.2 by 2006 -- tracking 1/deflator exactly, not a real earnings-composition gap.
    ep["meanlog"] = ep["meanlog"] + np.log(fac)

    gk = gkos_year_aggregate(guv_all, weights)
    print(f"GKOS side: {len(gk)} (year, sex) points, "
          f"n_ages {gk['n_ages'].min()}-{gk['n_ages'].max()} "
          f"(full window is {AGES[1] - AGES[0] + 1})")
    chk = (gk["meanlog"] - gk["meanlog_check"]).abs()
    print(f"mixture-CDF vs exact-moment meanlog check: "
          f"max |diff| = {chk.max():.4f}, mean = {chk.mean():.4f}")

    m = ep.merge(gk.add_suffix("_gkos").rename(columns={"year_gkos": "year", "sex_gkos": "sex"}),
                on=["year", "sex"], how="inner")
    m.to_csv(OUT_DIR / "guv_year_aggregate.csv", index=False)

    for c in SHOW:
        m[f"gap_{c}"] = np.where(m[f"{c}_cens"], np.nan, np.log(m[c] / m[f"{c}_gkos"]))
    m["decade"] = (m["year"] // 10) * 10
    pd.set_option("display.width", 200)
    print("\nmean log(EPUF/GKOS-aggregate) by decade, pooled cross-section ages 25-55:")
    print(m.groupby(["sex", "decade"])[[f"gap_{c}" for c in SHOW]].mean().round(3).to_string())

    plot(m)


# Color = categorical identity, fixed order across both panels: quantile level.
# Line style is the second, independent encoding (solid EPUF vs dashed GKOS), so
# source is never carried by color alone.
COL = {"p10": "#2a78d6", "p25": "#eb6834", "p50": "#1e9e64", "p75": "#8e5bd3"}


def plot(m):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharex=True)
    for ax, (sex, name) in zip(axes, ((1, "Men"), (2, "Women"))):
        d = m[m["sex"] == sex]
        for c in SHOW:
            # EPUF near the year's cap is a pile-up, not a real quantile -- break the
            # line rather than plot it (GKOS's own quantiles are never censored: the
            # published files impute above-cap earnings).
            epuf = d[c].where(~d[f"{c}_cens"])
            ax.plot(d["year"], epuf, color=COL[c], lw=1.8)
            ax.plot(d["year"], d[f"{c}_gkos"], color=COL[c], lw=1.8, ls="--")
        ax.set_title(name, fontsize=11)
        ax.grid(True, lw=0.4, alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=9)
    axes[0].set_ylabel("2013 $", fontsize=9)

    quant_handles = [plt.Line2D([], [], color=COL[c], lw=1.8) for c in SHOW]
    style_handles = [plt.Line2D([], [], color="0.3", lw=1.8),
                     plt.Line2D([], [], color="0.3", lw=1.8, ls="--")]
    fig.legend(quant_handles + style_handles, SHOW + ["EPUF", "GKOS"],
              ncol=len(SHOW) + 2, fontsize=8.5, frameon=False, loc="lower center",
              bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    for ext in ("pdf", "png"):
        fig.savefig(PLOT_DIR / f"guv_year_aggregate.{ext}", dpi=150)
    plt.close(fig)
    print(f"wrote {PLOT_DIR}/guv_year_aggregate.pdf (+ .png)")


if __name__ == "__main__":
    main()
