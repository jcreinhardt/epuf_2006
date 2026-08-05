#!/usr/bin/env python
"""Shared cross-section fitters: censored MLE of an earnings distribution for one
(year, sex) slice of the EPUF microdata.

Two models, one skeleton (doubly Type-I censored log-likelihood on log-earnings):
  - fit_dpln    -- double Pareto-lognormal (Normal-Laplace body+tails); used for men.
  - fit_mixture -- two-component lognormal mixture, 5 free params; used for women.

Both slice a single cross-section with load_earnings(year, sex), then fit the
interior between LOWC and a year-specific HIGHC = taxmax(year) - HIGH_MARGIN.
Everything is closed form (weighted normal pdf/cdf, or Normal-Laplace via Mills
ratios), so the censored likelihood has no integrals. duckdb via the CLI, per
repo convention.
"""
import subprocess
import numpy as np
from scipy.special import erfcx, ndtr
from scipy.optimize import minimize, fsolve

DB          = "processed_data/ssa.duckdb"
LOWC        = 200.0     # left-censoring threshold ($), fixed across years
HIGH_MARGIN = 1000.0    # HIGHC = taxmax(year) - this; absorbs the near-cap collapse spike
SIG_FLOOR   = 0.02      # guard against the mixture sigma->0 likelihood degeneracy
LOG2PI      = np.log(2 * np.pi)
SQRT2, SQRT_HALF_PI = np.sqrt(2.0), np.sqrt(np.pi / 2.0)


# ----------------------------------------------------------------------------- data
def load_earnings(year, sex, age=None):
    """Positive covered earnings for a (year, sex) slice; pass `age` (= year - yob)
    to further restrict to a single-year age cell."""
    age_clause = "" if age is None else f" AND a.year - d.yob={int(age)}"
    q = ("SELECT a.earnings FROM annual a JOIN demographic d USING(id) "
         f"WHERE a.year={int(year)} AND d.sex={int(sex)} AND a.earnings>0{age_clause}")
    out = subprocess.run(["duckdb", DB, "-noheader", "-csv", "-c", q],
                         capture_output=True, text=True, check=True).stdout
    return np.array(out.split(), dtype=float)


def taxmax(year):
    """Statutory taxable maximum for a year = the top-code, recoverable as MAX(earnings)."""
    q = f"SELECT MAX(earnings) FROM annual WHERE year={int(year)}"
    out = subprocess.run(["duckdb", DB, "-noheader", "-csv", "-c", q],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def censor_split(x, lowc, highc):
    """Return (log interior, n_low, n_high) for the doubly-censored likelihood."""
    low, high = x <= lowc, x >= highc
    yi = np.log(x[~(low | high)])
    return yi, int(low.sum()), int(high.sum())


def _hess_diag(f, x0, rel=1e-4):
    """Diagonal of the numerical Hessian of the negll f at the optimum x0 -- the
    observed information per coordinate, in the optimiser's theta space. It is the
    identifiability weight consumed by the smoothing stage (smooth_params.py):
    near-zero along a flat ridge (defer to neighbours), large where sharply pinned."""
    x0 = np.asarray(x0, dtype=float)
    f0 = f(x0)
    out = np.empty_like(x0)
    for i in range(x0.size):
        h = rel * max(abs(x0[i]), 1.0)
        xp = x0.copy(); xp[i] += h
        xm = x0.copy(); xm[i] -= h
        out[i] = (f(xp) - 2.0 * f0 + f(xm)) / (h * h)
    return out


# ------------------------------------------------------------------ dPlN (men)
def _mills(w):                      # Mills ratio (1-Phi)/phi, stable via erfcx
    return SQRT_HALF_PI * erfcx(w / SQRT2)


def _log_phi(z):
    return -0.5 * LOG2PI - 0.5 * z * z


def nl_logpdf(y, a, b, nu, tau):    # Normal-Laplace log-density on log scale
    z = (y - nu) / tau
    return (np.log(a) + np.log(b) - np.log(a + b) + _log_phi(z)
            + np.log(_mills(a * tau - z) + _mills(b * tau + z)))


def nl_cdf(y, a, b, nu, tau):       # Normal-Laplace CDF (scalar thresholds)
    z = (y - nu) / tau
    phi = np.exp(_log_phi(z))
    return ndtr(z) - phi * (b * _mills(a * tau - z) - a * _mills(b * tau + z)) / (a + b)


def _mom_start(yi):
    m = yi.mean(); s2 = yi.var()
    d = yi - m
    k3 = (d**3).mean()
    k4 = (d**4).mean() - 3 * s2**2
    S, K = k3 / 2.0, k4 / 6.0
    p0 = (max(K, 1e-9) / 2.0) ** 0.25
    sol, _, ok, _ = fsolve(lambda v: [v[0]**3 - v[1]**3 - S, v[0]**4 + v[1]**4 - K],
                           [p0 * 1.1, p0 * 0.9], full_output=True)
    p, q = sol
    tau2 = s2 - (p**2 + q**2)
    if ok == 1 and p > 0 and q > 0 and tau2 > 0:
        return 1.0 / p, 1.0 / q, m - (p - q), np.sqrt(tau2)
    return 2.0, 2.0, m, np.sqrt(s2)


def dpln_theta(r):                  # pack a fitted dPlN result into a warm-start theta
    return [np.log(r["alpha"]), np.log(r["beta"]), r["nu"], np.log(r["tau"])]


def fit_dpln(x, lowc, highc, start=None):
    """Fit the dPlN by censored MLE. `start` (a theta from dpln_theta) warm-starts
    the optimizer from a neighbouring cell as a single local solve; None runs a
    small multi-start -- the moment start plus a low- and a high-alpha seed that
    straddle the two basins of the weakly-identified upper tail -- and keeps the
    best. (Under heavy censoring the tail is nearly flat, so a single start can
    converge to a worse local optimum; the seeds pin down the better basin.)"""
    yi, n_low, n_high = censor_split(x, lowc, highc)
    tlo, thi = np.log(lowc), np.log(highc)

    def negll(theta):
        a, b, nu, tau = np.exp(theta[0]), np.exp(theta[1]), theta[2], np.exp(theta[3])
        ll = (nl_logpdf(yi, a, b, nu, tau).sum()
              + n_low  * np.log(nl_cdf(tlo, a, b, nu, tau))
              + n_high * np.log1p(-nl_cdf(thi, a, b, nu, tau)))
        return -ll if np.isfinite(ll) else 1e18

    if start is not None:
        seeds = [start]
    else:
        m, s = yi.mean(), yi.std()
        a0, b0, nu0, tau0 = _mom_start(yi)
        seeds = [[np.log(a0), np.log(b0), nu0, np.log(tau0)],   # moment start
                 [np.log(3.0),  0.0, m, np.log(s)],             # low-alpha basin
                 [np.log(30.0), 0.0, m, np.log(s)]]             # high-alpha ridge
    res = None
    for seed in seeds:
        r = minimize(negll, seed, method="L-BFGS-B")
        if res is None or r.fun < res.fun:
            res = r
    a, b, nu, tau = np.exp(res.x[0]), np.exp(res.x[1]), res.x[2], np.exp(res.x[3])
    hd = _hess_diag(negll, res.x)                          # info in theta=[logα,logβ,ν,logτ]
    return dict(model="dpln", n=x.size, n_low=n_low, n_high=n_high,
                negll=float(res.fun), converged=bool(res.success),
                alpha=a, beta=b, nu=nu, tau=tau,
                info_alpha=float(hd[0]), info_beta=float(hd[1]),
                info_nu=float(hd[2]), info_tau=float(hd[3]),
                p_low_model=float(nl_cdf(tlo, a, b, nu, tau)),
                p_high_model=float(1 - nl_cdf(thi, a, b, nu, tau)))


# --------------------------------------------------- lognormal mixture (women)
def _unpack(theta):                 # (mu1, mu2, log sig1, log sig2, logit w)
    mu1, mu2, ls1, ls2, lw = theta
    s1 = SIG_FLOOR + np.exp(ls1)
    s2 = SIG_FLOOR + np.exp(ls2)
    w = 1.0 / (1.0 + np.exp(-lw))
    return mu1, mu2, s1, s2, w


def _comp_logpdf(y, mu, s):
    z = (y - mu) / s
    return -np.log(s) - 0.5 * LOG2PI - 0.5 * z * z


def mix_cdf(y, mu1, mu2, s1, s2, w):
    return w * ndtr((y - mu1) / s1) + (1 - w) * ndtr((y - mu2) / s2)


def mix_sf(y, mu1, mu2, s1, s2, w):     # survival via Phi(-z), avoids cancellation
    return w * ndtr((mu1 - y) / s1) + (1 - w) * ndtr((mu2 - y) / s2)


def mix_logpdf(y, mu1, mu2, s1, s2, w):
    return np.logaddexp(np.log(w) + _comp_logpdf(y, mu1, s1),
                        np.log1p(-w) + _comp_logpdf(y, mu2, s2))


def mix_theta(r):                   # pack a fitted mixture result into a warm-start theta
    s1 = max(r["sig1"] - SIG_FLOOR, 1e-6)
    s2 = max(r["sig2"] - SIG_FLOOR, 1e-6)
    w = min(max(r["w"], 1e-6), 1 - 1e-6)
    return [r["mu1"], r["mu2"], np.log(s1), np.log(s2), np.log(w / (1 - w))]


def fit_mixture(x, lowc, highc, start=None):
    """Fit the lognormal mixture by censored MLE. `start` (a theta from mix_theta)
    warm-starts from a neighbouring cell as a single local optimisation; None runs
    the deterministic 6-point restart grid."""
    yi, n_low, n_high = censor_split(x, lowc, highc)
    tlo, thi = np.log(lowc), np.log(highc)

    def negll(theta):
        p = _unpack(theta)
        ll = (mix_logpdf(yi, *p).sum()
              + n_low  * np.log(mix_cdf(tlo, *p))
              + n_high * np.log(mix_sf(thi, *p)))
        return -ll if np.isfinite(ll) else 1e18

    if start is not None:
        best = minimize(negll, start, method="L-BFGS-B")
    else:
        # deterministic restarts: vary weight and component separation about the interior mean
        m, s = yi.mean(), yi.std()
        ls = np.log(max(0.7 * s - SIG_FLOOR, 1e-3))
        best = None
        for w0 in (0.3, 0.5, 0.7):
            for d in (0.4, 0.9):
                theta0 = [m + d * s, m - d * s, ls, ls, np.log(w0 / (1 - w0))]
                res = minimize(negll, theta0, method="L-BFGS-B")
                if best is None or res.fun < best.fun:
                    best = res

    mu1, mu2, s1, s2, w = _unpack(best.x)
    hd = _hess_diag(negll, best.x)      # info in theta=[μ1,μ2,logσ1',logσ2',logit w]
    if mu1 < mu2:                       # label: component 1 = higher mean
        mu1, mu2, s1, s2, w = mu2, mu1, s2, s1, 1 - w
        hd = hd[[1, 0, 3, 2, 4]]        # keep info aligned with the relabelled params
    p = (mu1, mu2, s1, s2, w)
    return dict(model="mixture", n=x.size, n_low=n_low, n_high=n_high,
                negll=float(best.fun), converged=bool(best.success),
                mu1=mu1, mu2=mu2, sig1=s1, sig2=s2, w=w,
                info_mu1=float(hd[0]), info_mu2=float(hd[1]), info_sig1=float(hd[2]),
                info_sig2=float(hd[3]), info_w=float(hd[4]),
                p_low_model=float(mix_cdf(tlo, *p)),
                p_high_model=float(mix_sf(thi, *p)))


def ppf_mixture(prob, p, lo=np.log(1.0), hi=np.log(1e7)):
    """Invert the mixture CDF by bisection (used by the plot / diagnostic scripts)."""
    prob = np.asarray(prob, dtype=float)
    lo, hi = np.full_like(prob, lo), np.full_like(prob, hi)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        go = mix_cdf(mid, *p) < prob
        lo = np.where(go, mid, lo)
        hi = np.where(go, hi, mid)
    return 0.5 * (lo + hi)
