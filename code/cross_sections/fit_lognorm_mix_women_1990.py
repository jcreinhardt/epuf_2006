#!/usr/bin/env python
"""Fit a two-component lognormal mixture to the 1990 female earnings cross-section.

log-earnings ~ w * N(mu1, sig1^2) + (1-w) * N(mu2, sig2^2). All five parameters
(mu1, mu2, sig1, sig2, w) are estimated freely by MLE. Doubly Type-I censored,
same thresholds as the male dPlN fit:
  - right-censored at C = $50,300 (taxmax 51300 - 1000 base; absorbs the cap pile
    plus the near-cap collapse spike);
  - left-censored at $200 (absorbs the sub-$100 bottom-code spike).
Everything is closed form: the mixture density and CDF are weighted sums of the
normal pdf/cdf, so the censored log-likelihood has no integrals. A small floor on
sigma guards against the normal-mixture likelihood-blowup degeneracy. A handful of
deterministic restarts guard against bad local optima. numerical-gradient MLE.
duckdb via the CLI, per repo convention.
"""
import subprocess
import numpy as np
from scipy.special import ndtr
from scipy.optimize import minimize

DB    = "processed_data/ssa.duckdb"
LOWC  = 200.0        # left-censoring threshold ($)
HIGHC = 50300.0      # right-censoring threshold ($) = 1990 taxmax 51300 - 1000 base
LOG2PI = np.log(2 * np.pi)
SIG_FLOOR = 0.02     # guard against the sigma->0 likelihood degeneracy


def load_earnings():
    q = ("SELECT a.earnings FROM annual a JOIN demographic d USING(id) "
         "WHERE a.year=1990 AND d.sex=2 AND a.earnings>0")
    out = subprocess.run(["duckdb", DB, "-noheader", "-csv", "-c", q],
                         capture_output=True, text=True, check=True).stdout
    return np.array(out.split(), dtype=float)


def unpack(theta):                  # (mu1, mu2, log sig1, log sig2, logit w)
    mu1, mu2, ls1, ls2, lw = theta
    s1 = SIG_FLOOR + np.exp(ls1)
    s2 = SIG_FLOOR + np.exp(ls2)
    w = 1.0 / (1.0 + np.exp(-lw))
    return mu1, mu2, s1, s2, w


def comp_logpdf(y, mu, s):          # log normal density
    z = (y - mu) / s
    return -np.log(s) - 0.5 * LOG2PI - 0.5 * z * z


def mix_cdf(y, mu1, mu2, s1, s2, w):
    return w * ndtr((y - mu1) / s1) + (1 - w) * ndtr((y - mu2) / s2)


def mix_sf(y, mu1, mu2, s1, s2, w):     # survival, via Phi(-z) to avoid cancellation
    return w * ndtr((mu1 - y) / s1) + (1 - w) * ndtr((mu2 - y) / s2)


def mix_logpdf(y, mu1, mu2, s1, s2, w):
    return np.logaddexp(np.log(w) + comp_logpdf(y, mu1, s1),
                        np.log1p(-w) + comp_logpdf(y, mu2, s2))


def make_negll(yi, n_low, n_high):
    tlo, thi = np.log(LOWC), np.log(HIGHC)
    def negll(theta):
        p = unpack(theta)
        ll = (mix_logpdf(yi, *p).sum()
              + n_low  * np.log(mix_cdf(tlo, *p))
              + n_high * np.log(mix_sf(thi, *p)))
        return -ll if np.isfinite(ll) else 1e18
    return negll


def ppf(prob, p, lo=np.log(1.0), hi=np.log(1e7)):    # invert mixture CDF by bisection
    lo, hi = np.full_like(prob, lo), np.full_like(prob, hi)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        go = mix_cdf(mid, *p) < prob
        lo = np.where(go, mid, lo)
        hi = np.where(go, hi, mid)
    return 0.5 * (lo + hi)


def main():
    x = load_earnings()
    N = x.size
    low, high = x <= LOWC, x >= HIGHC
    inter = ~(low | high)
    yi = np.log(x[inter])
    n_low, n_high = int(low.sum()), int(high.sum())
    negll = make_negll(yi, n_low, n_high)

    # deterministic restarts: vary weight and component separation about the interior mean
    m, s = yi.mean(), yi.std()
    best = None
    for w0 in (0.3, 0.5, 0.7):
        for d in (0.4, 0.9):
            ls = np.log(max(0.7 * s - SIG_FLOOR, 1e-3))
            theta0 = [m + d * s, m - d * s, ls, ls, np.log(w0 / (1 - w0))]
            res = minimize(negll, theta0, method="L-BFGS-B")
            if best is None or res.fun < best.fun:
                best = res

    mu1, mu2, s1, s2, w = unpack(best.x)
    # label convention: component 1 = higher mean (full-time-ish), carry its weight
    if mu1 < mu2:
        mu1, mu2, s1, s2, w = mu2, mu1, s2, s1, 1 - w
    p = (mu1, mu2, s1, s2, w)

    tlo, thi = np.log(LOWC), np.log(HIGHC)
    print(f"N={N:,}  interior={inter.sum():,}  "
          f"low(<= ${LOWC:.0f})={n_low:,} ({100*n_low/N:.2f}%)  "
          f"high(>= ${HIGHC:.0f})={n_high:,} ({100*n_high/N:.2f}%)")
    print(f"converged : {best.success}  negll={best.fun:,.1f}")
    print(f"MLE       : w={w:.4f}")
    print(f"  comp1 (upper): mu1={mu1:.4f} sig1={s1:.4f}  median exp(mu1)=${np.exp(mu1):,.0f}")
    print(f"  comp2 (lower): mu2={mu2:.4f} sig2={s2:.4f}  median exp(mu2)=${np.exp(mu2):,.0f}")
    print("fit check (model vs observed censoring mass):")
    print(f"  P(X<= ${LOWC:.0f}) : {mix_cdf(tlo,*p):.4f} vs {n_low/N:.4f}")
    print(f"  P(X>= ${HIGHC:.0f}): {mix_sf(thi,*p):.4f} vs {n_high/N:.4f}")
    print("fit check (model vs full-sample data quantiles, interior band only):")
    lo_f, hi_f = n_low / N, 1 - n_high / N
    for q in (0.25, 0.50, 0.75, 0.90):
        if not (lo_f < q < hi_f):
            continue                          # quantile sits inside a censored pile
        dq = np.quantile(x, q)
        mq = np.exp(ppf(np.array([q]), p)[0])
        print(f"  p{int(q*100):<2d}: model ${mq:,.0f}  vs data ${dq:,.0f}")


if __name__ == "__main__":
    main()
