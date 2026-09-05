#!/usr/bin/env python
"""Published and projected SSA aggregate series -- the external benchmarks every part of
this section is measured against. Workbooks only: no EPUF, no duckdb, no matplotlib.

This module exists because the same published quantities used to be loaded independently
in three places, and TWO OF THEM WERE THE SAME NUMBER:

  * crosssec_mle.ass_uncapped_target()   -- the per-year uncapped mean the joint solve PINS
  * extrapolate_params.ass_total_earnings()/ass_workers() -- the pre-1951 alpha calibration TARGET
  * plot_agg_tax_total.ass_total()/ass_workers()          -- what VALIDATES both of the above

The first two are `ass_uncapped_per_worker()` below, computed two different ways from the
same two columns and reconciled only by a comment. If they ever drifted, the estimator would
be constrained to one quantity and validated against another -- a silent, circular error that
no output would reveal. One definition, one place.

Units, stated once because the old copies disagreed:
  aggregate earnings      $M   (millions of dollars, the workbook's own unit)
  worker counts           persons
  per-worker earnings     $
"""
from functools import lru_cache
from pathlib import Path

import pandas as pd

ASS_XLSX = Path("raw_data/annual_statistical_supplement.xlsx")
TR_XLSX  = Path("raw_data/tr2023_summary.xlsx")
MUSD     = 1e6                 # dollars per $M, for callers converting between the two


@lru_cache(maxsize=1)
def _ass():
    """The curated Annual Statistical Supplement sheet. Cached: several callers here read
    it, and openpyxl parsing dominates their runtime."""
    return pd.read_excel(ASS_XLSX, sheet_name="data")


def ass_workers():
    """Covered-worker counts (persons) per year, annual 1937-2022 -- the worker base
    underlying the ASS earnings aggregates. Weighting the model by these over the published
    span (TR covered workers only for the 2023+ projection) makes model/benchmark a
    denominator-matched per-worker comparison, and lets the model reach back to 1937."""
    d = _ass()
    return {int(y): float(v) * 1e3 for y, v in zip(d["year"], d["num_wrk"]) if pd.notna(v)}


def ass_taxable():
    """Aggregate TAXABLE (capped) earnings ($M) per year: wage + self-employed, annual
    1937-2022 (1980 ASS Table 30 pre-1951, 2023 ASS Table 4.B2 for 1951+). Replaces the
    sparse Table-4.B1 series (only 1937/40/45/50 before 1951); reconciles to it exactly
    where they overlap."""
    d = _ass()
    tax = d["aggearn_tax_wage"].fillna(0) + d["aggearn_tax_se"].fillna(0)
    return {int(y): float(v) for y, v in zip(d["year"], tax) if pd.notna(v)}


def ass_total():
    """Aggregate TOTAL (UNCAPPED) covered earnings ($M) per year: wage + self-employed,
    annual 1937-2022. The uncapped counterpart to ass_taxable. The taxable comparison hides
    tail-shape error behind the cap (a too-heavy upper tail still matches taxable earnings
    once the cap clips it); the uncapped one exposes it directly."""
    d = _ass()
    tot = d["aggearn_tot_wage"].fillna(0) + d["aggearn_tot_se"].fillna(0)
    return {int(y): float(v) for y, v in zip(d["year"], tot) if v > 0}


def ass_uncapped_per_worker():
    """ASS average UNCAPPED earnings per covered worker ($/worker) per year -- aggearn_tot
    over num_wrk. THE quantity the pipeline is pinned to, in both directions:

      * crosssec_mle stage 3 root-finds the per-year eta so the fitted surface's
        composition-weighted E[X] hits this (1951-2006);
      * extrapolate_params.calibrate_alpha_scale root-finds men's pre-1951 alpha scale
        against the same target (1937-1950);
      * plot_agg_tax_total's uncapped row plots the model against it.

    It is the mean the censored MLE cannot see, because the mass above the taxable maximum
    is exactly what the top-code removes. Years with no earnings total or no worker count
    are absent (in practice num_wrk is present and positive for every ASS year)."""
    tot, cov = ass_total(), ass_workers()
    return {y: tot[y] * MUSD / cov[y] for y in tot if y in cov and cov[y] > 0}


def trustees():
    """2023 OASDI Trustees Report, intermediate assumptions:
    (covered workers (persons), average wage index, taxable payroll ($M))."""
    d = pd.read_excel(TR_XLSX, sheet_name="Intermediate", header=0)
    d = d.rename(columns={d.columns[0]: "year"})
    d["year"] = d["year"].astype("Int64")

    def col(name, scale=1.0):
        sub = d.dropna(subset=[name])[["year", name]]
        return {int(r.year): float(r._2) * scale for r in sub.itertuples()}

    return (col("Thousands of Covered Workers", 1e3),
            col("Average Wage Index"),
            col("Taxable Payroll, Billions", 1e3))          # billions -> millions


def combined_benchmark(ass, trpay):
    """One spliced published/projected series: the ASS taxable-earnings series where it
    exists (annual 1937-2022), the TR taxable-payroll projection afterward. The two agree
    closely in their overlap, so the splice is near-seamless. Returns (benchmark, last ASS
    year)."""
    ass_last = max(ass)
    B = dict(trpay)
    B.update(ass)                    # ASS overrides TR in the overlap (1960-2022)
    return B, ass_last
