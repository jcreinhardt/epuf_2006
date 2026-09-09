"""EPUF cohort x age MEDIAN log earnings: the second target block for the g(t) estimator.

GKSW publish cohort x age moments for ages 25-55 ONLY -- every tabulation in
replication_repos/GKOS_2022 stops there -- so nothing in their data disciplines the profile
outside that window, and a polynomial fitted on 25-55 extrapolates badly (a cubic reaches
$386k at age 84; even the quadratic has no retirement margin).  EPUF covers ages 20-70 for
the same cohorts and is the only source that does, so it supplies the out-of-span target.

WHY THE MEDIAN, on both sides.  EPUF earnings are top-coded at the year's taxable maximum, so
its mean is unusable, but its median is not: in the cells this module returns the top code
binds for 9% (men) to 14% (men, 1988-2006) of positive earners, far above the median.  GKSW's
data carry no top code, so their p50 is clean too.  Matching median to median also keeps the
model's own mean-vs-median relation out of the bridge, which matters because that relation is
badly wrong: MEASURED, the model's mean-minus-median of log earnings is +0.03 while the data's
is -0.10 to -0.20 (the process is mildly right-skewed in log levels where the data are left-
skewed, unsurprising since GKOS target skewness of earnings CHANGES), a discrepancy of
0.12-0.23 log points that TRENDS with age at -0.039/decade.  A design matching GKSW meanlog to
EPUF p50 would force the wedge intercept to absorb that trend, and a constant cannot, so the
residual would land in the out-of-span shape -- exactly what the EPUF block exists to measure.

HOW BADLY, measured.  One g satisfying both blocks forces the identity

    delta(a) = EPUF p50(a) - GKSW meanlog(a) + [model mean(a) - model median(a)],

so delta's age slope IS the bias a constant pushes into the hinges.  Over the 31-age overlap
that slope is -0.043/decade for men and -0.039 for women (sd 0.045, 0.048), against -0.004 and
-0.007 (sd 0.022, 0.027) for the like-to-like median wedge this module actually uses -- ten
times less flat.  Fitted at the in-span mean age it misstates the requirement by -0.128 log
points at age 70 and +0.085 at age 20 (men).  The whole estimated old-age hinge is worth -0.125
log points at 70 for men, so the bias would be the SIZE OF THE SIGNAL.  The driver is not mainly
the model: the data's own mean-minus-median shrinks from -0.195 at age 25 to -0.100 at 55 while
the model's sits flat near +0.03, so the mixed design asks a constant to track a moving target.

THE SCREEN IS GKSW'S OWN, applied to EPUF: keep earnings >= 0.5 x 520 h x minimum wage in
nominal dollars (`guv_targets.sel0_threshold`, the ONE definition), so the truncation is the
same on both blocks and the same model cut log(Ymin) - g(t) serves both.  Earnings are then
deflated to BASE_YEAR dollars with GKSW's own PCE vintage, again the same one the published
files were built with.

WHAT IS NOT REMOVED, and is handled by a parameter instead: EPUF and GKSW are different
populations.  GKSW is Kopczuk-Saez-Song commerce-and-industry W-2 wages; EPUF is all covered
earnings including self-employment, agriculture, households, hospitals, education and public
administration.  The same cell therefore has a different median in the two sources.  MEASURED
over the 31-age overlap for cohorts 1957-1983, that wedge is -0.063 log points for men and
+0.023 for women, and -- this is what makes the design work -- it is nearly FLAT in age
(slope -0.004 and -0.007 per decade) and stable across cohorts (sd 0.008 and 0.014).  So one
free intercept per (sex, cohort) block absorbs it, and carrying that intercept from the
overlap out to age 70 mis-states it by under 0.01 log points.  See gcohort_epuf.py.

Cohort is GKSW's convention, the year at age 25 (cohort = yob + 25), so year = cohort + age -
25 and EPUF's 1951-2006 span gives cohort c the ages max(20, 1976 - c) to min(70, 2031 - c).
Every fitted cohort (1957-1983) therefore has all of 20-24; the old side runs from 19 cohorts
at age 56 down to 5 at age 70, and cohorts 1976+ have nothing above 55.

One DuckDB query, in the parent process; the result is passed into the workers.
"""
import io
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "code/cross_sections")    # run from the project root, per repo convention
from guv_targets import BASE_YEAR, _PCE_GKSW, sel0_threshold   # noqa: E402

DB = "processed_data/ssa.duckdb"
YEARS = (1951, 2006)                  # EPUF's span
AGES = np.arange(20, 71)              # the widest window the process is defensible over
CAP_MARGIN = 0.999                    # a median at/above this share of the top code is unusable


def load_p50(min_n=500, db=DB):
    """DataFrame(sex, cohort, age, year, n, p50, capped) -- p50 in log BASE_YEAR dollars.

    `capped` flags cells whose median is at the top code; they are returned rather than
    dropped so a caller can report the loss.  `usable` = n >= min_n and not capped.
    """
    y0, y1 = YEARS
    par = ",".join(f"({y},{sel0_threshold(y):.4f},"
                   f"{_PCE_GKSW[BASE_YEAR - 1947] / _PCE_GKSW[y - 1947]:.8f})"
                   for y in range(y0, y1 + 1))
    q = f"""COPY (WITH par(year, thr, defl) AS (VALUES {par}),
    tm AS (SELECT year, MAX(earnings) AS cap FROM annual WHERE earnings > 0 GROUP BY year),
    c AS (SELECT d.sex, d.yob + 25 AS cohort, a.year - d.yob AS age, a.year AS year,
                 a.earnings * par.defl AS re, tm.cap * par.defl AS capr
          FROM annual a JOIN demographic d USING (id)
          JOIN par ON par.year = a.year JOIN tm ON tm.year = a.year
          WHERE a.earnings >= par.thr AND d.sex IN (1, 2) AND d.yob IS NOT NULL
            AND a.year - d.yob BETWEEN {AGES[0]} AND {AGES[-1]})
    SELECT sex, cohort, age, year, COUNT(*) AS n, MAX(capr) AS capr,
           quantile_cont(re, 0.50) AS p50
    FROM c GROUP BY 1, 2, 3, 4) TO '/dev/stdout' (FORMAT CSV, HEADER TRUE);"""
    txt = subprocess.run(["duckdb", db, "-c", q], capture_output=True, text=True,
                         check=True).stdout
    d = pd.read_csv(io.StringIO(txt))
    d["sex"] = d["sex"].map({1: "male", 2: "female"})
    d["capped"] = d["p50"] >= CAP_MARGIN * d["capr"]
    d["usable"] = (d["n"] >= min_n) & ~d["capped"]
    d["p50"] = np.log(d["p50"])                  # log BASE_YEAR dollars, as the GKSW block
    return d.drop(columns="capr").sort_values(["sex", "cohort", "age"], ignore_index=True)


def by_block(d):
    """(sex, cohort) -> (ages, log p50, n) over the usable cells only."""
    out = {}
    for (sex, c), g in d[d.usable].groupby(["sex", "cohort"]):
        out[(sex, int(c))] = (g["age"].to_numpy(int), g["p50"].to_numpy(float),
                              g["n"].to_numpy(int))
    return out
