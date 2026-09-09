# SSA Earnings Data — EPUF 2006 + Annual Statistical Supplement

## Data sources

This repository collects **two complementary SSA earnings data sources**, both ultimately
from the Master Earnings File but not interchangeable:

1. **EPUF 2006** — the 1% individual **microdata** (person and person-year records); detailed below.
2. **Annual Statistical Supplement (ASS)** — SSA's published **aggregate** tables (currently
   Table 4.B1, 2008 edition), used as an external benchmark when replicating Compson (2012).

| | EPUF 2006 | Annual Statistical Supplement |
|---|---|---|
| Grain | individual microdata (1% sample) | published annual aggregates |
| Sampling frame | 1% of all SSNs | CWHS frame |
| Earnings cap | capped at the taxable max **per person** | taxable capped **per job** (can exceed the max); also reports uncapped total |
| Adjustments | disclosure-protected: bottom/top-coded, random-rounded; ages ≤14/≥86 zeroed | OCACT adjustments for late/erroneous reporting |
| In this repo | `EPUF2006_*.csv` | `supplement_2008_table_4B1.csv` |

Because of the per-person vs per-job cap and the OCACT adjustments, EPUF aggregates *should*
fall **below** the Supplement's taxable-earnings totals — this is the expectation behind RS
Note 2012-01, and something we have **not yet tested** against our own EPUF extract.

The **2006 Earnings Public-Use File (EPUF)** is a public microdata file released by the
U.S. Social Security Administration (SSA). It is a **systematic 1% random sample of all
Social Security numbers (SSNs) issued before January 2007**, and it reports **annual
Social Security taxable earnings from 1951 to 2006** for the sampled individuals (plus a
1937–1950 aggregate).

**Where the earnings come from — the Master Earnings File (MEF).** The values are drawn
from the *summary segment* of SSA's MEF, the administrative system of record used to
determine benefit eligibility and compute benefit amounts. The MEF summary segment holds,
for each person-year, a running total of Social Security *covered* earnings (wages subject
to the payroll tax, plus taxable self-employment income).

**"Capped" earnings — the key measurement caveat.** The MEF itself records taxable
earnings that can exceed the annual taxable maximum when a person has multiple employers.
EPUF instead reports **capped** taxable earnings: each person-year is **top-coded at that
year's taxable maximum**. So EPUF measures covered earnings *up to the cap*, not total
labor income — the gap widens in years/for workers where earnings exceed the cap.

**Which records are in the sample.** The sample is defined on SSNs, not on a work-history
frame. From an underlying 1% draw, SSA removed some individuals during data cleaning (e.g.,
overlap with the New Beneficiary Data System) and, for disclosure protection, **zeroed out
earnings at ages ≤ 14 or ≥ 86**. All monetary values are additionally **bottom-coded and
random-rounded** (rounding base grows with the amount), so individual dollar figures are
approximate by design.

**Relation to the CWHS.** EPUF is *not* the Continuous Work History Sample (CWHS). The CWHS
is a **separate sampling frame** that SSA's Office of Research, Evaluation, and Statistics
uses to produce the published aggregates in the *Annual Statistical Supplement*. Because
EPUF (a 1%-of-SSNs draw from the MEF) and the CWHS are distinct frames — and because the
Supplement uses uncapped taxable earnings and applies Office of the Chief Actuary
adjustments for delinquent/fraudulent/late reporting that EPUF does **not** — estimates
from the two sources differ, though the differences are modest once the capping and
adjustments are accounted for.

**Further documentation**
- Compson, Michael (2012). *Comparing Earnings Estimates from the 2006 Earnings Public-Use
  File and the Annual Statistical Supplement.* SSA Research and Statistics Note No. 2012-01.
  <https://www.ssa.gov/policy/docs/rsnotes/rsn2012-01.html>
- Compson, Michael (2011). *The 2006 Earnings Public-Use Micro Data File: An Introduction.*
  Social Security Bulletin 71(4).
- `raw_data/epuf_dictionary.pdf` — field-level data dictionary shipped with the file.
- `raw_data/READ ME FIRST.doc` — SSA's original release notes.

### Annual Statistical Supplement — Table 4.B1 (2008 edition)

*"Number of workers with taxable earnings, amount of earnings, and Social Security numbers
issued, selected years 1937–2007."* Saved page: `raw_data/supplement_2008_table_4B1.source.html`
(from `.../supplement/2008/4b.html`; SSA's edge blocks non-browser fetches, so it was captured
from the browser). `code/data_import/extract_table_4B1.py` parses it to
`output/data_import/supplement_2008_table_4B1.csv` **and** loads it as table `supplement_4b1`
into the shared `processed_data/ssa.duckdb` (see [Database structure](#database-structure)).

Used to replicate Compson (2012), whose Table 1 compares the EPUF 1% sample against the
taxable-earnings series here. Columns that map to that comparison: **`reported_taxable_musd`**
(per-job-capped taxable — the headline series), **`workers_total_thousands`** (worker count),
and **`total_covered_earnings_musd`** (fully uncapped total — the other end of the capping wedge).

| Column | Meaning |
|---|---|
| `year` | Earnings year (selected years 1937–2007) |
| `prelim_flag` | SSA preliminary-data flag e/f/g (blank = final) |
| `workers_total_thousands` | Workers with taxable earnings (thousands); 1937–50 wage & salary only, 1951+ incl. self-employment |
| `workers_with_max_thousands` | Workers with earnings at the taxable maximum (thousands) |
| `new_entrants_thousands` | Workers with first taxable earnings under the program that year (thousands) |
| `total_covered_earnings_musd` | Total wages incl. estimated amounts above the taxable limit ($M); **uncapped** |
| `reported_taxable_musd` | Reported taxable earnings ($M); **per-job capped** |
| `reported_taxable_pct` | Reported taxable as % of total covered earnings |
| `avg_total_earnings_usd` | Average total earnings per worker ($) |
| `avg_reported_taxable_usd` | Average reported taxable earnings per worker ($) |
| `ssn_issued_thousands` | Social Security numbers issued (thousands; excludes railroad numbers) |

Empty `workers_with_max`/`new_entrants` for 2007 = "not available" (`--` in source).
Preliminary footnotes: **e** preliminary; **f** taxable = preliminary SSA, employment =
preliminary BLS; **g** preliminary BLS/BEA. SSA source line: *Master Earnings File, 1 percent
sample; BEA; BLS.*

Related Supplement tables for the note's other comparisons (not yet collected): **4.B4**
(% below max by sex), **4.B6** (median earnings by sex and age), **4.B3** (median by type and sex).

## Repository layout

```
epuf_2006/
├── README.md                     # this file
├── raw_data/                     # source data, as distributed (large; do not edit)
│   ├── EPUF2006_DEMOGRAPHIC.csv               #  151 MB — EPUF, one row per person
│   ├── EPUF2006_ANNUAL.csv                    # 1.75 GB — EPUF, one row per person-year
│   ├── epuf_dictionary.pdf                    # EPUF field dictionary
│   ├── READ ME FIRST.doc                      # EPUF release notes
│   └── supplement_2008_table_4B1.source.html  # ASS Table 4.B1, saved source page
├── code/
│   ├── data_import/
│   │   ├── build_epuf_duckdb.sql          # load EPUF CSVs → ssa.duckdb (demographic, annual)
│   │   └── extract_table_4B1.py           # parse saved 4.B1 HTML → CSV + ssa.duckdb (supplement_4b1)
│   ├── ssa_replication/
│   │   ├── example_panel_to_age60.sql     # sample analysis query (see below)
│   │   ├── replicate_note_table2.sql      # replicate Table 2 of RS Note 2012-01
│   │   └── plots/
│   │       └── plot_chart4_replication.py # replicate Chart 4 → output/ssa_replication/chart4_replication.pdf
│   ├── cross_sections/
│   │   ├── estimate_cross_sections.py     # UNIFIED ENTRY POINT: --mode mle | mle-gmm | both
│   │   ├── crosssec_fit.py                # shared (year, sex[, age]) fitters: dPlN (men) + lognormal mixture (women)
│   │   ├── crosssec_mle.py                # --mode mle:     joint smoothed, aggregate-constrained censored MLE
│   │   ├── crosssec_gmm.py                # --mode mle-gmm: convex combination of that likelihood with a GMM
│   │   │                                  #                 criterion on the published GKSW targets
│   │   ├── guv_targets.py                 # GKSW target loading + stable log-space Normal-Laplace pdf/cdf
│   │   ├── extrapolate_params.py          # stage 2: extrapolate off the data edges → cross_section_params_extrapolated.csv
│   │   └── plots/
│   │       ├── plot_cross_section.py      # raw histogram + fitted density, one (age, cohort, sex) cell
│   │       ├── plot_param.py              # cohort×age heatmaps of every fitted/smoothed parameter
│   │       ├── plot_agg_tax_total.py      # aggregate earnings, capped + uncapped: model vs EPUF vs ASS+TR
│   │       ├── plot_guv_comparison.py     # fitted cells vs the published GKSW functionals
│   │       ├── plot_guv_quantile_validation.py
│   │       ├── plot_nu_tau.py             # slide-sized ν/τ panels
│   │       └── plot_ass_capped_ratio.py
│   └── dynamics/
│       ├── estimate_g_cohort.py           # UNIFIED ENTRY POINT: --mode ols | smm-mean | smm-quantiles
│       ├── gcohort_model.py               # GKOS process, simulation, suffix tables, the moment map (no plotting)
│       ├── gcohort_ols.py                 # --mode ols: CMS's per-block OLS (reproduces their coefficients)
│       ├── gcohort_smm.py                 # --mode smm-*: SMM with multi-step optimal weighting
│       ├── gcohort_epuf.py               # --mode smm-p50: GKSW + EPUF medians, wedge, hinges
│       ├── epuf_targets.py                # EPUF cohort × age medians, ages 20–70
│       ├── relevel_g_cohort.py            # median for shape, mean for level
│       ├── extrapolate_g_cohort.py        # extrapolate g(t) off the observed cohort range; price_index()
│       └── plots/
│           ├── plot_g_cohort.py           # coefficient paths by cohort, any fit/extrapolated CSVs overlaid
│           ├── compare_g_cms.py           # fitted g vs CMS's published lifecycle profiles
│           ├── plot_agg_tax_dynamics.py   # aggregate taxable earnings from the g(t) path vs ASS
│           ├── plot_cohort_profile.py     # one cohort by age: model vs GKSW vs EPUF
│           ├── plot_p50_fit.py            # both target sources, model median, model + δ
│           ├── plot_shape_gap.py          # log-earnings spreads and E[Y] by rank bin, model vs GKSW
│           ├── plot_cms_selection.py      # CMS's process as they coded it: the selection wedge
│           └── plot_gkos_ordinal.py       # ordinal-transform invariance to g(t)
├── processed_data/
│   └── ssa.duckdb                     # shared DB: demographic + annual + supplement_4b1 (~1.6 GB)
└── output/                            # generated artifacts (regenerable; not version-controlled)
    ├── data_import/
    │   └── supplement_2008_table_4B1.csv  # ASS Table 4.B1, extracted (1937–2007)
    ├── ssa_replication/
    │   └── chart4_replication.pdf
    └── cross_sections/
        ├── cross_section_params.csv           # stage-1 fitted params (+ info_*), one row per year × sex × single-year age (≥1000 obs)
        ├── cross_section_params_smoothed.csv  # stage-2 smoothed params (feeds the downstream polynomial extrapolation)
        ├── plots/                             # all figures
    └── dynamics/
        ├── g_cohort_{ols,smm_mean,smm_quantiles}[tag].csv   # one row per sex x cohort
        ├── *_extrapolated.csv                 # every cohort 1892-2105, read by plot_agg_tax_dynamics.py
        └── plots/                             # all figures
            ├── {women_mixture,men_dpln}_c<cohort>_a<age>.{pdf,png}
            ├── param_heatmaps_{men,women}{,_smoothed}.{pdf,png}
            ├── compare_men_<yearA>_<yearB>.{pdf,png}
            └── aggregate_taxable{,_smoothed}.{pdf,png}
```

`raw_data/` and `processed_data/` are large and are not version-controlled; regenerate the
database from the raw CSVs with the build script.

## Database structure

All SSA data live in one shared [DuckDB](https://duckdb.org) database,
`processed_data/ssa.duckdb`, with three tables:

| Table | Source | Grain | Rows |
|---|---|---|---|
| `demographic` | EPUF demographic sub-file | one row per person | 4,384,254 |
| `annual` | EPUF annual sub-file | one row per person-year | 60,326,474 |
| `supplement_4b1` | ASS Table 4.B1 (2008) | one row per year (1937–2007) | 61 |

Build it from the project root (`epuf_2006/`) in two steps — the EPUF tables via SQL,
then the Supplement table via the Python extractor (which also writes the CSV):

```bash
duckdb processed_data/ssa.duckdb < code/data_import/build_epuf_duckdb.sql   # ~7 s → demographic, annual
python code/data_import/extract_table_4B1.py                                # → supplement_4b1
```

Both steps use `CREATE OR REPLACE`, so they are idempotent and order-independent.
The `demographic`/`annual` schemas are detailed below; `supplement_4b1` mirrors the
CSV columns documented under
[Annual Statistical Supplement — Table 4.B1](#annual-statistical-supplement--table-4b1-2008-edition).

### Table `demographic` — one row per person (4,384,254 rows)

Every sampled individual appears exactly once; `id` is unique.

| Column          | Type     | Range / codes   | Meaning |
|-----------------|----------|-----------------|---------|
| `id`            | INTEGER  | 1 – 4,384,254   | Random person identifier (join key, unique) |
| `yob`           | SMALLINT | 1870 – 2006     | Year of birth |
| `sex`           | TINYINT  | 1, 2, **NULL**  | 1 = Male, 2 = Female. **The raw code 3 ("unspecified", 3,054 people) is stored as `NULL`.** |
| `agg_earn_3750` | INTEGER  | 0 – 41,500      | Aggregate taxable earnings 1937–1950 (raw `TOT_COV_EARN3750` / dict. `AE3750`); top-coded at 41,500; ~80% are 0 |
| `qc_3750`       | SMALLINT | 0 – 56          | Credits (quarters of coverage) earned 1937–1950 (raw `QC3750` / dict. `TC3750`) |
| `qc_5152`       | SMALLINT | 0 – 8           | Credits earned 1951–1952 (raw `QC5152` / dict. `TC5152`); provided here because annual 1951–52 credits are unavailable |

### Table `annual` — one row per person-year (60,326,474 rows)

Long/tidy: only the 3.13M people with ≥1 positive-earning year appear, and only their
**positive-earning years**. **An absent `(id, year)` means zero covered earnings that
year** — this is a sparse panel, not a balanced one.

| Column     | Type     | Range / codes | Meaning |
|------------|----------|---------------|---------|
| `id`       | INTEGER  | → demographic | Person identifier (join key; repeats across years) |
| `year`     | SMALLINT | 1951 – 2006   | Earnings year (raw `YEAR_EARN`) |
| `earnings` | INTEGER  | ~45 – 94,200  | **Capped** SS taxable earnings; top-coded at the year's taxable maximum, bottom-coded, random-rounded |
| `qtrs`     | TINYINT  | 0 – 4, **NULL** | Quarters of coverage (SS credits) earned that year. **The raw missing code `.` (all 1951–52 rows) is stored as `NULL`.** |

Column-name changes from the raw CSVs are applied in the build script; both the raw header
name and the dictionary label are noted above because the CSV header and the
`epuf_dictionary.pdf` labels differ.

## Example query — earnings panel of fully-observed histories to age 60

`code/ssa_replication/example_panel_to_age60.sql` returns a **balanced, zero-filled long panel** of annual
earnings for every person whose **entire earnings history through age 60 is observed**
within the 1951–2006 window (i.e., uncensored at both ends).

Assuming careers start at **age 25** (the earnings-dynamics convention used in this
project), a history is fully observed when the whole age span 25–60 lies inside 1951–2006:

- reaches age 60 by 2006 → `yob + 60 <= 2006` (born ≤ 1946), and
- career start is observed → `yob + 25 >= 1951` (born ≥ 1926).

So the eligible cohorts are **birth years 1926–1946**: 644,793 people × 36 ages =
**23,212,548 person-year rows**. Missing years are filled with `earnings = 0` (a true zero,
since the full history is observed).

```sql
WITH cohort AS (                       -- uncensored history through age 60
    SELECT d.id, d.yob, d.sex
    FROM demographic d
    WHERE d.yob + 60 <= 2006           -- age 60 observed   (yob <= 1946)
      AND d.yob + 25 >= 1951           -- career start obs. (yob >= 1926)
),
ages AS (SELECT age FROM generate_series(25, 60) AS g(age))
SELECT
    cohort.id, cohort.sex, cohort.yob,
    ages.age,
    cohort.yob + ages.age    AS year,
    COALESCE(a.earnings, 0)  AS earnings,   -- 0 = no covered earnings that year
    a.qtrs
FROM cohort
CROSS JOIN ages
LEFT JOIN annual a
       ON a.id = cohort.id
      AND a.year = cohort.yob + ages.age
ORDER BY cohort.id, ages.age;
```

Run it with:

```bash
duckdb processed_data/ssa.duckdb ".read code/ssa_replication/example_panel_to_age60.sql"
```

Lowering the assumed start age tightens the window (it requires observing more early years,
so the lower birth-year bound rises and fewer cohorts qualify).

## Analysis caveats

- **Top-coding.** `earnings` is capped at the annual taxable maximum, so it understates true
  earnings — severely in early years (the cap binds near the ~56th percentile in 1965), much
  less after ~1980. Restrict to `year >= 1980` for top-of-distribution work.
- **Random rounding / bottom-coding.** Values are rounded to bases of $25/$100/$1,000
  (rising with earnings); values under $100 are replaced by the sub-$100 mean. Individual
  amounts are approximate.
- **Sparse panel.** Absence of a person-year = zero covered earnings, not missing data.
  Disclosure rules also zero out ages ≤ 14 and ≥ 86.
- **EPUF quantiles sit below the GKSW (Guvenen–Kaplan–Song–Weidner 2022) cohort × age
  files, and that is sample composition, not a bug.** Both are 1% samples of SSNs, so the
  *frames* are statistically equivalent (sampling error at a cell quantile is < 1%). The
  *sample selection* is not: the GKSW files are Kopczuk–Saez–Song's "commerce and industry"
  W-2 wages — no self-employment income, no agriculture, private households, hospitals,
  education, social services or public administration — while `earnings` here is all
  covered earnings including taxable self-employment (the Supplement's Table 4.B2 puts the
  self-employed at 7–11% of covered workers, with mean taxable earnings 45–80% of the wage
  mean). EPUF carries no industry or self-employment flag, so that selection cannot be
  reproduced. The wedge has the composition signature, not a deflation one: it is
  bottom-heavy (men's p10 15–20% below GKSW, p50 5–7%, p75 ~4%; women's p50/p75 at or above
  GKSW) and grows with age (men's p10 gap ~0 at 25–30, −25 to −33% at 50–55), whereas a
  price-index error would be one scalar per year. It closes in 2005 only because GKSW's own
  source switches from the KSS sample to the raw MEF (their p10 falls 8–17% in one year onto
  EPUF's). `code/cross_sections/plots/plot_guv_gap_signature.py` is the measurement; the
  screen and deflator are one shared definition in `guv_targets.py`, asserted at runtime by
  `check_guv_conventions()`.
- **`qtrs` is not "time worked".** It is an earnings-threshold credit count (max 4); since
  1978 it is a coarse function of annual earnings, not calendar quarters employed, and it
  saturates at 4 for most full-year workers.

## Cross-sectional distribution fits

For each `(year, sex, single-year age)` cross-section of **positive** capped earnings we fit a
parametric distribution to **log-earnings** by censored maximum likelihood. The two sexes get
different families — men a **double Pareto-lognormal** (single mode, heavy upper tail), women a
**two-component lognormal mixture** (the part-time/full-time bimodality) — but they share one
censored log-likelihood, derived below. The shared fitters live in
`code/cross_sections/crosssec_fit.py`. The analysis is a **two-stage pipeline**: one joint solve
that fits every cell while simultaneously smoothing along age and pinning each year's uncapped
aggregate mean to the published ASS benchmark, then an extrapolation off the two data edges.
(Fitting and smoothing were once separate stages; they have to be solved together, because
smoothing after constraining breaks the constraint and constraining after smoothing breaks the
smoothness — see `CLAUDE.md` for the details of the joint solve.)

All estimation goes through **one entry point**, `estimate_cross_sections.py`, whose `--mode`
selects the data term. `--mode mle` is the canonical pipeline; `--mode mle-gmm` combines the same
censored likelihood with a GMM criterion on the published GKSW targets (see `CLAUDE.md`).

```bash
# stage 1, mode mle — joint smoothed-constrained MLE over every (year, sex, age) cell, ≥1000 obs
#           → cross_section_params_smoothed.csv, plus the raw stage-0 fits in cross_section_params.csv
python code/cross_sections/estimate_cross_sections.py --mode mle [--jobs N] [--rho R] [--rho-steps S]
# stage 1, mode mle-gmm — convex combination with the GKSW targets, weight lam
#           → cross_section_params_guvgmm_smoothed.csv
python code/cross_sections/estimate_cross_sections.py --mode mle-gmm [--lam L] [--gmm-iters K]
# stage 2 — anchor + wage-index extrapolation off the data edges → cross_section_params_extrapolated.csv
python code/cross_sections/extrapolate_params.py

python code/cross_sections/plots/plot_cross_section.py [age] [cohort] [sex]  # raw histogram + fitted density; defaults to age 40, cohort 1950, women (year = cohort + age)
python code/cross_sections/plots/plot_param.py [men|women|both] [csv] [suffix]   # cohort×age parameter heatmaps
python code/cross_sections/plots/plot_agg_tax_total.py                       # end-to-end: capped and uncapped aggregates vs ASS + Trustees Report
```

### Lifecycle profile g(t) by cohort × sex

Also one entry point, `estimate_g_cohort.py`, with three estimators of the same object:

```bash
python code/dynamics/estimate_g_cohort.py --mode ols             # CMS's per-block OLS on the published moment
python code/dynamics/estimate_g_cohort.py --mode smm-mean        # SMM on meanlog alone (model inversion)
python code/dynamics/estimate_g_cohort.py --mode smm-quantiles   # SMM on meanlog + p10…p98, optimal weighting
python code/dynamics/extrapolate_g_cohort.py --fits output/dynamics/g_cohort_smm_mean.csv
python code/dynamics/plots/plot_g_cohort.py output/dynamics/g_cohort_smm_mean.csv output/dynamics/g_cohort_smm_mean_extrapolated.csv
python code/dynamics/plots/plot_agg_tax_dynamics.py --profiles output/dynamics/g_cohort_smm_mean_extrapolated.csv
```

g(t) is quadratic by default (GKOS's own form); `--degree 3` is available but diverges outside
the fitted 25–55 span. Estimation CSVs land in `output/dynamics/`, every figure in `output/dynamics/plots/`.
`--mode ols` reproduces CMS's published `lifecycle_income_*.dta` coefficients to ~4e-6 on `sel3`.
Its `g` is on a different **level** from the SMM modes — it absorbs the `E[u | u ≥ log(Ymin) − g]`
term the SMM modes strip out — so it reports `eu_offset` per block, with
`g0(ols) = g0(smm-mean) + eu_offset` exact. Slopes need no such correction.

The GKOS process is held at its published parameters, with one correction to note: the HIP
slope dispersion is `σ_β = 0.196` per decade of age (Table IV, on the same `t = (age−24)/10` as
g(t)), not the `0.196/10` CMS's `Simulation.m` uses. `CLAUDE.md` records what that changes.

**Stage 1** (`--mode mle`, implemented in `crosssec_mle.py`) fits ~6.4k `(year, sex, age)` cells (single-year ages
with ≥1000 positive-earnings observations; smaller cells skipped) in ~3 minutes: it pulls the data
once per year and fits years in parallel (BLAS pinned to one thread per worker). Each cell uses
**multi-start keep-best** — a warm start from the previous age and a robust cold start (the dPlN's
moment + low/high-α seeds, the mixture's 6-point grid), keeping the lowest-`negll` converged fit.
This matters because L-BFGS-B reports convergence at local optima too: under heavy top-censoring
(mid-1950s, mid-1970s) the weakly-identified upper tail has a secondary basin that a single warm
solve can fall into for a whole year, throwing off that year's aggregate. Each output row carries
a `converged` flag and the diagonal observed information (`info_*`) used by stage 2.

**Stage 2** (`smooth_params.py`) resolves the flat likelihood ridges — the dPlN upper-tail index,
the mixture's minority component — whose global argmax slides between near-identical neighbouring
cells at negligible likelihood cost. For each parameter it solves, in the fitter's theta
coordinate, a precision-weighted roughness-penalized least-squares system (the Laplace/penalized-MLE
approximation): the data weight is the stored `info_*`, so well-identified parameters (ν, μ1) are
frozen and the aggregate is preserved while ridge parameters are set by their neighbours; the
penalty is the residual of a local-linear fit to each cell's `--neighbors` (default 5) nearest
neighbours, which is trend-preserving (planar age/cohort gradients pass free). `--lam` (default 10)
reads as an information threshold — a parameter is borrowed from neighbours only where its own
information falls below ~λ. The women's two components are smoothed as `μ2` and `log(μ1−μ2)`, so
the full-time/part-time modes stay ordered and never cross.

Throughout, $\varphi$ and $\Phi$ denote the standard normal pdf and cdf.

### The censored log-likelihood (shared by both models)

Fix a cell (a year, sex, and single-year age), let the observed positive earnings be
$X_1,\dots,X_N>0$, and work on the log scale $Y_i=\log X_i$. Each model supplies a density $f(y;\theta)$ and cdf $F(y;\theta)$
for log-earnings.

The recorded dollar amounts are distorted at both extremes (see [Analysis
caveats](#analysis-caveats)): a bottom-code spike below ~\$100, and at the top a pile at the
taxable maximum plus a near-cap "collapse" spike from random rounding. We therefore do not
trust the exact values there and treat both extremes as **Type-I censored** — keeping only the
information "value below $t_{\text{lo}}$" or "value above $t_{\text{hi}}$", at the fixed
thresholds

$$ t_{\text{lo}} = \log 200, \qquad t_{\text{hi}} = \log\!\big(\mathrm{taxmax}(\text{year}) - 1000\big). $$

Only $t_{\text{hi}}$ moves with the year, through the statutory taxable maximum (recovered
from the data as that year's maximum earnings); $t_{\text{lo}}$ and both censoring rules are
identical across years and sexes. Partition the sample into

- **left-censored:** $Y_i \le t_{\text{lo}}$, count $n_{\text{lo}}$;
- **right-censored:** $Y_i \ge t_{\text{hi}}$, count $n_{\text{hi}}$;
- **interior:** the remaining $n_{\text{in}} = N - n_{\text{lo}} - n_{\text{hi}}$, with log-values $\{y_i\}$.

An interior observation is seen exactly and contributes its density $f(y_i;\theta)$. A
left-censored observation reveals only the event $\{Y\le t_{\text{lo}}\}$, of probability
$F(t_{\text{lo}};\theta)$; a right-censored one only $\{Y\ge t_{\text{hi}}\}$, of probability
$1-F(t_{\text{hi}};\theta)$. Because the thresholds are common to all censored observations
(that is what makes this Type-I), the censored factors collapse to powers, and the sample
likelihood is

$$ L(\theta) = \Bigg[\prod_{i\in\text{interior}} f(y_i;\theta)\Bigg]\, F(t_{\text{lo}};\theta)^{\,n_{\text{lo}}}\,\big[1-F(t_{\text{hi}};\theta)\big]^{\,n_{\text{hi}}}. $$

Taking logs gives the objective maximized in `crosssec_fit.py`:

$$ \ell(\theta) = \sum_{i\in\text{interior}} \log f(y_i;\theta) \;+\; n_{\text{lo}}\,\log F(t_{\text{lo}};\theta) \;+\; n_{\text{hi}}\,\log\!\big[1-F(t_{\text{hi}};\theta)\big]. $$

The two models differ **only** in the closed forms of $f$ and $F$ plugged into these three
blocks. Everything is computed in log-earnings space $y$ — the interior density and both
thresholds alike — so the change of variables from $X$ to $Y$ needs no Jacobian.

### Model A — double Pareto-lognormal (men)

$Y=\log X$ follows Reed's Normal–Laplace law $NL(\alpha,\beta,\nu,\tau)$: the distribution of
$Z+W$ with $Z\sim N(\nu,\tau^2)$ and $W$ an asymmetric Laplace with right/left rates
$\alpha,\beta>0$. On the dollar scale this is the double Pareto-lognormal — a lognormal body
with Pareto tails of index $\alpha$ (upper) and $\beta$ (lower). With $z=(y-\nu)/\tau$ and the
Mills ratio $R(w)=\big(1-\Phi(w)\big)/\varphi(w)$,

$$ f(y) = \frac{\alpha\beta}{\alpha+\beta}\,\varphi(z)\,\big[\,R(\alpha\tau - z) + R(\beta\tau + z)\,\big], $$

$$ F(y) = \Phi(z) - \varphi(z)\,\frac{\beta\,R(\alpha\tau - z) - \alpha\,R(\beta\tau + z)}{\alpha+\beta}. $$

The Mills ratio is evaluated as $R(w)=\sqrt{\pi/2}\,\operatorname{erfcx}(w/\sqrt2)$ for
stability in the tails. The four parameters are optimized unconstrained through
$(\log\alpha,\log\beta,\nu,\log\tau)$, warm-started by method of moments on the interior
Normal–Laplace cumulants.

### Model B — two-component lognormal mixture (women)

$Y=\log X$ is a mixture of two normals with weight $w$ on the first component:

$$ f(y) = \frac{w}{\sigma_1}\,\varphi\!\Big(\frac{y-\mu_1}{\sigma_1}\Big) + \frac{1-w}{\sigma_2}\,\varphi\!\Big(\frac{y-\mu_2}{\sigma_2}\Big), $$

$$ F(y) = w\,\Phi\!\Big(\frac{y-\mu_1}{\sigma_1}\Big) + (1-w)\,\Phi\!\Big(\frac{y-\mu_2}{\sigma_2}\Big), $$

so on the dollar scale $X$ is a mixture of two lognormals. All five parameters
$(\mu_1,\mu_2,\sigma_1,\sigma_2,w)$ are free. The right-tail survival $1-F(t_{\text{hi}})$ is
computed as $w\,\Phi(-z_1)+(1-w)\,\Phi(-z_2)$ to avoid cancellation. Optimization is
unconstrained through $(\mu_1,\mu_2,\log\sigma_1,\log\sigma_2,\operatorname{logit}w)$, with a
floor $\sigma_k \ge 0.02$ guarding the classic mixture degeneracy (the likelihood diverges as
a component collapses onto a data point, $\sigma_k\to 0$); several deterministic restarts
guard against local optima, and components are relabeled after the fit so component 1 is the
higher-mean one.

Both censored log-likelihoods are **fully closed form** — weighted normal pdf/cdf for the
mixture, Normal–Laplace pdf/cdf via Mills ratios for the dPlN — so no block requires numerical
integration; only the outer optimization is iterative.
