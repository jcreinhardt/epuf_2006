#!/usr/bin/env python
"""Extrapolate the per-cohort g(t) off the estimated cohort edges, so that every cohort the
aggregate validation needs has a profile and the aggregate tracks the realized (then
projected) average-wage path.

`estimate_g_cohort.py` fits a cohort x sex polynomial only where the published GKSW moments
cover the full age span 25-55, i.e. cohorts 1957-1983 (a "cohort" is the year it turns 25).
The taxable-earnings validation covers years 1937-2100 over ages 20-70, so it needs cohorts
1937-70+25 = 1892 through 2100-20+25 = 2105 -- the defaults here.  The missing cohorts are
filled by the standard anchor rule, per sex and per direction:

  * SHAPE frozen at the nearest data edge: g1, g2 (and g3, zero for the default quadratic; in t centred on age 40) are set to
    their mean over the `--anchor` edge cohorts (1957-61 backward, 1979-83 forward).  They
    carry no secular trend worth extrapolating, and a 5-cohort mean damps the cohort-level
    noise a single edge cohort would propagate to every extrapolated year.

  * LEVEL driven by the average-wage path: g0 (log real earnings at age 40) is rigidly
    log-shifted off the same anchor,

        g0(c) = mean(g0 | anchor) + [ W(c + ref_age - 25) - mean(W | anchor) ]

    where W(y) is the log REAL average covered wage in BASE_YEAR dollars: the Supplement's
    aggearn_tot / num_wrk deflated by `price_index` through the last published year, then
    the 2023 Trustees Report's projected real wage growth, and before 1937 (no published
    level) walked back at the average realized growth of the first BACKFILL_N years.
    `--ref-age` picks the calendar year that indexes a cohort's shift; 25 is GKSW's cohort
    label, 40 the age g0 is the level at.  `--drift const` replaces the index path with one
    constant average growth rate.

Estimated cohorts are kept VERBATIM; the rule fills only the two tails.

CAVEAT, the first thing to look at in plots/plot_g_cohort.py's figure: over the estimated
cohorts men's g0 is FLAT (1957-1983 spread ~0.09 log points) while W rises ~0.3, so "shift
the level by average wage growth" is not what the observed male cohorts did, and the forward
splice puts a kink in the male level path.  That is a deliberate modelling choice (the
aggregate must track the published wage path for the Supplement comparison), not something
the data imply; the printed diagnostic reports the in-sample slope of g0 on W every run.

`price_index(y0, y1)` is also the section's ONE conversion between BASE_YEAR and nominal
dollars: GKSW's own PCE vintage (the one the targets were deflated with) where it exists,
chained on the current FRED PCE outside it, then on the Trustees Report's implied wage
deflator.  The plots import it; nothing re-codes it.

Run from the project root:
    python code/dynamics/extrapolate_g_cohort.py --fits output/dynamics/g_cohort_smm_mean.csv
Output: output/dynamics/<stem of --fits>_extrapolated[tag].csv
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "code/dynamics")          # run from the project root, per repo convention
import gcohort_model as E

OUT = "output/dynamics"
ASS_XLSX = "raw_data/annual_statistical_supplement.xlsx"
PCE_CSV = "raw_data/deflator/DPCERG3A086NBEA.csv"
TR_XLSX = "raw_data/tr2023_summary.xlsx"
TR_NOM, TR_REAL = ("Average Annual Nominal Wage in Covered Employment APC",
                   "Average Annual Real Wage in Covered Employment APC")
Y0, Y1, AGE_LO, AGE_HI = 1937, 2100, 20, 70   # the aggregate validation's window
C0, C1 = Y0 - AGE_HI + 25, Y1 - AGE_LO + 25    # cohorts it needs: 1892-2105
BACKFILL_N = 14          # years of realized growth averaged to walk W back before 1937

COEFS = ["g0", "g1", "g2", "g3"]


def trustees_apc():
    """TR intermediate projection: (nominal, real) average-wage growth, percent per year."""
    d = pd.read_excel(TR_XLSX, sheet_name="Intermediate", header=0)
    d = d.rename(columns={d.columns[0]: "year"})
    col = lambda c: {int(y): float(v) for y, v in zip(d["year"], d[c]) if pd.notna(v)}
    return col(TR_NOM), col(TR_REAL)


def price_index(y0, y1):
    """P(y) = nominal dollars per E.BASE_YEAR dollar, y0..y1."""
    p = pd.read_csv(PCE_CSV)
    p["year"] = pd.to_datetime(p["observation_date"]).dt.year
    fred = dict(zip(p["year"].astype(int), p.iloc[:, 1].astype(float)))
    nom, real = trustees_apc()
    P = {y: E.pce(y) / E.pce(E.BASE_YEAR) for y in range(1947, 2015)}    # GKSW vintage
    for y in range(1946, min(fred) - 1, -1):                             # chain on FRED
        P[y] = P[y + 1] * fred[y] / fred[y + 1]
    for y in range(2015, int(y1) + 1):
        if y in fred and y - 1 in fred:
            P[y] = P[y - 1] * fred[y] / fred[y - 1]
        else:                                                            # TR wage deflator
            infl = (1 + nom.get(y, nom[max(nom)]) / 100) / (1 + real.get(y, real[max(real)]) / 100)
            P[y] = P[y - 1] * infl
    return {y: P[y] for y in range(int(y0), int(y1) + 1) if y in P}   # FRED starts 1929


def wage_log_index(y0, y1):
    """W(y): log REAL average covered wage in E.BASE_YEAR dollars, y0..y1."""
    d = pd.read_excel(ASS_XLSX, sheet_name="data")
    nom = (d["aggearn_tot_wage"].fillna(0) + d["aggearn_tot_se"].fillna(0)) * 1e6 \
        / (d["num_wrk"] * 1e3)
    ass = {int(y): float(v) for y, v in zip(d["year"], nom) if pd.notna(v) and v > 0}
    first, last = min(ass), max(ass)
    P = price_index(first, max(y1, last))
    W = {y: float(np.log(ass[y] / P[y])) for y in ass}
    gb = float(np.mean(np.diff([W[y] for y in range(first, first + BACKFILL_N)])))
    for y in range(first - 1, int(y0) - 1, -1):
        W[y] = W[y + 1] - gb
    _, real = trustees_apc()
    for y in range(last + 1, int(y1) + 1):
        W[y] = W[y - 1] + float(np.log1p(real.get(y, real[max(real)]) / 100.0))
    return {y: W[y] for y in range(int(y0), int(y1) + 1)}


def extrapolate(fit, W, c0, c1, n_anchor, ref_age, drift, const_g, beta=1.0):
    """One sex: DataFrame of centred (and raw) coefficients for every cohort in [c0, c1]."""
    fit = fit.sort_values("cohort").set_index("cohort")
    obs = fit.index.to_numpy(int)
    ref = {c: W[c + ref_age - 25] for c in range(c0, c1 + 1)}
    anchor = {"back": obs[:n_anchor], "fwd": obs[-n_anchor:]}
    # a hinge-disciplined fit (--mode smm-p50) carries the out-of-span shape in extra
    # columns; they are shape like g1..g3, so the same edge-freezing rule applies
    cols = COEFS + [c for c in [*E.HINGES, "delta"] if c in fit.columns]
    rows = []
    for c in range(c0, c1 + 1):
        if c in obs:
            rows.append([c, "fit", *fit.loc[c, cols].to_numpy(float)])
            continue
        side = "back" if c < obs[0] else "fwd"
        m = fit.loc[anchor[side], cols].mean()
        dW = ref[c] - np.mean([ref[a] for a in anchor[side]])
        if drift == "index":
            shift = dW                                   # g0 tracks the wage index 1:1
        elif drift == "fitted":
            shift = beta * dW                            # ... at the IN-SAMPLE slope instead
        else:
            shift = const_g * (c - float(np.mean(anchor[side])))
        rows.append([c, f"extrap_{side}", m["g0"] + shift, *m[cols[1:]].to_numpy(float)])
    out = pd.DataFrame(rows, columns=["cohort", "source"] + cols)
    raw = np.array([E.uncentre(r) for r in out[COEFS].to_numpy(float)])
    for k, name in enumerate(COEFS):
        out[f"{name}_raw"] = raw[:, k]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits", default=f"{OUT}/g_cohort_smm_mean.csv")
    ap.add_argument("--c0", type=int, default=C0)
    ap.add_argument("--c1", type=int, default=C1)
    ap.add_argument("--anchor", type=int, default=5, help="edge cohorts averaged")
    ap.add_argument("--ref-age", type=int, default=25,
                    help="age whose calendar year indexes the wage shift")
    ap.add_argument("--drift", choices=["index", "fitted", "const"], default="index",
                    help="how g0 moves off the anchor. index: one for one with the real "
                         "average covered wage -- the published wage path the aggregate "
                         "benchmark is built on. fitted: at the slope actually estimated in "
                         "sample, clipped to --beta-clip; men's raw slope is NEGATIVE, which "
                         "is not credible extrapolated for a century, so the clip does real "
                         "work and 0 means a flat real profile. const: one average log "
                         "growth rate.")
    ap.add_argument("--beta-clip", type=float, nargs=2, default=[0.0, 1.0],
                    metavar=("LO", "HI"), help="bounds on the --drift fitted slope")
    ap.add_argument("--outdir", default=OUT)
    ap.add_argument("--tag", default="", help="suffix on the output file")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    fits = pd.read_csv(args.fits)
    lo, hi = int(fits["cohort"].min()), int(fits["cohort"].max())
    W = wage_log_index(args.c0 + args.ref_age - 25, args.c1 + args.ref_age - 25)
    gbar = float(np.mean(np.diff([W[y] for y in sorted(W)])))
    print(f"wage index W: average log growth {gbar:+.5f}/yr ({100 * np.expm1(gbar):+.2f}%)")
    print(f"estimated cohorts {lo}-{hi}; anchors {lo}-{lo + args.anchor - 1} (back), "
          f"{hi - args.anchor + 1}-{hi} (fwd)")
    print("in-sample check -- the rule assumes slope 1 of g0 on W:")
    parts = []
    for sex in ("male", "female"):
        f = fits[fits["sex"] == sex]
        w = np.array([W[c + args.ref_age - 25] for c in f["cohort"]])
        g0 = f["g0"].to_numpy(float)
        print(f"  {sex:6s} slope {np.polyfit(w, g0, 1)[0]:+.3f}  corr {np.corrcoef(w, g0)[0, 1]:+.3f}"
              f"   g0 spread {np.ptp(g0):.3f} vs W spread {np.ptp(w):.3f}")
        raw_b = float(np.polyfit(w, g0, 1)[0])
        b_hat = float(np.clip(raw_b, *args.beta_clip))
        if args.drift == "fitted":
            print(f"         drift slope: fitted {raw_b:+.3f} -> using {b_hat:.3f}")
        d = extrapolate(f, W, args.c0, args.c1, args.anchor, args.ref_age, args.drift,
                        gbar, b_hat)
        d.insert(0, "sex", sex)
        parts.append(d)
    tab = pd.concat(parts, ignore_index=True)

    stem = os.path.splitext(os.path.basename(args.fits))[0]
    csv = os.path.join(args.outdir, f"{stem}_extrapolated{args.tag}.csv")
    tab.to_csv(csv, index=False, float_format="%.6f")
    print(f"wrote {csv}  ({len(tab)} rows, cohorts {args.c0}-{args.c1}, both sexes)")
    for sex in ("male", "female"):
        d = tab[tab["sex"] == sex].set_index("cohort")["g0"]
        print(f"  {sex:6s} g0: {args.c0} {d[args.c0]:.3f} | {lo} {d[lo]:.3f} -> {hi} {d[hi]:.3f}"
              f" | {args.c1} {d[args.c1]:.3f};  forward splice slope in-sample "
              f"{(d[hi] - d[hi - 4]) / 4:+.4f} vs extrapolated {(d[hi + 5] - d[hi + 1]) / 4:+.4f}")


if __name__ == "__main__":
    main()
