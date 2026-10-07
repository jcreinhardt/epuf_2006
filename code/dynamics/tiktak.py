"""TikTak, the multistart global optimizer of Arnoud, Guvenen and Kleineberg (2022, Section 2.1 and Appendix A),
minimal and parallel. Library only; `estimate_nonemp.py --tiktak N` uses it.

The procedure, for f on the box [lo, hi]:
  0. draw N scrambled Sobol' points in the box and evaluate f at all of them (in parallel);
  1. keep the N* best as seeds, sorted by f (AGK: N* = 10% of N; default here one batch of `workers`, since the
     first local search from every seed is where the cost is, and step 3 extends the list if needed);
  2. local searches start from a convex combination of the next seed and the best local minimum found so far,
         start_i = (1 - theta_i) s_i + theta_i Z*,   theta_i = min(max(theta_min, (i / N*)^gamma), theta_max);
     AGK use gamma = 1/2, theta_min = 0.1, theta_max = 0.995. gamma < 1/2 is steeper: the weight on the incumbent
     rises faster, so the search concentrates sooner.
     Searches run `workers` at a time (the parallel variant on AGK's website): one batch shares one Z*, and Z* is
     updated after each batch.
  3. stop when the last two DIFFERENT values of Z* are within `tol` of each other (AGK's heuristic) and at least
     N* seeds have been used; if not converged after N* seeds, keep going down the sorted Sobol' list until it
     converges, the list runs out, or `budget` seconds have passed;
  4. polish: one local search from Z* with a tight tolerance.

LOCAL SEARCH: derivative-free, because f is a simulated-moments objective with common random numbers, so it is
piecewise constant in theta (every moment is a share of indicator draws) and gradients, automatic or finite-difference,
are zero or garbage. `local` is "nm" (Nelder-Mead, adaptive, initial simplex `step` x the box width) or "powell";
both use scipy's box support. Tolerances are absolute, in the units of f and theta.

PARALLELISM: `multiprocessing` with the fork start method, so f (a closure over large simulation state) is inherited
by the workers rather than pickled. Set OMP/BLAS threads to 1 before numpy is imported in the parent.
"""
import multiprocessing as mp
import time

import numpy as np
from scipy.optimize import minimize
from scipy.stats import qmc

_F = None       # the objective; set in the parent before the pool forks, inherited by the workers


def _eval(x):
    return _F(x)


def _local(args):
    """One local search; returns (x, f, nfev)."""
    x0, lo, hi, method, maxfev, tol, step = args
    bounds = list(zip(lo, hi))
    if method == "nm":
        simplex = np.vstack([x0] + [np.clip(x0 + step * (hi - lo) * np.eye(x0.size)[i], lo, hi)
                                    for i in range(x0.size)])
        res = minimize(_F, x0, method="Nelder-Mead", bounds=bounds,
                       options=dict(maxfev=maxfev, xatol=tol, fatol=tol, adaptive=True, initial_simplex=simplex))
    elif method == "powell":
        res = minimize(_F, x0, method="Powell", bounds=bounds, options=dict(maxfev=maxfev, xtol=tol, ftol=tol))
    else:
        raise ValueError(method)
    return np.asarray(res.x, float), float(res.fun), int(res.nfev)


def theta_rule(i, n_keep, gamma, theta_min, theta_max):
    return min(max(theta_min, (i / n_keep) ** gamma), theta_max)


def tiktak(f, lo, hi, n_sobol=256, n_keep=None, workers=8, local="nm", gamma=0.25, theta_min=0.1,
           theta_max=0.995, maxfev=120, tol=1e-2, step=0.1, polish_maxfev=200, polish_tol=1e-3, budget=300.0,
           seed=0, log=print):
    """Minimise f over the box [lo, hi]. Returns (x_best, f_best, history), history a list of dicts, one per
    local search (plus the polish), with start, x, f, nfev, theta, stage."""
    global _F
    _F = f
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    d = lo.size
    n_keep = n_keep or workers              # one batch: the first local search from every seed is the costly part
    t0 = time.time()
    S = qmc.scale(qmc.Sobol(d, scramble=True, seed=seed).random(n_sobol), lo, hi)
    ctx = mp.get_context("fork")
    hist = []
    with ctx.Pool(workers) as pool:
        fs = np.array(pool.map(_eval, S, chunksize=max(1, n_sobol // (4 * workers))))
        order = np.argsort(fs)
        best_x, best_f = S[order[0]].copy(), fs[order[0]]
        log(f"sobol: {n_sobol} points in {time.time() - t0:.0f}s; best {best_f:.4f} at "
            + " ".join(f"{v:+.3f}" for v in best_x) + f"; keeping {n_keep}")
        i, zs = 0, [best_f]                      # zs: the successive DIFFERENT values of Z*
        while i < n_sobol:
            if i >= n_keep:
                if len(zs) >= 2 and abs(zs[-1] - zs[-2]) < tol:
                    log(f"converged: last two Z* {zs[-2]:.4f} -> {zs[-1]:.4f}")
                    break
                if time.time() - t0 > budget:
                    log(f"budget: {budget:.0f}s elapsed after {i} local searches")
                    break
            idx = order[i:i + workers]
            thetas = [theta_rule(i + k + 1, n_keep, gamma, theta_min, theta_max) for k in range(len(idx))]
            starts = [(1 - th) * S[j] + th * best_x for th, j in zip(thetas, idx)]
            res = pool.map(_local, [(x0, lo, hi, local, maxfev, tol, step) for x0 in starts], chunksize=1)
            for x0, th, (x, fv, nfev) in zip(starts, thetas, res):
                hist.append(dict(stage="local", theta=th, start=x0, x=x, f=fv, nfev=nfev))
                if fv < best_f - 1e-12:
                    best_x, best_f = x.copy(), fv
            if best_f != zs[-1]:
                zs.append(best_f)
            i += len(idx)
            log(f"  searches {i:4d}  theta {thetas[-1]:.3f}  batch best {min(r[1] for r in res):.4f}  "
                f"Z* {best_f:.4f}  " + " ".join(f"{v:+.3f}" for v in best_x) + f"  [{time.time() - t0:.0f}s]")
    x, fv, nfev = _local((best_x, lo, hi, local, polish_maxfev, polish_tol, step / 4))
    hist.append(dict(stage="polish", theta=1.0, start=best_x, x=x, f=fv, nfev=nfev))
    if fv < best_f:
        best_x, best_f = x, fv
    log(f"polish: {fv:.4f} ({nfev} evals); done in {time.time() - t0:.0f}s, "
        f"{sum(h['nfev'] for h in hist) + n_sobol} evaluations")
    return best_x, best_f, hist
