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
distributions). This is a **two-stage pipeline**: fit each cell, then smooth the
parameter surfaces (the smoothed CSV feeds a downstream polynomial extrapolation).

```bash
# stage 1 — fit every (year, sex, age) cell → cross_section_params.csv (+ per-cell info)
python code/cross_sections/estimate_cross_sections.py [--jobs N]
# stage 2 — penalized smooth over the age×cohort grid → cross_section_params_smoothed.csv
python code/cross_sections/smooth_params.py [--lam L] [--neighbors K]

python code/cross_sections/plot_cross_section.py [age] [cohort] [sex]         # raw histogram vs fitted density (defaults age 40, cohort 1950, women)
python code/cross_sections/param_visualization.py [men|women|both] [csv]      # cohort×age heatmaps of every parameter (pass the smoothed CSV for its surfaces)
python code/cross_sections/plot_aggregate_taxable.py [params.csv]             # model vs EPUF vs ASS aggregate taxable (defaults to raw; pass smoothed CSV to check it)
python code/cross_sections/compare_year_fits.py [yearA yearB] [ages...]       # overlay two years' male dPlN fits across ages (the 1956-vs-1957 basin diagnostic)
```

**Stage 1** (`estimate_cross_sections.py`) fits one distribution per `(year, sex,
single-year age)` cell (~6.4k cells, ≥1000 obs each; smaller cells skipped), ~3 min.
Fast via one DB pull per year and parallelism across years (`ProcessPoolExecutor`,
BLAS pinned to one thread per worker). Robust via **multi-start keep-best**: each cell
is fit from a warm start (the previous age) *and* a cold start (dPlN: moment + low/high-α
seeds; mixture: 6-point grid), keeping the lowest-negll converged fit — L-BFGS-B reports
success at local optima too, so a single warm solve can lock a whole year into a worse
basin (this was the 1957/1974 heavy-censoring aggregate bug). The CSV carries a `converged`
flag and each cell's diagonal observed information (`info_*` columns) for stage 2.

**Stage 2** (`smooth_params.py`) borrows strength across cells to resolve the flat
likelihood ridges (the dPlN upper-tail index, the mixture's minority component) whose
argmax wanders between near-identical neighbours. It solves, per parameter in theta
space, a precision-weighted roughness-penalized system: weight = the stored `info_*`
(so well-identified ν/μ1 are frozen and the aggregate is preserved, ridge params defer
to neighbours), penalty = the residual of a local-linear fit to each cell's `--neighbors`
(default 5) nearest neighbours (trend-preserving, isotropic). `--lam` (default 10) is an
information threshold: a parameter is smoothed only where its own info < ~λ. The women's
two components are smoothed as `mu2` and `log(mu1−mu2)` so the full-time/part-time modes
stay ordered and never cross.

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
  lognormal mixture — then smooth the parameter surfaces over the age×cohort grid).
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
