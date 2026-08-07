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
python code/ssa_replication/plot_chart4_replication.py                                  # → output/ssa_replication/chart4_replication.pdf
```

Run cross-sectional distribution fits (per year × sex × single-year-age earnings
distributions). This is a **three-stage pipeline**: fit each cell, smooth the parameter
surfaces while pinning the censored upper tail to the published uncapped mean, then
extrapolate the surfaces off the observed span. Run the stages in order — each reads the
prior CSV:

```bash
# stage 1 — fit every (year, sex, age) cell → cross_section_params.csv (+ per-cell info)
python code/cross_sections/estimate_cross_sections.py [--jobs N]
# stage 1.5 — penalized smooth over the age×cohort grid + ASS uncapped-mean moment match
#             → cross_section_params_iterated.csv   (this is the current smoothing stage)
python code/cross_sections/iterate_fit_smooth.py [--outer T] [--window W] [--jobs N] [--no-moment]
# stage 3 — anchor + wage-index extrapolation off the data edges → cross_section_params_extrapolated.csv
python code/cross_sections/extrapolate_params.py

python code/cross_sections/plot_cross_section.py [age] [cohort] [sex]                 # raw histogram vs fitted density (defaults age 40, cohort 1950, women)
python code/cross_sections/param_visualization.py [men|women|both] [csv]              # cohort×age heatmaps of every parameter (pass the iterated CSV for its surfaces)
python code/cross_sections/plot_aggregate_taxable.py [params.csv]                     # in-sample-only diagnostic: model vs EPUF vs ASS aggregate taxable (pre-extrapolation)
python code/cross_sections/plot_aggregate_taxable_extrapolated.py                     # END-TO-END validation: extrapolated model vs ASS+TR, capped AND uncapped (the figure to trust)
python code/cross_sections/compare_year_fits.py [yearA yearB] [ages...]               # overlay two years' male dPlN fits across ages (the 1956-vs-1957 basin diagnostic)
```

`smooth_params.py` is the **old standalone stage 2**, superseded by `iterate_fit_smooth.py`
(which folds its smoothing into the fit): it is no longer run as a pipeline stage and its
`cross_section_params_smoothed.csv` output feeds nothing. The module is retained only because
`iterate_fit_smooth` imports its `to_theta` transform helper.

**Stage 1** (`estimate_cross_sections.py`) fits one distribution per `(year, sex,
single-year age)` cell (~6.4k cells, ≥1000 obs each; smaller cells skipped), ~3 min.
Fast via one DB pull per year and parallelism across years (`ProcessPoolExecutor`,
BLAS pinned to one thread per worker). Robust via **multi-start keep-best**: each cell
is fit from a warm start (the previous age) *and* a cold start (dPlN: moment + low/high-α
seeds; mixture: 6-point grid), keeping the lowest-negll converged fit — L-BFGS-B reports
success at local optima too, so a single warm solve can lock a whole year into a worse
basin (this was the 1957/1974 heavy-censoring aggregate bug). The CSV carries a `converged`
flag and each cell's diagonal observed information (`info_*` columns) for stage 1.5.

**Stage 1.5** (`iterate_fit_smooth.py`) does two things. First it borrows strength across
cells to resolve the flat likelihood ridges (the dPlN upper-tail index, the mixture's
minority component) whose argmax wanders between near-identical neighbours: an EM-style loop
refits each cell against the *true* censored likelihood plus a roughness penalty toward the
local-linear fit of its age×cohort neighbours, with a REML per-parameter precision `lam` (so
well-identified ν/μ1 follow the data while the flat-ridge α snaps to the neighbour line).
Then a **final moment-match pass** (`moment_match`, on by default; `--no-moment` skips) pins
the one quantity the taxable cap censors — the mean. Under a tight cap ~40–45% of older men
are top-coded and the censored MLE fits a heavy dPlN tail (`α≤1`, an *infinite* uncapped
mean); capped comparisons hide this but the implied uncapped mean ran ~1.9× ASS pre-1951 and
3–4× in the tight-cap late-1950s/60s. Per year we solve a single multiplier `eta` so the
composition-weighted model `E[X]` over men+women 15–77 equals the published ASS uncapped mean
(`aggearn_tot / num_wrk`), refitting each men cell **full-vector** (α, β, ν, τ together, so
the body compensates as the tail thins) under `negll + Σ lam(θ−line)² + eta·w·E[X]`. Women's
finite mixture mean is a fixed offset; `eta≥0` only thins, and is 0 where the model doesn't
overshoot, so it self-limits to the tight-cap era. This makes stage 1.5 depend on the ASS
workbook; the output gains `alpha_premoment` and `eta_mean` diagnostics.

The fits themselves live in `code/cross_sections/crosssec_fit.py` — a shared,
`(year, sex[, age])`-parameterized module: `fit_dpln` (men, double Pareto-lognormal)
and `fit_mixture` (women, two-component lognormal mixture), both doubly Type-I censored
at `LOWC = $200` and a year-specific `HIGHC = taxmax(year) - $1000`. Both accept an
optional `start=` warm-start theta (packed by `dpln_theta` / `mix_theta`; `start=None`
runs the multi-start), and both return the diagonal observed information at the optimum.
`load_earnings(year, sex, age=None)` slices a cell; `plot_cross_section` addresses a
cell as `(age, cohort, sex)` with `year = cohort + age`. The entry-point scripts above
import this module; write new cross-section analyses against it too.

`extract_table_4B1.py` has flags: `--no-duckdb` (write CSV only), `--html/--out/--duckdb/--table`.

## Architecture

- **Code and outputs are organized into three parallel sections**, each a subfolder of
  both `code/` and `output/`: `data_import/` (build the shared DB from raw CSV + saved
  HTML), `ssa_replication/` (replicate Compson 2012 RS Note figures/tables), and
  `cross_sections/` (fit per-cell earnings distributions by year × sex × age — dPlN,
  lognormal mixture — smooth the parameter surfaces over the age×cohort grid while pinning
  the censored tail to the ASS uncapped mean, then extrapolate off the data edges).
  Everything is still run **from the project root**, so in-code paths stay root-relative
  (`processed_data/ssa.duckdb`, `output/<section>/...`).
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

- **`annual` is a sparse panel: an absent `(id, year)` means zero covered earnings that
  year, not missing data.** Balanced-panel work must zero-fill (see `example_panel_to_age60.sql`).
- **`earnings` is top-coded** at each year's taxable maximum (plus bottom-coded and
  random-rounded). It understates true earnings, severely before ~1980. Restrict to
  `year >= 1980` for top-of-distribution analysis.
- **EPUF is a 1% sample:** scale to population by ×100 when comparing to Supplement totals
  (as the replication scripts do).
- Raw sentinel codes are normalized on load and stored as `NULL`: `sex = 3` ("unspecified")
  and `qtrs = '.'` (all 1951–52 rows). Account for these NULLs.
- In `example_panel_to_age60.sql`, `generate_series` needs **literal** age bounds, so the
  start/end ages (25/60) appear as literals in two places — keep them in sync.
