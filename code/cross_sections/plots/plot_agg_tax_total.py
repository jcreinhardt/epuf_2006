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

TWO OPTIONAL OVERLAYS, both off by default:

  --gkos CSV  the GKOS/Guvenen cohort-model aggregate, exported by
              code/dynamics/plots/plot_agg_tax_dynamics.py --export. That model is a
              lifecycle process -- log Y = g(t) + u with every parameter but g fixed at
              GKOS's published estimate -- so it reaches the same aggregate by a route
              that shares NO parameters with the per-cell surface this script's own model
              line comes from. It must be exported with --renorm-comp (enforced): that
              model covers ages 20-70 only, and without renormalising the composition
              inside that window its worker base is not all covered workers, so the
              age-coverage gap would read as model error against this figure's other
              series. Both are then per-covered-worker over the published worker total.
  --e9f PARQUET  the prior cross-section pipeline's agg_taxable_earnings_extrap.parquet.
              It is in REAL 2013 dollars while this figure is nominal. Reflating it with
              THIS project's price index is wrong -- ours is PCE, e9f's is CPI, and they
              differ by up to 25% mid-century. The conversion instead recovers e9f's own
              deflator from the file, as nominal taxmax / its `tax_max_2013` column.

  python code/cross_sections/plots/plot_agg_tax_total.py [params_csv] [tag]
        [--gkos output/dynamics/agg_taxable_gkos_smmq_quad.csv] [--e9f PATH]
    -> output/cross_sections/plots/aggregate_taxable_extrapolated[_tag].pdf (+ .png)   2x2
       output/cross_sections/plots/aggregate_taxable_capped[_tag].pdf (+ .png)         levels + ratio
       output/cross_sections/plots/aggregate_taxable_ratio_insample[_tag].pdf (+ .png)  1951-2006, with EPUF
       output/cross_sections/plots/aggregate_taxable_ratio_full[_tag].pdf (+ .png)      1937-2100, without EPUF

`params_csv` swaps the parameter surface (e.g. cross_section_params_guvgmm_smoothed.csv);
`tag` suffixes the output files so alternative surfaces sit next to the canonical figures.
Years whose cells cover under 85% of that year's worker composition (e.g. the guvgmm
surface's 2007-13 rows, which exist for ages 25-55 only) are EXCLUDED from the model
series with a note -- summing a partial age range against a full-population benchmark
would just measure the missing ages.
"""
import io
import subprocess
import argparse
import sys
from pathlib import Path

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator

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
TAG    = ""                                          # "_<tag>" suffix on the output files
COVER_MIN = 0.85    # a year enters the model series only if its cells carry at least this
                    # share of the year's (sex, age) worker composition
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


# Series colors. Categorical slots 1 and 2 of the reference palette plus a near-black for
# the benchmark, which is a reference line rather than a category. Validated as a set on a
# light surface: worst normal-vision dE 33.6 (floor 15), worst CVD dE 24.7 (target >=8),
# every contrast >= 3:1 -- so the three stay separable in print and under color blindness,
# which matplotlib's default C0/C3 pairing does not guarantee.
C_BENCH, C_EPUF, C_MODEL = "#1a1a19", "#2a78d6", "#eb6834"
C_GKOS, C_E9F = "#2e9e6b", "#8e5bb5"
# Slide cut: fewer words and bigger type. The 2x2 diagnostic keeps the long, self-describing
# labels (it is read on its own, off-slide); the slide version is read from across a room.
SLIDE_RC = {"font.size": 14, "axes.titlesize": 17, "axes.labelsize": 14,
            "xtick.labelsize": 13, "ytick.labelsize": 13, "legend.fontsize": 12}


def panel_levels(ax, bench, epuf, yr, m, y_lo, y_hi, ass_last, slide=False,
                 gkos=None, e9f=None):
    """Taxable (capped) aggregate levels, log y, $ trillions."""
    by, ey = sorted(bench), sorted(epuf)
    lab = (["ASS + TR benchmark", "EPUF $\\times$100", "model"] if slide else
           ["benchmark: ASS taxable (1937–2022) + TR 2023 (after)",
            "EPUF (raw 1% microdata ×100)", "extrapolated model"])
    ax.plot(by, [bench[y] / 1e6 for y in by], color=C_BENCH, lw=3.0 if slide else 2.2,
            label=lab[0])
    ax.plot(ey, [epuf[y] / 1e6 for y in ey], color=C_EPUF, lw=2.4 if slide else 1.4,
            marker="o", ms=3.5 if slide else 2.5, label=lab[1])
    ax.plot(yr, m / 1e6, color=C_MODEL, lw=2.8 if slide else 1.9, ls=":", label=lab[2])
    if gkos:
        gy = sorted(gkos)
        ax.plot(gy, [gkos[y] / 1e6 for y in gy], color=C_GKOS,
                lw=2.4 if slide else 1.7, ls=(0, (5, 1.6)),
                label="GKOS" if slide else "GKOS cohort model (quadratic $g(t)$, SMM on quantiles)")
    if e9f:
        ey2 = sorted(e9f)
        ax.plot(ey2, [e9f[y] / 1e6 for y in ey2], color=C_E9F,
                lw=2.2 if slide else 1.5, ls=(0, (1, 1.4)),
                label="e9f" if slide else "e9f series (prior cross-section pipeline)")
    ax.axvspan(y_lo, y_hi, color="grey", alpha=0.08)
    ax.axvline(ass_last, color="grey", lw=0.8, ls="--")
    ax.set_yscale("log")
    ax.set_ylabel("$ trillions" if slide else "aggregate taxable earnings ($ trillions)")
    ax.set_xlabel("year")
    ax.set_title("Taxable earnings (log scale)" if slide else "Taxable (capped): levels — log scale")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.legend(frameon=False, loc="upper left", fontsize=None if slide else 8.5)


def panel_ratio(ax, bench, epuf, years, model, y_lo, y_hi, ass_last, slide=False,
                gkos=None, e9f=None):
    """Taxable (capped) series divided by the combined ASS+TR benchmark."""
    ax.axhline(1.0, color=C_BENCH, lw=1.2)
    xe = [y for y in sorted(epuf) if y in bench]
    xm = [y for y in years if y in bench]
    ax.plot(xe, [epuf[y] / bench[y] for y in xe], color=C_EPUF, lw=2.4 if slide else 1.6,
            marker="o", ms=3.5 if slide else 2.5, label="EPUF" if slide else "EPUF / benchmark")
    ax.plot(xm, [model[y] / bench[y] for y in xm], color=C_MODEL, lw=2.8 if slide else 1.8,
            ls=":", label="model" if slide else "model / benchmark")
    if gkos:
        xg = [y for y in sorted(gkos) if y in bench]
        ax.plot(xg, [gkos[y] / bench[y] for y in xg], color=C_GKOS,
                lw=2.4 if slide else 1.7, ls=(0, (5, 1.6)),
                label="GKOS" if slide else "GKOS cohort model / benchmark")
    if e9f:
        xf = [y for y in sorted(e9f) if y in bench]
        ax.plot(xf, [e9f[y] / bench[y] for y in xf], color=C_E9F,
                lw=2.2 if slide else 1.5, ls=(0, (1, 1.4)),
                label="e9f" if slide else "e9f / benchmark")
    ax.axvspan(y_lo, y_hi, color="grey", alpha=0.08,
               label=None if slide else "observed-composition years")
    ax.axvline(ass_last, color="grey", lw=0.8, ls="--")
    ax.set_ylabel("ratio to benchmark" if slide else "series / combined benchmark")
    ax.set_xlabel("year")
    ax.set_title("Relative to benchmark" if slide
                 else "Taxable (capped): relative to benchmark (1.0 = exact)")
    if slide:                      # the default 0.02 steps crowd the axis at slide type
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4, steps=[1, 2, 5, 10]))
    ax.legend(frameon=False, loc="best", fontsize=None if slide else 8.5)


def load_gkos(path):
    """The GKOS/Guvenen cohort-model aggregate exported by
    code/dynamics/plots/plot_agg_tax_dynamics.py --export.

    Returns (taxable $M by year, uncapped $M by year, 2013$->nominal price index).
    Refuses a series that was NOT exported with --renorm-comp: without it the model covers
    only its own age window (default 20-70) and falls short of the published total by
    whatever the other ages carry -- on this figure, whose other series are per-covered-
    worker over ALL ages, that coverage gap would read as model error."""
    d = pd.read_csv(path)
    if not bool(d["renorm_comp"].iloc[0]):
        sys.exit(f"{path} was exported without --renorm-comp, so its worker base is the "
                 f"modelled age window rather than all covered workers. Re-run "
                 f"plot_agg_tax_dynamics.py with --renorm-comp before overlaying it here.")
    tax = {int(r.year): float(r.agg_taxable_musd) for r in d.itertuples()}
    unc = {int(r.year): float(r.agg_uncapped_musd) for r in d.itertuples()}
    price = {int(r.year): float(r.price_2013_to_nominal) for r in d.itertuples()}
    return tax, unc, price


def load_e9f(path, taxmax):
    """The prior cross-section pipeline's aggregate taxable earnings
    (project_vu .../data/intermediate/agg_taxable_earnings_extrap.parquet).

    That series is in REAL 2013 dollars and this figure is nominal, so it has to be
    reflated -- but NOT with this project's price index. Ours is PCE-based; e9f's is CPI,
    and the two diverge by up to 25% mid-century (1960: 0.1297 vs 0.1623), which lands
    entirely on the plotted line. So the conversion uses e9f's OWN deflator, which the
    file pins down exactly: it carries `tax_max_2013`, the real-2013 value of a taxable
    maximum whose nominal value we know, hence

        P_e9f(y) = nominal taxmax(y) / tax_max_2013(y)

    with the nominal path from taxmax_series() -- the EPUF top-code in sample, so this is
    exact where it matters and only relies on the AWI-indexed projection after 2006. No
    assumption about WHICH index they used is needed, which is the point of doing it this
    way rather than looking up a CPI vintage. Years with no taxmax are dropped."""
    d = pd.read_parquet(path)
    if "agg_earn_total" not in d.columns:
        sys.exit(f"{path} has no 'agg_earn_total' column; found {list(d.columns)}")
    out = {}
    for r in d.itertuples():
        y = int(r.year)
        tm13 = float(r.tax_max_2013)
        if y in taxmax and tm13 > 0:
            out[y] = float(r.agg_earn_total) * (taxmax[y] / tm13) / MUSD
    return out


# --- minimalist ratio cuts ---------------------------------------------------
# Standalone ratio figures, styled apart from the 2x2 and the slide cut on purpose:
# solid lines, one colour AND one marker per series, no shaded bands, no boxed legend.
# Markers rather than dashes carry the series identity, so the lines stay readable where
# four of them sit inside a two-point band.
SERIES = {
    "epuf":  dict(color="#3b7dd8", marker="o", label="EPUF"),
    "model": dict(color="#e2622c", marker="s", label="parametric cross-sections"),
    "gkos":  dict(color="#1f9e77", marker="^", label="GKOS cohort model"),
    "e9f":   dict(color="#8e5bb5", marker="D", label="e9f (prior pipeline)"),
}

# For the moment-set comparison the two lines ARE the same model, so they get their own
# palette rather than borrowing SERIES["gkos"] -- nothing else on that figure to collide with.
GKOS_SERIES = {
    "gkos_mean": dict(color="#c2456b", marker="o",
                      label="$g(t)$ from SMM on the mean only"),
    "gkos":      dict(color="#1f9e77", marker="^",
                      label="$g(t)$ from SMM on mean + p10…p98"),
}


def _despine(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color("#9a9a9a")
    ax.spines["bottom"].set_color("#9a9a9a")
    ax.tick_params(colors="#4a4a4a", length=3)


def ratio_figure(path, bench, series, x0, x1, title, styles=None, nmark=14):
    """One panel: each series divided by the benchmark, over [x0, x1].

    `series` is an ordered list of (style_key, {year: value}); a series contributing no
    year inside the window is dropped rather than drawn as an empty line."""
    styles = styles or SERIES
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    ax.axhline(1.0, color="#9a9a9a", lw=1.0, zorder=1)
    ax.annotate("ASS", xy=(1.0, 1.0), xytext=(4, 2), xycoords=("axes fraction", "data"),
                textcoords="offset points", color="#6a6a6a", fontsize=9.5,
                va="bottom", ha="left", annotation_clip=False)
    for key, d in series:
        xs = [y for y in sorted(d) if x0 <= y <= x1 and y in bench]
        if not xs:
            continue
        ys = [d[y] / bench[y] for y in xs]
        st = styles[key]
        step = max(1, len(xs) // nmark)
        ax.plot(xs, ys, color=st["color"], lw=1.7, solid_capstyle="round",
                marker=st["marker"], ms=4.2, markevery=step,
                markerfacecolor="white", markeredgewidth=1.3, label=st["label"], zorder=2)
    _despine(ax)
    ax.set_xlim(x0, x1)
    ax.set_xlabel("year")
    ax.set_ylabel("ratio to ASS+TR benchmark")
    ax.set_title(title, loc="left", fontsize=11.5)
    ax.legend(frameon=False, loc="best", fontsize=9.5, handlelength=2.6)
    fig.tight_layout()
    fig.savefig(path + ".pdf"); fig.savefig(path + ".png", dpi=150)
    plt.close(fig)


def main(gkos_path=None, e9f_path=None, gkos_mean_path=None):
    cov, awi, trpay = trustees()
    cov.update(ass_workers())                           # ASS num_wrk over 1937-2022; TR keeps 2023+
    df = pd.read_csv(PARAMS)
    years = sorted(set(df["year"]) & set(cov))          # model x covered-workers overlap (from 1937)
    taxmax = taxmax_series(years, awi)
    counts = epuf_counts()
    comp_by_year, back, fwd = composition_by_year(counts, years)
    y_lo, y_hi = BACK[0], DATA_LAST                      # observed-composition window

    # coverage guard: drop years whose cells carry too little of the composition
    # (partial-age surfaces, e.g. guvgmm's ages-25-55-only 2007-13 rows)
    have = {(int(r.year), int(r.sex), int(r.age)) for r in df.itertuples()}
    keep = []
    for y in years:
        share = sum(f for (s, a), f in comp_by_year[y].items() if (y, s, a) in have)
        if share >= COVER_MIN:
            keep.append(y)
    if len(keep) < len(years):
        dropped = sorted(set(years) - set(keep))
        print(f"NOTE: {len(dropped)} years excluded for partial age coverage "
              f"(<{COVER_MIN:.0%} of composition): {dropped[:8]}"
              + (" ..." if len(dropped) > 8 else ""))
        years = keep
        taxmax = {y: taxmax[y] for y in years}
        comp_by_year = {y: comp_by_year[y] for y in years}

    means = model_means(PARAMS, taxmax)
    model = agg_composed(means, taxmax, comp_by_year, cov)   # observed comp in-sample, fixed off-sample

    ass = ass_taxable()                                     # annual 1937-2022 taxable earnings
    bench, ass_last = combined_benchmark(ass, trpay)        # ASS through 2022, TR after
    epuf = epuf_direct()                                    # raw 1% microdata aggregate

    gkos = gkos_unc = e9f = gkos_mean = None
    if gkos_path:
        gkos, gkos_unc, _ = load_gkos(gkos_path)
    if e9f_path:
        e9f = load_e9f(e9f_path, taxmax)
    if gkos_mean_path:
        gkos_mean, _, _ = load_gkos(gkos_mean_path)

    # ---- uncapped: model implied mean E[X] per worker vs ASS aggearn_tot/worker ----
    ass_tot = ass_total()                                   # uncapped total earnings ($M), 1937-2022
    ass_unc = {y: ass_tot[y] * MUSD / cov[y] for y in ass_tot if y in cov}   # $ per worker
    unc = model_uncapped_means(PARAMS, set(years))
    mu_fin, mu_infshare = agg_uncapped(unc, comp_by_year, cov)               # $ per worker, inf share
    inf_years = [y for y in sorted(mu_infshare) if mu_infshare[y] > 0.005]

    yr = np.array(years)
    m = np.array([model[y] for y in years])
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(13.5, 10))

    # ---- (top row) the capped comparison: levels, then ratio to the benchmark ----
    panel_levels(ax1, bench, epuf, yr, m, y_lo, y_hi, ass_last, gkos=gkos, e9f=e9f)
    panel_ratio(ax2, bench, epuf, years, model, y_lo, y_hi, ass_last, gkos=gkos, e9f=e9f)

    # ---- (bottom-left) uncapped mean earnings per worker (log y, $) ----
    ux = sorted(mu_fin); ax = sorted(ass_unc)
    ax3.plot(ax, [ass_unc[y] for y in ax], color="k", lw=2.2,
             label="ASS avg earnings/worker (uncapped: aggearn_tot / num_wrk)")
    ax3.plot(ux, [mu_fin[y] for y in ux], color="C3", lw=1.9, ls=":",
             label="model uncapped mean E[X]/worker (finite α>1 cells)")
    if gkos_unc:
        gu = {y: gkos_unc[y] * MUSD / cov[y] for y in sorted(gkos_unc) if y in cov}
        ax3.plot(sorted(gu), [gu[y] for y in sorted(gu)], color=C_GKOS, lw=1.7,
                 ls=(0, (5, 1.6)), label="GKOS cohort model uncapped mean/worker")
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
    if gkos_unc:
        xg = [y for y in sorted(gkos_unc) if y in cov and y in ass_unc]
        ax4.plot(xg, [gkos_unc[y] * MUSD / cov[y] / ass_unc[y] for y in xg], color=C_GKOS,
                 lw=1.7, ls=(0, (5, 1.6)), label="GKOS cohort model / ASS  (uncapped mean)")
    ax4.fill_between(ux, [mu_infshare.get(y, 0.0) for y in ux], 0, color="grey", alpha=0.18,
                     label="share of workers in infinite-mean (α≤1) cells")
    if inf_years:
        ax4.axvspan(min(inf_years), max(inf_years), color="C3", alpha=0.06)
    ax4.axvline(ass_last, color="grey", lw=0.8, ls="--")
    ax4.set_ylabel("model / ASS  (ratio; grey = inf-mean share)"); ax4.set_xlabel("year")
    ax4.set_title("Uncapped: ratio (finite-cell mean — a lower bound where shaded)")
    ax4.legend(frameon=False, fontsize=8.5, loc="best")

    extra = [n for n, on in (("GKOS", gkos), ("e9f", e9f)) if on]
    fig.suptitle("Aggregate earnings: EPUF"
                 + (", " + " & ".join(extra) if extra else "")
                 + " & extrapolated model vs ASS+TR — capped (top) and uncapped (bottom)",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    outp = f"output/cross_sections/plots/aggregate_taxable_extrapolated{TAG}"
    fig.savefig(outp + ".pdf"); fig.savefig(outp + ".png", dpi=150); plt.close(fig)

    # Slide cut: the capped comparison only (levels + ratio). The uncapped row is the
    # diagnostic that tail error is hiding under the cap -- it belongs in the 2x2 above,
    # not on a slide whose claim is about taxable totals.
    with plt.rc_context(SLIDE_RC):
        figs, (bx1, bx2) = plt.subplots(1, 2, figsize=(8.6, 3.18))
        panel_levels(bx1, bench, epuf, yr, m, y_lo, y_hi, ass_last, slide=True,
                     gkos=gkos, e9f=e9f)
        panel_ratio(bx2, bench, epuf, years, model, y_lo, y_hi, ass_last, slide=True,
                    gkos=gkos, e9f=e9f)
        figs.tight_layout()
    outs = f"output/cross_sections/plots/aggregate_taxable_capped{TAG}"
    figs.savefig(outs + ".pdf"); figs.savefig(outs + ".png", dpi=150); plt.close(figs)

    # Two standalone ratio cuts, per the two questions they answer. IN SAMPLE keeps EPUF,
    # which is the point of that window -- it is the only stretch where the microdata
    # exist, so model-vs-EPUF is the real success criterion there. FULL SPAN drops EPUF:
    # it stops in 2006, and a line covering a third of the axis reads as though the other
    # series lose a comparator rather than EPUF simply not existing.
    ser_all = [("epuf", epuf), ("model", model)]
    if gkos:
        ser_all.append(("gkos", gkos))
    if e9f:
        ser_all.append(("e9f", e9f))

    outr = f"output/cross_sections/plots/aggregate_taxable_ratio_insample{TAG}"
    ratio_figure(outr, bench, ser_all, 1951, 2006,
                 "Aggregate taxable earnings relative to ASS, 1951–2006")
    outf = f"output/cross_sections/plots/aggregate_taxable_ratio_full{TAG}"
    ratio_figure(outf, bench, [s for s in ser_all if s[0] != "epuf"], 1937, 2100,
                 "Aggregate taxable earnings relative to ASS+TR, 1937–2100")

    print(f"\nwrote {outp}.pdf and .png")
    print(f"wrote {outs}.pdf and .png   (slide cut: levels + ratio)")
    if gkos_mean and gkos:
        outg = f"output/cross_sections/plots/aggregate_taxable_ratio_gkos_moments{TAG}"
        ratio_figure(outg, bench, [("gkos_mean", gkos_mean), ("gkos", gkos)], 1937, 2100,
                     "GKOS cohort model: what the moment set does to the implied aggregate",
                     styles=GKOS_SERIES)
        rm = {y: gkos_mean[y] / bench[y] for y in gkos_mean if y in bench}
        rq = {y: gkos[y] / bench[y] for y in gkos if y in bench}
        both = sorted(set(rm) & set(rq))
        for lab, y0, y1 in (("1937-1950", 1937, 1950), ("1951-2006", 1951, 2006),
                            ("2007-2022", 2007, 2022), ("2023+", 2023, 2100)):
            v = [(rm[y], rq[y]) for y in both if y0 <= y <= y1]
            if v:
                m0 = np.mean([a for a, _ in v]); q0 = np.mean([b for _, b in v])
                d = [abs(a - b) for a, b in v]
                print(f"GKOS moment set, {lab:10s} mean-only {m0:.3f}  quantiles {q0:.3f}  "
                      f"mean|diff| {np.mean(d):.4f}  max {max(d):.4f}")
        print(f"wrote {outg}.pdf and .png   (GKOS: mean-only vs quantiles)")
    print(f"wrote {outr}.pdf and .png   (ratio, 1951-2006, with EPUF)")
    print(f"wrote {outf}.pdf and .png   (ratio, 1937-2100, without EPUF)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("params", nargs="?", default=None, help="parameter surface CSV")
    ap.add_argument("tag", nargs="?", default=None, help="suffix on the output filenames")
    ap.add_argument("--gkos", default=None,
                    help="overlay the GKOS/Guvenen cohort-model aggregate exported by "
                         "code/dynamics/plots/plot_agg_tax_dynamics.py --export "
                         "(must have been exported with --renorm-comp)")
    ap.add_argument("--gkos-mean", default=None,
                    help="a SECOND GKOS export, fitted on the mean only; with --gkos this "
                         "adds a figure comparing the two moment sets")
    ap.add_argument("--e9f", default=None,
                    help="overlay the prior pipeline's agg_taxable_earnings_extrap.parquet "
                         "(real 2013$; reflated with its OWN deflator, recovered from its "
                         "tax_max_2013 column -- ours is PCE, e9f's is CPI)")
    a = ap.parse_args()
    if a.params:
        PARAMS = Path(a.params)
    if a.tag:
        TAG = "_" + a.tag.lstrip("_")
    main(gkos_path=a.gkos, e9f_path=a.e9f, gkos_mean_path=a.gkos_mean)
