#!/usr/bin/env python
"""CMS-style OLS estimation of the cohort x sex lifecycle profile g(t).

This is the `--mode ols` estimator behind estimate_g_cohort.py, and the cheap
counterpart to the two SMM modes.  CMS ("Social Security and Trends in Wealth
Inequality") build their profiles in

    replication_repos/CMS/source/derived/lifecycle_income/create_lifecycle_income_parameters.do

by a plain per-(cohort, sex) regression of the PUBLISHED GKSW moment on an age
polynomial, with the moment first expressed relative to the economy-wide average wage:

    log( cohort mean-log earnings / SSA average wage )  ~  age + age^2 + age^3

THE DIFFERENCE THAT MATTERS, versus --mode smm-mean / smm-quantiles: CMS regress the
observed moment DIRECTLY, while the SMM modes invert it through the GKOS process, so
their g is the deterministic profile that makes the MODEL reproduce the moment after
nonemployment and the Ymin censoring.  The two are therefore not on the same level.
Writing u for the g-free part of log earnings, the model moment is

    meanlog(t) = g(t) + E[ u | u >= log(Ymin) - g(t) ],

so an OLS g absorbs the whole E[u | .] term that an SMM g strips out.  The gap is
reported per block as `eu_offset` = g0(OLS) - g0(the same OLS inverted through the moment
map).  Two details are what make it an exact bridge rather than a rough one.  E[u | .]
varies with age, so it is PROJECTED onto the same cubic basis and reduced to its constant
term (the plain mean over ages leaves ~0.08 log points on the table).  And it has to be
read at the INVERTED g, not at the OLS g -- that is a fixed point, solved here by cheap
functional iteration on suffix-table lookups (no optimizer; evaluating it one-shot at the
OLS g instead is off by 0.10-0.18 log points, and by different amounts for men and women).
With both, so

    g0(--mode ols)  =  g0(--mode smm-mean)  +  eu_offset

holds block by block, to the SMM fit's own residual.  The offset is large (~0.36 log
points), so do NOT read a level difference between the modes as disagreement.  Slope
coefficients need no such correction and are the directly useful comparison.

TWO BASES ARE REPORTED, per the columns below, because they answer different questions:

  g0..g3          project basis: OLS of meanlog on [1, tc, tc^2, tc^3], tc = t - T_CENTRE,
                  t = (age - 24)/10, in log 2013 dollars, NOT normalised by the average
                  wage.  This is the basis the SMM modes and every downstream consumer
                  (extrapolate_g_cohort.py, plot_agg_tax_dynamics.py) use, so it is what
                  makes --mode ols drop-in comparable and plottable against them.
  g0_raw..g3_raw  the same fit re-expressed on raw t, as elsewhere in the pipeline.
  cms_b0..cms_b3  CMS's own basis: OLS of meanlog - log(SSA average wage) on
                  [1, age, age^2, age^3] with RAW age.  b0 is the constant, b1..b3 the
                  age, age^2 and age^3 coefficients.  Directly comparable to the
                  coefficients in CMS's lifecycle_income_{male,female}.dta -- which is
                  exactly the check plots/compare_g_cms.py runs.

The average-wage series is CMS's own (`gksw2017.xlsx`, sheet data_mean_2013d_impute,
column `ssa`, thousands of 2013 dollars), so the reproduction uses their input, not a
re-derived one.  It requires replication_repos/CMS to be present; --mode ols is the only
mode that needs it.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "code/dynamics")          # run from project root, per repo convention
import gcohort_model as E

GKSW_XLSX = ("replication_repos/CMS/datastore/raw/lifecycle_income/orig/gksw2017.xlsx")

COLS = ("sex,cohort,n_ages,g0,g1,g2,g3,g0_raw,g1_raw,g2_raw,g3_raw,"
        "rmse,max_abs_resid,sdlog_gap,max_censored_share,"
        "cms_b0,cms_b1,cms_b2,cms_b3,eu_offset,"
        "se_g0,se_g1,se_g2,se_g3").split(",")


def average_wage():
    """SSA average earnings by year, thousands of 2013 dollars (CMS's own input)."""
    if not os.path.exists(GKSW_XLSX):
        sys.exit(f"--mode ols needs CMS's average-wage series but {GKSW_XLSX} is missing.\n"
                 f"Clone replication_repos/CMS, or use --mode smm-mean / smm-quantiles.")
    d = pd.read_excel(GKSW_XLSX, "data_mean_2013d_impute")[["year", "ssa"]].dropna()
    return dict(zip(d.year.astype(int), d.ssa.astype(float)))


def _ols(X, y):
    """Coefficients, residuals and classical standard errors."""
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    dof = max(X.shape[0] - X.shape[1], 1)
    s2 = float(r @ r) / dof
    se = np.sqrt(np.diag(np.linalg.pinv(X.T @ X)) * s2)
    return b, r, se


def fit_block(ages, target, sdtarget, cohort, awi, tables, degree=3):
    """One (sex, cohort) block.  Returns the tuple of values for COLS[3:]."""
    jj = ages - E.AGES[0]
    tc = E.T[jj] - E.T_CENTRE

    # --- project basis (centred t), and the same fit re-expressed on raw t
    X = np.vander(tc, degree + 1, increasing=True)
    b, r, se = _ols(X, target)
    coef = E.pad(b)
    coef_raw = E.uncentre(coef)

    # --- CMS basis: net of the average wage, RAW age, cubic
    rel = target - np.log(1000.0 * np.array([awi[cohort + a - 25] for a in ages]))
    Xc = np.column_stack([np.ones_like(ages, float), ages, ages**2.0, ages**3.0])
    bc, _, _ = _ols(Xc, rel)

    # --- diagnostics at the fitted g, on the same footing as the SMM modes.  eu_offset
    # is the E[u | .] term an OLS g absorbs and an SMM g strips out (see the docstring).
    years = cohort + ages - 25
    logymin = np.log(np.array([E.ymin(y) for y in years]))
    # The bridge to an SMM g is a FIXED POINT, not a one-shot evaluation: E[u | .] has to
    # be read at the INVERTED g, which is itself what subtracting E[u | .] produces.  Plain
    # functional iteration on b_inv = proj(target - E[u | g(b_inv)]) converges in a handful
    # of passes and costs only suffix-table lookups -- no optimizer, so --mode ols stays
    # cheap.  Only this DIAGNOSTIC is inverted; the reported g0..g3 remain pure OLS.
    b_inv = b.copy()
    for _ in range(100):
        cuts = logymin - (X @ b_inv)
        eut = np.array([E.cond_mean(tables[j], c) for j, c in zip(jj, cuts)])
        nxt = np.linalg.lstsq(X, target - eut, rcond=None)[0]
        if np.max(np.abs(nxt - b_inv)) < 1e-11:
            b_inv = nxt
            break
        b_inv = nxt
    eu = float(b[0] - b_inv[0])

    # sdlog_gap and max_censored_share are read at the INVERTED g (the loop's last cuts),
    # not at the OLS g, so they mean the same thing here as in the SMM modes' columns.
    cuts = logymin - (X @ b_inv)
    sd_gap = float(np.mean([E.cond_sd(tables[j], c) - sd
                            for j, c, sd in zip(jj, cuts, sdtarget)]))
    cens = max(E.censored_share(tables[j], c) for j, c in zip(jj, cuts))

    return (*coef, *coef_raw, float(np.sqrt((r**2).mean())), float(np.abs(r).max()),
            sd_gap, cens, *bc, eu, *E.pad(se))


def solve_all(sel, min_ages, tables, awi, degree=3):
    """All blocks: (rows, fits) with fits[(label, cohort)] = (ages, data, model)."""
    rows, fits = [], {}
    for sexcode, label in ((0, "female"), (1, "male")):
        tgt = E.load_targets(sexcode, sel)
        cohorts = sorted({c for c, _ in tgt})
        kept = 0
        for c in cohorts:
            ages = np.array(sorted(a for cc, a in tgt if cc == c))
            if ages.size < min_ages:
                continue
            target = np.array([tgt[(c, a)][0] for a in ages])
            sdtarget = np.array([tgt[(c, a)][1] for a in ages])
            vals = fit_block(ages, target, sdtarget, c, awi, tables, degree)
            rows.append((label, c, ages.size, *vals))
            X = np.vander(E.T[ages - E.AGES[0]] - E.T_CENTRE, degree + 1, increasing=True)
            fits[(label, c)] = (ages, target, X @ np.asarray(vals[:degree + 1]))
            kept += 1
        print(f"{label}: fitted {kept} cohorts with >= {min_ages} observed ages")
    return rows, fits
