#!/usr/bin/env python
"""DATA TERM 1: the doubly Type-I censored log-likelihood of one (year, sex, age) cell.

EPUF earnings are censored on both sides -- bottom-coded, and top-coded at the year's
taxable maximum -- so a cell's contribution is the interior density on (LOWC, HIGHC) plus
two tail masses:

    negll(theta) = -[ Sum_interior log f(y) + n_low log F(log LOWC)
                                            + n_high log (1 - F(log HIGHC)) ]

This is the ONLY thing this module builds. It knows nothing about penalties, smoothing, the
aggregate constraint or the GKSW targets -- estimate_cross_sections composes those on top.

TWO THINGS ARE LOAD-BEARING HERE:

  * The interior is BINNED ONCE, at build time (xs_model.bin_interior, <=256 mass points),
    so the sum runs over bin centres rather than over every observation. The joint solve
    refits each cell tens of times from a warm start, and this is the single biggest
    speedup in the pipeline -- a warm dPlN fit goes 46 ms -> 0.7 ms. Bin width is ~0.03 in
    log-earnings, negligible for the smooth densities fitted here; cells with n <= 256 pass
    through unbinned.
  * A non-finite likelihood returns 1e18 rather than inf or nan. L-BFGS-B's line search
    needs a finite value to back away from; nan makes it stop where it stands.

The returned `info` carries the censoring counts and thresholds the caller needs to write
its output row, so nothing downstream has to re-derive them from the data.
"""
import numpy as np

import xs_model as xm


def censored_negll(sex, x, lowc, highc):
    """Build the censored negative log-likelihood for one cell's earnings vector.

    Returns (negll, info): `negll(theta)` takes the sex's internal theta (see xs_model),
    and `info` holds n / n_low / n_high and the log thresholds. Doing the censor split and
    the interior binning here -- once per cell rather than once per objective evaluation --
    is what makes the warm inner-loop refits cheap."""
    yi, n_low, n_high = xm.censor_split(x, lowc, highc)
    yc, wc = xm.bin_interior(yi)
    tlo, thi = np.log(lowc), np.log(highc)
    info = dict(n=int(x.size), n_low=n_low, n_high=n_high, tlo=tlo, thi=thi,
                yi=yi, lowc=lowc, highc=highc)

    if sex == 1:
        def negll(theta):
            a, b, nu, tau = np.exp(theta[0]), np.exp(theta[1]), theta[2], np.exp(theta[3])
            ll = (float(xm.nl_logpdf(yc, a, b, nu, tau) @ wc)
                  + n_low * np.log(xm.nl_cdf(tlo, a, b, nu, tau))
                  + n_high * np.log1p(-xm.nl_cdf(thi, a, b, nu, tau)))
            return -ll if np.isfinite(ll) else 1e18
    else:
        def negll(theta):
            p = xm._unpack(theta)
            ll = (float(xm.mix_logpdf(yc, *p) @ wc)
                  + n_low * np.log(xm.mix_cdf(tlo, *p))
                  + n_high * np.log(xm.mix_sf(thi, *p)))
            return -ll if np.isfinite(ll) else 1e18

    return negll, info


def moment_starts(sex, x, lowc):
    """A few basin-spanning warm starts for a cold fit: grid the regime-defining coordinate
    and moment-match the rest, so a top-K keep captures the COMPETING optima rather than one
    basin K times. Men: the upper-tail index alpha (the weakly identified one under a tight
    cap). Women: the weight x separation of the two components, whose swap is the mixture's
    own regime flip."""
    yi, _, _ = xm.censor_split(x, lowc, x.max())
    m, s = yi.mean(), max(yi.std(), 1e-2)
    if sex == 1:
        return [[np.log(a0), np.log(3.0), m, np.log(s)] for a0 in (1.5, 3.0, 20.0)]
    ls = np.log(max(0.7 * s - xm.SIG_FLOOR, 1e-3))
    return [[m + d * s, m - d * s, ls, ls, np.log(w0 / (1 - w0))]
            for w0, d in ((0.3, 0.9), (0.5, 0.4), (0.7, 0.9))]
