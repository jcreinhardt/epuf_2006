#!/usr/bin/env python
"""Joint smoothed-constrained MLE of the earnings cross-section for every
(year, sex, single-year age) cell -> one tidy CSV of fitted parameters.

This is the single optimization stage of the cross-section pipeline. It implements
the `smoothed-constrained-mle` skill: fit each cell's censored distribution (dPlN for
men, lognormal mixture for women) while, WITHIN one joint solve per year,

  (1) borrowing strength across neighbouring ages -- a roughness penalty on the cells'
      regime-invariant FUNCTIONALS g(theta) (log-scale location/dispersion/skew, censoring
      rate, tail measures; all closed form), NOT the raw parameters (which flip meaning
      across the mixture's component swaps and the dPlN body/tail reparameterizations); and
  (2) pinning the year's UNCAPPED aggregate mean to the published ASS benchmark -- one
      scalar multiplier eta per year, shared across BOTH sexes, root-found on the
      composition-weighted E[X].

Smoothing sits INSIDE the eta loop (constrain-then-smooth or smooth-then-constrain both
break one of the two -- skill Sec.12). The roughness operator is a ROBUST (Huber) second
difference along age: it crushes the finite-sample sawtooth of basin-hopping but lets a
genuine, isolated regime jump (retirement, young-age entry) through at ~linear cost, so
the real switches survive instead of being smeared. Basin-hopping proper is handled up
front by the regime-invariant g plus a Viterbi basin selection over multi-start candidates.

Algorithm per year (constraint group; smoothing nested within, so years are independent
and run in parallel -- skill Sec.1,7):

  stage 0  multi-start MLE per cell, keep top-K optima deduped in g-space
  (Omega, rho: frozen ONCE, globally, from the stage-0 fits)
  stage 1  Viterbi basin selection along age at the target rho
  stage 2  rho-continuation (graduated non-convexity): Gauss-Seidel sweeps, eta=0
  stage 3  eta search at target rho (pure restart-from-base per eval; two-sided, best-tracking)
  stage 4  re-check basins at the converged eta; re-seed + redo 2-3 if any cell moved

  python code/cross_sections/estimate_cross_sections.py [--jobs N] [--rho R] [--rho-steps S]
    -> output/cross_sections/cross_section_params_smoothed.csv   (smoothed+constrained; feeds extrapolate)
       output/cross_sections/cross_section_params.csv            (raw stage-0 fits; for the raw heatmap)
       plots/param_heatmaps_{men,women}{,_smoothed}.pdf/.png     (raw vs penalized surfaces)
"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import csv
import sys
import time
import copy
import subprocess
from io import StringIO
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd
import crosssec_fit as cf

YEARS      = range(1951, 2007)
MIN_N      = 1000               # skip cells with fewer positive-earnings observations
MATCH_AGES = (15, 77)           # cells entering the year's aggregate-mean constraint
ASS_XLSX   = Path("raw_data/annual_statistical_supplement.xlsx")
MOMENT_TOL = 1e-3               # relative tolerance on the per-year aggregate-mean match
ETA_HI     = 256.0             # ceiling on the per-year multiplier (tail fully thinned before this)
K_CAND     = 3                 # top-K multi-start candidates kept per cell (skill Sec.8)
DEDUPE     = 5e-2              # min g-distance between distinct candidates
# rho0 target: the penalty is worth this fraction of the fit at the unsmoothed solution, calibrated
# by hand off the path below (skill Sec.6). rho trades against the mean constraint, and in ONE
# direction only. Smoothing shrinks the cross-cell dispersion of the log-scale quantities, and E[X]
# is exponential in them, so by Jensen the year's aggregate mean is biased DOWN -- intrinsic to
# smoothing in logs and aggregating in levels, not a tail artifact (zeroing the tail slot out of the
# penalty was tried and did not help). eta>0 can only thin, so the smoothed fit must still OVERSHOOT
# for the constraint to pin it exactly; where it undershoots, the year is simply left as fitted.
#     frac     ratio@eta=0: 1990 / 2000        roughness cut (1990)
#     3e-4        0.988   / 0.998                   83%
#     1e-4        0.9955  / 1.012 -> pinned         70%   <- chosen
#     3e-5        1.010   / 1.014 -> both pinned    52%
# At 1e-4 the tight-cap years (which overshoot 3-4x) and most loose-cap years pin exactly; the worst
# case (1990) is left 0.45% under. Retune with --rho; judge on the heatmaps + the validation figure.
SMOOTH_FRAC = 1e-4
RHO_STEPS  = 4                # rho-continuation steps (skill Sec.7)
RHO0_START = 30.0             # continuation begins at RHO0_START * rho_target
# Gauss-Seidel effort. Read from the environment because the year workers are SPAWNED (macOS), so
# they re-import this module and never see globals rebound in main(); env vars they do inherit.
CONT_PASSES = int(os.environ.get("XS_CONT_PASSES", "2"))   # passes per rho during continuation
ETA_PASSES  = int(os.environ.get("XS_ETA_PASSES", "3"))    # passes per eta evaluation in the search
BISECT_ITERS = 18            # bisection steps for eta (see the best-tracking search in solve_eta)
GS_TOL     = 1e-3            # early-stop a pass sweep: max |dg| across cells
HUBER_K    = 1.5            # Huber knee, in standardized (Omega-scaled) roughness units
STAGE4     = 2             # max basin re-check rounds
NG         = 6           # length of the functional vector g

RAW = Path("output/cross_sections/cross_section_params.csv")
OUT = Path("output/cross_sections/cross_section_params_smoothed.csv")
# per sex: label, fitter, warm-start packer, g-map, uncapped-mean map
SEX = {1: ("male",   cf.fit_dpln,    cf.dpln_theta, cf.g_dpln,
           lambda r: cf.dpln_mean(r["alpha"], r["beta"], r["nu"], r["tau"])),
       2: ("female", cf.fit_mixture, cf.mix_theta,  cf.g_mix,
           lambda r: cf.mix_mean(r["mu1"], r["mu2"], r["sig1"], r["sig2"], r["w"]))}
COLS = ["year", "sex", "age", "model", "n", "n_low", "n_high", "negll", "converged",
        "alpha", "beta", "nu", "tau", "mu1", "mu2", "sig1", "sig2", "w",
        "lowc", "highc", "p_low_model", "p_high_model", "eta_year"]


# --------------------------------------------------------------------------- data / target
def load_year(year):
    q = ("SELECT d.sex, a.year - d.yob AS age, a.earnings "
         "FROM annual a JOIN demographic d USING(id) "
         f"WHERE a.year={int(year)} AND a.earnings>0 AND d.sex IN (1,2)")
    out = subprocess.run(["duckdb", "-readonly", cf.DB, "-noheader", "-csv", "-c", q],
                         capture_output=True, text=True, check=True).stdout
    return pd.read_csv(StringIO(out), header=None, names=["sex", "age", "earnings"])


def ass_uncapped_target():
    """ASS average UNCAPPED earnings per covered worker ($/worker) per year -- the published
    mean the censored MLE can't see (mass above the cap). Matches plot_agg_tax_total."""
    d = pd.read_excel(ASS_XLSX, sheet_name="data")
    tot = d["aggearn_tot_wage"].fillna(0) + d["aggearn_tot_se"].fillna(0)   # $M
    return {int(y): float(t) * 1e6 / (float(nw) * 1e3)
            for y, t, nw in zip(d["year"], tot, d["num_wrk"])
            if t > 0 and pd.notna(nw) and nw > 0}


def cells_by_age(df):
    return {sex: {int(a): sub["earnings"].to_numpy(dtype=float)
                  for a, sub in df.loc[df["sex"] == sex].groupby("age") if len(sub) >= MIN_N}
            for sex in SEX}


# --------------------------------------------------------------------------- stage 0
def basin_starts(sex, x):
    """A few basin-spanning warm starts (skill Sec.8: grid the regime-defining coordinate,
    moment-match the rest) so top-K captures the competing optima, not one basin K times."""
    yi, _, _ = cf.censor_split(x, cf.LOWC, x.max())
    m, s = yi.mean(), max(yi.std(), 1e-2)
    if sex == 1:                              # grid the upper-tail index alpha
        return [[np.log(a0), np.log(3.0), m, np.log(s)] for a0 in (1.5, 3.0, 20.0)]
    ls = np.log(max(0.7 * s - cf.SIG_FLOOR, 1e-3))   # grid weight x separation
    return [[m + d * s, m - d * s, ls, ls, np.log(w0 / (1 - w0))]
            for w0, d in ((0.3, 0.9), (0.5, 0.4), (0.7, 0.9))]


def stage0_year(year):
    """Unconstrained multi-start fits; return top-K candidates {theta, negll, g} per cell,
    the best row (raw params) for the raw CSV, and the year's plumbing."""
    df = load_year(year)
    highc = float(df["earnings"].max()) - cf.HIGH_MARGIN
    logcap = np.log(highc)
    by_age = cells_by_age(df)
    lo_a, hi_a = MATCH_AGES
    ntot = sum(x.size for sex in SEX for a, x in by_age[sex].items() if lo_a <= a <= hi_a)
    w_of = {sex: {a: (by_age[sex][a].size / ntot if lo_a <= a <= hi_a else 0.0)
                  for a in by_age[sex]} for sex in SEX}
    ages_win = {sex: [a for a in sorted(by_age[sex]) if lo_a <= a <= hi_a and ntot > 0]
                for sex in SEX}

    cand, best_row = {sex: {} for sex in SEX}, {sex: {} for sex in SEX}
    for sex in SEX:
        _, fit, pack, gfun, _ = SEX[sex]
        for a in sorted(by_age[sex]):
            x = by_age[sex][a]
            rows = [fit(x, cf.LOWC, highc, start=s) for s in basin_starts(sex, x)]
            uniq = []
            for r in sorted(rows, key=lambda r: r["negll"]):
                th = pack(r); gv = gfun(th, logcap)
                if all(np.linalg.norm(gv - u["g"]) > DEDUPE for u in uniq):
                    uniq.append(dict(theta=list(th), negll=r["negll"], g=gv, row=r))
                if len(uniq) >= K_CAND:
                    break
            cand[sex][a] = uniq
            best_row[sex][a] = dict(uniq[0]["row"], year=year, sex=sex, age=a,
                                    lowc=cf.LOWC, highc=highc, eta_year=0.0)
    return dict(year=year, highc=highc, logcap=logcap, w_of=w_of, ntot=ntot,
                ages_win=ages_win, cand=cand, best_row=best_row)


# --------------------------------------------------------------------------- Omega, rho
def second_diffs(g_by_age, ages):
    """Row-stacked second differences g[a+1]-2g[a]+g[a-1] over the interior ages."""
    return np.array([g_by_age[ages[i + 1]] - 2 * g_by_age[ages[i]] + g_by_age[ages[i - 1]]
                     for i in range(1, len(ages) - 1)]) if len(ages) >= 3 else np.empty((0, NG))


def freeze_omega_rho(metas):
    """Freeze, once and globally, from the stage-0 fits (skill Sec.5,6):
      Omega_j = 1/MAD_a[(Dg)_j]^2   (per sex, pooled over the whole grid), and
      rho0 (per-observation units) so the penalty is worth ~SMOOTH_FRAC of the fit at the
      unsmoothed solution: rho0 = SMOOTH_FRAC * (total negll) / (Sum_year n_k * robust roughness).
    The n_k factor converts the per-observation rho into the summed-likelihood units the fitters
    minimize; the robust (Huber) roughness keeps a few big regime jumps from inflating rho0."""
    Dg = {sex: [] for sex in SEX}
    for m in metas:
        for sex in SEX:
            best = {a: m["cand"][sex][a][0]["g"] for a in m["cand"][sex]}
            D = second_diffs(best, sorted(best))
            if D.size:
                Dg[sex].append(D)
    Omega = {}
    for sex in SEX:
        D = np.vstack(Dg[sex]) if Dg[sex] else np.ones((1, NG))
        mad = np.median(np.abs(D - np.median(D, axis=0)), axis=0) * 1.4826
        Omega[sex] = 1.0 / np.maximum(mad, 1e-6) ** 2
    negll_tot, P1 = 0.0, 0.0
    for m in metas:
        for sex in SEX:
            cs = m["cand"][sex]
            negll_tot += sum(cs[a][0]["negll"] for a in cs)
            best = {a: cs[a][0]["g"] for a in cs}
            P1 += m["ntot"] * roughness(best, sorted(best), Omega[sex])
    return Omega, SMOOTH_FRAC * negll_tot / max(P1, 1e-9)


# --------------------------------------------------------------------------- penalty pieces
def _huber_terms(r, omega):
    """Standardized roughness u = sqrt(Omega)*r and its Huber value + IRLS weight."""
    u = np.sqrt(omega) * r
    au = np.abs(u)
    val = np.where(au <= HUBER_K, u * u, HUBER_K * (2 * au - HUBER_K))
    hw = np.where(au <= HUBER_K, 1.0, HUBER_K / np.maximum(au, 1e-12))
    return val, hw


def roughness(g_by_age, ages, omega):
    """rho-free robust roughness Sum_a Sum_j huber(sqrt(Omega_j) (Dg)_{a,j}) -- the Viterbi cost core."""
    tot = 0.0
    for i in range(1, len(ages) - 1):
        r = g_by_age[ages[i + 1]] - 2 * g_by_age[ages[i]] + g_by_age[ages[i - 1]]
        tot += float(_huber_terms(r, omega)[0].sum())
    return tot


def smooth_pen(sex_g, a, ages, omega, rho):
    """(wvec, target) for the Gauss-Seidel pull of cell a's g toward its 2nd-difference
    neighbour target -- the IRLS quadratic surrogate of the robust roughness. None at endpoints.

    All g slots are pulled equally. Restricting the pull to the body (zeroing the upper-tail slot,
    on the theory that the mean constraint should own what the cap censors) was tried and made the
    aggregate-mean bias slightly WORSE -- the bias is not a tail effect, it is Jensen acting on
    every smoothed log-scale slot at once. See SMOOTH_FRAC."""
    i = ages.index(a)
    if i == 0 or i == len(ages) - 1:
        return None
    gm, gp = sex_g[ages[i - 1]], sex_g[ages[i + 1]]
    r = gp - 2 * sex_g[a] + gm            # current 2nd difference at a
    hw = _huber_terms(r, omega)[1]
    return 4.0 * rho * hw * omega, 0.5 * (gm + gp)


# --------------------------------------------------------------------------- Viterbi (stage 1)
def viterbi(cands, ages, omega, rho):
    """Pick one candidate per cell minimizing Sum negll + rho*robust-roughness of g, exactly,
    over consecutive triples (state = candidate pair at the last two ages). Returns {age: idx}."""
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


# --------------------------------------------------------------------------- stage 2/3 solve
def solve_year(args):
    """Stages 1-4 for one year at frozen Omega, rho grid. Returns (year, rows, timing)."""
    meta, Omega, rho_grid, target_unc = args
    t_start = time.time()
    year, highc, logcap = meta["year"], meta["highc"], meta["logcap"]
    w_of, ages_win, cand = meta["w_of"], meta["ages_win"], meta["cand"]
    by_age = cells_by_age(load_year(year))
    ages = {sex: sorted(cand[sex]) for sex in SEX}
    winset = {sex: set(ages_win[sex]) for sex in SEX}
    # per-obs rho -> summed-likelihood units (the fitters minimize a SUM over observations):
    # multiply by the year total n_k, which is uniform across the year's cells (not per-cell n_c).
    rho_grid = [r * meta["ntot"] for r in rho_grid]
    rho_t = rho_grid[-1]
    nsolve = [0]

    def gfun(sex, th):
        return SEX[sex][3](th, logcap)

    # stage 1 -- Viterbi basin selection at the target rho
    sel = {sex: viterbi(cand[sex], ages[sex], Omega[sex], rho_t) for sex in SEX}
    theta = {sex: {a: list(cand[sex][a][sel[sex][a]]["theta"]) for a in ages[sex]} for sex in SEX}
    g = {sex: {a: cand[sex][a][sel[sex][a]]["g"] for a in ages[sex]} for sex in SEX}
    rows = {sex: {a: cand[sex][a][sel[sex][a]]["row"] for a in ages[sex]} for sex in SEX}

    def gs_solve(eta, rho, passes):
        for p in range(passes):                 # single-direction passes, alternating up/down
            maxch = 0.0
            for sex in SEX:
                _, fit, pack, _, _ = SEX[sex]
                order = ages[sex] if p % 2 == 0 else ages[sex][::-1]
                for a in order:
                    sp = smooth_pen(g[sex], a, ages[sex], Omega[sex], rho)
                    w = w_of[sex][a] if a in winset[sex] else 0.0
                    r = fit(by_age[sex][a], cf.LOWC, highc, start=theta[sex][a],
                            mean_pen=(eta, w), smooth_pen=sp)
                    nsolve[0] += 1
                    nth = pack(r); ng = gfun(sex, nth)
                    maxch = max(maxch, float(np.max(np.abs(ng - g[sex][a]))))
                    theta[sex][a], g[sex][a], rows[sex][a] = nth, ng, r
            if maxch < GS_TOL:
                break

    def s_full():
        """Composition-weighted uncapped mean over the in-window cells. Non-finite means the
        structural bounds in the fitters failed to contain a cell (alpha<=1, or exp(nu+tau^2/2)
        overflowing) -- raise rather than substitute a sentinel, which would silently drive the
        eta root-find to its ceiling instead of surfacing the bad cell."""
        v = sum(w_of[sex][a] * SEX[sex][4](rows[sex][a]) for sex in SEX for a in ages_win[sex])
        if not np.isfinite(v):
            bad = [(sex, a) for sex in SEX for a in ages_win[sex]
                   if not np.isfinite(SEX[sex][4](rows[sex][a]))]
            raise FloatingPointError(f"{year}: non-finite cell mean at {bad[:5]}")
        return v

    # stage 2 -- rho continuation at eta=0 (graduated non-convexity)
    for rho in rho_grid:
        gs_solve(0.0, rho, CONT_PASSES)

    # stage 3 -- eta root-find with the smoothing INSIDE the loop (skill Sec.12: decoupling it
    # breaks the constraint -- doing so cost ~7% on the aggregate). Each S(eta) restarts from the
    # eta=0 base and re-runs Gauss-Seidel at eta, so S is a pure function of eta (brentq needs that);
    # affordable because the binned likelihood + closed-form g make one warm fit ~4 ms.
    # eta >= 0 ONLY, and that is a mathematical constraint, not a modelling preference. The term
    # is +eta*w*E[X]: for eta>0 it is bounded below (E[X]>0) and thinning is well posed. For eta<0
    # it becomes -|eta|*w*E[X] with E[X] ~ 1/(alpha-1) unbounded above as alpha->1, so the objective
    # is UNBOUNDED BELOW -- there is no interior optimum, and once |eta| beats the likelihood
    # curvature every cell slams into the alpha floor at once (measured in 1990: the aggregate
    # jumps from 0.96x the benchmark at eta=-0.05 to 60,000x at eta=-0.1). So a year whose model
    # mean sits BELOW the benchmark is left alone; the fix for that is less smoothing, not a
    # negative multiplier (see SMOOTH_FRAC).
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

        s1 = S(1.0)                                   # log-secant seed (S thins ~exponentially in eta)
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
            # S(eta) is only piecewise continuous -- a cell can change basin under the pull, and
            # S jumps there -- so a root-finder that assumes continuity (brentq) happily converges
            # onto a discontinuity and returns an eta whose S is far from the target (this cost 7%
            # in 1990). Bisecting on the sign while remembering the best-seen eta is robust to that.
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

    # stage 4 -- re-run basin selection at the converged eta (tail thinning can change which basin
    # wins) and CHECK it. The candidate refits here carry mean_pen only, so they are diagnostics,
    # never the answer: adopting them wholesale would overwrite the smoothed+constrained solution
    # with unsmoothed fits and silently break the constraint. Only if a cell genuinely changes basin
    # do we re-seed from the new picks and redo stages 2-3; otherwise the solution stands.
    for _ in range(STAGE4):
        picks, moved = {}, False
        for sex in SEX:
            _, fit, pack, _, _ = SEX[sex]
            rc = {}
            for a in ages[sex]:
                w = w_of[sex][a] if a in winset[sex] else 0.0
                fits = [fit(by_age[sex][a], cf.LOWC, highc, start=c["theta"], mean_pen=(eta, w))
                        for c in cand[sex][a]]
                nsolve[0] += len(fits)
                rc[a] = [dict(theta=pack(r), negll=r["negll"], g=gfun(sex, pack(r)), row=r)
                         for r in fits]
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
    for sex in SEX:
        for a in ages[sex]:
            out.append(dict(rows[sex][a], year=year, sex=sex, age=a,
                            lowc=cf.LOWC, highc=highc, eta_year=eta))
    return year, out, dict(sec=time.time() - t_start, nsolve=nsolve[0], eta=eta)


# --------------------------------------------------------------------------- driver
def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: (r["year"], r["sex"], r["age"]))
    with path.open("w", newline="") as fh:
        wtr = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        wtr.writeheader(); wtr.writerows(rows)


def main(jobs=None, rho=None, rho_steps=RHO_STEPS, plots=True):
    target = ass_uncapped_target()
    t0 = time.time()

    print("=== stage 0: multi-start candidates ===", flush=True)
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        metas = list(ex.map(stage0_year, YEARS))
    print(f"  {len(metas)} years, {time.time() - t0:.0f}s", flush=True)

    Omega, rho0 = freeze_omega_rho(metas)
    rho_t = rho0 if rho is None else rho
    rho_grid = list(np.geomspace(rho_t * RHO0_START, rho_t, rho_steps))
    print(f"=== Omega frozen; rho0={rho0:.3g} target={rho_t:.3g} "
          f"grid={[f'{r:.2g}' for r in rho_grid]} ===", flush=True)

    # raw stage-0 fits + raw heatmap
    write_csv(RAW, [r for m in metas for sex in SEX for r in m["best_row"][sex].values()])

    print("=== stages 1-4: joint smoothed-constrained solve ===", flush=True)
    args = [(m, Omega, rho_grid, target.get(m["year"])) for m in metas]
    rows, timing = [], []
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        for year, yr_rows, tm in ex.map(solve_year, args):
            rows.extend(yr_rows); timing.append((year, tm))
            print(f"  {year}: {len(yr_rows):>3} cells  eta={tm['eta']:.3g}  "
                  f"{tm['nsolve']} solves  {tm['sec']:.1f}s", flush=True)
    write_csv(OUT, rows)

    # runtime hotspots + validation heatmaps (raw vs penalized)
    timing.sort(key=lambda t: -t[1]["sec"])
    tot = sum(t[1]["sec"] for t in timing)
    print(f"\nwrote {len(rows)} rows -> {OUT}   total {time.time() - t0:.0f}s")
    print("  slowest years: " + ", ".join(f"{y}({tm['sec']:.0f}s/{tm['nsolve']})"
                                           for y, tm in timing[:5]) +
          f"  | solve-phase sum {tot:.0f}s")
    if plots:
        sys.path.insert(0, "code/cross_sections/plots")   # figures are a side deliverable:
        import plot_param as pv                          # imported here so the estimator
        pv.main("both", RAW, "")                          # never depends on matplotlib
        pv.main("both", OUT, "_smoothed")
