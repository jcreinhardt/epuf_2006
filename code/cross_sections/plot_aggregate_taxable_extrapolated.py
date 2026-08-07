#!/usr/bin/env python
"""Validate the EXTRAPOLATED parameter surfaces against ONE combined published/projected
benchmark: the curated Annual Statistical Supplement aggregate taxable earnings (wage +
self-employed, annual 1937-2022, from raw_data/annual_statistical_supplement.xlsx) spliced
onto the 2023 OASDI Trustees Report intermediate projection (Taxable Payroll) afterward.
The two agree closely in their overlap, so the splice is near-seamless.

Two series are compared to that benchmark: the raw EPUF empirical aggregate (100 x
SUM(earnings), the 1% microdata scaled to population) and our extrapolated model. EPUF
itself runs ~2-3% below ASS (a known EPUF-vs-Supplement gap), so the model -- which is
anchored to EPUF -- inherits that offset; the model tracking EPUF is the real success
criterion, and the model/benchmark and EPUF/benchmark ratios sitting on top of each other
in-sample is what shows it.

The model determines the SHAPE of each cell's earnings distribution -- hence mean
taxable earnings per covered worker -- not how many workers there are. The worker weight
is the EPUF empirical joint (sex, single-year age) composition of positive earners scaled
by the published covered-worker total: ASS num_wrk over 1937-2022 (the base underlying the
benchmark, so the ratio's denominators match), the TR worker projection for 2023+:

    workers(sex, age, y) = covered workers(y)  x  comp(sex, age, y)

comp is the OBSERVED per-year EPUF composition where we have microdata (1951-2004), held
fixed at the two data edges off-sample: the 1951-1955 average before 1951 and the
2000-2004 average after 2004 (the only composition we can carry into years with no EPUF;
the TR has no sex/age breakdown). This matters because the composition shifted hard --
women were 34% of earners in 1951 vs 48% in 2004 -- so forcing the 2000-04 mix onto the
early years (the old design) over-weighted women and misfit the in-sample aggregate.
Because comp sums to 1, the model's worker TOTAL equals the published covered-worker total
every year and model / benchmark is a pure comparison of taxable earnings PER WORKER: the
extrapolated distribution vs SSA's wage assumptions. The taxable maximum caps every mean: the EPUF top-code (1951-2006),
$3,000 before, and AWI-indexed off 2006 forward (taxmax(y) = taxmax(2006) * AWI(y)/AWI(2006)).

The figure is 2x2. The TOP row is the taxable (capped) comparison above. The BOTTOM row
adds the UNCAPPED check: the model's implied mean earnings per worker E[X] (analytic dPlN /
mixture mean, NO cap) vs the ASS uncapped average aggearn_tot / num_wrk, 1937-2022. This
matters because the cap HIDES tail-shape error -- a too-heavy upper tail reproduces taxable
earnings once the cap clips it, so the capped panel can sit near 1.0 while the underlying
distribution is wildly off. The uncapped panel exposes that: the model's uncapped mean runs
~1.9x ASS pre-1951 (and spikes to 3-4x in the tight-cap late-1950s/60s) before converging to
~1.0 by 1980, even though the capped ratio never strays far. Men ages ~46-73 fit alpha<=1
(an INFINITE uncapped mean -- the censored-MLE upper-tail pathology, unidentified above the
cap); the finite-cell line renormalizes over the alpha>1 cells and is thus a LOWER bound
wherever the shaded infinite-mean-worker share is positive. EPUF is absent from the uncapped
row: it is top-coded, so it has no uncapped mean to plot.

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


def model_mean_taxable(row, taxmax):
    """E[min(exp Y, taxmax)] under the fitted distribution for one (year, sex, age) cell.

    Integrate exp(y) f(y) up to log(taxmax) on a fine grid, then add the capped contribution
    taxmax * P(Y > log taxmax) of the mass above the cap."""
    thi = np.log(taxmax)
    yy = np.linspace(np.log(1.0), thi, 6000)
    if row["model"] == "dpln":
        a, b, nu, tau = (float(row[k]) for k in ("alpha", "beta", "nu", "tau"))
        dens = np.exp(cf.nl_logpdf(yy, a, b, nu, tau))
        sf = 1.0 - cf.nl_cdf(thi, a, b, nu, tau)
    else:
        mu1, mu2, s1, s2, w = (float(row[k]) for k in ("mu1", "mu2", "sig1", "sig2", "w"))
        dens = np.exp(cf.mix_logpdf(yy, mu1, mu2, s1, s2, w))
        sf = cf.mix_sf(thi, mu1, mu2, s1, s2, w)
    # the Normal-Laplace pdf overflows to +inf ~30 sigma into the lower tail (Mills ratio blows up
    # where the density is negligible); zero those out.
    integrand = np.nan_to_num(np.exp(yy) * dens, nan=0.0, posinf=0.0, neginf=0.0)
    return np.trapz(integrand, yy) + taxmax * float(np.clip(sf, 0.0, 1.0))


PARAMS = Path("output/cross_sections/cross_section_params_extrapolated.csv")
TR_XLSX = Path("raw_data/tr2023_summary.xlsx")
ASS_XLSX = Path("raw_data/annual_statistical_supplement.xlsx")
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


def ass_workers():
    """Covered-worker counts (persons) per year from the ASS workbook, annual 1937-2022 --
    the worker base underlying the ASS taxable benchmark. Weighting the model by these over
    the published span (TR covered workers only for the 2023+ projection) makes model/benchmark
    a denominator-matched per-worker comparison, and lets the model reach back to 1937."""
    d = pd.read_excel(ASS_XLSX, sheet_name="data")
    return {int(y): float(v) * 1e3 for y, v in zip(d["year"], d["num_wrk"]) if pd.notna(v)}


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


def ass_taxable():
    """Aggregate taxable (capped) earnings ($M) per year from the curated Annual Statistical
    Supplement workbook: wage + self-employed taxable earnings, annual 1937-2022 (1980 ASS
    Table 30 pre-1951, 2023 ASS Table 4.B2 for 1951+). Replaces the sparse Table-4.B1 series
    (which had only 1937/40/45/50 before 1951); reconciles to it exactly where they overlap."""
    d = pd.read_excel(ASS_XLSX, sheet_name="data")
    tax = (d["aggearn_tax_wage"].fillna(0) + d["aggearn_tax_se"].fillna(0))
    return {int(y): float(v) for y, v in zip(d["year"], tax) if pd.notna(v)}


def ass_total():
    """Aggregate TOTAL (UNCAPPED) covered earnings ($M) per year from the ASS workbook: wage +
    self-employed, annual 1937-2022. The uncapped counterpart to ass_taxable -- aggearn_tot /
    num_wrk is average earnings per worker with NO taxable cap applied, the benchmark for the
    model's IMPLIED uncapped mean E[X]. The taxable comparison hides tail-shape error behind the
    cap (a too-heavy upper tail matches taxable earnings once the cap clips it); comparing
    uncapped means exposes it directly, over the whole published span."""
    d = pd.read_excel(ASS_XLSX, sheet_name="data")
    tot = (d["aggearn_tot_wage"].fillna(0) + d["aggearn_tot_se"].fillna(0))
    return {int(y): float(v) for y, v in zip(d["year"], tot) if v > 0}


def combined_benchmark(ass, trpay):
    """One spliced published/projected series: the ASS taxable-earnings series where it exists
    (annual 1937-2022), the TR 2023 taxable-payroll projection afterward. Returns
    (benchmark, last ASS year)."""
    ass_last = max(ass)
    B = dict(trpay)
    B.update(ass)                    # ASS overrides TR in the overlap (1960-2022)
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


def uncapped_cell_mean(r):
    """Analytic UNCAPPED mean E[X] of one cell -- NO cap applied. dPlN (men):
    exp(nu+tau^2/2) * alpha*beta/((alpha-1)(beta+1)), which is INFINITE where alpha<=1 (the
    censored-MLE heavy-tail pathology: fit to top-coded data the upper Pareto index is unidentified
    and parks below 1). Two-component lognormal mean (women): always finite."""
    if int(r["sex"]) == 1:
        a, b, nu, tau = r["alpha"], r["beta"], r["nu"], r["tau"]
        if not (a > 1.0):
            return np.inf
        return np.exp(nu + tau * tau / 2) * (a * b) / ((a - 1) * (b + 1))
    w = r["w"]
    return w * np.exp(r["mu1"] + r["sig1"] ** 2 / 2) + (1 - w) * np.exp(r["mu2"] + r["sig2"] ** 2 / 2)


def model_uncapped_means(params, years_set):
    """Per-cell uncapped mean E[X] for (year, sex, age) in years_set (np.inf where alpha<=1)."""
    df = pd.read_csv(params)
    return {(int(r["year"]), int(r["sex"]), int(r["age"])): uncapped_cell_mean(r)
            for r in df.to_dict("records") if int(r["year"]) in years_set}


def agg_uncapped(unc, comp_by_year, cov):
    """Per-year model uncapped mean earnings PER WORKER (composition-weighted), plus the share of
    workers in infinite-mean (alpha<=1) cells. The finite mean renormalizes over the finite cells,
    so wherever that share is positive it is a LOWER BOUND on the model's true (infinite) uncapped
    mean. Per-worker, so no worker total is needed -- comp already sums to 1."""
    fin, inf_share = {}, {}
    for y, comp in comp_by_year.items():
        if y not in cov:
            continue
        num = wf = wi = 0.0
        for (sex, age), frac in comp.items():
            m = unc.get((y, sex, age))
            if m is None:
                continue
            if np.isinf(m):
                wi += frac
            else:
                num += m * frac; wf += frac
        if wf > 0:
            fin[y] = num / wf
            inf_share[y] = wi / (wf + wi)
    return fin, inf_share


def main():
    cov, awi, trpay = trustees()
    cov.update(ass_workers())                           # ASS num_wrk over 1937-2022; TR keeps 2023+
    df = pd.read_csv(PARAMS)
    years = sorted(set(df["year"]) & set(cov))          # model x covered-workers overlap (from 1937)
    taxmax = taxmax_series(years, awi)
    counts = epuf_counts()
    comp_by_year, back, fwd = composition_by_year(counts, years)
    y_lo, y_hi = BACK[0], DATA_LAST                      # observed-composition window

    means = model_means(PARAMS, taxmax)
    model = agg_composed(means, taxmax, comp_by_year, cov)   # observed comp in-sample, fixed off-sample

    ass = ass_taxable()                                     # annual 1937-2022 taxable earnings
    bench, ass_last = combined_benchmark(ass, trpay)        # ASS through 2022, TR after
    epuf = epuf_direct()                                    # raw 1% microdata aggregate

    # ---- uncapped: model implied mean E[X] per worker vs ASS aggearn_tot/worker ----
    ass_tot = ass_total()                                   # uncapped total earnings ($M), 1937-2022
    ass_unc = {y: ass_tot[y] * MUSD / cov[y] for y in ass_tot if y in cov}   # $ per worker
    unc = model_uncapped_means(PARAMS, set(years))
    mu_fin, mu_infshare = agg_uncapped(unc, comp_by_year, cov)               # $ per worker, inf share
    inf_years = [y for y in sorted(mu_infshare) if mu_infshare[y] > 0.005]

    yr = np.array(years)
    m = np.array([model[y] for y in years])
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(13.5, 10))

    # ---- (top-left) taxable levels (log y, trillions) ----
    by = sorted(bench); ey = sorted(epuf)
    ax1.plot(by, [bench[y] / 1e6 for y in by], color="k", lw=2.2,
             label="benchmark: ASS taxable (1937–2022) + TR 2023 (after)")
    ax1.plot(ey, [epuf[y] / 1e6 for y in ey], color="C0", lw=1.4, marker="o", ms=2.5,
             label="EPUF (raw 1% microdata ×100)")
    ax1.plot(yr, m / 1e6, color="C3", lw=1.9, ls=":", label="extrapolated model")
    ax1.axvspan(y_lo, y_hi, color="grey", alpha=0.08)
    ax1.axvline(ass_last, color="grey", lw=0.8, ls="--")
    ax1.set_yscale("log"); ax1.set_ylabel("aggregate taxable earnings ($ trillions)")
    ax1.set_xlabel("year"); ax1.set_title("Taxable (capped): levels — log scale")
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax1.legend(frameon=False, fontsize=8.5, loc="upper left")

    # ---- (top-right) taxable ratio to the combined benchmark ----
    ax2.axhline(1.0, color="k", lw=1.0)
    xe = [y for y in ey if y in bench]; re = [epuf[y] / bench[y] for y in xe]
    xm = [y for y in years if y in bench]; rm = [model[y] / bench[y] for y in xm]
    ax2.plot(xe, re, color="C0", lw=1.6, marker="o", ms=2.5, label="EPUF / benchmark")
    ax2.plot(xm, rm, color="C3", lw=1.8, ls=":", label="model / benchmark")
    ax2.axvspan(y_lo, y_hi, color="grey", alpha=0.08, label="observed-composition years")
    ax2.axvline(ass_last, color="grey", lw=0.8, ls="--")
    ax2.set_ylabel("series / combined benchmark"); ax2.set_xlabel("year")
    ax2.set_title("Taxable (capped): relative to benchmark (1.0 = exact)")
    ax2.legend(frameon=False, fontsize=8.5, loc="best")

    # ---- (bottom-left) uncapped mean earnings per worker (log y, $) ----
    ux = sorted(mu_fin); ax = sorted(ass_unc)
    ax3.plot(ax, [ass_unc[y] for y in ax], color="k", lw=2.2,
             label="ASS avg earnings/worker (uncapped: aggearn_tot / num_wrk)")
    ax3.plot(ux, [mu_fin[y] for y in ux], color="C3", lw=1.9, ls=":",
             label="model uncapped mean E[X]/worker (finite α>1 cells)")
    if inf_years:
        ax3.axvspan(min(inf_years), max(inf_years), color="C3", alpha=0.08)
    ax3.axvline(ass_last, color="grey", lw=0.8, ls="--")
    ax3.set_yscale("log"); ax3.set_ylabel("mean earnings per worker ($)")
    ax3.set_xlabel("year"); ax3.set_title("Uncapped: mean earnings per worker — log scale")
    ax3.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax3.legend(frameon=False, fontsize=8.5, loc="upper left")

    # ---- (bottom-right) uncapped ratio + infinite-mean worker share ----
    ax4.axhline(1.0, color="k", lw=1.0)
    xu = [y for y in ux if y in ass_unc]
    ax4.plot(xu, [mu_fin[y] / ass_unc[y] for y in xu], color="C3", lw=1.8, ls=":",
             label="model / ASS  (uncapped mean)")
    ax4.fill_between(ux, [mu_infshare.get(y, 0.0) for y in ux], 0, color="grey", alpha=0.18,
                     label="share of workers in infinite-mean (α≤1) cells")
    if inf_years:
        ax4.axvspan(min(inf_years), max(inf_years), color="C3", alpha=0.06)
    ax4.axvline(ass_last, color="grey", lw=0.8, ls="--")
    ax4.set_ylabel("model / ASS  (ratio; grey = inf-mean share)"); ax4.set_xlabel("year")
    ax4.set_title("Uncapped: ratio (finite-cell mean — a lower bound where shaded)")
    ax4.legend(frameon=False, fontsize=8.5, loc="best")

    fig.suptitle("Aggregate earnings: EPUF & extrapolated model vs ASS+TR — capped (top) and uncapped (bottom)",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    outp = "output/cross_sections/aggregate_taxable_extrapolated"
    fig.savefig(outp + ".pdf"); fig.savefig(outp + ".png", dpi=150); plt.close(fig)

    print(f"{'year':>4} {'model($M)':>13} {'bench($M)':>13} {'mdl/bn':>7}   "
          f"{'MDunc/wk':>9} {'ASSunc/wk':>9} {'unc mdl/AS':>10} {'inf%':>5}")
    for y in years:
        if y % 10 == 0 or y in (years[0], years[-1], 2004, 2006, ass_last):
            b = bench.get(y); au = ass_unc.get(y); mf = mu_fin.get(y)
            ur = (mf / au) if (au and mf) else 0.0
            print(f"{y:>4} {model[y]:>13,.0f} {b if b else 0:>13,.0f} "
                  f"{model[y]/b if b else 0:>7.3f}   "
                  f"{mf if mf else 0:>9,.0f} {au if au else 0:>9,.0f} {ur:>10.3f} "
                  f"{mu_infshare.get(y, 0.0)*100:>4.0f}%")
    print(f"\nwrote {outp}.pdf and .png")


if __name__ == "__main__":
    main()
