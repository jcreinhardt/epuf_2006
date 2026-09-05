#!/usr/bin/env python
"""WHERE the EPUF-vs-GKSW wedge lives: the same quantile computed on both sides, cell by
cell, and the log gap decomposed by quantile x year and by quantile x age. No model
anywhere -- this is the data-vs-data companion to plot_guv_quantile_validation.py, which
answers "how far apart" for complete cohorts; this one answers "why", by showing the
SHAPE of the gap. Three shapes are possible and they are mutually exclusive:

  - a deflator / price-index mistake is ONE SCALAR PER YEAR: every quantile and every
    age in that year would be off by the same log amount, tracking the CPI-vs-PCE
    line drawn for reference (+0.25 log points in 1960 -> 0 in 2013);
  - a screen mismatch (threshold coded differently on one side) moves ONLY the
    quantiles near the threshold, identically at every age;
  - a sample-composition / earnings-concept wedge is quantile- AND age-specific.

Measured (1957-2006, GKSW's own PCE matrix and screen on both sides), the gap is the
third kind, unambiguously:

  - it is BOTTOM-HEAVY: men's p10 sits 15-20% below GKSW, p25 ~10%, p50 5-7%, p75 ~4%;
    women's p50 and p75 are AT or slightly ABOVE GKSW while their p10 is 4-7% below;
  - it GROWS WITH AGE: men's p10 gap is ~0 at 25-30 and -25 to -33% at 50-55;
  - it does NOT follow the CPI/PCE line (men's p75 gap is flat at -4% from 1973 to 2006
    while that line falls from 0.21 to 0.02).

That is the signature of extra LOW earners on the EPUF side, concentrated among older
men -- exactly who the GKSW sample excludes: EPUF `earnings` is ALL covered earnings
(wages in every covered sector PLUS taxable self-employment income), whereas the GKSW
files are Kopczuk-Saez-Song's "commerce and industry" W-2 wages only: no
self-employment income at all, and no agriculture, private households, hospitals,
educational/social services, religious organisations or public administration (~30% of
private employment; the Supplement's Table 4.B2 puts self-employed workers at 7-11% of
covered workers with mean taxable earnings 45-80% of the wage-worker mean, rising with
age). Both are 1% random samples of SSNs, so sampling error (cells of 4-17k) is <1% at a
quantile and cannot produce a 5-30% gap; the FRAMES are near-identical, the SAMPLE
SELECTION is not, and EPUF carries no industry or self-employment flag with which to
reproduce it.

Two natural experiments in the GKSW files confirm the direction, both breaks on the
GKSW side with EPUF flat:
  - 2005: the paper builds 1957-2004 from the KSS sample and extends 2004-2013 "using
    the underlying data from the MEF". At 2005 GKSW's p10 drops 8% (men) / 17% (women)
    in one year and lands ON TOP of EPUF's (gap +0.03 / +0.18 at p10; p25 within 1%);
  - 1978: the switch from quarterly LEED reports to W-2 Box 1 lifts GKSW's men's p10
    by 10% against EPUF's 5%, widening the gap by ~5 log points.
Neither can be a property of EPUF, whose extract is one file built one way.

Consequences for the pipeline: the level wedge is a data-concept gap and is expected;
sdlog/skewlog/kurtlog and the within-year SHAPE are the comparable quantities. The
sel0 screen and the deflator are verified identical on both sides at every run by
guv_targets.check_guv_conventions().

EPUF side per (year, sex, age): the exact sel0 screen, empirical quantiles
(quantile_disc = the do-file's r[ceil(q*N)]), deflated per cell with GKSW's PCE
matrix; a quantile within HIGH_MARGIN of the cap is censored and dropped. The by-year
panel averages over ages 25-55 and requires ALL 31 ages uncensored (so men's p50
starts in 1966, p75 in 1973); the by-age panel averages over 1980-2006, where every
plotted quantile clears the cap at every age.

  python code/cross_sections/plots/plot_guv_gap_signature.py
    -> output/cross_sections/guv_gap_cells.csv            per-cell values and log gaps
    -> output/cross_sections/plots/guv_gap_signature.pdf (+ .png)
"""
import sys
from pathlib import Path

sys.path[:0] = ["code/cross_sections", "code/cross_sections/plots"]   # run from project root
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import crosssec_fit as cf
from guv_targets import (load_guv, load_deflator, check_guv_conventions, _PCE_GKSW,
                         BASE_YEAR)
from plot_guv_quantile_validation import epuf_quantiles, YEARS, AGES

OUT_DIR  = Path("output/cross_sections")
PLOT_DIR = Path("output/cross_sections/plots")
SHOW     = ["p10", "p25", "p50", "p75"]       # p90/p98 never clear the cap for men
BYAGE_YEARS = (1980, 2006)
BREAKS = {1978: "GKSW: quarterly reports -> W-2", 2005: "GKSW: KSS sample -> raw MEF"}

# GKSW's own CPI-U matrix (merge_reshape_25mar2015_1pc.do, 1947-2014), reference only:
# the log gap a CPI-vs-PCE mix-up WOULD produce, one scalar per year.
_CPI_GKSW = [22.332, 24.045, 23.809, 24.063, 25.973, 26.567, 26.768, 26.865, 26.796,
             27.191, 28.113, 28.881, 29.15, 29.585, 29.902, 30.253, 30.633, 31.038,
             31.528, 32.471, 33.375, 34.792, 36.683, 38.842, 40.483, 41.808, 44.425,
             49.317, 53.825, 56.933, 60.617, 65.242, 72.583, 82.383, 90.933, 96.533,
             99.583, 103.933, 107.6, 109.692, 113.617, 118.275, 123.942, 130.658,
             136.167, 140.308, 144.475, 148.225, 152.383, 156.858, 160.525, 163.008,
             166.583, 172.192, 177.042, 179.867, 184, 188.908, 195.267, 201.558,
             207.344, 215.254, 214.565, 218.076, 224.93, 229.6, 232.962, 236.712]


def cpi_vs_pce(year):
    """log(real-2013$ under CPI / real-2013$ under PCE) for a nominal amount of `year`."""
    i, b = year - 1947, BASE_YEAR - 1947
    return np.log((_CPI_GKSW[b] / _CPI_GKSW[i]) / (_PCE_GKSW[b] / _PCE_GKSW[i]))


def cell_gaps():
    guv = load_guv()
    ep = epuf_quantiles()
    fac = ep["year"].map(load_deflator())
    for c in SHOW:
        ep[f"{c}_cens"] = ep[c] >= ep["taxmax"] - cf.HIGH_MARGIN     # on nominal values
        ep[c] = ep[c] * fac
    m = guv[["year", "sex", "age", "cohort"] + SHOW].rename(
        columns={c: f"{c}_guv" for c in SHOW}).merge(
        ep[["year", "sex", "age", "n"] + SHOW + [f"{c}_cens" for c in SHOW]].rename(
            columns={c: f"{c}_epuf" for c in SHOW}),
        on=["year", "sex", "age"], how="inner")
    for c in SHOW:
        m[f"gap_{c}"] = np.where(m[f"{c}_cens"], np.nan,
                                 np.log(m[f"{c}_epuf"] / m[f"{c}_guv"]))
    return m


def main():
    check_guv_conventions()
    m = cell_gaps()
    m.to_csv(OUT_DIR / "guv_gap_cells.csv", index=False)
    nages = AGES[1] - AGES[0] + 1
    print(f"{len(m)} matched cells, years {YEARS[0]}-{YEARS[1]}, ages {AGES[0]}-{AGES[1]}")

    # by year: mean over ages, only where all 31 ages are uncensored for that quantile
    def year_mean(g):
        out = {}
        for c in SHOW:
            out[c] = g[f"gap_{c}"].mean() if g[f"{c}_cens"].sum() == 0 and len(g) == nages else np.nan
        return pd.Series(out)
    by_year = m.groupby(["sex", "year"]).apply(year_mean).reset_index()

    # by age: mean over BYAGE_YEARS, requiring every cell uncensored
    w = m[(m["year"] >= BYAGE_YEARS[0]) & (m["year"] <= BYAGE_YEARS[1])]
    def age_mean(g):
        return pd.Series({c: g[f"gap_{c}"].mean() if g[f"{c}_cens"].sum() == 0 else np.nan
                          for c in SHOW})
    by_age = w.groupby(["sex", "age"]).apply(age_mean).reset_index()

    pd.set_option("display.width", 200)
    m["decade"] = (m["year"] // 10) * 10
    print("\nmean log(EPUF/GKSW) by decade (cells uncensored at that quantile):")
    print(m.groupby(["sex", "decade"])[[f"gap_{c}" for c in SHOW]].mean().round(3).to_string())
    print("\nmen's p10 gap by decade x age group:")
    mm = m[m["sex"] == 1].copy()
    mm["ages"] = pd.cut(mm["age"], [24, 30, 35, 40, 45, 50, 55])
    print(mm.pivot_table(index="decade", columns="ages", values="gap_p10",
                         aggfunc="mean", observed=True).round(3).to_string())
    for yb in BREAKS:
        for sex, nm in ((1, "men"), (2, "women")):
            a = m[(m["sex"] == sex) & (m["year"] == yb - 1)]
            b = m[(m["sex"] == sex) & (m["year"] == yb)]
            dg = np.log(b["p10_guv"]).mean() - np.log(a["p10_guv"]).mean()
            de = np.log(b["p10_epuf"]).mean() - np.log(a["p10_epuf"]).mean()
            print(f"{yb - 1}->{yb} {nm:5s} p10: GKSW {dg:+.3f}, EPUF {de:+.3f}  ({BREAKS[yb]})")
    plot(by_year, by_age)


def plot(by_year, by_age):
    # fixed categorical order p10 -> p75; the first three are the repo's validated slots
    COL = {"p10": "#2a78d6", "p25": "#eb6834", "p50": "#1e9e64", "p75": "#8e5bd3"}
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharey="row")
    for r, (sex, name) in enumerate(((1, "men"), (2, "women"))):
        ax = axes[r, 0]
        d = by_year[by_year["sex"] == sex]
        for c in SHOW:
            ax.plot(d["year"], d[c], color=COL[c], lw=1.8, label=c)
        ax.plot(d["year"], [cpi_vs_pce(y) for y in d["year"]], color="0.45", lw=1.4,
                ls=":", label="what a CPI-vs-PCE mix-up would look like")
        for yb, txt in BREAKS.items():
            ax.axvline(yb, color="0.6", lw=0.9, ls="--")
            if r == 0:                      # label once; the women's row has no room
                ax.text(yb + 0.4, 0.28, f"{yb}: {txt}", fontsize=8, color="0.35",
                        va="top", rotation=90)
        ax.axhline(0, color="0.3", lw=0.8)
        ax.set_title(f"{name}: by year, averaged over ages {AGES[0]}-{AGES[1]}", fontsize=11)
        ax.set_xlabel("year")

        ax = axes[r, 1]
        d = by_age[by_age["sex"] == sex]
        for c in SHOW:
            ax.plot(d["age"], d[c], color=COL[c], lw=1.8, marker="o", ms=3, label=c)
        ax.axhline(0, color="0.3", lw=0.8)
        ax.set_title(f"{name}: by age, averaged over {BYAGE_YEARS[0]}-{BYAGE_YEARS[1]}",
                     fontsize=11)
        ax.set_xlabel("age")
    for ax in axes.flat:
        ax.grid(True, lw=0.4, alpha=0.4)
        ax.tick_params(labelsize=9)
    axes[0, 0].set_ylabel("log(EPUF quantile / GKSW quantile)")
    axes[1, 0].set_ylabel("log(EPUF quantile / GKSW quantile)")
    axes[0, 0].set_ylim(-0.35, 0.30)
    h, l = axes[0, 0].get_legend_handles_labels()
    axes[0, 1].legend(h, l, fontsize=9, frameon=False, loc="lower left")
    fig.suptitle("EPUF vs GKSW sel0 quantiles, same screen and deflator on both sides: "
                 "the gap is bottom-heavy and age-increasing,\nnot a per-year scalar -- "
                 "a sample-composition wedge (covered wages + self-employment vs "
                 "commerce-and-industry W-2 wages), not deflation", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    for ext in ("pdf", "png"):
        fig.savefig(PLOT_DIR / f"guv_gap_signature.{ext}", dpi=150)
    plt.close(fig)
    print(f"wrote {PLOT_DIR}/guv_gap_signature.pdf (+ .png)")


if __name__ == "__main__":
    main()
