#!/usr/bin/env python
"""Unified entry point for the per-cell cross-section fits.

One script, two estimators of the same object -- the (year, sex, single-year age)
earnings distribution (dPlN for men, two-component lognormal mixture for women, both
doubly Type-I censored).  They differ in what the DATA TERM is:

  --mode mle       Smoothed, aggregate-constrained censored MLE on EPUF microdata alone.
                   Per year: multi-start stage 0, Viterbi basin selection along age,
                   rho-continuation Gauss-Seidel smoothing of the regime-invariant
                   functionals g(theta), and an eta search that pins the year's uncapped
                   aggregate mean to the published ASS benchmark.  Implementation:
                   crosssec_mle.py.  This is the canonical pipeline -- the surface that
                   feeds extrapolate_params.py and the aggregate validation.

  --mode mle-gmm   Convex combination of that censored likelihood with an iterated GMM
                   criterion on the published GKSW (guv) sel0 cohort x age targets:

                       (1 - lam) * negll(theta) / n  +  lam * r(theta)' W r(theta)

                   with r the 10-vector of residuals against meanlog/sdlog/skewlog/
                   kurtlog + p10..p98.  Cells with no guv counterpart fall back to pure
                   censored MLE, so the surface stays complete; years 2007-13 have guv
                   targets but no microdata and are fit by pure GMM.  Implementation:
                   crosssec_gmm.py.  NOTE it deliberately drops the aggregate-mean
                   constraint -- see that module's docstring before feeding its output
                   to EPUF-denominated aggregate validation.

  --mode both      Run mle then mle-gmm, writing both surfaces.

lam = 0 reduces mle-gmm to the censored MLE (but on THIS mode's cell floor and rho
calibration, which differ -- see crosssec_gmm.py -- so it is not identical to --mode mle);
lam = 1 makes every guv-covered cell pure GMM.

Output filenames are unchanged from the two scripts this replaces, so every downstream
consumer (extrapolate_params.py, the plots/ scripts) reads them as before:

    --mode mle      -> output/cross_sections/cross_section_params_smoothed.csv
                       output/cross_sections/cross_section_params.csv        (raw stage 0)
    --mode mle-gmm  -> output/cross_sections/cross_section_params_guvgmm_smoothed.csv
                       output/cross_sections/cross_section_params_guvgmm.csv (--no-smooth)

Run from the project root:

    python code/cross_sections/estimate_cross_sections.py --mode mle     [--jobs N] [--rho R]
    python code/cross_sections/estimate_cross_sections.py --mode mle-gmm [--lam L] [--gmm-iters K]
"""
import argparse
import sys

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention


def build_parser():
    ap = argparse.ArgumentParser(
        description="Per-cell cross-section fits: censored MLE, or MLE+GMM against the "
                    "published GKSW targets.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("--mode", choices=("mle", "mle-gmm", "both"), default="mle",
                    help="which data term to fit")
    ap.add_argument("--jobs", type=int, default=None, help="parallel year workers")
    ap.add_argument("--rho", type=float, default=None,
                    help="roughness penalty; overrides the mode's SMOOTH_FRAC calibration")
    ap.add_argument("--no-plots", action="store_true",
                    help="skip the parameter heatmaps (mle mode)")

    g = ap.add_argument_group("mle only")
    g.add_argument("--rho-steps", type=int, default=None, help="rho-continuation steps")

    g = ap.add_argument_group("mle-gmm only")
    g.add_argument("--lam", type=float, default=None,
                   help="convex weight on the GMM criterion, in [0, 1]")
    g.add_argument("--gmm-iters", type=int, default=None,
                   help="weight-matrix updates after the iteration-0 fit")
    g.add_argument("--smooth-frac", type=float, default=None, help="rho calibration")
    g.add_argument("--no-smooth", action="store_true",
                   help="independent per-cell fits (skip the joint smoothed solve)")
    g.add_argument("--out", default=None, help="override the output CSV path")
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)

    if a.mode in ("mle", "both"):
        import crosssec_mle
        kw = dict(jobs=a.jobs, plots=not a.no_plots)
        if a.rho is not None:       kw["rho"] = a.rho
        if a.rho_steps is not None: kw["rho_steps"] = a.rho_steps
        print("=" * 30 + " mode: mle (smoothed, aggregate-constrained censored MLE)",
              flush=True)
        crosssec_mle.main(**kw)

    if a.mode in ("mle-gmm", "both"):
        from pathlib import Path
        import crosssec_gmm
        kw = dict(jobs=a.jobs, smooth=not a.no_smooth)
        if a.lam is not None:         kw["lam"] = a.lam
        if a.gmm_iters is not None:   kw["gmm_iters"] = a.gmm_iters
        if a.rho is not None:         kw["rho"] = a.rho
        if a.smooth_frac is not None: kw["smooth_frac"] = a.smooth_frac
        if a.out is not None:         kw["out"] = Path(a.out)
        print("=" * 30 + " mode: mle-gmm (convex combination with the GKSW targets)",
              flush=True)
        crosssec_gmm.main(**kw)


if __name__ == "__main__":
    main()
