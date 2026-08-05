#!/usr/bin/env python
"""Aggregate taxable earnings, three ways, year by year.

Cross-checks the fitted per-(year, sex) cross-sections against the two data
sources they sit between:

  1. model    -- integrate each fitted distribution to its mean taxable earnings
                 E[min(exp Y, taxmax)], scale by the sample count N and x100.
  2. EPUF     -- SUM(earnings) x100 straight from the microdata.
  3. ASS      -- reported_taxable_musd from Supplement Table 4.B1 (published).

All three are capped at the taxable maximum: EPUF `earnings` is top-coded there,
the model total caps exp(Y) at taxmax, and the Supplement column is reported
(taxable) earnings, not total covered earnings -- so they are like-for-like.

Two panels: levels on a log axis (secular-rise sanity check) and the ratio to
the published ASS total (the discriminating view -- 1.0 = exact agreement).

  python code/cross_sections/plot_aggregate_taxable.py
    -> output/cross_sections/aggregate_taxable.pdf (+ .png)
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

import crosssec_fit as cf

PARAMS = Path("output/cross_sections/cross_section_params.csv")
DB     = cf.DB
SCALE  = 100.0     # EPUF is a 1% sample -> x100 to population
MUSD   = 1e6       # dollars -> millions of USD (Supplement's unit)


def model_mean_taxable(row, taxmax):
    """E[min(exp Y, taxmax)] under the fitted distribution for one (year, sex).

    Integrate exp(y) f(y) up to log(taxmax) on a fine grid, then add the capped
    contribution taxmax * P(Y > log taxmax) of the mass above the cap."""
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
    # the Normal-Laplace pdf overflows to +inf ~30 sigma into the lower tail
    # (Mills ratio blows up where the density is negligible); zero those out.
    integrand = np.nan_to_num(np.exp(yy) * dens, nan=0.0, posinf=0.0, neginf=0.0)
    sf = float(np.clip(sf, 0.0, 1.0))
    return np.trapz(integrand, yy) + taxmax * sf


def model_totals():
    """Model-implied taxable total (millions USD) per year, summed over sexes."""
    tot = {}
    with PARAMS.open() as fh:
        for row in csv.DictReader(fh):
            year = int(row["year"])
            taxmax = float(row["highc"]) + cf.HIGH_MARGIN
            mean = model_mean_taxable(row, taxmax)
            tot[year] = tot.get(year, 0.0) + mean * int(row["n"]) * SCALE / MUSD
    return tot


def epuf_totals():
    """EPUF taxable total (millions USD) per year: SUM(earnings) x100, sexes 1&2."""
    import subprocess
    q = ("COPY (SELECT a.year, SUM(a.earnings) AS s FROM annual a JOIN demographic d "
         "USING(id) WHERE d.sex IN (1,2) AND a.earnings>0 GROUP BY a.year ORDER BY a.year) "
         "TO '/dev/stdout' (FORMAT CSV, HEADER FALSE);")
    out = subprocess.run(["duckdb", DB, "-c", q], capture_output=True, text=True, check=True).stdout
    return {int(y): float(s) * SCALE / MUSD for y, s in
            (ln.split(",") for ln in out.strip().splitlines())}


def ass_totals():
    """Published ASS reported taxable earnings (already millions USD) per year."""
    import subprocess
    q = ("COPY (SELECT year, reported_taxable_musd FROM supplement_4b1 "
         "WHERE reported_taxable_musd IS NOT NULL ORDER BY year) "
         "TO '/dev/stdout' (FORMAT CSV, HEADER FALSE);")
    out = subprocess.run(["duckdb", DB, "-c", q], capture_output=True, text=True, check=True).stdout
    return {int(y): float(v) for y, v in
            (ln.split(",") for ln in out.strip().splitlines())}


def main():
    model = model_totals()
    epuf  = epuf_totals()
    ass   = ass_totals()

    years = sorted(set(model) & set(epuf) & set(ass))
    m = np.array([model[y] for y in years])
    e = np.array([epuf[y]  for y in years])
    a = np.array([ass[y]   for y in years])
    yr = np.array(years)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2))

    # ---- levels (log y) ----
    ax1.plot(yr, a / 1e6, color="k",  lw=2.0, label="ASS reported taxable (published)")
    ax1.plot(yr, e / 1e6, color="C0", lw=1.6, ls="--", label="EPUF SUM(earnings) x100")
    ax1.plot(yr, m / 1e6, color="C3", lw=1.6, ls=":",  label="fitted model E[min(w, taxmax)]")
    ax1.set_yscale("log")
    ax1.set_ylabel("aggregate taxable earnings ($ trillions)")
    ax1.set_xlabel("year")
    ax1.set_title("Levels (log scale)")
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax1.legend(frameon=False, fontsize=8.5, loc="upper left")

    # ---- ratio to ASS ----
    ax2.axhline(1.0, color="k", lw=1.2)
    ax2.plot(yr, e / a, color="C0", lw=1.8, marker="o", ms=2.5, label="EPUF / ASS")
    ax2.plot(yr, m / a, color="C3", lw=1.8, marker="s", ms=2.5, label="model / ASS")
    ax2.set_ylabel("ratio to ASS reported taxable")
    ax2.set_xlabel("year")
    ax2.set_title("Relative to published ASS total (1.0 = exact)")
    ax2.legend(frameon=False, fontsize=9, loc="lower right")

    fig.suptitle("Aggregate taxable earnings: fitted model vs EPUF microdata vs ASS Table 4.B1",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out = "output/cross_sections/aggregate_taxable.pdf"
    fig.savefig(out)
    fig.savefig("output/cross_sections/aggregate_taxable.png", dpi=150)
    plt.close(fig)

    # brief console summary
    print(f"{'year':>4} {'ASS($M)':>12} {'EPUF/ASS':>9} {'model/ASS':>10}")
    for i, y in enumerate(years):
        if y % 5 == 0 or y == years[-1]:
            print(f"{y:>4} {a[i]:>12,.0f} {e[i]/a[i]:>9.3f} {m[i]/a[i]:>10.3f}")
    print(f"\nwrote {out} and .png")


if __name__ == "__main__":
    main()
