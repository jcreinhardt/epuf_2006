# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Data-engineering + replication project around SSA earnings data. Two complementary sources
are loaded into one shared DuckDB database and used to replicate figures/tables from Compson
(2012), RS Note 2012-01:

- **EPUF 2006** — 1% individual **microdata** (`demographic`, `annual` tables).
- **Annual Statistical Supplement, Table 4.B1** — published annual **aggregates** (`supplement_4b1`).

`README.md` is the authoritative reference for data semantics, table schemas, and the
measurement caveats (capping, random-rounding, sparse panels, EPUF-vs-Supplement differences).
Read it before doing any analysis — the caveats materially change what queries mean.

## Environment

- Python code needs the conda env **`socsec_mac`** (`conda activate socsec_mac`); the base
  `python3` lacks the deps. Key packages: `beautifulsoup4`, `lxml`, `pandas`, `matplotlib`.
- **DuckDB is used via its CLI (`duckdb`), not a Python module.** The Python scripts
  deliberately `subprocess` out to the `duckdb` binary so they carry no `python-duckdb`
  dependency — follow this pattern rather than importing `duckdb` in Python.

## Common commands

Run everything **from the project root** (`epuf_2006/`); all paths in the code are relative to it.

Build the database (two steps, idempotent via `CREATE OR REPLACE`, order-independent):

```bash
duckdb processed_data/ssa.duckdb < code/data_import/build_epuf_duckdb.sql   # ~7 s → demographic, annual
python code/data_import/extract_table_4B1.py                                # → supplement_4b1 (+ CSV)
```

Run SSA-figure replication:

```bash
duckdb processed_data/ssa.duckdb < code/ssa_replication/replicate_note_table2.sql       # Table 2 of RS Note 2012-01
duckdb processed_data/ssa.duckdb ".read code/ssa_replication/example_panel_to_age60.sql"
python code/ssa_replication/plots/plot_chart4_replication.py                            # → output/ssa_replication/chart4_replication.pdf
```

Run cross-sectional distribution fits (per year × sex × single-year-age earnings
distributions). **Two stages**: one joint optimization, then extrapolation off the observed
span. Run in order — the second reads the first's CSV:

**One entry point**, `estimate_cross_sections.py`, dispatches on `--mode`:

- `--mode mle` — smoothed, aggregate-constrained censored MLE on EPUF alone. Implementation
  `crosssec_mle.py`. Canonical; feeds `extrapolate_params.py` and the aggregate validation.
- `--mode mle-gmm` — convex combination `(1−λ)·negll/n + λ·r'Wr` of that likelihood with an
  iterated GMM criterion on the published GKSW (guv) sel0 targets. Implementation
  `crosssec_gmm.py`. **Deliberately drops the aggregate-mean constraint** — read that module's
  docstring before feeding its surface to EPUF-denominated aggregate validation.
- `--mode both` — run both.

```bash
# stage 1 — joint smoothed-constrained MLE → cross_section_params_smoothed.csv
#           (also writes the raw stage-0 fits to cross_section_params.csv, + both heatmap sets)
python code/cross_sections/estimate_cross_sections.py --mode mle [--jobs N] [--rho R] [--rho-steps S]
# stage 1 alt — MLE+GMM against the GKSW targets → cross_section_params_guvgmm_smoothed.csv
python code/cross_sections/estimate_cross_sections.py --mode mle-gmm [--lam L] [--gmm-iters K] [--no-smooth]
# stage 2 — anchor + wage-index extrapolation off the data edges → cross_section_params_extrapolated.csv
python code/cross_sections/extrapolate_params.py

python code/cross_sections/plots/plot_agg_tax_total.py   # END-TO-END validation: model vs ASS+TR, capped AND uncapped
#   two optional overlays on that figure:
#     --gkos CSV   the GKOS/Guvenen cohort-model aggregate (see the dynamics block below)
#     --e9f  PATH  the prior pipeline's agg_taxable_earnings_extrap.parquet (real 2013$)
python code/cross_sections/plots/plot_param.py [men|women|both] [csv] [suffix]   # cohort×age parameter heatmaps
python code/cross_sections/plots/plot_guv_quantile_validation.py   # DATA-vs-DATA: raw EPUF quantiles vs GKSW sel0, complete cohorts
python code/cross_sections/plots/plot_guv_gap_signature.py         # DATA-vs-DATA: the EPUF/GKSW log gap by quantile × year and × age
python code/cross_sections/plots/plot_cross_section.py [age] [cohort] [sex] [--year Y] [--refit] [--overlay]   # one cell: histogram + fitted density
```

### Lifecycle profile g(t) — `code/dynamics/`

**One entry point**, `estimate_g_cohort.py`, three estimators of the same cohort × sex polynomial
`g(t) = g0 + g1·t + g2·t²`, `t = (age−24)/10` (GKOS's own quadratic; `--degree 3` adds a cubic
term, which fits 25–55 ~0.006 better in rmse and diverges outside it — men's mean earnings at
70 reach $200k for cohort 1970 — so the **whole pipeline is quadratic by default**), against
the published GKSW cohort × age files, with every other GKOS parameter fixed (`gcohort_model.py` holds the process, its
simulation, the suffix tables and the moment map; it draws nothing):

```bash
python code/dynamics/estimate_g_cohort.py --mode ols             # gcohort_ols.py — CMS's per-block OLS
python code/dynamics/estimate_g_cohort.py --mode smm-mean        # gcohort_smm.py — SMM on meanlog alone
python code/dynamics/estimate_g_cohort.py --mode smm-quantiles   # gcohort_smm.py — meanlog + p10…p98
python code/dynamics/estimate_g_cohort.py --mode smm-p50         # gcohort_epuf.py — GKSW **and EPUF** medians
python code/dynamics/relevel_g_cohort.py --fits output/dynamics/g_cohort_smm_p50.csv   # → *_relevelled.csv
#   --level epuf (default) takes the level from EPUF's own mean log; --level gksw is the old one
python code/dynamics/plots/plot_p50_fit.py [--cohort 1970]       # both sources, model, model+δ
python code/dynamics/plots/plot_shape_gap.py                     # why the level misses: log-earnings shape
python code/dynamics/plots/plot_level_shape_decomp.py            # model/EPUF per worker: level x shape
python code/dynamics/extrapolate_g_cohort.py --fits output/dynamics/g_cohort_smm_mean.csv   # → *_extrapolated.csv
python code/dynamics/plots/plot_g_cohort.py output/dynamics/g_cohort_*.csv     # coefficient paths, any CSVs overlaid
python code/dynamics/plots/compare_g_cms.py [--fits CSV]                       # vs CMS's lifecycle_income_*.dta
python code/dynamics/plots/plot_agg_tax_dynamics.py [--profiles CSV] [--ages 20 70]
#   --export CSV writes the model aggregate for other figures to overlay;
#   --renorm-comp is REQUIRED when exporting for plot_agg_tax_total.py (see below)
python code/dynamics/plots/plot_cohort_profile.py [--cohort 1970]   # one cohort by age: model vs GKSW vs EPUF, mean log + mean level
python code/dynamics/plots/plot_cms_selection.py    # CMS's process as they coded it: selection wedge
python code/dynamics/plots/plot_gkos_ordinal.py     # ordinal-transform invariance to g(t)
```

Estimation writes CSVs to `output/dynamics/`; every figure goes to `output/dynamics/plots/`.
**The extrapolation CSV is load-bearing**: `plot_agg_tax_dynamics.py` reads it (default
`g_cohort_smm_quantiles_extrapolated.csv`) rather than re-running the rule, so the
`--anchor/--ref-age/--drift` choices made there are the ones the aggregate is validated with.
Its default cohort range 1892–2105 is what a 1937–2100 × ages 20–70 window needs; the plot
refuses a narrower file.

### `--mode smm-p50`: the only profile disciplined outside ages 25–55

**The design in one place, because the pieces are easy to mis-remember.** Per (sex, cohort) block,
cohorts 1957–1983, 54 blocks:

| stage | free parameters | targets |
|---|---|---|
| SMM (`gcohort_epuf.py`) | `g0, g1, g2` + `h_young, h_old` + `δ` — **six** | GKSW **p50** of log earnings, ages 25–55, vs the model median; EPUF **p50**, ages 20–70, vs the model median **+ δ** |
| re-level (`relevel_g_cohort.py`) | `g0` alone | EPUF's **mean log of capped earnings**, ages 25–55, with the model clipped at the same top code |

**No mean appears anywhere in the SMM objective, and no GKSW mean is used at all** on the default
path — `--level gksw` was the old one. Both SMM blocks are medians against medians; that is the
whole point, since a mean on one side and a median on the other forces δ to track a target that
moves at −0.043/decade (see `epuf_targets.py`). Shorthand: **medians set the shape, EPUF's capped
mean log sets the level.** The two stages commute cleanly because `g0` is a pure intercept and
everything else is shape.

**Extrapolation happens at two separate layers, and only the second is about unobserved cohorts.**

1. *Inside* 1957–1983, where EPUF runs out of ages. A block needs `MIN_YOUNG = 3` observed ages
   below 25 and `MIN_OLD = 4` above 55 to carry a hinge **column at all**. Every fitted cohort has
   all of 20–24, so `h_young` is always estimated; above 55 the coverage thins (19 cohorts at 56
   down to 5 at 70, none for cohorts 1976+), so **11 of 27 blocks per sex are fitted without the
   `h_old` column** and then given their sex's 16-cohort mean (−0.083 men, −0.375 women) by
   `fill_hinges`. The column is absent from the design rather than set to zero, so their fitted `g`
   is untouched.
2. *Outside* 1957–1983, out to cohorts 1892–2105 (`extrapolate_g_cohort.py`). Every shape
   parameter — `g1`, `g2`, `h_young`, `h_old`, and `δ` where present — is **frozen at the mean of
   the 5 edge cohorts** (1957–61 backward, 1979–83 forward); only `g0` moves, rigid-shifted
   one-for-one with the real average wage index read at age 25. Cohorts 1892 and 1952 in the
   output carry identical shape and differ only in `g0`, which is the rule made visible.

That one-for-one drift is the weakest assumption in the chain and it is a modelling choice, not a
finding: the in-sample regression of `g0` on the wage index gives **−0.36 for men** (see below).

Every GKOS/GKSW tabulation stops at age 55 (verified across the whole replication package), so
the other modes extrapolate blind. EPUF covers 20–70 for the same cohorts. This mode targets the
**median of log earnings in both sources** — the one statistic each measures well, since EPUF's
mean is destroyed by the top code while its median sits far below the cap, and GKSW's data carry
no cap. Three pieces, `epuf_targets.py` + `gcohort_epuf.py`:

- **δ, the wedge intercept**, one free parameter per (sex, cohort). EPUF is all covered earnings,
  GKSW is commerce-and-industry W-2 wages, so the same cell has a different median: measured
  −0.063 (men), +0.023 (women). Identified on the 31-age overlap. Carrying one constant out to 70
  is licensed by the wedge being flat in age (slope −0.004/−0.007 per decade) and stable across
  cohorts (sd 0.008/0.014).
- **Hinges** in `(t₂₅−t)₊` and `(t−t₅₅)₊`, identically zero inside 25–55 (`gcohort_model.design`),
  so the published-moment fit is untouched and they are identified purely by EPUF outside it.
  Estimated: h_young −1.07 (men) / −0.67 (women), h_old −0.08 / −0.38. Young coverage is complete;
  the old side runs 19 cohorts at 56 down to 5 at 70, and cohorts 1976+ have none, so those blocks
  are fitted without the column and filled from their sex's mean.
- **Extrapolation** carries hinges and δ as shape, frozen at the edge like `g1`/`g2`.

**MATCH LIKE TO LIKE — a GKSW mean against an EPUF median does not work.** The model would have to
supply the mean-median difference from its own u, and it supplies it backwards: its mean-minus-
median of log earnings is **+0.03 where the data's is −0.10 to −0.20**, a 0.12–0.23 gap that
**trends at −0.039/decade**. A constant δ cannot absorb a trending term, so that trend would land
in the out-of-span shape — the thing being estimated.

**The model cannot match the mean and the median at once, and which you target decides the
aggregate.** Measured over 25–55, model minus GKSW data:

| fit | p50 gap | meanlog gap | sd log gap |
|---|---|---|---|
| `smm-p50` | −0.001 | **+0.171** | −0.004 |
| `smm-quantiles` | −0.150 | +0.022 | −0.004 |

So a level fitted to the median inherits the whole skewness error, worth about exp(0.17) on
E[e^g]. `relevel_g_cohort.py` is the resolution: **median for shape, mean for level**. It moves
only `g0`, per block, to a fixed point against one published mean per block, leaving curvature
and hinges exactly as fitted. `delta` is dropped either way, so the aggregate takes
`--universe gksw`.

**WHICH POPULATION the mean comes from is worth more than the choice of functional, and it is
`--level`.** The EPUF↔GKSW wedge is statistic-dependent — −0.063 in the median but **−0.164 in
the mean**, for men — so a level read off GKSW's mean (`--level gksw`, shifts −0.170/−0.183) puts
the *covered* population 0.19 log points high, and the aggregate benchmark is ASS covered
earnings over all covered workers, which is EPUF's universe. `--level epuf`, now the **default**,
targets EPUF's own mean log instead (shifts −0.348/−0.389) with the **model clipped at the same
top code**, so the moment is mean log min(Y, C) on both sides and EPUF's cap cancels rather than
biasing the target down. Only `g0` moves; the shape still comes entirely from the medians.

Aggregate, `--renorm-comp`, ages 20–70, in sample 1951–2006:

| profile | taxable | uncapped |
|---|---|---|
| `smm-quantiles` | 1.091 | 1.282 |
| `smm-mean` | 1.103 | 1.268 |
| `smm-p50`, `--universe epuf` | 1.173 | 1.380 |
| `smm-p50` re-levelled, `--level gksw` | 1.070 | 1.212 |
| **`smm-p50` re-levelled, `--level epuf`** | **0.943** | **1.022** |

EPUF itself is 0.948 of the published total, so the last row is **model/EPUF = 0.995**: the model
now reproduces the microdata, and the residual 5% is EPUF's own coverage of the published series,
not model error. Forward it is 1.035 (2007–22) and 1.059 (2023–2100), against 1.21–1.24 before.
**The uncapped 1.022 is the one to be impressed by** — the uncapped mean is targeted nowhere, so
matching it is the shape passing a test it was not fitted to. Set against that, the level is now
calibrated to EPUF, so the *taxable* comparison to ASS is no longer independent of the data.

**Where the error was, split exactly** (`plots/plot_level_shape_decomp.py`: every cell weighted by
EPUF's OWN worker count, so composition and worker totals cancel; capped on both sides, so the
top code cancels too). Taxable earnings per covered worker, 1951–2006, ages 20–70:

| level | model / EPUF | = level | × shape |
|---|---|---|---|
| `--level gksw` | 1.060 | 1.195 | 0.887 |
| `--level epuf` | 0.915 | 1.031 | 0.887 |

Shape is identical because re-levelling moves only `g0` — that is the check that the split is
real. **The old total looked better than either of its parts**: a +20% population-wedge level
error was cancelling against an −11% capped-shape shortfall. Uncapped the two do not cancel, and
1.212 ÷ 1.022 = 1.186 is the same wedge showing up undisguised.

**The overshoot was NOT an age-extrapolation failure**, and that is measured rather than assumed:
the +0.171 mean-log gap above is computed on ages 25–55 only, and alone implies ≈1.19× on levels
before any extrapolation happens. (Do NOT try to confirm this by re-running the aggregate on
`--ages 25 55`: `--renorm-comp` then assumes the under-25s and over-55s earn like the 25–55
average, which they do not, and the ratio rises to 1.167/1.353 from the renormalisation alone.
The rank-mapping below is the clean version of the same check.) What remains is the model's log-earnings **shape**, which no choice of g can fix.

**The shape error is in the UPPER HALF, and it is not an extreme-tail problem**
(`plots/plot_shape_gap.py`). Netting the level out — the re-levelled fit, so mean log matches —
leaves sd log matching to 0.005, but that agreement is two errors cancelling. Ages 25–55, log
points, men:

| spread | data | model |
|---|---|---|
| p50 − p10 | 1.24 | 1.02 |
| p90 − p50 | 0.70 | 1.13 |
| p98 − p90 (age 25 → 55) | 0.26 → 0.94 | 0.58 → 0.86 |

The data's lower half is **flat in age** (1.27 → 1.32) while the model's fans out (0.79 → 1.31);
the model's upper half sits ~0.4 above the data's at every age. So the process disperses roughly
symmetrically in logs where the data disperse one-sidedly, and the mismatch is between the median
and p90 — the very top segment p98 − p90 is if anything too NARROW at older ages. That is why
model skew log is +1.09 (men) / +0.83 (women) above the data's, and mean-minus-median is +0.03
against the data's −0.14.

Mapping the model's own draws rank-preservingly onto the published percentiles isolates the price
of that shape: **E[Y] model / data-shaped = 1.076 (men), 1.099 (women)** on ages 25–55 at a
matched mean log. Everything above p75 contributes +160% of the excess and everything below it
−60%. It is also why capping helps so much (1.212 uncapped → 1.070 taxable): the cap removes
exactly the part that is wrong. The remaining gap to 1.212 is the same mechanism running past 55,
where the fan keeps widening unopposed — E[e^u]/median goes 1.30 at age 25, 1.81 at 55, 2.42 at
70 — plus the GKSW-vs-EPUF universe wedge. Fixing it means changing the process (the HIP fan
σ_β·t is normal and symmetric, so it cannot produce a flat lower half), not g.

**`--drift fitted` is available and is NOT recommended.** It replaces the assumption that `g0`
tracks the wage index one-for-one with the in-sample slope (men −0.10, clipped to 0). It fixes the
forward drift (2023–2100 falls 1.36 → 0.99) but blows up backward: pre-1951 goes to 1.57 capped
and **2.83 uncapped**, because a flat real male profile extrapolated back to 1937 sits far above
the actual wage level. The index rule is the better of the two.

**Putting the GKOS aggregate on the cross-section figure.** The two models reach aggregate
taxable earnings by routes that share no parameters — the per-cell dPlN/mixture surface vs the
GKOS lifecycle process with only g(t) free — so overlaying them is a real check. Four steps:

```bash
python code/dynamics/estimate_g_cohort.py --mode smm-p50 --jobs 8
python code/dynamics/relevel_g_cohort.py --fits output/dynamics/g_cohort_smm_p50.csv
python code/dynamics/extrapolate_g_cohort.py \
    --fits output/dynamics/g_cohort_smm_p50_relevelled.csv
python code/dynamics/plots/plot_agg_tax_dynamics.py \
    --profiles output/dynamics/g_cohort_smm_p50_relevelled_extrapolated.csv \
    --universe gksw --renorm-comp --export output/dynamics/agg_taxable_gkos_p50_relev.csv
python code/cross_sections/plots/plot_agg_tax_total.py \
    --gkos output/dynamics/agg_taxable_gkos_p50_relev.csv
```

**The headline figure is that last command's ratio pair** — every series divided by the ASS+TR
benchmark, with the benchmark itself drawn as the labelled line at 1:

  * `output/cross_sections/plots/aggregate_taxable_ratio_insample.png` — 1951–2006, EPUF +
    parametric cross-sections + GKOS cohort model, the only window where all three exist.
  * `output/cross_sections/plots/aggregate_taxable_ratio_full.png` — 1937–2100, the two models
    (EPUF has no years outside 1951–2006).

What it shows: the two models agree to a few points from 1980 on and settle at 1.02 (parametric)
and 1.07 (GKOS) on the TR projection. Before 1980 the GKOS line runs 0.87–0.91 while EPUF and the
parametric surface sit at 0.96–0.98, and that gap is the **backward cohort extrapolation**, not
the fit: those years are carried by cohorts outside 1957–1983 whose shape is frozen at the
1957–61 edge and whose level rides the wage index one for one.

**`--renorm-comp` is not optional here, and the loader enforces it.** The dynamics model covers
ages 20–70 only; its own figure compares to the undivided published total and reports the
resulting coverage shortfall explicitly. The cross-section figure's other series are
per-covered-worker over ALL ages, so dropping the un-renormalised series onto it would show a
~4% age-coverage gap as if it were model error. With the composition renormalised inside the
window, both are "mean taxable earnings per covered worker × the published worker total" — at
the cost of assuming workers outside 20–70 earn like the 20–70 average.

**The HIP slope is σ_β = 0.196 per DECADE of age, and getting it wrong is invisible in the
mean-only fit.** Table IV's 0.196 is on the same `t = (age−24)/10` as g(t) (Table D.III's note;
the paper's own gloss "σ_β ≃ 2%" per year). CMS's `Simulation.m` uses `SigBeta = .196/10` on
that t, and this section copied it until 2026-09-05. E[u] does not depend on σ_β and the Ymin
cut is non-binding, so `--mode smm-mean` and `--mode ols` are unchanged by the fix. What moves:

- the LEVEL E[e^u]: ×1.12 at age 40, ×1.36 at 55, ×1.79 at 70 — which is what the aggregate
  validation runs on;
- the dispersion (sd log at 55: 0.70 → 1.05), which brings the untargeted sdlog to within 0.013
  of the sel0 data on average — and, through it, the model's log PERCENTILES relative to its
  mean. So `--mode smm-quantiles` DOES move: its g0 rises by 0.14 (men) / 0.15 (women), and
  where it used to sit 0.14 below the mean-only fit it now agrees with it to ±0.05.

The aggregate validation, GKOS/benchmark with `--renorm-comp`, quadratic g (all four rows):

| in sample 1951–2006 | taxable | uncapped |
|---|---|---|
| old pipeline (σ_β/10, old quantile fit) | 0.996 [0.953–1.045] | 0.990 [0.876–1.071] |
| old quantile fit, σ_β fixed | 1.019 [0.952–1.091] | 1.145 [1.028–1.238] |
| **refit, `smm-quantiles`** | **1.091 [0.995–1.194]** | **1.282 [1.174–1.366]** |
| refit, `smm-mean` (σ_β-invariant) | 1.103 [0.991–1.226] | 1.268 [1.199–1.329] |

Over 2007–22 the refit is 1.21–1.24 taxable, on the TR projection 1.23–1.27. **So the old
headline — 0.992, "agrees with the parametric surface to under a point" — was two errors
cancelling**: σ_β/10 depressed the level by ~10–15%, and the too-narrow model pulled the
quantile-weighted g0 down by ~0.14. Fixed, the GKOS process with only g(t) free overshoots
covered earnings by ~10% capped and ~30% uncapped. Two known sources, both with the right
sign: g is fitted to the GKSW files, whose quantiles sit ABOVE EPUF's by a bottom-heavy,
age-increasing sample-composition wedge (see the Gotchas), so a g reproducing GKSW's mean log
earnings puts the covered population's mean too high; and the fixed GKOS dispersion at 55 (sd
log 1.05) exceeds the data's, and E[e^u] is exponential in it (exp(Δσ²/2) ≈ 1.10). Do not
"fix" this by retuning σ_β; the cross-section figure's `--gkos` overlay now shows the gap.

`plot_cms_selection.py` deliberately keeps CMS's `.196/10` and their `corr = 0.786` (Table IV:
0.768): its subject is CMS's process as run, and it says so.

**Three things about the modes that are easy to get wrong:**

- **`--mode ols` is on a different LEVEL.** It regresses the observed moment directly, so its `g`
  absorbs the `E[u | u ≥ log(Ymin) − g]` term the SMM modes strip out (~0.38 log points). It
  reports `eu_offset` per block, and `g0(ols) = g0(smm-mean) + eu_offset` holds exactly. The
  offset is a **fixed point** — `E[u|·]` must be read at the *inverted* g, and projected onto the
  polynomial basis and reduced to its constant term. Evaluating it one-shot at the OLS g, or as a plain
  mean over ages, is off by 0.08–0.18 log points and by different amounts for men and women.
  Slopes need no correction and are the useful comparison. On `--sel sel3` this mode reproduces
  CMS's published coefficients to ~4e-6 (`compare_g_cms.py` prints it).
- **The shape moments cannot identify g, and that is measured, not assumed.** `dm/dg` is ~1.000
  for meanlog and every log percentile, and ~0.00–0.02 for sdlog/skewlog/kurtlog, because at the
  GKOS parameters the Ymin truncation is nearly non-binding among positive earners (max censored
  share ~0.001 — the nonemployment shock puts the low mass at exactly zero, not just above Ymin).
  So there is no `--mode` for them. `gcohort_smm.SETS` still exposes `all`/`quantiles` for the
  **specification test** they do support, which rejects the fixed GKOS calibration in 100% of
  blocks.
- **Weight-matrix noise dominates the reported standard errors.** Across bootstrap redraws of Ŝ
  the sd of `ĝ0` is 6–9× the asymptotic SE. The `se_*` columns understate real uncertainty by
  that factor; `wsd_*` records the measured noise; `--wnoise K` re-measures it on any run.
  Raising `--reps` above 1000 is the lever, at linear cost.

**The extrapolation rule assumes g0 tracks the average wage one-for-one, and men's does not.**
`extrapolate_g_cohort.py` prints the in-sample regression of g0 on the wage index every run:
with the quadratic `smm-quantiles` fit men's slope is **−0.47** (corr −0.72; g0 falls 0.15 log
points from cohort 1957 to 1983 while the real average wage rises 0.32; `smm-mean`: −0.14, flat),
women's +1.3. The forward splice therefore kinks the male level path (in-sample +1.1%/yr at the
edge, extrapolated +1.7%/yr). That is a
modelling choice made so the aggregate tracks the published wage path; the data do not imply it.

`--mode ols` and `compare_g_cms.py` need `replication_repos/CMS` for the SSA average-wage
series; the SMM modes do not. The deflator and the sel0 screen come from
`cross_sections/guv_targets.py` (ONE definition); the section's own single nominal↔2013$
conversion is `extrapolate_g_cohort.price_index` (GKSW's PCE vintage where it exists, chained on
FRED outside it, then the TR wage deflator), which the plots import.

Two cohort×age heatmap scripts live with the report they were written for
(`presentation/2026-08-24/`) rather than under `code/` + `output/`, so that folder is
self-contained. They are still run **from the project root** and write into
`presentation/2026-08-24/figures/`:

```bash
python presentation/2026-08-24/code/plot_censored_share.py [csv]   # share of a cell censored at the cap
python presentation/2026-08-24/code/plot_guv_gap_heatmaps.py [--params CSV] [--tag T] [--reuse] [--units absolute|logpoints|both]
```

`plot_guv_gap_heatmaps.py` compares the fitted surface against the GKSW/GKOS 2022
cohort×age file per cell (the per-cell version of `plot_guv_comparison.py`'s averaged
lines), one figure per functional with men and women side by side, in **both** absolute
units and log points. The log-point set covers the level functionals only — sd/skew/kurt
of logs are already scale-free, so no duplicate is written.

The per-figure scripts read the CSVs, so they are seconds, not minutes. `plot_cross_section.py`
defaults to the pipeline parameters; `--refit` fits the cell standalone and `--overlay` draws
both, which is how to see what smoothing changed in one cell.

**Stage 1** (`--mode mle`, implemented in `crosssec_mle.py`) implements the `smoothed-constrained-mle` skill:
per `(year, sex, single-year age)` cell (~6.4k cells, ≥1000 obs each), fit the censored
distribution while **simultaneously** (a) borrowing strength across neighbouring ages and
(b) pinning each year's uncapped aggregate mean to the published ASS benchmark. The two must
be solved *together* — smoothing after constraining breaks the constraint (measured: ~7% off),
and constraining after smoothing breaks the smoothness. Per year:

- **stage 0** multi-start MLE per cell, keep top-K=3 optima **deduped in g-space**, not θ-space.
- **Ω, ρ frozen once, globally** from the stage-0 fits: `Ω_j = 1/MAD[(Dg)_j]²` per sex, and
  `ρ₀` scaled by `SMOOTH_FRAC` off the fit magnitude. ρ is in per-observation units,
  multiplied by the year's `ntot` inside the solve since the fitters minimize a *sum*.
- **stage 1** Viterbi basin selection along age (exact over consecutive triples, K² states).
- **stage 2** ρ-continuation (graduated non-convexity), Gauss–Seidel passes alternating direction.
- **stage 3** η search with the smoothing **inside** the loop, by a bisection that tracks the
  *closest achieved* aggregate (S(η) is only piecewise continuous — cells change basin under the
  pull — so `brentq`, which assumes continuity, converges onto a discontinuity instead of a root).
- **stage 4** re-check basins at the converged η; re-seed and redo 2–3 only if a cell moved. The
  candidate refits here are diagnostics — adopting them directly would overwrite the smoothed,
  constrained solution with unsmoothed fits.

The penalty acts on **functionals g(θ)**, never raw parameters: raw-parameter distance is
meaningless across a regime flip (the women's mixture components swap roles), so a raw penalty
looks like it works while the flips go untouched. Both sexes share one 6-slot layout —
`[E logY, sd logY, skew logY, logit S(cap), lower tail, upper tail]` — so a single ρ means the
same thing for both. **Every slot is closed form** (Normal-Laplace cumulants; normal-mixture
central moments; mean excess at the cap): g is evaluated inside every objective evaluation, and
quantile-based functionals needing CDF bisection cost ~30× more.

The roughness operator is a **robust (Huber) second difference** along age. Basin-hopping is
already handled by g + Viterbi, so the operator's job is to protect *genuine* regime switches
(retirement, young-age entry): a quadratic ‖Dg‖² charges a true step quadratically and smears it,
while the Huber loss crushes sawtooth but lets a sparse, isolated jump through at ~linear cost.
It is location-free — no cutoff to hard-code, and the year-varying retirement age is handled
automatically.

The fits live in `code/cross_sections/crosssec_fit.py` — `fit_dpln` (men, double
Pareto-lognormal) and `fit_mixture` (women, two-component lognormal mixture), both doubly
Type-I censored at `LOWC = $200` and a year-specific `HIGHC = taxmax(year) - $1000`. Both take
an optional `start=` warm-start theta (`start=None` runs the multi-start), plus `mean_pen=(eta, w)`
and `smooth_pen=(wvec, g_target)`. Two performance/robustness details that matter:

- **The interior likelihood is binned** (`bin_interior`, ≤256 mass points). The joint solve refits
  each cell tens of times; this is the single biggest speedup (a warm dPlN fit: 46 ms → 0.7 ms).
- **Parameters are boxed structurally, not by penalty** (`NU_LO/NU_HI`, `TAU_MIN/TAX_MAX`,
  `SIG_MIN/SIG_MAX`, and `ALPHA_MIN = 1.05` whenever the mean pull is on). In a ~75%-censored cell
  the interior carries almost no shape information, and without boxes `exp(ν+τ²/2)` overflows or
  `α≤1` gives an *infinite* uncapped mean — either poisons the whole year's aggregate.

Warm inner-loop solves use loose L-BFGS tolerances (`WARM_OPTS`); cold multi-starts use
`COLD_OPTS`. Parallelism is across years (`ProcessPoolExecutor`, BLAS pinned to one thread).

**Runtime** ≈ **6 min** at `--jobs 8` (stage 0 ≈ 27 s; the joint solve ≈ 340 s wall / 2400 s CPU).
The tight-cap years (1951–56) are slowest, ~80 s each: heavy censoring means a flat likelihood and
more η iterations. That ~6 min is close to the *converged* cost, not a corner-cut — `GS_TOL` stops
a sweep once nothing moves and the η search exits at `MOMENT_TOL`, so extra passes mostly idle.
`XS_CONT_PASSES` / `XS_ETA_PASSES` (env vars, defaults 2 / 3) raise the Gauss-Seidel effort;
raising them to 3 / 4 costs only +13% for that reason. They are **environment** variables, not CLI
flags, because the year workers are spawned and re-import the module, so globals rebound in
`main()` never reach them. To actually buy quality, raise `K_CAND` (richer basin set for Viterbi)
or `RHO_STEPS` — those change what is explored rather than how long it is polished.

**How much the constraint is worth**, measured on the in-sample uncapped mean per worker (the
exact quantity stage 3 drives: cells weighted by their `n` share, analytic `dpln_mean`/`mix_mean`).
Comparing `cross_section_params.csv` (stage 0, unconstrained) against
`cross_section_params_smoothed.csv` over 1951–2006: the unconstrained fit averages **1.33×** the
ASS benchmark and peaks at **3.5×** in the tight-cap 1950s–60s, against **0.9955 [0.969–1.004]**
constrained. It also leaves **374 of 3326 men's cells at α≤1**, i.e. an *infinite* uncapped mean —
up to 15% of a year's workers, so the unconstrained aggregate is not merely biased but undefined.
Zero cells hit α≤1 after the joint solve. That is what the aggregate constraint buys; the two
bullets below are how to keep it.

**Two properties of the constraint that are easy to get wrong:**

- **η ≥ 0 (thinning only) — a mathematical fact, not a preference.** The term is `+η·w·E[X]`:
  bounded below for η>0, so thinning has an interior optimum. For η<0 it is `−|η|·w·E[X]` with
  `E[X] ∝ 1/(α−1)` unbounded above, so the objective is **unbounded below** and every cell slams
  into the α floor at once (measured in 1990: aggregate goes from 0.96× benchmark at η=−0.05 to
  60,000× at η=−0.1). A year whose model mean is *below* the benchmark is therefore left alone.
  In practice most years pin exactly (mean ratio 1.0000); the rest sit slightly under.
- **ρ is calibrated against that.** Smoothing shrinks the cross-cell dispersion of the log-scale g
  slots, and E[X] is exponential in them, so by Jensen it biases the aggregate mean **down** —
  which η cannot undo, per the above. So ρ must be small enough that the smoothed fit still
  *overshoots*. `SMOOTH_FRAC = 1e-4` was chosen from a **5-point sweep of full re-solves**
  (`output/cross_sections/plots/rho_sweep_ass_tr_ratios.png`), which is also the recipe for retuning it:

  | SMOOTH_FRAC | in-sample uncapped mean [min–max] |
  |---|---|
  | 3e-5 | 0.9915 [0.955–1.001] |
  | **1e-4** | **0.9923 [0.967–1.002]** |
  | 3e-4 | 0.9907 [0.965–1.001] |
  | 1e-3 | 0.9852 [0.952–1.001] |
  | 3e-3 | 0.9776 [0.920–1.001] |

  1e-4 is an *interior* optimum (it beats less smoothing at 3e-5), so it is a real choice rather
  than "as little smoothing as possible". ρ only moves the ratio in the η=0 years; elsewhere
  the constraint pins the aggregate whatever ρ is. Retune with `--rho`, judging on the heatmaps plus
  the uncapped ratio. **Note that a sweep leaves the canonical output CSVs holding the LAST ρ run** —
  restore the chosen one before regenerating the heatmaps and the validation figure.

**Stage 2** (`extrapolate_params.py`) is unchanged in structure — shapes frozen at the nearest data
edge (2000–04 forward, 1951–55 backward), locations rigid-shifted by the published/projected wage
index — with one calibration. The pre-1951 years are *before* the data, so they inherit the 1951–55
tail unadjusted, which lands ~5% under the ASS benchmark. `calibrate_alpha_scale` fixes that with a
**per-year multiplicative scale on men's α**, root-found so each year's uncapped mean matches
exactly; women's parameters are held fixed and enter as an offset. One scalar against one published
moment per year — exactly identified, and legitimate precisely because α is unidentified above the
low pre-1951 cap. E[X] ∝ α/(α−1) is monotone in α, so unlike the in-sample η this direction is well
posed **both** ways, and `k·α > 1` is enforced so every cell keeps a finite mean.

Two caveats on that calibration, both visible in the validation figure: it makes pre-1951 *capped*
earnings worse (~1.02 → ~1.07 at 1937), because under the very low pre-1951 cap most mass is above
it, so moving α moves the capped mean too; and the implied k path is erratic (**1938 is a 10×
outlier**, k=5.24 between neighbours of 0.49 and 0.78) because the wage index misses the 1938
downturn and α, the only free parameter, absorbs the whole residual. If that matters, the residual
belongs in the location (ν) rather than the tail.

`extract_table_4B1.py` has flags: `--no-duckdb` (write CSV only), `--html/--out/--duckdb/--table`.

## Architecture

- **Code and outputs are organized into four parallel sections**, each a subfolder of
  both `code/` and `output/`: `data_import/` (build the shared DB from raw CSV + saved
  HTML), `ssa_replication/` (replicate Compson 2012 RS Note figures/tables),
  `cross_sections/` (fit per-cell earnings distributions by year × sex × age — dPlN,
  lognormal mixture — in one joint solve that smooths along age and pins each year's uncapped
  mean to the ASS benchmark, then extrapolate off the data edges), and `dynamics/` (estimate
  the GKOS lifecycle profile g(t) by cohort × sex, then extrapolate and validate it against
  aggregate taxable earnings).
  Everything is still run **from the project root**, so in-code paths stay root-relative
  (`processed_data/ssa.duckdb`, `output/<section>/...`).
- **Each section separates estimation from figures.** Estimators live in the section root and
  never import a plotting module; every figure script lives in `code/<section>/plots/` and
  mirrors `output/<section>/plots/`. This is load-bearing, not cosmetic: the MLE+GMM estimator
  used to import its GKSW target loaders *from* `plot_guv_comparison.py`, which made an
  estimation run depend on matplotlib. Those loaders are now `cross_sections/guv_targets.py`.
  Where an estimator does produce figures as a side deliverable (`--mode mle` writes the
  parameter heatmaps), it **lazy-imports** the plot module inside `main()` so the dependency
  never exists at module import time.
- **Each section has ONE estimation entry point** that dispatches on `--mode`:
  `estimate_cross_sections.py` (`mle` | `mle-gmm` | `both`) and `estimate_g_cohort.py`
  (`ols` | `smm-mean` | `smm-quantiles`). The modules behind them (`crosssec_mle.py`,
  `crosssec_gmm.py`, `gcohort_model.py`, `gcohort_ols.py`, `gcohort_smm.py`) are libraries with
  no CLI of their own — add a mode to the entry point rather than a new top-level script.
- **Single shared DB `processed_data/ssa.duckdb`** is the integration point. Everything —
  EPUF microdata and Supplement aggregates — lives here so replication queries can `JOIN`
  microdata against the published series `USING (year)`. The two loaders each touch only
  their own tables (`CREATE OR REPLACE`), so they compose without stepping on each other.
- **`raw_data/` and `processed_data/` are large and not version-controlled.** The DB is a
  regenerable artifact — rebuild it from the raw CSVs, never hand-edit it. `raw_data/` is
  treated as read-only source data.
- **Ingestion is CSV → typed DuckDB tables** (`build_epuf_duckdb.sql`) and **saved HTML →
  CSV → DuckDB** (`extract_table_4B1.py`). The Supplement page is committed as saved HTML
  (`*.source.html`) because SSA's edge blocks non-browser fetches — parse that file, do not
  try to re-download it.

## Gotchas that will bite you

- **The e9f series is CPI-deflated; this project's price index is PCE.** `agg_taxable_earnings_extrap.parquet`
  (the prior cross-section pipeline, `project_vu`) is in real 2013 dollars, and reflating it with
  our `price_index()` overstates it by up to **25%** mid-century (1960: 0.1297 vs 0.1623). The two
  indices agree exactly at 2013 and diverge going back, so the error is invisible at the recent end
  and worst where the series is hardest to eyeball — it put e9f at 1.12× the published benchmark in
  sample, i.e. implausibly above a series it is built from. `load_e9f` recovers e9f's OWN deflator
  from the file instead, as `nominal taxmax(y) / tax_max_2013(y)`, which needs no assumption about
  which index they used. Corrected, e9f/benchmark is 0.972 [0.882–1.049] in sample, alongside EPUF
  (0.948) and the parametric surface (0.987). 1950 is the check year: the taxable maximum was flat
  at $3,000 through 1950, and the recovered conversion lands on 1.000 there.
  **Any other real-dollar series from an outside pipeline deserves the same treatment** — find a
  quantity whose nominal value you know, recover their deflator from it, and do not assume ours.

- **`annual` is a sparse panel: an absent `(id, year)` means zero covered earnings that
  year, not missing data.** Balanced-panel work must zero-fill (see `example_panel_to_age60.sql`).
- **EPUF quantiles sit below the GKSW cohort × age files by design, not by error.** GKSW's
  files are Kopczuk–Saez–Song "commerce and industry" W-2 wages (no self-employment, no
  agriculture/households/hospitals/education/public admin); EPUF `earnings` is all covered
  earnings incl. taxable self-employment, and has no flag to reproduce that selection. The
  gap is bottom-heavy and age-increasing (men's p10 −15 to −20%, p75 −4%; women's p50/p75
  ≈ 0), which no per-year deflator error can produce, and it closes in 2005 only because
  GKSW's source switches to the raw MEF. The sel0 screen (`sel0_threshold`) and the PCE
  deflator (BEA 2009 = 100 vintage, 2013 entry 107.572 as base) are ONE definition in
  `guv_targets.py`, asserted by `check_guv_conventions()` — do not re-code either inline.
  `plot_guv_gap_signature.py` is the measurement; `README.md` has the full caveat.
- **`earnings` is top-coded** at each year's taxable maximum (plus bottom-coded and
  random-rounded). It understates true earnings, severely before ~1980. Restrict to
  `year >= 1980` for top-of-distribution analysis.
- **EPUF is a 1% sample:** scale to population by ×100 when comparing to Supplement totals
  (as the replication scripts do).
- Raw sentinel codes are normalized on load and stored as `NULL`: `sex = 3` ("unspecified")
  and `qtrs = '.'` (all 1951–52 rows). Account for these NULLs.
- In `example_panel_to_age60.sql`, `generate_series` needs **literal** age bounds, so the
  start/end ages (25/60) appear as literals in two places — keep them in sync.
