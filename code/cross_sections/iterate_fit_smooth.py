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

FINAL PASS -- aggregate-mean moment match (moment_match, on by default; --no-moment skips).
Both the raw MLE and the smoothed likelihood are BLIND to the earnings mass above the taxable
cap: under a tight maximum ~40-45% of older men are top-coded and the censored likelihood fits
a heavy dPlN upper tail (alpha<=1, an INFINITE uncapped mean) to explain the pile-up. So after
smoothing converges we pin the ONE quantity the cap censors -- the mean -- to the published ASS
uncapped average earnings per worker (aggearn_tot / num_wrk). Per year we solve a single
multiplier eta so the composition-weighted model E[X] over men+women 15-77 hits that mean,
refitting each men cell FULL-vector via the penalized objective  negll(theta) + Sum_p lam_p
(theta_p - line_p)^2 + eta*w*E[X](theta)  (fit_dpln_mean in crosssec_fit). All of alpha, beta,
nu, tau move together, so the body re-optimizes to compensate as the tail thins -- the mean
match costs little likelihood, where freezing the body and pushing alpha alone is far more
expensive (measured ~15x the negll cost). Women's mixture mean is finite and enters as a fixed
offset; men's tails absorb the aggregate, and because the pull is a shared eta against each
cell's own likelihood curvature, the correction is INFORMATION-ROUTED -- well-identified cells
barely move, censored flat-ridge cells take it. eta>=0 only THINS an over-heavy tail (never
fattens), and eta=0 where the model already doesn't overshoot (the high-cap years), so it
self-limits to the tight-cap era. This makes stage 1.5 depend on the ASS workbook. Output gains
alpha_premoment (pre-match alpha) and eta_mean (the year's multiplier).

  python code/cross_sections/iterate_fit_smooth.py [--outer T] [--window W] [--jobs N] [--no-moment]
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
ASS_XLSX   = Path("raw_data/annual_statistical_supplement.xlsx")   # uncapped-mean benchmark
MATCH_AGES = (15, 77)  # cells entering the aggregate-mean moment (matches the validation window)
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


def ass_uncapped_target():
    """ASS average UNCAPPED earnings per covered worker ($/worker) per year: (aggearn_tot_wage
    + aggearn_tot_se) / num_wrk, annual 1937-2022. This is the published mean the censored MLE
    can't see (the mass above the cap), and the target the moment match pins the model to. Same
    definition as ass_unc in plot_aggregate_taxable_extrapolated, so the fit hits what's judged."""
    d = pd.read_excel(ASS_XLSX, sheet_name="data")
    tot = d["aggearn_tot_wage"].fillna(0) + d["aggearn_tot_se"].fillna(0)   # $M
    out = {}
    for y, t, nw in zip(d["year"], tot, d["num_wrk"]):
        if t > 0 and pd.notna(nw) and nw > 0:
            out[int(y)] = float(t) * 1e6 / (float(nw) * 1e3)               # $ per worker
    return out


def _match_year(args):
    """Solve one year's aggregate-mean moment: find the single eta so the composition-weighted
    model uncapped mean E[X] over men+women 15-77 equals the ASS target, refitting each men cell
    FULL-vector (alpha, beta, nu, tau together) under the penalized objective, so the body
    compensates as the tail thins. Women's mixture mean is finite -> the fixed offset S_women.
    Returns {age: (alpha, beta, nu, tau)}, the year's eta, and the negll change summed over men
    (>=0, the fit cost of the match). eta=0 (no change) when the model does not overshoot -- the
    correction only ever THINS an over-heavy censored tail, never fattens."""
    year, men_cells, S_women, target_unc, lam = args
    dfy = ec.load_year(year)
    highc = float(dfy["earnings"].max()) - cf.HIGH_MARGIN
    xby = {a: sub["earnings"].to_numpy(dtype=float)
           for a, sub in dfy.loc[dfy["sex"] == 1].groupby("age")}
    cells = []                          # (age, x, start_theta, line_theta, w, negll0)
    for age, theta, line, w in men_cells:
        x = xby.get(age)
        if x is None or x.size < ec.MIN_N:
            continue
        th = np.asarray(theta, float)
        negll0 = cf.dpln_negll(x, cf.LOWC, highc, np.exp(th[0]), np.exp(th[1]), th[2], np.exp(th[3]))
        cells.append((age, x, th, np.asarray(line, float), w, negll0))
    if not cells:
        return year, {}, 0.0, 0.0

    def solve(eta):                     # refit every men cell at this eta; weighted mean + fits
        fits = {}
        M = 0.0
        for age, x, theta, line, w, _n0 in cells:
            a, b, nu, tau, nll = cf.fit_dpln_mean(x, cf.LOWC, highc, theta, line, lam, eta, w)
            fits[age] = (a, b, nu, tau, nll)
            M += w * cf.dpln_mean(a, b, nu, tau)
        return fits, M

    T_men = target_unc - S_women        # men's share of the target weighted-mean
    f0, M0 = solve(0.0)
    if T_men <= 0 or not np.isfinite(M0) or M0 <= T_men:
        return year, {a: f[:4] for a, f in f0.items()}, 0.0, \
               sum(f0[c[0]][4] - c[5] for c in cells)
    lo, hi = 0.0, 1e-3
    for _ in range(60):                 # grow the bracket until the mean undershoots the target
        if solve(hi)[1] < T_men or hi > 1e8:
            break
        hi *= 10.0
    for _ in range(40):                 # bisection on the monotone (decreasing) mean(eta)
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if solve(mid)[1] > T_men else (lo, mid)
    eta = 0.5 * (lo + hi)
    fits, _ = solve(eta)
    dnll = sum(fits[c[0]][4] - c[5] for c in cells)   # negll increase vs the smooth fit
    return year, {a: f[:4] for a, f in fits.items()}, eta, dnll


def moment_match(df, jobs=None):
    """Final stage-1.5 pass: bend each year's men cells so the composition-weighted model
    uncapped mean matches the ASS published mean, via the FULL-vector penalized fit in
    fit_dpln_mean (likelihood + smoothness + the shared per-year moment). All of alpha, beta,
    nu, tau move so the body compensates as the tail thins; women are held at their finite fit;
    the correction is information-routed to the censored cells. Adds alpha_premoment (the
    pre-match alpha) and eta_mean (the year's multiplier) for diagnostics, and reports the total
    negll cost so any fit loss is visible."""
    line, lam = lines_and_lambdas(df)
    lam_men = lam[1]                                 # per-param precision, dPlN theta order
    target = ass_uncapped_target()
    lo_age, hi_age = MATCH_AGES

    tasks = []
    for y, g in df.groupby("year"):
        y = int(y)
        if y not in target:
            continue
        gg = g[(g["age"] >= lo_age) & (g["age"] <= hi_age)]
        ntot = float(gg["n"].sum())
        if ntot <= 0:
            continue
        wom = gg[gg["sex"] == 2]
        s_women = float(sum((r["n"] / ntot) *
                            cf.mix_mean(r["mu1"], r["mu2"], r["sig1"], r["sig2"], r["w"])
                            for r in wom.to_dict("records")))
        men_cells = [(int(r["age"]), cf.dpln_theta(r),
                      list(line[(1, int(r["year"] - r["age"]), int(r["age"]))]),
                      float(r["n"] / ntot))
                     for r in gg[gg["sex"] == 1].to_dict("records")]
        tasks.append((y, men_cells, s_women, float(target[y]), lam_men))

    results = {}
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(_match_year, t): t[0] for t in tasks}
        for fut in as_completed(futs):
            y, fits, eta, dnll = fut.result()
            results[y] = (fits, eta, dnll)

    df = df.copy()
    df["alpha_premoment"] = df["alpha"]
    df["eta_mean"] = 0.0
    idx = {(int(r.year), int(r.sex), int(r.age)): i for i, r in df.iterrows()}
    n_moved, tot_dnll = 0, 0.0
    for y, (fits, eta, dnll) in results.items():
        df.loc[df["year"] == y, "eta_mean"] = eta
        tot_dnll += dnll
        for age, (a, b, nu, tau) in fits.items():
            i = idx[(y, 1, age)]
            if abs(a - df.at[i, "alpha"]) > MOVE_TOL:
                n_moved += 1
            df.at[i, "alpha"], df.at[i, "beta"], df.at[i, "nu"], df.at[i, "tau"] = a, b, nu, tau
    # refresh men's censoring diagnostics at the new params (cheap, keeps the CSV self-consistent)
    for i, r in df[df["sex"] == 1].iterrows():
        tlo, thi = np.log(r["lowc"]), np.log(r["highc"])
        df.at[i, "p_low_model"]  = float(cf.nl_cdf(tlo, r["alpha"], r["beta"], r["nu"], r["tau"]))
        df.at[i, "p_high_model"] = float(1 - cf.nl_cdf(thi, r["alpha"], r["beta"], r["nu"], r["tau"]))
    etas = {y: e for y, (_f, e, _d) in results.items() if e > 0}
    print(f"moment match: {n_moved} men cells moved across {len(etas)} years (eta>0); "
          f"eta range [{min(etas.values(), default=0):.3g}, {max(etas.values(), default=0):.3g}]; "
          f"total negll cost {tot_dnll:,.0f} over {n_moved} cells "
          f"({tot_dnll / max(n_moved,1):.1f}/cell)", flush=True)
    return df


def main(outer=MAX_OUTER, window=WINDOW, jobs=None, moment=True):
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

    # final pass: pin each year's men alpha to the ASS uncapped mean (penalized profile-on-alpha),
    # correcting the censored upper-tail that the smoothed likelihood alone leaves too heavy.
    out_cols = ec.COLS
    if moment:
        df = moment_match(df, jobs)
        out_cols = ec.COLS + ["alpha_premoment", "eta_mean"]

    df[out_cols].to_csv(OUT, index=False)
    print(f"\nwrote {len(df)} penalized rows -> {OUT}  (window={window}, moment={moment})")


if __name__ == "__main__":
    kw = {}
    for flag, key, cast in [("--outer", "outer", int), ("--window", "window", int),
                            ("--jobs", "jobs", int)]:
        if flag in sys.argv:
            kw[key] = cast(sys.argv[sys.argv.index(flag) + 1])
    if "--no-moment" in sys.argv:          # skip the ASS uncapped-mean match (pure smoothing)
        kw["moment"] = False
    main(**kw)
