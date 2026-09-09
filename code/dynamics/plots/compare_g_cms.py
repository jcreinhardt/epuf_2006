#!/usr/bin/env python
"""Compare an estimated g(t) against the CMS (JF 2025) lifecycle profiles, coefficient by
coefficient in CMS's own basis.

CMS build their profiles by OLS per cohort x sex of the published GKSW meanlog on raw age,
net of the SSA average wage (see gcohort_ols.py).  Their input is the same published moment
this project targets: the male_3/female_3 sheets of gksw2017.xlsx reproduce the sel3 files
to machine precision.  Two differences from a default run here:

  1. CMS use sel3 (lifetime earnings above a floor AND >= 15 years of work); the default
     targets are sel0.  Pass a fit made with `--sel sel3` for the apples-to-apples check --
     with --mode ols it reproduces CMS's coefficients to ~3e-7.
  2. The SMM modes invert the moment through the GKOS process, so their g sits below the
     observed moment by E[u | .]; the constant differs by that offset, the slopes compare.

The fitted g (raw-t basis, log 2013 dollars) is converted to CMS's basis exactly as CMS
run their regression: subtract log of the average wage in the cell's calendar year, then
project onto [1, age, age^2, age^3] over ages 25-55.  Only cohorts observed over the full
span are drawn, so every polynomial interpolates.  Needs replication_repos/CMS.

Run from the project root:
    python code/dynamics/plots/compare_g_cms.py [--fits output/dynamics/g_cohort_ols.csv]
Output: output/dynamics/plots/g_vs_cms<tag>.{pdf,png}
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "code/dynamics")          # run from the project root, per repo convention
import gcohort_model as E
import gcohort_ols as O

CMS_COEF = "replication_repos/CMS/datastore/derived/lifecycle_income/lifecycle_income_{}.dta"
OUT = "output/dynamics/plots"
PARAMS = [("cons", 3, "constant"), ("age", 0, "age"), ("age2", 1, "age$^2$"), ("age3", 2, "age$^3$")]
OURS = dict(color="#1f6fb4", marker="o", label="this fit")
THEIRS = dict(color="#d1642f", marker="s", label="CMS (OLS on GKSW sel3)")


def cms_coefficients():
    """{(sex, cohort): [b_age, b_age2, b_age3, cons]} -- CMS's own column order."""
    out = {}
    for sex in ("male", "female"):
        d = pd.read_stata(CMS_COEF.format(sex))
        for col in d.columns:
            out[(sex, int(col.split("_")[1]))] = d[col].to_numpy(float)
    return out


def to_cms_basis(coef_raw, cohort, awi):
    """Fitted g (raw-t basis) -> CMS's [age, age^2, age^3, cons] over ages 25-55."""
    g = E.basis(E.T, 3) @ E.pad(coef_raw)
    rel = g - np.log(1000.0 * np.array([awi[cohort + a - 25] for a in E.AGES]))
    b = O.cms_basis(rel, E.AGES)
    return np.array([b[1], b[2], b[3], b[0]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits", default="output/dynamics/g_cohort_ols.csv")
    ap.add_argument("--outdir", default=OUT)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    awi, cms = O.average_wage(), cms_coefficients()
    fits = pd.read_csv(args.fits)
    fits = fits[fits["n_ages"] == E.AGES.size]
    # --mode ols carries CMS's own regression (cms_b*: cubic in raw age, whatever --degree);
    # an SMM fit is projected onto that basis instead.
    if "cms_b0" in fits:
        ours = {(r.sex, int(r.cohort)): np.array([r.cms_b1, r.cms_b2, r.cms_b3, r.cms_b0])
                for r in fits.itertuples()}
    else:
        ours = {(r.sex, int(r.cohort)): to_cms_basis([r.g0_raw, r.g1_raw, r.g2_raw, r.g3_raw],
                                                      int(r.cohort), awi)
                for r in fits.itertuples()}
    cohorts = sorted({c for (s, c) in ours if (s, c) in cms and s == "male"})
    print(f"{args.fits}: full-span cohorts in both sources {cohorts[0]}-{cohorts[-1]} "
          f"({len(cohorts)} cohorts)")

    fig, axes = plt.subplots(4, 2, figsize=(8.0, 9.5), sharex=True)
    for i, (name, idx, pretty) in enumerate(PARAMS):
        for j, sex in enumerate(("male", "female")):
            a = np.array([ours[(sex, c)][idx] for c in cohorts])
            b = np.array([cms[(sex, c)][idx] for c in cohorts])
            print(f"  {sex:6s} {name:5s}: mean |this - CMS| {np.abs(a - b).mean():.3e}")
            ax = axes[i, j]
            ax.plot(cohorts, a, lw=1.3, ms=4, mfc="none", **OURS)
            ax.plot(cohorts, b, lw=1.3, ms=4, mfc="none", **THEIRS)
            if i == 0:
                ax.set_title("Men" if sex == "male" else "Women", fontsize=10)
            if j == 0:
                ax.set_ylabel(f"coefficient on {pretty}", fontsize=9)
            if i == 3:
                ax.set_xlabel("cohort (year at age 25)", fontsize=9)
            ax.tick_params(labelsize=8)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
    axes[0, 1].legend(frameon=False, fontsize=8)
    fig.suptitle(f"g(t) in CMS's basis: {os.path.basename(args.fits)} vs CMS", fontsize=10)
    fig.tight_layout()
    path = os.path.join(args.outdir, f"g_vs_cms{args.tag}")
    for ext in ("pdf", "png"):
        fig.savefig(f"{path}.{ext}", dpi=200)
    print(f"wrote {path}.pdf/.png")


if __name__ == "__main__":
    main()
