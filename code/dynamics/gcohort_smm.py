"""Re-estimate the GKOS (2021) lifecycle profile g(t) by simulated method of moments.

This is the over-identified sibling of the mean-only fit in `gcohort_model.py`.  That targets ONE
statistic per (cohort, age) cell -- the mean of log earnings -- and solves an exactly
identified nonlinear least-squares problem.  But g(t) shifts the ENTIRE conditional
distribution of earnings, so every published statistic of that distribution carries
information about it.  The GKSW cell files publish ten:

    meanlog  sdlog  skewlog  kurtlog  p10  p25  p50  p75  p90  p98

(the first four are Stata's population-form moments of log real wage income; the last six
are percentiles in 2013 dollars).  This estimator targets all ten at every age, giving up
to 31 x 10 = 310 moment conditions against 3-4 free coefficients per (sex, cohort) block,
and solves them by SMM with a multi-step optimal weight matrix.

--------------------------------------------------------------------------------
The moment map
--------------------------------------------------------------------------------
The structure that makes `gcohort_model.py` cheap survives intact.  With
log Y = g(t) + u and the sample rule Y >= Ymin, everything is a functional of the single
scalar cut  c = log(Ymin) - g(t)  applied to the age-t distribution of u:

    meanlog       = g(t) + E[ u | u >= c ]
    sd/skew/kurt  =        the corresponding CENTRAL moments of ( u | u >= c )
    log p_q       = g(t) + Q_q( u | u >= c )

So one simulated panel still suffices: sort u within each age once, carry suffix sums of
u, u^2, u^3, u^4 for the central moments and the sorted array itself for the order
statistics, and every objective evaluation is a binary search plus O(1) arithmetic.

--------------------------------------------------------------------------------
What actually identifies g -- read this before interpreting the output
--------------------------------------------------------------------------------
The ten moments split cleanly in two:

  * SEVEN LEVEL moments (meanlog and the six log percentiles) shift ONE FOR ONE with g,
    up to the truncation.  These identify g.
  * THREE SHAPE moments (sdlog, skewlog, kurtlog) are central moments of (u | u >= c) and
    depend on g ONLY through the cut.  Since the cut is near non-binding at the GKOS
    parameters (the nonemployment shock puts the low mass at exactly zero, not just above
    Ymin -- max censored share ~0.001), dm/dg for these is ~1e-3, i.e. essentially zero.

That is a fact about the model, not a defect of the estimator, and the Jacobian summary
printed at the end reports it explicitly.  Two consequences:

  1. Adding the shape moments cannot help pin down g directly, because with g the only free
     parameter the model's dispersion and skewness are whatever the FIXED GKOS parameters
     make them.  They enter the criterion as a near-constant misfit -- and thereby give an
     honest, correctly-scaled specification test (the J statistic below) that the
     mean-only estimator cannot produce, since with one moment per age it is exactly
     identified and has zero degrees of freedom.
  2. They can still MOVE g, but only indirectly: the optimal weight matrix is not diagonal,
     so a systematically misfit sdlog tilts the level moments it is correlated with.  Use
     `--moments level` to switch that channel off and compare.

The real payoff of the over-identification is within the level block.  Mean-targeting and
quantile-targeting agree only if the model's conditional log-earnings SHAPE is right; where
it is not, they disagree, and GMM picks the weighted compromise with the smallest
sampling-variance-adjusted distance.

--------------------------------------------------------------------------------
The weight matrix
--------------------------------------------------------------------------------
Optimal W = S^-1 with S = Var( m_data - m_model ).  The published cells give no standard
errors, so S is built from the model itself, which is exactly what SMM licenses: under the
null the data cell IS a finite sample from the simulated distribution.  Per block,

  * bootstrap R replications of a synthetic cohort from the simulated panel.  Individuals
    are resampled ONCE per replication and reused at every age, so the panel correlation of
    the sampling error along age -- which is what a cohort-by-age table actually has -- is
    reproduced rather than assumed away.  Cell sizes come from EPUF's own count of positive
    earners at (sex, cohort, age), edge-held at 2006 for the 214 cells GKSW report past the
    end of EPUF.  Age j keeps the first n_j selected draws of the common permutation, so the
    cells are nested down the age profile, as attrition makes them in the data.
  * inflate by (1 + n / N_sim) for simulation noise in m_model (~5% at the defaults).
  * shrink toward the diagonal, S <- (1-lam) S + lam diag(S), because 310 moments estimated
    from R ~ 400 replications is not comfortably invertible.  The condition number after
    shrinkage is printed.

Multi-step, exactly the textbook loop: step 1 uses diag(S)^-1 (units only, no correlations),
step 2 uses the full S^-1 at the step-1 estimate, and further steps iterate S and theta to a
fixed point.  The bootstrap uses COMMON RANDOM NUMBERS across steps, which is what makes the
loop converge: S depends on theta only through the cut, and the cut is near non-binding, so
with the draws held fixed the iteration lands on a fixed point at step 3 (MEASURED movement
1.9e-2, 3.0e-1, 6.0e-5, then exactly 0).  Re-drawing the bootstrap each step instead makes it
chase the Monte-Carlo noise in S-hat and it never settles -- measured moves of 3.6e-1, 1.2e-1,
1.5e-1, 1.2e-1, 6.2e-2, 4.7e-2 over seven steps.  Step 2 is where the real work happens: the
jump from diagonal to full weighting moves g0 by ~0.3 log points, because the off-diagonals
are large.

That last fact is also the estimator's main weakness, and `--wnoise K` measures it: re-solve
each block K extra times with fresh bootstrap draws and report the spread of theta across
them.  MEASURED on men, cohort 1970, reps=1000: sd(g0) across bootstrap seeds is 0.021 under
`--moments all` against an asymptotic standard error of 0.004, and 0.006 against 0.004 under
`--moments level`.  So with the shape moments in, WHICH DRAW OF S-HAT YOU GET moves the answer
several times more than sampling error does, and the reported standard errors understate the
true spread.  Raise `--reps` to shrink it; the level-only weighting is far better behaved
because S is far better conditioned without the near-collinear shape block.

Reported per block: the coefficients (centred on age 40 and on raw t, as in the sibling
script), asymptotic standard errors sqrt(diag (G' S^-1 G)^-1) in BOTH bases (the recentring
is linear, so the delta method is exact), the J statistic with its degrees of freedom and
p-value, and the rmse by moment type.

CAVEAT unchanged from the sibling script: GKOS estimate on men only, sex0 is FEMALE and
sex1 is MALE in the source do-file, and the male parameter vector is applied to both.  Read
g_female as descriptive.  Here that shows up sharply in the J statistic, which is a joint
test of "the fixed GKOS parameters generate this cohort's whole distribution".

Run from the project root:
    python code/dynamics/estimate_g_cohort.py --mode smm-quantiles [--sel sel0] [--degree 3] [--jobs 8]
Output: output/dynamics/g_cohort_gmm<tag>.csv             (same layout as the LS fit, plus
                                                           standard errors and the J test)
        output/dynamics/g_gmm_vs_ls<tag>.{pdf,png}
        output/dynamics/g_gmm_moment_fit<tag>.{pdf,png}
"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse
import io
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.linalg import cholesky, solve_triangular
from scipy.optimize import least_squares
from scipy.stats import chi2

sys.path.insert(0, "code/dynamics")          # run from project root, per repo convention
import gcohort_model as E

DB = "processed_data/ssa.duckdb"
OUT = "output/dynamics"

# --- the published moment vector ---------------------------------------------
# Order is fixed: the four log moments, then the six percentiles (logged on load, so
# every entry of the vector is in log points and the shape moments are dimensionless).
QS = np.array([0.10, 0.25, 0.50, 0.75, 0.90, 0.98])
MOMENTS = ["meanlog", "sdlog", "skewlog", "kurtlog",
           "p10", "p25", "p50", "p75", "p90", "p98"]
LEVEL = ["meanlog", "p10", "p25", "p50", "p75", "p90", "p98"]
SHAPE = ["sdlog", "skewlog", "kurtlog"]
SETS = {"all": MOMENTS, "level": LEVEL, "quantiles": MOMENTS[4:], "mean": ["meanlog"]}

C_GMM, C_LS = "#eb6834", "#2a78d6"


# --- data ---------------------------------------------------------------------

def load_moments(sex, sel):
    """(cohort, age) -> length-10 vector of published moments, percentiles in logs."""
    path = f"{E.TARGET_DIR}/cohortage_rwageinc_{sel}_25_55_sex{sex}.txt"
    raw = np.genfromtxt(path, skip_header=1)
    out = {}
    for row in raw:
        m = row[2:12].copy()
        m[4:] = np.log(m[4:])
        out[(int(row[0]), int(row[1]))] = m
    return out


def cell_sizes():
    """(sex_label, cohort, age) -> count of EPUF positive earners in that cell.

    A proxy for the GKSW cell size: same universe (SSA covered workers), same 1% sampling
    rate.  Only the RELATIVE sizes matter -- a common factor cancels out of the GMM
    estimator -- so the proxy has to get the age and cohort profile right, not the level.
    GKSW run to 2013 and EPUF stops in 2006, so the 214 later cells are edge-held at the
    same age in 2006.
    """
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

    def get(sex, cohort, age):
        return tab.get((sex, age, min(cohort + age - 25, last)), 0)
    return get


# --- model moments from one simulated panel -----------------------------------

def moment_tables(u):
    """Per age: sorted finite u, plus suffix sums of u^1..u^4 for the central moments."""
    tables = []
    for j in range(u.shape[1]):
        v = np.sort(u[np.isfinite(u[:, j]), j])
        s = [np.concatenate([np.cumsum((v**k)[::-1])[::-1], [0.0]]) for k in (1, 2, 3, 4)]
        tables.append((v, *s))
    return tables


def _central(r1, r2, r3, r4, m):
    """(mean, sd, skew, kurt) from raw sums, in Stata's population form (no n-1, raw
    kurtosis rather than excess) -- which is what `egen skew`/`kurt` produced upstream."""
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
    """Same quantiles from an UNSORTED array, by partial selection.

    np.partition places the requested order statistics and nothing else, which is what the
    bootstrap needs: six percentiles out of ~13k draws, several hundred thousand times.
    """
    m = x.size
    i, i1, f = _quant_idx(m, qs)
    kth = np.unique(np.concatenate([i, i1]))
    x = np.partition(x, kth)
    return x[i] * (1 - f) + x[i1] * f


def cell_moments(table, cut):
    """The full length-10 model moment vector of (u | u >= cut), g-free part only."""
    v, s1, s2, s3, s4 = table
    k = int(np.searchsorted(v, cut, side="left"))
    m = v.size - k
    if m < 8:                                     # degenerate cut; keep the solver finite
        k, m = v.size - 8, 8
    mean, sd, skew, kurt = _central(s1[k], s2[k], s3[k], s4[k], m)
    return np.concatenate([[mean, sd, skew, kurt], _quants(v, k, m, QS)])


def block_moments(coef, jj, logymin, tables, keep):
    """Model moments for one (sex, cohort) block, ages stacked, `keep` moments each."""
    c = E.pad(coef)
    tt = E.T[jj] - E.T_CENTRE
    g = c[0] + c[1] * tt + c[2] * tt**2 + c[3] * tt**3
    out = np.empty((jj.size, keep.size))
    for r, (j, gi, ci) in enumerate(zip(jj, g, logymin)):
        mv = cell_moments(tables[j], ci - gi)
        mv[0] += gi                               # meanlog and the log percentiles
        mv[4:] += gi                              # ride one for one with g
        out[r] = mv[keep]
    return out.ravel()


def block_jacobian(coef, jj, logymin, tables, keep, degree, h=1e-3):
    """d m / d theta.

    g is the ONLY channel through which theta enters, and age j's moments depend only on
    g(t_j), so the Jacobian factorises as diag(dm/dg) @ (polynomial basis).  dm/dg is taken
    by a central difference in a common level shift -- two block evaluations for the whole
    matrix.  The step is deliberately coarse (1e-3 log points): the order statistics move
    in jumps of order 1/N_sim as the cut crosses a draw, and a default-sized finite
    difference would resolve that granularity instead of the derivative.
    """
    c = E.pad(coef)
    up = block_moments(c + np.array([h, 0, 0, 0]), jj, logymin, tables, keep)
    dn = block_moments(c - np.array([h, 0, 0, 0]), jj, logymin, tables, keep)
    dmdg = (up - dn) / (2 * h)                              # (J*K,)
    tt = E.T[jj] - E.T_CENTRE
    basis = np.vstack([tt**k for k in range(degree + 1)]).T  # (J, p)
    return dmdg[:, None] * np.repeat(basis, keep.size, axis=0)


# --- the weight matrix --------------------------------------------------------

def bootstrap_cov(u, jj, cuts, ncell, keep, reps, rng):
    """Sampling covariance of the DATA moment vector, simulated under the model.

    One resample of individuals per replication, reused across ages: the moment vector of a
    cohort-by-age table is correlated down the age dimension because it is the same people,
    and a per-age bootstrap would understate exactly the covariances the optimal weight
    matrix exists to exploit.  Age j takes the first ncell[j] draws that clear its own cut,
    which both nests the cells and reproduces the model's employment margin.
    """
    # age-major, so one age's draws are a contiguous gather rather than a strided slice of
    # a (ndraw x J) copy -- the copy is the whole cost of this loop at these replication counts
    uj = np.ascontiguousarray(u[:, jj].T)
    n, J, K = uj.shape[1], jj.size, keep.size
    rate = np.array([max((uj[j] >= cuts[j]).mean(), 1e-3) for j in range(J)])
    ndraw = min(n, int(np.ceil(1.25 * np.max(ncell / rate))) + 64)   # headroom
    # so every age still fills its cell after its own selection

    M = np.empty((reps, J * K))
    for r in range(reps):
        idx = rng.integers(0, n, ndraw)
        for j in range(J):
            x = uj[j][idx]
            x = x[x >= cuts[j]][:ncell[j]]        # random order in, random subsample out
            x2 = x * x
            mean, sd, skew, kurt = _central(x.sum(), x2.sum(), (x2 * x).sum(),
                                            (x2 * x2).sum(), x.size)
            mv = np.concatenate([[mean, sd, skew, kurt], _quants_unsorted(x, QS)])
            M[r, j * K:(j + 1) * K] = mv[keep]
    S = np.cov(M, rowvar=False)
    return S * (1.0 + float(np.mean(ncell)) / n)  # + simulation noise in m_model


def regularise(S, lam):
    d = np.diag(np.diag(S))
    S = (1 - lam) * S + lam * d
    return S + 1e-12 * np.eye(S.shape[0]) * np.trace(S) / S.shape[0]


# --- one (sex, cohort) block --------------------------------------------------

def solve_block(sex, cohort, ages, target, tables, u, ncell, keep, degree, steps,
                reps, lam, seed):
    jj = ages - E.AGES[0]
    logymin = np.log(np.array([E.ymin(cohort + a - 25) for a in ages]))
    full_target, target = target, target[:, keep]   # `target` arrives with all 10 moments
    y = target.ravel()
    # E's helpers take the 3-tuple (v, s1, s2); the first three slots here are identical
    ls_tables = [t[:3] for t in tables]

    def resid_raw(c):
        return block_moments(c, jj, logymin, tables, keep) - y

    # step 0: the exactly-identified mean-only LS fit is the start value
    coef = E.fit_block(jj, logymin, full_target[:, 0], ls_tables,
                       E.G_START, degree)[0][:degree + 1]

    path, S, C = [], None, None
    for step in range(1, steps + 1):
        cuts = _cuts(coef, jj, logymin, degree)
        # COMMON RANDOM NUMBERS: the same bootstrap draws at every step, so that step-to-
        # step movement measures the theta-dependence of S and not the Monte-Carlo noise in
        # estimating it.  Without this the loop wanders at the scale of that noise, which
        # here is several times the asymptotic standard error, and never settles.
        S = regularise(bootstrap_cov(u, jj, cuts, ncell, keep, reps,
                                     np.random.default_rng(seed)), lam)
        C = cholesky(S if step > 1 else np.diag(np.diag(S)), lower=True)
        res = least_squares(
            lambda c: solve_triangular(C, resid_raw(c), lower=True),
            coef, method="lm", xtol=1e-13, ftol=1e-13,
            jac=lambda c: solve_triangular(
                C, block_jacobian(c, jj, logymin, tables, keep, degree), lower=True))
        path.append(np.max(np.abs(res.x - coef)))
        coef = res.x

    # J test and asymptotic variance at the final (optimal) weight matrix
    r = resid_raw(coef)
    C = cholesky(S, lower=True)
    Jstat = float(solve_triangular(C, r, lower=True) @ solve_triangular(C, r, lower=True))
    G = block_jacobian(coef, jj, logymin, tables, keep, degree)
    GS = solve_triangular(C, G, lower=True)
    V = np.linalg.inv(GS.T @ GS)
    df = max(r.size - coef.size, 1)

    full = E.pad(coef)
    A = _uncentre_matrix()
    se = np.zeros(4)
    se[:degree + 1] = np.sqrt(np.diag(V))
    Vf = np.zeros((4, 4))
    Vf[:degree + 1, :degree + 1] = V
    se_raw = np.sqrt(np.diag(A @ Vf @ A.T))

    cuts = _cuts(coef, jj, logymin, degree)
    sd_gap = np.mean([E.cond_sd(ls_tables[j], ci) for j, ci in zip(jj, cuts)]
                     - full_target[:, 1])
    cens = max(E.censored_share(ls_tables[j], ci) for j, ci in zip(jj, cuts))
    rby = np.abs(r.reshape(jj.size, keep.size)).mean(axis=0)   # rmse-ish, by moment
    return dict(sex=sex, cohort=cohort, n_ages=ages.size, coef=full, raw=E.uncentre(full),
                se=se, se_raw=se_raw, rmse=float(np.sqrt((r**2).mean())),
                max_abs_resid=float(np.abs(r).max()), sdlog_gap=float(sd_gap),
                max_censored_share=float(cens), J=Jstat, df=df,
                p_value=float(chi2.sf(Jstat, df)), step_move=path, by_moment=rby,
                cond=float(np.linalg.cond(S)),
                dmdg=block_jacobian(coef, jj, logymin, tables, keep, degree
                                    )[:, 0].reshape(jj.size, keep.size).mean(axis=0))


def _cuts(coef, jj, logymin, degree):
    c = E.pad(coef)
    tt = E.T[jj] - E.T_CENTRE
    return logymin - (c[0] + c[1] * tt + c[2] * tt**2 + c[3] * tt**3)


def _uncentre_matrix():
    """`E.uncentre` written as a matrix, so the delta method on it is exact."""
    m = E.T_CENTRE
    return np.array([[1, -m, m**2, -m**3], [0, 1, -2 * m, 3 * m**2],
                     [0, 0, 1, -3 * m], [0, 0, 0, 1]], float)


# --- parallel driver ----------------------------------------------------------

_W = {}


def _init(n, seed):
    u = E.simulate_u(np.random.default_rng(seed), n)
    _W["u"], _W["tables"] = u, moment_tables(u)


def _run(args):
    args, wnoise = args[:-1], args[-1]
    r = solve_block(*args[:2], *args[2:4], _W["tables"], _W["u"], *args[4:])
    if wnoise:
        alt = [solve_block(*args[:2], *args[2:4], _W["tables"], _W["u"], *args[4:-1],
                           args[-1] + 7919 * (k + 1))["coef"] for k in range(wnoise)]
        r["wsd"] = np.vstack([r["coef"]] + alt).std(axis=0, ddof=1)
    else:
        r["wsd"] = np.full(4, np.nan)
    return r


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200_000, help="simulated individuals")
    ap.add_argument("--min-ages", type=int, default=31)
    ap.add_argument("--sel", default="sel0")
    ap.add_argument("--degree", type=int, default=3, choices=[2, 3])
    ap.add_argument("--moments", default="all", choices=sorted(SETS),
                    help="all (default) | level (mean + log percentiles) | quantiles | mean")
    ap.add_argument("--steps", type=int, default=3,
                    help="1 = diagonal weights only; 2 = two-step optimal; >2 iterates")
    ap.add_argument("--reps", type=int, default=1000,
                    help="bootstrap replications for S; must comfortably exceed the number "
                         "of moment conditions (31 x len(--moments)) for S to be invertible")
    ap.add_argument("--wnoise", type=int, default=0,
                    help="re-solve each block this many extra times with fresh bootstrap "
                         "draws and report the spread of theta over them -- the sampling "
                         "noise the asymptotic standard errors do NOT contain")
    ap.add_argument("--shrink", type=float, default=0.10,
                    help="shrinkage of S toward its diagonal")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--seed", type=int, default=20260821)
    ap.add_argument("--out", default=None, help="parameter CSV (default: tagged by --tag)")
    ap.add_argument("--tag", default="", help="suffix on every output filename")
    ap.add_argument("--ls", default=None, help="LS fit CSV to overlay (default: matching --sel)")
    args = ap.parse_args(argv)

    os.makedirs(OUT, exist_ok=True)
    args.out = args.out or f"{OUT}/g_cohort_gmm{args.tag}.csv"
    keep = np.array([MOMENTS.index(m) for m in SETS[args.moments]])
    print(f"targeting {keep.size} moments per age: {', '.join(SETS[args.moments])}")
    print(f"simulating {args.n:,} individuals over ages 25-55 ...")
    _init(args.n, args.seed)
    size = cell_sizes()

    jobs = []
    for sexcode, label in ((0, "female"), (1, "male")):
        tgt = load_moments(sexcode, args.sel)
        for c in sorted({c for c, _ in tgt}):
            ages = np.array(sorted(a for cc, a in tgt if cc == c))
            if ages.size < args.min_ages:
                continue
            target = np.array([tgt[(c, a)] for a in ages])
            ncell = np.array([max(size(label, c, a), 200) for a in ages])
            jobs.append((label, c, ages, target, ncell, keep, args.degree,
                         args.steps, args.reps, args.shrink, args.seed + c, args.wnoise))
    print(f"{len(jobs)} blocks x {args.steps} GMM steps x {args.reps} bootstrap reps")

    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(max_workers=args.jobs, initializer=_init,
                             initargs=(args.n, args.seed)) as ex:
        futs = [ex.submit(_run, j) for j in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            rows.append(f.result())
            if i % 20 == 0 or i == len(futs):
                print(f"  {i}/{len(futs)} blocks  ({time.time() - t0:.0f}s)")
    rows.sort(key=lambda r: (r["sex"], r["cohort"]))
    write_csv(rows, args.out)
    report(rows, keep, args)
    plot(rows, keep, args)


def write_csv(rows, path):
    """First columns replicate `g_cohort_cubic.csv` exactly, so the extrapolation and the
    aggregate-validation scripts read this file with no change."""
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


def report(rows, keep, args):
    names = [MOMENTS[k] for k in keep]
    move = np.array([r["step_move"] for r in rows])
    print("\nGMM step movement (max |dtheta| across coefficients, median over blocks):")
    for s in range(move.shape[1]):
        print(f"  step {s + 1}: {np.median(move[:, s]):.2e}")
    print(f"weight-matrix condition number after {args.shrink:.0%} shrinkage: "
          f"median {np.median([r['cond'] for r in rows]):.3g}")
    if args.wnoise:
        w = np.nanmedian(np.array([r["wsd"] for r in rows]), axis=0)
        a = np.median(np.array([r["se"] for r in rows]), axis=0)
        print(f"weight-matrix noise vs asymptotic se, median over blocks ({args.wnoise + 1} "
              f"bootstrap draws of S-hat):")
        for k in range(args.degree + 1):
            print(f"  g{k}: sd across S-hat draws {w[k]:.4f}   asymptotic se {a[k]:.4f}"
                  f"   ratio {w[k] / a[k]:.1f}x")

    dm = np.array([r["dmdg"] for r in rows]).mean(axis=0)
    by = np.array([r["by_moment"] for r in rows])
    print("\nper moment:   dm/dg (identification)   mean |model - data|")
    for i, nm in enumerate(names):
        print(f"  {nm:8s} {dm[i]:+22.4f}   {by[:, i].mean():18.4f}")

    for label in ("female", "male"):
        sub = [r for r in rows if r["sex"] == label]
        rm = np.array([r["rmse"] for r in sub])
        pv = np.array([r["p_value"] for r in sub])
        print(f"\n{label}: rmse median {np.median(rm):.4f}, max {rm.max():.4f}   "
              f"| J test rejects at 5% in {100 * (pv < 0.05).mean():.0f}% of blocks "
              f"(median p {np.median(pv):.3g}, df {sub[0]['df']})")


def _ls_table(args):
    path = args.ls or f"{OUT}/g_cohort_cubic_{args.sel}.csv"
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


def plot(rows, keep, args):
    d = pd.DataFrame([dict(sex=r["sex"], cohort=r["cohort"], p=r["p_value"],
                           **{f"g{k}": r["coef"][k] for k in range(4)},
                           **{f"se{k}": r["se"][k] for k in range(4)})
                      for r in rows])
    ls = _ls_table(args)
    npar = args.degree + 1
    fig, axes = plt.subplots(2, npar, figsize=(3.0 * npar, 5.2), sharex=True)
    for i, sex in enumerate(("male", "female")):
        s = d[d["sex"] == sex].sort_values("cohort")
        for k in range(npar):
            ax = axes[i, k]
            ax.fill_between(s["cohort"], s[f"g{k}"] - 1.96 * s[f"se{k}"],
                            s[f"g{k}"] + 1.96 * s[f"se{k}"], color=C_GMM, alpha=0.22, lw=0)
            ax.plot(s["cohort"], s[f"g{k}"], color=C_GMM, lw=1.5, label="GMM (all moments)")
            if ls is not None:
                t = ls[ls["sex"] == sex].sort_values("cohort")
                ax.plot(t["cohort"], t[f"g{k}"], color=C_LS, lw=1.3, ls=(0, (3, 2)),
                        label="LS (meanlog only)")
            ax.set_title(f"{sex}: g{k}", fontsize=9)
            ax.tick_params(labelsize=8)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            if i == 1:
                ax.set_xlabel("cohort (year at 25)", fontsize=8)
    axes[0, npar - 1].legend(frameon=False, fontsize=7)
    fig.suptitle(f"g(t) coefficients, centred on age 40  —  {args.sel}, "
                 f"degree {args.degree}, shaded 95% CI", fontsize=10)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(f"{OUT}/g_gmm_vs_ls{args.tag}.{ext}", dpi=200)
    plt.close(fig)

    names = [MOMENTS[k] for k in keep]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.4))
    ax = axes[0]
    for i, nm in enumerate(names):
        for sex, ls_ in (("male", "-"), ("female", (0, (2, 2)))):
            sub = [r for r in rows if r["sex"] == sex]
            ax.plot([r["cohort"] for r in sub], [r["by_moment"][i] for r in sub],
                    ls=ls_, lw=1.1, color=plt.cm.viridis(i / max(len(names) - 1, 1)),
                    label=nm if sex == "male" else None)
    ax.set_yscale("log")
    ax.set_title("mean |model − data| by moment (solid men, dashed women)", fontsize=9)
    ax.set_xlabel("cohort (year at 25)", fontsize=8)
    ax.legend(frameon=False, fontsize=6, ncol=2)

    ax = axes[1]
    for sex, col in (("male", "#2a78d6"), ("female", "#c1554d")):
        sub = [r for r in rows if r["sex"] == sex]
        ax.plot([r["cohort"] for r in sub], [r["p_value"] for r in sub], lw=1.3,
                color=col, label=sex)
    ax.axhline(0.05, color="0.6", lw=0.8, ls=(0, (3, 2)))
    ax.set_yscale("log")
    ax.set_title(f"J test p-value (df {rows[0]['df']})", fontsize=9)
    ax.set_xlabel("cohort (year at 25)", fontsize=8)
    ax.legend(frameon=False, fontsize=8)
    for a in axes:
        a.tick_params(labelsize=8)
        for side in ("top", "right"):
            a.spines[side].set_visible(False)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(f"{OUT}/g_gmm_moment_fit{args.tag}.{ext}", dpi=200)
    plt.close(fig)
    print(f"wrote {OUT}/g_gmm_vs_ls{args.tag}.pdf/.png and "
          f"{OUT}/g_gmm_moment_fit{args.tag}.pdf/.png")


if __name__ == "__main__":
    main()
