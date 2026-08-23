#!/usr/bin/env python
"""Extrapolate the per-cohort cubic g(t) off the estimated cohort edges, so that
every cohort 1937-2100 has a profile and the aggregate tracks the realized (then
projected) average-wage path.

`estimate_g_cohort.py` fits a cohort x sex cubic only where the published GKSW
moments cover the FULL age span 25-55, i.e. cohorts 1957-1983 (a "cohort" is the
year the cohort turns 25, GKSW's own convention).  The taxable-earnings validation
against the Annual Statistical Supplement needs cohorts 1937-2100, so the missing
ones are filled by the standard anchor rule, applied per sex and per direction:

  * SHAPE frozen at the nearest data edge.  g1, g2, g3 (the cubic in t centred on
    age 40) are set to their mean over the 5 edge cohorts -- 1957-1961 backward,
    1979-1983 forward.  They carry no secular trend worth extrapolating, so the
    edge average is the honest prior, and a 5-cohort mean damps the cohort-level
    noise that a single edge cohort would propagate to every extrapolated year.

  * LEVEL driven by the average-wage path.  g0 (log real earnings at age 40) is
    rigidly log-shifted off the same 5-cohort anchor,

        g0(c) = mean(g0 | anchor) + [ W(c) - mean(W(c') | c' in anchor) ]

    where W(y) is the log REAL average covered wage in BASE_YEAR dollars and a
    cohort is indexed by the year it turns 25, so W is only ever evaluated on
    1937-2100.  W splices the Supplement's realized average covered earnings
    (aggearn_tot / num_wrk, deflated by the same PCE index the estimation uses)
    through 2022 onto the 2023 Trustees Report's projected REAL wage growth
    thereafter -- the same wage path the TR taxable-payroll benchmark is built on.
    Real, not nominal, because the fitted g is in BASE_YEAR dollars; nominal
    conversion belongs downstream, at the taxable-maximum step.

Estimated cohorts (1957-1983) are kept VERBATIM; the rule fills only the two tails.

CAVEAT, and it is the first thing to look at in the output figure: over the
estimated cohorts men's g0 is FLAT (1957-1983 spread 0.085 log points) while W
rises 0.32 over the same span -- the regression of g0 on W has slope ~0 for men
(+1.2 for women).  So "shift the level by average wage growth" is not what the
observed male cohorts did, and the forward splice at 1984 puts a kink in the male
level path: flat in sample, then ~1.5%/yr.  That is a deliberate modelling choice
(it makes the model's aggregate track the published wage path, which is what the
Supplement comparison needs), not something the data imply.  The printed diagnostic
reports that slope every run; `--drift const` replaces the year-by-year index path
with a single constant average log growth rate, which changes the level path's
wiggles but not this discrepancy.

Run from the project root:
    python code/dynamics/extrapolate_g_cohort.py [--c0 1937] [--c1 2100]
        [--anchor 5] [--ref-age 25] [--drift index|const]
Output: output/dynamics/<stem of --fits>_extrapolated.csv
        output/dynamics/g_cohort_extrapolation.{pdf,png}
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gcohort_model as E

FITS = "output/dynamics/g_cohort_smm_mean.csv"
OUT = "output/dynamics"
ASS_XLSX = "raw_data/annual_statistical_supplement.xlsx"
PCE_CSV = "raw_data/deflator/DPCERG3A086NBEA.csv"
TR_XLSX = "raw_data/tr2023_summary.xlsx"
TR_REAL_WAGE = "Average Annual Real Wage in Covered Employment APC"
BACKFILL_N = 14          # years of realized growth averaged to walk W back before 1937

COEFS = ["g0", "g1", "g2", "g3"]
SHAPE = ["g1", "g2", "g3"]
STYLE = {"fit": dict(color="#1f6fb4", marker="o", label="estimated (GKSW full span)"),
         "extrap": dict(color="#d1642f", marker="s", label="extrapolated")}


def wage_log_index(y0, y1):
    """W(y): log REAL average covered wage in E.BASE_YEAR dollars, y0..y1.

    Supplement average covered earnings per worker (nominal) deflated by the PCE
    index through the last published year, then the Trustees Report's projected
    real wage growth (APC, percent per year) accumulated forward.
    """
    d = pd.read_excel(ASS_XLSX, sheet_name="data")
    nom = (d["aggearn_tot_wage"].fillna(0) + d["aggearn_tot_se"].fillna(0)) * 1e6 \
        / (d["num_wrk"] * 1e3)
    ass = {int(y): float(v) for y, v in zip(d["year"], nom) if pd.notna(v) and v > 0}

    p = pd.read_csv(PCE_CSV)
    p["year"] = pd.to_datetime(p["observation_date"]).dt.year
    pce = dict(zip(p["year"].astype(int), p.iloc[:, 1].astype(float)))
    base = pce[E.BASE_YEAR]

    last = max(ass)
    W = {y: float(np.log(ass[y] * base / pce[y])) for y in ass}

    # Before the Supplement starts (1937) there is no published covered-wage level, so walk
    # W back at the average realized real growth of the first BACKFILL_N years. Only the
    # aggregate comparison reaches there -- a 1937 cross-section needs cohorts back to 1907.
    first = min(ass)
    if y0 < first:
        seq = [W[y] for y in range(first, first + BACKFILL_N)]
        gb = float(np.mean(np.diff(seq)))
        for y in range(first - 1, int(y0) - 1, -1):
            W[y] = W[y + 1] - gb

    tr = pd.read_excel(TR_XLSX, sheet_name="Intermediate", header=0)
    tr = tr.rename(columns={tr.columns[0]: "year"})[["year", TR_REAL_WAGE]].dropna()
    apc = {int(y): float(v) for y, v in zip(tr["year"], tr[TR_REAL_WAGE])}
    apc_last = apc[max(apc)]
    for y in range(last + 1, int(y1) + 1):
        W[y] = W[y - 1] + float(np.log1p(apc.get(y, apc_last) / 100.0))
    return {y: W[y] for y in range(int(y0), int(y1) + 1)}


def anchor_block(cohorts, n, side):
    """The n edge cohorts on `side` ('back' or 'fwd') of the estimated range."""
    c = sorted(cohorts)
    return c[:n] if side == "back" else c[-n:]


def extrapolate(fit, W, c0, c1, n_anchor, ref_age, drift, const_g):
    """One sex: DataFrame of centred coefficients for every cohort in [c0, c1]."""
    fit = fit.sort_values("cohort")
    obs = fit["cohort"].to_numpy(int)
    ref = {c: W[c + ref_age - 25] for c in range(c0, c1 + 1)}

    blocks = {}
    for side in ("back", "fwd"):
        b = anchor_block(obs, n_anchor, side)
        m = fit[fit["cohort"].isin(b)]
        blocks[side] = dict(cohorts=b,
                            shape=m[SHAPE].mean().to_numpy(float),
                            g0=float(m["g0"].mean()),
                            wbar=float(np.mean([ref[c] for c in b])))

    rows = []
    for c in range(c0, c1 + 1):
        if c in obs:
            r = fit[fit["cohort"] == c].iloc[0]
            rows.append([c, "fit"] + [float(r[k]) for k in COEFS])
            continue
        side = "back" if c < obs[0] else "fwd"
        b = blocks[side]
        if drift == "index":
            shift = ref[c] - b["wbar"]
        else:                                    # constant average log growth
            shift = const_g * (c - float(np.mean(b["cohorts"])))
        rows.append([c, f"extrap_{side}", b["g0"] + shift, *b["shape"]])

    out = pd.DataFrame(rows, columns=["cohort", "source"] + COEFS)
    raw = np.array([E.uncentre(r) for r in out[COEFS].to_numpy(float)])
    for k, name in enumerate(["g0_raw", "g1_raw", "g2_raw", "g3_raw"]):
        out[name] = raw[:, k]
    return out


def diagnostics(fit, W, ref_age, label):
    """How the estimated level actually co-moves with the wage index."""
    c = fit["cohort"].to_numpy(int)
    w = np.array([W[y + ref_age - 25] for y in c])
    g0 = fit["g0"].to_numpy(float)
    b = np.polyfit(w, g0, 1)
    print(f"  {label:6s} g0 on W: slope {b[0]:+.3f}  corr {np.corrcoef(w, g0)[0, 1]:+.3f}"
          f"   g0 spread {g0.max() - g0.min():.3f} vs W spread {w.max() - w.min():.3f}")
    return b[0]


def figure(tab, obs_range, path):
    """Four coefficients x two sexes; estimated and extrapolated drawn apart."""
    fig, axes = plt.subplots(4, 2, figsize=(9.5, 10.0), sharex=True)
    titles = {"g0": "$a_0$  (level at age 40)", "g1": "$a_1$  (slope)",
              "g2": "$a_2$  (curvature)", "g3": "$a_3$  (cubic)"}
    for j, sex in enumerate(["male", "female"]):
        d = tab[tab["sex"] == sex]
        for i, k in enumerate(COEFS):
            ax = axes[i, j]
            # the two extrapolated blocks are drawn apart: one line across the
            # in-sample gap would falsely connect the backward and forward anchors
            first = True
            for blk in ("extrap_back", "extrap_fwd"):
                m = d["source"] == blk
                s = dict(STYLE["extrap"])
                if not first:
                    s.pop("label")
                ax.plot(d.loc[m, "cohort"], d.loc[m, k], lw=1.2, ms=0, **s)
                first = False
            m = d["source"] == "fit"
            ax.plot(d.loc[m, "cohort"], d.loc[m, k], ls="none", ms=4, mfc="none",
                    **STYLE["fit"])
            for c in obs_range:
                ax.axvline(c, color="0.75", lw=0.6, ls=":")
            if i == 0:
                ax.set_title(sex, fontsize=10)
            if j == 0:
                ax.set_ylabel(titles[k], fontsize=9)
            if i == 3:
                ax.set_xlabel("cohort (year at age 25)", fontsize=9)
            ax.tick_params(labelsize=8)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
    axes[0, 0].legend(fontsize=8, frameon=False, loc="upper left")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(f"{path}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits", default=FITS)
    ap.add_argument("--c0", type=int, default=1937)
    ap.add_argument("--c1", type=int, default=2100)
    ap.add_argument("--anchor", type=int, default=5, help="edge cohorts averaged")
    ap.add_argument("--ref-age", type=int, default=25,
                    help="age whose calendar year indexes the wage shift")
    ap.add_argument("--drift", choices=["index", "const"], default="index")
    ap.add_argument("--outdir", default=OUT)
    ap.add_argument("--tag", default="", help="suffix on the output files")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    fits = pd.read_csv(args.fits)
    lo, hi = int(fits["cohort"].min()), int(fits["cohort"].max())
    y_lo, y_hi = args.c0 + args.ref_age - 25, args.c1 + args.ref_age - 25
    W = wage_log_index(y_lo, y_hi)

    gbar = float(np.mean(np.diff([W[y] for y in sorted(W)])))
    print(f"wage index W: {y_lo}-{y_hi}, average log growth {gbar:+.5f}/yr "
          f"({100 * np.expm1(gbar):+.2f}%)")
    print(f"estimated cohorts {lo}-{hi}; anchors {lo}-{lo + args.anchor - 1} (back), "
          f"{hi - args.anchor + 1}-{hi} (fwd)")
    print("in-sample check -- the rule assumes slope 1:")
    for sex in ("male", "female"):
        diagnostics(fits[fits["sex"] == sex], W, args.ref_age, sex)

    parts = []
    for sex in ("male", "female"):
        d = extrapolate(fits[fits["sex"] == sex], W, args.c0, args.c1,
                        args.anchor, args.ref_age, args.drift, gbar)
        d.insert(0, "sex", sex)
        parts.append(d)
    tab = pd.concat(parts, ignore_index=True)

    # name the artifact after the fit it extrapolates, so --mode ols / smm-mean /
    # smm-quantiles inputs cannot silently overwrite each other's output
    stem = os.path.splitext(os.path.basename(args.fits))[0]
    csv = os.path.join(args.outdir, f"{stem}_extrapolated{args.tag}.csv")
    tab.to_csv(csv, index=False, float_format="%.6f")
    figure(tab, (lo, hi), os.path.join(args.outdir, f"g_cohort_extrapolation{args.tag}"))

    print(f"\nwrote {csv}  ({len(tab)} rows, cohorts {args.c0}-{args.c1}, both sexes)")
    for sex in ("male", "female"):
        d = tab[tab["sex"] == sex].set_index("cohort")
        j = pd.Series({c: d.loc[c, "g0"] for c in (args.c0, lo, hi, args.c1)})
        print(f"  {sex:6s} a0: {args.c0} {j[args.c0]:.3f} | {lo} {j[lo]:.3f} -> "
              f"{hi} {j[hi]:.3f} | {args.c1} {j[args.c1]:.3f}")
    print("  splice slope (log pts/cohort-yr), a0 either side of each edge:")
    for sex in ("male", "female"):
        d = tab[tab["sex"] == sex].set_index("cohort")["g0"]
        ins = (d[hi] - d[hi - 4]) / 4
        out = (d[hi + 5] - d[hi + 1]) / 4
        print(f"    {sex:6s} forward: in-sample {ins:+.4f}  extrapolated {out:+.4f}")


if __name__ == "__main__":
    main()
