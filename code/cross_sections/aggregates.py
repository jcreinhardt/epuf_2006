#!/usr/bin/env python
"""Turn a fitted parameter surface into aggregate earnings, and load the EPUF-side
quantities that go with it. No matplotlib: this is the library half of what used to be
plot_agg_tax_total.py.

It was split out for the same reason guv_targets.py was split out of plot_guv_comparison.py
-- non-plotting code had come to depend on a plotting module. agg_tax_emp_weighted.py and
the 2026-08-24 report script both import `ass_taxable` / `epuf_direct` / `model_means`, and
were pulling in matplotlib to read a spreadsheet. Figures now import THIS; nothing imports
figures.

WHAT THE MODEL DOES AND DOES NOT DETERMINE. The fitted surface gives the SHAPE of each
(year, sex, age) cell's earnings distribution -- hence mean taxable earnings per covered
worker -- and nothing about how many workers there are. The worker weight is therefore
supplied separately, as

    workers(sex, age, y) = covered workers(y)  x  comp(sex, age, y)

with the published covered-worker total from benchmarks (ASS num_wrk 1937-2022, TR after)
and `comp` the EPUF composition of positive earners: observed per year over 1951-DATA_LAST,
held at the 1951-1955 average before and the 2000-2004 average after. The composition
shifted hard -- women were 34% of earners in 1951 against 48% in 2004 -- so freezing the
2000-04 mix onto the early years (an earlier design) over-weighted women and misfit the
in-sample aggregate.

Units follow benchmarks.py: aggregate earnings $M, worker counts persons, per-worker $.
"""
import io
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd

import crosssec_fit as cf
from benchmarks import MUSD

PARAMS = Path("output/cross_sections/cross_section_params_extrapolated.csv")
TAXMAX_1937_50 = 3000.0   # statutory taxable maximum, flat from 1937 through 1950
ANCHOR = (2000, 2004)     # forward composition: fixed at this window (last observed edge)
BACK   = (1951, 1955)     # pre-1951 composition: fixed at the earliest observed edge
DATA_LAST = 2004          # observed per-year composition used through here; fixed after


def _duck(q):
    return subprocess.run(["duckdb", cf.DB, "-c", q], capture_output=True, text=True,
                          check=True).stdout


# --------------------------------------------------------------------- EPUF-side series
def taxmax_series(years, awi):
    """Taxable maximum ($): $3,000 (<=1950), the EPUF top-code (1951-2006, recovered as
    MAX(earnings)), AWI-indexed off 2006 afterward."""
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
    taxable maximum, so their sum IS taxable earnings). The observed microdata benchmark.
    EPUF itself runs ~2-3% below ASS -- a known EPUF-vs-Supplement gap -- so a model
    anchored to EPUF inherits that offset, and tracking EPUF is the real success criterion
    in sample."""
    out = _duck("COPY (SELECT year, 100*SUM(earnings)/1e6 FROM annual WHERE earnings>0 "
                "GROUP BY year) TO '/dev/stdout' (FORMAT CSV, HEADER FALSE);")
    return {int(y): float(v) for y, v in (l.split(",") for l in out.strip().splitlines())}


def epuf_counts():
    """Positive-earner counts by (year, sex, single-year age), 1951-2006."""
    q = ("COPY (SELECT a.year, d.sex, (a.year-d.yob) AS age, COUNT(*) AS n "
         "FROM annual a JOIN demographic d USING(id) "
         "WHERE a.earnings>0 AND d.sex IN (1,2) AND d.yob IS NOT NULL "
         "AND (a.year-d.yob) BETWEEN 15 AND 77 GROUP BY 1,2,3 ORDER BY 1,2,3) "
         "TO '/dev/stdout' (FORMAT CSV, HEADER TRUE);")   # ORDER BY: fixes the (sex, age)
         # iteration order, hence the summation order in agg_composed / agg_uncapped
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
    """Per-year (sex, age) composition for the model: the OBSERVED EPUF share each year over
    1951-DATA_LAST, held fixed at the 1951-1955 average before 1951 and at the 2000-2004
    average after DATA_LAST (the two data edges we can carry off-sample; the TR has no
    sex/age breakdown). Returns (comp_by_year, back_share, fwd_share)."""
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


# ------------------------------------------------------------------ model cell means
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


def uncapped_cell_mean(row):
    """Analytic UNCAPPED mean E[X] of one parameter row -- NO cap applied. Delegates to the
    fitters' own closed forms (cf.dpln_mean / cf.mix_mean) so the estimator's notion of E[X]
    and the validation's are the same code; men's is INFINITE where alpha <= 1, the
    censored-MLE heavy-tail pathology (above the cap the upper Pareto index is unidentified
    and can park below 1)."""
    if int(row["sex"]) == 1:
        return cf.dpln_mean(row["alpha"], row["beta"], row["nu"], row["tau"])
    return cf.mix_mean(row["mu1"], row["mu2"], row["sig1"], row["sig2"], row["w"])


def model_means(params, taxmax):
    """Model mean TAXABLE ($) per (year, sex, age), for the years present in `taxmax`."""
    df = pd.read_csv(params)
    means = {}
    for r in df.to_dict("records"):
        y = int(r["year"])
        if y in taxmax:
            means[(y, int(r["sex"]), int(r["age"]))] = model_mean_taxable(r, taxmax[y])
    return means


def model_uncapped_means(params, years_set):
    """Per-cell uncapped mean E[X] for (year, sex, age) in years_set (np.inf where alpha<=1)."""
    df = pd.read_csv(params)
    return {(int(r["year"]), int(r["sex"]), int(r["age"])): uncapped_cell_mean(r)
            for r in df.to_dict("records") if int(r["year"]) in years_set}


# ------------------------------------------------------------------ aggregation
def agg_composed(means, taxmax, comp_by_year, cov):
    """Aggregate taxable ($M) with a per-year (sex, age) composition x covered workers(y)."""
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


# ------------------------------------------------------- outside-pipeline comparison series
def load_gkos(path):
    """The GKOS/Guvenen cohort-model aggregate exported by
    code/dynamics/plots/plot_agg_tax_dynamics.py --export.

    Returns (taxable $M by year, uncapped $M by year, 2013$->nominal price index).
    Refuses a series that was NOT exported with --renorm-comp: without it the model covers
    only its own age window (default 20-70) and falls short of the published total by
    whatever the other ages carry -- against series that are per-covered-worker over ALL
    ages, that coverage gap would read as model error."""
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
    (project_vu .../data/intermediate/agg_taxable_earnings_extrap.parquet), reflated to
    nominal $M.

    That series is in REAL 2013 dollars -- but it must NOT be reflated with this project's
    price index. Ours is PCE-based; e9f's is CPI, and the two diverge by up to 25%
    mid-century (1960: 0.1297 vs 0.1623), which lands entirely on the converted series. So
    the conversion uses e9f's OWN deflator, which the file pins down exactly: it carries
    `tax_max_2013`, the real-2013 value of a taxable maximum whose nominal value we know,
    hence

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
