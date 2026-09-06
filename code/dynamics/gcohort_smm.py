"""Simulated method of moments for the cohort x sex profile g(t): the `--mode smm-*`
estimators behind estimate_g_cohort.py.  Library only; the CLI lives in the entry point.

Per (sex, cohort) block, `keep` of the ten published moments at each of 31 ages are matched
to their model counterparts (gcohort_model: every moment is a functional of the cut
log(Ymin) - g(t) on one simulated panel), with a multi-step optimal weight matrix:

  * step 1 weights by diag(S)^-1 (units only), step 2 by the full S^-1 at the step-1
    estimate, further steps iterate S and theta to a fixed point.
  * S = Var(m_data) is BOOTSTRAPPED FROM THE MODEL, which is what SMM licenses: the
    published cells carry no standard errors, and under the null a data cell is a finite
    sample from the simulated distribution.  Individuals are resampled ONCE per replication
    and reused at every age, so the along-age panel correlation of a cohort x age table is
    reproduced rather than assumed away; age j keeps the first n_j draws clearing its own
    cut, nesting the cells as attrition does.  Cell sizes are EPUF's counts of positive
    earners (same universe, same 1% rate; only relative sizes matter), edge-held at 2006 for
    the cells GKSW report past EPUF's end.  S is inflated by (1 + n/N_sim) for simulation
    noise and shrunk toward its diagonal, because 217 moments from 1000 replications is not
    comfortably invertible.
  * COMMON RANDOM NUMBERS across steps: the same bootstrap draws at every step, so that the
    step-to-step movement measures the theta-dependence of S and not the Monte-Carlo noise
    in estimating it.  Measured movement 9e-3, 2e-1, 2e-4: the jump from diagonal to full
    weighting is where the work happens, and step 3 is the fixed point.  Re-drawing each
    step never settles.
  * The Jacobian factorises: g is the only channel and age j's moments depend only on
    g(t_j), so d m / d theta = diag(dm/dg) x (polynomial basis), with dm/dg by a coarse
    central difference (order statistics move in 1/N_sim jumps, and a default-sized step
    would resolve that granularity instead of the derivative).

Which moments identify g is measured, not assumed, and the printed Jacobian summary
reports it: meanlog and the log percentiles move one for one with g; sdlog/skewlog/kurtlog
depend on g only through the near-non-binding cut (dm/dg ~ 0).  The entry point therefore
offers `mean` and `level` (mean + percentiles) only; `all`/`quantiles` remain here for the
specification test the shape moments DO support -- the J statistic, which rejects the fixed
GKOS calibration in every block.

The reported asymptotic standard errors understate the real uncertainty: across bootstrap
redraws of S-hat the sd of g0 is several times the asymptotic se (`--wnoise K` re-measures
it, `wsd_*` records it).  Raising `--reps` is the lever, at linear cost.

Output: one CSV whose first 15 columns (sex, cohort, n_ages, g0..g3, g0_raw..g3_raw, rmse,
max_abs_resid, sdlog_gap, max_censored_share) are shared with --mode ols, followed by
standard errors in both bases, the weight-matrix-noise columns and the J test.
"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import io
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
from scipy.linalg import cholesky, solve_triangular
from scipy.optimize import least_squares
from scipy.stats import chi2

sys.path.insert(0, "code/dynamics")          # run from the project root, per repo convention
import gcohort_model as E

DB = "processed_data/ssa.duckdb"
LEVEL = ["meanlog", "p10", "p25", "p50", "p75", "p90", "p98"]
SETS = {"all": E.MOMENTS, "level": LEVEL, "quantiles": E.MOMENTS[4:], "mean": ["meanlog"]}


# --- data ---------------------------------------------------------------------

def cell_sizes():
    """(sex_label, cohort, age) -> EPUF count of positive earners in that cell, edge-held
    at EPUF's last year for the cells GKSW report after it."""
    q = ("COPY (SELECT d.sex, a.year - d.yob AS age, a.year AS year, count(*) AS n "
         "FROM annual a JOIN demographic d USING (id) "
         "WHERE a.earnings > 0 AND d.sex IS NOT NULL AND a.year - d.yob BETWEEN 25 AND 55 "
         "GROUP BY 1, 2, 3) TO '/dev/stdout' (FORMAT CSV, HEADER)")
    txt = subprocess.run(["duckdb", DB, "-c", q], capture_output=True, text=True,
                         check=True).stdout
    d = pd.read_csv(io.StringIO(txt))
    d["sex"] = d["sex"].map({1: "male", 2: "female"})
    tab = {(r.sex, r.age, r.year): int(r.n) for r in d.itertuples()}
    last = max(y for _, _, y in tab)
    return lambda sex, cohort, age: tab.get((sex, age, min(cohort + age - 25, last)), 0)


# --- model moments from one simulated panel -----------------------------------

def _central(r1, r2, r3, r4, m):
    """(mean, sd, skew, kurt) from raw sums, in Stata's population form (no n-1, raw rather
    than excess kurtosis) -- what `egen skew`/`kurt` produced upstream."""
    a1, a2, a3, a4 = r1 / m, r2 / m, r3 / m, r4 / m
    c2 = a2 - a1**2
    c3 = a3 - 3 * a1 * a2 + 2 * a1**3
    c4 = a4 - 4 * a1 * a3 + 6 * a1**2 * a2 - 3 * a1**4
    sd = np.sqrt(max(c2, 1e-12))
    return a1, sd, c3 / sd**3, c4 / sd**4


def _quant_idx(m, qs):
    p = qs * (m - 1)
    i = np.floor(p).astype(int)
    return i, np.minimum(i + 1, m - 1), p - i


def _quants(v, k, m, qs):
    """Linearly interpolated quantiles of the sorted tail v[k:], length m."""
    i, i1, f = _quant_idx(m, qs)
    return v[k + i] * (1 - f) + v[k + i1] * f


def _quants_unsorted(x, qs):
    """Same quantiles from an UNSORTED array by partial selection -- six order statistics
    out of ~13k draws, several hundred thousand times in the bootstrap."""
    i, i1, f = _quant_idx(x.size, qs)
    x = np.partition(x, np.unique(np.concatenate([i, i1])))
    return x[i] * (1 - f) + x[i1] * f


def cell_moments(table, cut):
    """The full length-10 model moment vector of (u | u >= cut), g-free part only."""
    v, s1, s2, s3, s4 = table
    k = int(np.searchsorted(v, cut, side="left"))
    m = v.size - k
    if m < 8:                                     # degenerate cut; keep the solver finite
        k, m = v.size - 8, 8
    mean, sd, skew, kurt = _central(s1[k], s2[k], s3[k], s4[k], m)
    return np.concatenate([[mean, sd, skew, kurt], _quants(v, k, m, E.QS)])


def block_moments(coef, jj, logym, tables, keep):
    """Model moments for one block, ages stacked, `keep` moments each."""
    g = E.gpoly(coef, E.TC[jj])
    out = np.empty((jj.size, keep.size))
    for r, (j, gi, ci) in enumerate(zip(jj, g, logym)):
        mv = cell_moments(tables[j], ci - gi)
        mv[0] += gi                               # meanlog and the log percentiles
        mv[4:] += gi                              # ride one for one with g
        out[r] = mv[keep]
    return out.ravel()


def block_jacobian(coef, jj, logym, tables, keep, degree, h=1e-3):
    """d m / d theta = diag(dm/dg) @ basis; dm/dg by a central difference in a common level
    shift, two block evaluations for the whole matrix."""
    c = E.pad(coef)
    up = block_moments(c + np.array([h, 0, 0, 0]), jj, logym, tables, keep)
    dn = block_moments(c - np.array([h, 0, 0, 0]), jj, logym, tables, keep)
    dmdg = (up - dn) / (2 * h)
    return dmdg[:, None] * np.repeat(E.basis(E.TC[jj], degree), keep.size, axis=0)


# --- the weight matrix --------------------------------------------------------

def bootstrap_cov(u, jj, cuts, ncell, keep, reps, rng):
    """Sampling covariance of the DATA moment vector, simulated under the model: one
    resample of individuals per replication, reused across ages (see module docstring)."""
    uj = np.ascontiguousarray(u[:, jj].T)        # age-major: one age = one contiguous gather
    n, J, K = uj.shape[1], jj.size, keep.size
    rate = np.array([max((uj[j] >= cuts[j]).mean(), 1e-3) for j in range(J)])
    ndraw = min(n, int(np.ceil(1.25 * np.max(ncell / rate))) + 64)   # fills every cell
    M = np.empty((reps, J * K))
    for r in range(reps):
        idx = rng.integers(0, n, ndraw)
        for j in range(J):
            x = uj[j][idx]
            x = x[x >= cuts[j]][:ncell[j]]        # random order in, random subsample out
            x2 = x * x
            mean, sd, skew, kurt = _central(x.sum(), x2.sum(), (x2 * x).sum(),
                                            (x2 * x2).sum(), x.size)
            mv = np.concatenate([[mean, sd, skew, kurt], _quants_unsorted(x, E.QS)])
            M[r, j * K:(j + 1) * K] = mv[keep]
    return np.cov(M, rowvar=False) * (1.0 + float(np.mean(ncell)) / n)


def regularise(S, lam):
    S = (1 - lam) * S + lam * np.diag(np.diag(S))
    return S + 1e-12 * np.eye(S.shape[0]) * np.trace(S) / S.shape[0]


# --- one (sex, cohort) block --------------------------------------------------

def solve_block(sex, cohort, ages, target, tables, u, ncell, keep, degree, steps,
                reps, lam, seed):
    jj = ages - E.AGES[0]
    logym = E.logymin(cohort, ages)
    y = target[:, keep].ravel()
    resid = lambda c: block_moments(c, jj, logym, tables, keep) - y
    cuts = lambda c: logym - E.gpoly(c, E.TC[jj])

    # step 0: the exactly-identified mean-only LS fit is the start value
    coef = E.fit_block(jj, logym, target[:, 0], tables, E.G_START, degree)[0][:degree + 1]
    path = []
    for step in range(1, steps + 1):
        S = regularise(bootstrap_cov(u, jj, cuts(coef), ncell, keep, reps,
                                     np.random.default_rng(seed)), lam)   # common random numbers
        C = cholesky(S if step > 1 else np.diag(np.diag(S)), lower=True)
        res = least_squares(
            lambda c: solve_triangular(C, resid(c), lower=True), coef, method="lm",
            xtol=1e-13, ftol=1e-13,
            jac=lambda c: solve_triangular(
                C, block_jacobian(c, jj, logym, tables, keep, degree), lower=True))
        path.append(np.max(np.abs(res.x - coef)))
        coef = res.x

    # J test and asymptotic variance at the final (optimal) weight matrix
    r = resid(coef)
    C = cholesky(S, lower=True)
    rw = solve_triangular(C, r, lower=True)
    G = block_jacobian(coef, jj, logym, tables, keep, degree)
    GS = solve_triangular(C, G, lower=True)
    V = np.zeros((4, 4))
    V[:degree + 1, :degree + 1] = np.linalg.inv(GS.T @ GS)
    df = max(r.size - coef.size, 1)
    Jstat = float(rw @ rw)

    full = E.pad(coef)
    cut = cuts(coef)
    return dict(sex=sex, cohort=cohort, n_ages=ages.size, coef=full, raw=E.uncentre(full),
                se=np.sqrt(np.diag(V)), se_raw=np.sqrt(np.diag(E.UNCENTRE @ V @ E.UNCENTRE.T)),
                rmse=float(np.sqrt((r**2).mean())), max_abs_resid=float(np.abs(r).max()),
                sdlog_gap=float(np.mean([E.cond_sd(tables[j], ci) for j, ci in zip(jj, cut)]
                                        - target[:, 1])),
                max_censored_share=max(E.censored_share(tables[j], ci) for j, ci in zip(jj, cut)),
                J=Jstat, df=df, p_value=float(chi2.sf(Jstat, df)), step_move=path,
                by_moment=np.abs(r.reshape(jj.size, keep.size)).mean(axis=0),
                cond=float(np.linalg.cond(S)),
                dmdg=G[:, 0].reshape(jj.size, keep.size).mean(axis=0))


# --- parallel driver ----------------------------------------------------------

_W = {}


def _init(n, seed):
    _W["u"] = E.simulate_u(np.random.default_rng(seed), n)
    _W["tables"] = E.suffix_tables(_W["u"], order=4)


def _run(job):
    sex, cohort, ages, target, rest, wnoise = job
    solve = lambda seed: solve_block(sex, cohort, ages, target, _W["tables"], _W["u"],
                                     *rest[:-1], seed)
    r = solve(rest[-1])
    alt = [solve(rest[-1] + 7919 * (k + 1))["coef"] for k in range(wnoise)]
    r["wsd"] = (np.vstack([r["coef"]] + alt).std(axis=0, ddof=1) if wnoise
                else np.full(4, np.nan))
    return r


def run(a, out, moments):
    """Estimate every block under the entry point's namespace `a`; write `out`."""
    keep = np.array([E.MOMENTS.index(m) for m in SETS[moments]])
    print(f"targeting {keep.size} moments per age: {', '.join(SETS[moments])}")
    print(f"simulating {a.n:,} individuals over ages 25-55 ...")
    size = cell_sizes()
    jobs = [(label, c, ages, target,
             (np.array([max(size(label, c, x), 200) for x in ages]), keep, a.degree,
              a.steps, a.reps, a.shrink, a.seed + c), a.wnoise)
            for label, c, ages, target in E.blocks(a.sel, a.min_ages)]
    print(f"{len(jobs)} blocks x {a.steps} GMM steps x {a.reps} bootstrap reps")

    t0, rows = time.time(), []
    with ProcessPoolExecutor(max_workers=a.jobs, initializer=_init,
                             initargs=(a.n, a.seed)) as ex:
        futs = [ex.submit(_run, j) for j in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            rows.append(f.result())
            if i % 20 == 0 or i == len(futs):
                print(f"  {i}/{len(futs)} blocks  ({time.time() - t0:.0f}s)")
    rows.sort(key=lambda r: (r["sex"], r["cohort"]))
    write_csv(rows, out)
    report(rows, keep, a)


def write_csv(rows, path):
    cols = (["sex", "cohort", "n_ages"] + [f"g{k}" for k in range(4)]
            + [f"g{k}_raw" for k in range(4)]
            + ["rmse", "max_abs_resid", "sdlog_gap", "max_censored_share"]
            + [f"se_g{k}" for k in range(4)] + [f"se_g{k}_raw" for k in range(4)]
            + [f"wsd_g{k}" for k in range(4)] + ["J", "df", "p_value"])
    with open(path, "w") as f:
        f.write(",".join(cols) + "\n")
        for r in rows:
            vals = [*r["coef"], *r["raw"], r["rmse"], r["max_abs_resid"], r["sdlog_gap"],
                    r["max_censored_share"], *r["se"], *r["se_raw"], *r["wsd"], r["J"]]
            f.write(f"{r['sex']},{r['cohort']},{r['n_ages']},"
                    + ",".join(f"{v:.6f}" for v in vals)
                    + f",{r['df']},{r['p_value']:.3e}\n")
    print(f"wrote {path}  ({len(rows)} blocks)")


def report(rows, keep, a):
    move = np.array([r["step_move"] for r in rows])
    print("\nGMM step movement (max |dtheta| across coefficients, median over blocks):")
    for s in range(move.shape[1]):
        print(f"  step {s + 1}: {np.median(move[:, s]):.2e}")
    print(f"weight-matrix condition number after {a.shrink:.0%} shrinkage: "
          f"median {np.median([r['cond'] for r in rows]):.3g}")
    if a.wnoise:
        w = np.nanmedian(np.array([r["wsd"] for r in rows]), axis=0)
        s = np.median(np.array([r["se"] for r in rows]), axis=0)
        print(f"weight-matrix noise vs asymptotic se, median over blocks ({a.wnoise + 1} "
              f"bootstrap draws of S-hat):")
        for k in range(a.degree + 1):
            print(f"  g{k}: sd across S-hat draws {w[k]:.4f}   asymptotic se {s[k]:.4f}"
                  f"   ratio {w[k] / s[k]:.1f}x")
    dm = np.array([r["dmdg"] for r in rows]).mean(axis=0)
    by = np.array([r["by_moment"] for r in rows]).mean(axis=0)
    print("\nper moment:   dm/dg (identification)   mean |model - data|")
    for i, k in enumerate(keep):
        print(f"  {E.MOMENTS[k]:8s} {dm[i]:+22.4f}   {by[i]:18.4f}")
    for label in ("female", "male"):
        sub = [r for r in rows if r["sex"] == label]
        rm = np.array([r["rmse"] for r in sub])
        pv = np.array([r["p_value"] for r in sub])
        print(f"\n{label}: rmse median {np.median(rm):.4f}, max {rm.max():.4f}   "
              f"| J test rejects at 5% in {100 * (pv < 0.05).mean():.0f}% of blocks "
              f"(median p {np.median(pv):.3g}, df {sub[0]['df']})")
