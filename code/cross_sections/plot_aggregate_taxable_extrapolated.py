#!/usr/bin/env python
"""Validate the EXTRAPOLATED parameter surfaces against ONE combined published/projected
benchmark: ASS Table 4.B1 where it exists (aggregate taxable earnings, 1937-2007) spliced
onto the 2023 OASDI Trustees Report intermediate projection (Taxable Payroll) afterward.
The two agree to <2.5% in their 1970-2007 overlap, so the splice is near-seamless.

Two series are compared to that benchmark: the raw EPUF empirical aggregate (100 x
SUM(earnings), the 1% microdata scaled to population) and our extrapolated model. EPUF
itself runs ~2-3% below ASS (a known EPUF-vs-Supplement gap), so the model -- which is
anchored to EPUF -- inherits that offset; the model tracking EPUF is the real success
criterion, and the model/benchmark and EPUF/benchmark ratios sitting on top of each other
in-sample is what shows it.

The model determines the SHAPE of each cell's earnings distribution -- hence mean
taxable earnings per covered worker -- not how many workers there are. The worker weight
is the EPUF empirical joint (sex, single-year age) composition of positive earners scaled
by the TR's own worker projection:

    workers(sex, age, y) = TR covered workers(y)  x  comp(sex, age, y)

comp is the OBSERVED per-year EPUF composition where we have microdata (1951-2004), held
fixed at the two data edges off-sample: the 1951-1955 average before 1951 and the
2000-2004 average after 2004 (the only composition we can carry into years with no EPUF;
the TR has no sex/age breakdown). This matters because the composition shifted hard --
women were 34% of earners in 1951 vs 48% in 2004 -- so forcing the 2000-04 mix onto the
early years (the old design) over-weighted women and misfit the in-sample aggregate.
Because comp sums to 1, the model's worker TOTAL equals the TR's every year and model / TR
is a pure comparison of taxable earnings PER WORKER: the extrapolated distribution vs SSA's
wage assumptions. The taxable maximum caps every mean: the EPUF top-code (1951-2006),
$3,000 before, and AWI-indexed off 2006 forward (taxmax(y) = taxmax(2006) * AWI(y)/AWI(2006)).

A dashed diagnostic overlays the OLD fixed-2000-04-composition aggregate, so the in-sample
gain from using observed composition is visible directly.

  python code/cross_sections/plot_aggregate_taxable_extrapolated.py
    -> output/cross_sections/aggregate_taxable_extrapolated.pdf (+ .png)
"""
import io
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

import crosssec_fit as cf
from plot_aggregate_taxable import model_mean_taxable   # reuse E[min(exp Y, taxmax)]

PARAMS = Path("output/cross_sections/cross_section_params_extrapolated.csv")
TR_XLSX = Path("raw_data/tr2023_summary.xlsx")
DB      = cf.DB
MUSD    = 1e6
TAXMAX_1937_50 = 3000.0
ANCHOR = (2000, 2004)     # forward composition: fixed at this window (last observed edge)
BACK   = (1951, 1955)     # pre-1951 composition: fixed at the earliest observed edge
DATA_LAST = 2004          # observed per-year composition used through here; fixed after


def _duck(q):
    return subprocess.run(["duckdb", DB, "-c", q], capture_output=True, text=True,
                          check=True).stdout


def trustees():
    """TR intermediate: covered workers (persons), AWI, taxable payroll (millions USD)."""
    d = pd.read_excel(TR_XLSX, sheet_name="Intermediate", header=0)
    d = d.rename(columns={d.columns[0]: "year"})
    d["year"] = d["year"].astype("Int64")
    cov = d.dropna(subset=["Thousands of Covered Workers"])
    awi = d.dropna(subset=["Average Wage Index"])
    pay = d.dropna(subset=["Taxable Payroll, Billions"])
    return (
        {int(r.year): float(r._2) * 1e3 for r in
         cov[["year", "Thousands of Covered Workers"]].itertuples()},
        {int(r.year): float(r._2) for r in awi[["year", "Average Wage Index"]].itertuples()},
        {int(r.year): float(r._2) * 1e3 for r in
         pay[["year", "Taxable Payroll, Billions"]].itertuples()},   # billions -> millions
    )


def taxmax_series(years, awi):
    """Taxable maximum: $3,000 (<=1950), EPUF top-code (1951-2006), AWI-indexed off 2006."""
    out = _duck("COPY (SELECT year, MAX(earnings) FROM annual WHERE earnings>0 "
                "GROUP BY year) TO '/dev/stdout' (FORMAT CSV, HEADER FALSE);")
    tmax = {int(y): float(v) for y, v in (l.split(",") for l in out.strip().splitlines())}
    base06 = tmax[2006]
    tm = {}
    for y in years:
        if y in tmax:
            tm[y] = tmax[y]
        elif y <= 1950:
            tm[y] = TAXMAX_1937_50
        else:
            tm[y] = base06 * awi[y] / awi[2006]
    return tm


def epuf_direct():
    """Raw EPUF empirical aggregate taxable earnings ($M) per year = 100 x SUM(earnings)
    over positive earners (1% sample -> population; earnings are already top-coded at the
    taxable max, so their sum IS taxable earnings). The observed benchmark from microdata."""
    out = _duck("COPY (SELECT year, 100*SUM(earnings)/1e6 FROM annual WHERE earnings>0 "
                "GROUP BY year) TO '/dev/stdout' (FORMAT CSV, HEADER FALSE);")
    return {int(y): float(v) for y, v in (l.split(",") for l in out.strip().splitlines())}


def combined_benchmark(ass, trpay):
    """One spliced published/projected series: ASS Table 4.B1 where it exists (1937-2007),
    the TR 2023 taxable-payroll projection afterward. Returns (benchmark, last ASS year)."""
    ass_last = max(ass)
    B = dict(trpay)
    B.update(ass)                    # ASS overrides TR in the overlap (1970-2007)
    return B, ass_last


def epuf_counts():
    """Positive-earner counts by (year, sex, single-year age), 1951-2006."""
    q = ("COPY (SELECT a.year, d.sex, (a.year-d.yob) AS age, COUNT(*) AS n "
         "FROM annual a JOIN demographic d USING(id) "
         "WHERE a.earnings>0 AND d.sex IN (1,2) AND d.yob IS NOT NULL "
         "AND (a.year-d.yob) BETWEEN 15 AND 77 GROUP BY 1,2,3) "
         "TO '/dev/stdout' (FORMAT CSV, HEADER TRUE);")
    return pd.read_csv(io.StringIO(_duck(q)))


def joint_share(counts, y0, y1):
    """The (sex, age) joint share of positive earners averaged over [y0, y1]. Sums to 1."""
    w = counts[(counts.year >= y0) & (counts.year <= y1)]
    tot = w["n"].sum()
    return {(int(r.sex), int(r.age)): r.n / tot for r in
            w.groupby(["sex", "age"], as_index=False)["n"].sum().itertuples()}


def per_year_shares(counts):
    """True per-year (sex, age) share -- the observed in-sample composition."""
    sh = {}
    for y, g in counts.groupby("year"):
        tot = g["n"].sum()
        sh[int(y)] = {(int(r.sex), int(r.age)): r.n / tot for r in g.itertuples()}
    return sh


def composition_by_year(counts, years):
    """Per-year (sex, age) composition for the model: the OBSERVED EPUF share each year
    over 1951-DATA_LAST, held fixed at the 1951-1955 average before 1951 and at the
    2000-2004 average after DATA_LAST (the two data edges we can carry off-sample).
    Returns (comp_by_year, back_share, fwd_share)."""
    back = joint_share(counts, *BACK)          # pre-1951 fallback (earliest observed edge)
    fwd  = joint_share(counts, *ANCHOR)        # post-2004 fallback (latest observed edge)
    per  = per_year_shares(counts)
    comp = {}
    for y in years:
        if y <= BACK[0] - 1:
            comp[y] = back
        elif y <= DATA_LAST:
            comp[y] = per.get(y, fwd)          # observed composition, verbatim
        else:
            comp[y] = fwd
    return comp, back, fwd


def model_means(params, taxmax):
    """Model mean taxable ($) per (year, sex, age), for the years present in `taxmax`."""
    df = pd.read_csv(params)
    means = {}
    for r in df.to_dict("records"):
        y = int(r["year"])
        if y in taxmax:
            means[(y, int(r["sex"]), int(r["age"]))] = model_mean_taxable(r, taxmax[y])
    return means


def agg_fixed(means, taxmax, comp, cov):
    """Aggregate taxable ($M) with fixed 2000-04 composition scaled by TR workers(y)."""
    agg = {}
    for y in taxmax:
        s = 0.0
        for (sex, age), frac in comp.items():
            mt = means.get((y, sex, age))
            if mt is not None and np.isfinite(mt):
                s += mt * cov[y] * frac
        agg[y] = s / MUSD
    return agg


def agg_composed(means, taxmax, comp_by_year, cov):
    """Aggregate taxable ($M) with a per-year (sex, age) composition x TR workers(y)."""
    agg = {}
    for y in taxmax:
        comp = comp_by_year.get(y)
        if comp is None or y not in cov:
            continue
        s = 0.0
        for (sex, age), frac in comp.items():
            mt = means.get((y, sex, age))
            if mt is not None and np.isfinite(mt):
                s += mt * cov[y] * frac
        agg[y] = s / MUSD
    return agg


def main():
    cov, awi, trpay = trustees()
    df = pd.read_csv(PARAMS)
    years = sorted(set(df["year"]) & set(cov))          # model x TR-covered-workers overlap
    taxmax = taxmax_series(years, awi)
    counts = epuf_counts()
    comp_by_year, back, fwd = composition_by_year(counts, years)
    y_lo, y_hi = BACK[0], DATA_LAST                      # observed-composition window

    means = model_means(PARAMS, taxmax)
    model = agg_composed(means, taxmax, comp_by_year, cov)   # observed comp in-sample, fixed off-sample

    out = _duck("COPY (SELECT year, reported_taxable_musd FROM supplement_4b1 "
                "WHERE reported_taxable_musd IS NOT NULL) TO '/dev/stdout' (FORMAT CSV, HEADER FALSE);")
    ass = {int(y): float(v) for y, v in (l.split(",") for l in out.strip().splitlines())}
    bench, ass_last = combined_benchmark(ass, trpay)        # ASS pre-2008, TR after
    epuf = epuf_direct()                                    # raw 1% microdata aggregate

    yr = np.array(years)
    m = np.array([model[y] for y in years])
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.4))

    # ---- levels (log y, trillions) ----
    by = sorted(bench); ey = sorted(epuf)
    ax1.plot(by, [bench[y] / 1e6 for y in by], color="k", lw=2.2,
             label=f"benchmark: ASS 4.B1 (≤2007) + TR 2023 (after)")
    ax1.plot(ey, [epuf[y] / 1e6 for y in ey], color="C0", lw=1.4, marker="o", ms=2.5,
             label="EPUF (raw 1% microdata ×100)")
    ax1.plot(yr, m / 1e6, color="C3", lw=1.9, ls=":", label="extrapolated model")
    ax1.axvspan(y_lo, y_hi, color="grey", alpha=0.08)
    ax1.axvline(ass_last, color="grey", lw=0.8, ls="--")
    ax1.set_yscale("log"); ax1.set_ylabel("aggregate taxable earnings ($ trillions)")
    ax1.set_xlabel("year"); ax1.set_title("Levels (log scale)")
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax1.legend(frameon=False, fontsize=8.5, loc="upper left")

    # ---- ratio to the combined benchmark ----
    ax2.axhline(1.0, color="k", lw=1.0)
    xe = [y for y in ey if y in bench]; re = [epuf[y] / bench[y] for y in xe]
    xm = [y for y in years if y in bench]; rm = [model[y] / bench[y] for y in xm]
    ax2.plot(xe, re, color="C0", lw=1.6, marker="o", ms=2.5, label="EPUF / benchmark")
    ax2.plot(xm, rm, color="C3", lw=1.8, ls=":", label="model / benchmark")
    ax2.axvspan(y_lo, y_hi, color="grey", alpha=0.08, label="observed-composition years")
    ax2.axvline(ass_last, color="grey", lw=0.8, ls="--")
    ax2.set_ylabel("series / combined benchmark"); ax2.set_xlabel("year")
    ax2.set_title("Relative to benchmark (1.0 = exact)")
    ax2.legend(frameon=False, fontsize=8.5, loc="best")

    fig.suptitle("Aggregate taxable earnings: EPUF & extrapolated model vs combined ASS+TR benchmark",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    outp = "output/cross_sections/aggregate_taxable_extrapolated"
    fig.savefig(outp + ".pdf"); fig.savefig(outp + ".png", dpi=150); plt.close(fig)

    print(f"{'year':>4} {'model($M)':>13} {'EPUF($M)':>13} {'bench($M)':>13} "
          f"{'mdl/bn':>7} {'epf/bn':>7}")
    for y in years:
        if y % 10 == 0 or y in (years[0], years[-1], 2004, 2006, ass_last):
            e = epuf.get(y); b = bench.get(y)
            print(f"{y:>4} {model[y]:>13,.0f} {e if e else 0:>13,.0f} {b if b else 0:>13,.0f} "
                  f"{model[y]/b if b else 0:>7.3f} {e/b if (e and b) else 0:>7.3f}")
    print(f"\nwrote {outp}.pdf and .png")


if __name__ == "__main__":
    main()
