#!/usr/bin/env python
"""Unified entry point for estimating the cohort x sex lifecycle profile g(t).

One script, three estimators of the same object.  Every other parameter of the GKOS (2021)
benchmark process is held FIXED at the published estimate (gcohort_model.py); only

    g(t) = g0 + g1*t + g2*t^2 + g3*t^3,      t = (age - 24)/10

is searched over, per (sex, cohort) block, against the published GKSW cohort x age files.

  --mode ols             CMS's estimator: per-block OLS of the published meanlog on an age
                         polynomial, no model inversion.  Seconds; needs replication_repos/CMS
                         for the average-wage series.  Implementation: gcohort_ols.py.
  --mode smm-mean        SMM on meanlog alone: 1 moment x 31 ages against the coefficients,
                         model-inverted (g is the profile that makes the MODEL reproduce the
                         moment after nonemployment and the Ymin screen).
  --mode smm-quantiles   SMM on meanlog + p10/p25/p50/p75/p90/p98 with multi-step optimal
                         weighting.  Implementation for both: gcohort_smm.py.

--mode ols is on a different LEVEL from the SMM modes (its g absorbs the E[u | .] term they
strip out; it reports the gap as `eu_offset`).  Slopes are the meaningful comparison.  The
shape moments are not offered as a mode because they cannot identify g (measured dm/dg ~ 0);
gcohort_smm.SETS still exposes them for the J specification test.

Outputs (--out overrides, --tag suffixes) in output/dynamics/:
    g_cohort_ols.csv | g_cohort_smm_mean.csv | g_cohort_smm_quantiles.csv
All share their first 15 columns (sex, cohort, n_ages, g0..g3, g0_raw..g3_raw, rmse,
max_abs_resid, sdlog_gap, max_censored_share), the schema extrapolate_g_cohort.py and the
plots read, so any mode's output is a drop-in downstream.

Run from the project root:
    python code/dynamics/estimate_g_cohort.py --mode ols
    python code/dynamics/estimate_g_cohort.py --mode smm-mean      [--jobs 8]
    python code/dynamics/estimate_g_cohort.py --mode smm-quantiles [--jobs 8] [--wnoise 2]
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, "code/dynamics")          # run from the project root, per repo convention

OUT = "output/dynamics"
SMM_MOMENTS = {"smm-mean": "mean", "smm-quantiles": "level"}


def build_parser():
    ap = argparse.ArgumentParser(
        description="Estimate the cohort x sex lifecycle profile g(t) by OLS (CMS) or SMM.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("--mode", choices=("ols", "smm-mean", "smm-quantiles"),
                    default="smm-quantiles")
    ap.add_argument("--n", type=int, default=200_000, help="simulated individuals")
    ap.add_argument("--min-ages", type=int, default=31,
                    help="skip cohorts with fewer observed ages (31 = the full 25-55 span)")
    ap.add_argument("--sel", default="sel0", help="selection tag of the target file")
    ap.add_argument("--degree", type=int, default=3, choices=[2, 3],
                    help="2 restores GKOS's own quadratic g(t); 3 is the cubic")
    ap.add_argument("--seed", type=int, default=20260821)
    ap.add_argument("--out", default=None, help="parameter CSV (default: per --mode)")
    ap.add_argument("--tag", default="", help="suffix on the output filename")
    g = ap.add_argument_group("smm modes only")
    g.add_argument("--steps", type=int, default=3,
                   help="1 = diagonal weights only; 2 = two-step optimal; >2 iterates")
    g.add_argument("--reps", type=int, default=1000,
                   help="bootstrap replications for the weight matrix S")
    g.add_argument("--wnoise", type=int, default=0,
                   help="extra re-solves with fresh draws of S, to report the sampling "
                        "noise the asymptotic standard errors do NOT contain")
    g.add_argument("--shrink", type=float, default=0.10, help="shrinkage of S to its diagonal")
    g.add_argument("--jobs", type=int, default=8)
    return ap


def run_ols(a, out):
    import gcohort_model as E
    import gcohort_ols as O

    awi = O.average_wage()
    print(f"simulating {a.n:,} individuals over ages 25-55 (for the eu_offset / sdlog / "
          f"censoring diagnostics) ...")
    tables = E.suffix_tables(E.simulate_u(np.random.default_rng(a.seed), a.n))
    rows = O.solve_all(a.sel, a.min_ages, tables, awi, a.degree)
    with open(out, "w") as f:
        f.write(",".join(O.COLS) + "\n")
        for r in rows:
            f.write(f"{r[0]},{r[1]},{r[2]}," + ",".join(f"{v:.6f}" for v in r[3:]) + "\n")
    print(f"wrote {out}  ({len(rows)} blocks)")

    i = O.COLS.index
    rmse = np.array([r[i("rmse")] for r in rows])
    print(f"fit rmse over blocks: median {np.median(rmse):.4f}, "
          f"p90 {np.percentile(rmse, 90):.4f}, max {rmse.max():.4f} log points")
    for label in ("female", "male"):
        sub = [r for r in rows if r[0] == label]
        eu = np.median([r[i("eu_offset")] for r in sub])
        gap = np.median([r[i("sdlog_gap")] for r in sub])
        print(f"{label}: eu_offset (add to an SMM g0 to compare with this g0) median {eu:+.3f};"
              f" UNTARGETED sdlog gap median {gap:+.3f}")


def main(argv=None):
    a = build_parser().parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    out = a.out or f"{OUT}/g_cohort_{a.mode.replace('-', '_')}{a.tag}.csv"
    print("=" * 30 + f" mode: {a.mode}", flush=True)
    if a.mode == "ols":
        run_ols(a, out)
    else:
        import gcohort_smm
        gcohort_smm.run(a, out, SMM_MOMENTS[a.mode])


if __name__ == "__main__":
    main()
