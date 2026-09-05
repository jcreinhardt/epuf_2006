# 2026-08-24 — g(t) re-estimated as a cohort x sex cubic, vs. CMS

Frozen snapshot of the scripts as they stood on 2026-08-24, in `code/`, plus the figures
they produced, in `figures/`.  Run from the **project root**:

```bash
python presentation/2026-08-24/code/estimate_g_cohort.py --sel sel3
python presentation/2026-08-24/code/compare_g_cms.py --sel sel3 --outdir presentation/2026-08-24/figures
python presentation/2026-08-24/code/plot_aggregate_taxable_ratio.py
```

`plot_aggregate_taxable_ratio.py` arrived separately (it is not part of the g(t)-vs-CMS
snapshot): it draws EPUF, the employment-panel-weighted model and e9f as ratios to ASS
over 1951-2006, and reads `output/cross_sections/agg_taxable_emp_weighted.csv`, so run
`code/cross_sections/agg_tax_emp_weighted.py` first. Unlike the two scripts above it is
NOT frozen -- it imports the live `plots/plot_agg_tax_total.py`.

THE SNAPSHOT IS DELIBERATELY FROZEN AND NO LONGER MATCHES THE LIVE PIPELINE. Since this
was presented, `code/dynamics/` was reorganised: the estimator here became the library
`gcohort_model.py` behind the entry point `estimate_g_cohort.py --mode smm-mean`, and
`compare_g_cms.py` moved to `code/dynamics/plots/`. The live equivalent of this deck's
fit is

```bash
python code/dynamics/estimate_g_cohort.py --mode smm-mean --sel sel3
```

which is not identical: it applies optimal weighting across the 31 age-moments where the
snapshot ran plain least squares. Re-run the snapshot to reproduce the figures as shown;
use the live pipeline for anything new.

Needs the `socsec_mac` conda env, plus `raw_data/guv_quantiles/` and
`replication_repos/CMS/` (both gitignored; symlink them into a fresh worktree).

## What is estimated

Every parameter of the GKOS (2021) benchmark process is held fixed at the published
estimate (Table IV spec 6 + Table D.III).  Only the four coefficients of a cubic
lifecycle profile are searched over, separately per (sex, cohort):

    g(t) = g0 + g1*t + g2*t^2 + g3*t^3,     t = (age - 24)/10

The target is `meanlog` from `cohortage_rwageinc_sel3_25_55_sex{0,1}.txt` — mean log
real earnings by cohort x age, conditional on clearing a quarter of full-time work
at half the minimum wage.  Only the 27 cohorts observed over the **full 25–55 span**
(1957–1983, indexed by year at age 25) are used, so every cubic interpolates.

Because g enters the level before the censoring, `log Y = g(t) + u` and the sample
rule becomes `u >= log(Ymin) - g(t)`.  One simulated panel (200k) is therefore
enough: sort `u` within each age, take suffix means, and every objective evaluation
is a binary search.  Self-recovery from model-generated targets is exact to 1e-14;
swapping the simulation seed moves g(t) by 0.0017 log points.

## Comparison with CMS

CMS ("Social Security and Trends in Wealth Inequality") estimate the same object by
OLS per cohort x sex in
`replication_repos/CMS/source/derived/lifecycle_income/create_lifecycle_income_parameters.do`.
Their input is *this same published moment*: the `male_3`/`female_3` sheets of
`gksw2017.xlsx` reproduce the `sel3` files to machine precision (verified).  Both
sides here therefore target sel3 — an apples-to-apples estimator comparison.

To compare, the fitted g (log 2013 dollars) is put on the CMS basis: subtract
`log(1000 * ssa_average_earnings)` for the cell's calendar year, then project onto
`[1, age, age^2, age^3]` — exactly the regression CMS run on their own input.

## Caveats

- GKOS estimate on **men only**; both sexes here use the male parameter vector
  (sex0 = female, sex1 = male in the source do-file), so the female cubic absorbs
  every sex difference in dispersion and nonemployment risk.  Descriptive, not structural.
- The Ymin censoring is nearly **non-binding** among positive earners (max censored
  share ~0.001): the nonemployment shock puts the low-earnings mass at exactly zero
  rather than just above Ymin, so dm/dg ~ 1 and the fit is effectively least squares
  on the cubic basis.  Estimates are insensitive to the Ymin construction.
- Untargeted check: the model's within-cell sd of log earnings is 0.081 (men) /
  0.085 (women) below the sel3 data — noticeably closer than the 0.17 gap against
  sel0, since sel3 trims the low earners the model does not generate.  Residual
  under-dispersion points at sigma_alpha and the nonemployment logit, not at g.
- `g_cohort_cubic_sel3.csv` holds the fitted coefficients: `g0..g3` on
  (t - 1.6), `g0_raw..g3_raw` on raw t, plus per-block fit and diagnostic columns.
