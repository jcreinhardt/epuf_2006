"""Re-estimate the GKOS (2021) lifecycle profile g(t) as a cohort x sex cubic.

Every other parameter of the benchmark process (Table IV spec 6 + Table D.III) is
held FIXED at the published estimate; only the four coefficients of

    g(t) = g0 + g1*t + g2*t^2 + g3*t^3,      t = (age - 24)/10

are searched over, separately for each (sex, cohort) block.  The target is the
published mean of log real wage income by cohort x age,

    raw_data/guv_quantiles/cohortage_rwageinc_sel0_25_55_sex{0,1}.txt

whose `meanlog` column is built in the GKOS replication package by
`Appendix/DoFiles/AppendixD-DoFiles/cohortage_16mar2016_1pc.do` as

    keep if rwageinc >= 0.5*rminwg*520 & rwageinc ~= .   <- the censoring
    by cohort age: egen meanlog = mean(log(rwageinc))

i.e. the mean of log earnings CONDITIONAL on clearing a quarter of full-time work
(13 weeks x 40 hours = 520 hours) at half the legal minimum wage, in 2013 dollars.
Cohort is indexed by the calendar year at age 25 (`cohort = yob + 25`), so

    year = cohort + (age - 25),

which is why each cohort's cubic is estimated on its own diagonal of the APC plane.

The estimator exploits the fact that g enters the level multiplicatively, before
the censoring.  Writing u = log(1-nu) + alpha + beta*t + z + eps for the g-free
part of log earnings, log Y = g(t) + u and the sample rule Y >= Ymin becomes
u >= log(Ymin) - g(t).  So the model moment is

    m(g; t, year) = g(t) + E[ u | u >= log(Ymin_year) - g(t) ],

a function of the single scalar log(Ymin) - g(t) once the age-t distribution of u
is drawn.  One simulated panel is therefore enough: sort u within each age, take
suffix means, and every objective evaluation is a binary search.  m is strictly
increasing in g(t) (dm/dg lies in (0,1)), so each block is a well-behaved fit.

MEASURED: at the GKOS parameters the censoring turns out to be almost non-binding
*among positive earners* -- the reported max censored share is ~0.001 -- because
the nonemployment shock puts the entire low-earnings mass at exactly zero rather
than just above Ymin (cf. the paper's footnote 22: a $50,000 earner needs a -350
log point shock to fall below Ymin).  So dm/dg is ~1.000 in practice and the fit
is effectively least squares of meanlog on the cubic basis, shifted by E[u].  The
truncation machinery is still implemented exactly, but it does little work here,
which also means the estimates are insensitive to the Ymin construction.

CAVEAT: GKOS estimate on men only.  sex0 is FEMALE and sex1 is MALE in the source
do-file, and this script applies the male parameter vector to both, so the female
cubic absorbs every sex difference in dispersion and nonemployment risk on top of
the age profile.  Read g_female as a descriptive profile, not a structural one.

Run from the project root:
    python code/dynamics/estimate_g_cohort.py [--n N] [--min-ages K] [--sel sel0]
Output: output/dynamics/g_cohort_cubic.csv, output/dynamics/g_cohort_fit.{pdf,png}
"""

import argparse
import os

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import least_squares

TARGET_DIR = "raw_data/guv_quantiles"
OUT = "output/dynamics"

# --- GKOS benchmark parameters (Table IV spec 6; Table D.III) -----------------
# Identical to code/dynamics/simulate_gkos_ordinal.py.
RHO = 0.959
P_Z, MU_Z1, SIG_Z1, SIG_Z2 = 0.407, -0.085, 0.364, 0.069
MU_Z2 = -P_Z * MU_Z1 / (1 - P_Z)
SIG_Z0 = 0.714
P_E, MU_E1, SIG_E1, SIG_E2 = 0.130, 0.271, 0.285, 0.037
MU_E2 = -P_E * MU_E1 / (1 - P_E)
SIG_A, SIG_B, CORR_AB = 0.300, 0.196 / 10, 0.768
LAMBDA = 0.0001
NU_A, NU_B, NU_C, NU_D = -3.353, -0.859, -5.034, -2.895

# GKOS's own quadratic, shifted by log(1000) because the process is calibrated in
# thousands of dollars while the targets are in dollars.  Used only as a start value.
G_START = np.array([2.581 + np.log(1000.0) + 0.812 * 1.6 - 0.185 * 1.6**2,
                    0.812 - 2 * 0.185 * 1.6, -0.185, 0.0])

AGES = np.arange(25, 56)                      # 25..55, the span of the targets
T = (AGES - 24) / 10.0
# The cubic is estimated in t centred on age 40, so g0 is the (well-determined)
# level at mid-career rather than an extrapolation back to age 24.  Raw-t
# coefficients are recovered exactly by `uncentre` and reported alongside.
T_CENTRE = (40 - 24) / 10.0

# --- Deflator and minimum wage ------------------------------------------------
# Verbatim from replication_repos/GKOS_2022/DoFiles/merge_reshape_06jan2016_1pc.do.
# PCE price index, 1947-2014; base_price=67 -> 2013 dollars.
PCE_FIRST_YEAR = 1947
PCE = np.array([
    13.325, 14.079, 13.969, 14.136, 15.098, 15.408, 15.613, 15.746, 15.810, 16.126, 16.616,
    17.007, 17.262, 17.546, 17.730, 17.939, 18.149, 18.414, 18.681, 19.155, 19.637, 20.402,
    21.327, 22.325, 23.274, 24.070, 25.368, 28.009, 30.348, 32.013, 34.091, 36.479, 39.714,
    43.978, 47.908, 50.553, 52.729, 54.724, 56.661, 57.887, 59.650, 61.974, 64.642, 67.440,
    69.653, 71.494, 73.279, 74.803, 76.356, 77.981, 79.327, 79.935, 81.110, 83.132, 84.736,
    85.874, 87.572, 89.703, 92.261, 94.729, 97.101, 100.065, 100.000, 101.653, 104.149,
    106.121, 107.572, 109.105])
# Nominal federal minimum wage, 1947-2013.
MINWG = np.array([
    0.40, 0.40, 0.40, 0.40, 0.75, 0.75, 0.75, 0.75, 0.75, 1.00, 1.00, 1.00, 1.00, 1.00,
    1.00, 1.15, 1.15, 1.25, 1.25, 1.25, 1.25, 1.40, 1.60, 1.60, 1.60, 1.60, 1.60, 1.60,
    2.00, 2.10, 2.10, 2.30, 2.65, 2.90, 3.10, 3.35, 3.35, 3.35, 3.35, 3.35, 3.35, 3.35,
    3.35, 3.35, 3.80, 4.25, 4.25, 4.25, 4.25, 4.25, 4.75, 5.15, 5.15, 5.15, 5.15, 5.15,
    5.15, 5.15, 5.15, 5.15, 5.15, 5.85, 6.55, 7.25, 7.25, 7.25, 7.25])
BASE_YEAR = 2013
HOURS = 520.0                                 # 13 weeks x 40 hours
MINWG_FRAC = 0.5                              # half the legal minimum wage


def ymin(year):
    """Annual earnings floor in BASE_YEAR dollars, as imposed in the do-file."""
    if not PCE_FIRST_YEAR <= year <= PCE_FIRST_YEAR + MINWG.size - 1:
        raise ValueError(f"year {year} outside the deflator/minimum-wage tables")
    i = year - PCE_FIRST_YEAR
    rminwg = MINWG[i] * PCE[BASE_YEAR - PCE_FIRST_YEAR] / PCE[i]
    return MINWG_FRAC * rminwg * HOURS


# --- Targets ------------------------------------------------------------------

def load_targets(sex, sel):
    """(cohort, age) -> (meanlog, sdlog).  Only meanlog is targeted; sdlog is
    carried along as an untargeted check on the fixed dispersion parameters."""
    path = f"{TARGET_DIR}/cohortage_rwageinc_{sel}_25_55_sex{sex}.txt"
    raw = np.genfromtxt(path, skip_header=1, usecols=(0, 1, 2, 3))
    return {(int(c), int(a)): (m, sd) for c, a, m, sd in raw}


# --- Simulation of the g-free part of log earnings ----------------------------

def simulate_u(rng, n):
    """u[i, j] = log(1 - nu) + alpha + beta*t + z + eps at age AGES[j].

    Full-year nonemployment (nu == 1) yields zero earnings, which can never clear
    Ymin, so those draws are recorded as -inf and dropped from the sorted arrays.
    """
    cov = CORR_AB * SIG_A * SIG_B
    ab = rng.multivariate_normal([0, 0], [[SIG_A**2, cov], [cov, SIG_B**2]], n)
    alpha, beta = ab[:, 0], ab[:, 1]

    u = np.empty((n, AGES.size))
    z = SIG_Z0 * rng.standard_normal(n)
    for j, t in enumerate(T):
        if j > 0:
            pick = rng.random(n) < P_Z
            eta = np.where(pick, MU_Z1 + SIG_Z1 * rng.standard_normal(n),
                           MU_Z2 + SIG_Z2 * rng.standard_normal(n))
            z = RHO * z + eta
        pick = rng.random(n) < P_E
        eps = np.where(pick, MU_E1 + SIG_E1 * rng.standard_normal(n),
                       MU_E2 + SIG_E2 * rng.standard_normal(n))
        xi = NU_A + NU_B * t + NU_C * z + NU_D * t * z
        hit = rng.random(n) < 1 / (1 + np.exp(-xi))
        nu = np.where(hit, np.minimum(1.0, rng.exponential(1 / LAMBDA, n)), 0.0)
        with np.errstate(divide="ignore"):
            u[:, j] = np.log1p(-nu) + alpha + beta * t + z + eps
    return u


def suffix_tables(u):
    """Per age: sorted finite u with suffix sums of u and u^2, for O(log n)
    truncated means and standard deviations."""
    tables = []
    for j in range(u.shape[1]):
        v = np.sort(u[np.isfinite(u[:, j]), j])
        s1 = np.concatenate([np.cumsum(v[::-1])[::-1], [0.0]])
        s2 = np.concatenate([np.cumsum((v**2)[::-1])[::-1], [0.0]])
        tables.append((v, s1, s2))
    return tables


def _tail(table, cut):
    v, s1, s2 = table
    k = np.searchsorted(v, cut, side="left")
    return v, s1, s2, k, v.size - k


def cond_mean(table, cut):
    """E[u | u >= cut]."""
    v, s1, _, k, m = _tail(table, cut)
    return v[-1] if m <= 0 else s1[k] / m


def cond_sd(table, cut):
    """sd(u | u >= cut); log Y and u differ by a constant, so this is sd(log Y)."""
    v, s1, s2, k, m = _tail(table, cut)
    if m <= 1:
        return np.nan
    return np.sqrt(max(s2[k] / m - (s1[k] / m) ** 2, 0.0))


def censored_share(table, cut):
    """Share of the positive-earnings draws that fall below the Ymin cut."""
    v, _, _, k, _ = _tail(table, cut)
    return k / v.size


# --- One (sex, cohort) block --------------------------------------------------

def uncentre(coef):
    """Coefficients on raw t, given coefficients on (t - T_CENTRE)."""
    a, m = coef, T_CENTRE
    return np.array([a[0] - a[1] * m + a[2] * m**2 - a[3] * m**3,
                     a[1] - 2 * a[2] * m + 3 * a[3] * m**2,
                     a[2] - 3 * a[3] * m,
                     a[3]])


def model_meanlog(coef, jj, logymin, tables):
    """m(g) = g(t) + E[u | u >= log(Ymin) - g(t)] at each requested age index."""
    tt = T[jj] - T_CENTRE
    g = coef[0] + coef[1] * tt + coef[2] * tt**2 + coef[3] * tt**3
    return np.array([gi + cond_mean(tables[j], ci - gi)
                     for j, gi, ci in zip(jj, g, logymin)])


def fit_block(jj, logymin, target, tables, start):
    res = least_squares(lambda c: model_meanlog(c, jj, logymin, tables) - target,
                        start, method="lm", xtol=1e-12, ftol=1e-12)
    return res.x, res.fun


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200_000, help="simulated individuals")
    ap.add_argument("--min-ages", type=int, default=31,
                    help="skip cohorts with fewer observed ages than this; a cubic "
                         "fitted to a short arc extrapolates wildly outside it")
    ap.add_argument("--sel", default="sel0", help="selection tag of the target file")
    ap.add_argument("--seed", type=int, default=20260821)
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    print(f"simulating {args.n:,} individuals over ages 25-55 ...")
    tables = suffix_tables(simulate_u(rng, args.n))
    empl = np.array([t[0].size for t in tables]) / args.n
    print(f"  share with positive earnings: {empl.min():.3f} (age {AGES[empl.argmin()]}) "
          f"to {empl.max():.3f} (age {AGES[empl.argmax()]})")

    rows, fits = [], {}
    for sex in (0, 1):
        label = "female" if sex == 0 else "male"
        tgt = load_targets(sex, args.sel)
        cohorts = sorted({c for c, _ in tgt})
        skipped = 0
        for c in cohorts:
            ages = np.array(sorted(a for cc, a in tgt if cc == c))
            if ages.size < args.min_ages:
                skipped += 1
                continue
            jj = ages - AGES[0]
            years = c + ages - 25
            logymin = np.log(np.array([ymin(y) for y in years]))
            target = np.array([tgt[(c, a)][0] for a in ages])
            coef, resid = fit_block(jj, logymin, target, tables, G_START)
            # untargeted diagnostics at the fitted g
            tt = T[jj] - T_CENTRE
            gfit = coef[0] + coef[1] * tt + coef[2] * tt**2 + coef[3] * tt**3
            cuts = logymin - gfit
            sd_gap = np.mean([cond_sd(tables[j], ci) - tgt[(c, a)][1]
                              for j, a, ci in zip(jj, ages, cuts)])
            cens = max(censored_share(tables[j], ci) for j, ci in zip(jj, cuts))
            rows.append((label, c, ages.size, *coef, *uncentre(coef),
                         np.sqrt((resid**2).mean()), np.abs(resid).max(),
                         sd_gap, cens))
            fits[(label, c)] = (ages, target, target + resid)
        print(f"{label}: fitted {len(cohorts) - skipped} cohorts, "
              f"skipped {skipped} with < {args.min_ages} ages")

    hdr = ("sex,cohort,n_ages,g0,g1,g2,g3,"          # on (t - T_CENTRE)
       "g0_raw,g1_raw,g2_raw,g3_raw,"            # on raw t
       "rmse,max_abs_resid,sdlog_gap,max_censored_share")
    path = f"{OUT}/g_cohort_cubic.csv"
    with open(path, "w") as f:
        f.write(hdr + "\n")
        for r in rows:
            f.write(f"{r[0]},{r[1]},{r[2]}," + ",".join(f"{v:.6f}" for v in r[3:]) + "\n")
    print(f"wrote {path}  ({len(rows)} blocks)")

    rmse = np.array([r[11] for r in rows])
    print(f"fit rmse over blocks: median {np.median(rmse):.4f}, "
          f"p90 {np.percentile(rmse, 90):.4f}, max {rmse.max():.4f} log points")
    for label in ("female", "male"):
        gap = np.array([r[13] for r in rows if r[0] == label])
        cens = np.array([r[14] for r in rows if r[0] == label])
        print(f"{label}: UNTARGETED sdlog gap (model - data) median {np.median(gap):+.3f}; "
              f"max censored share across cells {cens.max():.3f}")

    plot(rows, fits)


def plot(rows, fits):
    full = [c for (s, c) in fits if s == "male" and fits[(s, c)][0].size == 31]
    show = [full[0], full[len(full) // 2], full[-1]] if full else []
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.3))

    ax = axes[0]
    for label, color in (("female", "#c1554d"), ("male", "#2f6f9f")):
        for c in show:
            if (label, c) in fits:
                a, d, m = fits[(label, c)]
                ax.plot(a, d, color=color, lw=1.6)
                ax.plot(a, m, color=color, lw=1.4, ls=(0, (2, 2)))
    ax.set_title("mean log earnings: data (solid) vs fit (dashed)")
    ax.set_xlabel("age")

    full_lo, full_hi = (min(full), max(full)) if full else (None, None)

    for k, (i, name) in enumerate(((4, "g1 (linear)"), (5, "g2 (quadratic)"))):
        ax = axes[k + 1]
        for label, color in (("female", "#c1554d"), ("male", "#2f6f9f")):
            sel = [(r[1], r[i]) for r in rows if r[0] == label]
            ax.plot([x for x, _ in sel], [y for _, y in sel], color=color, lw=1.5,
                    label=label)
        ax.set_title(name + " coefficient by cohort")
        ax.set_xlabel("cohort (year at age 25)")
        ax.axhline(0, color="0.7", lw=0.8)
        # outside this band the cohort is observed over part of the age span only,
        # and the cubic is extrapolating rather than interpolating
        if full_lo is not None and full_lo != full_hi:
            ax.axvspan(full_lo, full_hi, color="0.9", zorder=0)
    axes[2].legend(frameon=False)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(f"{OUT}/g_cohort_fit.{ext}", dpi=200)
    print(f"wrote {OUT}/g_cohort_fit.pdf/.png")


if __name__ == "__main__":
    main()
