#!/usr/bin/env python
"""THE ESTIMATOR: one joint solve per year that combines both data terms, borrows strength
along age, and pins the year's aggregate to the published benchmark.

Per (year, sex, single-year age) cell the objective is a convex combination of the two data
terms, and the year's objective adds a roughness penalty coupling neighbouring ages:

    J_year(theta) = Sum_c [ (1-lam) negll_c + lam n_c Q_c ]          <- data
                  + eta Sum_c w_c E[X]_c                             <- aggregate constraint
                  + rho Sum_a huber( sqrt(Omega) D2 g_a )            <- roughness along age

  negll   obj_mle    doubly censored EPUF likelihood (dPlN men, lognormal mixture women)
  Q       obj_gmm    SHAPE-ONLY GMM criterion on the published GKSW targets, level projected out
  E[X]    xs_model   analytic uncapped mean; w_c the cell's share of the year's workers
  g       xs_model   the 6 regime-invariant functionals the penalty acts on

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

# rho0 target: the penalty is worth this fraction of the fit at the unsmoothed solution. rho
# trades against the mean constraint in ONE direction: smoothing shrinks the cross-cell
# dispersion of the log-scale g slots and E[X] is exponential in them, so by Jensen the year's
# aggregate mean is biased DOWN. eta > 0 can only thin, so the smoothed fit must still
# OVERSHOOT for the constraint to pin it exactly; where it undershoots the year is left as
# fitted. Calibrated by a 5-point sweep of full re-solves -- 1e-4 is an INTERIOR optimum, not
# "as little smoothing as possible". Retune with --rho; judge on the heatmaps + the validation
# figure.
SMOOTH_FRAC = 1e-4
RHO_STEPS  = 4                  # rho-continuation steps
RHO0_START = 30.0               # continuation begins at RHO0_START * rho_target
# Gauss-Seidel effort. Read from the environment because the year workers are SPAWNED (macOS),
# so they re-import this module and never see globals rebound in main(); env vars they inherit.
CONT_PASSES  = int(os.environ.get("XS_CONT_PASSES", "2"))
ETA_PASSES   = int(os.environ.get("XS_ETA_PASSES", "3"))
BISECT_ITERS = 18               # bisection steps for eta
GS_TOL     = 1e-3               # early-stop a pass sweep: max |dg| across cells
HUBER_K    = 1.5                # Huber knee, in standardized (Omega-scaled) roughness units
STAGE4     = 2                  # max basin re-check rounds
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
def _bounds(sex, floor_alpha):
    """Structural boxes (xs_model): constrain the degeneracies away rather than hoping a
    penalty outvotes an unbounded likelihood. alpha is floored above 1 whenever anything
    downstream will take the uncapped mean, which diverges as alpha -> 1."""
    if sex == 1:
        amin = np.log(xm.ALPHA_MIN) if floor_alpha else np.log(0.05)
        return [(amin, np.log(500.0)), (np.log(0.05), np.log(500.0)),
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
        val = (1.0 - lam) * negll(theta) if qfun is not None else negll(theta)
        if qfun is not None:
            q = qfun(theta)
            if not np.isfinite(q):
                return 1e18
            val += lam * n * q
        if mean_pen is not None:
            eta, w = mean_pen
            mth = cell_mean(sex, theta)
            if not np.isfinite(mth):
                return 1e18
            val += eta * w * mth
        if smooth_pen is not None:
            wv, gt = smooth_pen
            d = gf(theta, thi) - gt
            sp = float(np.dot(wv, d * d))
            if not np.isfinite(sp):
                return 1e18
            val += sp
        return val if np.isfinite(val) else 1e18

    bnds = _bounds(sex, floor_alpha=(mean_pen is not None or qfun is not None))
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
def load_year(year):
    """Every positive-earnings row of one year as (sex, age, earnings).

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
         "ORDER BY d.sex, age, a.earnings")
    out = subprocess.run(["duckdb", "-readonly", xm.DB, "-noheader", "-csv", "-c", q],
                         capture_output=True, text=True, check=True).stdout
    return pd.read_csv(StringIO(out), header=None, names=["sex", "age", "earnings"])


def cells_by_age(df, min_n=MIN_N):
    return {sex: {int(a): sub["earnings"].to_numpy(dtype=float)
                  for a, sub in df.loc[df["sex"] == sex].groupby("age") if len(sub) >= min_n}
            for sex in SEXES}


# --------------------------------------------------------------------------- stage 0
def _candidates(sex, x, lowc, highc, logcap, gmm, seeds):
    """Top-K optima kept per cell, DEDUPED IN g-SPACE. Raw-parameter distance is meaningless
    across a regime flip -- the mixture's components swap roles, the dPlN trades body against
    tail -- so a theta-space dedupe keeps K copies of one basin while believing they differ.
    The stored `data` is the cell's contribution to the joint objective in summed units, which
    is what Viterbi prices against rho x roughness."""
    lam, qfun = gmm if gmm is not None else (0.0, None)
    ent = []
    for s in seeds:
        row, th = fit_cell(sex, x, lowc, highc, start=s, gmm=gmm)
        if qfun is None:
            data = row["negll"]
        else:
            q = qfun(th)
            data = (1.0 - lam) * row["negll"] + lam * row["n"] * q if np.isfinite(q) else np.inf
        ent.append(dict(theta=th, negll=float(data), g=GFUN[sex](th, logcap), row=row))
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
    year, lam, gmm_iters, tgt_year = args
    df = load_year(year)
    highc = float(df["earnings"].max()) - xm.HIGH_MARGIN
    logcap = np.log(highc)
    by_age = cells_by_age(df)
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
                ages_win=ages_win, cand=cand, best_row=best_row, W=Wmat)


# --------------------------------------------------------------------------- Omega, rho
def second_diffs(g_by_age, ages):
    """Row-stacked second differences g[a+1]-2g[a]+g[a-1] over the interior ages."""
    return np.array([g_by_age[ages[i + 1]] - 2 * g_by_age[ages[i]] + g_by_age[ages[i - 1]]
                     for i in range(1, len(ages) - 1)]) if len(ages) >= 3 else np.empty((0, NG))


def freeze_omega_rho(metas, smooth_frac):
    """Freeze, once and GLOBALLY, from the stage-0 fits:
      Omega_j = 1/MAD_a[(Dg)_j]^2   (per sex, pooled over the whole grid), and
      rho0 in per-observation units so the penalty is worth ~smooth_frac of the fit at the
      unsmoothed solution: rho0 = smooth_frac * (total data term) / Sum_year ntot * roughness.
    Global, not per-year, so one rho means the same thing everywhere -- which is also why a
    single-year run cannot reproduce a full run's surface. The robust (Huber) roughness keeps
    a few genuine regime jumps from inflating rho0."""
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
    data_tot, P1 = 0.0, 0.0
    for m in metas:
        for sex in SEXES:
            cs = m["cand"][sex]
            data_tot += sum(cs[a][0]["negll"] for a in cs)
            best = {a: cs[a][0]["g"] for a in cs}
            P1 += m["ntot"] * roughness(best, sorted(best), Omega[sex])
    return Omega, smooth_frac * data_tot / max(P1, 1e-9)


# --------------------------------------------------------------------------- penalty pieces
def _huber_terms(r, omega):
    """Standardized roughness u = sqrt(Omega)*r and its Huber value + IRLS weight."""
    u = np.sqrt(omega) * r
    au = np.abs(u)
    val = np.where(au <= HUBER_K, u * u, HUBER_K * (2 * au - HUBER_K))
    hw = np.where(au <= HUBER_K, 1.0, HUBER_K / np.maximum(au, 1e-12))
    return val, hw


def roughness(g_by_age, ages, omega):
    """rho-free robust roughness Sum_a Sum_j huber(sqrt(Omega_j)(Dg)_{a,j}) -- the Viterbi core.

    The operator is a ROBUST (Huber) second difference along age, and the robustness is the
    point: basin-hopping is already handled by g plus Viterbi, so this operator's remaining job
    is to protect GENUINE regime switches (retirement, young-age entry). A quadratic ||Dg||^2
    charges a true step quadratically and smears it; the Huber loss crushes sawtooth but lets a
    sparse isolated jump through at ~linear cost. It is location-free -- no cutoff to hard-code,
    and the year-varying retirement age is handled automatically."""
    tot = 0.0
    for i in range(1, len(ages) - 1):
        r = g_by_age[ages[i + 1]] - 2 * g_by_age[ages[i]] + g_by_age[ages[i - 1]]
        tot += float(_huber_terms(r, omega)[0].sum())
    return tot


def smooth_pen(sex_g, a, ages, omega, rho):
    """(wvec, target) for the Gauss-Seidel pull of cell a's g toward its second-difference
    neighbour target -- the IRLS quadratic surrogate of the robust roughness. None at endpoints.

    All g slots are pulled equally. Restricting the pull to the body (zeroing the upper-tail
    slot, on the theory that the mean constraint should own what the cap censors) was tried and
    made the aggregate-mean bias slightly WORSE -- the bias is not a tail effect, it is Jensen
    acting on every smoothed log-scale slot at once."""
    i = ages.index(a)
    if i == 0 or i == len(ages) - 1:
        return None
    gm, gp = sex_g[ages[i - 1]], sex_g[ages[i + 1]]
    r = gp - 2 * sex_g[a] + gm            # current second difference at a
    hw = _huber_terms(r, omega)[1]
    return 4.0 * rho * hw * omega, 0.5 * (gm + gp)


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
                cost = np.array([dp[i, j] + rho * float(_huber_terms(
                    G[ap][l] - 2 * G[a][j] + G[am][i], omega)[0].sum()) for i in range(Km)])
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
    by_age = cells_by_age(load_year(year))
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
                rc[a] = [dict(theta=th, negll=r["negll"], g=GFUN[sex](th, logcap), row=r)
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
         smooth_frac=SMOOTH_FRAC, constrain=True, plots=True, raw=RAW, out=OUT):
    if not 0.0 <= lam < 1.0:
        raise SystemExit("--lam must be in [0, 1): at lam = 1 the GMM criterion is shape-only "
                         "and does not identify the level (obj_gmm)")
    target = ass_uncapped_per_worker() if constrain else {}
    tgt = obj_gmm.guv_targets(YEARS) if lam > 0.0 else {}
    by_year = {y: {(s, a): v for (yy, s, a), v in tgt.items() if yy == y} for y in YEARS}
    t0 = time.time()

    print(f"=== stage 0: per-cell fits (lam={lam}, gmm_iters={gmm_iters}, "
          f"{sum(len(v) for v in by_year.values())} guv-covered cells) ===", flush=True)
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        metas = list(ex.map(stage0_year, [(y, lam, gmm_iters, by_year[y]) for y in YEARS]))
    print(f"  {len(metas)} years, {time.time() - t0:.0f}s", flush=True)

    Omega, rho0 = freeze_omega_rho(metas, smooth_frac)
    rho_t = rho0 if rho is None else rho
    rho_grid = list(np.geomspace(rho_t * RHO0_START, rho_t, rho_steps))
    print(f"=== Omega frozen; rho0={rho0:.3g} target={rho_t:.3g} "
          f"grid={[f'{r:.2g}' for r in rho_grid]} ===", flush=True)

    write_csv(raw, [r for m in metas for sex in SEXES for r in m["best_row"][sex].values()])

    print("=== stages 1-4: joint smoothed-constrained solve ===", flush=True)
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
                    help="drop the per-year aggregate-mean constraint (diagnostic)")
    ap.add_argument("--no-plots", action="store_true", help="skip the parameter heatmaps")
    ap.add_argument("--out", default=str(OUT), help="smoothed-surface CSV")
    ap.add_argument("--raw", default=str(RAW), help="raw stage-0 CSV")
    return ap


if __name__ == "__main__":
    a = build_parser().parse_args()
    main(jobs=a.jobs, lam=a.lam, gmm_iters=a.gmm_iters, rho=a.rho, rho_steps=a.rho_steps,
         smooth_frac=a.smooth_frac, constrain=not a.no_constrain, plots=not a.no_plots,
         raw=Path(a.raw), out=Path(a.out))
