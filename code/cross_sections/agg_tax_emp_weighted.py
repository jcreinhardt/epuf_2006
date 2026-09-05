#!/usr/bin/env python
"""Aggregate TAXABLE (capped) earnings 1937-2099 from the extrapolated parameter surface,
weighted by the project_vu employment-by-(sex, single-year age) panel instead of the EPUF
composition that plot_agg_tax_total.py uses.

The employment panel (project_vu e6c, `full_{male,female}_emp_data.parquet`) is covered
workers by age 16-84 for every year 1937-2100: EPUF x100 in-sample (1951-2006), demographic
back-projection before, employment-rate x population projection after. Following the same
denominator-matching logic as plot_agg_tax_total.py, the panel is used only for the (sex,
age) COMPOSITION: each year it is normalized to shares and rescaled so the worker TOTAL
equals the published covered-worker count -- ASS num_wrk 1937-2022, the TR intermediate
projection 2023-2099. Model/benchmark is then a pure per-worker earnings comparison:

    taxable(y) = cov_workers(y) * SUM_{sex,age} share(sex,age,y) * E[min(X, taxmax(y))]

with E[min(X, cap)] the analytic-density integral per fitted cell (model_mean_taxable) and
taxmax the EPUF top-code in-sample, $3,000 before 1951, AWI-indexed after 2006. What this
buys over the EPUF-composition weighting: an OBSERVED/PROJECTED composition for every year
instead of freezing the 1951-55 / 2000-04 edges, so the post-2006 sex-age shift (boomer
aging, female share) is in the weights.

Cells with employment but no fitted distribution (men 78-84, women 75-84; params cover men
15-77, women 15-74) are skipped, NOT renormalized -- same convention as plot_agg_tax_total.
`coverage` in the output CSV is the employment share the summed cells carry; the total is
understated by roughly the uncovered share (old-age employment, ~1-3%).

2100 drops out: the parameter surface reaches it but the TR worker/AWI series end at 2099.

    python code/cross_sections/agg_tax_emp_weighted.py
      -> output/cross_sections/agg_taxable_emp_weighted.csv
         output/cross_sections/plots/aggregate_taxable_emp_weighted.pdf (+ .png)

NOTE the female counts file is a Dropbox online-only placeholder on this machine (0 bytes).
If the script exits asking for it: in Finder right-click the file -> Make Available Offline
(or open the folder in the Dropbox app), wait for the sync, rerun.
"""
import sys
from pathlib import Path

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from plot_agg_tax_total import (MUSD, ass_taxable, ass_workers, combined_benchmark,
                                model_means, taxmax_series, trustees,
                                C_BENCH, C_MODEL)

VU_DATA = Path("/Users/jr2728/Dropbox/GZ SSec RA share 2023-present/"
               "project_vu - Copy (2)/data/intermediate")
EMP_FILES = {1: VU_DATA / "full_male_emp_data.parquet",
             2: VU_DATA / "full_female_emp_data.parquet"}
PARAMS  = Path("output/cross_sections/cross_section_params_extrapolated.csv")
OUT_CSV = Path("output/cross_sections/agg_taxable_emp_weighted.csv")
OUT_FIG = Path("output/cross_sections/plots/aggregate_taxable_emp_weighted")


def emp_panel():
    """Long (year, sex, age, n) employment counts from the two wide project_vu parquets."""
    frames = []
    for sex, p in EMP_FILES.items():
        if not p.exists() or p.stat().st_size == 0:
            sys.exit(f"MISSING DATA: {p}\nis absent or a 0-byte Dropbox online-only "
                     "placeholder. In Finder, right-click it -> Make Available Offline, "
                     "wait for the sync to finish, then rerun.")
        w = pd.read_parquet(p)
        if "age" in w.columns:              # index sometimes round-trips as a column
            w = w.set_index("age")
        w.index = w.index.astype(int)
        long = (w.rename(columns=lambda c: int(c)).rename_axis("age").reset_index()
                  .melt(id_vars="age", var_name="year", value_name="n"))
        long["sex"] = sex
        frames.append(long)
    d = pd.concat(frames, ignore_index=True).dropna(subset=["n"])
    return d[d["n"] > 0]


def shares_by_year(emp):
    """Per-year (sex, age) employment share; sums to 1 within each year."""
    out = {}
    for y, g in emp.groupby("year"):
        tot = g["n"].sum()
        out[int(y)] = {(int(r.sex), int(r.age)): r.n / tot for r in g.itertuples()}
    return out


def aggregate(means, shares, cov, years):
    """Rows of (year, taxable $M total/men/women, employment-share coverage)."""
    rows = []
    for y in years:
        tot = {1: 0.0, 2: 0.0}
        covered = 0.0
        for (sex, age), frac in shares[y].items():
            mt = means.get((y, sex, age))
            if mt is not None and np.isfinite(mt):
                tot[sex] += mt * cov[y] * frac
                covered += frac
        rows.append({"year": y, "workers": cov[y], "coverage": covered,
                     "taxable_men_musd": tot[1] / MUSD, "taxable_women_musd": tot[2] / MUSD,
                     "taxable_total_musd": (tot[1] + tot[2]) / MUSD})
    return pd.DataFrame(rows)


def main():
    cov, awi, trpay = trustees()
    cov.update(ass_workers())                     # ASS num_wrk 1937-2022; TR keeps 2023+
    emp = emp_panel()
    shares = shares_by_year(emp)
    pyears = set(pd.read_csv(PARAMS, usecols=["year"])["year"].astype(int))
    years = sorted(pyears & set(cov) & set(shares))
    taxmax = taxmax_series(years, awi)
    means = model_means(PARAMS, taxmax)

    agg = aggregate(means, shares, cov, years)
    bench, ass_last = combined_benchmark(ass_taxable(), trpay)
    agg["bench_musd"] = agg["year"].map(bench)
    agg["ratio"] = agg["taxable_total_musd"] / agg["bench_musd"]
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(OUT_CSV, index=False)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.4))
    yrs = agg["year"].to_numpy()
    ax1.plot(yrs, agg["bench_musd"] / 1e6, color=C_BENCH, lw=2.2,
             label="benchmark: ASS taxable (1937–2022) + TR payroll (2023–99)")
    ax1.plot(yrs, agg["taxable_total_musd"] / 1e6, color=C_MODEL, lw=1.9, ls=":",
             label="model, employment-panel composition × ASS/TR workers")
    ax1.axvline(ass_last, color="grey", lw=0.8, ls="--")
    ax1.set_yscale("log"); ax1.set_xlabel("year")
    ax1.set_ylabel("aggregate taxable earnings ($ trillions)")
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax1.set_title("Taxable (capped): levels — log scale")
    ax1.legend(frameon=False, fontsize=8.5, loc="upper left")

    ax2.axhline(1.0, color=C_BENCH, lw=1.2)
    ax2.plot(yrs, agg["ratio"], color=C_MODEL, lw=1.8, ls=":", label="model / benchmark")
    ax2.plot(yrs, agg["coverage"], color="grey", lw=1.0, alpha=0.7,
             label="employment share covered by fitted cells")
    ax2.axvline(ass_last, color="grey", lw=0.8, ls="--")
    ax2.set_xlabel("year"); ax2.set_ylabel("ratio")
    ax2.set_title("Relative to benchmark (1.0 = exact)")
    ax2.legend(frameon=False, fontsize=8.5, loc="best")
    fig.tight_layout()
    OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_FIG.with_suffix(".pdf")); fig.savefig(OUT_FIG.with_suffix(".png"), dpi=150)

    print(f"{'year':>4} {'model($M)':>13} {'bench($M)':>13} {'mdl/bn':>7} {'cover':>6}")
    for r in agg.itertuples():
        if r.year % 10 == 0 or r.year in (years[0], years[-1], ass_last):
            print(f"{r.year:>4} {r.taxable_total_musd:>13,.0f} "
                  f"{r.bench_musd if pd.notna(r.bench_musd) else 0:>13,.0f} "
                  f"{r.ratio if pd.notna(r.ratio) else 0:>7.3f} {r.coverage:>6.1%}")
    print(f"\nwrote {OUT_CSV} and {OUT_FIG}.pdf/.png")


if __name__ == "__main__":
    main()
