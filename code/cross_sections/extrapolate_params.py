#!/usr/bin/env python
"""Stage 3: extrapolate the parameter surfaces to every birth cohort needed for
cross-sections over a target year range (default 1937-2100), by ANCHORING at the
recent data edge and driving only the location parameters with an external nominal
wage-growth series.

The joint smoothed-constrained fits (estimate_cross_sections.py) cover the years the data see (1951-2006),
and THOSE are the interpolation -- kept verbatim. To reach the cohorts a 1937-2100
panel needs (1860-2085 over ages 15-77) we extrapolate the missing years. The old
approach fit a global polynomial per parameter and let a free linear-in-year slope
carry the trend; that slope assumed constant nominal growth and so misfit the actual
DECELERATING wage path (in-sample +/-15%, ~1.9x too hot by 2099). This version fixes
that by construction, with three rules:

  * DROP the noisy tail: ignore fitted params after 2004 (the thinnest, most top-code-
    distorted years) and anchor on the 2000-2004 average per (sex, age).

  * FREEZE the shape parameters (men alpha/beta/tau; women sig1/sig2/w) at the NEAREST
    data edge -- the 2000-2004 average forward, the 1951-1955 average for pre-1951 years --
    constant across the extrapolated span. They carry no secular trend, so holding them
    fixed is the honest prior; anchoring backward on 1951-55 (not the far 2000-04 edge)
    keeps the extrapolated upper tail era-appropriate. The 2000-04 tail is a high-inequality
    tail, and dropping it onto the low pre-1951 taxable cap over-caps (too much earnings
    above the cap), which understated pre-1951 aggregate taxable earnings; the near edge
    fixes that. This mirrors the composition scheme in the validation plot, which likewise
    reaches to 1951-55 backward and 2000-04 forward.

    EXCEPTION -- men's alpha pre-1951. These years are before the data, so they inherit the 1951-55
    tail unadjusted, which lands ~5% under the ASS benchmark. So instead of freezing men's alpha we
    CALIBRATE it: a per-year MULTIPLICATIVE scale alpha *= k_y, one scalar against one published
    moment per year (aggearn_tot / num_wrk), solved by root-find so each year matches EXACTLY
    (calibrate_alpha_scale). Exactly identified, nothing overfitted -- and legitimate precisely
    because alpha is unidentified above the low pre-1951 cap, so the published mean is the only
    information about it. E[X] ~ alpha/(alpha-1) is monotone in alpha, so the solve is well posed in
    both directions, and k is bounded so k*alpha > 1 keeps every cell's mean finite. Women's params
    are held FIXED and enter as an offset, as does men's wage-driven location. beta/tau/nu still
    freeze/wage-shift as above; the scale is scoped to pre-1951 only, so the in-sample fits are
    untouched (a deliberate choice, leaving a step in alpha at the 1950/1951 splice).

  * DRIVE the location parameters (men nu; women mu1, mu2) by the published nominal
    wage series, as a rigid log-shift of the frozen 2000-2004 age profile:

        m(sex, age, y) = m0(sex, age) + [ G(y) - Gbar ]

    m0 = the 2000-2004 mean location; G(y) = cumulative log nominal wage -- the ASS's
    realized average covered earnings (log level) through 2004, spliced onto the
    Trustees Report's projected wage growth (APC) forward; Gbar = G averaged over
    2000-2004. Both women's means shift by the same G, so the gap is fixed and
    mu1 > mu2 for free. Nominal growth now EQUALS the published/projected wage path,
    the same assumption the TR taxable-payroll benchmark is built on.

In-sample (1951-2004) cells keep their iterated values; the anchor model fills only
the pre-data years (1937-1950, off the 1951-55 edge, walking G back with realized ASS
growth), the post-2004 years (2005-2100, off the 2000-04 edge, walking G forward with TR
growth), and the handful of sparse in-sample cells the fitter skipped. The retirement regime-switch needs no special
handling: shape is frozen per age and the location shifts per age, so nothing is ever
fit across ages and each age keeps its own 2000-2004 profile (retirement ages included).

  python code/cross_sections/extrapolate_params.py [--y0 1937] [--y1 2100]
    -> output/cross_sections/cross_section_params_extrapolated.csv
"""
import io
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd
from scipy.optimize import brentq

import crosssec_fit as cf   # DB, SIG_MIN

IN      = Path("output/cross_sections/cross_section_params_smoothed.csv")
OUT     = Path("output/cross_sections/cross_section_params_extrapolated.csv")
TR_XLSX = Path("raw_data/tr2023_summary.xlsx")
ASS_XLSX = Path("raw_data/annual_statistical_supplement.xlsx")
Y0, Y1  = 1937, 2100          # target year range for the synthesized cross-sections
ANCHOR  = (2000, 2004)        # forward anchor: shapes frozen + locations wage-shifted off here
BACK    = (1951, 1955)        # backward anchor for pre-1951 (mirrors the composition scheme)
CAL     = (1937, 1950)        # pre-1951 span the men-alpha tail scale is calibrated over
ALPHA_K_EPS = 1e-3            # margin keeping k*alpha strictly > 1 (finite uncapped mean)
ALPHA_K_HI  = 50.0            # upper bound on the per-year alpha scale
DATA_LAST = 2004              # last in-sample year kept (2005-06 dropped as noisy)
TR_WAGE_COL = "Average Annual Nominal Wage in Covered Employment APC"

# per sex: (model label, age ceiling, location params, shape params). Locations are
# rigid-shifted by the wage index; shapes are frozen at the 2000-2004 mean.
SPEC = {
    1: ("dpln",    77, ["nu"],         ["alpha", "beta", "tau"]),
    2: ("mixture", 74, ["mu1", "mu2"], ["sig1", "sig2", "w"]),
}
PARAM_COLS = ["alpha", "beta", "nu", "tau", "mu1", "mu2", "sig1", "sig2", "w"]


def wage_log_index(y0, y1):
    """G(y): cumulative log nominal wage over [y0, y1]. ASS realized average covered
    earnings (log level, interpolated across its pre-1951 gaps) through 2004, then the
    Trustees Report's projected wage growth (APC, % per year) spliced on forward."""
    # ASS historical log levels (annual 1951+, sparse 1937/40/45/50 before)
    out = subprocess.run(
        ["duckdb", cf.DB, "-c",
         "COPY (SELECT year, avg_total_earnings_usd FROM supplement_4b1 "
         "WHERE avg_total_earnings_usd IS NOT NULL AND year <= 2004 ORDER BY year) "
         "TO '/dev/stdout' (FORMAT CSV, HEADER FALSE);"],
        capture_output=True, text=True, check=True).stdout
    ay, av = zip(*[(int(a), float(b)) for a, b in
                   (l.split(",") for l in out.strip().splitlines())])
    ay, alog = np.array(ay), np.log(np.array(av))

    # TR projected nominal wage growth (annual percent change), 1960-2099
    tr = pd.read_excel(TR_XLSX, sheet_name="Intermediate", header=0)
    tr = tr.rename(columns={tr.columns[0]: "year"})[["year", TR_WAGE_COL]].dropna()
    apc = {int(r.year): float(getattr(r, "_2")) for r in tr.itertuples()}

    G = {}
    for y in range(int(y0), DATA_LAST + 1):
        G[y] = float(np.interp(y, ay, alog))                 # log level (exact at ASS years)
    apc_last = apc[max(apc)]
    for y in range(DATA_LAST + 1, int(y1) + 1):
        G[y] = G[y - 1] + np.log1p(apc.get(y, apc_last) / 100.0)   # accumulate TR growth
    return G


def anchors(df, window):
    """Mean of every parameter over [window] per (sex, age) -> dict (sex, age) -> Series."""
    win = df[(df["year"] >= window[0]) & (df["year"] <= window[1])]
    a = win.groupby(["sex", "age"])[PARAM_COLS].mean()
    return {k: a.loc[k] for k in a.index}


def _ass(col):
    """Column `col` of the ASS workbook as {year: value} (non-null)."""
    d = pd.read_excel(ASS_XLSX, sheet_name="data")
    return {int(y): float(v) for y, v in zip(d["year"], d[col]) if pd.notna(v)}


def ass_workers():
    """Covered-worker counts (persons) per year: ASS num_wrk (thousands -> persons)."""
    return {y: v * 1e3 for y, v in _ass("num_wrk").items()}


def ass_total_earnings():
    """Aggregate TOTAL (uncapped) covered earnings ($, not $M) per year: aggearn_tot wage + se."""
    d = pd.read_excel(ASS_XLSX, sheet_name="data")
    tot = d["aggearn_tot_wage"].fillna(0) + d["aggearn_tot_se"].fillna(0)
    return {int(y): float(v) * 1e6 for y, v in zip(d["year"], tot) if v > 0}


def back_composition():
    """The 1951-55 EPUF (sex, age) joint share of positive earners -- the pre-1951 worker
    composition (same window and slice the validation plot uses so the calibration targets exactly
    the aggregate the plot displays). Sums to 1 over ages 15-77, both sexes."""
    q = (f"COPY (SELECT d.sex, (a.year - d.yob) AS age, COUNT(*) AS n "
         f"FROM annual a JOIN demographic d USING(id) "
         f"WHERE a.earnings > 0 AND a.year BETWEEN {BACK[0]} AND {BACK[1]} "
         f"AND d.sex IN (1, 2) AND d.yob IS NOT NULL "
         f"AND (a.year - d.yob) BETWEEN 15 AND 77 GROUP BY 1, 2) "
         f"TO '/dev/stdout' (FORMAT CSV, HEADER TRUE);")
    out = subprocess.run(["duckdb", cf.DB, "-c", q], capture_output=True, text=True, check=True).stdout
    d = pd.read_csv(io.StringIO(out)); tot = d["n"].sum()
    return {(int(r.sex), int(r.age)): r.n / tot for r in d.itertuples()}


def _dpln_mean(alpha, beta, nu, tau):
    """UNCAPPED mean E[X] of a double Pareto-lognormal; INFINITE where alpha <= 1."""
    if alpha <= 1.0:
        return np.inf
    return np.exp(nu + tau * tau / 2) * (alpha * beta) / ((alpha - 1) * (beta + 1))


def _mix_mean(w, mu1, sig1, mu2, sig2):
    """UNCAPPED mean of a two-component lognormal mixture (always finite)."""
    return w * np.exp(mu1 + sig1 ** 2 / 2) + (1 - w) * np.exp(mu2 + sig2 ** 2 / 2)


def calibrate_alpha_scale(anc_back, G, Gbar_back):
    """Per-year MULTIPLICATIVE scale k_y on men's alpha over the pre-1951 span, solved so the model's
    implied UNCAPPED mean earnings per worker matches the ASS benchmark (aggearn_tot / num_wrk)
    EXACTLY, year by year. Women's mixture parameters are held fixed and enter as an offset, as does
    men's wage-driven location; only the men's tail index moves.

    These years are pure extrapolation -- EPUF starts in 1951, so no cell here is fit to data. We
    borrow the 1951-55 age PROFILE of alpha and rescale its level, one scalar per year against one
    published moment per year: exactly identified, nothing overfitted. A scale (not the additive
    shift used before) keeps the profile's shape in relative terms and cannot reorder ages.

    E[X] ~ alpha/(alpha-1) is strictly DECREASING in alpha, so each year is a monotone 1-D root-find
    -- unlike the in-sample eta multiplier, this direction is well posed both ways. k is bounded
    below so that k*alpha > 1 in every cell (finite mean) and above by ALPHA_K_HI; where the target
    lies outside the reachable range the year is clamped to the nearest bound.

    Returns ({year: k}, {year: model_uncapped/ASS ratio})."""
    comp = back_composition()
    cov, tot = ass_workers(), ass_total_earnings()
    yrs = [y for y in range(CAL[0], CAL[1] + 1) if y in cov and y in tot]
    men = {a: anc_back[(1, a)] for (s, a) in anc_back if s == 1}
    wom = {a: anc_back[(2, a)] for (s, a) in anc_back if s == 2}

    def model_pw(y, k):
        shift = G[y] - Gbar_back; s = 0.0
        for (sex, age), frac in comp.items():
            if sex == 1:
                b = men.get(age)
                if b is None:
                    continue
                m = _dpln_mean(k * b["alpha"], b["beta"], b["nu"] + shift, b["tau"])
            else:
                b = wom.get(age)
                if b is None:
                    continue
                m = _mix_mean(b["w"], b["mu1"] + shift, b["sig1"], b["mu2"] + shift, b["sig2"])
            if not np.isfinite(m):
                return np.inf
            s += m * frac
        return s

    a_min = min(b["alpha"] for b in men.values())
    k_lo = (1.0 + ALPHA_K_EPS) / a_min          # every k*alpha > 1 -> every cell mean finite
    scale, fit = {}, {}
    for y in yrs:
        target = tot[y] / cov[y]
        f_lo, f_hi = model_pw(y, k_lo) - target, model_pw(y, ALPHA_K_HI) - target
        if not np.isfinite(f_lo) or f_lo < 0:   # even the fattest allowed tail undershoots
            k = k_lo
        elif f_hi > 0:                          # even the thinnest still overshoots
            k = ALPHA_K_HI
        else:
            k = brentq(lambda v: model_pw(y, v) - target, k_lo, ALPHA_K_HI, xtol=1e-8, maxiter=100)
        scale[y] = float(k)
        fit[y] = model_pw(y, k) / target
    return scale, fit


def build(df, y0, y1):
    G = wage_log_index(y0, y1)
    Gbar_fwd  = np.mean([G[y] for y in range(ANCHOR[0], ANCHOR[1] + 1)])
    Gbar_back = np.mean([G[y] for y in range(BACK[0], BACK[1] + 1)])
    anc_fwd   = anchors(df, ANCHOR)     # forward / default edge (2000-2004)
    anc_back  = anchors(df, BACK)       # backward edge (1951-1955) for pre-1951 years
    kept = {(int(r.sex), int(r.age), int(r.year)): r          # iterated cells to keep verbatim
            for r in df[df["year"] <= DATA_LAST].itertuples()}

    # Pre-1951 men-alpha scale. Stage 1's constraint pins 1951 onward, but these years are BEFORE
    # the data and inherit the 1951-55 anchor unadjusted, which lands ~5% under the ASS benchmark.
    # One scalar per year on men's alpha closes that exactly; women's params stay fixed.
    a_scale, cal_fit = calibrate_alpha_scale(anc_back, G, Gbar_back)

    rows = []
    for sex, (model, a_hi, locs, shapes) in SPEC.items():
        for age in range(15, a_hi + 1):
            base_fwd  = anc_fwd.get((sex, age))
            base_back = anc_back.get((sex, age))
            for year in range(int(y0), int(y1) + 1):
                k = (sex, age, year)
                # pre-1951 anchors on the NEAR (1951-55) edge -- shape and location alike --
                # so the extrapolated tail is era-appropriate, not the fatter 2000-04 tail;
                # falls back to the forward edge only where 1951-55 lacks that (sex, age).
                if year < BACK[0] and base_back is not None:
                    base, Gbar = base_back, Gbar_back
                else:
                    base, Gbar = base_fwd, Gbar_fwd
                if k in kept:                                  # in-sample interpolation, verbatim
                    r = kept[k]
                    row = {p: getattr(r, p) for p in PARAM_COLS}
                elif base is not None:                         # anchor + wage-driven location
                    row = {p: float(base[p]) for p in shapes}
                    shift = G[year] - Gbar
                    for p in locs:
                        row[p] = float(base[p]) + shift
                    if sex == 1 and year < BACK[0] and base is base_back:
                        row["alpha"] *= a_scale.get(year, 1.0)       # per-year pre-1951 tail scale
                else:
                    continue                                   # no anchor for this (sex, age)
                if sex == 1:
                    row.update(mu1=np.nan, mu2=np.nan, sig1=np.nan, sig2=np.nan, w=np.nan)
                else:
                    row.update(alpha=np.nan, beta=np.nan, nu=np.nan, tau=np.nan)
                    row["sig1"] = max(row["sig1"], cf.SIG_MIN)
                    row["sig2"] = max(row["sig2"], cf.SIG_MIN)
                row.update(year=year, sex=sex, age=age, cohort=year - age, model=model)
                rows.append(row)

    full = pd.DataFrame(rows)
    cols = ["year", "sex", "age", "cohort", "model"] + PARAM_COLS
    full = full.reindex(columns=cols).sort_values(["sex", "age", "year"]).reset_index(drop=True)
    return full, {"scale": a_scale, "fit": cal_fit}


def main(y0=Y0, y1=Y1):
    df = pd.read_csv(IN)
    full, cal = build(df, y0, y1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    full.to_csv(OUT, index=False)

    n_kept = ((full["year"] >= 1951) & (full["year"] <= DATA_LAST)).sum()
    print(f"wrote {len(full)} rows -> {OUT}")
    print(f"  years {y0}-{y1}, cohorts {int(full.cohort.min())}-{int(full.cohort.max())}")
    print(f"  in-sample (iterated, verbatim-where-present): "
          f"{n_kept} cells over 1951-{DATA_LAST}")
    for sex, (model, a_hi, locs, _sh) in SPEC.items():
        s = full[full.sex == sex]
        loc = locs[0]
        print(f"  sex {sex} ({model}): ages 15-{a_hi}, {loc} "
              f"{s[loc].min():.2f}..{s[loc].max():.2f}")
        if sex == 2:
            assert (s["mu1"] >= s["mu2"]).all(), "mu1 < mu2 somewhere"
    if cal["fit"]:
        r, k = cal["fit"], cal["scale"]
        print(f"  pre-1951 men-alpha scale (per year, women fixed): "
              f"k {min(k.values()):.3f}@{min(k, key=k.get)} .. {max(k.values()):.3f}@{max(k, key=k.get)}")
        print(f"  uncapped model/ASS over {CAL[0]}-{CAL[1]}: "
              f"min {min(r.values()):.4f}  mean {np.mean(list(r.values())):.4f}  max {max(r.values()):.4f}")

if __name__ == "__main__":
    kw = {}
    for flag, key, cast in [("--y0", "y0", int), ("--y1", "y1", int)]:
        if flag in sys.argv:
            kw[key] = cast(sys.argv[sys.argv.index(flag) + 1])
    main(**kw)
