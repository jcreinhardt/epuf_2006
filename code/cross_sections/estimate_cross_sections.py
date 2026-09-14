#!/usr/bin/env python
"""THE ESTIMATOR: one joint solve per year that combines both data terms, borrows strength
along age, and pins the year's aggregate to the published benchmark.

Per (year, sex, single-year age) cell the objective is a convex combination of the two data
terms, and the year's objective adds a roughness penalty coupling neighbouring ages:

    J_year(theta) = Sum_c [ (1-lam) ( negll_c + eta w_c E[X]_c ) + lam n_c Q_c ]   <- data
                  + rho Sum_{a not free} || sqrt(Omega) D2 g_a ||^2            <- roughness

  negll   obj_mle    doubly censored EPUF likelihood (dPlN men, lognormal mixture women)
  Q       obj_gmm    SHAPE-ONLY GMM criterion on the published GKSW targets, level projected out
  E[X]    xs_model   analytic uncapped mean; w_c the cell's share of the year's workers
  g       xs_model   the 6 functionals the roughness penalty acts on (see below)

A CONSTRAINED MLE convex-combined with the GMM criterion -- note where the parenthesis falls.
The aggregate pull sits INSIDE the likelihood term, because it is a statement about the level
the likelihood identifies, and so must be weighted like the likelihood. Placed outside instead,
a guv cell feels the pull (1-lam)^-1 harder than the MLE-only cell beside it, since only the
former's likelihood is discounted -- eta then means two different things within one year while
the root-find reports a single number.

WHAT EACH INSTRUMENT IS FOR. The censored likelihood identifies the body from EPUF. The GKSW
targets pin SHAPE only (obj_gmm projects the level direction out), because their W-2 earnings
concept differs from EPUF covered earnings and efficient weighting would make that wedge bind
at ~10 sd of meanlog, beating eta. eta pins the year's LEVEL against the published ASS
aggregate, which the likelihood cannot supply where the cap is tight: in 1951-56, 70-75% of
men aged 40 sit above the taxable maximum, the likelihood sees little more than how MANY
exceeded it, and E[X] ~ alpha/(alpha-1) is nearly all tail. Measured, with the pull removed,
those years run 1.4-2.5x the published aggregate while 1980+ lands within 1-3% unaided.

The cost is that plot_agg_tax_total's uncapped row is then partly a restatement of the fit
rather than a check of it, in exactly the years where eta binds. `--no-constrain` recovers the
honest version, and 1980+ is where to read it.

lam = 0 is the pure censored MLE (and reproduces the pipeline this module replaces); lam = 1
would be pure GMM, which does NOT identify the level -- obj_gmm projects that direction out
by design -- so lam < 1 is required and the default is 0.5, the composite-likelihood weighting.

WHY THE TWO DATA TERMS COMPOSE AT ALL. They speak to different things by construction. The
GKSW targets carry GKSW's W-2 earnings concept, ~7-10% above EPUF covered earnings early on;
if the GMM term were allowed to speak to the LEVEL it would fight eta and win, since efficient
weighting makes a 0.08 log-point concept gap ~10 sampling sd's of meanlog. obj_gmm therefore
concentrates the level direction out, so the published series pins SHAPE (dispersion, skew,
kurtosis, quantile spacing) and eta pins LEVEL against the ASS aggregate. Neither instrument
is asked for something it cannot legitimately supply.

UNITS: everything above is in SUMMED-likelihood units -- negll is a sum over observations, so
Q is multiplied by the cell's n, rho by the year's ntot, and the smoothing weights arrive
already scaled. This is deliberately ONE unit system: the per-observation/summed split that
the two predecessor modules ran in parallel needed an n divisor on some terms and not others,
which is exactly how a mean pull silently acquires a per-cell 1/n and stops being the single
scalar the aggregate constraint assumes.

Algorithm per year (years are independent -- the penalty couples ages only -- so they run in
parallel; eta stays a per-year scalar):

  stage 0  per-cell fits; for guv cells the ITERATED GMM weight matrix, then top-K basin
           candidates at the frozen final W, deduped in g-space (not theta-space: a raw
           parameter distance is meaningless across a regime flip)
  (Omega, rho frozen ONCE, globally, from the stage-0 fits)
  stage 1  Viterbi basin selection along age -- exact over consecutive triples
  stage 2  rho-continuation (graduated non-convexity): Gauss-Seidel sweeps at eta = 0
  stage 3  eta search with the smoothing INSIDE the loop; bisection tracking the CLOSEST
           achieved aggregate, because S(eta) is only piecewise continuous
  stage 4  re-check basins at the converged eta; re-seed and redo 2-3 only if a cell moved

    python code/cross_sections/estimate_cross_sections.py [--lam L] [--jobs N] [--rho R]
      -> output/cross_sections/cross_section_params_smoothed.csv   (feeds extrapolate_params)
         output/cross_sections/cross_section_params.csv            (raw stage-0 fits)
         plots/param_heatmaps_{men,women}{,_smoothed}.pdf/.png
"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import csv
import sys
import time
import copy
import argparse
import subprocess
from io import StringIO
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd
from scipy.optimize import minimize

import xs_model as xm
import obj_mle
import obj_gmm
from benchmarks import ass_uncapped_per_worker

YEARS      = range(1951, 2007)
MIN_N      = 1000               # skip cells with fewer positive-earnings observations
MATCH_AGES = (15, 77)           # cells entering the year's aggregate-mean constraint
MOMENT_TOL = 1e-3               # relative tolerance on the per-year aggregate-mean match
ETA_HI     = 256.0              # ceiling on the per-year multiplier
K_CAND     = 3                  # top-K multi-start candidates kept per cell
DEDUPE     = 5e-2               # min g-distance between distinct candidates
LAM        = 0.5                # convex weight on the GMM criterion; see the docstring
GMM_ITERS  = 2                  # weight-matrix updates after the iteration-0 fit
NG         = 6                  # length of the functional vector g

# rho0 target: the penalty is worth this fraction of the fit at the unsmoothed solution.
#
# CHOSEN BY HELD-OUT LIKELIHOOD, 2026-09-10 (calibrate_smooth_frac.py; its figure is
# plots/smooth_frac_calibration.png). The previous 1e-4 came from a sweep judged on the in-sample
# aggregate ratio -- which the constraint pins by construction in every year eta binds, so it
# could not see rho -- and was run under the Huber loss. The replacement fits one half of the
# PEOPLE and scores the censored likelihood of the other half: 2 folds x 8 fractions, 59.8M
# held-out person-years, paired.
#
# WHY 3e-4 AND NOT THE 3e-3 THE PRE-REGISTERED RULE PICKED. On 1957-2006 the rule picks 3e-3, but
# that win is carried by 1957-79, still under a binding cap with eta ~ 3, where men's upper tail
# is partly unidentified -- the mechanism that already excludes 1951-56 (CLAUDE.md open item 3).
# On 1980-2006, the least-censored years and the ones the criterion is most trustworthy in, the
# same rule picks 3e-4 (band 3e-4, 1e-3) and 3e-3 is resolved WORSE, +1,352 +/- 33 nats.
#
# AND THE JENSEN CEILING BINDS. Smoothing shrinks the cross-cell dispersion of the log-scale g
# slots and E[X] is exponential in them, so the year's aggregate mean is biased DOWN -- and eta
# can only thin, so a year left short stays short. MEASURED at full sample, uncapped / ASS:
#   1e-4   0.9997 [0.994-1.003]   eta = 0 in  4 years   0 years >1% short
#   3e-4   0.9996 [0.990-1.002]   eta = 0 in  5 years   0 years >1% short
#   3e-3   0.9977 [0.974-1.006]   eta = 0 in 17 years   5 years >1% short (worst 2000, 0.974)
# Raising SMOOTH_FRAC past 3e-4 needs the two-sided pull of CLAUDE.md open item 5 first.
SMOOTH_FRAC = 3e-4
RHO_STEPS  = 4                  # rho-continuation steps
RHO0_START = 30.0               # continuation begins at RHO0_START * rho_target
# Gauss-Seidel effort. Read from the environment because the year workers are SPAWNED (macOS),
# so they re-import this module and never see globals rebound in main(); env vars they inherit.
CONT_PASSES  = int(os.environ.get("XS_CONT_PASSES", "2"))
ETA_PASSES   = int(os.environ.get("XS_ETA_PASSES", "3"))
BISECT_ITERS = 18               # bisection steps for eta
GS_TOL     = 1e-3               # early-stop a pass sweep: max |dg| across cells
STAGE4     = 2                  # max basin re-check rounds
# Steps into these ages (inclusive) are EXEMPT from the roughness penalty -- the retirement
# transition, which is a real feature of the profile and not something to smooth away.
#
# It is a WINDOW, not the single age 65, because that is what the unsmoothed fits show. The
# drop in E logY spans 62-70 against a baseline of ~-0.035/year, and the largest single step
# is at 66 (men -0.199, women -0.213), not 65 (-0.161 / -0.124). D2 charges CURVATURE, not
# slope, so a steady retirement decline is nearly free already; what it charges is the two
# CORNERS where the decline starts and stops, and those sit at 63 (+0.103) and 66 (+0.109) --
# one year after each Social Security threshold (62 early eligibility, 65 full), the lag a
# mid-year retirement produces as a partial year followed by a full one. Exempting 65 alone
# would have missed both.
#
# Env var, not a CLI flag: the year workers are SPAWNED, so a global rebound in main() never
# reaches them. Format "lo:hi"; set XS_FREE_STEPS=":" to penalize everything.
def _parse_free_steps(spec):
    """"lo:hi" -> (lo, hi); ":" -> None, meaning penalize every second difference.

    Validated at import so a malformed XS_FREE_STEPS fails here, with the offending value in
    hand, rather than as an unpacking error inside a spawned worker three minutes in."""
    if spec == ":":
        return None
    try:
        lo, hi = (int(v) for v in spec.split(":"))
    except ValueError:
        raise SystemExit(f'XS_FREE_STEPS must be "lo:hi" or ":", got {spec!r}') from None
    if lo > hi:
        raise SystemExit(f"XS_FREE_STEPS lo must not exceed hi, got {spec!r}")
    return lo, hi


FREE_STEPS = _parse_free_steps(os.environ.get("XS_FREE_STEPS", "62:67"))


def free_d2(a):
    """Is the second difference CENTRED at age a exempt? D2(a) = step(a+1) - step(a), so it
    straddles an exempt step whenever either of those two steps is in the window."""
    if FREE_STEPS is None:
        return False
    lo, hi = FREE_STEPS
    return lo - 1 <= a <= hi
# L-BFGS-B stopping. COLD (fresh multi-start) is thorough; WARM (an inner-loop solve seeded
# from the previous state) starts near-optimal, so a loose gtol stops it in 1-2 iterations --
# the joint solve calls it tens of times per cell. Both are calibrated to SUMMED-likelihood
# gradient scale, which is the only scale this module ever works in.
COLD_OPTS = dict(maxiter=200, ftol=1e-9, gtol=1e-6)
WARM_OPTS = dict(maxiter=40,  ftol=1e-6, gtol=1e-3)

RAW = Path("output/cross_sections/cross_section_params.csv")
OUT = Path("output/cross_sections/cross_section_params_smoothed.csv")
COLS = ["year", "sex", "age", "model", "n", "n_low", "n_high", "negll", "converged",
        "alpha", "beta", "nu", "tau", "mu1", "mu2", "sig1", "sig2", "w",
        "lowc", "highc", "p_low_model", "p_high_model", "eta_year",
        "lam", "gmm_q", "gmm_chi2", "has_guv", "wedge"]
SEXES = (1, 2)
PACK  = {1: xm.dpln_theta, 2: xm.mix_theta}
GFUN  = {1: xm.g_dpln,     2: xm.g_mix}


# --------------------------------------------------------------------------- the fitter
def _bounds(sex):
    """Structural boxes (xs_model): constrain the degeneracies away rather than hoping a
    penalty outvotes an unbounded likelihood.

    ALPHA_MIN applies ALWAYS, not only under the mean pull as it did while that pull was the
    default. alpha <= 1 gives an INFINITE uncapped mean, and it is a symptom of the upper tail
    being unidentified under the cap rather than a finding about earnings -- unconstrained
    censored MLE put 374 of 3326 men's cells there, up to 15% of a year's workers, which makes
    the year's aggregate undefined rather than merely biased. The floor does not rescue such a
    cell (at 1.05 the mean is still 20x the scale), it just keeps every downstream aggregate
    arithmetic rather than nan."""
    if sex == 1:
        return [(np.log(xm.ALPHA_MIN), np.log(500.0)), (np.log(0.05), np.log(500.0)),
                (xm.NU_LO, xm.NU_HI), (np.log(xm.TAU_MIN), np.log(xm.TAU_MAX))]
    lo, hi = np.log(xm.SIG_MIN - xm.SIG_FLOOR), np.log(xm.SIG_MAX - xm.SIG_FLOOR)
    return [(4.0, 13.0), (4.0, 13.0), (lo, hi), (lo, hi), (None, None)]


def cell_mean(sex, theta):
    """Analytic uncapped mean E[X] at an internal theta -- xs_model's single implementation,
    so the estimator's notion of the mean and the validation figure's cannot diverge."""
    if sex == 1:
        return xm.dpln_mean(np.exp(theta[0]), np.exp(theta[1]), theta[2], np.exp(theta[3]))
    return xm.mix_mean(*xm._unpack(theta))


def _row(sex, theta, negll, info, converged):
    """One cell's output record, in the fitted parameters' own units."""
    base = dict(n=info["n"], n_low=info["n_low"], n_high=info["n_high"],
                negll=float(negll), converged=bool(converged),
                lowc=info["lowc"], highc=info["highc"])
    if sex == 1:
        a, b, nu, tau = (np.exp(theta[0]), np.exp(theta[1]), theta[2], np.exp(theta[3]))
        return dict(base, model="dpln", alpha=a, beta=b, nu=nu, tau=tau,
                    p_low_model=float(xm.nl_cdf(info["tlo"], a, b, nu, tau)),
                    p_high_model=float(1 - xm.nl_cdf(info["thi"], a, b, nu, tau)))
    mu1, mu2, s1, s2, w = xm._unpack(theta)
    if mu1 < mu2:                       # label: component 1 = higher mean
        mu1, mu2, s1, s2, w = mu2, mu1, s2, s1, 1 - w
    p = (mu1, mu2, s1, s2, w)
    return dict(base, model="mixture", mu1=mu1, mu2=mu2, sig1=s1, sig2=s2, w=w,
                p_low_model=float(xm.mix_cdf(info["tlo"], *p)),
                p_high_model=float(xm.mix_sf(info["thi"], *p)))


def fit_cell(sex, x, lowc, highc, start=None, gmm=None, mean_pen=None, smooth_pen=None,
             opts=None):
    """Fit one cell. The objective, in SUMMED-likelihood units throughout:

        (1-lam) negll(theta) + lam n Q(theta) + eta w E[X](theta) + Sum_j wv_j (g_j - gt_j)^2

    `gmm=(lam, qfun)` supplies the shape-only GMM criterion (obj_gmm) and is None for cells
    with no guv counterpart, which then carry the pure likelihood. `mean_pen=(eta, w)` is the
    aggregate pull; `smooth_pen=(wvec, g_target)` the Gauss-Seidel roughness surrogate, whose
    weights are ALREADY in summed units. `start` warm-starts a single local solve; None runs
    the basin-spanning multi-start.

    Note the reported `negll` is the PURE likelihood at the optimum, never the composite --
    downstream diagnostics compare likelihoods across cells fit under different lam."""
    negll, info = obj_mle.censored_negll(sex, x, lowc, highc)
    n, thi = info["n"], info["thi"]
    lam, qfun = gmm if gmm is not None else (0.0, None)
    gf = GFUN[sex]

    def obj(theta):
        # The aggregate pull rides INSIDE the likelihood term, not alongside the composite.
        # It is a statement about the level the LIKELIHOOD identifies, so it must be weighted
        # like the likelihood: at (1-lam)(negll + eta w E[X]) + lam n Q every cell feels the
        # same pull relative to its own likelihood, guv or not. Adding it outside instead makes
        # a guv cell feel it (1-lam)^-1 times harder than its neighbour -- the likelihood is
        # discounted there and the pull is not -- so eta would mean two different things within
        # one year while the root-find reports one number.
        val = negll(theta)
        if mean_pen is not None:
            eta, w = mean_pen
            mth = cell_mean(sex, theta)
            if not np.isfinite(mth):
                return 1e18
            val += eta * w * mth
        if qfun is not None:
            q = qfun(theta)
            if not np.isfinite(q):
                return 1e18
            val = (1.0 - lam) * val + lam * n * q
        if smooth_pen is not None:
            wv, gt = smooth_pen
            d = gf(theta, thi) - gt
            sp = float(np.dot(wv, d * d))
            if not np.isfinite(sp):
                return 1e18
            val += sp
        return val if np.isfinite(val) else 1e18

    bnds = _bounds(sex)
    if start is not None:
        seeds, opts = [start], (opts or WARM_OPTS)
    else:
        seeds, opts = obj_mle.moment_starts(sex, x, lowc), (opts or COLD_OPTS)
    res = None
    for seed in seeds:
        r = minimize(obj, seed, method="L-BFGS-B", bounds=bnds, options=opts)
        if res is None or r.fun < res.fun:
            res = r
    row = _row(sex, res.x, negll(res.x), info, res.success)
    # The returned theta is re-packed FROM THE ROW, not handed back as the optimizer's own
    # res.x. That round trip is not free -- it costs an ulp -- but it buys the canonical
    # labelling: _row puts the mixture's higher-mean component first, so a warm start always
    # re-enters the next solve in the same orientation. Without it the two components swap
    # freely between Gauss-Seidel passes, and although the likelihood is symmetric under the
    # swap the optimizer's path is not, so neighbouring ages drift into mirrored
    # parameterizations of the same distribution.
    return row, PACK[sex](row)


# --------------------------------------------------------------------------- data
def load_year(year, fold=None):
    """Every positive-earnings row of one year as (sex, age, earnings).

    `fold` keeps one half of the PEOPLE, split by hash(id) % 2 -- the held-out likelihood in
    calibrate_smooth_frac.py. By person rather than by row, so a test person's earnings never
    inform the training fit in any year. hash() is stable within one DuckDB build, and the
    calibration output records which. None (the default) is every row, as before.

    Rows are ORDERED explicitly. DuckDB's scan is parallel and returns rows in a different
    order on every call, and the censored log-likelihood is a float sum over them -- so an
    unordered scan makes the last bits of every objective evaluation depend on the run. In a
    weakly-identified cell (the flat, heavily-censored ones this whole pipeline exists to
    handle) that is enough to tip the optimizer into a different basin: three stage-0 runs of
    identical code on 1990 once differed by up to 10x in fitted alpha. Ordering pins the
    summation order, which is what makes the fits reproducible and any two runs diffable."""
    q = ("SELECT d.sex, a.year - d.yob AS age, a.earnings "
         "FROM annual a JOIN demographic d USING(id) "
         f"WHERE a.year={int(year)} AND a.earnings>0 AND d.sex IN (1,2) "
         + (f"AND hash(a.id) % 2 = {int(fold)} " if fold is not None else "")
         + "ORDER BY d.sex, age, a.earnings")
    out = subprocess.run(["duckdb", "-readonly", xm.DB, "-noheader", "-csv", "-c", q],
                         capture_output=True, text=True, check=True).stdout
    return pd.read_csv(StringIO(out), header=None, names=["sex", "age", "earnings"])


def cells_by_age(df, min_n=MIN_N):
    return {sex: {int(a): sub["earnings"].to_numpy(dtype=float)
                  for a, sub in df.loc[df["sex"] == sex].groupby("age") if len(sub) >= min_n}
            for sex in SEXES}


# --------------------------------------------------------------------------- stage 0
def data_term(row, theta, gmm):
    """A cell's contribution to the year's objective, in summed units -- what Viterbi prices
    against rho x roughness. ONE definition: stage 1 and the stage-4 re-check must rank basins
    by the same cost, or the re-check can adopt a basin that fits the likelihood better and the
    published targets far worse, which is exactly the move stage 4 exists to prevent."""
    val = row["negll"]
    if gmm is None:
        return val
    lam, qfun = gmm[0], gmm[1]
    q = qfun(theta)
    return (1.0 - lam) * val + lam * row["n"] * q if np.isfinite(q) else np.inf


def _candidates(sex, x, lowc, highc, logcap, gmm, seeds):
    """Top-K optima kept per cell, DEDUPED IN g-SPACE. Raw-parameter distance is meaningless
    across a regime flip -- the mixture's components swap roles, the dPlN trades body against
    tail -- so a theta-space dedupe keeps K copies of one basin while believing they differ.
    The stored `data` is the cell's contribution to the joint objective in summed units, which
    is what Viterbi prices against rho x roughness."""
    ent = []
    for s in seeds:
        row, th = fit_cell(sex, x, lowc, highc, start=s, gmm=gmm)
        ent.append(dict(theta=th, negll=float(data_term(row, th, gmm)),
                        g=GFUN[sex](th, logcap), row=row))
    uniq = []
    for e in sorted(ent, key=lambda e: e["negll"]):
        if all(np.linalg.norm(e["g"] - u["g"]) > DEDUPE for u in uniq):
            uniq.append(e)
        if len(uniq) >= K_CAND:
            break
    return uniq


def stage0_year(args):
    """Per-cell fits plus the year's plumbing. Guv-covered cells run the ITERATED GMM first --
    fit at the diagonal iteration-0 W, then recompute the model-implied W at theta-hat and
    refit, `gmm_iters` times -- and the basin candidates are then built at the FROZEN final W,
    so the weight matrix never moves inside the joint solve."""
    year, lam, gmm_iters, tgt_year, fold, min_n = args
    df = load_year(year, fold)
    highc = float(df["earnings"].max()) - xm.HIGH_MARGIN
    logcap = np.log(highc)
    by_age = cells_by_age(df, min_n)
    lo_a, hi_a = MATCH_AGES
    ntot = sum(x.size for sex in SEXES for a, x in by_age[sex].items() if lo_a <= a <= hi_a)
    w_of = {sex: {a: (by_age[sex][a].size / ntot if lo_a <= a <= hi_a else 0.0)
                  for a in by_age[sex]} for sex in SEXES}
    ages_win = {sex: [a for a in sorted(by_age[sex]) if lo_a <= a <= hi_a and ntot > 0]
                for sex in SEXES}
    Sig0 = np.diag(np.concatenate((obj_gmm.MSCALE ** 2, obj_gmm.QARR * (1.0 - obj_gmm.QARR))))

    cand, best_row, Wmat = {s: {} for s in SEXES}, {s: {} for s in SEXES}, {}
    for sex in SEXES:
        for a in sorted(by_age[sex]):
            x = by_age[sex][a]
            tgt = tgt_year.get((sex, a))
            gmm, extra = None, dict(lam=0.0, gmm_q=np.nan, gmm_chi2=np.nan,
                                    has_guv=0, wedge=np.nan)
            seeds = obj_mle.moment_starts(sex, x, xm.LOWC)
            if tgt is not None and lam > 0.0:
                t, mtar, yq = tgt
                resid = obj_gmm.make_resid(sex, t, mtar, yq)
                n_guv = int((x >= np.exp(t)).sum())   # EPUF post-screen count as the guv-n proxy
                W = obj_gmm.weight_matrix(Sig0, n_guv, x.size)
                for j in range(gmm_iters + 1):       # iterated GMM: the outer loop on W
                    row, th = fit_cell(sex, x, xm.LOWC, highc,
                                       gmm=(lam, obj_gmm.make_qfun(resid, W)))
                    if j < gmm_iters:
                        lp, cd, ctr = obj_gmm.row_dists(sex, row)
                        W = obj_gmm.weight_matrix(obj_gmm.sigma_tilde(lp, cd, t, ctr),
                                                  n_guv, x.size)
                qfun = obj_gmm.make_qfun(resid, W)
                gq = qfun(th)
                gmm, Wmat[(sex, a)] = (lam, qfun), W
                seeds = [th] + seeds
                # 2 n gq recovers the chi-square-scale statistic n_guv r'Sigma~^-1 r; with the
                # level projected out its reference is chi2(NR-1), not chi2(NR).
                extra = dict(lam=lam, gmm_q=gq, gmm_chi2=2.0 * x.size * gq, has_guv=1,
                             wedge=obj_gmm.level_wedge(resid, W, th))
            cs = _candidates(sex, x, xm.LOWC, highc, logcap, gmm, seeds)
            cand[sex][a] = cs
            best_row[sex][a] = dict(cs[0]["row"], year=year, sex=sex, age=a,
                                    eta_year=0.0, **extra)
    return dict(year=year, highc=highc, logcap=logcap, w_of=w_of, ntot=ntot,
                ages_win=ages_win, cand=cand, best_row=best_row, W=Wmat,
                fold=fold, min_n=min_n)


# --------------------------------------------------------------------------- Omega, rho
def second_diffs(g_by_age, ages):
    """Row-stacked second differences g[a+1]-2g[a]+g[a-1] over the interior ages."""
    return np.array([g_by_age[ages[i + 1]] - 2 * g_by_age[ages[i]] + g_by_age[ages[i - 1]]
                     for i in range(1, len(ages) - 1)
                     if not free_d2(ages[i])]) if len(ages) >= 3 else np.empty((0, NG))


def freeze_omega_rho(metas, smooth_frac, pen_slots=None):
    """Freeze, once and GLOBALLY, from the stage-0 fits:
      Omega_j = 1/MAD_a[(Dg)_j]^2   (per sex, pooled over the whole grid), and
      rho0 in per-observation units so the penalty is worth ~smooth_frac of the fit at the
      unsmoothed solution: rho0 = smooth_frac * (total data term) / Sum_year ntot * roughness.
    Global, not per-year, so one rho means the same thing everywhere -- which is also why a
    single-year run cannot reproduce a full run's surface.

    Omega stays MAD-based, which is the only robustness left now that the loss is quadratic --
    without it the few huge second differences (men's log alpha, the 16-19 entry ages) would set
    the scale for every slot. rho0 itself is no longer protected: a quadratic charges those
    outliers in full, which inflates the roughness P1 in the denominator and pushes rho0 DOWN,
    while exempting FREE_STEPS removes the retirement jumps and pushes it back UP. The two act
    in opposite directions, so re-read the printed rho0 rather than assuming it carried over."""
    Dg = {sex: [] for sex in SEXES}
    for m in metas:
        for sex in SEXES:
            best = {a: m["cand"][sex][a][0]["g"] for a in m["cand"][sex]}
            D = second_diffs(best, sorted(best))
            if D.size:
                Dg[sex].append(D)
    Omega = {}
    for sex in SEXES:
        D = np.vstack(Dg[sex]) if Dg[sex] else np.ones((1, NG))
        mad = np.median(np.abs(D - np.median(D, axis=0)), axis=0) * 1.4826
        Omega[sex] = 1.0 / np.maximum(mad, 1e-6) ** 2
        if pen_slots is not None:                    # restrict which g slots are smoothed
            keep = np.zeros(NG, dtype=bool)
            keep[list(pen_slots)] = True
            Omega[sex] = np.where(keep, Omega[sex], 0.0)
    # Zeroing Omega is all it takes: roughness, smooth_pen and the Viterbi cost all reach the
    # penalty through it, so an excluded slot contributes no cost and exerts no pull. rho0 is
    # calibrated AFTER the mask, off the masked roughness, so the penalty is still worth
    # smooth_frac of the fit -- the same budget spread over fewer slots, not a smaller budget.
    data_tot, P1 = 0.0, 0.0
    for m in metas:
        for sex in SEXES:
            cs = m["cand"][sex]
            data_tot += sum(cs[a][0]["negll"] for a in cs)
            best = {a: cs[a][0]["g"] for a in cs}
            P1 += m["ntot"] * roughness(best, sorted(best), Omega[sex])
    return Omega, smooth_frac * data_tot / max(P1, 1e-9)


# --------------------------------------------------------------------------- penalty pieces
def rough_terms(r, omega):
    """Standardized roughness u = sqrt(Omega)*r, returned as its quadratic value u^2.

    This replaced a Huber loss. The Huber was location-free: it crushed sawtooth while letting
    ANY sparse, isolated jump through at ~linear cost, so genuine regime switches survived
    wherever they happened to be. A quadratic charges a true step quadratically and will smear
    it, so the breaks now have to be named -- which is what FREE_STEPS does for the retirement
    transition. Anything comparably sharp that is NOT in that window (young-age entry at 16-19
    is the other candidate the fits show) is now smoothed through. That is the trade: implicit,
    automatic robustness exchanged for an explicit, auditable exemption."""
    u = np.sqrt(omega) * r
    return u * u


def roughness(g_by_age, ages, omega):
    """rho-free roughness Sum_{a not free} Sum_j Omega_j (Dg)_{a,j}^2 -- the Viterbi cost core.

    A plain quadratic second difference along age, with the retirement window exempted by
    FREE_STEPS. Note what the operator does and does not charge: D2 is curvature, so a steady
    decline costs almost nothing however steep, and the exemption is really buying the two
    CORNERS at either end of the retirement drop rather than the drop itself."""
    tot = 0.0
    for i in range(1, len(ages) - 1):
        if free_d2(ages[i]):
            continue
        r = g_by_age[ages[i + 1]] - 2 * g_by_age[ages[i]] + g_by_age[ages[i - 1]]
        tot += float(rough_terms(r, omega).sum())
    return tot


def smooth_pen(sex_g, a, ages, omega, rho):
    """(wvec, target) for the Gauss-Seidel pull of cell a's g toward its second-difference
    neighbour target. None at the endpoints and across the exempt retirement window.

    Under a quadratic loss this is EXACT, not a surrogate: holding the neighbours fixed, the
    penalty term centred at a is rho Sum_j Omega_j (g_p - 2 g_a + g_m)_j^2, which in g_a is
    exactly 4 rho Omega_j (g_a - (g_m + g_p)/2)_j^2. The Huber version needed an IRLS reweight
    read off the CURRENT residual; nothing here depends on the current g_a, which is one fewer
    piece of state carried through the Gauss-Seidel sweep.

    Note it uses only the second difference CENTRED at a, though g_a also enters those centred
    at a +/- 1. That is the same coordinate-descent approximation the penalty has always made;
    the sweeps recover the coupling.

    All g slots are pulled equally. Restricting the pull to the body (zeroing the upper-tail
    slot, on the theory that the mean constraint should own what the cap censors) was tried and
    made the aggregate-mean bias slightly WORSE -- the bias is not a tail effect, it is Jensen
    acting on every smoothed log-scale slot at once. `--pen-slots` is the general form of that
    experiment; on 0123 men's alpha comes out 28% rougher and women are unchanged, so the
    default stays all six."""
    i = ages.index(a)
    if i == 0 or i == len(ages) - 1 or free_d2(a):
        return None
    gm, gp = sex_g[ages[i - 1]], sex_g[ages[i + 1]]
    return 4.0 * rho * omega, 0.5 * (gm + gp)


# --------------------------------------------------------------------------- Viterbi
def viterbi(cands, ages, omega, rho):
    """Pick one candidate per cell minimizing Sum data + rho*robust-roughness of g, EXACTLY,
    over consecutive triples (state = the candidate pair at the last two ages)."""
    if len(ages) < 3:
        return {a: int(np.argmin([c["negll"] for c in cands[a]])) for a in ages}
    node = {a: np.array([c["negll"] for c in cands[a]]) for a in ages}
    G = {a: [c["g"] for c in cands[a]] for a in ages}
    a0, a1 = ages[0], ages[1]
    dp = node[a0][:, None] + node[a1][None, :]          # dp[i,j]: cost ending (i@a0, j@a1)
    back = []
    for t in range(2, len(ages)):
        am, a, ap = ages[t - 2], ages[t - 1], ages[t]
        Km, K, Kp = len(G[am]), len(G[a]), len(G[ap])
        new = np.full((K, Kp), np.inf)
        bk = np.zeros((K, Kp), dtype=int)
        for j in range(K):
            for l in range(Kp):
                pen = 0.0 if free_d2(a) else rho
                cost = np.array([dp[i, j] + pen * float(rough_terms(
                    G[ap][l] - 2 * G[a][j] + G[am][i], omega).sum()) for i in range(Km)])
                bk[j, l] = int(np.argmin(cost)); new[j, l] = cost[bk[j, l]] + node[ap][l]
        dp, _ = new, back.append(bk)
    j, l = np.unravel_index(int(np.argmin(dp)), dp.shape)
    sel = {ages[-1]: l, ages[-2]: j}
    for t in range(len(ages) - 1, 1, -1):
        j = back[t - 2][sel[ages[t - 1]], sel[ages[t]]]
        sel[ages[t - 2]] = j
    return sel


# --------------------------------------------------------------------------- stages 1-4
def solve_year(args):
    """Stages 1-4 for one year at frozen Omega and rho grid. Returns (year, rows, timing)."""
    meta, Omega, rho_grid, target_unc, lam, tgt_year = args
    t_start = time.time()
    year, highc, logcap = meta["year"], meta["highc"], meta["logcap"]
    w_of, ages_win, cand = meta["w_of"], meta["ages_win"], meta["cand"]
    # the SAME rows stage 0 saw: a fold-restricted meta must not be re-solved on everyone
    by_age = cells_by_age(load_year(year, meta.get("fold")), meta.get("min_n", MIN_N))
    ages = {sex: sorted(cand[sex]) for sex in SEXES}
    winset = {sex: set(ages_win[sex]) for sex in SEXES}
    # per-obs rho -> summed units (the objective is a SUM over observations): multiply by the
    # year total ntot, uniform across the year's cells -- not the per-cell n.
    rho_grid = [r * meta["ntot"] for r in rho_grid]
    rho_t = rho_grid[-1]
    nsolve = [0]
    # The per-cell GMM criteria are closures, so they cannot be pickled into this worker;
    # rebuild them from the targets and the FROZEN stage-0 W.
    gmm = {}
    for (sex, a), W in meta["W"].items():
        t, mtar, yq = tgt_year[(sex, a)]
        resid = obj_gmm.make_resid(sex, t, mtar, yq)
        gmm[(sex, a)] = (lam, obj_gmm.make_qfun(resid, W), resid, W)

    def gmm_arg(sex, a):
        e = gmm.get((sex, a))
        return None if e is None else (e[0], e[1])

    # stage 1 -- Viterbi basin selection at the target rho
    sel = {sex: viterbi(cand[sex], ages[sex], Omega[sex], rho_t) for sex in SEXES}
    theta = {sex: {a: list(cand[sex][a][sel[sex][a]]["theta"]) for a in ages[sex]} for sex in SEXES}
    g = {sex: {a: cand[sex][a][sel[sex][a]]["g"] for a in ages[sex]} for sex in SEXES}
    rows = {sex: {a: cand[sex][a][sel[sex][a]]["row"] for a in ages[sex]} for sex in SEXES}

    def gs_solve(eta, rho, passes):
        for p in range(passes):                 # single-direction passes, alternating up/down
            maxch = 0.0
            for sex in SEXES:
                order = ages[sex] if p % 2 == 0 else ages[sex][::-1]
                for a in order:
                    sp = smooth_pen(g[sex], a, ages[sex], Omega[sex], rho)
                    w = w_of[sex][a] if a in winset[sex] else 0.0
                    r, nth = fit_cell(sex, by_age[sex][a], xm.LOWC, highc,
                                      start=theta[sex][a], gmm=gmm_arg(sex, a),
                                      mean_pen=(eta, w), smooth_pen=sp)
                    nsolve[0] += 1
                    ng = GFUN[sex](nth, logcap)
                    maxch = max(maxch, float(np.max(np.abs(ng - g[sex][a]))))
                    theta[sex][a], g[sex][a], rows[sex][a] = nth, ng, r
            if maxch < GS_TOL:
                break

    def s_full():
        """Composition-weighted uncapped mean over the in-window cells. Non-finite means the
        structural boxes failed to contain a cell -- raise rather than substitute a sentinel,
        which would silently drive the eta root-find to its ceiling instead of surfacing it."""
        v = sum(w_of[sex][a] * cell_mean(sex, theta[sex][a])
                for sex in SEXES for a in ages_win[sex])
        if not np.isfinite(v):
            bad = [(sex, a) for sex in SEXES for a in ages_win[sex]
                   if not np.isfinite(cell_mean(sex, theta[sex][a]))]
            raise FloatingPointError(f"{year}: non-finite cell mean at {bad[:5]}")
        return v

    # stage 2 -- rho continuation at eta = 0 (graduated non-convexity)
    for rho in rho_grid:
        gs_solve(0.0, rho, CONT_PASSES)

    # stage 3 -- eta search with the smoothing INSIDE the loop. Decoupling the two breaks one
    # of them: constrain-then-smooth loses the constraint (measured: ~7% off), smooth-then-
    # constrain loses the smoothness. Each S(eta) restarts from the eta=0 base and re-runs
    # Gauss-Seidel, so S is a pure function of eta.
    #
    # eta >= 0 ONLY, and that is a mathematical fact, not a modelling preference. The term is
    # +eta*w*E[X]: for eta>0 it is bounded below and thinning has an interior optimum. For
    # eta<0 it is -|eta|*w*E[X] with E[X] ~ 1/(alpha-1) unbounded above, so the objective is
    # UNBOUNDED BELOW and every cell slams into the alpha floor at once (measured in 1990: the
    # aggregate goes from 0.96x the benchmark at eta=-0.05 to 60,000x at eta=-0.1). A year whose
    # model mean sits BELOW the benchmark is therefore left alone; the fix for that is less
    # smoothing, not a negative multiplier.
    def snapshot():
        return copy.deepcopy((theta, g, rows))

    def restore(snap):
        for d, s in zip((theta, g, rows), copy.deepcopy(snap)):
            d.update(s)

    def solve_eta():
        S0 = s_full()
        if (target_unc is None or target_unc <= 0                      # no benchmark, or
                or S0 <= target_unc                                    # undershoot -> leave alone
                or abs(S0 / target_unc - 1.0) <= MOMENT_TOL):          # already matched
            return 0.0
        base = snapshot()

        def S(e):
            restore(base); gs_solve(e, rho_t, ETA_PASSES); return s_full()

        s1 = S(1.0)                            # log-secant seed (S thins ~exponentially in eta)
        e0 = (np.log(target_unc / S0) / np.log(s1 / S0)) if 0 < s1 < S0 else 1.0
        if not np.isfinite(e0) or e0 <= 0:
            e0 = 1.0
        hi = float(np.clip(e0, 0.1, ETA_HI))
        s_hi = S(hi)
        while s_hi > target_unc and hi < ETA_HI:       # grow until the target is bracketed
            hi *= 4.0
            s_hi = S(hi)
        if s_hi > target_unc:                         # target below what thinning can reach
            e = hi
        else:
            # Bisection that TRACKS THE CLOSEST ACHIEVED aggregate rather than a sign change.
            # S(eta) is only piecewise continuous -- a cell can change basin under the pull and
            # S jumps there -- so a root-finder assuming continuity (brentq) happily converges
            # onto a discontinuity and returns an eta whose S is far from the target (this cost
            # 7% in 1990). Bisecting on the sign while remembering the best-seen eta is robust.
            lo_e, hi_e, e, best = 0.0, hi, 0.0, abs(S0 / target_unc - 1.0)
            for _ in range(BISECT_ITERS):
                mid = 0.5 * (lo_e + hi_e)
                v = S(mid)
                if abs(v / target_unc - 1.0) < best:
                    best, e = abs(v / target_unc - 1.0), mid
                if best <= MOMENT_TOL:
                    break
                if v > target_unc:                   # still too heavy -> thin harder
                    lo_e = mid
                else:
                    hi_e = mid
        S(e)                                          # leave state at the returned eta
        return e

    eta = solve_eta()

    # stage 4 -- re-run basin selection at the converged eta (tail thinning can change which
    # basin wins) and CHECK it. The candidate refits here carry mean_pen only, so they are
    # diagnostics, never the answer: adopting them wholesale would overwrite the smoothed,
    # constrained solution with unsmoothed fits and silently break the constraint. Only if a
    # cell genuinely changes basin do we re-seed from the new picks and redo stages 2-3.
    for _ in range(STAGE4):
        picks, moved = {}, False
        for sex in SEXES:
            rc = {}
            for a in ages[sex]:
                w = w_of[sex][a] if a in winset[sex] else 0.0
                fits = [fit_cell(sex, by_age[sex][a], xm.LOWC, highc, start=c["theta"],
                                 gmm=gmm_arg(sex, a), mean_pen=(eta, w))
                        for c in cand[sex][a]]
                nsolve[0] += len(fits)
                # Node cost is the DATA term only -- the same quantity stage 1 ranked by, so
                # the two Viterbi passes are commensurable. Deliberately NOT including the
                # eta*w*E[X] pull the refits above carry: that would let basin choice trade
                # tail-thinness against roughness, which measurably moves the surface (eta by
                # up to 25 in a year) and is a modelling change, not a consistency fix.
                rc[a] = [dict(theta=th, g=GFUN[sex](th, logcap), row=r,
                              negll=float(data_term(r, th, gmm_arg(sex, a))))
                         for r, th in fits]
            newsel = viterbi(rc, ages[sex], Omega[sex], rho_t)
            for a in ages[sex]:
                picks[(sex, a)] = pick = rc[a][newsel[a]]
                moved |= bool(np.linalg.norm(pick["g"] - g[sex][a]) > DEDUPE)
        if not moved:
            break
        for (sex, a), pick in picks.items():        # re-seed, then redo the smooth + constraint
            theta[sex][a], g[sex][a], rows[sex][a] = list(pick["theta"]), pick["g"], pick["row"]
        for rho in rho_grid:
            gs_solve(0.0, rho, CONT_PASSES)
        eta = solve_eta()

    out = []
    for sex in SEXES:
        for a in ages[sex]:
            e = gmm.get((sex, a))
            if e is None:
                extra = dict(lam=0.0, gmm_q=np.nan, gmm_chi2=np.nan, has_guv=0, wedge=np.nan)
            else:
                _, qfun, resid, W = e
                gq = qfun(theta[sex][a])
                extra = dict(lam=lam, gmm_q=gq, gmm_chi2=2.0 * rows[sex][a]["n"] * gq,
                             has_guv=1, wedge=obj_gmm.level_wedge(resid, W, theta[sex][a]))
            out.append(dict(rows[sex][a], year=year, sex=sex, age=a, eta_year=eta, **extra))
    return year, out, dict(sec=time.time() - t_start, nsolve=nsolve[0], eta=eta)


# --------------------------------------------------------------------------- driver
def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: (r["year"], r["sex"], r["age"]))
    with path.open("w", newline="") as fh:
        wtr = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        wtr.writeheader(); wtr.writerows(rows)


def main(jobs=None, lam=LAM, gmm_iters=GMM_ITERS, rho=None, rho_steps=RHO_STEPS,
         smooth_frac=SMOOTH_FRAC, constrain=True, pen_slots=None, plots=True,
         raw=RAW, out=OUT):
    if not 0.0 <= lam < 1.0:
        raise SystemExit("--lam must be in [0, 1): at lam = 1 the GMM criterion is shape-only "
                         "and does not identify the level (obj_gmm)")
    # Checked HERE, not where it is used: pen_slots is not consumed until freeze_omega_rho,
    # which runs after stage 0 -- so a typo would otherwise surface as an IndexError several
    # minutes into a run.
    if pen_slots is not None:
        bad = sorted(set(pen_slots) - set(range(NG)))
        if bad or not pen_slots:
            raise SystemExit(f"--pen-slots must be a non-empty subset of 0..{NG - 1}, "
                             f"got {bad or 'nothing'}")
    target = ass_uncapped_per_worker() if constrain else {}
    tgt = obj_gmm.guv_targets(YEARS) if lam > 0.0 else {}
    by_year = {y: {(s, a): v for (yy, s, a), v in tgt.items() if yy == y} for y in YEARS}
    t0 = time.time()

    print(f"=== stage 0: per-cell fits (lam={lam}, gmm_iters={gmm_iters}, "
          f"{sum(len(v) for v in by_year.values())} guv-covered cells) ===", flush=True)
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        metas = list(ex.map(stage0_year, [(y, lam, gmm_iters, by_year[y], None, MIN_N)
                                           for y in YEARS]))
    print(f"  {len(metas)} years, {time.time() - t0:.0f}s", flush=True)

    Omega, rho0 = freeze_omega_rho(metas, smooth_frac, pen_slots)
    rho_t = rho0 if rho is None else rho
    rho_grid = list(np.geomspace(rho_t * RHO0_START, rho_t, rho_steps))
    print(f"=== Omega frozen on g slots "
          f"{''.join(str(j) for j in (pen_slots if pen_slots is not None else range(NG)))}; "
          f"rho0={rho0:.3g} target={rho_t:.3g} "
          f"grid={[f'{r:.2g}' for r in rho_grid]} ===", flush=True)

    write_csv(raw, [r for m in metas for sex in SEXES for r in m["best_row"][sex].values()])

    print(f"=== stages 1-4: joint smoothed solve"
          f"{' + aggregate constraint' if constrain else ' (UNCONSTRAINED)'} ===", flush=True)
    args = [(m, Omega, rho_grid, target.get(m["year"]), lam, by_year[m["year"]]) for m in metas]
    rows, timing = [], []
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        for year, yr_rows, tm in ex.map(solve_year, args):
            rows.extend(yr_rows); timing.append((year, tm))
            print(f"  {year}: {len(yr_rows):>3} cells  eta={tm['eta']:.3g}  "
                  f"{tm['nsolve']} solves  {tm['sec']:.1f}s", flush=True)
    write_csv(out, rows)

    timing.sort(key=lambda t: -t[1]["sec"])
    tot = sum(t[1]["sec"] for t in timing)
    print(f"\nwrote {len(rows)} rows -> {out}   total {time.time() - t0:.0f}s")
    print("  slowest years: " + ", ".join(f"{y}({tm['sec']:.0f}s/{tm['nsolve']})"
                                          for y, tm in timing[:5]) +
          f"  | solve-phase sum {tot:.0f}s")
    if lam > 0:
        wg = np.array([r["wedge"] for r in rows if r["has_guv"] and np.isfinite(r["wedge"])])
        if wg.size:
            print(f"  GKSW level wedge (log points, diagnostic only): median {np.median(wg):+.3f}"
                  f"  [p10 {np.percentile(wg, 10):+.3f}, p90 {np.percentile(wg, 90):+.3f}]"
                  f"  over {wg.size} cells")
    if plots:
        sys.path.insert(0, "code/cross_sections/plots")   # figures are a side deliverable:
        import plot_param as pv                           # imported here so the estimator
        pv.main("both", raw, "")                          # never depends on matplotlib
        pv.main("both", out, "_smoothed")


def build_parser():
    ap = argparse.ArgumentParser(
        description="Joint per-cell cross-section fits: censored MLE combined with a "
                    "shape-only GMM criterion on the published GKSW targets, smoothed along "
                    "age and pinned to the ASS aggregate.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument("--lam", type=float, default=LAM,
                    help="convex weight on the GMM criterion, in [0, 1); 0 = pure censored MLE")
    ap.add_argument("--gmm-iters", type=int, default=GMM_ITERS,
                    help="weight-matrix updates after the iteration-0 fit")
    ap.add_argument("--jobs", type=int, default=None, help="parallel year workers")
    ap.add_argument("--rho", type=float, default=None,
                    help="roughness penalty; overrides the --smooth-frac calibration")
    ap.add_argument("--smooth-frac", type=float, default=SMOOTH_FRAC,
                    help="rho calibration: penalty as a fraction of the unsmoothed fit")
    ap.add_argument("--rho-steps", type=int, default=RHO_STEPS, help="rho-continuation steps")
    ap.add_argument("--no-constrain", action="store_true",
                    help="drop the per-year aggregate-mean pull, leaving the level to the "
                         "likelihood alone. Diagnostic: it makes plot_agg_tax_total an "
                         "out-of-sample check, at the cost of the tight-cap years.")
    ap.add_argument("--pen-slots", default=None,
                    help="which g slots the roughness penalty acts on, as digits, e.g. 0123 "
                         "for the four common functionals only (E logY, sd logY, skew logY, "
                         "logit S(cap)) -- excluding slots 4-5, which are log-beta/log-alpha "
                         "for men but mean excess either side of the cap for women. Default: "
                         "all six.")
    ap.add_argument("--no-plots", action="store_true", help="skip the parameter heatmaps")
    ap.add_argument("--out", default=str(OUT), help="smoothed-surface CSV")
    ap.add_argument("--raw", default=str(RAW), help="raw stage-0 CSV")
    return ap


if __name__ == "__main__":
    a = build_parser().parse_args()
    main(jobs=a.jobs, lam=a.lam, gmm_iters=a.gmm_iters, rho=a.rho, rho_steps=a.rho_steps,
         smooth_frac=a.smooth_frac, constrain=not a.no_constrain,
         pen_slots=(None if a.pen_slots is None else [int(c) for c in a.pen_slots]),
         plots=not a.no_plots,
         raw=Path(a.raw), out=Path(a.out))
