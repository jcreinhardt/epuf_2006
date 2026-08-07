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
distributions). **Two stages**: one joint optimization, then extrapolation off the observed
span. Run in order — the second reads the first's CSV:

```bash
# stage 1 — joint smoothed-constrained MLE → cross_section_params_smoothed.csv
#           (also writes the raw stage-0 fits to cross_section_params.csv, + both heatmap sets)
python code/cross_sections/estimate_cross_sections.py [--jobs N] [--rho R] [--rho-steps S]
# stage 2 — anchor + wage-index extrapolation off the data edges → cross_section_params_extrapolated.csv
python code/cross_sections/extrapolate_params.py

python code/cross_sections/plot_aggregate_taxable_extrapolated.py   # END-TO-END validation: model vs ASS+TR, capped AND uncapped
python code/cross_sections/param_visualization.py [men|women|both] [csv] [suffix]   # cohort×age parameter heatmaps
```

**Stage 1** (`estimate_cross_sections.py`) implements the `smoothed-constrained-mle` skill:
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
  (`output/cross_sections/rho_sweep_ass_tr_ratios.png`), which is also the recipe for retuning it:

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

- **Code and outputs are organized into three parallel sections**, each a subfolder of
  both `code/` and `output/`: `data_import/` (build the shared DB from raw CSV + saved
  HTML), `ssa_replication/` (replicate Compson 2012 RS Note figures/tables), and
  `cross_sections/` (fit per-cell earnings distributions by year × sex × age — dPlN,
  lognormal mixture — in one joint solve that smooths along age and pins each year's uncapped
  mean to the ASS benchmark, then extrapolate off the data edges).
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
