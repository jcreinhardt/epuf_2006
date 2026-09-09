"""EPUF-disciplined SMM for g(t): the `--mode smm-p50` estimator behind estimate_g_cohort.py.

TWO TARGET BLOCKS, ONE FUNCTIONAL.  GKSW publish cohort x age moments for ages 25-55 only, so
a profile fitted on them alone is unconstrained outside that window and extrapolates badly.
EPUF covers ages 20-70 for the same cohorts.  This mode targets the MEDIAN of log earnings in
both sources -- the one statistic each measures well (EPUF's mean is destroyed by the top
code, GKSW's data carry none, and both medians sit far below the cap in every cell used):

    GKSW cell, ages 25-55:   log p50  ~  g(t) + Q50(u | u >= log(Ymin) - g(t))
    EPUF cell, ages 20-70:   log p50  ~  g(t) + Q50(u | u >= log(Ymin) - g(t)) + delta

Like is matched to like.  Matching a GKSW MEAN to an EPUF MEDIAN would instead force the model
to supply the mean-median difference out of its own u, and it supplies it badly: MEASURED, the
model's mean-minus-median of log earnings is +0.03 against the data's -0.10 to -0.20, a gap of
0.12-0.23 log points that TRENDS at -0.039/decade.  A constant delta cannot absorb a trending
term, so that trend would land in the out-of-span shape -- the thing being estimated.

DELTA, the wedge intercept, is one free parameter per (sex, cohort) block.  EPUF and GKSW are
different populations: GKSW is Kopczuk-Saez-Song commerce-and-industry W-2 wages, EPUF is all
covered earnings including self-employment, agriculture, households, hospitals, education and
public administration.  Their medians differ for reasons that have nothing to do with g, by
-0.063 log points for men and +0.023 for women.  Estimating that rather than assuming it away
is what makes the two blocks commensurable; without it the estimator would read the gap as
information about g and split the difference between two samples, and no weight matrix would
help -- GMM downweights imprecise moments, not biased ones, and EPUF cells carry ~13k
observations each.  Delta is identified by the 31-age OVERLAP, where both sources report the
same cell.  What licenses carrying one constant out of that overlap is that the p50 wedge is
nearly flat in age (slope -0.004 men, -0.007 women per decade) and stable across cohorts (sd
0.008 and 0.014), so extending it from 55 to 70 mis-states it by under 0.01 log points.

THE HINGES are what the out-of-span cells buy.  g is the quadratic plus one-sided terms in
(t25 - t)+ and (t - t55)+, which are identically zero inside 25-55 (gcohort_model.design).  So
the published-moment fit is untouched, and the hinges are identified purely by EPUF outside the
span.  Young-side coverage is complete -- all 27 fitted cohorts have ages 20-24 -- but the old
side runs from 19 cohorts at age 56 down to 5 at 70, and cohorts 1976+ have none, so a block
without at least `min_old` old ages is fitted without that column and the coefficient is filled
afterwards from the cross-cohort mean for its sex.  Those blocks have no out-of-span old data
by construction, so nothing about their g is affected; the fill only gives them a shape to
extrapolate with.

READ THE HINGE AS REDUCED FORM.  What it picks up past 55 is partial retirement and selection
into low-earnings work, which the GKOS process does not contain -- its nonemployment incidence
FALLS with age at z = 0.  For an aggregate that needs mean earnings per covered worker this is
the right object; it is not a wage profile.

WEIGHTING.  Optimal multi-step, as in gcohort_smm: step 1 diagonal, step 2 the full S at the
step-1 estimate, further steps iterate, with COMMON RANDOM NUMBERS so the movement measures S's
theta-dependence rather than Monte-Carlo noise.  S is bootstrapped from the simulated panel
separately per block, individuals resampled once per replication and reused across ages (the
along-age correlation of a cohort x age table is what optimal weighting exists to exploit), and
the two blocks are stacked BLOCK-DIAGONALLY: EPUF is a 1% sample of the population and GKSW a
10% sample of a subpopulation, so their sampling errors are effectively independent.  GKSW cell
sizes are unpublished and proxied by EPUF's own counts times GKSW_SCALE; only the RATIO of the
two blocks' precisions matters and the estimator is insensitive to it, because delta absorbs
the level difference the in-span EPUF cells would otherwise carry.

Output: the 15-column prefix shared with every other mode (so the extrapolation and the plots
read it unchanged; g0..g3 are the in-span polynomial, where the hinges are zero by
construction), then h_young, h_old, delta and their standard errors, the per-block rmse and
the J test.  NOTE that downstream consumers do not yet evaluate the hinge columns.
"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
from scipy.linalg import block_diag, cholesky, solve_triangular
from scipy.optimize import least_squares
from scipy.stats import chi2

sys.path.insert(0, "code/dynamics")          # run from the project root, per repo convention
import gcohort_model as E
import epuf_targets as P
from gcohort_smm import regularise

P50 = E.MOMENTS.index("p50")
GKSW_SCALE = 10.0            # GKSW's 10% sample vs EPUF's 1%; see the weighting note above
MIN_YOUNG, MIN_OLD = 3, 4    # out-of-span ages needed to identify each hinge


# --- the moment map -----------------------------------------------------------

def _tail_sd(v, cut):
    """sd(u | u >= cut) = sd(log Y | Y >= Ymin); the untargeted dispersion check the other
    modes report, computed straight off the sorted tail."""
    x = v[int(np.searchsorted(v, cut, side="left")):]
    return np.nan if x.size < 2 else float(x.std())


def cond_median(v, cut):
    """Q50(u | u >= cut) from the sorted finite draws `v`, linearly interpolated."""
    k = int(np.searchsorted(v, cut, side="left"))
    m = v.size - k
    if m < 8:                                     # degenerate cut; keep the solver finite
        k, m = v.size - 8, 8
    p = 0.5 * (m - 1)
    i = int(np.floor(p))
    f = p - i
    return v[k + i] * (1 - f) + v[k + min(i + 1, m - 1)] * f


def model_p50(gcoef, X, jj, logym, vs):
    """g(t) + Q50(u | u >= log(Ymin) - g(t)) at each age of one block."""
    g = X @ gcoef
    return np.array([gi + cond_median(vs[j], ci - gi) for j, gi, ci in zip(jj, g, logym)])


def resid(theta, blocks_):
    """Stacked model-minus-data over the GKSW block then the EPUF block; delta on EPUF only."""
    g, delta = theta[:-1], theta[-1]
    return np.concatenate([model_p50(g, X, jj, lym, vs) + off * delta - y
                           for X, jj, lym, vs, y, off in blocks_])


def jacobian(theta, blocks_, h=1e-3):
    """d m / d theta.  g enters only through a level shift at each age, so dm/dg comes from
    one central difference in theta[0] (column 0 of every design is the constant); delta
    enters the EPUF block one for one.  The step is deliberately coarse: the order statistic
    moves in jumps of order 1/N_sim as the cut crosses a draw."""
    rows = []
    for X, jj, lym, vs, y, off in blocks_:
        g = theta[:-1]
        up = model_p50(g + h * np.eye(g.size)[0], X, jj, lym, vs)
        dn = model_p50(g - h * np.eye(g.size)[0], X, jj, lym, vs)
        dmdg = (up - dn) / (2 * h)
        rows.append(np.hstack([dmdg[:, None] * X, np.full((X.shape[0], 1), float(off))]))
    return np.vstack(rows)


# --- the weight matrix --------------------------------------------------------

def bootstrap_median_cov(u, jj, cuts, ncell, reps, rng):
    """Sampling covariance of one block's DATA median vector, simulated under the model:
    one resample of individuals per replication, reused at every age, each age keeping the
    first ncell[j] draws that clear its own cut."""
    uj = np.ascontiguousarray(u[:, jj].T)        # age-major: one age = one contiguous gather
    n, J = uj.shape[1], jj.size
    rate = np.array([max((uj[j] >= cuts[j]).mean(), 1e-3) for j in range(J)])
    ndraw = min(n, int(np.ceil(1.25 * np.max(ncell / rate))) + 64)
    M = np.empty((reps, J))
    for r in range(reps):
        idx = rng.integers(0, n, ndraw)
        for j in range(J):
            x = uj[j][idx]
            x = x[x >= cuts[j]][:ncell[j]]
            M[r, j] = np.median(x)
    return np.cov(M, rowvar=False) * (1.0 + float(np.mean(ncell)) / n)


# --- one (sex, cohort) block --------------------------------------------------

def start_values(X, jj, logym, vs, y, degree):
    """Functional iteration b <- proj(y - Q50(u | g(b))), the cheap fixed point that strips
    the model's median offset out of the data median; converges in a handful of passes."""
    Xp = X[:, :degree + 1]
    b = np.linalg.lstsq(Xp, y, rcond=None)[0]
    for _ in range(50):
        g = Xp @ b
        q = np.array([cond_median(vs[j], ci - gi) for j, gi, ci in zip(jj, g, logym)])
        nxt = np.linalg.lstsq(Xp, y - q, rcond=None)[0]
        done = np.max(np.abs(nxt - b)) < 1e-11
        b = nxt
        if done:
            break
    return b


def solve_block(sex, cohort, gk_ages, gk_target, ep_ages, ep_y, ep_n, degree, steps, reps,
                lam, seed, vs, u):
    gk_y = gk_target[:, P50]
    hinges = (int((ep_ages < E.KNOTS[0]).sum()) >= MIN_YOUNG,
              int((ep_ages > E.KNOTS[1]).sum()) >= MIN_OLD)
    npg = degree + 1 + sum(hinges)
    X_gk, X_ep = E.design(gk_ages, degree, hinges), E.design(ep_ages, degree, hinges)
    jj_gk, jj_ep = E.sim_jj(gk_ages), E.sim_jj(ep_ages)
    lym_gk, lym_ep = E.logymin(cohort, gk_ages), E.logymin(cohort, ep_ages)
    # GKSW cell sizes are unpublished; proxy by EPUF's own count in the same cell, scaled
    n_by_age = dict(zip(ep_ages, ep_n))
    med_n = int(np.median(ep_n))
    gk_n = np.array([int(GKSW_SCALE * n_by_age.get(a, med_n)) for a in gk_ages])

    blocks_ = [(X_gk, jj_gk, lym_gk, vs, gk_y, 0.0), (X_ep, jj_ep, lym_ep, vs, ep_y, 1.0)]
    b0 = start_values(X_gk, jj_gk, lym_gk, vs, gk_y, degree)
    theta = np.concatenate([b0, np.zeros(npg - (degree + 1)), [0.0]])
    theta[-1] = float(np.mean(ep_y - model_p50(theta[:-1], X_ep, jj_ep, lym_ep, vs)))

    path, S = [], None
    for step in range(1, steps + 1):
        g = theta[:-1]
        parts = [bootstrap_median_cov(u, jj, lym - X @ g, nc, reps,
                                      np.random.default_rng(seed + off))    # independent samples
                 for (X, jj, lym, *_), nc, off in
                 ((blocks_[0], gk_n, 0), (blocks_[1], ep_n, 104729))]
        S = regularise(block_diag(*parts), lam)
        C = cholesky(S if step > 1 else np.diag(np.diag(S)), lower=True)
        res = least_squares(
            lambda th: solve_triangular(C, resid(th, blocks_), lower=True), theta,
            method="lm", xtol=1e-13, ftol=1e-13,
            jac=lambda th: solve_triangular(C, jacobian(th, blocks_), lower=True))
        path.append(float(np.max(np.abs(res.x - theta))))
        theta = res.x

    r = resid(theta, blocks_)
    C = cholesky(S, lower=True)
    rw = solve_triangular(C, r, lower=True)
    GS = solve_triangular(C, jacobian(theta, blocks_), lower=True)
    V = np.linalg.inv(GS.T @ GS)
    Jstat, df = float(rw @ rw), max(r.size - theta.size, 1)

    poly = E.pad(theta[:degree + 1])
    k = degree + 1
    hy = float(theta[k]) if hinges[0] else np.nan
    ho = float(theta[k + hinges[0]]) if hinges[1] else np.nan
    se = np.sqrt(np.diag(V))
    cut = lym_gk - X_gk @ theta[:-1]
    return dict(
        sex=sex, cohort=cohort, n_ages=gk_ages.size, coef=poly, raw=E.uncentre(poly),
        se=np.concatenate([se[:degree + 1], np.zeros(3 - degree)]),
        h_young=hy, h_old=ho, delta=float(theta[-1]),
        se_h_young=float(se[k]) if hinges[0] else np.nan,
        se_h_old=float(se[k + hinges[0]]) if hinges[1] else np.nan,
        se_delta=float(se[-1]), n_epuf=ep_ages.size,
        n_young=int((ep_ages < E.KNOTS[0]).sum()), n_old=int((ep_ages > E.KNOTS[1]).sum()),
        rmse=float(np.sqrt((r**2).mean())),
        rmse_gksw=float(np.sqrt((r[:gk_ages.size]**2).mean())),
        rmse_epuf=float(np.sqrt((r[gk_ages.size:]**2).mean())),
        max_abs_resid=float(np.abs(r).max()),
        sdlog_gap=float(np.mean([_tail_sd(vs[j], ci) for j, ci in zip(jj_gk, cut)]
                                 - gk_target[:, 1])),
        max_censored_share=float(max(
            np.searchsorted(vs[j], ci) / vs[j].size for j, ci in zip(jj_gk, cut))),
        J=Jstat, df=df, p_value=float(chi2.sf(Jstat, df)), step_move=path,
        cond=float(np.linalg.cond(S)))


# --- parallel driver ----------------------------------------------------------

_W = {}


def _init(n, seed):
    u = E.simulate_u(np.random.default_rng(seed), n, E.SIM_AGES)
    _W["u"] = u
    _W["vs"] = [np.sort(u[np.isfinite(u[:, j]), j]) for j in range(u.shape[1])]


def _run(job):
    return solve_block(*job, _W["vs"], _W["u"])


def run(a, out):
    """Estimate every block under the entry point's namespace `a`; write `out`."""
    print(f"simulating {a.n:,} individuals over ages {E.SIM_AGES[0]}-{E.SIM_AGES[-1]} ...")
    ep = P.by_block(P.load_p50(min_n=a.min_cell))
    jobs = []
    for label, c, ages, target in E.blocks(a.sel, a.min_ages):
        if (label, c) not in ep:
            continue
        ea, ey, en = ep[(label, c)]
        jobs.append((label, c, ages, target, ea, ey, en, a.degree, a.steps,
                     a.reps, a.shrink, a.seed + c))
    ny = np.mean([int((j[4] < 25).sum()) for j in jobs])
    no = np.mean([int((j[4] > 55).sum()) for j in jobs])
    print(f"{len(jobs)} blocks: 31 GKSW ages + {np.mean([j[4].size for j in jobs]):.0f} EPUF "
          f"ages on average ({ny:.1f} below 25, {no:.1f} above 55)")
    print(f"{a.steps} GMM steps x {a.reps} bootstrap reps")

    t0, rows = time.time(), []
    with ProcessPoolExecutor(max_workers=a.jobs, initializer=_init,
                             initargs=(a.n, a.seed)) as ex:
        futs = [ex.submit(_run, j) for j in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            rows.append(f.result())
            if i % 10 == 0 or i == len(futs):
                print(f"  {i}/{len(futs)} blocks  ({time.time() - t0:.0f}s)", flush=True)
    rows.sort(key=lambda r: (r["sex"], r["cohort"]))
    fill_hinges(rows)
    write_csv(rows, out)
    report(rows, a)


def fill_hinges(rows):
    """Blocks with too few out-of-span ages carry no hinge column; give them their sex's mean
    so downstream has a complete set.  Those blocks have no data there by construction, so
    nothing about their fitted g changes."""
    for key in ("h_young", "h_old"):
        for sex in ("female", "male"):
            sub = [r for r in rows if r["sex"] == sex]
            have = [r[key] for r in sub if np.isfinite(r[key])]
            if not have:
                continue
            m = float(np.mean(have))
            for r in sub:
                if not np.isfinite(r[key]):
                    r[key], r[key + "_filled"] = m, 1
            n = sum(r.get(key + "_filled", 0) for r in sub)
            if n:
                print(f"  {sex}: {key} filled from the {len(have)}-cohort mean "
                      f"({m:+.3f}) for {n} blocks with < {MIN_OLD} out-of-span ages")


def write_csv(rows, path):
    cols = (["sex", "cohort", "n_ages"] + [f"g{k}" for k in range(4)]
            + [f"g{k}_raw" for k in range(4)]
            + ["rmse", "max_abs_resid", "sdlog_gap", "max_censored_share"]
            + [f"se_g{k}" for k in range(4)]
            + ["h_young", "h_old", "delta", "se_h_young", "se_h_old", "se_delta",
               "h_old_filled", "n_epuf", "n_young", "n_old", "rmse_gksw", "rmse_epuf",
               "J", "df", "p_value"])
    with open(path, "w") as f:
        f.write(",".join(cols) + "\n")
        for r in rows:
            v = [*r["coef"], *r["raw"], r["rmse"], r["max_abs_resid"], r["sdlog_gap"],
                 r["max_censored_share"], *r["se"], r["h_young"], r["h_old"], r["delta"],
                 r["se_h_young"], r["se_h_old"], r["se_delta"]]
            f.write(f"{r['sex']},{r['cohort']},{r['n_ages']},"
                    + ",".join("nan" if v_ is None or not np.isfinite(v_) else f"{v_:.6f}"
                               for v_ in v)
                    + f",{r.get('h_old_filled', 0)},{r['n_epuf']},{r['n_young']},{r['n_old']}"
                    + f",{r['rmse_gksw']:.6f},{r['rmse_epuf']:.6f},{r['J']:.4f}"
                    + f",{r['df']},{r['p_value']:.3e}\n")
    print(f"wrote {path}  ({len(rows)} blocks)")


def report(rows, a):
    move = np.array([r["step_move"] for r in rows])
    print("\nGMM step movement (max |dtheta|, median over blocks):")
    for s in range(move.shape[1]):
        print(f"  step {s + 1}: {np.median(move[:, s]):.2e}")
    print(f"weight-matrix condition number after {a.shrink:.0%} shrinkage: "
          f"median {np.median([r['cond'] for r in rows]):.3g}")
    print(f"\n{'sex':7s} {'delta':>16s} {'h_young':>16s} {'h_old':>16s}"
          f" {'rmse gksw':>10s} {'rmse epuf':>10s}")
    for sex in ("male", "female"):
        s = [r for r in rows if r["sex"] == sex]
        f = lambda k: (np.median([r[k] for r in s]),
                       np.median([r["se_" + k] for r in s if np.isfinite(r["se_" + k])]))
        d, hy, ho = f("delta"), f("h_young"), f("h_old")
        print(f"{sex:7s} {d[0]:+9.3f} ({d[1]:.3f}) {hy[0]:+9.3f} ({hy[1]:.3f}) "
              f"{ho[0]:+9.3f} ({ho[1]:.3f}) "
              f"{np.median([r['rmse_gksw'] for r in s]):10.4f} "
              f"{np.median([r['rmse_epuf'] for r in s]):10.4f}")
    print("\n(median over blocks, asymptotic se in parentheses; h_young and h_old are the "
          "slopes\n of g in t-units outside 25-55, so a NEGATIVE h_old is a fall after 55.)")
    for sex in ("male", "female"):
        s = [r for r in rows if r["sex"] == sex]
        pv = np.array([r["p_value"] for r in s])
        print(f"{sex}: J rejects at 5% in {100 * (pv < 0.05).mean():.0f}% of blocks "
              f"(median p {np.median(pv):.3g}, df {s[0]['df']})")
