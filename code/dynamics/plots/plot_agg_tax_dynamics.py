#!/usr/bin/env python
"""Validate the extrapolated GKOS cohort profiles against published aggregate TAXABLE
earnings: the Annual Statistical Supplement (1937-2022) spliced onto the 2023 Trustees
Report taxable-payroll projection.  The dynamics counterpart of
code/cross_sections/plots/plot_agg_tax_total.py.

The benchmark is the PUBLISHED TOTAL, undivided.  The model covers ages AGE_LO-AGE_HI
(default 20-70) and falls short of the total by whatever those ages miss; `coverage()`
reports that gap by year and by single-year age, and EPUF is restricted to the SAME window
so EPUF/benchmark carries the identical mechanical shortfall.  20 and 70 bound where the
rest of the process is still defensible: below 20 the persistent component has no
definition (`gcohort_model.entry_sd` solves the age-20 initial condition; earlier drives
the variance negative), and above 70 GKOS's nonemployment logit has no retirement margin
(at z = 0 the incidence FALLS with age), so the model's old workers are barely more selected
than its young ones.  Worker COUNTS come from the ASS, so only their mean earnings are wrong,
and 71+ is ~1% of earnings.

Worker weights: workers(sex, age, y) = covered workers(y) x comp(sex, age, y), with covered
workers from ASS num_wrk then the TR projection, and comp the EPUF per-year (sex, age) share
of positive earners over ALL ages 15-77 (observed 1951-2004, edge-held outside).  The model
supplies mean earnings per covered worker, never the number of workers.

Per-cell means come from the simulated panel: with log Y = g_c(age) + u, one panel of u by
age gives every cell at once,

    E[min(Y, C) | Y > 0] = ( e^g * SUM_{u < b} e^u + C * #{u >= b} ) / N,   b = log C - g

over the N individuals with finite u.  Conditioning on Y > 0 rather than on the estimation
screen Y >= Ymin, because ASS covered workers are all positive earners (measured: the two
differ by under 0.1% of workers, since the nu shock puts the low mass at exactly zero).

Nominal throughout: g is in 2013 dollars and is inflated by `extrapolate_g_cohort.price_index`
before the taxable maximum applies ($3,000 to 1950, the EPUF top-code 1951-2006, AWI-indexed
off 2006 after).  The BOTTOM row drops the cap -- model uncapped earnings against ASS
aggearn_tot -- which is where tail-shape error shows, since a too-heavy upper tail still
reproduces taxable earnings once clipped.

Profiles are read from extrapolate_g_cohort.py's CSV, which by default already spans the
cohorts a 1937-2100 x 20-70 window needs (1892-2105); the script refuses a narrower file.

    python code/dynamics/plots/plot_agg_tax_dynamics.py [--profiles CSV] [--ages 20 70]
        [--renorm-comp] [--export CSV]
    -> output/dynamics/plots/aggregate_taxable_dynamics_<tag>.{pdf,png}
       output/dynamics/plots/age_coverage_<tag>.{pdf,png}
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

sys.path.insert(0, "code/dynamics")          # run from the project root, per repo convention
import gcohort_model as E
import extrapolate_g_cohort as X

DB = "processed_data/ssa.duckdb"
OUT = "output/dynamics/plots"
PROFILES = "output/dynamics/g_cohort_smm_quantiles_quad_extrapolated.csv"

Y0, Y1 = X.Y0, X.Y1
COMP_LO, COMP_HI = 15, 77          # EPUF ages the composition is built over (99.9% of earnings)
MUSD = 1e6
TAXMAX_1937_50 = 3000.0
BACK, ANCHOR, DATA_LAST = (1951, 1955), (2000, 2004), 2004
EPUF_LAST = 2006
ERAS = [(1951, 1955), (1975, 1985), (2000, 2006)]
C_BENCH, C_EPUF, C_MODEL = "#1a1a19", "#2a78d6", "#eb6834"


def _duck(q):
    return subprocess.run(["duckdb", DB, "-c", q], capture_output=True, text=True,
                          check=True).stdout


# --- published series ---------------------------------------------------------

def trustees():
    d = pd.read_excel(X.TR_XLSX, sheet_name="Intermediate", header=0)
    d = d.rename(columns={d.columns[0]: "year"})
    col = lambda c, f: {int(y): f(v) for y, v in zip(d["year"], d[c]) if pd.notna(v)}
    return (col("Thousands of Covered Workers", lambda v: float(v) * 1e3),
            col("Average Wage Index", float),
            col("Taxable Payroll, Billions", lambda v: float(v) * 1e3))   # -> $M


def ass():
    """num_wrk (persons), aggregate taxable ($M), aggregate total ($M), per year."""
    d = pd.read_excel(X.ASS_XLSX, sheet_name="data")
    w = {int(y): float(v) * 1e3 for y, v in zip(d["year"], d["num_wrk"]) if pd.notna(v)}
    tax = d["aggearn_tax_wage"].fillna(0) + d["aggearn_tax_se"].fillna(0)
    tot = d["aggearn_tot_wage"].fillna(0) + d["aggearn_tot_se"].fillna(0)
    return (w, {int(y): float(v) for y, v in zip(d["year"], tax) if v > 0},
            {int(y): float(v) for y, v in zip(d["year"], tot) if v > 0})


def taxmax_series(years, awi):
    """$3,000 (<=1950), the EPUF top-code (1951-2006), AWI-indexed off 2006 after."""
    out = _duck("COPY (SELECT year, MAX(earnings) FROM annual WHERE earnings>0 "
                "GROUP BY year) TO '/dev/stdout' (FORMAT CSV, HEADER FALSE);")
    tm = {int(y): float(v) for y, v in (l.split(",") for l in out.strip().splitlines())}
    return {y: (tm[y] if y in tm else TAXMAX_1937_50 if y <= 1950
                else tm[2006] * awi[y] / awi[2006]) for y in years}


# --- EPUF composition and coverage --------------------------------------------

def epuf_cells():
    q = (f"COPY (SELECT a.year, d.sex, (a.year-d.yob) AS age, COUNT(*) AS n, "
         f"SUM(a.earnings) AS earn FROM annual a JOIN demographic d USING(id) "
         f"WHERE a.earnings>0 AND d.sex IN (1,2) AND d.yob IS NOT NULL "
         f"AND (a.year-d.yob) BETWEEN {COMP_LO} AND {COMP_HI} GROUP BY 1,2,3) "
         f"TO '/dev/stdout' (FORMAT CSV, HEADER TRUE);")
    return pd.read_csv(io.StringIO(_duck(q)))


def _share(cells):
    tot = cells["n"].sum()
    return {(int(r.sex), int(r.age)): r.n / tot
            for r in cells.groupby(["sex", "age"], as_index=False)["n"].sum().itertuples()}


def composition(cells, years, lo, hi, renorm):
    """Per-year (sex, age) share of positive earners over COMP_LO-COMP_HI, edge-held; with
    `renorm`, renormalised within [lo, hi] so the modelled slice carries the whole total."""
    back, fwd = _share(cells[cells.year.between(*BACK)]), _share(cells[cells.year.between(*ANCHOR)])
    per = {int(y): _share(g) for y, g in cells.groupby("year")}
    comp = {y: (back if y < BACK[0] else per.get(y, fwd) if y <= DATA_LAST else fwd)
            for y in years}
    if renorm:
        for y in years:
            inw = {k: v for k, v in comp[y].items() if lo <= k[1] <= hi}
            tot = sum(inw.values())
            comp[y] = {k: v / tot for k, v in inw.items()}
    return comp


def coverage(cells, lo, hi):
    """EPUF share of workers/earnings inside the modelled window, per year; and by-age
    profiles per era, to say which ages the shortfall sits in."""
    inw = cells.age.between(lo, hi)
    per = {col: {int(y): float(v) for y, v in
                 (cells[inw].groupby("year")[col].sum() / cells.groupby("year")[col].sum()).items()}
           for col in ("n", "earn")}
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


def load_profiles(path, c0, c1):
    d = pd.read_csv(path)
    have = set(zip(d["sex"], d["cohort"].astype(int)))
    missing = [c for c in range(c0, c1 + 1) if ("male", c) not in have or ("female", c) not in have]
    if missing:
        sys.exit(f"{path} lacks cohorts {missing[0]}..{missing[-1]}; re-run "
                 f"extrapolate_g_cohort.py with --c0 {c0} --c1 {c1} (its defaults)")
    return {(r.sex, int(r.cohort)): np.array([r.g0, r.g1, r.g2, r.g3]) for r in d.itertuples()}


def model_aggregate(prof, tables, taxmax, P, comp, cov, years, ages):
    """Per year: model aggregate taxable and uncapped earnings ($M) over covered workers in
    the modelled age window."""
    tc = E.tt(ages) - E.T_CENTRE
    agg, unc = {}, {}
    for y in years:
        tax_sum = unc_sum = 0.0
        for sexname, sexcode in (("male", 1), ("female", 2)):
            for j, age in enumerate(ages):
                w = cov[y] * comp[y].get((sexcode, age), 0.0)
                if w <= 0:
                    continue
                g = E.gpoly(prof[(sexname, y - age + 25)], tc[j]) + np.log(P[y])  # -> nominal
                v, csum, n = tables[j]
                k = int(np.searchsorted(v, np.log(taxmax[y]) - g))
                tax_sum += w * (np.exp(g) * csum[k] + taxmax[y] * (n - k)) / n
                unc_sum += w * np.exp(g) * csum[-1] / n
        agg[y], unc[y] = tax_sum / MUSD, unc_sum / MUSD
    return agg, unc


# --- figures ------------------------------------------------------------------

def _frame(ax, ass_last):
    ax.axvspan(BACK[0], EPUF_LAST, color="grey", alpha=0.08)
    ax.axvline(ass_last, color="grey", lw=0.8, ls="--")
    ax.set_xlabel("year")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def _row(axl, axr, bench, epuf, model, lo, hi, ass_last, ylab, title, bench_lab, cover):
    by = sorted(bench)
    ey = [y for y in sorted(epuf) if y in bench] if epuf else []
    xm = [y for y in sorted(model) if y in bench]
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
    _frame(axl, ass_last)

    axr.axhline(1.0, color=C_BENCH, lw=1.2)
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
    _frame(axr, ass_last)


def figure(bench, epuf, model, unc_bench, unc_model, lo, hi, ass_last, cover, path):
    fig, ax = plt.subplots(2, 2, figsize=(12.5, 8.0))
    _row(ax[0, 0], ax[0, 1], bench, epuf, model, lo, hi, ass_last,
         "aggregate taxable earnings ($ trillions)", "Taxable (capped)",
         "benchmark: ASS taxable total (TR payroll after 2022)", cover)
    _row(ax[1, 0], ax[1, 1], unc_bench, None, unc_model, lo, hi, ass_last,
         "aggregate uncapped earnings ($ trillions)", "Uncapped",
         "benchmark: ASS total covered earnings", cover)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(f"{path}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)


def coverage_figure(prof, lo, hi, path):
    """Where the excluded earnings and workers sit, by single-year age and era."""
    fig, ax = plt.subplots(1, 2, figsize=(11.0, 4.0))
    for a, (col, ttl) in zip(ax, (("n", "share of covered workers"),
                                  ("earn", "share of taxable earnings"))):
        for c, e in zip(["#2a78d6", "#7a5195", "#eb6834"], ERAS):
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


def band(d, y0, y1):
    v = [d[y] for y in d if y0 <= y <= y1]
    return f"{np.mean(v):.3f} [{min(v):.3f}-{max(v):.3f}]" if v else "n/a"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", default=PROFILES, help="extrapolate_g_cohort.py's CSV")
    ap.add_argument("--tag", default=None, help="output suffix (default: from --profiles)")
    ap.add_argument("--ages", type=int, nargs=2, default=[X.AGE_LO, X.AGE_HI], metavar=("LO", "HI"))
    ap.add_argument("--n", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=20260821)
    ap.add_argument("--outdir", default=OUT)
    ap.add_argument("--export", default=None,
                    help="also write the model aggregate to this CSV, for "
                         "cross_sections/plots/plot_agg_tax_total.py --gkos")
    ap.add_argument("--renorm-comp", action="store_true",
                    help="renormalise the (sex, age) composition WITHIN the modelled ages so "
                         "the model's worker total equals the published covered-worker total. "
                         "Off, the model covers ages LO-HI only and falls short of the total by "
                         "whatever the other ages carry, which is what this figure reports. "
                         "REQUIRED when exporting for a figure whose other series are "
                         "per-covered-worker over ALL ages.")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    lo, hi = args.ages
    ages = np.arange(lo, hi + 1)
    tag = args.tag or os.path.basename(args.profiles).replace("g_cohort_", "").replace(
        "_extrapolated.csv", "") + f"_{lo}{hi}"

    cov, awi, trpay = trustees()
    wrk, ass_tax, ass_tot = ass()
    cov.update(wrk)                                   # ASS through 2022, TR projection after
    years = [y for y in range(Y0, Y1 + 1) if y in cov]
    taxmax = taxmax_series(years, awi)
    P = X.price_index(Y0, Y1)
    prof = load_profiles(args.profiles, Y0 - hi + 25, Y1 - lo + 25)

    cells = epuf_cells()
    comp = composition(cells, years, lo, hi, args.renorm_comp)
    cov_per, cov_prof = coverage(cells, lo, hi)
    tables = exp_tables(E.simulate_u(np.random.default_rng(args.seed), args.n, ages))
    agg, unc = model_aggregate(prof, tables, taxmax, P, comp, cov, years, ages)

    bench = {**trpay, **ass_tax}
    ass_last = max(ass_tax)
    epuf = epuf_direct(lo, hi)
    figure(bench, epuf, agg, ass_tot, unc, lo, hi, ass_last, cov_per["earn"],
           os.path.join(args.outdir, f"aggregate_taxable_dynamics_{tag}"))
    coverage_figure(cov_prof, lo, hi, os.path.join(args.outdir, f"age_coverage_{tag}"))

    r = {y: agg[y] / bench[y] for y in years if y in bench}
    ru = {y: unc[y] / ass_tot[y] for y in years if y in ass_tot}
    re = {y: epuf[y] / bench[y] for y in epuf if y in bench}
    rme = {y: agg[y] / epuf[y] for y in epuf if y in agg}
    print(f"profiles {args.profiles}, ages {lo}-{hi}, renorm_comp={args.renorm_comp}")
    print("\nCOVERAGE -- EPUF share inside the modelled age window (the mechanical ceiling):")
    for y0, y1 in ERAS:
        print(f"  {y0}-{y1}: workers {band(cov_per['n'], y0, y1)}   "
              f"earnings {band(cov_per['earn'], y0, y1)}")
    print("\nTAXABLE, vs the published TOTAL:")
    for lab, y0, y1 in (("pre-EPUF 1937-1950", 1937, 1950), ("in sample 1951-2006", 1951, 2006),
                        ("2007-2022 (ASS)", 2007, 2022), ("2023-2100 (TR)", 2023, 2100)):
        print(f"  {lab:22s} model {band(r, y0, y1)}   EPUF {band(re, y0, y1)}   "
              f"model/EPUF {band(rme, y0, y1)}")
    print("UNCAPPED, vs ASS total covered earnings:")
    for lab, y0, y1 in (("pre-EPUF 1937-1950", 1937, 1950), ("in sample 1951-2006", 1951, 2006),
                        ("2007-2022 (ASS)", 2007, 2022)):
        print(f"  {lab:22s} model {band(ru, y0, y1)}")

    if args.export:
        os.makedirs(os.path.dirname(os.path.abspath(args.export)), exist_ok=True)
        with open(args.export, "w") as fh:
            # price_2013_to_nominal travels with the series: any other real-2013$ series a
            # consumer puts on the same nominal axis needs exactly this factor.
            fh.write("year,agg_taxable_musd,agg_uncapped_musd,cov_share_workers,"
                     "cov_share_earnings,price_2013_to_nominal,renorm_comp\n")
            for y in years:
                fh.write(f"{y},{agg[y]:.6f},{unc[y]:.6f},"
                         f"{cov_per['n'].get(y, float('nan')):.6f},"
                         f"{cov_per['earn'].get(y, float('nan')):.6f},"
                         f"{P[y]:.8f},{int(args.renorm_comp)}\n")
        print(f"wrote {args.export}  ({len(years)} years, renorm_comp={args.renorm_comp})")
    print(f"\nwrote {args.outdir}/aggregate_taxable_dynamics_{tag}.pdf/.png and "
          f"age_coverage_{tag}.pdf/.png")


if __name__ == "__main__":
    main()
