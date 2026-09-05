#!/usr/bin/env python
"""GKSW (Guvenen et al.) published cohort x age targets, and the numerically stable
log-space Normal-Laplace pdf/cdf they are compared against.

This module is the LIBRARY half of what used to live in plot_guv_comparison.py.  It was
split out because the estimation path imports it: the MLE+GMM mode of
estimate_cross_sections.py --mode mle-gmm needs load_guv / load_deflator / min_wage, and an estimator
must not import a plotting script (that dependency also dragged in matplotlib, and it
broke the moment the plot scripts moved into plots/).

Nothing here draws.  Contents:

  nl_logpdf_s / nl_cdf_s   log-space Normal-Laplace density and cdf.  crosssec_fit's
                           nl_cdf / nl_logpdf multiply phi(z) by a Mills ratio whose
                           erfcx overflows ~38 sd out, which the quadrature grid and
                           the bracket search do reach; these keep every term in logs.
                           Agreement with the originals in the mid-range is asserted by
                           _check_stable_vs_original (~1e-12).
  min_wage(year)           GKSW's own minimum-wage matrix, kept verbatim.
  load_deflator()          GKSW's own PCE vintage, base 2013, kept verbatim.
  load_guv()               the sel0 cohort x age moment files as one long frame, with
                           our sex coding (guv sex1 = men -> sex 1) and year = cohort +
                           age - 25.

Both matrices are the GKSW vintage rather than the current published series ON PURPOSE:
the guv files were produced with these, so reproducing their screen and their real-dollar
conversion requires them.  Do not "update" them.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import erfcx, ndtr

from crosssec_fit import nl_logpdf, nl_cdf

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


SEL0_HOURS, SEL0_FRAC = 520.0, 0.5


def sel0_threshold(year):
    """GKSW's per-year sample screen in NOMINAL dollars: keep earnings >= 0.5 x 520 h x
    minimum wage (cohortage_partiallifecycle_25mar2016_1pc.do, `keep if rwageinc >=
    0.5*rminwg*520`). The do-file states it in real terms, but rwageinc and rminwg carry
    the SAME year's deflator, so this nominal form is exact. It is the ONE definition every
    script that reproduces the screen must use -- the EPUF-side quantile validation, the
    model-side conditioning in plot_guv_comparison, the GMM targets in crosssec_gmm."""
    return SEL0_FRAC * SEL0_HOURS * min_wage(year)

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



def _bracket(cdf, target, y0, step, up):
    """Walk from y0 in steps until cdf crosses target, return the bracketing endpoint."""
    y = y0
    for _ in range(200):
        y = y + step if up else y - step
        if (cdf(y) > target) == up:
            return y
    raise RuntimeError("bracket search failed")


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


def check_guv_conventions():
    """Assert the hard-coded GKSW matrices still say what every loader assumes. Cheap, and
    the two mistakes it guards against are silent: a year-alignment slip in the PCE matrix
    would rescale every real-dollar comparison by a constant, and a screen coded in real
    dollars on one side only would move the bottom quantiles. Checks: 1947-2013 minimum-wage
    and 1947-2014 PCE matrices; the matrix is BEA's 2009 = 100 vintage, so its 2009 entry
    is exactly 100 (year alignment) and its 2013 entry is 107.572 -- the value the do-file's
    1-based base_price = 67 picks, so `deflate = cpi[67]/cpi[yr]` gives real 2013 dollars
    and the factor is 1.0 in 2013 (NOT "the 2013 entry is 100": that is a different
    matrix); and the do-file's real-dollar screen 0.5*rminwg*520 with rminwg = minwg x
    deflator equals sel0_threshold x the same deflator in every year, i.e. the nominal
    screen is the exact one."""
    assert len(_MW_GKSW) == 2013 - 1947 + 1, "minimum-wage matrix must span 1947-2013"
    assert len(_PCE_GKSW) == 2014 - 1947 + 1, "PCE matrix must span 1947-2014"
    assert _PCE_GKSW[2009 - 1947] == 100.0, "PCE matrix misaligned: 2009 entry is not 100"
    assert _PCE_GKSW[BASE_YEAR - 1947] == 107.572, "PCE matrix 2013 entry != do-file base"
    defl = load_deflator()
    assert abs(defl[BASE_YEAR] - 1.0) < 1e-12
    for y in range(1957, 2014):
        rminwg = min_wage(y) * defl[y]                       # do-file: real minimum wage
        assert abs(SEL0_FRAC * rminwg * SEL0_HOURS - sel0_threshold(y) * defl[y]) < 1e-9


def _check_stable_vs_original():
    a, b, nu, tau = 1.9, 0.55, 9.2, 0.5
    y = np.linspace(nu - 5, nu + 8, 200)          # mid-range, both versions valid
    assert np.max(np.abs(nl_cdf_s(y, a, b, nu, tau) - nl_cdf(y, a, b, nu, tau))) < 1e-10
    assert np.max(np.abs(nl_logpdf_s(y, a, b, nu, tau) - nl_logpdf(y, a, b, nu, tau))) < 1e-10

