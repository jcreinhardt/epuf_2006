#!/usr/bin/env python
"""One cohort's lifecycle profile: model vs data, by age, men and women.

Left column: MEAN LOG earnings, the targeted moment.  The GKSW sel0 points are what g was
fitted to; the model line is g(t) + E[u | u >= log(Ymin) - g(t)] from one simulated panel;
the EPUF line is the same statistic on EPUF (positive earners clearing the same nominal
screen), which shows the GKSW-vs-EPUF sample-composition wedge directly.  EPUF is top-coded,
so its mean log is biased down where the cap bites (before ~1980 in particular).

Right column: MEAN LEVEL earnings per positive earner in 2013 dollars, which is what the
aggregate validation runs on.  Model uncapped E[Y | Y > 0] and capped E[min(Y, C) | Y > 0]
against EPUF's mean of (top-coded) earnings, so the like-for-like pair is the two capped
series.  Ages run 20-70 here; the fit only saw 25-55.

Run from the project root:
    python code/dynamics/plots/plot_cohort_profile.py [--cohort 1970] [--profiles CSV ...]
Output: output/dynamics/plots/cohort_profile_<cohort>.{pdf,png}
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

sys.path.insert(0, "code/dynamics")          # run from the project root, per repo convention
import gcohort_model as E
import extrapolate_g_cohort as X
from guv_targets import sel0_threshold   # the screen: ONE definition

DB = "processed_data/ssa.duckdb"
OUT = "output/dynamics/plots"
AGES = np.arange(20, 71)
COLORS = ["#eb6834", "#7a5195", "#3a9d5d"]


def epuf_profile(cohort, sex):
    """Per age: (year, n, mean earnings, mean log earnings above the sel0 screen)."""
    rows = []
    for a in AGES:
        y = cohort + a - 25
        rows.append(f"SELECT {y} AS year, {a} AS age, {sel0_threshold(min(max(y, 1947), 2013)):.2f} AS thr")
    q = ("COPY (WITH c AS (" + " UNION ALL ".join(rows) + ") "
         "SELECT c.year, c.age, COUNT(*) AS n, AVG(a.earnings) AS mean_earn, "
         "AVG(CASE WHEN a.earnings >= c.thr THEN LN(a.earnings) END) AS meanlog "
         "FROM c JOIN annual a ON a.year = c.year JOIN demographic d ON d.id = a.id "
         f"WHERE a.earnings > 0 AND d.sex = {sex} AND a.year - d.yob = c.age "
         "GROUP BY 1, 2 ORDER BY 2) TO '/dev/stdout' (FORMAT CSV, HEADER TRUE);")
    out = subprocess.run(["duckdb", DB, "-c", q], capture_output=True, text=True, check=True)
    return pd.read_csv(io.StringIO(out.stdout)).set_index("age")


def taxmax():
    out = subprocess.run(["duckdb", DB, "-c", "COPY (SELECT year, MAX(earnings) FROM annual "
                          "GROUP BY 1) TO '/dev/stdout' (FORMAT CSV, HEADER FALSE);"],
                         capture_output=True, text=True, check=True).stdout
    return {int(y): float(v) for y, v in (l.split(",") for l in out.strip().splitlines())}


def model_curves(coef, cohort, tables, st, P, tm):
    """(meanlog, mean uncapped, mean capped) by age, 2013 dollars."""
    ml, mu, mc = [], [], []
    for j, a in enumerate(AGES):
        y = cohort + a - 25
        g = E.gpoly(coef, E.tt(a) - E.T_CENTRE)
        v, csum, n = tables[j]
        ym = E.ymin(y)
        ml.append(g + E.cond_mean(st[j], np.log(ym) - g))
        mu.append(np.exp(g) * csum[-1] / n)
        if y in tm:
            cap = tm[y] / P[y]
            k = int(np.searchsorted(v, np.log(cap) - g))
            mc.append((np.exp(g) * csum[k] + cap * (n - k)) / n)
        else:
            mc.append(np.nan)
    return np.array(ml), np.array(mu), np.array(mc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", type=int, default=1970)
    ap.add_argument("--profiles", nargs="+",
                    default=["output/dynamics/g_cohort_smm_quantiles_extrapolated.csv",
                             "output/dynamics/g_cohort_smm_mean_extrapolated.csv"])
    ap.add_argument("--n", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=20260821)
    ap.add_argument("--outdir", default=OUT)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    c = args.cohort

    u = E.simulate_u(np.random.default_rng(args.seed), args.n, AGES)
    st = E.suffix_tables(u)
    tables = []
    for j in range(AGES.size):
        v = np.sort(u[np.isfinite(u[:, j]), j])
        tables.append((v, np.concatenate([[0.0], np.cumsum(np.exp(v))]), v.size))
    P = X.price_index(c + AGES[0] - 25, c + AGES[-1] - 25)
    tm = taxmax()
    fits = {os.path.basename(p).replace("g_cohort_", "").replace("_extrapolated.csv", ""):
            pd.read_csv(p) for p in args.profiles}

    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5))
    for i, (sex, code, guv) in enumerate((("male", 1, "male"), ("female", 2, "female"))):
        tgt = E.load_moments(guv, "sel0")
        gages = np.array([a for a in E.AGES if (c, a) in tgt])
        gml = np.array([tgt[(c, a)][0] for a in gages])
        ep = epuf_profile(c, code)
        pe = np.array([P[c + a - 25] for a in ep.index])
        axl, axr = axes[i]
        axl.plot(gages, gml, "o", ms=4, color="0.1", mfc="none", label="GKSW sel0 (target)")
        axl.plot(ep.index, ep["meanlog"] - np.log(pe), "s", ms=3, color="#2a78d6",
                 label="EPUF, same screen (top-coded)")
        axr.plot(ep.index, ep["mean_earn"] / pe / 1e3, "s", ms=3, color="#2a78d6",
                 label="EPUF mean (top-coded)")
        for (name, d), col in zip(fits.items(), COLORS):
            r = d[(d["sex"] == sex) & (d["cohort"] == c)].iloc[0]
            ml, mu, mc = model_curves([r.g0, r.g1, r.g2, r.g3], c, tables, st, P, tm)
            axl.plot(AGES, ml, color=col, lw=1.8, label=f"model, {name}")
            axr.plot(AGES, mu / 1e3, color=col, lw=1.8, label=f"model uncapped, {name}")
            axr.plot(AGES, mc / 1e3, color=col, lw=1.4, ls="--", label=f"model capped, {name}")
        for ax in (axl, axr):
            ax.axvspan(25, 55, color="0.93", zorder=0)
            ax.set_xlabel("age")
            ax.tick_params(labelsize=8)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
        axl.set_ylabel(f"{sex}: mean log earnings (2013 $)")
        axr.set_ylabel(f"{sex}: mean earnings ($ thousand, 2013)")
        axl.legend(fontsize=7, frameon=False)
        axr.legend(fontsize=7, frameon=False, loc="upper left")
    fig.suptitle(f"cohort {c} (age 25 in {c}): model vs data by age; shaded = fitted span",
                 fontsize=10)
    fig.tight_layout()
    path = os.path.join(args.outdir, f"cohort_profile_{c}")
    for ext in ("pdf", "png"):
        fig.savefig(f"{path}.{ext}", dpi=200, bbox_inches="tight")
    print(f"wrote {path}.pdf/.png")


if __name__ == "__main__":
    main()
