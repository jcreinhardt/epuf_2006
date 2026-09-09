#!/usr/bin/env python
"""Split the model's aggregate error into LEVEL and SHAPE, cell by cell against EPUF.

The aggregate figure compares the model to the published ASS total, which folds together the
model's error, EPUF's coverage of that total, and the age window.  This one holds all of that
fixed: every cell is weighted by EPUF's OWN worker count, so composition and worker totals
cancel and what is left is the model's error per covered worker.

EVERYTHING IS CAPPED ON BOTH SIDES.  EPUF `earnings` is already top-coded at the year's taxable
maximum, and the mean of a top-coded variable is not the mean of anything -- so the model is
clipped at the same cap and the comparison is exactly like-for-like, with no top-code bias to
argue about.  That makes this the taxable-earnings decomposition; the uncapped counterpart has
no EPUF measurement to stand on and is read off the aggregate figure instead.

THREE AGGREGATES over the same cells:

    EPUF                     sum n * mean(Y)
    model                    sum n * mean(min(Y_model, C))
    model at EPUF's level    the same, after shifting each cell's g so its mean LOG matches

so model/EPUF is the whole error, the third over EPUF is SHAPE alone, and their ratio is LEVEL
alone.  The split is exact, not a log-linearisation: the middle rung is a real aggregate.

WHAT IT SHOWS, for the smm-p50 fit.  SHAPE is 0.887 whichever level is used -- as it must be,
since re-levelling moves only g0 -- and the level is what changed:

    --level gksw   model/EPUF 1.060 = LEVEL 1.195 x SHAPE 0.887
    --level epuf   model/EPUF 0.915 = LEVEL 1.031 x SHAPE 0.887

The 1.195 is the GKSW-vs-EPUF population wedge in the MEAN, and it was cancelling against the
model's capped-shape shortfall to produce a total that looked better than either piece.

Run from the project root:
    python code/dynamics/plots/plot_level_shape_decomp.py [--profiles CSV] [--universe gksw]
Output: output/dynamics/plots/level_shape_decomp.{pdf,png}
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
sys.path.insert(0, "code/dynamics/plots")
import gcohort_model as E
import extrapolate_g_cohort as X
import plot_agg_tax_dynamics as A

OUT = "output/dynamics/plots"
PROFILES = "output/dynamics/g_cohort_smm_p50_relevelled_extrapolated.csv"
AGES = np.arange(20, 71)
YEARS = (1951, 2006)                          # EPUF's span
MIN_N = 50
ERAS = ((1951, 1965), (1966, 1980), (1981, 1995), (1996, 2006))
BANDS = ((20, 24), (25, 39), (40, 55), (56, 70))
C_TOT, C_LEVEL, C_SHAPE = "#1a1a19", "#eb6834", "#2a78d6"


def epuf_cells():
    """Per (year, sex, age): workers, total earnings, total log earnings -- positive earners,
    no screen, because ASS's universe is every covered worker."""
    q = (f"COPY (SELECT a.year, d.sex, (a.year-d.yob) AS age, COUNT(*) n, SUM(a.earnings) s, "
         f"SUM(LN(a.earnings)) sl FROM annual a JOIN demographic d USING(id) "
         f"WHERE a.earnings>0 AND d.sex IN (1,2) AND d.yob IS NOT NULL "
         f"AND a.year BETWEEN {YEARS[0]} AND {YEARS[1]} "
         f"AND (a.year-d.yob) BETWEEN {AGES[0]} AND {AGES[-1]} GROUP BY 1,2,3) "
         f"TO '/dev/stdout' (FORMAT CSV, HEADER TRUE);")
    d = pd.read_csv(io.StringIO(subprocess.run(["duckdb", A.DB, "-c", q], capture_output=True,
                                               text=True, check=True).stdout))
    return d[d.n >= MIN_N]


def cap_tables(u):
    """Per age: sorted finite u, prefix sums of e^u, prefix sums of u, and the count."""
    out = []
    for j in range(u.shape[1]):
        v = np.sort(u[np.isfinite(u[:, j]), j])
        out.append((v, np.concatenate([[0.0], np.cumsum(np.exp(v))]),
                    np.concatenate([[0.0], np.cumsum(v)]), v.size))
    return out


def capped(tab, g, lc):
    """(mean of min(Y, C), mean of log min(Y, C)) per positive earner; g, lc nominal logs."""
    v, ce, cv, n = tab
    k = int(np.searchsorted(v, lc - g))
    return ((np.exp(g) * ce[k] + np.exp(lc) * (n - k)) / n,
            (g * k + cv[k] + lc * (n - k)) / n)


def build(profiles, universe, n, seed):
    ep = epuf_cells()
    tab = cap_tables(E.simulate_u(np.random.default_rng(seed), n, AGES))
    prof = A.load_profiles(profiles, 1892, 2105)
    off = {k: (v.get("delta", 0.0) if universe == "epuf" else 0.0) for k, v in prof.items()}
    gt = {k: E.g_at(v, AGES) + off[k] for k, v in prof.items()}
    P = X.price_index(*YEARS)
    _, awi, _ = A.trustees()
    tm = A.taxmax_series(range(YEARS[0], YEARS[1] + 1), awi)

    rows = []
    for r in ep.itertuples():
        sexname = "male" if r.sex == 1 else "female"
        j, lc = int(r.age) - AGES[0], np.log(tm[r.year])
        g = gt[(sexname, r.year - r.age + 25)][j] + np.log(P[r.year])
        m, ml = capped(tab[j], g, lc)
        mle = r.sl / r.n
        s = 0.0                              # shift g so the model's capped mean log matches
        for _ in range(80):
            step = mle - capped(tab[j], g + s, lc)[1]
            s += step
            if abs(step) < 1e-10:
                break
        rows.append(dict(year=r.year, sex=sexname, age=r.age, n=r.n, epuf=r.s / r.n, model=m,
                         model_lv=capped(tab[j], g + s, lc)[0], dml=ml - mle))
    return pd.DataFrame(rows)


def ratios(d):
    """(total, shape-only, level-only) for a set of cells."""
    t = lambda c: float((d.n * d[c]).sum())
    return t("model") / t("epuf"), t("model_lv") / t("epuf"), t("model") / t("model_lv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", default=PROFILES)
    ap.add_argument("--universe", choices=["epuf", "gksw"], default="gksw")
    ap.add_argument("--n", type=int, default=400_000)
    ap.add_argument("--seed", type=int, default=20260821)
    ap.add_argument("--outdir", default=OUT)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    d = build(a.profiles, a.universe, a.n, a.seed)
    tot, shape, level = ratios(d)
    print(f"{a.profiles}  universe {a.universe}   {len(d)} cells, "
          f"{YEARS[0]}-{YEARS[1]}, ages {AGES[0]}-{AGES[-1]}, EPUF's own worker counts")
    print(f"  model / EPUF, taxable   {tot:.3f}  =  LEVEL {level:.3f}  x  SHAPE {shape:.3f}")
    e = d.assign(w=d.n * d.epuf)
    for s in ("male", "female"):
        x = e[e.sex == s]
        print(f"    {s:6s} mean log gap (model - EPUF), earnings-weighted "
              f"{float((x.w * x.dml).sum() / x.w.sum()):+.3f}")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, groups, key, lab in ((axes[0], ERAS, "year", "year"),
                                 (axes[1], BANDS, "age", "age")):
        cut = [ratios(d[d[key].between(lo, hi)]) for lo, hi in groups]
        x = np.arange(len(groups))
        # bars anchored AT 1.0 rather than at zero: these are ratios, and a bar chart with a
        # cut-off baseline exaggerates whatever sits above it
        for i, (col, name) in enumerate(((C_TOT, "model / EPUF"), (C_LEVEL, "level alone"),
                                         (C_SHAPE, "shape alone"))):
            v = np.array([c[(0, 2, 1)[i]] for c in cut])
            ax.bar(x + (i - 1) * .27, v - 1.0, .27, bottom=1.0, color=col, label=name)
        ax.axhline(1.0, color="0.4", lw=0.8)
        ax.set_xticks(x, [f"{lo}-{hi}" for lo, hi in groups], fontsize=8)
        ax.set_xlabel(lab)
        ax.set_ylabel("ratio to EPUF, taxable earnings per worker")
        ax.tick_params(labelsize=8)
        ax.margins(y=0.22)
        ax.legend(fontsize=7, frameon=False, ncol=3, loc="lower center")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    fig.suptitle(f"{os.path.basename(a.profiles)}: model / EPUF = {tot:.3f} "
                 f"= level {level:.3f} x shape {shape:.3f}", fontsize=10)
    fig.tight_layout()
    path = os.path.join(a.outdir, "level_shape_decomp")
    for ext in ("pdf", "png"):
        fig.savefig(f"{path}.{ext}", dpi=200, bbox_inches="tight")
    print(f"wrote {path}.pdf/.png")


if __name__ == "__main__":
    main()
