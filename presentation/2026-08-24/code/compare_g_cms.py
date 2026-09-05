"""Compare the re-estimated g(t) against the CMS (2024) lifecycle profiles.

Only cohorts observed over the FULL age span 25-55 are used, so every cubic is
interpolating rather than extrapolating.

CMS ("Social Security and Trends in Wealth Inequality") build their profiles in
`replication_repos/CMS/source/derived/lifecycle_income/create_lifecycle_income_parameters.do`
from the same published GKSW moments this project targets: the `male_3`/`female_3`
sheets of `gksw2017.xlsx` reproduce `cohortage_rwageinc_sel3_*` exactly (verified
to machine precision), and `male_0` reproduces `sel0`.  Their estimator is a plain
OLS per cohort x sex,

    log( cohort mean-log earnings / economy-wide average wage )  ~  age + age^2 + age^3

so their coefficients are on RAW age and their dependent variable is normalised by
the SSA average wage, in 2013 dollars.  Two differences from this project's fit:

  1. CMS use sel3 (lifetime earnings above a floor AND >= 15 years of work); the
     estimation here targets sel0.  Pass --sel sel3 for the apples-to-apples run;
     the printed summary reports how much the choice moves each coefficient.
  2. CMS regress the observed moment directly.  This project inverts the moment
     through the GKOS process, so its g is the deterministic profile that makes the
     MODEL reproduce the moment after nonemployment and the Ymin censoring.

To make the two comparable, the fitted g (log 2013 dollars, in t = (age-24)/10) is
converted to the CMS basis: subtract log of the average wage in the cell's calendar
year, then project onto [1, age, age^2, age^3] over ages 25-55 -- exactly the
regression CMS run on their own input.

Run from the project root:  python code/dynamics/compare_g_cms.py [--sel sel0]
Output: output/dynamics/g_vs_cms_{cons,age,age2,age3}.{pdf,png}
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import estimate_g_cohort as E

CMS = "replication_repos/CMS"
CMS_COEF = f"{CMS}/datastore/derived/lifecycle_income/lifecycle_income_{{}}.dta"
GKSW_XLSX = f"{CMS}/datastore/raw/lifecycle_income/orig/gksw2017.xlsx"
OUT = "output/dynamics"

PARAMS = [("cons", 3, "constant"), ("age", 0, "age"),
          ("age2", 1, "age$^2$"), ("age3", 2, "age$^3$")]

OURS = dict(color="#1f6fb4", marker="o", label="this fit (GKOS inversion)")
THEIRS = dict(color="#d1642f", marker="s", label="CMS (OLS on GKSW)")


def average_wage():
    """SSA average earnings by year, thousands of 2013 dollars."""
    d = pd.read_excel(GKSW_XLSX, "data_mean_2013d_impute")[["year", "ssa"]].dropna()
    return dict(zip(d.year.astype(int), d.ssa.astype(float)))


def cms_coefficients():
    """{(sex, cohort): [b_age, b_age2, b_age3, cons]}."""
    out = {}
    for sex in ("male", "female"):
        d = pd.read_stata(CMS_COEF.format(sex))
        for col in d.columns:
            out[(sex, int(col.split("_")[1]))] = d[col].to_numpy(float)
    return out


def to_cms_basis(coef_raw_t, cohort, awi):
    """Fitted g (log dollars, raw-t basis) -> CMS's [age, age^2, age^3, cons]."""
    ages = E.AGES
    t = (ages - 24) / 10.0
    g = sum(coef_raw_t[k] * t**k for k in range(4))
    rel = g - np.log(1000.0 * np.array([awi[cohort + a - 25] for a in ages]))
    X = np.column_stack([np.ones_like(ages, float), ages, ages**2.0, ages**3.0])
    b = np.linalg.lstsq(X, rel, rcond=None)[0]
    return np.array([b[1], b[2], b[3], b[0]])


def fit_all(sel, tables, awi):
    """{(sex, cohort): CMS-basis coefficients} for full-coverage cohorts only."""
    out = {}
    for sexcode, label in ((0, "female"), (1, "male")):
        tgt = E.load_targets(sexcode, sel)
        for c in sorted({c for c, _ in tgt}):
            ages = np.array(sorted(a for cc, a in tgt if cc == c))
            if ages.size != E.AGES.size:
                continue
            jj = ages - E.AGES[0]
            logymin = np.log([E.ymin(c + a - 25) for a in ages])
            target = np.array([tgt[(c, a)][0] for a in ages])
            coef, _ = E.fit_block(jj, logymin, target, tables, E.G_START)
            out[(label, c)] = to_cms_basis(E.uncentre(coef), c, awi)
    return out


def panel(ax, cohorts, ours, theirs, title):
    ax.plot(cohorts, ours, lw=1.3, ms=4, mfc="none", **OURS)
    ax.plot(cohorts, theirs, lw=1.3, ms=4, mfc="none", **THEIRS)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("cohort (year at age 25)", fontsize=9)
    ax.tick_params(labelsize=8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200_000)
    ap.add_argument("--sel", default="sel0", help="sel0 (default) or sel3 (CMS's sample)")
    ap.add_argument("--seed", type=int, default=20260821)
    ap.add_argument("--outdir", default=OUT, help="where to write the figures")
    args = ap.parse_args()

    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)
    awi = average_wage()
    cms = cms_coefficients()
    print(f"simulating {args.n:,} individuals ...")
    tables = E.suffix_tables(E.simulate_u(np.random.default_rng(args.seed), args.n))

    fits = {s: fit_all(s, tables, awi) for s in ("sel0", "sel3")}
    ours = fits[args.sel]
    cohorts = sorted({c for (_, c) in ours if ("male", c) in cms})
    print(f"full-coverage cohorts in both sources: {cohorts[0]}-{cohorts[-1]} "
          f"({len(cohorts)} cohorts)")

    for name, idx, _ in PARAMS:
        a = np.array([fits["sel0"][("male", c)][idx] for c in cohorts])
        b = np.array([fits["sel3"][("male", c)][idx] for c in cohorts])
        d = np.array([cms[("male", c)][idx] for c in cohorts])
        print(f"  men, {name:5s}: |sel0-sel3| {np.abs(a - b).mean():.3e}   "
              f"|sel0-CMS| {np.abs(a - d).mean():.3e}   "
              f"|sel3-CMS| {np.abs(b - d).mean():.3e}")

    for name, idx, pretty in PARAMS:
        fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.0), sharex=True)
        for ax, sex in zip(axes, ("male", "female")):
            panel(ax, cohorts,
                  [ours[(sex, c)][idx] for c in cohorts],
                  [cms[(sex, c)][idx] for c in cohorts],
                  f"{'Men' if sex == 'male' else 'Women'}")
        axes[1].legend(frameon=False, fontsize=8)
        fig.suptitle(f"coefficient on {pretty}   \u2014   targets: {args.sel}",
                     fontsize=10)
        fig.tight_layout()
        for ext in ("pdf", "png"):
            fig.savefig(f"{outdir}/g_vs_cms_{name}.{ext}", dpi=200)
        plt.close(fig)
    print(f"wrote {outdir}/g_vs_cms_{{cons,age,age2,age3}}.pdf/.png")


if __name__ == "__main__":
    main()
