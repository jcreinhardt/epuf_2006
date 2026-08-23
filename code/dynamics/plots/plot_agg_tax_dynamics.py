#!/usr/bin/env python
"""Validate the extrapolated GKOS cohort profiles against published aggregate TAXABLE
earnings: the Annual Statistical Supplement (1937-2022) spliced onto the 2023 Trustees
Report taxable-payroll projection.  The counterpart, for the dynamics model, of
code/cross_sections/plots/plot_agg_tax_total.py.

The benchmark is the PUBLISHED TOTAL, undivided.  No age split is imputed onto it -- an
earlier version scaled it by EPUF's share of earnings accruing to the modelled ages, which
put a microdata-derived, edge-held factor on the level of the thing being validated.  Here
the model simply covers ages AGE_LO-AGE_HI (default 20-70) and falls short of the total by
whatever those ages miss.  `coverage()` reports that gap explicitly, by year and by
single-year age, and EPUF is restricted to the SAME age window, so EPUF/benchmark carries
exactly the same mechanical shortfall and model-vs-EPUF stays a clean comparison.

Ages 20-70 with a QUADRATIC g(t) -- GKOS's own functional form -- rather than 25-55 with a
cubic.  Over 25-55 the quadratic costs about 0.006 log points of rmse (0.031 vs 0.025), and
buys an extrapolation that does not diverge: at age 84 the cubic reaches $386k for a 1970
male cohort against the quadratic's $15k.  20 and 70 bound where the rest of the model is
still defensible, not where the polynomial stops being finite:

  * BELOW 20 the persistent component has no definition.  SIG_Z0 is the dispersion of z at
    labour-market entry, which GKOS place at age 25, and the AR(1) has no backward form.
    `gcohort_model.entry_sd` solves the age-20 initial condition so that z's age-25
    dispersion is still exactly SIG_Z0 (0.613 -> 0.714), which keeps everything downstream
    on GKOS's calibration; going much earlier drives that variance negative.

  * ABOVE 70 the nonemployment process is the binding problem, not g.  GKOS's logistic
    incidence has a -0.859*t term, so at z = 0 nonemployment FALLS with age (0.031 at 25 to
    0.0002 at 84) and withdrawal happens only through the z*t interaction.  Extrapolated,
    the model has 68% of 84-year-olds employed -- no retirement margin at all.  Worker
    COUNTS come from ASS num_wrk so the aggregate is not distorted by that, but the model's
    old workers are barely more selected than its young ones, so their mean earnings are
    wrong.  70 keeps that error small; 71+ is ~1% of earnings anyway.

Worker weights follow the cross-section script:

    workers(sex, age, y) = covered workers(y) x comp(sex, age, y),   AGE_LO <= age <= AGE_HI

with covered workers from ASS num_wrk (1937-2022) then the TR projection, and comp the EPUF
per-year (sex, single-year age) share of positive earners over ALL ages 15-77 -- so the
modelled slice sums to less than one and yields the absolute count of covered workers in it.
comp is observed 1951-2004 and edge-held outside.  The model supplies mean earnings per
covered worker, never the number of workers.

Per-cell means come from the simulated GKOS panel, not a quadrature: with log Y = g_c(age) + u
and u the fixed stochastic part, one panel of u by age gives every cell at once,

    E[min(Y, C) | Y > 0] = ( e^g * SUM_{u < b} e^u  +  C * #{u >= b} ) / N,   b = log C - g

over the N individuals with FINITE u (positive earnings) at that age.  Conditioning on Y > 0
rather than the estimation sample's Y >= Ymin floor, because ASS covered workers are all
positive earners; measured, the two differ by under 0.1% of workers, since the nu shock
already puts the low-earnings mass at exactly zero (`--condition ymin` reports the other).

Nominal throughout: g is in 2013 dollars, so it is inflated by the PCE index (extended past
2025 by the TR's implied wage deflator, nominal minus real wage APC, keeping the nominal wage
path exactly the TR's) before the taxable maximum applies.  The maximum is the EPUF top-code
(1951-2006), $3,000 before, AWI-indexed off 2006 after.

The BOTTOM row drops the cap: model aggregate uncapped earnings against ASS aggearn_tot, the
same coverage gap on both rows.  The cap hides tail-shape error -- a too-heavy upper tail
still reproduces taxable earnings once clipped -- so the uncapped row is where it shows.

Ages up to AGE_HI in 1937 need cohorts back to Y0 - AGE_HI + 25, well before the extrapolation
CSV's 1937; this script therefore re-runs extrapolate_g_cohort's rule over the wider cohort
range rather than reading the CSV, so the rule has one source of truth.  Pre-1937 the wage
index has no published level and is walked back at the average realized real growth of
1937-1950.

  python code/dynamics/plots/plot_agg_tax_dynamics.py [--fits CSV] [--ages 20 70]
      [--condition positive|ymin]
    -> output/dynamics/aggregate_taxable_dynamics_<tag>.{pdf,png}
       output/dynamics/age_coverage_<tag>.{pdf,png}
"""

import argparse
import io
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

sys.path.insert(0, "code/dynamics")          # run from project root, per repo convention
import gcohort_model as E
import extrapolate_g_cohort as X

DB = "processed_data/ssa.duckdb"
ASS_XLSX = "raw_data/annual_statistical_supplement.xlsx"
TR_XLSX = "raw_data/tr2023_summary.xlsx"
PCE_CSV = "raw_data/deflator/DPCERG3A086NBEA.csv"
OUT = "output/dynamics"

Y0, Y1 = 1937, 2100
COMP_LO, COMP_HI = 15, 77          # EPUF ages the composition is built over (99.9% of earnings)
MUSD = 1e6
TAXMAX_1937_50 = 3000.0
BACK, ANCHOR, DATA_LAST = (1951, 1955), (2000, 2004), 2004
EPUF_LAST = 2006
TR_NOM, TR_REAL = ("Average Annual Nominal Wage in Covered Employment APC",
                   "Average Annual Real Wage in Covered Employment APC")
ERAS = [(1951, 1955), (1975, 1985), (2000, 2006)]

C_BENCH, C_EPUF, C_MODEL = "#1a1a19", "#2a78d6", "#eb6834"


def _duck(q):
    return subprocess.run(["duckdb", DB, "-c", q], capture_output=True, text=True,
                          check=True).stdout


# --- published series ---------------------------------------------------------

def trustees():
    d = pd.read_excel(TR_XLSX, sheet_name="Intermediate", header=0)
    d = d.rename(columns={d.columns[0]: "year"})
    col = lambda c, f: {int(y): f(v) for y, v in zip(d["year"], d[c]) if pd.notna(v)}
    return (col("Thousands of Covered Workers", lambda v: float(v) * 1e3),
            col("Average Wage Index", float),
            col("Taxable Payroll, Billions", lambda v: float(v) * 1e3),   # -> $M
            col(TR_NOM, float), col(TR_REAL, float))


def ass():
    """num_wrk (persons), aggregate taxable ($M), aggregate total ($M), per year."""
    d = pd.read_excel(ASS_XLSX, sheet_name="data")
    w = {int(y): float(v) * 1e3 for y, v in zip(d["year"], d["num_wrk"]) if pd.notna(v)}
    tax = d["aggearn_tax_wage"].fillna(0) + d["aggearn_tax_se"].fillna(0)
    tot = d["aggearn_tot_wage"].fillna(0) + d["aggearn_tot_se"].fillna(0)
    return (w,
            {int(y): float(v) for y, v in zip(d["year"], tax) if v > 0},
            {int(y): float(v) for y, v in zip(d["year"], tot) if v > 0})


def price_index(y1, nom_apc, real_apc):
    """P(y) = nominal dollars per E.BASE_YEAR dollar: PCE through its last published year,
    then the TR's implied wage deflator (nominal minus real wage growth)."""
    p = pd.read_csv(PCE_CSV)
    p["year"] = pd.to_datetime(p["observation_date"]).dt.year
    pce = dict(zip(p["year"].astype(int), p.iloc[:, 1].astype(float)))
    base, last = pce[E.BASE_YEAR], max(pce)
    P = {y: pce[y] / base for y in pce}
    for y in range(last + 1, int(y1) + 1):
        infl = (1 + nom_apc.get(y, nom_apc[max(nom_apc)]) / 100.0) \
             / (1 + real_apc.get(y, real_apc[max(real_apc)]) / 100.0) - 1.0
        P[y] = P[y - 1] * (1 + infl)
    return P


def taxmax_series(years, awi):
    """$3,000 (<=1950), the EPUF top-code (1951-2006), AWI-indexed off 2006 after."""
    out = _duck("COPY (SELECT year, MAX(earnings) FROM annual WHERE earnings>0 "
                "GROUP BY year) TO '/dev/stdout' (FORMAT CSV, HEADER FALSE);")
    tm = {int(y): float(v) for y, v in (l.split(",") for l in out.strip().splitlines())}
    base = tm[2006]
    return {y: (tm[y] if y in tm else
                TAXMAX_1937_50 if y <= 1950 else base * awi[y] / awi[2006]) for y in years}


# --- EPUF composition and coverage --------------------------------------------

def epuf_cells():
    q = (f"COPY (SELECT a.year, d.sex, (a.year-d.yob) AS age, COUNT(*) AS n, "
         f"SUM(a.earnings) AS earn FROM annual a JOIN demographic d USING(id) "
         f"WHERE a.earnings>0 AND d.sex IN (1,2) AND d.yob IS NOT NULL "
         f"AND (a.year-d.yob) BETWEEN {COMP_LO} AND {COMP_HI} GROUP BY 1,2,3) "
         f"TO '/dev/stdout' (FORMAT CSV, HEADER TRUE);")
    return pd.read_csv(io.StringIO(_duck(q)))


def _edge_share(cells, y0, y1):
    w = cells[cells.year.between(y0, y1)]
    tot = w["n"].sum()
    return {(int(r.sex), int(r.age)): r.n / tot
            for _, r in w.groupby(["sex", "age"], as_index=False)["n"].sum().iterrows()}


def composition(cells, years):
    """Per-year (sex, age) share of positive earners over COMP_LO-COMP_HI; edge-held."""
    back, fwd = _edge_share(cells, *BACK), _edge_share(cells, *ANCHOR)
    per = {int(y): {(int(r.sex), int(r.age)): r.n / g.n.sum() for r in g.itertuples()}
           for y, g in cells.groupby("year")}
    return {y: (back if y < BACK[0] else
                per.get(y, fwd) if y <= DATA_LAST else fwd) for y in years}


def coverage(cells, lo, hi):
    """What the modelled age window misses, from EPUF.

    Returns (in_window shares per year for workers and earnings, by-age profiles per era).
    The per-year shares are the mechanical ceiling on model/benchmark; the by-age profiles
    say which ages the shortfall sits in and how much that has moved over time.
    """
    inw = cells.age.between(lo, hi)
    per = {}
    for col in ("n", "earn"):
        num = cells[inw].groupby("year")[col].sum()
        den = cells.groupby("year")[col].sum()
        per[col] = {int(y): float(v) for y, v in (num / den).items()}
    prof = {}
    for e in ERAS:
        w = cells[cells.year.between(*e)]
        for col in ("n", "earn"):
            g = w.groupby("age")[col].sum()
            prof[(e, col)] = (g.index.to_numpy(int), (g / g.sum()).to_numpy(float))
    return per, prof


def epuf_direct(lo, hi):
    """EPUF's own aggregate taxable earnings ($M) over the modelled ages, 1% scaled x100."""
    out = _duck(f"COPY (SELECT a.year, 100*SUM(a.earnings)/1e6 FROM annual a "
                f"JOIN demographic d USING(id) WHERE a.earnings>0 AND d.yob IS NOT NULL "
                f"AND (a.year-d.yob) BETWEEN {lo} AND {hi} GROUP BY 1) "
                f"TO '/dev/stdout' (FORMAT CSV, HEADER FALSE);")
    return {int(y): float(v) for y, v in (l.split(",") for l in out.strip().splitlines())}


# --- the model ----------------------------------------------------------------

def exp_tables(u):
    """Per age: sorted finite u, prefix sums of e^u, and the employed count N."""
    out = []
    for j in range(u.shape[1]):
        v = np.sort(u[np.isfinite(u[:, j]), j])
        out.append((v, np.concatenate([[0.0], np.cumsum(np.exp(v))]), v.size))
    return out


def profiles(fits, W, c0, c1):
    """{(sex, cohort): centred coefficients} from extrapolate_g_cohort's rule."""
    out = {}
    for sex in ("male", "female"):
        d = X.extrapolate(fits[fits.sex == sex], W, c0, c1, 5, 25, "index", 0.0)
        for r in d.itertuples():
            out[(sex, int(r.cohort))] = np.array([r.g0, r.g1, r.g2, r.g3])
    return out


def model_aggregate(prof, tables, taxmax, P, comp, cov, years, ages, condition, ymin_real):
    """Per year: model aggregate taxable and uncapped earnings ($M) over covered workers
    in the modelled age window, plus the worker share the Ymin conditioning would drop."""
    tt = (ages - 24) / 10.0 - E.T_CENTRE
    agg, unc, cens = {}, {}, {}
    for y in years:
        tax_sum = unc_sum = w_sum = drop = 0.0
        for sexname, sexcode in (("male", 1), ("female", 2)):
            for j, age in enumerate(ages):
                w = cov[y] * comp[y].get((sexcode, age), 0.0)
                if w <= 0:
                    continue
                a = prof[(sexname, y - age + 25)]
                g = a[0] + a[1] * tt[j] + a[2] * tt[j] ** 2 + a[3] * tt[j] ** 3 \
                    + np.log(P[y])                     # 2013 dollars -> nominal
                v, csum, n = tables[j]
                k = int(np.searchsorted(v, np.log(taxmax[y]) - g))
                mt = (np.exp(g) * csum[k] + taxmax[y] * (n - k)) / n
                mu = np.exp(g) * csum[-1] / n
                if condition == "ymin":                # renormalise onto Y >= Ymin
                    lo = int(np.searchsorted(v, np.log(ymin_real[y] * P[y]) - g))
                    if n - lo > 0:
                        kk = max(k, lo)
                        mt = (np.exp(g) * (csum[kk] - csum[lo])
                              + taxmax[y] * (n - kk)) / (n - lo)
                        mu = np.exp(g) * (csum[-1] - csum[lo]) / (n - lo)
                    drop += w * lo / n
                tax_sum += mt * w
                unc_sum += mu * w
                w_sum += w
        agg[y] = tax_sum / MUSD
        unc[y] = unc_sum / MUSD
        cens[y] = drop / w_sum
    return agg, unc, cens


# --- figures ------------------------------------------------------------------

def _frame(ax, y_lo, y_hi, ass_last):
    ax.axvspan(y_lo, y_hi, color="grey", alpha=0.08)
    ax.axvline(ass_last, color="grey", lw=0.8, ls="--")
    ax.set_xlabel("year")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def _row(axl, axr, bench, epuf, model, years, lo, hi, y_lo, y_hi, ass_last,
         ylab, title, bench_lab, cover=None):
    by = sorted(bench)
    ey = [y for y in sorted(epuf) if y in bench] if epuf else []
    xm = [y for y in years if y in bench]

    axl.plot(by, [bench[y] / 1e6 for y in by], color=C_BENCH, lw=2.2, label=bench_lab)
    if ey:
        axl.plot(ey, [epuf[y] / 1e6 for y in ey], color=C_EPUF, lw=1.4, marker="o", ms=2.5,
                 label=f"EPUF ages {lo}–{hi} (1% $\\times$100)")
    axl.plot(xm, [model[y] / 1e6 for y in xm], color=C_MODEL, lw=1.9, ls=":",
             label=f"GKOS cohort model, ages {lo}–{hi}")
    axl.set_yscale("log")
    axl.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    axl.set_ylabel(ylab)
    axl.set_title(f"{title}: levels — log scale", fontsize=10)
    axl.legend(frameon=False, loc="upper left", fontsize=8)
    _frame(axl, y_lo, y_hi, ass_last)

    axr.axhline(1.0, color=C_BENCH, lw=1.2)
    if cover is not None:
        cy = [y for y in by if y in cover]
        axr.plot(cy, [cover[y] for y in cy], color="0.55", lw=1.2, ls="-.",
                 label=f"EPUF share of earnings in {lo}–{hi} (ceiling)")
    if ey:
        axr.plot(ey, [epuf[y] / bench[y] for y in ey], color=C_EPUF, lw=1.6, marker="o",
                 ms=2.5, label="EPUF / benchmark")
    axr.plot(xm, [model[y] / bench[y] for y in xm], color=C_MODEL, lw=1.8, ls=":",
             label="model / benchmark")
    axr.set_ylabel("series / published total")
    axr.set_title(f"{title}: relative to the published TOTAL (all ages)", fontsize=10)
    axr.legend(frameon=False, loc="best", fontsize=8)
    _frame(axr, y_lo, y_hi, ass_last)


def figure(bench, epuf, model, unc_bench, unc_model, years, lo, hi, ass_last,
           cover_tax, path):
    fig, ax = plt.subplots(2, 2, figsize=(12.5, 8.0))
    _row(ax[0, 0], ax[0, 1], bench, epuf, model, years, lo, hi, BACK[0], EPUF_LAST,
         ass_last, "aggregate taxable earnings ($ trillions)", "Taxable (capped)",
         "benchmark: ASS taxable total (TR payroll after 2022)", cover_tax)
    _row(ax[1, 0], ax[1, 1], unc_bench, None,
         {y: unc_model[y] for y in years if y in unc_bench},
         [y for y in years if y in unc_bench], lo, hi, BACK[0], EPUF_LAST, ass_last,
         "aggregate uncapped earnings ($ trillions)", "Uncapped",
         "benchmark: ASS total covered earnings", cover_tax)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(f"{path}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)


def coverage_figure(prof, lo, hi, path):
    """Where the excluded earnings and workers sit, by single-year age and era."""
    fig, ax = plt.subplots(1, 2, figsize=(11.0, 4.0))
    cols = ["#2a78d6", "#7a5195", "#eb6834"]
    for k, (col, ttl) in enumerate((("n", "share of covered workers"),
                                    ("earn", "share of taxable earnings"))):
        a = ax[k]
        for c, e in zip(cols, ERAS):
            x, y = prof[(e, col)]
            a.plot(x, 100 * y, color=c, lw=1.4, label=f"{e[0]}–{e[1]}")
        a.axvspan(lo, hi, color="grey", alpha=0.10)
        a.set_xlabel("age")
        a.set_ylabel(f"{ttl} (%)")
        a.set_title(f"EPUF {ttl} by age — shaded = modelled {lo}–{hi}", fontsize=10)
        a.legend(frameon=False, fontsize=8)
        for side in ("top", "right"):
            a.spines[side].set_visible(False)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(f"{path}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits", default=f"{OUT}/g_cohort_quad_sel0.csv")
    ap.add_argument("--tag", default="quad_2070")
    ap.add_argument("--ages", type=int, nargs=2, default=[20, 70], metavar=("LO", "HI"))
    ap.add_argument("--condition", choices=["positive", "ymin"], default="positive")
    ap.add_argument("--n", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=20260821)
    ap.add_argument("--outdir", default=OUT)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    lo, hi = args.ages
    ages = np.arange(lo, hi + 1)
    # a cross-section in [Y0, Y1] over ages [lo, hi] needs cohorts (= year at age 25)
    # from Y0 - hi + 25 to Y1 - lo + 25, wider on BOTH sides than the shipped CSV's 1937-2100
    coh_lo, coh_hi = Y0 - hi + 25, Y1 - lo + 25

    cov, awi, trpay, nom_apc, real_apc = trustees()
    wrk, ass_tax, ass_tot = ass()
    cov.update(wrk)                                   # ASS through 2022, TR projection after
    years = [y for y in range(Y0, Y1 + 1) if y in cov]
    taxmax = taxmax_series(years, awi)
    P = price_index(Y1, nom_apc, real_apc)

    W = X.wage_log_index(coh_lo, coh_hi)
    prof = profiles(pd.read_csv(args.fits), W, coh_lo, coh_hi)

    cells = epuf_cells()
    comp = composition(cells, years)
    cov_per, cov_prof = coverage(cells, lo, hi)
    tables = exp_tables(E.simulate_u(np.random.default_rng(args.seed), args.n, ages))

    agg, unc, cens = model_aggregate(
        prof, tables, taxmax, P, comp, cov, years, ages, args.condition,
        {y: E.ymin(min(max(y, 1947), 2013)) for y in years})

    bench = dict(trpay); bench.update(ass_tax)
    ass_last = max(ass_tax)
    unc_bench = dict(ass_tot)
    epuf = epuf_direct(lo, hi)

    figure(bench, epuf, agg, unc_bench, unc, years, lo, hi, ass_last,
           cov_per["earn"], os.path.join(args.outdir, f"aggregate_taxable_dynamics_{args.tag}"))
    coverage_figure(cov_prof, lo, hi, os.path.join(args.outdir, f"age_coverage_{args.tag}"))

    def band(d, y0, y1):
        v = [d[y] for y in d if y0 <= y <= y1]
        return f"{np.mean(v):.3f} [{min(v):.3f}-{max(v):.3f}]" if v else "n/a"

    r = {y: agg[y] / bench[y] for y in years if y in bench}
    ru = {y: unc[y] / unc_bench[y] for y in years if y in unc_bench}
    re = {y: epuf[y] / bench[y] for y in epuf if y in bench}
    rme = {y: agg[y] / epuf[y] for y in epuf if y in agg}
    print(f"fits {args.fits}, ages {lo}-{hi}, cohorts from {coh_lo}, "
          f"conditioning on {args.condition}"
          + (f" (drops {100*np.mean(list(cens.values())):.2f}% of workers)"
             if args.condition == "ymin" else ""))
    print("\nCOVERAGE -- EPUF share inside the modelled age window (the mechanical ceiling):")
    for lab, y0, y1 in (("1951-1955", 1951, 1955), ("1975-1985", 1975, 1985),
                        ("2000-2006", 2000, 2006)):
        print(f"  {lab}: workers {band(cov_per['n'], y0, y1)}   "
              f"earnings {band(cov_per['earn'], y0, y1)}")
    print(f"\n  excluded ages, {ERAS[-1][0]}-{ERAS[-1][1]} average:")
    for col, name in (("n", "workers"), ("earn", "earnings")):
        x, y = cov_prof[(ERAS[-1], col)]
        below = 100 * y[x < lo].sum(); above = 100 * y[x > hi].sum()
        top = sorted(zip(x[(x < lo) | (x > hi)], 100 * y[(x < lo) | (x > hi)]),
                     key=lambda p: -p[1])[:4]
        print(f"    {name:9s} below {lo}: {below:5.2f}%   above {hi}: {above:5.2f}%"
              f"   biggest single ages: "
              + ", ".join(f"{int(a)} ({v:.2f}%)" for a, v in top))

    print("\nTAXABLE, vs the published TOTAL:")
    for lab, y0, y1 in (("pre-EPUF 1937-1950", 1937, 1950), ("in sample 1951-2006", 1951, 2006),
                        ("2007-2022 (ASS)", 2007, 2022), ("2023-2100 (TR)", 2023, 2100)):
        print(f"  {lab:22s} model {band(r, y0, y1)}   EPUF {band(re, y0, y1)}   "
              f"model/EPUF {band(rme, y0, y1)}")
    print("UNCAPPED, vs ASS total covered earnings:")
    for lab, y0, y1 in (("pre-EPUF 1937-1950", 1937, 1950), ("in sample 1951-2006", 1951, 2006),
                        ("2007-2022 (ASS)", 2007, 2022)):
        print(f"  {lab:22s} model {band(ru, y0, y1)}")
    print(f"\nwrote {args.outdir}/aggregate_taxable_dynamics_{args.tag}.pdf/.png "
          f"and age_coverage_{args.tag}.pdf/.png")


if __name__ == "__main__":
    main()
