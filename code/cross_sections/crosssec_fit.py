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
SIG_MIN     = 0.20      # lower bound on each mixture sigma: stops a component collapsing onto
                        # a data-heaping spike (a round-earnings pile-up in sparse pre-1980
                        # retirement cells) -- the source of the sigma1/w basin ambiguity.
                        # Only ~1% of cells (all at the age extremes) ever push against it.
SIG_MAX     = 2.5       # upper bound on each mixture sigma: the mirror guard. Without it a minority
                        # component in a sparse old-age cell runs to sigma~12 (mu at its bound), and
                        # exp(mu+sigma^2/2) makes E[X] explode (~1e38); the pure-smoothing stage can
                        # soften but not undo that, so a single cell can dominate a year's uncapped
                        # aggregate. 2.5 clips only ~15 cells (all pathological; real dispersion <~2).
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


def fit_dpln(x, lowc, highc, start=None, penalty=None, mean_pen=None):
    """Fit the dPlN by censored MLE. `start` (a theta from dpln_theta) warm-starts
    the optimizer from a neighbouring cell as a single local solve; None runs a
    small multi-start -- the moment start plus a low- and a high-alpha seed that
    straddle the two basins of the weakly-identified upper tail -- and keeps the
    best. (Under heavy censoring the tail is nearly flat, so a single start can
    converge to a worse local optimum; the seeds pin down the better basin.)

    `penalty=(target, lam)` adds a per-parameter quadratic Sum lam_i (theta_i -
    target_i)^2 (theta = [logα,logβ,ν,logτ]) to the objective -- the smoothness
    prior that keeps a weakly-identified parameter (the flat-ridge upper tail) on
    the neighbour line instead of being driven to a copied neighbour value by bare
    keep-best.

    `mean_pen=(eta, w)` adds eta*w*E[X](theta) -- the ANALYTIC dPlN uncapped mean
    dpln_mean -- to the objective: a one-sided downward pull on the upper tail that
    constrains the (cap-censored, hence unidentified above the cap) mean toward the
    published aggregate. eta is a SINGLE global weight, tuned once so the 1937-2004
    ASS-vs-model aggregate lines up; w is the cell's per-worker share (n_cell /
    year total), which makes the pull scale-free against the likelihood -- both grow
    with n_cell, so the correction is information-routed (identified cells barely
    move, censored flat-ridge cells thin) and uniform across cell sizes. No per-year
    target and no per-year solve: a fixed eta makes the aggregate moment SEPARABLE
    into an independent per-cell penalty, so it lives in the stage-1 fit. When set,
    log-alpha is bounded so alpha>1 (finite mean).

    `negll`/`info_*` stay the PURE likelihood; `obj` is the penalized value used for
    keep-best across warm starts."""
    yi, n_low, n_high = censor_split(x, lowc, highc)
    tlo, thi = np.log(lowc), np.log(highc)

    def negll(theta):
        a, b, nu, tau = np.exp(theta[0]), np.exp(theta[1]), theta[2], np.exp(theta[3])
        ll = (nl_logpdf(yi, a, b, nu, tau).sum()
              + n_low  * np.log(nl_cdf(tlo, a, b, nu, tau))
              + n_high * np.log1p(-nl_cdf(thi, a, b, nu, tau)))
        return -ll if np.isfinite(ll) else 1e18

    pen = None if penalty is None else (np.asarray(penalty[0], float),
                                        np.asarray(penalty[1], float))

    def obj(theta):
        val = negll(theta)
        if pen is not None:
            val += float(np.dot(pen[1], (np.asarray(theta) - pen[0]) ** 2))
        if mean_pen is not None:
            eta, w = mean_pen
            mth = dpln_mean(np.exp(theta[0]), np.exp(theta[1]), theta[2], np.exp(theta[3]))
            if not np.isfinite(mth):
                return 1e18
            val += eta * w * mth
        return val

    bnds = ([(np.log(1.0 + 1e-3), None), (None, None), (None, None), (None, None)]
            if mean_pen is not None else None)   # alpha>1 -> finite mean under the pull

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
        r = minimize(obj, seed, method="L-BFGS-B", bounds=bnds)
        if res is None or r.fun < res.fun:
            res = r
    a, b, nu, tau = np.exp(res.x[0]), np.exp(res.x[1]), res.x[2], np.exp(res.x[3])
    hd = _hess_diag(negll, res.x)                          # info in theta=[logα,logβ,ν,logτ]
    return dict(model="dpln", n=x.size, n_low=n_low, n_high=n_high,
                negll=float(negll(res.x)), obj=float(res.fun), converged=bool(res.success),
                alpha=a, beta=b, nu=nu, tau=tau,
                info_alpha=float(hd[0]), info_beta=float(hd[1]),
                info_nu=float(hd[2]), info_tau=float(hd[3]),
                p_low_model=float(nl_cdf(tlo, a, b, nu, tau)),
                p_high_model=float(1 - nl_cdf(thi, a, b, nu, tau)))


# ---------------------------------------- dPlN uncapped mean + profiled-alpha match
def dpln_mean(a, b, nu, tau):
    """Analytic UNCAPPED mean E[X] of the dPlN (no cap). INFINITE where the upper Pareto
    index a<=1 -- the censored-MLE heavy-tail pathology under a tight taxable maximum."""
    if not (a > 1.0):
        return np.inf
    return np.exp(nu + tau * tau / 2.0) * (a * b) / ((a - 1.0) * (b + 1.0))


def dpln_var(a, b, nu, tau):
    """Analytic UNCAPPED variance of the dPlN, from the moment formula
    E[X^s] = exp(s*nu + s^2*tau^2/2) * a*b / ((a-s)(b+s)) for s < a. INFINITE where a<=2
    (the second moment diverges). Used only to seed the per-year multiplier search with the
    Gaussian starting guess lambda0 = gap / (weighted-average variance); heavy-tail cells
    (a<=2) return inf, which the caller treats as 'no usable local slope' and falls back."""
    if not (a > 2.0):
        return np.inf
    m1 = np.exp(nu + tau * tau / 2.0) * (a * b) / ((a - 1.0) * (b + 1.0))
    m2 = np.exp(2.0 * nu + 2.0 * tau * tau) * (a * b) / ((a - 2.0) * (b + 2.0))
    return float(m2 - m1 * m1)


def dpln_negll(x, lowc, highc, a, b, nu, tau):
    """Doubly-censored dPlN negative log-likelihood at a given parameter vector -- the pure
    fit measure (no penalties), used to price the fit cost of the mean-moment match."""
    yi, n_low, n_high = censor_split(x, lowc, highc)
    tlo, thi = np.log(lowc), np.log(highc)
    ll = (nl_logpdf(yi, a, b, nu, tau).sum()
          + n_low  * np.log(nl_cdf(tlo, a, b, nu, tau))
          + n_high * np.log1p(-nl_cdf(thi, a, b, nu, tau)))
    return float(-ll) if np.isfinite(ll) else 1e18


def fit_dpln_mean(x, lowc, highc, start, line, lam, eta, w, amin=1.0 + 1e-3):
    """FULL-vector penalized fit of one dPlN cell under a mean moment. Minimizes

        negll(theta)  +  Sum_p lam_p (theta_p - line_p)^2  +  eta * w * E[X](theta),

    theta = [logα, logβ, ν, logτ]. The three terms are the censored likelihood, the stage-1.5
    smoothness prior (line = neighbour-line theta, lam = its REML precision), and the aggregate-
    mean moment (eta shared across a year's cells, w the cell's worker weight). ALL FOUR params
    move, so the body (ν, τ, β) re-optimizes to compensate as the tail thins -- the mean match
    costs little likelihood, unlike freezing the body and pushing alpha alone. eta trades tail
    weight for mean; against each cell's own curvature the pull is information-routed (identified
    cells barely move, the censored flat-ridge alpha absorbs it). logα is bounded so alpha>amin,
    keeping E[X] finite. Returns (alpha, beta, nu, tau, negll_pure) -- negll at the optimum,
    WITHOUT the penalties, so fit loss vs the unconstrained smooth fit is measurable."""
    yi, n_low, n_high = censor_split(x, lowc, highc)
    tlo, thi = np.log(lowc), np.log(highc)
    line, lam = np.asarray(line, float), np.asarray(lam, float)

    def negll(theta):
        a, b, nu, tau = np.exp(theta[0]), np.exp(theta[1]), theta[2], np.exp(theta[3])
        ll = (nl_logpdf(yi, a, b, nu, tau).sum()
              + n_low  * np.log(nl_cdf(tlo, a, b, nu, tau))
              + n_high * np.log1p(-nl_cdf(thi, a, b, nu, tau)))
        return -ll if np.isfinite(ll) else 1e18

    def obj(theta):
        m = dpln_mean(np.exp(theta[0]), np.exp(theta[1]), theta[2], np.exp(theta[3]))
        if not np.isfinite(m):
            return 1e18
        return negll(theta) + float(np.dot(lam, (theta - line) ** 2)) + eta * w * m

    bnds = [(np.log(amin), None), (None, None), (None, None), (None, None)]
    res = minimize(obj, np.asarray(start, float), method="L-BFGS-B", bounds=bnds)
    a, b, nu, tau = np.exp(res.x[0]), np.exp(res.x[1]), res.x[2], np.exp(res.x[3])
    return a, b, nu, tau, float(negll(res.x))


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


def mix_mean(mu1, mu2, s1, s2, w):
    """Analytic UNCAPPED mean of the two-component lognormal mixture -- always finite, so the
    women's cells need no tail correction; they enter the moment match as a fixed offset."""
    return w * np.exp(mu1 + s1 * s1 / 2.0) + (1 - w) * np.exp(mu2 + s2 * s2 / 2.0)


def fit_mixture(x, lowc, highc, start=None, penalty=None):
    """Fit the lognormal mixture by censored MLE. `start` (a theta from mix_theta)
    warm-starts from a neighbouring cell as a single local optimisation; None runs
    the deterministic 6-point restart grid.

    `penalty=(target, lam)` adds Sum lam_i (theta_i - target_i)^2 (theta =
    [μ1,μ2,logσ1',logσ2',logit w]) to the objective -- the smoothness prior toward
    the neighbour line. `negll`/`info_*` stay the PURE likelihood; `obj` is the
    penalized value for keep-best. The target is in the mean-ordered convention
    (component 1 = higher mean), matching the relabelling below."""
    yi, n_low, n_high = censor_split(x, lowc, highc)
    tlo, thi = np.log(lowc), np.log(highc)

    def negll(theta):
        p = _unpack(theta)
        ll = (mix_logpdf(yi, *p).sum()
              + n_low  * np.log(mix_cdf(tlo, *p))
              + n_high * np.log(mix_sf(thi, *p)))
        return -ll if np.isfinite(ll) else 1e18

    if penalty is None:
        obj = negll
    else:
        t_t, lam = np.asarray(penalty[0], float), np.asarray(penalty[1], float)
        def obj(theta):
            return negll(theta) + float(np.dot(lam, (np.asarray(theta) - t_t) ** 2))

    # bound each log-sigma theta so sigma = SIG_FLOOR + exp(ls) >= SIG_MIN: forbids the
    # heaping-spike basin without touching the ~99% of cells that sit well above the floor.
    lo, hi = np.log(SIG_MIN - SIG_FLOOR), np.log(SIG_MAX - SIG_FLOOR)   # sigma in [SIG_MIN, SIG_MAX]
    bnds = [(4.0, 13.0), (4.0, 13.0), (lo, hi), (lo, hi), (None, None)]  # mu in a sane
    #   log-earnings range so a near-empty minority component can't run off to +/-100; then
    #   its info -> 0 and the stage-1.5 penalty cleanly pulls it onto the neighbour line.
    if start is not None:
        best = minimize(obj, start, method="L-BFGS-B", bounds=bnds)
    else:
        # deterministic restarts: vary weight and component separation about the interior mean
        m, s = yi.mean(), yi.std()
        ls = np.log(max(0.7 * s - SIG_FLOOR, 1e-3))
        best = None
        for w0 in (0.3, 0.5, 0.7):
            for d in (0.4, 0.9):
                theta0 = [m + d * s, m - d * s, ls, ls, np.log(w0 / (1 - w0))]
                res = minimize(obj, theta0, method="L-BFGS-B", bounds=bnds)
                if best is None or res.fun < best.fun:
                    best = res

    mu1, mu2, s1, s2, w = _unpack(best.x)
    hd = _hess_diag(negll, best.x)      # info in theta=[μ1,μ2,logσ1',logσ2',logit w]
    if mu1 < mu2:                       # label: component 1 = higher mean
        mu1, mu2, s1, s2, w = mu2, mu1, s2, s1, 1 - w
        hd = hd[[1, 0, 3, 2, 4]]        # keep info aligned with the relabelled params
    p = (mu1, mu2, s1, s2, w)
    return dict(model="mixture", n=x.size, n_low=n_low, n_high=n_high,
                negll=float(negll(best.x)), obj=float(best.fun), converged=bool(best.success),
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
