#!/usr/bin/env python
"""Stage 3: extrapolate the parameter surfaces to every birth cohort needed for
cross-sections over a target year range (default 1937-2100), by ANCHORING at the
recent data edge and driving only the location parameters with an external nominal
wage-growth series.

The penalized fits (iterate_fit_smooth.py) cover the years the data see (1951-2006),
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

    EXCEPTION -- men's alpha pre-1951. The 1951-55 alpha is itself a censoring artifact: under
    the low 1950s cap ~45% of older men are top-coded, so the censored MLE parks the upper Pareto
    index below 1 (an INFINITE uncapped mean). Frozen back onto the even looser pre-1951 caps that
    over-states the tail -- invisible in taxable earnings (the cap clips it) but a 1.9x overshoot in
    the model's implied UNCAPPED mean vs ASS aggearn_tot. So instead of freezing men's alpha we
    CALIBRATE it: a uniform additive linear-in-year trend alpha += c0 + c1*(1951 - y), ONE trend
    for all ages (the pre-1951 years have no microdata to identify an age-specific tail), with
    (c0, c1) fit so the model's uncapped mean per worker matches ASS aggearn_tot over 1937-1950
    (calibrate_alpha_trend). Two parameters against a published moment -- low-dimensional by design,
    since alpha is unidentified above the cap. beta/tau/nu and all of women's params still freeze/
    wage-shift as above; the trend is scoped to pre-1951 only, so the in-sample fits are untouched
    (a deliberate choice, leaving a step in alpha at the 1950/1951 splice).

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

  python code/cross_sections/extrapolate_params.py [--y0 1937] [--y1 2100] [--preview]
    -> output/cross_sections/cross_section_params_extrapolated.csv
"""
import io
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd
from scipy.optimize import minimize

import crosssec_fit as cf   # DB, SIG_MIN

IN      = Path("output/cross_sections/cross_section_params_smoothed.csv")
OUT     = Path("output/cross_sections/cross_section_params_extrapolated.csv")
TR_XLSX = Path("raw_data/tr2023_summary.xlsx")
ASS_XLSX = Path("raw_data/annual_statistical_supplement.xlsx")
Y0, Y1  = 1937, 2100          # target year range for the synthesized cross-sections
ANCHOR  = (2000, 2004)        # forward anchor: shapes frozen + locations wage-shifted off here
BACK    = (1951, 1955)        # backward anchor for pre-1951 (mirrors the composition scheme)
CAL     = (1937, 1950)        # pre-1951 span the men-alpha tail trend is calibrated over
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


def calibrate_alpha_trend(anc_back, G, Gbar_back):
    """Fit a UNIFORM additive linear-in-year shift delta(y) = c0 + c1*(BACK[0] - y) to men's alpha
    over the pre-1951 span, so the model's implied UNCAPPED mean earnings per worker matches the ASS
    aggearn_tot benchmark year by year. ONE trend for all ages: the pre-1951 years have no microdata,
    so an age-specific tail is unidentified; we borrow the 1951-55 age PROFILE of alpha and move only
    its level/slope, against a single published moment per year (aggearn_tot / num_wrk). Deliberately
    2-dimensional to avoid overfitting alpha -- which is itself unidentified above the low pre-1951
    cap (censored-MLE parks it below 1, an infinite-mean tail). Only men's dPlN tail moves; women's
    finite mixture mean and men's wage-driven location enter each year's target as fixed offsets.

    Returns (c0, c1, {year: model_uncapped/ASS ratio}). Additive on alpha is well-suited: d E[X]/d
    alpha is far steeper at small alpha, so a uniform shift corrects the pathological old-age tails
    (alpha ~ 0.5) much more than the already-thin young-age tails (alpha ~ 2)."""
    comp = back_composition()
    cov, tot = ass_workers(), ass_total_earnings()
    yrs = [y for y in range(CAL[0], CAL[1] + 1) if y in cov and y in tot]
    men = {a: anc_back[(1, a)] for (s, a) in anc_back if s == 1}
    wom = {a: anc_back[(2, a)] for (s, a) in anc_back if s == 2}

    def model_pw(y, c0, c1):
        d = c0 + c1 * (BACK[0] - y); shift = G[y] - Gbar_back; s = 0.0
        for (sex, age), frac in comp.items():
            if sex == 1:
                b = men.get(age)
                if b is None:
                    continue
                m = _dpln_mean(b["alpha"] + d, b["beta"], b["nu"] + shift, b["tau"])
            else:
                b = wom.get(age)
                if b is None:
                    continue
                m = _mix_mean(b["w"], b["mu1"] + shift, b["sig1"], b["mu2"] + shift, b["sig2"])
            if not np.isfinite(m):
                return np.inf
            s += m * frac
        return s

    def obj(p):
        c0, c1 = p
        if c0 < 0 or c1 < 0:                          # tails only thin (or hold) going back
            return 1e9
        e = 0.0
        for y in yrs:
            mp = model_pw(y, c0, c1)
            if not np.isfinite(mp):                   # any alpha<=1 cell -> infinite mean -> reject
                return 1e9
            e += (np.log(mp / (tot[y] / cov[y]))) ** 2
        return e

    res = minimize(obj, [1.0, 0.05], method="Nelder-Mead",
                   options={"xatol": 1e-4, "fatol": 1e-8, "maxiter": 3000})
    c0, c1 = float(res.x[0]), float(res.x[1])
    fit = {y: model_pw(y, c0, c1) / (tot[y] / cov[y]) for y in yrs}
    return c0, c1, fit


def build(df, y0, y1):
    G = wage_log_index(y0, y1)
    Gbar_fwd  = np.mean([G[y] for y in range(ANCHOR[0], ANCHOR[1] + 1)])
    Gbar_back = np.mean([G[y] for y in range(BACK[0], BACK[1] + 1)])
    anc_fwd   = anchors(df, ANCHOR)     # forward / default edge (2000-2004)
    anc_back  = anchors(df, BACK)       # backward edge (1951-1955) for pre-1951 years
    kept = {(int(r.sex), int(r.age), int(r.year)): r          # iterated cells to keep verbatim
            for r in df[df["year"] <= DATA_LAST].itertuples()}

    # pre-1951 men-alpha trend RETIRED: stage 1's uncapped-mean penalty (mean_pen) now pins the
    # tail at the source, so the 1951-55 backward anchor is already mean-correct -- no separate
    # pre-1951 alpha calibration. (calibrate_alpha_trend + its ASS helpers are dead; removed in cleanup.)
    c0 = c1 = 0.0; cal_fit = {}

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
                        row["alpha"] += c0 + c1 * (BACK[0] - year)   # calibrated pre-1951 tail trend
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
    return full, {"c0": c0, "c1": c1, "fit": cal_fit}


def main(y0=Y0, y1=Y1, preview=False):
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
        r = cal["fit"]
        print(f"  pre-1951 men-alpha trend: alpha += {cal['c0']:.3f} + {cal['c1']:.4f}*(1951-y)  "
              f"(delta {cal['c0'] + cal['c1'] * (BACK[0] - CAL[0]):.3f}@{CAL[0]} .. "
              f"{cal['c0'] + cal['c1']:.3f}@1950), calibrated to ASS aggearn_tot")
        print(f"  uncapped model/ASS over {CAL[0]}-{CAL[1]}: "
              f"min {min(r.values()):.3f}  mean {np.mean(list(r.values())):.3f}  max {max(r.values()):.3f}")
    if preview:
        import extrapolate_preview as pv
        pv.render(df, full, 1951, DATA_LAST)


if __name__ == "__main__":
    kw = {}
    for flag, key, cast in [("--y0", "y0", int), ("--y1", "y1", int)]:
        if flag in sys.argv:
            kw[key] = cast(sys.argv[sys.argv.index(flag) + 1])
    kw["preview"] = "--preview" in sys.argv
    main(**kw)
