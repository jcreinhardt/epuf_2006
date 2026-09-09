#!/usr/bin/env python
"""The parametric earnings models -- distributions, their functionals, and the boxes that
keep them well-behaved. NO objective function and NO optimizer live here: this is the layer
both data terms (obj_mle, obj_gmm) and everything downstream (estimate_cross_sections,
extrapolate_params, aggregates, the plots) are written against.

Two models, one 6-slot interface:
  - men    double Pareto-lognormal, i.e. a Normal-Laplace law for log-earnings
           (normal body, exponential tails; theta = [log alpha, log beta, nu, log tau]).
  - women  two-component lognormal mixture (theta = [mu1, mu2, log s1, log s2, logit w]).

Everything is CLOSED FORM -- densities and CDFs via Mills ratios or normal CDFs, the
uncapped mean E[X], and the functional vector g -- so no objective built on top of this
module contains an integral or a root-find.

g_dpln / g_mix share one layout -- [E logY, sd logY, skew logY, logit S(cap), lower tail,
upper tail] -- so a single roughness weight means the same thing for both sexes. Every slot
is a functional of the DISTRIBUTION, never of one component, which is what makes it survive
the mixture's component swaps and the dPlN's body/tail reparameterizations; that invariance
is the whole reason the roughness penalty acts on g rather than on raw parameters. All six
are closed form because g is evaluated inside every objective evaluation of the joint solve
-- quantile-style functionals, which need bisection on the CDF, cost ~30x more.

THE BOXES ARE STRUCTURAL, NOT PENALTIES. In a ~75%-censored cell the interior carries almost
no shape information, and an unboxed fit sends exp(nu + tau^2/2) to overflow or alpha below 1,
where the uncapped mean is INFINITE -- either poisons the whole year's aggregate. Constraining
the degeneracy away beats hoping a penalty outvotes an unbounded likelihood.

duckdb via the CLI, per repo convention.
"""
import subprocess
import numpy as np
from scipy.special import erfcx, ndtr
from scipy.optimize import fsolve

DB          = "processed_data/ssa.duckdb"
LOWC        = 200.0     # left-censoring threshold ($), fixed across years
HIGH_MARGIN = 1000.0    # HIGHC = taxmax(year) - this; absorbs the near-cap collapse spike
SIG_FLOOR   = 0.02      # guard against the mixture sigma->0 likelihood degeneracy
SIG_MIN     = 0.20      # lower bound on each mixture sigma: stops a component collapsing onto
                        # a data-heaping spike (a round-earnings pile-up in sparse pre-1980
                        # retirement cells) -- the source of the sigma1/w basin ambiguity.
NU_LO, NU_HI = 3.0, 14.0    # dPlN log-location box (e^3 ~ $20 .. e^14 ~ $1.2M): keeps a heavily
TAU_MIN, TAU_MAX = 0.05, 3.0  # censored cell's location/scale from running off, which would send
                        # E[X] = exp(nu + tau^2/2)*... to inf and poison the year's aggregate.
ALPHA_MIN   = 1.05      # floor on the dPlN upper-tail index whenever the mean pull is active. E[X]
                        # ~ 1/(alpha-1), so alpha->1 makes the uncapped mean diverge; 1.05 caps that
                        # factor at 20 and keeps the constrained mean well-defined in both directions.
SIG_MAX     = 2.5       # upper bound on each mixture sigma: the mirror guard. Without it a minority
                        # component in a sparse old-age cell runs to sigma~12 and exp(mu+sigma^2/2)
                        # makes E[X] explode; 2.5 clips only a few pathological cells.
LOG2PI      = np.log(2 * np.pi)
SQRT2, SQRT_HALF_PI = np.sqrt(2.0), np.sqrt(np.pi / 2.0)
# L-BFGS-B stopping: COLD (fresh multi-start) is thorough; WARM (an inner-loop solve seeded from


# ----------------------------------------------------------------------------- data
def load_earnings(year, sex, age=None):
    """Positive covered earnings for a (year, sex) slice; pass `age` (= year - yob)
    to further restrict to a single-year age cell.

    ORDER BY is load-bearing, not cosmetic -- see estimate_cross_sections.load_year: an unordered
    parallel scan makes the likelihood's float summation order vary run to run, which
    flips basins in weakly-identified cells."""
    age_clause = "" if age is None else f" AND a.year - d.yob={int(age)}"
    q = ("SELECT a.earnings FROM annual a JOIN demographic d USING(id) "
         f"WHERE a.year={int(year)} AND d.sex={int(sex)} AND a.earnings>0{age_clause} "
         "ORDER BY a.earnings")
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


BIN_N = 256
def bin_interior(yi):
    """Histogram the interior log-earnings into <=BIN_N weighted mass points, so the interior
    log-likelihood is a sum over ~256 bin centres rather than over every observation. Prime-age
    cells hold ~1e4 obs; the joint solve refits each cell tens of times, and this is the single
    biggest per-fit speedup. Bin width ~ range/256 ~ 0.03 in log-earnings -- negligible for the
    smooth densities fitted here. Small cells (n<=BIN_N) pass through unbinned."""
    if yi.size <= BIN_N:
        return yi, np.ones(yi.size)
    cnt, edges = np.histogram(yi, bins=BIN_N)
    c, m = 0.5 * (edges[:-1] + edges[1:]), cnt > 0
    return c[m], cnt[m].astype(float)


def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


# ------------------------------------------------------------------ dPlN (men)
def _mills(w):                      # Mills ratio (1-Phi)/phi, stable via erfcx
    return SQRT_HALF_PI * erfcx(w / SQRT2)


def _log_phi(z):
    return -0.5 * LOG2PI - 0.5 * z * z


def nl_logpdf(y, a, b, nu, tau):    # Normal-Laplace log-density on log scale
    z = (y - nu) / tau
    return (np.log(a) + np.log(b) - np.log(a + b) + _log_phi(z)
            + np.log(_mills(a * tau - z) + _mills(b * tau + z)))


def nl_cdf(y, a, b, nu, tau):       # Normal-Laplace CDF (of log-earnings)
    z = (y - nu) / tau
    phi = np.exp(_log_phi(z))
    return ndtr(z) - phi * (b * _mills(a * tau - z) - a * _mills(b * tau + z)) / (a + b)


def dpln_mean(a, b, nu, tau):
    """Analytic UNCAPPED mean E[X] of the dPlN (no cap). INFINITE where the upper Pareto
    index a<=1 -- the censored-MLE heavy-tail pathology under a tight taxable maximum."""
    if not (a > 1.0):
        return np.inf
    return np.exp(nu + tau * tau / 2.0) * (a * b) / ((a - 1.0) * (b + 1.0))


def g_dpln(theta, logcap):
    """Regime-invariant functional vector of the dPlN, common slots with g_mix:
    [E log Y, sd log Y, skew log Y, logit S(cap), lower-tail log b, upper-tail log a].

    ALL SIX ARE CLOSED FORM. logY ~ Normal-Laplace, whose cumulants are analytic:
    k1 = nu + 1/a - 1/b, k2 = tau^2 + a^-2 + b^-2, k3 = 2 a^-3 - 2 b^-3; S(cap) comes from
    nl_cdf. An earlier version used log-quantiles for the body, which need bisection on the
    CDF -- 30x slower (0.29 ms vs 0.01 ms) and evaluated inside EVERY objective evaluation of
    the joint solve. Cumulants pin the same body/shape content: location, dispersion, and the
    skew that separates 'dispersed body, thin tail' from 'tight body, fat tail' (the competing
    basins). theta = [log a, log b, nu, log tau]; logcap = log(HIGHC)."""
    a, b, nu, tau = np.exp(theta[0]), np.exp(theta[1]), theta[2], np.exp(theta[3])
    S = 1.0 - nl_cdf(logcap, a, b, nu, tau)
    k2 = tau * tau + 1.0 / (a * a) + 1.0 / (b * b)
    k3 = 2.0 / (a ** 3) - 2.0 / (b ** 3)
    sd = np.sqrt(max(k2, 1e-12))
    return np.array([nu + 1.0 / a - 1.0 / b, sd, k3 / sd ** 3,
                     float(_logit(S)), np.log(b), np.log(a)])


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
    """Analytic UNCAPPED mean of the two-component lognormal mixture -- always finite.
    Under a tight cap women are heavily top-coded too, so their censored fit can overshoot;
    the per-year moment match carries the women's cells (mean_pen) alongside the men's."""
    return w * np.exp(mu1 + s1 * s1 / 2.0) + (1 - w) * np.exp(mu2 + s2 * s2 / 2.0)


def _mix_tail_means(c, p, S):
    """(E[logY | logY>c], E[logY | logY<c]) for the two-component normal mixture, closed form.
    Per component, E[Y|Y>c] = mu + s*phi(z)/(1-Phi(z)); mixture-weight them by each component's
    share of the mass on that side. Returns finite fallbacks when a side carries ~no mass."""
    mu1, mu2, s1, s2, w = p
    tot_hi = max(S, 1e-12)
    tot_lo = max(1.0 - S, 1e-12)
    hi = lo = 0.0
    for mu, s, wt in ((mu1, s1, w), (mu2, s2, 1 - w)):
        z = (c - mu) / s
        sf = ndtr(-z)                      # P(Y > c) for this component
        pdf = np.exp(-0.5 * LOG2PI - 0.5 * z * z)
        hi += wt * (mu * sf + s * pdf)     # wt * P(>c) * E[Y|Y>c]
        lo += wt * (mu * ndtr(z) - s * pdf)
    return float(hi / tot_hi), float(lo / tot_lo)


def g_mix(theta, logcap):
    """Regime-invariant functional vector of the mixture, SAME slots as g_dpln:
    [E log Y, sd log Y, skew log Y, logit S(cap), lower-tail, upper-tail].

    ALL SIX ARE CLOSED FORM (normal-mixture central moments + mix_sf; no quantile inversion --
    see g_dpln). Every component is a functional of the DISTRIBUTION, never of a single component,
    so the vector is unchanged when the two components swap labels. That is why the tail slots are
    mean excess of logY on either side of the cap rather than a raw sigma: the larger-sigma
    component governs the tail and which one that is flips across cells."""
    mu1, mu2, s1, s2, w = p = _unpack(theta)
    S = mix_sf(logcap, *p)
    m = w * mu1 + (1 - w) * mu2
    var = w * (s1 * s1 + mu1 * mu1) + (1 - w) * (s2 * s2 + mu2 * mu2) - m * m
    c3 = (w * ((mu1 - m) ** 3 + 3 * (mu1 - m) * s1 * s1)
          + (1 - w) * ((mu2 - m) ** 3 + 3 * (mu2 - m) * s2 * s2))
    sd = np.sqrt(max(var, 1e-12))
    # E[logY | logY > cap] and E[logY | logY < cap], both closed form for a normal mixture via
    # the per-component truncated means; the pair pins what the mixture extrapolates above the cap.
    hi, lo_ = _mix_tail_means(logcap, p, S)
    return np.array([m, sd, c3 / sd ** 3, float(_logit(S)), lo_, hi])
