#!/usr/bin/env python
"""DATA TERM 2: a truncation-aware, iterated GMM criterion on the published GKSW (guv)
sel0 cohort x age targets -- r(theta)' W r(theta).

The residual vector is 10 statistics of the TRUNCATED log law (sel0 drops observations
below Ymin(t) = 260 x nominal minimum wage): meanlog, sdlog, skewlog, kurtlog, and six
inverted quantile conditions at p10/p25/p50/p75/p90/p98.

SHAPE ONLY -- THE LEVEL DIRECTION IS PROJECTED OUT. This is the single most important
thing about this module, and the reason it can share a surface with the aggregate-mean
constraint at all.

  The GKSW targets are built on a W-2 commerce-and-industry earnings concept that runs
  ~7-10% ABOVE EPUF covered earnings in the early decades. Efficient weighting makes that
  wedge bind HARD -- meanlog's sampling sd is ~sigma/sqrt(n) ~ 0.008, so a 0.08 log-point
  concept gap is ~10 standard deviations, and an unrestricted GMM term will spend fit
  freely to close it. Against estimate_cross_sections' eta constraint, which pins the same
  cells' level to the published ASS aggregate, that is a fight the GMM term wins: eta can
  only thin, so it would run to its ceiling against a criterion that keeps re-inflating.

  So the criterion is made blind to the level. Because a shift of the model's log scale is
  an EXACT group action on both families -- shifting nu (dPlN), or both mu's (mixture), by
  delta shifts log X by delta exactly -- the concept wedge is exactly one direction in
  residual space, and we concentrate it out:

      Q(theta) = min_delta  r(theta, delta)' W r(theta, delta)
               = r0' W r0  -  (d' W r0)^2 / (d' W d),     d = dr/d(delta)

  the W-orthogonal projection of that direction out of r. What survives is dispersion,
  skewness, kurtosis and the SPACING of the quantiles; what is discarded is exactly the one
  number the published series cannot legitimately tell us. Levels are not concept-robust;
  the shape functionals are.

  delta itself falls out for free as -(d' W r0)/(d' W d) -- an estimate of the W-2 vs
  covered-earnings wedge, per cell (`level_wedge`). It is a diagnostic, not an input.

  A CONSEQUENCE: this criterion does NOT identify the location on its own. At lam < 1 the
  likelihood pins it and all is well; at lam = 1 the level is unidentified by construction,
  which is why there is no pure-GMM path here.

  Note the truncation moves WITH the shift: the published statistics condition on the
  published concept exceeding Ymin, so the model sees threshold t - delta and evaluation
  points y_q - delta. Both are handled inside `make_resid`.

EVERYTHING IS CLOSED FORM (no quadrature, no root-finding inside the optimizer):
  - quantiles enter INVERTED, as CDF conditions: the published real-2013$ quantile is
    deflated to nominal logs y_q and the residual is (F(y_q)-F(t))/(1-F(t)) - q. Smooth in
    theta, no bisection.
  - the four truncated log-moments are closed form. Mixture: truncated-normal moment
    recursions per component. dPlN: the Normal-Laplace density is a sum of two
    exponentially-tilted normal-CDF terms (Reed-Jorgensen), and integration by parts reduces
    each centered partial moment to the recursion nl_trunc_central below, whose only
    primitives are Phi, phi and standard-normal upper partial moments. Every exp x Phi
    product is assembled in logs (log_ndtr), so tilts like e^{b^2/2} at beta*tau ~ 20 cannot
    overflow. Validated against a dense quadrature by _check_closed_forms().
  - d = dr/d(delta) is a central difference at DELTA_H. Analytic would need the derivative
    of the truncated moments in the threshold; two extra residual evaluations is the cheaper
    trade, and the projection only needs the direction to first order.

ITERATED GMM WEIGHTING. The published guv files carry no cell counts or covariances, so W
is estimated from the MODEL, iteratively:
  - iteration 0: a "uniform-ish" diagonal from fixed scales (MSCALE per moment, q(1-q) per
    quantile condition -- the latter is already that condition's exact asymptotic variance x n).
  - then, repeatedly: at the current theta-hat, compute the model-implied sampling covariance
    Sigma~ of the data statistics by influence functions on a dense grid of the truncated law,
    invert with an eigenvalue floor, refit with the new W.
  W is FROZEN during each inner solve -- iterated GMM's outer loop is where it moves -- so
  the grid-based Sigma~ never touches the analyticity of the inner objective. The guv cell
  size is proxied by EPUF's own post-screen cell count (both are 1% samples).

SCALING / lam SEMANTICS: W = n_guv * Sigma~^-1 / (2 n_epuf), so at lam = 0.5 the composite
objective (1-lam) negll/n + lam r'Wr is proportional to negll + (1/2) r' [Sigma~/n_guv]^-1 r
-- exactly the composite likelihood that treats the published statistics as Gaussian
observations at their estimated precision.
"""
import numpy as np
from math import comb
from scipy.special import ndtr, log_ndtr
from scipy.optimize import brentq

import xs_model as xm
from guv_targets import (load_guv, load_deflator, min_wage,
                         nl_logpdf_s, nl_cdf_s, _bracket, QUANTS, QCOLS)

# Iteration-0 diagonal scales: a "meaningful mismatch" per moment residual, and the exact
# asymptotic variance q(1-q) per (inverted) quantile condition. Moments in the order
# [meanlog, sdlog, skewlog, kurtlog].
MSCALE    = np.array([0.05, 0.05, 0.10, 0.30])
QARR      = np.array(QUANTS)
SQRT2PI   = np.sqrt(2.0 * np.pi)
EIG_FLOOR = 1e-9      # relative eigenvalue floor when inverting Sigma~
DELTA_H   = 0.02      # central-difference step for the level direction, in log points.
                      # Small against the ~0.08 wedge it is meant to span, large against the
                      # residuals' own curvature in delta.
NR = len(MSCALE) + len(QUANTS)      # residual length (10); rank 9 after the projection


# ------------------------------------------------------------------ guv targets
def guv_targets(years):
    """{(year, sex, age): (t_nominal_log, moment_targets[4], quantile_log_targets[6])} for
    the requested years, everything converted to NOMINAL log dollars via GKSW's own PCE
    deflator (so the same-year deflator cancels out of the sel0 screen)."""
    guv, defl = load_guv(), load_deflator()
    want, tab = set(years), {}
    for r in guv.itertuples():
        y = int(r.year)
        if y not in want:
            continue
        lfac = np.log(defl[y])                      # log(nominal -> real-2013 factor)
        t = np.log(260.0 * min_wage(y))             # the sel0 screen, nominal logs
        m = np.array([r.meanlog - lfac, r.sdlog, r.skewlog, r.kurtlog])
        yq = np.array([np.log(getattr(r, c)) - lfac for c in QCOLS])
        tab[(y, int(r.sex), int(r.age))] = (t, m, yq)
    return tab
# ------------------------------------------- closed-form truncated log-moments
def _norm_upper_moments(L, kmax):
    """m_j = int_L^inf s^j phi(s) ds, j = 0..kmax, by the standard recursion
    m_j = L^(j-1) phi(L) + (j-1) m_{j-2}."""
    phiL = np.exp(-0.5 * L * L) / SQRT2PI
    m = [ndtr(-L), phiL]
    for j in range(2, kmax + 1):
        m.append(L ** (j - 1) * phiL + (j - 1) * m[j - 2])
    return m


def _Tk(L, s0, kmax):
    """T_k = int_L^inf (s - s0)^k phi(s) ds, k = 0..kmax (binomial in the m_j)."""
    m = _norm_upper_moments(L, kmax)
    return [sum(comb(k, j) * (-s0) ** (k - j) * m[j] for j in range(k + 1))
            for k in range(kmax + 1)]


def nl_trunc_central(alpha, beta, nu, tau, t):
    """(survival, mean, mu2, mu3, mu4) of the Normal-Laplace | Y >= t. CLOSED FORM.

    Writing the NL density as (ab/(a+b)) [e^{a^2/2 - a s} Phi(s-a) + e^{b^2/2 + b s}
    Phic(s+b)] in standardized s = (y-nu)/tau with a = alpha*tau, b = beta*tau,
    integration by parts gives, for partial moments about a center s0,
        I_k^A = [(L-s0)^k cA + k I_{k-1}^A + T_k] / a
        I_k^B = [-(L-s0)^k cB - k I_{k-1}^B + T_k] / b
    with cA = e^{a^2/2 - aL} Phi(L-a), cB = e^{b^2/2 + bL} Phic(L+b) (both assembled
    in logs) and T_k the shifted normal partial moments. Two passes: s0 = 0 gives the
    conditional mean; re-centering at it gives the central moments without the
    catastrophic cancellation of a raw-moment binomial expansion."""
    a, b = alpha * tau, beta * tau
    L = (t - nu) / tau
    cA = np.exp(0.5 * a * a - a * L + log_ndtr(L - a))
    cB = np.exp(0.5 * b * b + b * L + log_ndtr(-(L + b)))

    def I_sum(s0, kmax):
        T = _Tk(L, s0, kmax)
        IA, IB = [(cA + T[0]) / a], [(-cB + T[0]) / b]
        for k in range(1, kmax + 1):
            d = (L - s0) ** k
            IA.append((d * cA + k * IA[k - 1] + T[k]) / a)
            IB.append((-d * cB - k * IB[k - 1] + T[k]) / b)
        return [ia + ib for ia, ib in zip(IA, IB)]

    I0 = I_sum(0.0, 1)
    if not (I0[0] > 0.0) or not np.isfinite(I0[0]):
        return None
    s_mean = I0[1] / I0[0]
    C = I_sum(s_mean, 4)                        # centered: C[1]/C[0] ~ 0 by construction
    S = (a * b / (a + b)) * I0[0]
    return (S, nu + tau * s_mean,
            tau ** 2 * C[2] / C[0], tau ** 3 * C[3] / C[0], tau ** 4 * C[4] / C[0])


def mix_trunc_central(p, t):
    """(survival, mean, mu2, mu3, mu4) of the two-normal mixture | Y >= t. CLOSED FORM
    via per-component truncated-normal partial moments (_Tk), mixture-weighted."""
    mu1, mu2_, s1, s2, w = p
    comps = ((mu1, s1, w), (mu2_, s2, 1.0 - w))
    S = sum(wt * ndtr((mu - t) / s) for mu, s, wt in comps)
    if not (S > 0.0):
        return None
    num = 0.0
    for mu, s, wt in comps:
        L = (t - mu) / s
        num += wt * (mu * ndtr(-L) + s * np.exp(-0.5 * L * L) / SQRT2PI)
    m = num / S
    cen = np.zeros(5)
    for mu, s, wt in comps:
        T = _Tk((t - mu) / s, (m - mu) / s, 4)
        cen += wt * np.array([s ** k * T[k] for k in range(5)])
    return S, m, cen[2] / S, cen[3] / S, cen[4] / S


def _check_closed_forms():
    """Startup validation: closed forms vs a dense trapezoid quadrature, both models."""
    for label, mom, logpdf, cdf, span in (
        ("dpln", lambda t: nl_trunc_central(2.1, 0.9, 9.3, 0.42, t),
         lambda y: nl_logpdf_s(y, 2.1, 0.9, 9.3, 0.42),
         lambda y: nl_cdf_s(y, 2.1, 0.9, 9.3, 0.42), (9.3 - 14.0, 9.3 + 18.0)),
        ("mix", lambda t: mix_trunc_central((9.6, 8.1, 0.55, 1.25, 0.62), t),
         lambda y: xm.mix_logpdf(y, 9.6, 8.1, 0.55, 1.25, 0.62),
         lambda y: xm.mix_cdf(y, 9.6, 8.1, 0.55, 1.25, 0.62), (8.1 - 12.0, 9.6 + 12.0)),
    ):
        for t in (span[0], 7.2, 8.9):
            S, m, mu2, mu3, mu4 = mom(t)
            y = np.linspace(max(t, span[0]), span[1], 200001)
            wq = np.exp(logpdf(y))
            wq[0] *= 0.5; wq[-1] *= 0.5
            wq /= wq.sum()
            mq = wq @ y
            d = y - mq
            ref = (1.0 - cdf(t), mq, wq @ d**2, wq @ d**3, wq @ d**4)
            err = max(abs(u - v) for u, v in zip((S, m, mu2, mu3, mu4), ref))
            assert err < 1e-4, f"closed-form {label} vs quadrature at t={t}: err {err}"



# ------------------------------------------------------------------ residuals + Q
def make_resid(sex, t, mtar, yq):
    """r(theta, delta) -- the NR-vector of residuals against one cell's guv targets, at a
    log-scale shift `delta` of the model.

    delta > 0 means the published concept sits above the model's: log X_guv = log X_model +
    delta. Because that shift is exact for both families, the whole comparison just moves --
    the model's own truncation threshold becomes t - delta, its quantile evaluation points
    y_q - delta, and its conditional mean gains delta. sd / skew / kurt are central moments,
    so they take no delta term of their own; they still feel the shift through the threshold.

    Returns None where the truncated law is degenerate (no mass above the screen, or a
    vanishing variance), which make_qfun turns into an infinite criterion."""
    if sex == 1:
        def resid(theta, delta=0.0):
            a, b = np.exp(theta[0]), np.exp(theta[1])
            nu, tau = theta[2], np.exp(theta[3])
            tt = t - delta
            Ft = float(nl_cdf_s(tt, a, b, nu, tau))
            St = 1.0 - Ft
            if St < 1e-9:
                return None
            mom = nl_trunc_central(a, b, nu, tau, tt)
            if mom is None or not (mom[2] > 1e-10):
                return None
            _, m, mu2, mu3, mu4 = mom
            sd = np.sqrt(mu2)
            rq = (nl_cdf_s(yq - delta, a, b, nu, tau) - Ft) / St - QARR
            return np.concatenate(([m + delta, sd, mu3 / sd**3, mu4 / mu2**2] - mtar, rq))
    else:
        def resid(theta, delta=0.0):
            p = xm._unpack(theta)
            tt = t - delta
            Ft = float(xm.mix_cdf(tt, *p))
            St = float(xm.mix_sf(tt, *p))
            if St < 1e-9:
                return None
            mom = mix_trunc_central(p, tt)
            if mom is None or not (mom[2] > 1e-10):
                return None
            _, m, mu2, mu3, mu4 = mom
            sd = np.sqrt(mu2)
            rq = (xm.mix_cdf(yq - delta, *p) - Ft) / St - QARR
            return np.concatenate(([m + delta, sd, mu3 / sd**3, mu4 / mu2**2] - mtar, rq))
    return resid


def _level_dir(resid, theta):
    """d = dr/d(delta) at delta = 0, by central difference. None if either side degenerates."""
    rp, rm = resid(theta, DELTA_H), resid(theta, -DELTA_H)
    if rp is None or rm is None:
        return None
    d = (rp - rm) / (2.0 * DELTA_H)
    return d if np.all(np.isfinite(d)) else None


def make_qfun(resid, W, project=True):
    """Q(theta) = r'Wr with the level direction concentrated out -- the fitters' gmm_pen
    contract (a scalar in theta, +inf where degenerate).

    With `project` (the default, and the whole point of this module -- see the docstring) the
    returned value is the profiled criterion min_delta r(theta,delta)'W r(theta,delta), which
    for a residual linear in delta is exactly the W-orthogonal projection

        r0'Wr0 - (d'Wr0)^2 / (d'Wd)

    a rank-(NR-1) form carrying only shape. `project=False` gives the raw criterion, which
    DOES speak to the level and therefore fights the aggregate constraint -- for diagnostics
    only. Degenerate cases fall back to the unprojected value rather than to inf: a direction
    we cannot measure is one we cannot remove, and an inf there would eject an otherwise fine
    cell from the fit."""
    def qfun(theta):
        r0 = resid(theta)
        if r0 is None or not np.all(np.isfinite(r0)):
            return np.inf
        q0 = float(r0 @ W @ r0)
        if not project:
            return q0
        d = _level_dir(resid, theta)
        if d is None:
            return q0
        dWd = float(d @ W @ d)
        if not (dWd > 0.0):
            return q0
        return q0 - float(d @ W @ r0) ** 2 / dWd
    return qfun


def level_wedge(resid, W, theta):
    """The concentrated delta-hat: the log-point gap between the published (GKSW W-2) concept
    and the fitted (EPUF covered-earnings) one for this cell. A BYPRODUCT of the projection,
    reported for diagnosis -- nothing in the fit consumes it. NaN where it is not measurable."""
    r0 = resid(theta)
    if r0 is None or not np.all(np.isfinite(r0)):
        return float("nan")
    d = _level_dir(resid, theta)
    if d is None:
        return float("nan")
    dWd = float(d @ W @ d)
    return -float(d @ W @ r0) / dWd if dWd > 0.0 else float("nan")
# --------------------------------------------------- model-implied weight matrix
def sigma_tilde(logpdf, cdf, t, center):
    """Per-observation sampling covariance Sigma~ (10x10) of the DATA-side statistics,
    under the model's truncated law, by influence functions on a dense grid:
      meanlog: y - m;  sdlog: ((y-m)^2 - mu2)/(2 sd);
      skew:  psi_mu3/mu2^1.5 - 1.5 g1 psi_mu2/mu2;  kurt: psi_mu4/mu2^2 - 2 g2 psi_mu2/mu2
      inverted quantile condition: 1{y <= y_q} - q  (empirical-process IF, so the
      quantile block is min(qi,qj) - qi qj exactly, density-free).
    Runs ONCE per cell per outer GMM iteration -- never inside the optimizer."""
    ylo = _bracket(cdf, 1e-9, center, 1.0, up=False)
    yhi = _bracket(cdf, 1.0 - 1e-9, center, 1.0, up=True)
    Ft = float(cdf(t))
    glo = max(ylo, t)
    y = np.linspace(glo, yhi, 4001)
    w = np.exp(logpdf(y))
    w[0] *= 0.5; w[-1] *= 0.5
    w /= w.sum()
    m = w @ y
    d = y - m
    mu2, mu3, mu4 = w @ d**2, w @ d**3, w @ d**4
    sd = np.sqrt(mu2)
    g1, g2 = mu3 / sd**3, mu4 / mu2**2
    psi2 = d**2 - mu2
    IF = [d,
          psi2 / (2.0 * sd),
          (d**3 - mu3 - 3.0 * mu2 * d) / mu2**1.5 - 1.5 * g1 * psi2 / mu2,
          (d**4 - mu4 - 4.0 * mu3 * d) / mu2**2 - 2.0 * g2 * psi2 / mu2]
    for q in QUANTS:
        v = brentq(lambda z: cdf(z) - (Ft + q * (1.0 - Ft)), glo - 1.0, yhi + 1.0)
        IF.append((y <= v).astype(float) - q)
    IF = np.vstack(IF)
    return (IF * w) @ IF.T


def row_dists(sex, r):
    """(logpdf, cdf, center) callables for a fitted-result dict."""
    if sex == 1:
        a, b, nu, tau = r["alpha"], r["beta"], r["nu"], r["tau"]
        return (lambda y: nl_logpdf_s(y, a, b, nu, tau),
                lambda y: nl_cdf_s(y, a, b, nu, tau), nu)
    p = (r["mu1"], r["mu2"], r["sig1"], r["sig2"], r["w"])
    return (lambda y: xm.mix_logpdf(y, *p),
            lambda y: xm.mix_cdf(y, *p), r["w"] * r["mu1"] + (1 - r["w"]) * r["mu2"])


def weight_matrix(Sig, n_guv, n_epuf):
    """W = n_guv Sigma~^{-1} / (2 n_epuf): the scaling that makes lam=0.5 the composite
    likelihood (docstring). Eigenvalue-floored inverse: 10 statistics of a 4-5 parameter
    family are near-collinear in places, and a raw inverse would blow those directions up."""
    Sig = 0.5 * (Sig + Sig.T)
    vals, vecs = np.linalg.eigh(Sig)
    vals = np.maximum(vals, EIG_FLOOR * vals.max())
    return (vecs / vals) @ vecs.T * (n_guv / (2.0 * n_epuf))


