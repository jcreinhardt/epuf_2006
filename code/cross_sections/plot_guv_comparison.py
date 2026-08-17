#!/usr/bin/env python
"""Compare the fitted cross-section distributions against the Guvenen et al. cohort x age
summary statistics in raw_data/guv_quantiles/ (meanlog, sdlog, skewlog, kurtlog, p10-p98
of real wage income, ages 25-55).

Provenance of those files is now PROVEN, not inferred: they are the output of
`cohortage_partiallifecycle_25mar2016_1pc.do` in the GKSW AEJ:Applied 2022 replication
package (replication_repos/GKOS_2022, "Lifetime Earnings in the United States over Six
Decades"; used for the paper's Figures 7, 11, 12). The package ships a column subset of
the same run (TextFiles/COHORTAGE_FULL: sdlog, p10, p50, p90) and every overlapping value
across all 1,764 cohort x age rows is byte-identical to our files. That do-file fixes the
exact conventions:
  - `cohort` is the YEAR THE PERSON TURNS 25 (`cohort = yob + 25`), so calendar year =
    cohort + age - 25; window 1957-2013, cohorts 1927-2011 partially observed at the
    edges. (Our own CSVs label cohorts by BIRTH year; do not mix them.)
  - sex1 = men, sex0 = women -- from the code itself (it loads the male longshape file
    for s==1). CONTRADICTS the label in full_model's e2b_build_df_earn.ipynb, which
    flips the same files.
  - BOTH sel0 and sel3 impose the per-year threshold screen before any statistic:
    keep if real earnings >= 0.5 * 520 * real minimum wage, i.e. NOMINAL earnings >=
    260 x nominal minwage (~$1,885 in 2013; the same-year deflator cancels). sel0 is
    therefore NOT "all positive earners".
  - sel3 additionally applies a PERSON-LEVEL lifetime attachment filter (prorated for
    partially observed cohorts): average real earnings over the person's available ages
    25-55 of at least 0.5*520*$6 = $1,560 (2013$), AND above the annual threshold in at
    least HALF of the available years (the paper's ">=15 of 31 years", prorated).
  - earnings are winsorized at the 99.999th percentile within each year, before selection.
  - values are REAL 2013 dollars, PCE-deflated -- the package ReadMe assigns this run to
    the PCE merge_reshape, and the paper (Section I.B) picks PCE as baseline explicitly.
    We use the package's own PCE matrix verbatim. NOTE an earlier empirical check here
    matched CPI-U better; the reconciliation is a concept gap, not the deflator: GKSW use
    total W-2 wage/salary income of "commerce and industry" workers (CWHS 1%), while EPUF
    records covered earnings of all covered workers -- MEF wage quantiles sit ~7-10%
    above EPUF's in the early decades (shrinking as coverage expands), which masquerades
    as the CPI/PCE wedge. Under PCE the model's meanlog / dollar quantiles therefore sit
    visibly BELOW the data in early years; that gap is the concept/coverage wedge and is
    expected. sdlog/skewlog/kurtlog are unaffected by the deflator entirely.
  - income concept: W-2 wage and salary only -- NO self-employment (GKSW footnote 10:
    Schedule SE exists from 1978 but is excluded; top-coded until 1994). Pre-1978
    above-cap earnings are imputed from quarterly patterns (Kopczuk-Saez-Song).

Model side: parameters from cross_section_params_extrapolated.csv (the canonical complete
surface -- in-sample pass-through where kept, plus the 2007-2013 years the Guvenen window
needs). For each (year, sex, age) cell the model's log-earnings law is fully specified
(Normal-Laplace for men, two-normal mixture for women), so every functional is computed
from the fitted distribution itself: log-moments by quadrature on the log-density,
quantiles by root-finding on the CDF. The model functional is computed CONDITIONAL ON
X >= Ymin(t) = 260 x nominal minwage -- the correct counterpart of sel0, since sel0
already carries that screen. sel3 has NO model counterpart (its extra selection is on the
person's earnings HISTORY, which a sequence of independent cross-sections cannot
reproduce), so the sel3 files are not used here at all.
Model nominal dollars are converted to real 2013 dollars with the same PCE deflator.

Cell coverage: the guv files are a COMPLETE grid over years 1957-2013 x ages 25-55 for
both sexes (cohorts 1927-2011; the only absent cells are cohorts 2012-13, i.e.
(2012, age 25), (2013, 25), (2013, 26)), and every guv cell has a fitted-parameter row.
The reverse does not hold: EPUF's in-sample years 1951-1956 and fitted ages outside
25-55 have no Guvenen counterpart and drop out of the comparison.
Deflating the FUNCTIONALS (rather than deflating draws and recomputing) is exact, not an
approximation: a (cohort, age) cell is a single calendar year, so deflation is one
constant c within the cell, and quantiles are equivariant under monotone maps
(Q_{cX}(p) = c Q_X(p)) while log(cX) = log c + log X shifts meanlog by log c and leaves
sd/skew/kurt of logs untouched. Nonlinearity would only bite if one deflated a statistic
already aggregated ACROSS years -- which never happens here: deflation is per cell,
averaging across cells comes after, matching how the Guvenen files themselves are built
(micro data deflated per year before the per-cell stats).

Output: two figures per sex. The by-cohort figure averages each functional across ages
25-55 with cohort on the x-axis; the by-age figure averages across cohorts with age on
the x-axis. Both averages are restricted, cell by cell, to the (cohort, age) cells
actually present in the Guvenen file and use equal cell weights ON BOTH SIDES, so the
model average carries the identical composition (edge cohorts are age-truncated by the
1957/2013 window; equivalently every age mixes a different cohort set).

  python code/cross_sections/plot_guv_comparison.py [params_csv] [tag]
    -> output/cross_sections/plots/guv_comparison_{men,women}[_tag].pdf (+ .png)       by cohort
    -> output/cross_sections/plots/guv_comparison_byage_{men,women}[_tag].pdf (+ .png) by age
    -> output/cross_sections/guv_comparison_{cohort,age}_means[_tag].csv

`params_csv` swaps the parameter surface (e.g. cross_section_params_guvgmm.csv, or the
pure-GMM cross_section_params_guvgmm_lam1.csv); `tag` suffixes every output file so
alternative fits sit next to the canonical figures instead of overwriting them. An
alternative surface without 2007-2013 rows just drops those guv cells (with a warning),
so its by-age averages mix years 1957-2006 only.
"""
import sys
from pathlib import Path

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import brentq
from scipy.special import erfcx, ndtr

from crosssec_fit import nl_logpdf, nl_cdf, mix_logpdf, mix_cdf

# ---- log-space Normal-Laplace pdf/cdf. crosssec_fit's nl_cdf/nl_logpdf multiply
# phi(z) by a Mills ratio whose erfcx overflows ~38 sd out, which the quadrature grid
# and bracket search do reach; these keep every term in logs and agree to ~1e-12 in the
# mid-range (asserted at startup).
SQRT2, LOG2PI = np.sqrt(2.0), np.log(2.0 * np.pi)
LOG_SQRT_HALF_PI = 0.5 * np.log(np.pi / 2.0)


def _log_mills(w):
    w = np.asarray(w, dtype=float)
    scalar = w.ndim == 0
    w = np.atleast_1d(w)
    out = np.empty_like(w)
    ok = w > -25.0
    out[ok] = LOG_SQRT_HALF_PI + np.log(erfcx(w[ok] / SQRT2))
    out[~ok] = np.log(2.0) + LOG_SQRT_HALF_PI + 0.5 * w[~ok] * w[~ok]
    return out[0] if scalar else out


def nl_logpdf_s(y, a, b, nu, tau):
    z = (np.asarray(y, dtype=float) - nu) / tau
    lphi = -0.5 * LOG2PI - 0.5 * z * z
    return (np.log(a) + np.log(b) - np.log(a + b) + lphi
            + np.logaddexp(_log_mills(a * tau - z), _log_mills(b * tau + z)))


def nl_cdf_s(y, a, b, nu, tau):
    z = (np.asarray(y, dtype=float) - nu) / tau
    lphi = -0.5 * LOG2PI - 0.5 * z * z
    l1 = lphi + np.log(b / (a + b)) + _log_mills(a * tau - z)
    l2 = lphi + np.log(a / (a + b)) + _log_mills(b * tau + z)
    return ndtr(z) - np.exp(l1) + np.exp(l2)

GUV_DIR   = Path("raw_data/guv_quantiles")
PARAMS    = Path("output/cross_sections/cross_section_params_extrapolated.csv")
OUT_DIR   = Path("output/cross_sections")            # the two *_means.csv
PLOT_DIR  = Path("output/cross_sections/plots")      # the four figures
TAG       = ""                                       # "_<tag>" suffix on every output file
BASE_YEAR = 2013

QUANTS  = [0.10, 0.25, 0.50, 0.75, 0.90, 0.98]
QCOLS   = ["p10", "p25", "p50", "p75", "p90", "p98"]
MCOLS   = ["meanlog", "sdlog", "skewlog", "kurtlog"]
FUNCTIONALS = MCOLS + QCOLS

# GKSW's own minimum-wage matrix (merge_reshape_*.do, 1947-2013; it lags statutory
# effective dates by ~a year -- kept verbatim to reproduce their screen). Ymin = 260 x
# this: their screen keeps real earnings >= 0.5 * rminwg * 520h. It is stated in real
# dollars, but the deflator cancels against the same-year earnings, so the nominal
# form is exact.
_MW_GKSW = [0.40, 0.40, 0.40, 0.40, 0.75, 0.75, 0.75, 0.75, 0.75, 1.00,   # 1947-56
            1.00, 1.00, 1.00, 1.00, 1.00, 1.15, 1.15, 1.25, 1.25, 1.25,   # 1957-66
            1.25, 1.40, 1.60, 1.60, 1.60, 1.60, 1.60, 1.60, 2.00, 2.10,   # 1967-76
            2.10, 2.30, 2.65, 2.90, 3.10, 3.35, 3.35, 3.35, 3.35, 3.35,   # 1977-86
            3.35, 3.35, 3.35, 3.35, 3.80, 4.25, 4.25, 4.25, 4.25, 4.25,   # 1987-96
            4.75, 5.15, 5.15, 5.15, 5.15, 5.15, 5.15, 5.15, 5.15, 5.15,   # 1997-2006
            5.15, 5.85, 6.55, 7.25, 7.25, 7.25, 7.25]                     # 2007-13

def min_wage(year):
    return _MW_GKSW[year - 1947]

# GKSW's own PCE deflator matrix (merge_reshape_06jan2016_1pc.do, 1947-2014, their
# vintage kept verbatim; the run that produced the guv files deflates with THIS, base
# 2013, per the package ReadMe).
_PCE_GKSW = [13.325, 14.079, 13.969, 14.136, 15.098, 15.408, 15.613, 15.746,   # 1947-54
             15.810, 16.126, 16.616, 17.007, 17.262, 17.546, 17.730, 17.939,   # 1955-62
             18.149, 18.414, 18.681, 19.155, 19.637, 20.402, 21.327, 22.325,   # 1963-70
             23.274, 24.070, 25.368, 28.009, 30.348, 32.013, 34.091, 36.479,   # 1971-78
             39.714, 43.978, 47.908, 50.553, 52.729, 54.724, 56.661, 57.887,   # 1979-86
             59.650, 61.974, 64.642, 67.440, 69.653, 71.494, 73.279, 74.803,   # 1987-94
             76.356, 77.981, 79.327, 79.935, 81.110, 83.132, 84.736, 85.874,   # 1995-2002
             87.572, 89.703, 92.261, 94.729, 97.101, 100.065, 100.000, 101.653,  # 2003-10
             104.149, 106.121, 107.572, 109.105]                               # 2011-14


# ---------------------------------------------------------------- model functionals
def _cell_dists(row):
    """(logpdf, cdf) callables on y = log earnings for one parameter row."""
    if row["sex"] == 1:
        a, b, nu, tau = row["alpha"], row["beta"], row["nu"], row["tau"]
        return (lambda y: nl_logpdf_s(y, a, b, nu, tau),
                lambda y: nl_cdf_s(y, a, b, nu, tau))
    m1, m2, s1, s2, w = row["mu1"], row["mu2"], row["sig1"], row["sig2"], row["w"]
    return (lambda y: mix_logpdf(y, m1, m2, s1, s2, w),
            lambda y: mix_cdf(y, m1, m2, s1, s2, w))


def _bracket(cdf, target, y0, step, up):
    """Walk from y0 in steps until cdf crosses target, return the bracketing endpoint."""
    y = y0
    for _ in range(200):
        y = y + step if up else y - step
        if (cdf(y) > target) == up:
            return y
    raise RuntimeError("bracket search failed")


def cell_functionals(row, x_min=None, ngrid=8001):
    """Log-moments (quadrature) and earnings quantiles (root-finding) of one fitted cell,
    optionally conditional on earnings > x_min (nominal $). Returns a dict. The 1e-10
    tail cutoffs matter: the NL tails are exponential, so kurtlog converges slowly --
    truncating at 1e-7 already costs ~2e-3."""
    logpdf, cdf = _cell_dists(row)
    center = row["nu"] if row["sex"] == 1 else (row["w"] * row["mu1"]
                                                + (1 - row["w"]) * row["mu2"])
    ylo = _bracket(cdf, 1e-10, center, 1.0, up=False)
    yhi = _bracket(cdf, 1.0 - 1e-10, center, 1.0, up=True)

    t = -np.inf if x_min is None else np.log(x_min)
    Ft = 0.0 if x_min is None else float(cdf(t))
    glo = max(ylo, t)

    y = np.linspace(glo, yhi, ngrid)
    wts = np.exp(logpdf(y))
    wts[0] *= 0.5; wts[-1] *= 0.5            # trapezoid
    wts /= wts.sum()                          # renormalizes truncation + conditioning
    m1 = wts @ y
    d = y - m1
    m2, m3, m4 = wts @ d**2, wts @ d**3, wts @ d**4
    out = {"meanlog": m1, "sdlog": np.sqrt(m2),
           "skewlog": m3 / m2**1.5, "kurtlog": m4 / m2**2}

    for q, col in zip(QUANTS, QCOLS):
        target = Ft + q * (1.0 - Ft)
        out[col] = np.exp(brentq(lambda v: cdf(v) - target, glo - 1.0, yhi + 1.0))
    return out


def check_against_cumulants(row):
    """Sanity check: unconditional quadrature vs the closed-form Normal-Laplace cumulants."""
    a, b, nu, tau = row["alpha"], row["beta"], row["nu"], row["tau"]
    k1 = nu + 1 / a - 1 / b
    k2 = tau**2 + a**-2 + b**-2
    k3 = 2 * a**-3 - 2 * b**-3
    k4 = 6 * a**-4 + 6 * b**-4
    exact = {"meanlog": k1, "sdlog": np.sqrt(k2),
             "skewlog": k3 / k2**1.5, "kurtlog": 3 + k4 / k2**2}
    got = cell_functionals(row)
    err = max(abs(got[k] - v) for k, v in exact.items())
    assert err < 1e-3, f"quadrature vs cumulants disagree: {err}"
    return err


# ---------------------------------------------------------------- data loading
def load_guv():
    frames = []
    for gsex, sex in ((1, 1), (0, 2)):           # guv sex1 = men -> our sex 1
        f = GUV_DIR / f"cohortage_rwageinc_sel0_25_55_sex{gsex}.txt"
        d = pd.read_csv(f, sep="\t")
        d["sex"] = sex
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    d["year"] = d["cohort"] + d["age"] - 25
    return d


def load_deflator():
    base = _PCE_GKSW[BASE_YEAR - 1947]
    return {1947 + i: base / p for i, p in enumerate(_PCE_GKSW)}   # nominal x factor -> real 2013 $


# ---------------------------------------------------------------- main
def _check_stable_vs_original():
    a, b, nu, tau = 1.9, 0.55, 9.2, 0.5
    y = np.linspace(nu - 5, nu + 8, 200)          # mid-range, both versions valid
    assert np.max(np.abs(nl_cdf_s(y, a, b, nu, tau) - nl_cdf(y, a, b, nu, tau))) < 1e-10
    assert np.max(np.abs(nl_logpdf_s(y, a, b, nu, tau) - nl_logpdf(y, a, b, nu, tau))) < 1e-10


def main():
    _check_stable_vs_original()
    guv = load_guv()
    par = pd.read_csv(PARAMS)
    par = par.set_index(["year", "sex", "age"])
    defl = load_deflator()

    chk = par.reset_index()
    chk = chk[(chk["sex"] == 1) & (chk["year"] == 1990) & (chk["age"] == 40)].iloc[0]
    print(f"quadrature-vs-cumulants check (men 1990 age 40): max err {check_against_cumulants(chk):.2e}")

    cells = guv[["year", "sex", "age"]].drop_duplicates()
    rows, missing = [], 0
    for _, c in cells.iterrows():
        key = (c["year"], c["sex"], c["age"])
        if key not in par.index:
            missing += 1
            continue
        prow = par.loc[key].copy()
        prow["sex"] = c["sex"]
        fac = defl[c["year"]]
        f = cell_functionals(prow, x_min=260.0 * min_wage(c["year"]))   # the sel0 screen
        rec = {"year": c["year"], "sex": c["sex"], "age": c["age"],
               "meanlog": f["meanlog"] + np.log(fac),
               "sdlog": f["sdlog"], "skewlog": f["skewlog"], "kurtlog": f["kurtlog"]}
        rec.update({q: f[q] * fac for q in QCOLS})
        rows.append(rec)
    if missing:
        print(f"WARNING: {missing} guv cells had no fitted parameters and were dropped")
    model = pd.DataFrame(rows)
    assert not model[FUNCTIONALS].isna().any().any(), \
        "NaN in model functionals (deflator coverage? parameter gaps?)"

    # wide layout: per cell one row with _sel0 (data) and _mod (model | X>=Ymin)
    merged = guv.rename(columns={c: f"{c}_sel0" for c in FUNCTIONALS}).merge(
        model.rename(columns={c: f"{c}_mod" for c in FUNCTIONALS}),
        on=["year", "sex", "age"], how="inner")
    allcols = [f"{c}_{s}" for c in FUNCTIONALS for s in ("sel0", "mod")]
    for bycol, stub in (("cohort", "cohort"), ("age", "age")):
        agg = merged.groupby(["sex", bycol])[allcols].mean().reset_index()
        agg.to_csv(OUT_DIR / f"guv_comparison_{stub}_means{TAG}.csv", index=False)
        plot_figures(agg, bycol)


def plot_figures(d_all, bycol):
    BLUE, ORANGE = "#2a78d6", "#eb6834"       # validated categorical slots 1-2
    labels = {"meanlog": "mean log earnings", "sdlog": "sd log earnings",
              "skewlog": "skewness log earnings", "kurtlog": "kurtosis log earnings",
              **{q: f"{q} of earnings (real {BASE_YEAR} $)" for q in QCOLS}}
    by_cohort = bycol == "cohort"
    if by_cohort:
        avg_txt, x_txt = "averaged over ages 25-55", "cohort (year turning age 25)"
        note = "shaded: cohorts using post-2006\nextrapolated parameters"
    else:
        avg_txt, x_txt = "averaged over cohorts 1927-2011", "age"
        note = ("every age mixes years 1957-2013,\n"
                "incl. post-2006 extrapolated parameters")
    for sex, name in ((1, "men"), (2, "women")):
        d = d_all[d_all["sex"] == sex].sort_values(bycol)
        fig, axes = plt.subplots(3, 4, figsize=(17, 10.5))
        for ax, col in zip(axes.flat, FUNCTIONALS):
            ax.plot(d[bycol], d[f"{col}_sel0"], color=BLUE, lw=1.8,
                    marker="o", ms=2.6, label="GKSW data, sel0 (above $Y_{min}$)")
            ax.plot(d[bycol], d[f"{col}_mod"], color=ORANGE, lw=1.8,
                    ls="--", label="model $\\mid X \\geq Y_{min}$")
            if by_cohort:
                ax.axvspan(1977, d[bycol].max() + 1, color="0.5", alpha=0.10, lw=0)
            ax.set_title(labels[col], fontsize=11)
            ax.tick_params(labelsize=9)
            ax.grid(True, lw=0.4, alpha=0.4)
            if col in QCOLS:
                ax.set_ylim(bottom=0)
        for ax in axes.flat[len(FUNCTIONALS):]:
            ax.axis("off")
        handles, leg_labels = axes.flat[0].get_legend_handles_labels()
        axes.flat[-1].legend(handles, leg_labels, loc="center left", fontsize=11,
                             frameon=False, title=note)
        fig.suptitle(f"GKSW cohort x age functionals vs fitted model -- {name}\n"
                     f"{avg_txt} (cells matched to data availability, equal weights); "
                     f"real dollars, GKSW PCE deflator base {BASE_YEAR}; level gaps partly "
                     f"reflect covered-vs-W2 earnings concepts",
                     fontsize=13)
        fig.supxlabel(x_txt, fontsize=11)
        fig.tight_layout(rect=(0, 0.01, 1, 0.96))
        suffix = "" if by_cohort else "_byage"
        for ext in ("pdf", "png"):
            fig.savefig(PLOT_DIR / f"guv_comparison{suffix}_{name}{TAG}.{ext}", dpi=150)
        plt.close(fig)
        print(f"wrote {PLOT_DIR}/guv_comparison{suffix}_{name}{TAG}.pdf (+ .png)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        PARAMS = Path(sys.argv[1])
    if len(sys.argv) > 2:
        TAG = "_" + sys.argv[2].lstrip("_")
    main()
