#!/usr/bin/env python
"""Stage 1.5: penalized-MLE smoothing of the per-cell fits by block coordinate descent.

Bare keep-best (argmin negll over neighbour warm starts) is a SELECTION operator: it
works only where basins are deep and well-separated (the men's retirement tau notch), but
on a flat likelihood ridge (the dPlN upper tail, info_alpha ~ 0) the negll differences
between neighbour starts are sub-nat noise, so it copies whichever neighbour value is
infinitesimally favoured -- turning alpha into a blocky, LESS smooth patchwork. The value
of a weakly-identified parameter must be set by smoothness, not by argmin.

So we fit the penalized MLE per cell against the TRUE censored likelihood:

    min_theta   negll_c(theta)  +  Sum_p lam_p (theta_p - line_{c,p})^2

  * line_{c,p} -- the local-linear (planar) fit to the 5-year age-cohort neighbours, in
    the fitter's theta coordinate; the smoothness target.
  * lam_p -- ONE precision per parameter, estimated by REML from the data (below), not
    guessed. Near the optimum each parameter becomes a precision-weighted average
    theta*_c = (H_c theta_hat_c + 2 lam_p line_c)/(H_c + 2 lam_p), H_c = observed info:
    sharp params (nu, mu) follow the data (H_c >> lam), the flat ridge follows the line.

Basins are explored with DIRECTIONAL graded warm starts: a cell is refit from its own
theta AND from neighbours 1-5 years out toward the reliable prime-age core (older donors
for ages < 45, younger donors for ages > 45 -- which also imports the retirement block's
low-tau basin from the clean younger side, since stage-1 propagates the ridge upward). The
lowest penalized objective wins. Own theta is always a start, so each step is monotone in
the global objective; iterate (recomputing line and lam each pass -- an EM-style outer
loop) until no cell moves. That is the stopping rule, and it is a genuine fixed point.

REML lambda: write theta_hat_c = line_c + eps_c with sampling variance v_c = 1/info_c and
smoothness variance s^2 = 1/(2 lam). Then (theta_hat_c - line_c) ~ N(0, s^2 + v_c), so
s^2 = max(0, median_c[(theta_hat_c-line_c)^2] - median_c[v_c]) and lam = 1/(2 s^2). For
alpha (huge v_c, no real variation) s^2 -> 0, lam -> large, alpha snaps to the line; for nu
(tiny v_c, real age-cohort structure) s^2 > 0, small lam, nu follows the data. (Medians for
robustness to the unrepaired spikes.) This folds stage-2 smoothing into the estimation.

  python code/cross_sections/iterate_fit_smooth.py [--outer T] [--window W] [--jobs N]
    -> output/cross_sections/cross_section_params_iterated.csv
"""
import os
# pin BLAS to one thread BEFORE numpy/scipy import -> no oversubscription across workers
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import sys
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

import crosssec_fit as cf
import smooth_params as sp
import estimate_cross_sections as ec

IN         = Path("output/cross_sections/cross_section_params.csv")
OUT        = Path("output/cross_sections/cross_section_params_iterated.csv")
MAX_OUTER  = 6        # EM-style passes; breaks early once no cell moves
WINDOW     = 5        # neighbour line + warm-start reach: +/- this many years (age & cohort)
MIDPOINT   = 45       # warm-start toward the core: older donors below it, younger above
INFO_FLOOR = 1e-9     # guard 1/info for the flat ridge
LAM_MAX    = 1e5      # lam when REML s^2 collapses to 0 (parameter fully set by the line)
MOVE_TOL   = 1e-3     # a cell "moved" if any theta changes by more than this

# per-sex parameter list in the fitter's theta order: (column, info column, transform).
# Must match dpln_theta / mix_theta packing so line, lam and warm starts share coordinates.
SPEC = {1: [("alpha", "info_alpha", "log"), ("beta", "info_beta", "log"),
            ("nu", "info_nu", "id"),        ("tau", "info_tau", "log")],
        2: [("mu1", "info_mu1", "id"),      ("mu2", "info_mu2", "id"),
            ("sig1", "info_sig1", "logsig"),("sig2", "info_sig2", "logsig"),
            ("w", "info_w", "logit")]}


def line_predict(ages, cohorts, theta, window=WINDOW):
    """Local-linear (planar) fit to each cell's neighbours within +/-window years in age
    AND cohort (Chebyshev ball), evaluated at the cell -- the smoothness target / (b)
    surface. Trend-preserving: any planar gradient passes through untouched."""
    pts = np.column_stack([ages, cohorts]).astype(float)
    tree = cKDTree(pts)
    pred = theta.copy()
    for c in range(len(pts)):
        nb = [j for j in tree.query_ball_point(pts[c], window, p=np.inf) if j != c]
        if len(nb) < 3:
            if nb:
                pred[c] = float(np.mean(theta[nb]))
            continue
        X = np.column_stack([np.ones(len(nb)), pts[nb, 0], pts[nb, 1]])
        if np.linalg.matrix_rank(X) < 3:
            pred[c] = float(np.mean(theta[nb]))
            continue
        coef, *_ = np.linalg.lstsq(X, theta[nb], rcond=None)
        pred[c] = float(coef @ np.array([1.0, pts[c, 0], pts[c, 1]]))
    return pred


def reml_s2(r, v):
    """Precision-weighted REML for the smoothness variance s^2 in theta_hat_c = line_c +
    N(0,s^2), theta_hat_c ~ N(theta_c, v_c): solve Sum r_c^2/(s^2+v_c)^2 = Sum 1/(s^2+v_c).
    Sharp cells (small v, large residual) dominate, so a real minority feature -- the tau
    retirement cliff -- keeps s^2 up (moderate lambda) instead of being smoothed away, while
    a parameter whose scatter is pure sampling noise gives f(0)<=0 -> s^2=0 -> full
    smoothing (the flat-ridge alpha)."""
    def f(s2):
        d = s2 + v
        return float(np.sum(r * r / d ** 2) - np.sum(1.0 / d))
    if f(0.0) <= 0.0:
        return 0.0
    lo, hi = 0.0, max(float(np.var(r)), 1e-9)
    while f(hi) > 0.0:
        hi *= 2.0
    for _ in range(60):                         # bisection on the monotone score
        mid = 0.5 * (lo + hi)
        (lo, hi) = (mid, hi) if f(mid) > 0.0 else (lo, mid)
    return 0.5 * (lo + hi)


def lines_and_lambdas(df, window=WINDOW):
    """Per sex: the neighbour-line target (theta space, keyed by (sex, cohort, age)) and the
    REML per-parameter lambda vector."""
    line = {}                                   # (sex, cohort, age) -> target theta vector
    lam = {}                                    # sex -> lambda vector (one per parameter)
    for sex, specs in SPEC.items():
        sub = df[df["sex"] == sex]
        ages = sub["age"].to_numpy(dtype=float)
        cohs = (sub["year"] - sub["age"]).to_numpy(dtype=float)
        keys = list(zip(sub["sex"].astype(int), (sub["year"] - sub["age"]).astype(int),
                        sub["age"].astype(int)))
        cols, lam_vec = [], []
        for name, infocol, kind in specs:
            th = sp.to_theta(sub[name].to_numpy(dtype=float), kind)
            ln = line_predict(ages, cohs, th, window)
            v = 1.0 / np.maximum(sub[infocol].to_numpy(dtype=float), INFO_FLOOR)
            s2 = reml_s2(th - ln, v)                                  # precision-weighted REML
            lam_vec.append(min(0.5 / s2, LAM_MAX) if s2 > 0 else LAM_MAX)
            cols.append(ln)
        lam[sex] = np.array(lam_vec)
        M = np.column_stack(cols)                                     # cell x parameter
        for i, k in enumerate(keys):
            line[k] = M[i]
    return line, lam


def _refit_year(args):
    """Penalized refit of one year's cells; keep the lowest penalized objective across the
    own + directional-neighbour warm starts."""
    year, cells, lam = args      # cells: (sex, age, own_row, target_theta, [donor thetas])
    df = ec.load_year(year)
    highc = float(df["earnings"].max()) - cf.HIGH_MARGIN
    by_age = {sex: {a: sub["earnings"].to_numpy(dtype=float)
                    for a, sub in df.loc[df["sex"] == sex].groupby("age")}
              for sex in ec.SEX}
    rows, n_moved = [], 0
    for sex, age, crow, target, donors in cells:
        _label, fit, pack = ec.SEX[sex]
        x = by_age[sex].get(age)
        if x is None or x.size < ec.MIN_N:
            rows.append(crow)
            continue
        pen = (target, lam[sex])
        own = pack(crow)
        cands = [fit(x, cf.LOWC, highc, start=s, penalty=pen) for s in [own] + donors]
        conv = [c for c in cands if c["converged"]] or cands
        best = min(conv, key=lambda c: c["obj"])
        if np.max(np.abs(np.asarray(pack(best)) - np.asarray(own))) > MOVE_TOL:
            n_moved += 1
        best.update(year=year, sex=sex, age=int(age), lowc=cf.LOWC, highc=highc)
        rows.append(best)
    return year, rows, n_moved


def main(outer=MAX_OUTER, window=WINDOW, jobs=None):
    df = pd.read_csv(IN)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # lambda is estimated ONCE from the raw fits and held fixed: re-estimating it from the
    # progressively-smoothed params is a runaway (smoother params -> smaller residual ->
    # REML infers less variation -> larger lambda -> smoother still -> collapse to the line).
    # With lambda fixed, only the line updates each pass -- block coordinate descent on the
    # fixed objective Sum negll_c + lambda||P theta||^2, which converges.
    _, lam = lines_and_lambdas(df, window)
    for t in range(1, outer + 1):
        line, _ = lines_and_lambdas(df, window)
        # pack current thetas once, keyed by (sex, cohort, age), for own + donor warm starts
        theta = {}
        for sex in SPEC:
            sub = df[df["sex"] == sex]
            for r in sub.to_dict("records"):
                theta[(sex, int(r["year"] - r["age"]), int(r["age"]))] = \
                    (ec.SEX[sex][2](r), r)          # (packed theta, row)
        payload = defaultdict(list)
        for (sex, c, a), (th, row) in theta.items():
            d = 1 if a < MIDPOINT else -1           # older donors young end, younger old end
            donors = [theta[(sex, c, a + d * k)][0] for k in range(1, window + 1)
                      if (sex, c, a + d * k) in theta]
            payload[int(c + a)].append((sex, a, row, line[(sex, c, a)], donors))
        rows, moved = [], 0
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            futs = {ex.submit(_refit_year, (y, cells, lam)): y for y, cells in payload.items()}
            for fut in as_completed(futs):
                _y, yr_rows, n_moved = fut.result()
                rows.extend(yr_rows)
                moved += n_moved
        df = pd.DataFrame(rows).sort_values(["year", "sex", "age"]).reset_index(drop=True)
        lam_str = "  ".join(f"{s}:[" + ",".join(f"{v:.0f}" for v in lam[s]) + "]" for s in lam)
        print(f"outer {t}/{outer}: {moved} cells moved   lambda {lam_str}", flush=True)
        if moved == 0:
            break

    df[ec.COLS].to_csv(OUT, index=False)
    print(f"\nwrote {len(df)} penalized rows -> {OUT}  (window={window})")


if __name__ == "__main__":
    kw = {}
    for flag, key, cast in [("--outer", "outer", int), ("--window", "window", int),
                            ("--jobs", "jobs", int)]:
        if flag in sys.argv:
            kw[key] = cast(sys.argv[sys.argv.index(flag) + 1])
    main(**kw)
