"""The GKOS (2021) benchmark earnings process with a cohort x sex lifecycle profile.

Every parameter of the benchmark process (Table IV spec 6 + Table D.III) is held FIXED at
the published estimate; only the coefficients of

    g(t) = g0 + g1*t + g2*t^2 + g3*t^3,      t = (age - 24)/10

are estimated, separately per (sex, cohort) block, against the published cohort x age
moment files in raw_data/guv_quantiles/ (see `load_moments`).  This module is the LIBRARY
shared by the estimators (gcohort_ols.py, gcohort_smm.py), the extrapolation and every
figure script: the process, its simulation, the suffix tables that make the moment map
O(log n), and the polynomial bookkeeping.  It draws nothing and has no CLI.

The process (paper eq. 2-8), with u the g-free part of log earnings:

    log Y = g(t) + u,   u = log(1 - nu) + alpha + beta*t + z + eps

    z_t = rho z_{t-1} + eta_t         eta ~ two-normal mixture, mean zero
    eps ~ two-normal mixture, mean zero
    (alpha, beta) ~ bivariate normal   (heterogeneous income profiles)
    nu = 1 w.p. p_nu(t, z) = logit(a + b t + c z + d t z), else 0   (lambda = 1e-4 makes
        every nonemployment spell a full year, so u = -inf and the observation is a zero)

The published target is the mean (and percentiles, sd, skew, kurt) of log real wage income
by cohort x age CONDITIONAL on the GKSW screen Y >= Ymin (a quarter of full-time work at half
the minimum wage, `guv_targets.sel0_threshold`).  Because g enters before the screen, the
sample rule is u >= log(Ymin) - g(t), so every model moment is a functional of the single
scalar cut c = log(Ymin) - g(t) applied to the age-t distribution of u:

    meanlog = g(t) + E[u | u >= c],   log p_q = g(t) + Q_q(u | u >= c),   sd/skew/kurt of (u | u >= c)

One simulated panel therefore suffices: sort u within each age once, keep suffix sums, and
each objective evaluation is a binary search.  MEASURED: at the GKOS parameters the cut is
nearly non-binding among positive earners (max censored share ~0.001) because the
nonemployment shock puts the low mass at exactly zero, so dm/dg ~ 1.000 for every level
moment and ~0 for the shape moments -- the shape moments cannot identify g.

Cohort is indexed by the calendar year at age 25 (`cohort = yob + 25`, GKSW's convention),
so year = cohort + age - 25 and each block is one diagonal of the APC plane.  The cubic is
estimated in t centred on age 40 (`T_CENTRE`), so g0 is the well-determined mid-career level;
`uncentre` recovers raw-t coefficients, which the CSVs carry as g*_raw.

TWO CAVEATS.  (1) GKOS estimate on men only; guv sex0 is FEMALE and sex1 MALE, and the male
parameter vector is applied to both, so g_female absorbs every sex difference in dispersion
and nonemployment risk on top of the age profile -- read it as descriptive.  (2) The HIP
slope: Table IV reports sigma_beta = 0.196 ON THE DECADE-SCALED t, i.e. ~2% per year of age
(the paper's own gloss, matching Guvenen 2009).  CMS's Simulation.m uses 0.196/10 on the same
t, and an earlier version of this module copied that.  It leaves mean log earnings -- and so
every g estimate -- untouched (E[u] does not depend on sigma_beta), but it understates the
dispersion of log earnings past age 40 and the mean LEVEL E[e^u] by 12% at age 40 and 36% at
55, which is what the aggregate-earnings validation runs on.
"""
import sys

import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, "code/cross_sections")    # run from the project root, per repo convention
from guv_targets import (BASE_YEAR, GUV_DIR, FUNCTIONALS, QUANTS, _PCE_GKSW,   # noqa: E402
                         sel0_threshold)

# --- GKOS benchmark parameters (Table IV spec 6; Table D.III) -----------------
RHO = 0.959
P_Z, MU_Z1, SIG_Z1, SIG_Z2 = 0.407, -0.085, 0.364, 0.069
MU_Z2 = -P_Z * MU_Z1 / (1 - P_Z)
SIG_Z0 = 0.714
P_E, MU_E1, SIG_E1, SIG_E2 = 0.130, 0.271, 0.285, 0.037
MU_E2 = -P_E * MU_E1 / (1 - P_E)
SIG_A, SIG_B, CORR_AB = 0.300, 0.196, 0.768      # sigma_beta per DECADE of age (t units)
LAMBDA = 0.0001
NU_A, NU_B, NU_C, NU_D = -3.353, -0.859, -5.034, -2.895
G_GKOS = np.array([2.581, 0.812, -0.185, 0.0])   # their g(t) on raw t, in thousands of dollars

# --- age bookkeeping ------------------------------------------------------------
AGES = np.arange(25, 56)                          # the span of the published targets
T_CENTRE = (40 - 24) / 10.0


def tt(age):
    """Normalised age t = (age - 24)/10."""
    return (np.asarray(age, float) - 24.0) / 10.0


T = tt(AGES)
TC = T - T_CENTRE                                 # centred t at the target ages


def pad(coef):
    """Any-degree coefficient vector padded out to the cubic layout (trailing zeros)."""
    c = np.asarray(coef, float)
    return np.concatenate([c, np.zeros(4 - c.size)]) if c.size < 4 else c


def basis(tc, degree):
    """[1, tc, tc^2, ...] as a (len(tc), degree+1) design matrix."""
    return np.vander(np.atleast_1d(np.asarray(tc, float)), degree + 1, increasing=True)


def gpoly(coef, tc):
    """g at centred t (scalar or vector), for a coefficient vector of any degree <= 3."""
    g = basis(tc, 3) @ pad(coef)
    return g[0] if np.ndim(tc) == 0 else g


_m = T_CENTRE
UNCENTRE = np.array([[1, -_m, _m**2, -_m**3], [0, 1, -2 * _m, 3 * _m**2],
                     [0, 0, 1, -3 * _m], [0, 0, 0, 1]], float)


def uncentre(coef):
    """Coefficients on raw t from coefficients on (t - T_CENTRE); exact and linear, so the
    delta method on UNCENTRE is exact too."""
    return UNCENTRE @ pad(coef)


def centre(coef_raw):
    return np.linalg.solve(UNCENTRE, pad(coef_raw))


# Start value: GKOS's own quadratic, shifted by log(1000) because their process is in
# thousands of dollars and the targets are in dollars.
G_START = centre(G_GKOS + np.array([np.log(1000.0), 0, 0, 0]))


# --- deflator and screen: ONE definition, in guv_targets ------------------------

def pce(year):
    """GKSW's PCE vintage (2009 = 100), 1947-2014 -- the one the target files were deflated
    with, so it is the one that turns their BASE_YEAR dollars back into nominal."""
    return _PCE_GKSW[year - 1947]


def ymin(year):
    """The GKSW screen in BASE_YEAR dollars: 0.5 x 520 h x minimum wage, deflated."""
    return sel0_threshold(year) * pce(BASE_YEAR) / pce(year)


# --- targets ----------------------------------------------------------------------
MOMENTS = list(FUNCTIONALS)     # meanlog sdlog skewlog kurtlog p10 p25 p50 p75 p90 p98
QS = np.array(QUANTS)
SEXES = (("female", 0), ("male", 1))              # our label -> guv file suffix


def load_moments(label, sel):
    """(cohort, age) -> the length-10 published moment vector, percentiles in logs so every
    entry is in log points."""
    code = dict(SEXES)[label]
    raw = np.genfromtxt(GUV_DIR / f"cohortage_rwageinc_{sel}_25_55_sex{code}.txt",
                        skip_header=1)
    out = {}
    for row in raw:
        m = row[2:12].copy()
        m[4:] = np.log(m[4:])
        out[(int(row[0]), int(row[1]))] = m
    return out


def blocks(sel, min_ages):
    """Every (label, cohort, ages, target[n_ages x 10]) block with >= min_ages observed ages.
    A cubic fitted to a short arc extrapolates wildly outside it, so the default keeps only
    the full 25-55 span (cohorts 1957-1983)."""
    for label, _ in SEXES:
        tgt = load_moments(label, sel)
        for c in sorted({c for c, _ in tgt}):
            ages = np.array(sorted(a for cc, a in tgt if cc == c))
            if ages.size >= min_ages:
                yield label, c, ages, np.array([tgt[(c, a)] for a in ages])


def logymin(cohort, ages):
    return np.log([ymin(cohort + a - 25) for a in ages])


# --- simulation of the g-free part of log earnings -------------------------------

def entry_sd(age0):
    """sd of z at `age0` such that sd(z) at age 25 is still SIG_Z0.  GKOS place labour-market
    entry at 25 and the AR(1) has no backward form, so a panel started earlier needs the
    initial condition solved: z's dispersion then GROWS from entry to 25 (0.61 at age 20)."""
    if age0 >= 25:
        return SIG_Z0
    ve = P_Z * (MU_Z1**2 + SIG_Z1**2) + (1 - P_Z) * (MU_Z2**2 + SIG_Z2**2)
    k = 25 - age0
    v0 = (SIG_Z0**2 - ve * sum(RHO ** (2 * i) for i in range(k))) / RHO ** (2 * k)
    if v0 <= 0:
        raise ValueError(f"age {age0} is too early to preserve the age-25 calibration")
    return float(np.sqrt(v0))


def simulate_u(rng, n, ages=AGES):
    """u[i, j] = log(1 - nu) + alpha + beta*t + z + eps at ages[j]; -inf for a full-year
    nonemployment spell (zero earnings, which can never clear the screen)."""
    ages = np.asarray(ages)
    cov = CORR_AB * SIG_A * SIG_B
    ab = rng.multivariate_normal([0, 0], [[SIG_A**2, cov], [cov, SIG_B**2]], n)
    alpha, beta = ab[:, 0], ab[:, 1]
    u = np.empty((n, ages.size))
    z = entry_sd(int(ages[0])) * rng.standard_normal(n)
    for j, t in enumerate(tt(ages)):
        if j > 0:
            pick = rng.random(n) < P_Z
            z = RHO * z + np.where(pick, MU_Z1 + SIG_Z1 * rng.standard_normal(n),
                                   MU_Z2 + SIG_Z2 * rng.standard_normal(n))
        pick = rng.random(n) < P_E
        eps = np.where(pick, MU_E1 + SIG_E1 * rng.standard_normal(n),
                       MU_E2 + SIG_E2 * rng.standard_normal(n))
        xi = NU_A + NU_B * t + NU_C * z + NU_D * t * z
        hit = rng.random(n) < 1 / (1 + np.exp(-xi))
        nu = np.where(hit, np.minimum(1.0, rng.exponential(1 / LAMBDA, n)), 0.0)
        with np.errstate(divide="ignore"):
            u[:, j] = np.log1p(-nu) + alpha + beta * t + z + eps
    return u


def suffix_tables(u, order=2):
    """Per age: (sorted finite u, suffix sums of u^1..u^order).  Order 2 serves the truncated
    mean and sd; the SMM shape moments need 4."""
    tables = []
    for j in range(u.shape[1]):
        v = np.sort(u[np.isfinite(u[:, j]), j])
        sums = [np.concatenate([np.cumsum((v**k)[::-1])[::-1], [0.0]])
                for k in range(1, order + 1)]
        tables.append((v, *sums))
    return tables


def _tail(table, cut):
    v, s1, s2 = table[:3]
    k = np.searchsorted(v, cut, side="left")
    return v, s1, s2, k, v.size - k


def cond_mean(table, cut):
    """E[u | u >= cut]."""
    v, s1, _, k, m = _tail(table, cut)
    return v[-1] if m <= 0 else s1[k] / m


def cond_sd(table, cut):
    """sd(u | u >= cut) = sd(log Y | Y >= Ymin), since the two differ by a constant."""
    _, s1, s2, k, m = _tail(table, cut)
    return np.nan if m <= 1 else np.sqrt(max(s2[k] / m - (s1[k] / m) ** 2, 0.0))


def censored_share(table, cut):
    """Share of the positive-earnings draws that fall below the cut."""
    v, _, _, k, _ = _tail(table, cut)
    return k / v.size


# --- the mean-only fit (start value for SMM; the OLS bridge) -----------------------

def model_meanlog(coef, jj, logym, tables):
    """m(g) = g(t) + E[u | u >= log(Ymin) - g(t)] at the age indices jj."""
    g = gpoly(coef, TC[jj])
    return np.array([gi + cond_mean(tables[j], ci - gi) for j, gi, ci in zip(jj, g, logym)])


def fit_block(jj, logym, target, tables, start=G_START, degree=3):
    """Least squares of the published meanlog on the model moment over the first degree+1
    coefficients; the rest stay zero so every fit shares the 4-column layout."""
    res = least_squares(lambda c: model_meanlog(c, jj, logym, tables) - target,
                        pad(start)[:degree + 1], method="lm", xtol=1e-12, ftol=1e-12)
    return pad(res.x), res.fun
