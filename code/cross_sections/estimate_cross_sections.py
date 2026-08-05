#!/usr/bin/env python
"""Estimate the earnings cross-section for every (year, sex, single-year age) cell
and dump the fitted parameters to one tidy CSV.

Men are fit with the double Pareto-lognormal, women with the two-component
lognormal mixture (the pairing from the 1990 scripts), doubly censored at LOWC /
taxmax-HIGH_MARGIN -- now sliced by single-year age as well as year and sex.
Three speedups keep the ~6.4k-cell sweep to well under a minute:

  1. one DB pull per year (not per cell) -- the JOIN and duckdb spawn happen 56
     times, not thousands; taxmax comes free as that year's MAX(earnings).
  2. parallel across years (one worker per year, both sexes, all ages).
  3. warm starts along age: within a (year, sex) the fitted params of one age seed
     the next age's optimiser, evaluated alongside a robust cold start (multi-start)
     and kept only if it wins on likelihood -- see the keep-best note in fit_year.

Only cells with at least MIN_N positive-earnings observations are fit; smaller
cells are skipped for now. BLAS is pinned to one thread per worker so the many
small optimisations don't oversubscribe cores.

  python code/cross_sections/estimate_cross_sections.py [--jobs N]
    -> output/cross_sections/cross_section_params.csv
"""
import os
# pin BLAS to one thread BEFORE numpy/scipy import -> no oversubscription across workers
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import csv
import sys
import subprocess
from io import StringIO
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd
import crosssec_fit as cf

YEARS  = range(1951, 2007)   # full EPUF annual span (heavily top-censored pre-1980)
MIN_N  = 1000                # skip cells with fewer positive-earnings observations
OUT    = Path("output/cross_sections/cross_section_params.csv")
# per-sex plumbing: label, fitter, warm-start packer
SEX = {1: ("male",   cf.fit_dpln,    cf.dpln_theta),
       2: ("female", cf.fit_mixture, cf.mix_theta)}
COLS = ["year", "sex", "age", "model", "n", "n_low", "n_high", "negll", "converged",
        "alpha", "beta", "nu", "tau",              # dPlN
        "mu1", "mu2", "sig1", "sig2", "w",         # mixture
        "info_alpha", "info_beta", "info_nu", "info_tau",              # dPlN theta-info
        "info_mu1", "info_mu2", "info_sig1", "info_sig2", "info_w",    # mixture theta-info
        "lowc", "highc", "p_low_model", "p_high_model"]


def load_year(year):
    """All positive-earnings (sex, age, earnings) rows for one year, in one pull."""
    q = ("SELECT d.sex, a.year - d.yob AS age, a.earnings "
         "FROM annual a JOIN demographic d USING(id) "
         f"WHERE a.year={int(year)} AND a.earnings>0 AND d.sex IN (1,2)")
    out = subprocess.run(["duckdb", "-readonly", cf.DB, "-noheader", "-csv", "-c", q],
                         capture_output=True, text=True, check=True).stdout
    return pd.read_csv(StringIO(out), header=None, names=["sex", "age", "earnings"])


def fit_year(year):
    """Fit every qualifying (sex, age) cell for one year; return a list of row dicts."""
    df = load_year(year)
    highc = float(df["earnings"].max()) - cf.HIGH_MARGIN   # taxmax(year) - margin
    rows = []
    for sex, (label, fit, pack) in SEX.items():
        g = df.loc[df["sex"] == sex]
        by_age = {a: sub["earnings"].to_numpy(dtype=float)
                  for a, sub in g.groupby("age") if len(sub) >= MIN_N}
        prev = None                                        # warm-start theta from previous age
        for age in sorted(by_age):                         # sweep ages upward
            x = by_age[age]
            # multi-start keep-best: the robust cold start (dPlN multi-start /
            # mixture 6-point grid) AND the warm neighbour, keeping the lowest-negll
            # converged fit. L-BFGS-B reports success at local optima too, so the
            # seeds must be compared -- warm alone can lock a whole year into a
            # worse basin (e.g. the 1957 men's upper-tail collapse).
            cands = [fit(x, cf.LOWC, highc, start=None)]
            if prev is not None:
                cands.append(fit(x, cf.LOWC, highc, start=prev))
            conv = [c for c in cands if c["converged"]]
            r = min(conv or cands, key=lambda c: c["negll"])
            prev = pack(r) if r["converged"] else None
            r.update(year=year, sex=sex, age=int(age), lowc=cf.LOWC, highc=highc)
            rows.append(r)
    return year, rows


def main(jobs=None):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(fit_year, y): y for y in YEARS}
        for fut in as_completed(futs):
            year, yr_rows = fut.result()
            rows.extend(yr_rows)
            nconv = sum(r["converged"] for r in yr_rows)
            print(f"{year}: {len(yr_rows):>3} cells fit, {nconv:>3} converged", flush=True)

    rows.sort(key=lambda r: (r["year"], r["sex"], r["age"]))
    with OUT.open("w", newline="") as fh:
        wtr = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        wtr.writeheader()
        wtr.writerows(rows)
    print(f"\nwrote {len(rows)} rows -> {OUT}")


if __name__ == "__main__":
    jobs = None
    if "--jobs" in sys.argv:
        jobs = int(sys.argv[sys.argv.index("--jobs") + 1])
    main(jobs)
