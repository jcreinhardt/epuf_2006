#!/usr/bin/env python
"""Estimate the cross-sectional earnings distribution for every year x gender and
dump the fitted parameters to one tidy CSV.

Per (year, sex): men are fit with the double Pareto-lognormal, women with the
two-component lognormal mixture (the pairing established by the 1990 scripts).
Right-censoring threshold is year-specific, taxmax(year) - HIGH_MARGIN; left at
LOWC. Years span the full EPUF annual range 1951-2006; pre-1980 top-coding is
severe (see README), so the early-year tail parameters are not to be trusted.

  python code/cross_sections/estimate_cross_sections.py
    -> output/cross_sections/cross_section_params.csv
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import crosssec_fit as cf

YEARS = range(1951, 2007)   # full EPUF annual span (heavily top-censored pre-1980)
# sex code -> fitter for that gender
FITTERS = {1: ("male",   cf.fit_dpln),
           2: ("female", cf.fit_mixture)}
OUT = Path("output/cross_sections/cross_section_params.csv")
COLS = ["year", "sex", "model", "n", "n_low", "n_high", "negll", "converged",
        "alpha", "beta", "nu", "tau",              # dPlN
        "mu1", "mu2", "sig1", "sig2", "w",         # mixture
        "lowc", "highc", "p_low_model", "p_high_model"]


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for year in YEARS:
        highc = cf.taxmax(year) - cf.HIGH_MARGIN
        for sex, (label, fit) in FITTERS.items():
            x = cf.load_earnings(year, sex)
            r = fit(x, cf.LOWC, highc)
            r.update(year=year, sex=sex, lowc=cf.LOWC, highc=highc)
            rows.append(r)
            print(f"{year} {label:6s} {r['model']:7s} "
                  f"N={r['n']:>7,} low={r['n_low']:>6,} high={r['n_high']:>6,} "
                  f"negll={r['negll']:>12,.1f} conv={r['converged']}")

    with OUT.open("w", newline="") as fh:
        wtr = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        wtr.writeheader()
        wtr.writerows(rows)
    print(f"\nwrote {len(rows)} rows -> {OUT}")


if __name__ == "__main__":
    main()
