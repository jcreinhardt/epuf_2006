#!/usr/bin/env python
"""GKOS (2021) Figure 12 -- "estimated model versus data: key moments" -- recomputed for ONE EPUF birth cohort, on
EPUF, on the GKOS process and on the modified nonemployment model (`nonemp_model.py`), by sex. Library + CLI; the
figure is `plots/plot_gkos_fig12.py`.

WHY. GKOS estimate every parameter of the earnings process -- the HIP dispersion, the AR(1) and its mixture
innovations, the transitory mixture -- by SMM on seven sets of moments (Appendix D.1), most of which are moments of
earnings CHANGES that a nonemployment spell moves a long way (an arc-percent change of -2 or +2). Their own
nonemployment block is a big part of how the benchmark fits those moments. So if the nonemployment block is replaced
by one estimated on EPUF, the remaining parameters would come out differently if re-estimated. These panels show
how far the untouched earnings parameters are from the data once only the nonemployment block changes.

THE SEVEN SETS GKOS TARGET (1,227 moments, equal weight 1/7 per set, arc-percent deviations):
  (i)   sd, skewness, kurtosis of ONE-year arc-percent earnings changes, 3 age groups x 13 RE groups   (117)
  (ii)  the same for FIVE-year changes                                                                  (117)
  (iii) impulse responses at 1-, 2-, 3-year horizons: E[arc change t-1 -> t+k | age, RE, arc change t-1 -> t]
  (iv)  the same at 5 and 10 years                                                             (iii + iv: 800)
  (v)   average dollar earnings at ages 25, 30, ..., 60 for 15 lifetime-earnings groups               (120)
  (vi)  the CDF of total years employed over ages 25-60                                                  (35)
  (vii) within-cohort variance of log earnings by age 25-60                                              (36)
Figure 12 shows six panels: sd / skewness / kurtosis of the five-year change by RE percentile (sets ii), log average
earnings growth 25 -> 55 by LE group (v), the employment CDF (vi) and the variance profile (vii).

DEFINITIONS, GKOS's (Sections 2.2, 5; Appendix C.2, D.1), applied identically to EPUF and to both models:
  Ymin_t    one quarter of full-time work at half the federal minimum wage, 260 x the minimum wage
            (guv_targets.sel0_threshold: GKSW's own minimum-wage matrix, the one definition in this repo);
  RE sample at t: earnings >= Ymin in t-1 and in at least two of t-5..t-2, age 25-54 at t-1;
  RE        mean over t-5..t-1 of max(Y, Ymin), real 2013$; percentile rank within the (cohort, t) cell (one age,
            so GKOS's age-dummy residualisation is moot), random tie-break (EPUF is random-rounded and capped);
  arc change  2 (Y_{t+5} - Y_t) / (Y_{t+5} + Y_t) on raw earnings, defined when at least one year is positive, so
            employed -> out is exactly -2 and out -> employed exactly +2; sd and the third and fourth STANDARDISED
            moments ("standardized moments", D.1), computed per 5-year age bin (age at t-1 25-29 ... 50-54, the five
            t's pooled) x 13 RE groups (1, 2-10, 11-20, ..., 81-90, 91-95, 96-99, 100) and averaged over the six
            bins (Figure 12 pools the age groups);
  LE sample: earnings >= Ymin in at least 15 of the ages 25-60; LE = mean earnings over 25-60, zeros included;
            15 groups (1, 2-5, 6-10, 11-20, ..., 81-90, 91-95, 96-97, 98-99, 100);
  growth    log E[Y_55 | LE group] - log E[Y_25 | LE group], zeros included (Section 5.1);
  employment CDF: P(years with Y >= Ymin over 25-60 <= k), k = 0..36, among people with at least one such year;
  variance  var(log Y_a | Y_a >= Ymin), each age 25-60 (one cohort, so no cohort dummies are needed).

THE MODELS GO THROUGH EPUF'S DISCLOSURE PROTECTION year by year (`epuf_disclosure.disclose`: cap at the taxable
maximum, random rounding, sub-$100 code) before anything is computed, so both sides carry the same artefacts. For
cohort 1937 the cap binds on 30-40% of men through the 1960s and 70s (ages 25-43), so the top RE groups are ranked
on a censored measure and the top of (a)-(c), (d) and (f) is the cap's arithmetic on EVERY line, not economics.
`cap_share` rows record the share at the cap by age so a reader can see where. Models: GKOS = GKOS's benchmark with
this repo's g(t) plus TR2023 mortality (as everywhere in the transition work); the modified model = the same with
the estimated nonemployment block. Both from estimate_nonemp.Problem (common random numbers, the cached inputs).

Run from the project root (the database is needed once, for the disclosure codes):
    python code/dynamics/gkos_moments.py [--yob 1937] [--spec absq_alpha] [--n-sim 100000]
Output: output/dynamics/gkos_fig12_yob<YOB>_<spec>.csv   (panel, sex, source, group, x, age, value, n)
  panel: arc_sd / arc_skew / arc_kurt (x = RE group midpoint percentile), le_growth (x = LE group midpoint),
         le_profile (x = LE group midpoint, age = 25..60 step 5, value = mean real earnings), emp_cdf (x = years),
         var_log (age), cap_share (age; share of the base at or above the cap),
         logy_mean / logy_sd / logy_skew / logy_kurt (age 20..65; moments of log real earnings among those at or
         above Y_min, the lifecycle version of GKSW's cross-sectional moments; capped like everything else)
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(PROJ, "code", "cross_sections"))
import epuf_disclosure as ED  # noqa: E402
import estimate_nonemp as EN  # noqa: E402
import nonemp_model as NM  # noqa: E402
from guv_targets import sel0_threshold  # noqa: E402

OUT_DEFAULT = os.path.join(PROJ, "output", "dynamics")
DB_MAIN = os.path.expanduser("~/PhD/projects/epuf_2006/processed_data/ssa.duckdb")   # worktrees carry a stub
A_LO, A_HI = 25, 60                      # GKOS's working life
K = 5                                    # the horizon Figure 12 shows
AGE_BINS = [(25, 29), (30, 34), (35, 39), (40, 44), (45, 49), (50, 54)]     # age at t-1
RE_GROUPS = [(1, 1), (2, 10), (11, 20), (21, 30), (31, 40), (41, 50), (51, 60), (61, 70), (71, 80), (81, 90),
             (91, 95), (96, 99), (100, 100)]
LE_GROUPS = [(1, 1), (2, 5), (6, 10), (11, 20), (21, 30), (31, 40), (41, 50), (51, 60), (61, 70), (71, 80),
             (81, 90), (91, 95), (96, 97), (98, 99), (100, 100)]
LE_MIN_YEARS = 15
PROFILE_AGES = list(range(25, 61, 5))


def percentile(x, rng):
    """1..100, equal-count, random tie-break."""
    order = np.lexsort((rng.random(x.size), x))
    r = np.empty(x.size, int)
    r[order] = np.arange(x.size)
    return (r * 100) // x.size + 1


def group_lookup(groups):
    g = np.full(101, -1, int)
    for i, (lo, hi) in enumerate(groups):
        g[lo:hi + 1] = i
    return g


def midpoints(groups):
    return [(lo + hi) / 2 for lo, hi in groups]


def std_moments(x):
    """sd, skewness m3/sd^3, kurtosis m4/sd^4 (not excess)."""
    x = np.asarray(x, float)
    if x.size < 3:
        return np.nan, np.nan, np.nan
    d = x - x.mean()
    sd = np.sqrt((d ** 2).mean())
    if sd == 0:
        return 0.0, np.nan, np.nan
    return sd, (d ** 3).mean() / sd ** 3, (d ** 4).mean() / sd ** 4


def arc_change_rows(E, ages, ymin, real, sex, source, rng):
    """Panels (a)-(c): standardised moments of the 5-year arc-percent change by RE group, averaged over age bins."""
    look = group_lookup(RE_GROUPS)
    per_bin = np.full((len(AGE_BINS), len(RE_GROUPS), 3), np.nan)
    n_tot = np.zeros(len(RE_GROUPS), int)
    adm = E >= ymin[None, :]
    for b, (lo, hi) in enumerate(AGE_BINS):
        pool = [[] for _ in RE_GROUPS]
        for a1 in range(lo, hi + 1):            # age at t-1
            j = a1 + 1 - ages[0]                # column of t
            if j + K >= E.shape[1]:
                continue
            insample = adm[:, j - 1] & (adm[:, j - 5:j - 1].sum(1) >= 2)
            if insample.sum() < 100:
                continue
            Yr = E[insample][:, j - 5:j] / real[None, j - 5:j]
            re = np.maximum(Yr, (ymin[j - 5:j] / real[j - 5:j])[None, :]).mean(1)
            grp = look[percentile(re, rng)]
            y0, y1 = E[insample, j] / real[j], E[insample, j + K] / real[j + K]
            ok = (y0 > 0) | (y1 > 0)
            arc = np.where(ok, 2 * (y1 - y0) / np.maximum(y1 + y0, 1e-300), np.nan)
            for g in range(len(RE_GROUPS)):
                pool[g].append(arc[(grp == g) & ok])
        for g in range(len(RE_GROUPS)):
            x = np.concatenate(pool[g]) if pool[g] else np.empty(0)
            per_bin[b, g] = std_moments(x)
            n_tot[g] += x.size
    mean = np.nanmean(per_bin, axis=0)
    rows = []
    for g, (lo, hi) in enumerate(RE_GROUPS):
        for m, name in enumerate(("arc_sd", "arc_skew", "arc_kurt")):
            rows.append((name, sex, source, f"{lo}-{hi}" if lo != hi else str(lo), midpoints(RE_GROUPS)[g], np.nan,
                         mean[g, m], int(n_tot[g])))
    return rows


def lifetime_rows(E, ages, ymin, real, sex, source, rng):
    """Panels (d) and (e), and the set-(v) profiles."""
    j0, j1 = A_LO - ages[0], A_HI - ages[0]
    W = E[:, j0:j1 + 1]
    emp = W >= ymin[None, j0:j1 + 1]
    yrs = emp.sum(1)
    rows = []
    # (e) employment CDF among people employed at least one year in 25-60
    y = yrs[yrs >= 1]
    for k in range(0, j1 - j0 + 2):
        rows.append(("emp_cdf", sex, source, "all", float(k), np.nan, (y <= k).mean(), int(y.size)))
    # (d) LE sample: >= 15 years employed; LE = mean earnings 25-60, zeros in
    le_s = yrs >= LE_MIN_YEARS
    Wr = W[le_s] / real[None, j0:j1 + 1]
    le = Wr.mean(1)
    grp = group_lookup(LE_GROUPS)[percentile(le, rng)]
    mids = midpoints(LE_GROUPS)
    for g, (lo, hi) in enumerate(LE_GROUPS):
        m = grp == g
        label = f"{lo}-{hi}" if lo != hi else str(lo)
        prof = {a: Wr[m][:, a - A_LO].mean() for a in PROFILE_AGES}
        for a in PROFILE_AGES:
            rows.append(("le_profile", sex, source, label, mids[g], float(a), prof[a], int(m.sum())))
        growth = np.log(prof[55]) - np.log(prof[25]) if prof[25] > 0 and prof[55] > 0 else np.nan
        rows.append(("le_growth", sex, source, label, mids[g], np.nan, growth, int(m.sum())))
    return rows


def variance_rows(E, ages, ymin, real, sex, source):
    """Panel (f): variance of log earnings among those at or above Ymin, by age."""
    rows = []
    for a in range(A_LO, A_HI + 1):
        j = a - ages[0]
        m = E[:, j] >= ymin[j]
        rows.append(("var_log", sex, source, "all", float(a), float(a), np.log(E[m, j]).var() if m.sum() > 1 else np.nan,
                     int(m.sum())))
    return rows


def logy_moment_rows(E, ages, ymin, real, sex, source):
    """Mean, sd, skewness and kurtosis of log real (2013$) earnings among those at or above Y_min, every age."""
    rows = []
    for j, a in enumerate(ages):
        m = E[:, j] >= ymin[j]
        if m.sum() < 30:
            continue
        ly = np.log(E[m, j] / real[j])
        sd, sk, ku = std_moments(ly)
        for name, v in (("logy_mean", ly.mean()), ("logy_sd", sd), ("logy_skew", sk), ("logy_kurt", ku)):
            rows.append((name, sex, source, "all", float(a), float(a), v, int(m.sum())))
    return rows


def cap_rows(E, ages, thr, sex, source):
    rows = []
    for a in range(A_LO, A_HI + 1):
        j = a - ages[0]
        rows.append(("cap_share", sex, source, "all", float(a), float(a), (E[:, j] >= thr[j]).mean(), int(E.shape[0])))
    return rows


def fig12_rows(E, ages, ymin, real, thr, sex, source, rng):
    """All panels for one (n, T) nominal earnings matrix (ages = columns), one sex, one source."""
    return (arc_change_rows(E, ages, ymin, real, sex, source, rng) + lifetime_rows(E, ages, ymin, real, sex, source, rng)
            + variance_rows(E, ages, ymin, real, sex, source) + cap_rows(E, ages, thr, sex, source)
            + logy_moment_rows(E, ages, ymin, real, sex, source))


def disclosed(E, years, codes, rng):
    """Nominal model earnings through EPUF's disclosure protection, column by column."""
    out = np.zeros_like(E)
    for j, y in enumerate(years):
        pos = E[:, j] > 0
        out[pos, j] = ED.disclose(E[pos, j], y, rng, codes[y])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yob", type=int, default=1937)
    ap.add_argument("--spec", default="absq_alpha", choices=tuple(k for k in EN.SPECS if k != "full"))
    ap.add_argument("--params", default=None, help="estimates CSV (default output/dynamics/nonemp_params_yob<YOB>_<spec>.csv)")
    ap.add_argument("--n-sim", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=20261006)
    ap.add_argument("--db", default=None, help="DuckDB with the EPUF tables (default: the local one, else the main checkout's)")
    ap.add_argument("--out", default=OUT_DEFAULT)
    args = ap.parse_args()

    db = args.db or (ED.DB if os.path.exists(ED.DB) and os.path.getsize(ED.DB) > 1e6 else DB_MAIN)
    ED.DB = db
    P = EN.Problem("/nonexistent", args.yob, args.n_sim, args.seed, "auto")
    ages = P.ages
    years = [args.yob + int(a) for a in ages]
    ymin = np.array([sel0_threshold(y) for y in years])
    codes = ED.epuf_codes_many(years)
    params = args.params or os.path.join(args.out, f"nonemp_params_yob{args.yob}_{args.spec}.csv")
    est = pd.read_csv(params).set_index("parameter").estimate
    theta = {"gcohort": EN.expand(EN.GKOS[args.spec], args.spec),
             args.spec: EN.expand([est[k] for k in EN.SPECS[args.spec]], args.spec)}
    print(f"yob {args.yob}: Ymin {ymin[A_LO - ages[0]]:.0f} at {A_LO} .. {ymin[A_HI - ages[0]]:.0f} at {A_HI}; "
          f"params {params}")
    rng = np.random.default_rng(args.seed)
    rows = []
    for sex in (1, 2):
        E = P.data_E[sex]
        rows += fig12_rows(E, ages, ymin, P.real, P.thr, sex, "epuf", rng)
        for src, th in theta.items():
            Em = NM.earnings(th, P.shocks[sex], sex, ages, P.q[sex], P.E, P.g[sex], P.logP)
            Em = disclosed(Em[(Em > 0).any(1)], years, codes, rng)
            rows += fig12_rows(Em, ages, ymin, P.real, P.thr, sex, src, rng)
        print(f"sex {sex}: EPUF n = {E.shape[0]:,}", flush=True)
    d = pd.DataFrame(rows, columns=["panel", "sex", "source", "group", "x", "age", "value", "n"])
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"gkos_fig12_yob{args.yob}_{args.spec}.csv")
    d.to_csv(path, index=False, float_format="%.6g")
    print("wrote", path)
    s = d[d.panel.isin(["arc_sd", "arc_skew", "arc_kurt", "le_growth"])]
    print(s.pivot_table(index=["panel", "sex", "x"], columns="source", values="value").round(3).to_string())
    e = d[(d.panel == "emp_cdf") & d.x.isin([0, 1, 5, 10, 18, 30, 35])]
    print(e.pivot_table(index=["sex", "x"], columns="source", values="value").round(3).to_string())


if __name__ == "__main__":
    main()
