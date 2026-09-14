#!/usr/bin/env python
"""Choose SMOOTH_FRAC by HELD-OUT LIKELIHOOD, splitting people in two.

WHY THE OLD CRITERION CANNOT BE REUSED. SMOOTH_FRAC = 1e-4 came from a 5-point sweep judged
on the in-sample uncapped aggregate ratio. Under the aggregate constraint that ratio is pinned
by construction in every year eta binds -- 52 of 56 in the 2026-09-09 run, leaving only 1984,
1994, 1999 and 2002 free -- so it barely sees rho at all: the regenerated surface came back at
0.9997 [0.994-1.003]. The sweep was also run under the Huber loss, and rho0 for the same
fraction has since moved 7.12e-08 -> 1.35e-08, so the number does not mean what it did.

THE CRITERION. People are split by hash(id) % 2. The production estimator -- same lam, same
constraint, same penalty -- is run on one half; the pure censored negll of the OTHER half's
person-years is then evaluated under the fitted surface; then the halves swap. Too little
smoothing fits the training half's noise, too much smears genuine age structure, and both cost
likelihood on data the fit never saw. The comparison is PAIRED -- every grid point is scored on
the same held-out observations -- so differences are far more precise than the totals' size
suggests. Measured on the first grid points, smoothing does generalise: moving 0 -> 1e-5 cost
the TRAINING likelihood +571.7 nats but the held-out one only +210.3.

WHY IT IS DECIDED ON 1957-2006 (DECIDE_FROM). The all-years total is dominated by 1951-56:
six years, 6% of the held-out observations, in which men's upper tail alpha is unidentified
under a cap 70-75% of prime-age men exceed. Stage-0 basins there sit 0.2 nats apart (5-10 nats
later) while disagreeing on log alpha by up to 6; the roughness penalty spends ~half its budget
pulling those arbitrary alphas together, and through the dPlN's coupling that moves S(cap),
which the censored likelihood weighs heavily. On fold 0's first grid points the held-out cost
there looked flat in strength (+513 at 1e-5, +557 at 3e-5); over the full grid, fold-summed, it
is not monotone at all (+485 at 1e-4, -91 at 3e-4, +827 at 1e-3, +1,706 at 3e-3) -- noise, which
is the point: those years do not price smoothing. 1951-56 also carry no GKSW targets and eta ~ 8.
So the choice is made on the rest, with the all-years total reported beside it. The fix for
1951-56 is CLAUDE.md open item 3 -- men's tail slot as a functional rather than raw log alpha --
not a different criterion.

WHAT THE FULL GRID SHOWED -- and why the window, not the rule, is the judgement that matters.
Applied mechanically, decide() picks 3e-3 on 1957-2006 with nothing else inside the noise band.
That win is carried by 1957-79: fold-summed gain against no smoothing is -3,856 nats there at
3e-3, against -732 in 1980-2006. Applied to 1980-2006 alone -- least censoring, smallest eta,
the years this criterion is most trustworthy in -- the same rule picks 3e-4 (band 3e-4 and 1e-3),
and 3e-3 is RESOLVED worse there (+1,352 +/- 33). 1957-79 still sits under a binding cap with
eta ~ 3, so part of what disqualified 1951-56 plausibly reaches into it. The aggregate constraint
points the same way: at 3e-3, 4-5 years per half-sample fall more than 1% below ASS (worst
0.971), against 0-2 at 3e-4. DECIDE_FROM was fixed before the full grid was seen; moving it after
would be choosing the criterion by its answer. So this module reports both, and the value of
SMOOTH_FRAC is chosen -- and its reasoning recorded -- in estimate_cross_sections.py.

WHAT IT CANNOT SEE, and what is reported beside it. The likelihood is censored at the cap, so
the tail above it reaches the criterion only through S(cap). Each grid point therefore also
records: the in-sample uncapped ratio and the years left at eta = 0 (the Jensen ceiling);
Sum n Q against the published targets (IN sample -- those statistics are not split); and the
median roughness of men's log alpha along age.

MIN_N is halved for the training halves so the cell grid stays close to production's: the two
halves carry 6,433 and 6,425 cells against production's 6,431, within 8. A half-sample at 1000
would drop exactly the thin edge ages -- the 16-19 entry break -- where smoothing is most
contested. The halves' grids differ slightly from EACH OTHER, which does not disturb the
criterion: pairing needs every grid point within a fold scored on the same cells, and it is;
summing the two folds' paired curves is then legitimate even over slightly different cell sets.

TRANSFER FROM n/2 TO n. rho0 is linear in the fraction, and the half-sample gives 1.57e-08 per
1e-4 against the full sample's 1.35e-08 -- within 16%, so a chosen fraction means nearly the
same rho at full size.

OUTPUTS. The summary row per (fold, frac) goes to smooth_frac_calibration.csv; the per-YEAR
held-out detail, which the decision needs, to smooth_frac_calibration_by_year.csv (both
tracked); the per-CELL detail and the fitted surfaces to the ignored cache under
processed_data/. File names carry a configuration tag whenever lam or the constraint differ
from the estimator's defaults, so a --no-constrain sweep cannot collide with this one. Stage 0
is independent of SMOOTH_FRAC and of the constraint, so it is cached once per (fold, lam) and
shared. Rows are appended as they finish and a finished (fold, frac) is skipped on re-run, so an
interrupted sweep resumes. --backfill scores cached surfaces that lack per-year detail and
refuses to write any that do not reproduce the summary totals exactly.

    python code/cross_sections/calibrate_smooth_frac.py [--grid 0 1e-5 ...] [--folds 0 1] [--jobs N]
    python code/cross_sections/calibrate_smooth_frac.py --backfill [--jobs N]
      -> output/cross_sections/smooth_frac_calibration{,_by_year}.csv
"""
import argparse
import csv
import pickle
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "code/cross_sections")    # run from the project root, per repo convention
import estimate_cross_sections as X          # noqa: E402  -- the solver: ONE implementation
import obj_gmm                               # noqa: E402
import obj_mle                               # noqa: E402
import xs_model as xm                        # noqa: E402
from benchmarks import ass_uncapped_per_worker   # noqa: E402

OUT = Path("output/cross_sections/smooth_frac_calibration.csv")
BY_YEAR = Path("output/cross_sections/smooth_frac_calibration_by_year.csv")
CACHE = Path("processed_data/smooth_frac_cache")
GRID = [0.0, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2]
DECIDE_FROM = 1957                          # the PRE-REGISTERED window; see the docstring
INFORMATIVE_FROM = 1980                     # the least-censored window, on which SMOOTH_FRAC was adopted
FIELDS = ["fold", "smooth_frac", "rho0", "heldout_negll", "heldout_nobs", "heldout_bad_cells",
          "unc_ratio_mean", "unc_ratio_min", "unc_ratio_max", "eta0_years", "gmm_nq",
          "alpha_rough_men", "solve_sec", "lam", "min_n", "duckdb"]
YEAR_FIELDS = ["fold", "smooth_frac", "year", "heldout_negll", "n_test", "cells", "bad_cells"]


def duckdb_version():
    return subprocess.run(["duckdb", "--version"], capture_output=True, text=True).stdout.split()[0]


def config_tag(lam, constrain):
    """'' at the estimator's defaults; otherwise a suffix that keeps runs from sharing files."""
    return ("" if np.isclose(lam, X.LAM) else f"_lam{lam:g}") + ("" if constrain else "_unconstrained")


def stage0(fold, lam, gmm_iters, min_n, jobs):
    """Stage 0 on the training half, cached: independent of SMOOTH_FRAC and of the constraint."""
    path = CACHE / f"stage0_fold{fold}_lam{lam}_it{gmm_iters}_n{min_n}.pkl"
    if path.exists():
        with path.open("rb") as fh:
            return pickle.load(fh)
    tgt = obj_gmm.guv_targets(X.YEARS) if lam > 0.0 else {}
    by_year = {y: {(s, a): v for (yy, s, a), v in tgt.items() if yy == y} for y in X.YEARS}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        metas = list(ex.map(X.stage0_year,
                            [(y, lam, gmm_iters, by_year[y], fold, min_n) for y in X.YEARS]))
    print(f"  stage 0, fold {fold}: {len(metas)} years, {time.time() - t0:.0f}s", flush=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        pickle.dump((metas, by_year), fh)
    return metas, by_year


def rho_grid_for(rho0):
    """The production continuation grid -- except at rho0 = 0, the unsmoothed reference, where
    a geometric sequence is undefined and there is nothing to continue from."""
    if rho0 <= 0.0:
        return [0.0]
    return list(np.geomspace(rho0 * X.RHO0_START, rho0, X.RHO_STEPS))


def heldout_year(args):
    """Pure censored negll of the held-out half, PER CELL, at the training year's cap."""
    year, test_fold, highc, surface = args
    by_age = X.cells_by_age(X.load_year(year, test_fold), min_n=1)
    out = []
    for (sex, a), theta in surface.items():
        x = by_age[sex].get(a)
        if x is None:
            continue
        negll, _ = obj_mle.censored_negll(sex, x, xm.LOWC, highc)
        v = negll(theta)
        bad = (not np.isfinite(v)) or v >= 1e17          # obj_mle's sentinel for a non-finite fit
        out.append(dict(year=year, sex=sex, age=a, n_test=x.size,
                        heldout_negll=np.nan if bad else v, bad=int(bad)))
    return out


def score(fold, surfaces, jobs):
    """surfaces: {year: (highc, {(sex, age): theta})} -> per-cell DataFrame on the other half."""
    ev = [(y, 1 - fold, h, s) for y, (h, s) in sorted(surfaces.items())]
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        return pd.DataFrame([r for rows in ex.map(heldout_year, ev) for r in rows])


def write_detail(cells, fold, frac):
    """Per-year detail to the tracked CSV, per-cell detail to the cache. Returns the totals."""
    ok = cells[cells.bad == 0]
    # observations are counted only in cells that were actually scored, so n_test and the negll
    # sum describe the same set -- the pairing check compares exactly these counts
    n_ok = cells.n_test.where(cells.bad == 0, 0)
    yr = (cells.assign(n_ok=n_ok).groupby("year")
          .agg(heldout_negll=("heldout_negll", "sum"), n_test=("n_ok", "sum"),
               cells=("age", "size"), bad_cells=("bad", "sum"))
          .reset_index())
    yr.insert(0, "smooth_frac", frac)
    yr.insert(0, "fold", fold)
    yr[YEAR_FIELDS].to_csv(BY_YEAR, mode="a", header=not BY_YEAR.exists(), index=False)
    c = cells.assign(fold=fold, smooth_frac=frac)
    c.to_csv(CELLS, mode="a", header=not CELLS.exists(), index=False)
    return float(ok.heldout_negll.sum()), int(ok.n_test.sum()), int(cells.bad.sum())


def alpha_roughness(rows):
    """Median over years of mean |D2 log alpha| along age, men, exempt steps skipped."""
    out = []
    for y in sorted({r["year"] for r in rows}):
        la = {r["age"]: np.log(r["alpha"]) for r in rows if r["year"] == y and r["sex"] == 1}
        ages = sorted(la)
        d = [abs(la[ages[i + 1]] - 2 * la[ages[i]] + la[ages[i - 1]])
             for i in range(1, len(ages) - 1) if not X.free_d2(ages[i])]
        if d:
            out.append(np.mean(d))
    return float(np.median(out)) if out else np.nan


def keys(path):
    if not path.exists():
        return set()
    with path.open() as fh:
        return {(int(r["fold"]), float(r["smooth_frac"])) for r in csv.DictReader(fh)}


def append(row):
    new = not OUT.exists()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def surface_path(fold, frac):
    return CACHE / f"surface_fold{fold}_frac{frac:g}{TAG}.csv"


def run_point(fold, frac, metas, by_year, lam, constrain, min_n, jobs, target, ver):
    t0 = time.time()
    Omega, rho0 = X.freeze_omega_rho(metas, frac)
    grid = rho_grid_for(rho0)
    args = [(m, Omega, grid, target.get(m["year"]) if constrain else None, lam, by_year[m["year"]])
            for m in metas]
    rows, etas = [], {}
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        for year, yr_rows, tm in ex.map(X.solve_year, args):
            rows.extend(yr_rows)
            etas[year] = tm["eta"]
    solve_sec = time.time() - t0
    X.write_csv(surface_path(fold, frac), rows)

    # in-sample aggregate: EXACTLY the solver's s_full, per year, against the same target
    theta = {(r["year"], r["sex"], r["age"]): X.PACK[r["sex"]](r) for r in rows}
    ratios = []
    for m in metas:
        tgt = target.get(m["year"])
        if not tgt:
            continue
        s = sum(m["w_of"][sex][a] * X.cell_mean(sex, theta[(m["year"], sex, a)])
                for sex in X.SEXES for a in m["ages_win"][sex])
        ratios.append(s / tgt)
    ratios = np.array(ratios)

    cells = score(fold, {m["year"]: (m["highc"], {(r["sex"], r["age"]): theta[(r["year"], r["sex"], r["age"])]
                                                  for r in rows if r["year"] == m["year"]})
                         for m in metas}, jobs)
    tot, nobs, bad = write_detail(cells, fold, frac)
    row = dict(fold=fold, smooth_frac=frac, rho0=rho0, heldout_negll=tot, heldout_nobs=nobs,
               heldout_bad_cells=bad,
               unc_ratio_mean=float(ratios.mean()) if ratios.size else np.nan,
               unc_ratio_min=float(ratios.min()) if ratios.size else np.nan,
               unc_ratio_max=float(ratios.max()) if ratios.size else np.nan,
               eta0_years=int(sum(1 for e in etas.values() if e == 0.0)),
               gmm_nq=float(sum(r["n"] * r["gmm_q"] for r in rows
                                if r["has_guv"] and np.isfinite(r["gmm_q"]))),
               alpha_rough_men=alpha_roughness(rows), solve_sec=round(solve_sec),
               lam=lam, min_n=min_n, duckdb=ver)
    append(row)
    print(f"  fold {fold}  frac {frac:<7g} rho0 {rho0:.3g}  held-out negll/obs {tot / nobs:.6f}  "
          f"eta0 {row['eta0_years']}  unc [{row['unc_ratio_min']:.3f}-{row['unc_ratio_max']:.3f}]  "
          f"alpha rough {row['alpha_rough_men']:.3f}  {solve_sec:.0f}s", flush=True)


def backfill(jobs):
    """Score cached surfaces that have a summary row but no per-year detail. Writes nothing for a
    surface whose per-cell scores do not reproduce the summary totals exactly."""
    summ = pd.read_csv(OUT).set_index(["fold", "smooth_frac"])
    todo = sorted(keys(OUT) - keys(BY_YEAR))
    if not todo:
        print("backfill: every summary row already has per-year detail")
        return
    for fold, frac in todo:
        p = surface_path(fold, frac)
        if not p.exists():
            print(f"  fold {fold} frac {frac:g}: no cached surface at {p} -- cannot backfill")
            continue
        s = pd.read_csv(p)
        surfaces = {int(y): (float(g.highc.iloc[0]),
                             {(int(r["sex"]), int(r["age"])): X.PACK[int(r["sex"])](r) for r in g.to_dict("records")})
                    for y, g in s.groupby("year")}
        cells = score(fold, surfaces, jobs)
        ok = cells[cells.bad == 0]
        want = summ.loc[(fold, frac)]
        match = (np.isclose(ok.heldout_negll.sum(), want.heldout_negll, rtol=0, atol=1e-3)
                 and int(ok.n_test.sum()) == int(want.heldout_nobs) and int(cells.bad.sum()) == int(want.heldout_bad_cells))
        if not match:
            print(f"  fold {fold} frac {frac:g}: MISMATCH ({ok.heldout_negll.sum():.3f} vs {want.heldout_negll:.3f}) -- NOT written")
            continue
        write_detail(cells, fold, frac)
        print(f"  fold {fold} frac {frac:g}: {len(cells)} cells, reproduces the summary -> detail written", flush=True)


def decide(by_year, decide_from=DECIDE_FROM):
    """The pre-registered choice, applied mechanically so the result can be re-derived.

    Fold-summed held-out negll over years >= decide_from; the raw best is its argmin. A candidate is
    WITHIN NOISE of the best when its summed gap is no larger than the two folds' disagreement about
    that same gap, |gap_fold0 - gap_fold1| -- with two folds that disagreement is the only replicate
    spread there is. The CHOICE is the smallest fraction within noise: the one-standard-error analogue,
    taking less bias whenever the data cannot separate two smoothing strengths. An optimum on the
    grid's upper edge is flagged, not chosen -- it has not been located yet.

    Both rules were written down before the full grid was seen (see the module docstring)."""
    late = by_year[by_year.year >= decide_from]
    w = late.groupby(["smooth_frac", "fold"]).heldout_negll.sum().unstack("fold").dropna()
    if w.shape[1] != 2:
        raise ValueError("decide() needs exactly two folds: the noise band IS their disagreement")
    f0, f1 = w.columns
    tot = w[f0] + w[f1]
    best = float(tot.idxmin())
    rows = []
    for c in w.index:
        g0, g1 = w.loc[c, f0] - w.loc[best, f0], w.loc[c, f1] - w.loc[best, f1]
        rows.append(dict(smooth_frac=float(c), gap=g0 + g1, disagreement=abs(g0 - g1),
                         within=bool(np.isclose(c, best) or g0 + g1 <= abs(g0 - g1))))
    t = pd.DataFrame(rows).set_index("smooth_frac")
    band = [float(c) for c in t.index[t.within]]
    return dict(best=best, chosen=min(band), band=band,
                edge=bool(np.isclose(best, float(w.index.max()))), table=t)


def summarize():
    d = pd.read_csv(OUT)
    d["above"] = d.groupby("fold")["heldout_negll"].transform(lambda v: v - v.min())
    wide = d.pivot_table(index="smooth_frac", columns="fold", values="above")
    wide["total"] = wide.sum(axis=1, min_count=wide.shape[1])
    print("\nheld-out negll ABOVE each fold's best, ALL years (summed, lower is better):")
    print(wide.round(1).to_string())
    if not BY_YEAR.exists():
        return
    b = pd.read_csv(BY_YEAR)
    for lab, sub in ((f"{DECIDE_FROM}+ (pre-registered)", b[b.year >= DECIDE_FROM]),
                     (f"{INFORMATIVE_FROM}+ (least censoring)", b[b.year >= INFORMATIVE_FROM]),
                     ("all years", b)):
        w = sub.groupby(["smooth_frac", "fold"]).heldout_negll.sum().unstack("fold").dropna()
        if w.empty:
            continue
        tot = w.sum(axis=1)
        print(f"\n{lab}: fold-summed held-out negll above best -> best SMOOTH_FRAC {tot.idxmin():g}")
        print((tot - tot.min()).round(1).to_string())
    if b.fold.nunique() == 2:
        for start, lab in ((DECIDE_FROM, "pre-registered"), (INFORMATIVE_FROM, "least censoring")):
            dd = decide(b, start)
            print(f"\nRULE on {start}+ ({lab}): raw best {dd['best']:g}   within noise "
                  f"{[f'{c:g}' for c in dd['band']]}   -> rule pick {dd['chosen']:g}"
                  + ("   ** OPTIMUM ON THE GRID EDGE: extend before choosing **" if dd["edge"] else ""))
            print(dd["table"].round(1).to_string())
        print(f"\nADOPTED: SMOOTH_FRAC = {X.SMOOTH_FRAC:g} (estimate_cross_sections.py records why)")


def main():
    global OUT, BY_YEAR, CACHE, CELLS, TAG
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--grid", type=float, nargs="+", default=GRID)
    ap.add_argument("--folds", type=int, nargs="+", default=[0, 1], choices=[0, 1])
    ap.add_argument("--lam", type=float, default=X.LAM)
    ap.add_argument("--gmm-iters", type=int, default=X.GMM_ITERS)
    ap.add_argument("--min-n", type=int, default=X.MIN_N // 2,
                    help="cell floor on the training HALF; production's floor halved keeps each half's "
                         "grid within 8 cells of production's (6,433 and 6,425 vs 6,431)")
    ap.add_argument("--no-constrain", action="store_true")
    ap.add_argument("--jobs", type=int, default=None)
    ap.add_argument("--backfill", action="store_true",
                    help="score cached surfaces lacking per-year detail, then summarize; no solving")
    ap.add_argument("--years", type=int, nargs=2, default=None, metavar=("Y0", "Y1"),
                    help="restrict to a year range -- for a smoke test only: rho0 is frozen "
                         "GLOBALLY, so a subset calibrates a different penalty")
    a = ap.parse_args()
    TAG = config_tag(a.lam, not a.no_constrain)
    if a.years:
        # A subset run must not touch the real sweep's files (the stage-0 cache key does not
        # encode the year range), so suffix everything, cache included.
        X.YEARS = range(a.years[0], a.years[1] + 1)
        TAG += f"_years{a.years[0]}-{a.years[1]}"
        CACHE = CACHE.with_name(CACHE.name + f"_years{a.years[0]}-{a.years[1]}")
    OUT = OUT.with_name(OUT.stem + TAG + OUT.suffix)
    BY_YEAR = BY_YEAR.with_name(BY_YEAR.stem.replace("_by_year", "") + TAG + "_by_year" + BY_YEAR.suffix)
    CELLS = CACHE / f"heldout_cells{TAG}.csv"
    if a.backfill:
        backfill(a.jobs)
        summarize()
        return
    target = {} if a.no_constrain else ass_uncapped_per_worker()
    ver, done = duckdb_version(), keys(OUT)
    for fold in a.folds:
        metas, by_year = stage0(fold, a.lam, a.gmm_iters, a.min_n, a.jobs)
        for frac in a.grid:
            if (fold, float(frac)) in done:
                print(f"  fold {fold}  frac {frac:g}: already in {OUT}, skipped", flush=True)
                continue
            run_point(fold, frac, metas, by_year, a.lam, not a.no_constrain, a.min_n,
                      a.jobs, target, ver)
    summarize()


TAG, CELLS = "", CACHE / "heldout_cells.csv"

if __name__ == "__main__":
    main()
