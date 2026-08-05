#!/usr/bin/env python
"""Fit a double Pareto-lognormal (dPlN) to the 1990 male earnings cross-section.

log-earnings ~ Normal-Laplace(alpha, beta, nu, tau). Doubly Type-I censored:
  - right-censored at the taxable max minus one rounding base (C = $50,300),
    absorbing both the $51,300 cap pile and the $50,819 near-cap collapse spike;
  - left-censored at $200, absorbing the sub-$100 bottom-code spike ($52).
Warm start by method of moments (Normal-Laplace cumulants) on the interior;
numerical-gradient MLE. This is the single-year wrapper; the fit itself lives in
crosssec_fit (shared with estimate_cross_sections.py).

  python code/cross_sections/fit_dpln_male_1990.py
"""
import sys

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import crosssec_fit as cf

YEAR, SEX = 1990, 1


def main():
    highc = cf.taxmax(YEAR) - cf.HIGH_MARGIN
    x = cf.load_earnings(YEAR, SEX)
    r = cf.fit_dpln(x, cf.LOWC, highc)
    N = r["n"]
    print(f"N={N:,}  interior={N - r['n_low'] - r['n_high']:,}  "
          f"low(<= ${cf.LOWC:.0f})={r['n_low']:,} ({100*r['n_low']/N:.2f}%)  "
          f"high(>= ${highc:.0f})={r['n_high']:,} ({100*r['n_high']/N:.2f}%)")
    print(f"converged : {r['converged']}  negll={r['negll']:,.1f}")
    print(f"MLE       : alpha={r['alpha']:.4f} beta={r['beta']:.4f} "
          f"nu={r['nu']:.4f} tau={r['tau']:.4f}")
    print(f"  upper tail index alpha={r['alpha']:.3f}  lower tail index beta={r['beta']:.3f}")
    import numpy as np
    print(f"  lognormal body location exp(nu)=${np.exp(r['nu']):,.0f}  (not the median)")
    print("fit check (model vs observed censoring mass):")
    print(f"  P(X<= ${cf.LOWC:.0f}) : {r['p_low_model']:.4f} vs {r['n_low']/N:.4f}")
    print(f"  P(X>= ${highc:.0f}): {r['p_high_model']:.4f} vs {r['n_high']/N:.4f}")


if __name__ == "__main__":
    main()
