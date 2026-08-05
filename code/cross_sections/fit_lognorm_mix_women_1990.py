#!/usr/bin/env python
"""Fit a two-component lognormal mixture to the 1990 female earnings cross-section.

log-earnings ~ w * N(mu1, sig1^2) + (1-w) * N(mu2, sig2^2). All five parameters
(mu1, mu2, sig1, sig2, w) are estimated freely by MLE. Doubly Type-I censored,
same thresholds as the male dPlN fit ($200 low; taxmax - 1000 = $50,300 high).
Everything is closed form: the mixture density and CDF are weighted sums of the
normal pdf/cdf, so the censored log-likelihood has no integrals. This is the
single-year wrapper; the fit itself lives in crosssec_fit (shared with
estimate_cross_sections.py).

  python code/cross_sections/fit_lognorm_mix_women_1990.py
"""
import sys

import numpy as np

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import crosssec_fit as cf

YEAR, SEX = 1990, 2


def main():
    highc = cf.taxmax(YEAR) - cf.HIGH_MARGIN
    x = cf.load_earnings(YEAR, SEX)
    r = cf.fit_mixture(x, cf.LOWC, highc)
    N, n_low, n_high = r["n"], r["n_low"], r["n_high"]
    p = (r["mu1"], r["mu2"], r["sig1"], r["sig2"], r["w"])

    print(f"N={N:,}  interior={N - n_low - n_high:,}  "
          f"low(<= ${cf.LOWC:.0f})={n_low:,} ({100*n_low/N:.2f}%)  "
          f"high(>= ${highc:.0f})={n_high:,} ({100*n_high/N:.2f}%)")
    print(f"converged : {r['converged']}  negll={r['negll']:,.1f}")
    print(f"MLE       : w={r['w']:.4f}")
    print(f"  comp1 (upper): mu1={r['mu1']:.4f} sig1={r['sig1']:.4f}  median exp(mu1)=${np.exp(r['mu1']):,.0f}")
    print(f"  comp2 (lower): mu2={r['mu2']:.4f} sig2={r['sig2']:.4f}  median exp(mu2)=${np.exp(r['mu2']):,.0f}")
    print("fit check (model vs observed censoring mass):")
    print(f"  P(X<= ${cf.LOWC:.0f}) : {r['p_low_model']:.4f} vs {n_low/N:.4f}")
    print(f"  P(X>= ${highc:.0f}): {r['p_high_model']:.4f} vs {n_high/N:.4f}")
    print("fit check (model vs full-sample data quantiles, interior band only):")
    lo_f, hi_f = n_low / N, 1 - n_high / N
    for q in (0.25, 0.50, 0.75, 0.90):
        if not (lo_f < q < hi_f):
            continue                          # quantile sits inside a censored pile
        dq = np.quantile(x, q)
        mq = np.exp(cf.ppf_mixture(np.array([q]), p)[0])
        print(f"  p{int(q*100):<2d}: model ${mq:,.0f}  vs data ${dq:,.0f}")


if __name__ == "__main__":
    main()
