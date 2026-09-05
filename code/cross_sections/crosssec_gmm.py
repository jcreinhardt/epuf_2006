#!/usr/bin/env python
"""Per-cell MLE+GMM fit of the earnings cross-sections: a convex combination of the
censored log-likelihood and a truncation-aware, ITERATED GMM criterion on the Guvenen
(GKSW) sel0 cohort x age targets.

For every (year, sex, single-year age) cell the objective is

    (1 - lam) * negll(theta) / n  +  lam * r(theta)' W r(theta)

where negll is the doubly-censored EPUF log-likelihood (dPlN for men, lognormal
mixture for women -- crosssec_fit, unchanged), r is the 10-vector of residuals against
the published sel0 functionals of the matching guv cell (meanlog/sdlog/skewlog/kurtlog
+ p10/p25/p50/p75/p90/p98), and W is a weight matrix. Cells with no guv counterpart
(years 1951-56, ages outside 25-55) carry the pure censored MLE as their data term, so
the output CSV is a complete surface.

BY DEFAULT the per-cell fits above are only stage 0: the estimator is a JOINT SMOOTHED
solve per year (--no-smooth reproduces the independent per-cell fits). In the summed
units the fitters minimize, the year's joint objective is

    J = Sum_c [ (1-lam) negll_c + lam n_c Q_c ]  +  rho Sum_a huber(sqrt(Omega) D2 g_a)

-- every cell's composite data term plus the SAME robust (Huber) second-difference
roughness penalty along age, on the same regime-invariant functionals g(theta), reusing
crosssec_mle.py's machinery wholesale: stage 0 fits plus top-K g-deduped basin
candidates at each guv cell's FROZEN final W; Omega and rho frozen once, globally, from
the stage-0 fits; Viterbi basin selection at the target rho (node cost = the cell's data
term in J); rho-continuation Gauss-Seidel sweeps. The guv-anchored cells are stiff (10
precise statistics barely move under the penalty), so smoothing mostly propagates their
consistency ACROSS the window edges (ages 25/55, the 1957 diagonal) into the MLE-only
cells instead of averaging noise with noise. The same bridging drags a slice of the
W-2-vs-covered level wedge a few ages past the edge -- the price of continuity there.

UNIT CARE: the fitters add smooth_pen AFTER the gmm_pen convex combination, and the gmm
objective is per-observation, so a guv cell's Gauss-Seidel subproblem is J_c / n_c and
its wvec is the summed-units weight divided by n_c; MLE-only cells take it undivided.
Non-guv cells refit with mean_pen=(0, 0) -- a zero-strength pull whose only effect is
the structural ALPHA_MIN floor -- so every cell of the smoothed surface keeps a finite
uncapped mean even in the tight-cap years.

GUV-ONLY YEARS 2007-13: the guv targets extend past the EPUF microdata, so those years'
ages-25-55 cells are fit by PURE GMM -- minimize r'Wr directly over theta with the
fitters' structural boxes (no data to censor; the in-sample W's scalar n factor cannot
move a pure-GMM argmin, so W is the plain floored inverse of Sigma~), iterated weighting
as in-sample, warm-seeded from the final 2006 surface. Unlike the wage-index rigid shift
of extrapolate_params.py this captures the actual 2008-09 moment movements, but the cells
are GKSW-W-2-denominated (like every lam=1 quantity) and cover NO ages outside 25-55;
their rows carry n=0 and NaN censoring fields.

Other differences from the canonical pipeline: cells enter at MIN_N=500 (not 1000) --
the smoothing penalty is what makes small cells usable -- and the default smoothing is
SMOOTH_FRAC_GMM = 1e-3, 10x canonical: the canonical value was capped by the eta
interaction, absent here, and the guv-covered region shows the truth is much smoother
than unsmoothed censored MLE suggests. Gauss-Seidel refits run at REFIT_OPTS (tighter
than WARM_OPTS, whose gtol is calibrated to summed-likelihood scale and can stall on the
per-observation composite objective).

DELIBERATELY ABSENT (vs crosssec_mle.py, --mode mle): the per-year aggregate-mean
constraint. Nothing here pins the uncapped aggregate: smoothing log-scale g slots biases
level aggregates DOWN (Jensen), and inside the guv window levels follow GKSW's W-2
concept anyway. Don't feed this surface to EPUF-denominated aggregate validation
without remembering both.

THE RESIDUAL VECTOR IS FULLY CLOSED FORM (no quadrature inside the optimizer):
  - sel0 drops observations below Ymin(t) = 260 x nominal minwage (same-year deflator
    cancels), so every model functional is of the TRUNCATED law X | X >= Ymin.
  - quantiles enter INVERTED, as CDF conditions: the published real-2013$ quantile p_q
    is deflated to nominal logs y_q and the residual is
    (F(y_q) - F(t)) / (1 - F(t)) - q, with t = log Ymin -- nl_cdf / mix_cdf, smooth
    in theta, no root-finding.
  - the four truncated log-moments are closed form. Mixture: truncated-normal moment
    recursions per component. dPlN: the Normal-Laplace density is a sum of two
    exponentially-tilted normal-CDF terms (Reed-Jorgensen), and integration by parts
    reduces each centered partial moment to the recursion _nl_trunc_central below,
    whose only primitives are Phi, phi and standard-normal upper partial moments.
    Every exp x Phi product is assembled in logs (log_ndtr), so tilts like
    e^{b^2/2} at beta*tau ~ 20 cannot overflow. Validated at startup against a dense
    quadrature (_check_closed_forms).

ITERATED GMM WEIGHTING. The published guv files carry no cell counts or covariances,
so W is estimated from the MODEL, iteratively:
  - iteration 0: "uniform-ish" diagonal W from fixed scales (MSCALE per moment,
    q(1-q) per quantile condition -- the latter is already each quantile condition's
    exact asymptotic variance x n).
  - then, repeatedly (--gmm-iters, default 2): at the current theta-hat, compute the
    model-implied sampling covariance Sigma~ of the data statistics by influence
    functions on a dense grid of the truncated law (moment IFs are the standard
    polynomial ones; the inverted quantile residuals have empirical-process IF
    1{y<=y_q} - q, giving the min(qi,qj)-qi*qj block), invert with an eigenvalue
    floor, and refit with the new W (fresh multi-start each pass).
  W is FROZEN during each inner solve -- iterated GMM's outer loop is where it moves --
  so the grid-based Sigma~ never touches the analyticity of the inner objective.
  The guv cell size is proxied by EPUF's own post-screen cell count (both are 1%
  samples; GKSW's commerce-and-industry frame is close enough for a weighting).

SCALING / lam SEMANTICS: W = n_guv * Sigma~^{-1} / (2 n_epuf), so at lam = 0.5 the
objective is proportional to  negll + (1/2) r' [Sigma~/n_guv]^{-1} r  -- exactly the
composite likelihood that treats the published statistics as Gaussian observations at
their estimated precision. lam tilts away from that anchor; lam=0 is the raw MLE and
lam=1 is pure GMM (the likelihood is ignored in guv-covered cells) -- a diagnostic
bound on what the parametric family can do, not a production surface: at lam=1 the
parameters describe GKSW's W-2 concept, not EPUF covered earnings, and clash with the
pure-MLE cells outside the guv window. Keep its output out of the canonical CSV via
--out (convention: cross_section_params_guvgmm_lam1.csv).

CAVEAT (by construction, not a bug): the guv targets embed GKSW's W-2
commerce-and-industry earnings concept, ~7-10% ABOVE EPUF covered earnings in the
early decades. Efficient weighting makes this BIND HARDER: meanlog's sampling sd is
~sigma/sqrt(n) ~ 0.008, so the concept wedge is dozens of sd's and the GMM term will
spend fit freely to close it. Levels are not concept-robust; the shape functionals are.

  python code/cross_sections/estimate_cross_sections.py --mode mle-gmm [--jobs N] [--lam L]
        [--gmm-iters K] [--out CSV] [--no-smooth] [--rho R] [--smooth-frac F]
    -> output/cross_sections/cross_section_params_guvgmm_smoothed.csv  (default)
       output/cross_sections/cross_section_params_guvgmm.csv           (--no-smooth default)
  (both include the pure-GMM 2007-13 rows)
"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import csv
import sys
import time
from math import comb
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
from scipy.special import ndtr, log_ndtr
from scipy.optimize import brentq, minimize

import crosssec_fit as cf
import crosssec_mle as ec
from crosssec_mle import (load_year, basin_starts,
                                     freeze_omega_rho, viterbi, smooth_pen)
from guv_targets import (load_guv, load_deflator, min_wage, sel0_threshold,
                         nl_logpdf_s, nl_cdf_s, _bracket, QUANTS, QCOLS)

YEARS = range(1951, 2007)
GUV_ONLY_YEARS = range(2007, 2014)   # guv targets but NO EPUF microdata: pure-GMM cells
LAM_DEFAULT = 0.5           # = the composite-likelihood weighting, see docstring
GMM_ITERS_DEFAULT = 2       # weight-matrix updates after the iteration-0 fit
MIN_N = 500                 # cell floor for THIS pipeline (canonical keeps 1000): the
                            # smoothing penalty is exactly what makes 500-obs cells usable
SMOOTH_FRAC_GMM = 1e-3      # default rho calibration, 10x the canonical SMOOTH_FRAC. The
                            # canonical value was capped by the eta interaction (smoothing may
                            # not push the aggregate below the benchmark); with no mean
                            # constraint here the binding limit is only smearing genuine
                            # regime switches, which the Huber loss protects. Override with
                            # --smooth-frac / --rho.
GS_PASSES = 3               # Gauss-Seidel passes per rho step (canonical env default is 2)
REFIT_OPTS = dict(maxiter=100, ftol=1e-9, gtol=1e-5)   # GS refits: tighter than WARM_OPTS --
                            # the composite objective is per-observation scale in guv cells,
                            # where WARM's gtol=1e-3 can stop a refit before it moves at all
OUT = Path("output/cross_sections/cross_section_params_guvgmm.csv")
OUT_SMOOTH = Path("output/cross_sections/cross_section_params_guvgmm_smoothed.csv")


def cells_by_age(df):
    """As estimate_cross_sections.cells_by_age but at THIS pipeline's MIN_N floor."""
    return {sex: {int(a): sub["earnings"].to_numpy(dtype=float)
                  for a, sub in df.loc[df["sex"] == sex].groupby("age")
                  if len(sub) >= MIN_N}
            for sex in (1, 2)}

# Iteration-0 diagonal scales: a "meaningful mismatch" per moment residual, and the
# exact asymptotic variance q(1-q) per (inverted) quantile condition. Moments in the
# order [meanlog, sdlog, skewlog, kurtlog].
MSCALE = np.array([0.05, 0.05, 0.10, 0.30])
QARR   = np.array(QUANTS)
SQRT2PI = np.sqrt(2.0 * np.pi)
EIG_FLOOR = 1e-9            # relative eigenvalue floor when inverting Sigma~

COLS = ["year", "sex", "age", "model", "n", "n_low", "n_high", "negll", "converged",
        "alpha", "beta", "nu", "tau", "mu1", "mu2", "sig1", "sig2", "w",
        "lowc", "highc", "p_low_model", "p_high_model", "lam", "gmm_q", "gmm_chi2",
        "has_guv"]


# ------------------------------------------------------------------ guv targets
def guv_targets():
    """{(year, sex, age): (t_nominal_log, moment_targets[4], quantile_log_targets[6])},
    everything converted to NOMINAL log dollars via GKSW's own PCE deflator."""
    guv, defl = load_guv(), load_deflator()
    tab = {}
    for r in guv.itertuples():
        y = int(r.year)
        if y not in YEARS and y not in GUV_ONLY_YEARS:
            continue
        lfac = np.log(defl[y])                      # log(nominal -> real-2013 factor)
        t = np.log(sel0_threshold(y))               # the sel0 screen, nominal logs
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
         lambda y: cf.mix_logpdf(y, 9.6, 8.1, 0.55, 1.25, 0.62),
         lambda y: cf.mix_cdf(y, 9.6, 8.1, 0.55, 1.25, 0.62), (8.1 - 12.0, 9.6 + 12.0)),
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
def make_resid_dpln(t, mtar, yq):
    """r(theta), 10-vector, for a men's cell; theta = [log a, log b, nu, log tau]."""
    def resid(theta):
        a, b = np.exp(theta[0]), np.exp(theta[1])
        nu, tau = theta[2], np.exp(theta[3])
        Ft = float(nl_cdf_s(t, a, b, nu, tau))
        St = 1.0 - Ft
        if St < 1e-9:
            return None
        mom = nl_trunc_central(a, b, nu, tau, t)
        if mom is None or not (mom[2] > 1e-10):
            return None
        _, m, mu2, mu3, mu4 = mom
        sd = np.sqrt(mu2)
        rq = (nl_cdf_s(yq, a, b, nu, tau) - Ft) / St - QARR
        return np.concatenate(([m, sd, mu3 / sd**3, mu4 / mu2**2] - mtar, rq))
    return resid


def make_resid_mix(t, mtar, yq):
    """r(theta), 10-vector, for a women's cell; theta as in crosssec_fit._unpack."""
    def resid(theta):
        p = cf._unpack(theta)
        Ft = float(cf.mix_cdf(t, *p))
        St = float(cf.mix_sf(t, *p))
        if St < 1e-9:
            return None
        mom = mix_trunc_central(p, t)
        if mom is None or not (mom[2] > 1e-10):
            return None
        _, m, mu2, mu3, mu4 = mom
        sd = np.sqrt(mu2)
        rq = (cf.mix_cdf(yq, *p) - Ft) / St - QARR
        return np.concatenate(([m, sd, mu3 / sd**3, mu4 / mu2**2] - mtar, rq))
    return resid


def make_qfun(resid, W):
    """Q(theta) = r' W r; the fitters' gmm_pen contract (inf where degenerate)."""
    def qfun(theta):
        r = resid(theta)
        if r is None or not np.all(np.isfinite(r)):
            return np.inf
        return float(r @ W @ r)
    return qfun


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
    return (lambda y: cf.mix_logpdf(y, *p),
            lambda y: cf.mix_cdf(y, *p), r["w"] * r["mu1"] + (1 - r["w"]) * r["mu2"])


def weight_matrix(Sig, n_guv, n_epuf):
    """W = n_guv Sigma~^{-1} / (2 n_epuf): the scaling that makes lam=0.5 the composite
    likelihood (docstring). Eigenvalue-floored inverse: 10 statistics of a 4-5 parameter
    family are near-collinear in places, and a raw inverse would blow those directions up."""
    Sig = 0.5 * (Sig + Sig.T)
    vals, vecs = np.linalg.eigh(Sig)
    vals = np.maximum(vals, EIG_FLOOR * vals.max())
    return (vecs / vals) @ vecs.T * (n_guv / (2.0 * n_epuf))


# per sex: fitter, warm-start packer, residual builder; and the g-map for the penalty
SEXES = {1: (cf.fit_dpln,    cf.dpln_theta, make_resid_dpln),
         2: (cf.fit_mixture, cf.mix_theta,  make_resid_mix)}
GFUN  = {1: cf.g_dpln, 2: cf.g_mix}


# ------------------------------------------------------------------ per-year workers
def _dedupe(fits, pack, gfun, logcap, qf, lam, n):
    """Top-K candidates deduped in g-space (as estimate_cross_sections.stage0_year). The
    stored 'negll' is the cell's DATA TERM in the joint objective's summed units --
    (1-lam) negll + lam n q for guv cells, plain negll otherwise -- which is what viterbi
    prices against rho x roughness."""
    ent = []
    for r in fits:
        th = pack(r)
        if qf is None:
            data = r["negll"]
        else:
            q = qf(th)
            data = (1.0 - lam) * r["negll"] + lam * n * q if np.isfinite(q) else np.inf
        ent.append(dict(theta=list(th), negll=float(data), g=gfun(th, logcap), row=r))
    uniq = []
    for e in sorted(ent, key=lambda e: e["negll"]):
        if all(np.linalg.norm(e["g"] - u["g"]) > ec.DEDUPE for u in uniq):
            uniq.append(e)
        if len(uniq) >= ec.K_CAND:
            break
    return uniq


def fit_year(args):
    """Stage 0: independent fits for every cell of one year. Guv-covered cells run the
    iterated GMM: fit at the diagonal iteration-0 W, then (gmm_iters times) recompute the
    model-implied W at theta-hat and refit with a fresh multi-start. With want_cand, also
    return the joint-solve plumbing: each guv cell's FROZEN final W, and per cell the
    top-K basin candidates evaluated at it (non-guv candidates refit with mean_pen=(0,0)
    so the alpha floor holds everywhere the smoothed surface will live)."""
    year, lam, gmm_iters, tgt_year, want_cand = args
    t0 = time.time()
    df = load_year(year)
    highc = float(df["earnings"].max()) - cf.HIGH_MARGIN
    logcap = np.log(highc)
    by_age = cells_by_age(df)
    Sig0 = np.diag(np.concatenate((MSCALE ** 2, QARR * (1.0 - QARR))))
    out, qs = [], []
    cand, Wmat = {sex: {} for sex in SEXES}, {}
    for sex, (fit, pack, make) in SEXES.items():
        gfun = GFUN[sex]
        for a in sorted(by_age[sex]):
            x = by_age[sex][a]
            tgt = tgt_year.get((sex, a))
            if tgt is None:
                r = fit(x, cf.LOWC, highc)
                out.append(dict(r, year=year, sex=sex, age=a, lowc=cf.LOWC,
                                highc=highc, lam=0.0, gmm_q=float("nan"),
                                gmm_chi2=float("nan"), has_guv=0))
                if want_cand:
                    seeds = [pack(r)] + basin_starts(sex, x)
                    fits = [fit(x, cf.LOWC, highc, start=s, mean_pen=(0.0, 0.0))
                            for s in seeds]
                    cand[sex][a] = _dedupe(fits, pack, gfun, logcap, None, lam, x.size)
                continue
            t, mtar, yq = tgt
            resid = make(t, mtar, yq)
            n_guv = int((x >= np.exp(t)).sum())     # EPUF post-screen count as guv-n proxy
            W = weight_matrix(Sig0, n_guv, x.size)
            for j in range(gmm_iters + 1):
                r = fit(x, cf.LOWC, highc, gmm_pen=(lam, make_qfun(resid, W)))
                if j < gmm_iters:
                    logpdf, cdf, center = row_dists(sex, r)
                    W = weight_matrix(sigma_tilde(logpdf, cdf, t, center), n_guv, x.size)
            qf = make_qfun(resid, W)
            gq = qf(pack(r))
            # gq = r'Wr = (n_guv/2n) r'Sigma~^{-1} r; 2n*gq recovers the chi-square-scale
            # statistic n_guv r'Sigma~^{-1} r (~E[chi2(10)]=10 were family+concept correct)
            chi2 = 2.0 * x.size * gq
            qs.append(chi2)
            out.append(dict(r, year=year, sex=sex, age=a, lowc=cf.LOWC, highc=highc,
                            lam=lam, gmm_q=gq, gmm_chi2=chi2, has_guv=1))
            if want_cand:
                Wmat[(sex, a)] = W
                seeds = [pack(r)] + basin_starts(sex, x)
                fits = [fit(x, cf.LOWC, highc, start=s, gmm_pen=(lam, qf))
                        for s in seeds]
                cand[sex][a] = _dedupe(fits, pack, gfun, logcap, qf, lam, x.size)
    med_q = float(np.median(qs)) if qs else float("nan")
    ntot = sum(x.size for sex in SEXES for x in by_age[sex].values())
    meta = (dict(year=year, highc=highc, logcap=logcap, ntot=ntot, cand=cand, W=Wmat)
            if want_cand else None)
    return year, out, dict(sec=time.time() - t0, n_guv=len(qs), med_q=med_q), meta


def solve_year(args):
    """The joint smoothed solve for one year at frozen Omega / per-observation rho grid:
    Viterbi basin selection at the target rho, then rho-continuation Gauss-Seidel sweeps
    (estimate_cross_sections stages 1-2). No eta stage: there is no aggregate-mean
    constraint here, by design (module docstring)."""
    meta, Omega, rho_grid, lam, tgt_year = args
    t0 = time.time()
    year, highc, logcap = meta["year"], meta["highc"], meta["logcap"]
    cand = meta["cand"]
    by_age = cells_by_age(load_year(year))
    ages = {sex: sorted(cand[sex]) for sex in SEXES}
    rho_grid = [r * meta["ntot"] for r in rho_grid]   # per-obs -> summed-likelihood units
    # rebuild the (unpicklable) per-cell GMM criteria from the targets + frozen W
    qf = {}
    for (sex, a), W in meta["W"].items():
        t, mtar, yq = tgt_year[(sex, a)]
        qf[(sex, a)] = make_qfun(SEXES[sex][2](t, mtar, yq), W)
    nsolve = [0]

    sel = {sex: viterbi(cand[sex], ages[sex], Omega[sex], rho_grid[-1]) for sex in SEXES}
    theta = {sex: {a: list(cand[sex][a][sel[sex][a]]["theta"]) for a in ages[sex]}
             for sex in SEXES}
    g = {sex: {a: cand[sex][a][sel[sex][a]]["g"] for a in ages[sex]} for sex in SEXES}
    rows = {sex: {a: cand[sex][a][sel[sex][a]]["row"] for a in ages[sex]} for sex in SEXES}

    def gs_solve(rho, passes):
        for p in range(passes):                 # single-direction passes, alternating
            maxch = 0.0
            for sex, (fit, pack, _) in SEXES.items():
                gfun = GFUN[sex]
                order = ages[sex] if p % 2 == 0 else ages[sex][::-1]
                for a in order:
                    x = by_age[sex][a]
                    sp = smooth_pen(g[sex], a, ages[sex], Omega[sex], rho)
                    if (sex, a) in qf:
                        if sp is not None:
                            sp = (sp[0] / x.size, sp[1])   # summed -> per-obs units
                        r = fit(x, cf.LOWC, highc, start=theta[sex][a],
                                gmm_pen=(lam, qf[(sex, a)]), smooth_pen=sp,
                                opts=REFIT_OPTS)
                    else:
                        r = fit(x, cf.LOWC, highc, start=theta[sex][a],
                                mean_pen=(0.0, 0.0), smooth_pen=sp, opts=REFIT_OPTS)
                    nsolve[0] += 1
                    nth = pack(r)
                    ngv = gfun(nth, logcap)
                    maxch = max(maxch, float(np.max(np.abs(ngv - g[sex][a]))))
                    theta[sex][a], g[sex][a], rows[sex][a] = nth, ngv, r
            if maxch < ec.GS_TOL:
                break

    for rho in rho_grid:
        gs_solve(rho, GS_PASSES)

    out = []
    for sex, (fit, pack, _) in SEXES.items():
        for a in ages[sex]:
            r = rows[sex][a]
            key = (sex, a)
            if key in qf:
                gq = qf[key](pack(r))
                out.append(dict(r, year=year, sex=sex, age=a, lowc=cf.LOWC, highc=highc,
                                lam=lam, gmm_q=gq, gmm_chi2=2.0 * r["n"] * gq, has_guv=1))
            else:
                out.append(dict(r, year=year, sex=sex, age=a, lowc=cf.LOWC, highc=highc,
                                lam=0.0, gmm_q=float("nan"), gmm_chi2=float("nan"),
                                has_guv=0))
    return year, out, dict(sec=time.time() - t0, nsolve=nsolve[0])


# ---------------------------------------------------- guv-only years (2007-13)
def _theta_row(sex, th):
    """Parameter dict (fitter-result shape) from an internal theta."""
    if sex == 1:
        return dict(model="dpln", alpha=float(np.exp(th[0])), beta=float(np.exp(th[1])),
                    nu=float(th[2]), tau=float(np.exp(th[3])))
    mu1, mu2, s1, s2, w = cf._unpack(th)
    if mu1 < mu2:                       # label: component 1 = higher mean
        mu1, mu2, s1, s2, w = mu2, mu1, s2, s1, 1 - w
    return dict(model="mixture", mu1=float(mu1), mu2=float(mu2),
                sig1=float(s1), sig2=float(s2), w=float(w))


def _guv_seeds(sex, mtar, warm):
    """Multi-start seeds for a data-free cell: the previous year's solution (when given)
    plus target-moment spreads (the truncated meanlog/sdlog as rough location/scale)."""
    m, s = mtar[0], max(mtar[1], 0.2)
    if sex == 1:
        seeds = [[np.log(a0), np.log(3.0), m, np.log(s)] for a0 in (1.5, 3.0, 20.0)]
    else:
        ls = np.log(max(0.7 * s - cf.SIG_FLOOR, 1e-3))
        seeds = [[m + d * s, m - d * s, ls, ls, np.log(w0 / (1 - w0))]
                 for w0, d in ((0.3, 0.9), (0.5, 0.4), (0.7, 0.9))]
    return ([list(warm)] if warm is not None else []) + seeds


def _pure_gmm_min(sex, qfun, seeds):
    """Minimize r'Wr directly over theta with the fitters' structural boxes -- the
    data-free counterpart of a lam=1 fit (there is no microdata to censor)."""
    if sex == 1:
        bnds = [(np.log(cf.ALPHA_MIN), np.log(500.0)), (np.log(0.05), np.log(500.0)),
                (cf.NU_LO, cf.NU_HI), (np.log(cf.TAU_MIN), np.log(cf.TAU_MAX))]
    else:
        lo, hi = np.log(cf.SIG_MIN - cf.SIG_FLOOR), np.log(cf.SIG_MAX - cf.SIG_FLOOR)
        bnds = [(4.0, 13.0), (4.0, 13.0), (lo, hi), (lo, hi), (None, None)]
    best = None
    for s in seeds:
        r = minimize(qfun, s, method="L-BFGS-B", bounds=bnds, options=cf.COLD_OPTS)
        if best is None or r.fun < best.fun:
            best = r
    return best


def fit_guv_year(args):
    """One guv-only year (2007-13): every ages-25-55 cell fit by PURE GMM with iterated
    model-implied weighting. The in-sample W's scalar factor n_guv/(2n) cannot affect a
    pure-GMM argmin, so W here is the plain eigenvalue-floored inverse of Sigma~ and only
    Sigma~'s STRUCTURE matters. Warm-seeded from the 2006 surface; chi2 is reported with
    the 2006 EPUF post-screen count as the n_guv proxy. Output rows carry n=0 and NaN
    censoring fields (there is no microdata), and are GKSW-W-2-denominated like every
    guv-anchored quantity -- see the docstring caveat."""
    year, gmm_iters, tgt_year, warm, nguv = args
    t0 = time.time()
    Sig0 = np.diag(np.concatenate((MSCALE ** 2, QARR * (1.0 - QARR))))
    out, qs = [], []
    for (sex, a), (t, mtar, yq) in sorted(tgt_year.items()):
        resid = SEXES[sex][2](t, mtar, yq)
        W = weight_matrix(Sig0, 1.0, 0.5)          # scalar factor = 1: plain inverse
        seeds = _guv_seeds(sex, mtar, warm.get((sex, a)))
        for j in range(gmm_iters + 1):
            best = _pure_gmm_min(sex, make_qfun(resid, W), seeds)
            row = _theta_row(sex, best.x)
            if j < gmm_iters:
                logpdf, cdf, center = row_dists(sex, row)
                W = weight_matrix(sigma_tilde(logpdf, cdf, t, center), 1.0, 0.5)
                seeds = [list(best.x)]
        gq = float(make_qfun(resid, W)(best.x))
        chi2 = nguv.get((sex, a), 10000) * gq      # W = Sigma~^-1, so n r'Wr is the stat
        qs.append(chi2)
        out.append(dict(row, year=year, sex=sex, age=a, n=0, n_low=0, n_high=0,
                        negll=float("nan"), converged=bool(best.success),
                        lowc=float("nan"), highc=float("nan"),
                        p_low_model=float("nan"), p_high_model=float("nan"),
                        lam=1.0, gmm_q=gq, gmm_chi2=chi2, has_guv=1))
    med_q = float(np.median(qs)) if qs else float("nan")
    return year, out, dict(sec=time.time() - t0, n_guv=len(qs), med_q=med_q)


# ------------------------------------------------------------------ driver
def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: (r["year"], r["sex"], r["age"]))
    with path.open("w", newline="") as fh:
        wtr = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        wtr.writeheader()
        wtr.writerows(rows)


def main(jobs=None, lam=LAM_DEFAULT, gmm_iters=GMM_ITERS_DEFAULT, out=None,
         smooth=True, rho=None, smooth_frac=None):
    if not (0.0 <= lam <= 1.0):
        sys.exit(f"--lam must be in [0, 1], got {lam}")
    out = (OUT_SMOOTH if smooth else OUT) if out is None else out
    _check_closed_forms()
    t0 = time.time()
    targets = guv_targets()
    per_year = {y: {(s, a): v for (yy, s, a), v in targets.items() if yy == y}
                for y in YEARS}
    print(f"=== stage 0: iterated MLE+GMM per-cell fits: lam={lam}, {gmm_iters} weight "
          f"updates, {len(targets)} guv target cells ===", flush=True)
    args = [(y, lam, gmm_iters, per_year[y], smooth) for y in YEARS]
    rows, metas = [], []
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        for year, yr_rows, tm, meta in ex.map(fit_year, args):
            rows.extend(yr_rows)
            metas.append(meta)
            print(f"  {year}: {len(yr_rows):>3} cells ({tm['n_guv']} with guv targets)  "
                  f"median chi2={tm['med_q']:.0f}  {tm['sec']:.1f}s", flush=True)
    if smooth:
        if smooth_frac is not None:
            ec.SMOOTH_FRAC = smooth_frac    # freeze_omega_rho reads its module's global
        else:
            ec.SMOOTH_FRAC = SMOOTH_FRAC_GMM
        Omega, rho0 = freeze_omega_rho(metas)
        rho_t = rho0 if rho is None else rho
        rho_grid = list(np.geomspace(rho_t * ec.RHO0_START, rho_t, ec.RHO_STEPS))
        print(f"=== Omega frozen; rho0={rho0:.3g} target={rho_t:.3g} "
              f"grid={[f'{r:.2g}' for r in rho_grid]} ===", flush=True)

        print("=== joint smoothed solve (Viterbi + rho-continuation Gauss-Seidel) ===",
              flush=True)
        args2 = [(m, Omega, rho_grid, lam, per_year[m["year"]]) for m in metas]
        rows = []
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            for year, yr_rows, tm in ex.map(solve_year, args2):
                rows.extend(yr_rows)
                print(f"  {year}: {len(yr_rows):>3} cells  {tm['nsolve']} solves  "
                      f"{tm['sec']:.1f}s", flush=True)

    # guv-only years 2007-13: pure-GMM cells, warm-seeded off the final 2006 surface
    print("=== guv-only years (pure GMM, no EPUF) ===", flush=True)
    warm = {(r["sex"], r["age"]): SEXES[r["sex"]][1](r) for r in rows
            if r["year"] == 2006}
    by06 = cells_by_age(load_year(2006))
    thr06 = sel0_threshold(2006)
    nguv = {(s, a): int((x >= thr06).sum()) for s in by06 for a, x in by06[s].items()}
    ext = {y: {(s, a): v for (yy, s, a), v in targets.items() if yy == y}
           for y in GUV_ONLY_YEARS}
    args3 = [(y, gmm_iters, ext[y], warm, nguv) for y in GUV_ONLY_YEARS]
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        for year, yr_rows, tm in ex.map(fit_guv_year, args3):
            rows.extend(yr_rows)
            print(f"  {year}: {len(yr_rows):>3} cells  median chi2={tm['med_q']:.0f}  "
                  f"{tm['sec']:.1f}s", flush=True)

    write_csv(out, rows)
    print(f"\nwrote {len(rows)} rows -> {out}   total {time.time() - t0:.0f}s")
    print("(guv cells anchored at their frozen W; 2007-13 = pure GMM, W-2-denominated, "
          "ages 25-55 only; NO aggregate-mean constraint -- uncapped aggregates are "
          "unpinned by design)")
