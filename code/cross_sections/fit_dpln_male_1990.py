#!/usr/bin/env python
"""Fit a double Pareto-lognormal (dPlN) to the 1990 male earnings cross-section.

log-earnings ~ Normal-Laplace(alpha, beta, nu, tau). Doubly Type-I censored:
  - right-censored at the taxable max minus one rounding base (C = $50,300),
    absorbing both the $51,300 cap pile and the $50,819 near-cap collapse spike;
  - left-censored at $200, absorbing the sub-$100 bottom-code spike ($52).
Warm start by method of moments (Normal-Laplace cumulants) on the interior;
numerical-gradient MLE. duckdb via the CLI, per repo convention.
"""
import subprocess, sys
import numpy as np
from scipy.special import erfcx, ndtr
from scipy.optimize import minimize, fsolve

DB   = "processed_data/ssa.duckdb"
LOWC = 200.0        # left-censoring threshold ($)
HIGHC = 50300.0     # right-censoring threshold ($) = 1990 taxmax 51300 - 1000 base
SQRT2, SQRT_HALF_PI = np.sqrt(2.0), np.sqrt(np.pi / 2.0)


def load_earnings():
    q = ("SELECT a.earnings FROM annual a JOIN demographic d USING(id) "
         "WHERE a.year=1990 AND d.sex=1 AND a.earnings>0")
    out = subprocess.run(["duckdb", DB, "-noheader", "-csv", "-c", q],
                         capture_output=True, text=True, check=True).stdout
    return np.array(out.split(), dtype=float)


def mills(w):                       # Mills ratio (1-Phi)/phi, stable via erfcx
    return SQRT_HALF_PI * erfcx(w / SQRT2)


def log_phi(z):
    return -0.5 * np.log(2 * np.pi) - 0.5 * z * z


def nl_logpdf(y, a, b, nu, tau):    # Normal-Laplace log-density on log scale
    z = (y - nu) / tau
    return (np.log(a) + np.log(b) - np.log(a + b) + log_phi(z)
            + np.log(mills(a * tau - z) + mills(b * tau + z)))


def nl_cdf(y, a, b, nu, tau):       # Normal-Laplace CDF (scalar thresholds)
    z = (y - nu) / tau
    phi = np.exp(log_phi(z))
    return ndtr(z) - phi * (b * mills(a * tau - z) - a * mills(b * tau + z)) / (a + b)


def mom_start(yi):
    m = yi.mean(); s2 = yi.var()
    d = yi - m
    k3 = (d**3).mean()
    k4 = (d**4).mean() - 3 * s2**2          # 4th cumulant
    S, K = k3 / 2.0, k4 / 6.0               # p^3-q^3=S, p^4+q^4=K  (p=1/a, q=1/b)
    p0 = (max(K, 1e-9) / 2.0) ** 0.25
    sol, _, ok, _ = fsolve(lambda v: [v[0]**3 - v[1]**3 - S, v[0]**4 + v[1]**4 - K],
                           [p0 * 1.1, p0 * 0.9], full_output=True)
    p, q = sol
    tau2 = s2 - (p**2 + q**2)
    if ok == 1 and p > 0 and q > 0 and tau2 > 0:
        return 1.0 / p, 1.0 / q, m - (p - q), np.sqrt(tau2)
    return 2.0, 2.0, m, np.sqrt(s2)         # fallback: lognormal body, moderate tails


def make_negll(yi, n_low, n_high):
    tlo, thi = np.log(LOWC), np.log(HIGHC)
    def negll(theta):
        a, b, nu, tau = np.exp(theta[0]), np.exp(theta[1]), theta[2], np.exp(theta[3])
        ll = (nl_logpdf(yi, a, b, nu, tau).sum()
              + n_low  * np.log(nl_cdf(tlo, a, b, nu, tau))
              + n_high * np.log1p(-nl_cdf(thi, a, b, nu, tau)))
        return -ll if np.isfinite(ll) else 1e18
    return negll


def main():
    x = load_earnings()
    N = x.size
    low, high = x <= LOWC, x >= HIGHC
    inter = ~(low | high)
    yi = np.log(x[inter])
    n_low, n_high = int(low.sum()), int(high.sum())

    a0, b0, nu0, tau0 = mom_start(yi)
    negll = make_negll(yi, n_low, n_high)
    theta0 = [np.log(a0), np.log(b0), nu0, np.log(tau0)]
    res = minimize(negll, theta0, method="L-BFGS-B")
    a, b, nu, tau = np.exp(res.x[0]), np.exp(res.x[1]), res.x[2], np.exp(res.x[3])

    tlo, thi = np.log(LOWC), np.log(HIGHC)
    print(f"N={N:,}  interior={inter.sum():,}  "
          f"low(<= ${LOWC:.0f})={n_low:,} ({100*n_low/N:.2f}%)  "
          f"high(>= ${HIGHC:.0f})={n_high:,} ({100*n_high/N:.2f}%)")
    print(f"MoM start : alpha={a0:.3f} beta={b0:.3f} nu={nu0:.3f} tau={tau0:.3f}")
    print(f"converged : {res.success}  negll={res.fun:,.1f}")
    print(f"MLE       : alpha={a:.4f} beta={b:.4f} nu={nu:.4f} tau={tau:.4f}")
    print(f"  upper tail index alpha={a:.3f}  lower tail index beta={b:.3f}")
    print(f"  lognormal body location exp(nu)=${np.exp(nu):,.0f}  (not the median)")
    print("fit check (model vs observed censoring mass):")
    print(f"  P(X<= ${LOWC:.0f}) : {nl_cdf(tlo,a,b,nu,tau):.4f} vs {n_low/N:.4f}")
    print(f"  P(X>= ${HIGHC:.0f}): {1-nl_cdf(thi,a,b,nu,tau):.4f} vs {n_high/N:.4f}")


if __name__ == "__main__":
    main()
