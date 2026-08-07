#!/usr/bin/env python
"""Estimate the earnings cross-section for every (year, sex, single-year age) cell
and dump the fitted parameters to one tidy CSV.

Men are fit with the double Pareto-lognormal, women with the two-component
lognormal mixture (the pairing from the 1990 scripts), doubly censored at LOWC /
taxmax-HIGH_MARGIN -- now sliced by single-year age as well as year and sex.
Three speedups keep the ~6.4k-cell sweep to well under a minute:

  1. one DB pull per year (not per cell) -- the JOIN and duckdb spawn happen 56
     times, not thousands; taxmax comes free as that year's MAX(earnings).
  2. parallel across years (one worker per year, both sexes, all ages).
  3. warm starts along age: within a (year, sex) the fitted params of one age seed
     the next age's optimiser, evaluated alongside a robust cold start (multi-start)
     and kept only if it wins on likelihood -- see the keep-best note in fit_year.

Only cells with at least MIN_N positive-earnings observations are fit; smaller
cells are skipped for now. BLAS is pinned to one thread per worker so the many
small optimisations don't oversubscribe cores.

  python code/cross_sections/estimate_cross_sections.py [--jobs N]
    -> output/cross_sections/cross_section_params.csv
"""
import os
# pin BLAS to one thread BEFORE numpy/scipy import -> no oversubscription across workers
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import csv
import sys
import subprocess
from io import StringIO
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd
from scipy.optimize import brentq
import crosssec_fit as cf

YEARS  = range(1951, 2007)   # full EPUF annual span (heavily top-censored pre-1980)
MIN_N  = 1000                # skip cells with fewer positive-earnings observations
MATCH_AGES = (15, 77)        # men cells in the year's aggregate moment; also the per-worker denominator
ASS_XLSX = Path("raw_data/annual_statistical_supplement.xlsx")   # uncapped-mean target
MOMENT_TOL = 1e-3            # relative tolerance on the per-year aggregate-mean match
ETA_HI     = 256.0           # ceiling on the per-year multiplier: the dPlN tail is fully thinned to
                             # the lognormal-body floor well before this, so hitting it means the
                             # target sits below that floor (a ~1-2% residual thinning cannot remove)
OUT    = Path("output/cross_sections/cross_section_params.csv")
# per-sex plumbing: label, fitter, warm-start packer
SEX = {1: ("male",   cf.fit_dpln,    cf.dpln_theta),
       2: ("female", cf.fit_mixture, cf.mix_theta)}
COLS = ["year", "sex", "age", "model", "n", "n_low", "n_high", "negll", "converged",
        "alpha", "beta", "nu", "tau",              # dPlN
        "mu1", "mu2", "sig1", "sig2", "w",         # mixture
        "info_alpha", "info_beta", "info_nu", "info_tau",              # dPlN theta-info
        "info_mu1", "info_mu2", "info_sig1", "info_sig2", "info_w",    # mixture theta-info
        "lowc", "highc", "p_low_model", "p_high_model", "eta_year"]    # eta_year: the year's multiplier


def load_year(year):
    """All positive-earnings (sex, age, earnings) rows for one year, in one pull."""
    q = ("SELECT d.sex, a.year - d.yob AS age, a.earnings "
         "FROM annual a JOIN demographic d USING(id) "
         f"WHERE a.year={int(year)} AND a.earnings>0 AND d.sex IN (1,2)")
    out = subprocess.run(["duckdb", "-readonly", cf.DB, "-noheader", "-csv", "-c", q],
                         capture_output=True, text=True, check=True).stdout
    return pd.read_csv(StringIO(out), header=None, names=["sex", "age", "earnings"])


def ass_uncapped_target():
    """ASS average UNCAPPED earnings per covered worker ($/worker) per year: (aggearn_tot_wage
    + aggearn_tot_se) / num_wrk, annual 1937-2022. The published mean the censored MLE can't see
    (the mass above the cap) -- the per-year target the moment match pins the model to. Same
    definition as ass_unc in plot_aggregate_taxable_extrapolated, so the fit hits what's judged."""
    d = pd.read_excel(ASS_XLSX, sheet_name="data")
    tot = d["aggearn_tot_wage"].fillna(0) + d["aggearn_tot_se"].fillna(0)   # $M
    out = {}
    for y, t, nw in zip(d["year"], tot, d["num_wrk"]):
        if t > 0 and pd.notna(nw) and nw > 0:
            out[int(y)] = float(t) * 1e6 / (float(nw) * 1e3)               # $ per worker
    return out


def _fit_cells(by_age, fit, pack, highc, mean_pen_of=None):
    """Warm-start-along-age multi-start keep-best over a sex's cells. mean_pen_of(age)->(eta,w)
    or None adds the uncapped-mean penalty per cell (men). Returns {age: row dict}."""
    out, prev = {}, None
    for age in sorted(by_age):                             # sweep ages upward
        x = by_age[age]
        extra = {} if mean_pen_of is None else {"mean_pen": mean_pen_of(age)}
        # multi-start keep-best: robust cold start AND the warm neighbour, lowest-negll converged.
        # L-BFGS-B reports success at local optima too, so seeds must be compared -- warm alone can
        # lock a whole year into a worse basin (the 1957 men's upper-tail collapse).
        cands = [fit(x, cf.LOWC, highc, start=None, **extra)]
        if prev is not None:
            cands.append(fit(x, cf.LOWC, highc, start=prev, **extra))
        conv = [c for c in cands if c["converged"]]
        r = min(conv or cands, key=lambda c: c["negll"])
        prev = pack(r) if r["converged"] else None
        out[age] = r
    return out


def _cell_mean(sex, r):
    """Analytic UNCAPPED mean E[X] of a fitted cell, by model."""
    if sex == 1:
        return cf.dpln_mean(r["alpha"], r["beta"], r["nu"], r["tau"])
    return cf.mix_mean(r["mu1"], r["mu2"], r["sig1"], r["sig2"], r["w"])


def fit_year(year, target_unc=None):
    """Fit every qualifying (sex, age) cell for one year, matching the year's UNCAPPED aggregate
    mean to the ASS target. The moment couples ALL cells -- men and women, both sexes -- only
    through the scalar aggregate S = sum_c w_c E[X]_c, so the constrained fit decomposes
    (dual/rank-1, per the mean-constrained-MLE skill): condition on ONE multiplier eta and each
    cell solves independently  min negll_c + eta*w_c*E[X]_c  (fit_dpln / fit_mixture mean_pen);
    an outer 1-D root-find sets eta so S = target. eta>=0 only THINS an over-heavy censored tail
    and is 0 where the model does not overshoot (high-cap years), so well-fit years are untouched.

    Both sexes carry the SAME eta: under a tight cap women are also 15-25% top-coded (1951-65),
    so a men-only correction over-thins the men to absorb women's inflated censored tail. The
    joint multiplier thins each sex's unidentified tail in proportion to its own overshoot."""
    df = load_year(year)
    highc = float(df["earnings"].max()) - cf.HIGH_MARGIN   # taxmax(year) - margin
    lo_a, hi_a = MATCH_AGES
    by_age = {sex: {a: sub["earnings"].to_numpy(dtype=float)
                    for a, sub in df.loc[df["sex"] == sex].groupby("age") if len(sub) >= MIN_N}
              for sex in SEX}
    # per-worker-share denominator = obs in the FITTED in-window cells (both sexes), so the cell
    # shares w_c sum to 1 over exactly the cells that enter the aggregate S = sum_c w_c E[X]_c.
    # (Using all-15-77 earners here instead would leave sum w_c ~ 0.99 -- the unfitted age-extreme
    # cells are ~9% of cells but ~0.6-1% of workers -- and the moment match would miss by that gap.)
    ntot = sum(x.size for sex in SEX for a, x in by_age[sex].items() if lo_a <= a <= hi_a)
    in_win = lambda a: lo_a <= a <= hi_a and ntot > 0
    w_of = {sex: {a: by_age[sex][a].size / ntot for a in by_age[sex]} for sex in SEX}
    ages_win = {sex: [a for a in sorted(by_age[sex]) if in_win(a)] for sex in SEX}

    # ---- bounded base fit at eta=0 for both sexes (men's alpha>1 -> finite E[X]) ----
    base = {sex: _fit_cells(by_age[sex], SEX[sex][1], SEX[sex][2], highc,
                            mean_pen_of=lambda a, s=sex: (0.0, w_of[s][a]))
            for sex in SEX}

    def s_full(fits):                      # composition-weighted uncapped mean over in-window cells
        return sum(w_of[sex][a] * _cell_mean(sex, fits[sex][a])
                   for sex in SEX for a in ages_win[sex])

    base_theta = {sex: {a: SEX[sex][2](base[sex][a]) for a in ages_win[sex]} for sex in SEX}
    def refit(eta):                        # in-window cells refit at eta, from the FIXED base start so
        f = {sex: dict(base[sex]) for sex in SEX}   # refit(.) is a pure function of eta (brentq needs
        for sex in SEX:                             # that); warm-chaining would make refit(0) path-
            for a in ages_win[sex]:                 # dependent through the near-flat censored tail
                f[sex][a] = SEX[sex][1](by_age[sex][a], cf.LOWC, highc,
                                        start=base_theta[sex][a], mean_pen=(eta, w_of[sex][a]))
        return f

    eta, fits = 0.0, base
    any_win = ages_win[1] or ages_win[2]
    S0 = s_full(base)
    if target_unc is not None and any_win and S0 > target_unc > 0:    # overshoot -> thin to target
        # log-secant seed: the censored tail thins ~exponentially in eta, so log S(eta) is
        # near-linear; probe S(1) and interpolate log S from (0,S0),(1,S1) to the target. Works
        # under heavy tails (needs no finite variance, unlike the Gaussian seed). The grow-then-
        # brentq envelope below is correct regardless of the seed, so a rough seed just saves probes.
        S1 = s_full(refit(1.0))
        eta0 = np.log(target_unc / S0) / np.log(S1 / S0) if S1 < S0 else 1.0
        hi = float(np.clip(eta0, 0.1, ETA_HI))
        s_hi = s_full(refit(hi))
        while s_hi > target_unc and hi < ETA_HI:                      # seed too low -> grow bracket
            hi *= 4.0
            s_hi = s_full(refit(hi))
        if s_hi > target_unc:         # target sits below the tail-free body floor -> thin maximally
            eta = hi
        else:                         # S(eta) monotone decreasing: brentq on the scalar residual
            eta = brentq(lambda e: s_full(refit(e)) - target_unc, 0.0, hi,
                         xtol=1e-4, rtol=MOMENT_TOL, maxiter=60)
        fits = refit(eta)

    rows = []
    for sex in SEX:
        for a, r in fits[sex].items():
            r.update(year=year, sex=sex, age=int(a), lowc=cf.LOWC, highc=highc, eta_year=eta)
            rows.append(r)
    return year, rows


def main(jobs=None):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    target = ass_uncapped_target()                      # per-year ASS uncapped mean ($/worker)
    rows = []
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(fit_year, y, target.get(y)): y for y in YEARS}
        for fut in as_completed(futs):
            year, yr_rows = fut.result()
            rows.extend(yr_rows)
            nconv = sum(r["converged"] for r in yr_rows)
            eta = next((r["eta_year"] for r in yr_rows if r["sex"] == 1), 0.0)
            print(f"{year}: {len(yr_rows):>3} cells fit, {nconv:>3} converged, "
                  f"eta={eta:.3g}{' (matched)' if eta > 0 else ''}", flush=True)

    rows.sort(key=lambda r: (r["year"], r["sex"], r["age"]))
    with OUT.open("w", newline="") as fh:
        wtr = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        wtr.writeheader()
        wtr.writerows(rows)
    print(f"\nwrote {len(rows)} rows -> {OUT}")


if __name__ == "__main__":
    jobs = None
    if "--jobs" in sys.argv:
        jobs = int(sys.argv[sys.argv.index("--jobs") + 1])
    main(jobs)
