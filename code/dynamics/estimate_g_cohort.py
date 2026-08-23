#!/usr/bin/env python
"""Unified entry point for estimating the cohort x sex lifecycle profile g(t).

One script, three estimators of the same object.  Every other parameter of the GKOS
(2021) benchmark process is held FIXED at the published estimate; only the coefficients of

    g(t) = g0 + g1*t + g2*t^2 + g3*t^3,      t = (age - 24)/10

are searched over, separately for each (sex, cohort) block, against the published GKSW
cohort x age moment files in raw_data/guv_quantiles/.

  --mode ols             CMS's estimator: plain per-block OLS of the published moment on
                         an age polynomial, no model inversion.  Reports both CMS's own
                         basis (raw age, net of the SSA average wage) and this project's
                         basis, so it is comparable to CMS's published coefficients AND
                         plottable against the two SMM modes.  Seconds to run; needs
                         replication_repos/CMS for the average-wage series.
                         Implementation: gcohort_ols.py.

  --mode smm-mean        Simulated method of moments on meanlog alone -- 1 moment x 31
                         ages against 4 coefficients, so still over-identified along age
                         and it yields a J test.  This is the model-inversion estimator:
                         g is the deterministic profile that makes the MODEL reproduce
                         the moment after nonemployment and the Ymin censoring.

  --mode smm-quantiles   SMM on the mean AND the published log percentiles
                         (meanlog + p10/p25/p50/p75/p90/p98), 7 moments x 31 ages, with
                         the multi-step optimal weighting.  The weight matrix is
                         bootstrapped from the simulated panel -- individuals resampled
                         once per replication and reused at every age, reproducing the
                         along-age panel correlation of a cohort x age table.
                         Implementation for both SMM modes: gcohort_smm.py.

WHAT SEPARATES THEM, and it is not a detail: --mode ols regresses the OBSERVED moment
directly, so its g absorbs the E[u | u >= log(Ymin) - g] term that the SMM modes strip
out.  The levels are therefore NOT comparable as-is; --mode ols reports the gap per block
as `eu_offset`.  Slopes are much closer, and that is the meaningful comparison.

The published shape moments (sdlog, skewlog, kurtlog) are deliberately NOT offered as a
mode: measured dm/dg is ~0.00-0.02 for all three, because at the GKOS parameters the Ymin
truncation is nearly non-binding among positive earners (the nonemployment shock puts the
low mass at exactly zero, not just above Ymin).  They cannot identify g.  gcohort_smm.py
still exposes them via --moments {all,quantiles} for the specification test they DO
support -- and that test rejects the fixed GKOS calibration in every block.

Outputs (--out overrides, --tag suffixes):

    --mode ols             -> output/dynamics/g_cohort_ols.csv
    --mode smm-mean        -> output/dynamics/g_cohort_smm_mean.csv
    --mode smm-quantiles   -> output/dynamics/g_cohort_smm_quantiles.csv

All three share their first 15 columns (sex, cohort, n_ages, g0..g3, g0_raw..g3_raw,
rmse, max_abs_resid, sdlog_gap, max_censored_share), which is the schema
extrapolate_g_cohort.py and plots/plot_agg_tax_dynamics.py read by name, so any mode's
output is a drop-in for them.  Mode-specific columns follow.

Run from the project root:

    python code/dynamics/estimate_g_cohort.py --mode ols
    python code/dynamics/estimate_g_cohort.py --mode smm-mean      [--jobs 8]
    python code/dynamics/estimate_g_cohort.py --mode smm-quantiles [--jobs 8] [--wnoise 2]
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, "code/dynamics")          # run from project root, per repo convention

OUT = "output/dynamics"
SMM_MOMENTS = {"smm-mean": "mean", "smm-quantiles": "level"}
DEFAULT_OUT = {"ols": "g_cohort_ols.csv",
               "smm-mean": "g_cohort_smm_mean.csv",
               "smm-quantiles": "g_cohort_smm_quantiles.csv"}


def build_parser():
    ap = argparse.ArgumentParser(
        description="Estimate the cohort x sex lifecycle profile g(t) by OLS (CMS) or SMM.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("--mode", choices=("ols", "smm-mean", "smm-quantiles"),
                    default="smm-quantiles", help="which estimator to run")
    ap.add_argument("--n", type=int, default=200_000, help="simulated individuals")
    ap.add_argument("--min-ages", type=int, default=31,
                    help="skip cohorts with fewer observed ages; a cubic fitted to a "
                         "short arc extrapolates wildly outside it")
    ap.add_argument("--sel", default="sel0", help="selection tag of the target file")
    ap.add_argument("--degree", type=int, default=3, choices=[2, 3],
                    help="2 restores GKOS's own quadratic g(t); 3 is the cubic")
    ap.add_argument("--seed", type=int, default=20260821)
    ap.add_argument("--out", default=None, help="parameter CSV (default: per --mode)")
    ap.add_argument("--tag", default="", help="suffix on every output filename")

    g = ap.add_argument_group("smm modes only")
    g.add_argument("--steps", type=int, default=3,
                   help="1 = diagonal weights only; 2 = two-step optimal; >2 iterates")
    g.add_argument("--reps", type=int, default=1000,
                   help="bootstrap replications for the weight matrix S")
    g.add_argument("--wnoise", type=int, default=0,
                   help="extra re-solves with fresh draws of S, to report the sampling "
                        "noise the asymptotic standard errors do NOT contain")
    g.add_argument("--shrink", type=float, default=0.10,
                   help="shrinkage of S toward its diagonal")
    g.add_argument("--jobs", type=int, default=8)
    g.add_argument("--ls", default=None, help="fit CSV to overlay on the comparison figure")
    return ap


def run_ols(a, out):
    import gcohort_model as E
    import gcohort_ols as O

    os.makedirs(OUT, exist_ok=True)
    awi = O.average_wage()
    print(f"simulating {a.n:,} individuals over ages 25-55 "
          f"(for the eu_offset / sdlog / censoring diagnostics) ...")
    tables = E.suffix_tables(E.simulate_u(np.random.default_rng(a.seed), a.n))
    rows, fits = O.solve_all(a.sel, a.min_ages, tables, awi, a.degree)

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
        sel = [r for r in rows if r[0] == label]
        eu = np.array([r[i("eu_offset")] for r in sel])
        gap = np.array([r[i("sdlog_gap")] for r in sel])
        print(f"{label}: eu_offset (add to an SMM g0 to compare with this g0) "
              f"median {np.median(eu):+.3f}; UNTARGETED sdlog gap median {np.median(gap):+.3f}")
    E.plot(rows, fits, tag="_ols" + a.tag)


def main(argv=None):
    a = build_parser().parse_args(argv)
    out = a.out or f"{OUT}/{DEFAULT_OUT[a.mode].replace('.csv', a.tag + '.csv')}"

    if a.mode == "ols":
        run_ols(a, out)
        return

    import gcohort_smm
    fwd = ["--moments", SMM_MOMENTS[a.mode], "--n", str(a.n), "--min-ages", str(a.min_ages),
           "--sel", a.sel, "--degree", str(a.degree), "--seed", str(a.seed),
           "--steps", str(a.steps), "--reps", str(a.reps), "--wnoise", str(a.wnoise),
           "--shrink", str(a.shrink), "--jobs", str(a.jobs), "--out", out, "--tag", a.tag]
    if a.ls:
        fwd += ["--ls", a.ls]
    print("=" * 30 + f" mode: {a.mode} (moments: {SMM_MOMENTS[a.mode]})", flush=True)
    gcohort_smm.main(fwd)


if __name__ == "__main__":
    main()
