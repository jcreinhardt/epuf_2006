"""CMS-style OLS estimation of the cohort x sex profile g(t): the `--mode ols` estimator
behind estimate_g_cohort.py, and the cheap counterpart to the SMM modes.

CMS ("Social Security and Trends in Wealth Inequality") build their profiles in
replication_repos/CMS/source/derived/lifecycle_income/create_lifecycle_income_parameters.do
by a plain per-(cohort, sex) regression of the PUBLISHED GKSW meanlog on an age polynomial,
with the moment first expressed relative to the economy-wide average wage:

    log( cohort mean-log earnings / SSA average wage )  ~  age + age^2 + age^3

THE DIFFERENCE THAT MATTERS, versus the SMM modes: CMS regress the observed moment DIRECTLY,
while the SMM modes invert it through the GKOS process.  With the model moment
meanlog(t) = g(t) + E[u | u >= log(Ymin) - g(t)], an OLS g absorbs the whole E[u | .] term an
SMM g strips out, so the two are on different LEVELS.  The gap is reported per block as
`eu_offset` = g0(OLS) - g0(the same OLS inverted through the moment map), and

    g0(--mode ols) = g0(--mode smm-mean) + eu_offset

holds block by block to the SMM fit's own residual.  Two details make that exact rather than
rough: E[u | .] varies with age, so it is PROJECTED onto the cubic basis and reduced to its
constant term (a plain mean over ages is off by ~0.08); and it must be read at the INVERTED g,
which is a fixed point solved by functional iteration on suffix-table lookups (reading it
one-shot at the OLS g is off by 0.10-0.18, differently for men and women).  The offset is
~0.36 log points, so never read a level difference between modes as disagreement; slopes need
no correction and are the useful comparison.

Two bases are reported: g0..g3 / g*_raw in the project basis (log 2013 dollars, centred and
raw t), which makes this mode drop-in comparable with the SMM modes downstream, and
cms_b0..cms_b3 in CMS's own basis (net of the average wage, RAW age), directly comparable
with their lifecycle_income_{male,female}.dta -- which is the check plots/compare_g_cms.py
runs.  The average-wage series is CMS's own input (gksw2017.xlsx), so this is the only mode
that needs replication_repos/CMS.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "code/dynamics")          # run from the project root, per repo convention
import gcohort_model as E

GKSW_XLSX = "replication_repos/CMS/datastore/raw/lifecycle_income/orig/gksw2017.xlsx"

COLS = ("sex,cohort,n_ages,g0,g1,g2,g3,g0_raw,g1_raw,g2_raw,g3_raw,"
        "rmse,max_abs_resid,sdlog_gap,max_censored_share,"
        "cms_b0,cms_b1,cms_b2,cms_b3,eu_offset,se_g0,se_g1,se_g2,se_g3").split(",")


def average_wage():
    """SSA average earnings by year, thousands of 2013 dollars (CMS's own input)."""
    if not os.path.exists(GKSW_XLSX):
        sys.exit(f"--mode ols needs CMS's average-wage series but {GKSW_XLSX} is missing.\n"
                 f"Clone replication_repos/CMS, or use --mode smm-mean / smm-quantiles.")
    d = pd.read_excel(GKSW_XLSX, "data_mean_2013d_impute")[["year", "ssa"]].dropna()
    return dict(zip(d.year.astype(int), d.ssa.astype(float)))


def cms_basis(rel, ages):
    """OLS of `rel` on [1, age, age^2, age^3] with RAW age: (b0, b1, b2, b3)."""
    X = np.column_stack([np.ones_like(ages, float), ages, ages**2.0, ages**3.0])
    return np.linalg.lstsq(X, rel, rcond=None)[0]


def fit_block(ages, target, cohort, awi, tables, degree=3):
    """One (sex, cohort) block; `target` holds all 10 moments.  Returns COLS[3:]."""
    jj = ages - E.AGES[0]
    X = E.basis(E.TC[jj], degree)
    meanlog, sdlog = target[:, 0], target[:, 1]

    b, *_ = np.linalg.lstsq(X, meanlog, rcond=None)
    r = meanlog - X @ b
    s2 = float(r @ r) / max(X.shape[0] - X.shape[1], 1)
    se = np.sqrt(np.diag(np.linalg.pinv(X.T @ X)) * s2)
    coef = E.pad(b)

    rel = meanlog - np.log(1000.0 * np.array([awi[cohort + a - 25] for a in ages]))
    bc = cms_basis(rel, ages)

    # eu_offset: the fixed point b_inv = proj(meanlog - E[u | g(b_inv)]).  Diagnostic only;
    # the reported g stays pure OLS.
    logym = E.logymin(cohort, ages)
    b_inv = b.copy()
    for _ in range(100):
        eut = np.array([E.cond_mean(tables[j], c) for j, c in zip(jj, logym - X @ b_inv)])
        nxt = np.linalg.lstsq(X, meanlog - eut, rcond=None)[0]
        done = np.max(np.abs(nxt - b_inv)) < 1e-11
        b_inv = nxt
        if done:
            break
    cuts = logym - X @ b_inv       # sdlog_gap / censoring read at the INVERTED g, as in SMM
    sd_gap = float(np.mean([E.cond_sd(tables[j], c) for j, c in zip(jj, cuts)] - sdlog))
    cens = max(E.censored_share(tables[j], c) for j, c in zip(jj, cuts))
    return (*coef, *E.uncentre(coef), float(np.sqrt((r**2).mean())), float(np.abs(r).max()),
            sd_gap, cens, *bc, float(b[0] - b_inv[0]), *E.pad(se))


def solve_all(sel, min_ages, tables, awi, degree=3):
    rows = [(label, c, ages.size, *fit_block(ages, target, c, awi, tables, degree))
            for label, c, ages, target in E.blocks(sel, min_ages)]
    for label in ("female", "male"):
        n = sum(r[0] == label for r in rows)
        print(f"{label}: fitted {n} cohorts with >= {min_ages} observed ages")
    return rows
