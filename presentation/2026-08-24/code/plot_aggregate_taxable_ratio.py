#!/usr/bin/env python
"""Aggregate taxable earnings relative to the ASS benchmark, 1951-2006 -- the 08_24 slide
figure comparing three series against ASS aggregate taxable earnings (wage + SE):

  o  EPUF / ASS        raw 1% microdata x100: the EPUF-vs-Supplement data gap (~2-4%)
  s  our model / ASS   this repo's extrapolated surface aggregated by the project_vu
                       employment panel x ASS/TR worker totals
                       (output/cross_sections/agg_taxable_emp_weighted.csv, written by
                       code/cross_sections/agg_tax_emp_weighted.py -- rerun that first if
                       the parameter surface changed)
  ^  e9f purple / ASS  project_vu's simulated aggregate (agg_taxable_earnings_extrap.parquet).
                       Pinned to ASS by construction through 1956 (the e7 scaling regime);
                       free per-year fits from 1957, swinging -12% (1978) to +5% (2001).

The purple parquet is in 2013 USD. Its own deflator is recovered from the file itself:
tax_max_2013(y) / nominal taxable max(y) (ASS workbook) = their CPI factor per year --
matches the TR2023 Adjusted CPI to 4 decimals on the 1970+ overlap, and extends it back to
1937, which is what lets the purple line reach 1951 here.

Run from the project root:  python presentation/2026-08-24/code/plot_aggregate_taxable_ratio.py
  -> presentation/2026-08-24/figures/aggregate_taxable_ratio_1951_2006.pdf (+ .png)
"""
import sys

sys.path[:0] = ["code/cross_sections", "code/cross_sections/plots"]   # run from project root
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from benchmarks import ass_taxable
from aggregates import epuf_direct
from plot_agg_tax_total import C_BENCH, C_EPUF, C_MODEL   # figure palette only

VU = ("/Users/jr2728/Dropbox/GZ SSec RA share 2023-present/project_vu - Copy (2)/"
      "data/intermediate/")
OURS_CSV = "output/cross_sections/agg_taxable_emp_weighted.csv"
OUT = "presentation/2026-08-24/figures/aggregate_taxable_ratio_1951_2006"
YEARS = list(range(1951, 2007))


def main():
    purple = pd.read_parquet(VU + "agg_taxable_earnings_extrap.parquet").set_index("year")
    assx = pd.read_excel("raw_data/annual_statistical_supplement.xlsx", sheet_name="data")
    tmax = {int(r.year): float(r.taxable_maximum)
            for r in assx.dropna(subset=["taxable_maximum"]).itertuples()}
    # their 2013$/nominal deflator, backed out of the purple file's own cap column
    f = {y: purple.loc[y, "tax_max_2013"] / tmax[y] for y in purple.index if y in tmax}

    ass, ep = ass_taxable(), epuf_direct()
    ours = pd.read_csv(OURS_CSV).set_index("year")

    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.axhline(1.0, color=C_BENCH, lw=1.2)
    ax.plot(YEARS, [ep[y] / ass[y] for y in YEARS], color=C_EPUF, lw=1.3,
            marker="o", ms=4, markevery=2, label="EPUF / ASS")
    ax.plot(YEARS, [ours.loc[y, "ratio"] for y in YEARS], color=C_MODEL, lw=1.3,
            marker="s", ms=4, markevery=2, label="our model / ASS")
    ax.plot(YEARS, [purple.loc[y, "agg_earn_total"] / f[y] / (ass[y] * 1e6) for y in YEARS],
            color="purple", lw=1.3, marker="^", ms=4.5, markevery=2,
            label="e9f purple / ASS")
    ax.set_xlabel("year")
    ax.set_ylabel("ratio to ASS benchmark")
    ax.set_title("Aggregate taxable earnings relative to ASS, 1951–2006 (1.0 = exact)")
    ax.set_xlim(1950, 2007)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT + ".pdf")
    fig.savefig(OUT + ".png", dpi=150)
    print(f"wrote {OUT}.pdf and .png")


if __name__ == "__main__":
    main()
