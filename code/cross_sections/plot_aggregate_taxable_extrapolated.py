#!/usr/bin/env python
"""Validate the EXTRAPOLATED parameter surfaces against published aggregate taxable
earnings: ASS Table 4.B1 (1937-2007) and the 2023 OASDI Trustees Report intermediate
projection (Taxable Payroll, 1970-2099). The two benchmarks span the target range and
agree to <2.5% where they overlap.

The model determines the SHAPE of each cell's earnings distribution -- hence mean
taxable earnings per covered worker -- not how many workers there are. So per the
stage-3 design, the worker weight is anchored entirely at the recent data edge and
scaled by the TR's own worker projection:

    workers(sex, age, y) = TR covered workers(y)  x  comp_2000-04(sex, age)

comp_2000-04 is the EPUF empirical joint (sex, single-year age) composition of positive
earners averaged over 2000-2004 -- the fixed 2000-04 gender ratio and age profile -- so
the model's worker TOTAL equals the TR's every year by construction and model / TR is a
pure comparison of taxable earnings PER WORKER: the extrapolated distribution vs SSA's
wage assumptions. The taxable maximum caps every mean: the EPUF top-code (1951-2006),
$3,000 before, and AWI-indexed off 2006 forward (taxmax(y) = taxmax(2006) * AWI(y)/AWI(2006)).

A control overlays the iterated (pre-extrapolation) params under the model's TRUE
per-year EPUF composition, in-sample -- so any in-sample model/benchmark gap splits into
the fixed-composition cost (control vs model) and the distribution-shape fit (control vs ASS).

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
ITER   = Path("output/cross_sections/cross_section_params_iterated.csv")
TR_XLSX = Path("raw_data/tr2023_summary.xlsx")
DB      = cf.DB
MUSD    = 1e6
TAXMAX_1937_50 = 3000.0
ANCHOR = (2000, 2004)


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


def epuf_counts():
    """Positive-earner counts by (year, sex, single-year age), 1951-2006."""
    q = ("COPY (SELECT a.year, d.sex, (a.year-d.yob) AS age, COUNT(*) AS n "
         "FROM annual a JOIN demographic d USING(id) "
         "WHERE a.earnings>0 AND d.sex IN (1,2) AND d.yob IS NOT NULL "
         "AND (a.year-d.yob) BETWEEN 15 AND 77 GROUP BY 1,2,3) "
         "TO '/dev/stdout' (FORMAT CSV, HEADER TRUE);")
    return pd.read_csv(io.StringIO(_duck(q)))


def fixed_composition(counts):
    """The 2000-2004 joint (sex, age) share of positive earners -- one composition for
    all years (the fixed gender ratio x age profile). Sums to 1 over cells."""
    w = counts[(counts.year >= ANCHOR[0]) & (counts.year <= ANCHOR[1])]
    tot = w["n"].sum()
    return {(int(r.sex), int(r.age)): r.n / tot for r in
            w.groupby(["sex", "age"], as_index=False)["n"].sum().itertuples()}


def per_year_shares(counts):
    """True per-year (sex, age) share -- for the in-sample control weighting."""
    sh = {}
    for y, g in counts.groupby("year"):
        tot = g["n"].sum()
        sh[int(y)] = {(int(r.sex), int(r.age)): r.n / tot for r in g.itertuples()}
    return sh


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


def agg_peryear(means, taxmax, shares, cov):
    """Aggregate taxable ($M) with the true per-year EPUF composition x TR workers(y)."""
    agg = {}
    for y in taxmax:
        if y not in shares:
            continue
        s = 0.0
        for (sex, age), frac in shares[y].items():
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
    comp = fixed_composition(counts)
    shares = per_year_shares(counts)
    y_lo, y_hi = min(shares), max(shares)

    model = agg_fixed(model_means(PARAMS, taxmax), taxmax, comp, cov)
    fit_tm = {y: taxmax[y] for y in taxmax if y_lo <= y <= y_hi}
    control = agg_peryear(model_means(ITER, fit_tm), fit_tm, shares, cov)   # in-sample control

    out = _duck("COPY (SELECT year, reported_taxable_musd FROM supplement_4b1 "
                "WHERE reported_taxable_musd IS NOT NULL) TO '/dev/stdout' (FORMAT CSV, HEADER FALSE);")
    ass = {int(y): float(v) for y, v in (l.split(",") for l in out.strip().splitlines())}

    yr = np.array(years)
    m = np.array([model[y] for y in years])
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.4))

    # ---- levels (log y, trillions) ----
    ass_y = sorted(ass); tr_y = sorted(trpay)
    ax1.plot(ass_y, [ass[y] / 1e6 for y in ass_y], color="k", lw=2.0,
             label="ASS Table 4.B1 (published)")
    ax1.plot(tr_y, [trpay[y] / 1e6 for y in tr_y], color="C2", lw=2.0,
             label="TR 2023 taxable payroll (intermediate)")
    ax1.plot(yr, m / 1e6, color="C3", lw=1.7, ls=":", label="extrapolated model")
    fy = sorted(control)
    ax1.plot(fy, [control[y] / 1e6 for y in fy], color="C1", lw=1.3,
             label="iterated control (true composition)")
    ax1.axvspan(y_lo, y_hi, color="grey", alpha=0.08)
    ax1.axvline(ANCHOR[1], color="grey", lw=0.8, ls="--")
    ax1.set_yscale("log"); ax1.set_ylabel("aggregate taxable earnings ($ trillions)")
    ax1.set_xlabel("year"); ax1.set_title("Levels (log scale)")
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax1.legend(frameon=False, fontsize=8.5, loc="upper left")

    # ---- ratio to each benchmark ----
    ax2.axhline(1.0, color="k", lw=1.0)
    xa = [y for y in years if y in ass]; ra = [model[y] / ass[y] for y in xa]
    xt = [y for y in years if y in trpay]; rt = [model[y] / trpay[y] for y in xt]
    ax2.plot(xa, ra, color="k", lw=1.8, marker="o", ms=2.5, label="model / ASS")
    ax2.plot(xt, rt, color="C2", lw=1.8, marker="s", ms=2.5, label="model / TR")
    fcx = [y for y in fy if y in ass]; fc = [control[y] / ass[y] for y in fcx]
    ax2.plot(fcx, fc, color="C1", lw=1.3, label="control / ASS (true composition)")
    ax2.axvspan(y_lo, y_hi, color="grey", alpha=0.08, label="EPUF data years")
    ax2.axvline(ANCHOR[1], color="grey", lw=0.8, ls="--")
    ax2.set_ylabel("model / published benchmark"); ax2.set_xlabel("year")
    ax2.set_title("Relative to benchmark (1.0 = exact)")
    ax2.legend(frameon=False, fontsize=8.5, loc="best")

    fig.suptitle("Aggregate taxable earnings: extrapolated model vs ASS 4.B1 vs Trustees Report 2023",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    outp = "output/cross_sections/aggregate_taxable_extrapolated"
    fig.savefig(outp + ".pdf"); fig.savefig(outp + ".png", dpi=150); plt.close(fig)

    print(f"{'year':>4} {'model($M)':>13} {'ASS($M)':>13} {'TR($M)':>13} {'m/ASS':>6} {'m/TR':>6}")
    for y in years:
        if y % 10 == 0 or y in (years[0], years[-1], 2004, 2007):
            a = ass.get(y); t = trpay.get(y)
            print(f"{y:>4} {model[y]:>13,.0f} {a if a else 0:>13,.0f} {t if t else 0:>13,.0f} "
                  f"{model[y]/a if a else 0:>6.3f} {model[y]/t if t else 0:>6.3f}")
    print(f"\nwrote {outp}.pdf and .png")


if __name__ == "__main__":
    main()
