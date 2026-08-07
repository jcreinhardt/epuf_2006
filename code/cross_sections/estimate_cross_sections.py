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


def fit_year(year, target_unc=None):
    """Fit every qualifying (sex, age) cell for one year, matching the year's UNCAPPED aggregate
    mean to the ASS target. The moment couples the men cells only through the scalar aggregate
    S = sum_c w_c E[X]_c, so the joint fit decomposes (dual/rank-1): condition on ONE multiplier
    eta and each men cell solves independently  min negll_c + eta*w_c*E[X]_c  (fit_dpln mean_pen);
    an outer 1-D root-find sets eta so S = target. eta>=0 only THINS an over-heavy censored tail,
    and is 0 where the model does not overshoot (high-cap years), so well-fit years are untouched.
    Women (finite mixture mean) are unpenalized and enter as the fixed offset S_women."""
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

    # ---- women: plain censored MLE; accumulate their fixed uncapped-mean contribution ----
    women = _fit_cells(by_age[2], cf.fit_mixture, cf.mix_theta, highc)
    s_women = sum((by_age[2][a].size / ntot) *
                  cf.mix_mean(r["mu1"], r["mu2"], r["sig1"], r["sig2"], r["w"])
                  for a, r in women.items() if in_win(a))

    # ---- men: bounded base fit (eta=0), then the per-year eta that matches the aggregate ----
    w_of = {a: by_age[1][a].size / ntot for a in by_age[1]}
    base = _fit_cells(by_age[1], cf.fit_dpln, cf.dpln_theta, highc,
                      mean_pen_of=lambda a: (0.0, w_of[a]))   # eta=0 -> bounded MLE (alpha>1), finite E[X]
    ages_win = [a for a in sorted(by_age[1]) if in_win(a)]

    def s_men(fits):
        return sum(w_of[a] * cf.dpln_mean(fits[a]["alpha"], fits[a]["beta"],
                                          fits[a]["nu"], fits[a]["tau"]) for a in ages_win)

    base_theta = {a: cf.dpln_theta(base[a]) for a in ages_win}
    def refit(eta):                        # in-window men refit at eta, from the FIXED base start so
        f = dict(base)                     # refit(.) is a pure function of eta (brentq needs that);
        for a in ages_win:                 # warm-chaining the start would make refit(0) path-dependent
            f[a] = cf.fit_dpln(by_age[1][a], cf.LOWC, highc,
                               start=base_theta[a], mean_pen=(eta, w_of[a]))
        return f

    eta, men = 0.0, base
    T_men = (target_unc - s_women) if target_unc is not None else None
    if T_men is not None and ages_win and s_men(base) > T_men > 0:    # overshoot -> thin to target
        # Gaussian/Newton seed (mean-constrained-MLE skill): linearize S(eta) at eta=0, where
        # dS/deta = -(1/ntot) sum_c w_c Var_c, giving eta0 = ntot * gap / sum_c w_c Var_c from the
        # unconstrained (eta=0) fits. It lands us near the root in the mild-overshoot case; heavy
        # dPlN tails (alpha<=2) have infinite Var (no local slope) -> fall back to eta0=1 and let the
        # x4 growth climb. The grow-then-brentq envelope below is correct regardless of the seed.
        denom = sum(w_of[a] * cf.dpln_var(base[a]["alpha"], base[a]["beta"],
                                          base[a]["nu"], base[a]["tau"]) for a in ages_win)
        eta0 = ntot * (s_men(base) - T_men) / denom if np.isfinite(denom) and denom > 0 else 1.0
        hi = float(np.clip(eta0, 0.1, ETA_HI))
        s_hi = s_men(refit(hi))
        while s_hi > T_men and hi < ETA_HI:                           # seed too low -> grow bracket
            hi *= 4.0
            s_hi = s_men(refit(hi))
        if s_hi > T_men:              # target sits below the tail-free body floor -> thin maximally
            eta = hi
        else:                         # S(eta) monotone decreasing: brentq on the scalar residual
            eta = brentq(lambda e: s_men(refit(e)) - T_men, 0.0, hi,
                         xtol=1e-4, rtol=MOMENT_TOL, maxiter=60)
        men = refit(eta)

    rows = []
    for a, r in men.items():
        r.update(year=year, sex=1, age=int(a), lowc=cf.LOWC, highc=highc, eta_year=eta)
        rows.append(r)
    for a, r in women.items():
        r.update(year=year, sex=2, age=int(a), lowc=cf.LOWC, highc=highc, eta_year=0.0)
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
