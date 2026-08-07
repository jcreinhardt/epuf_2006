#!/usr/bin/env python
"""Stage 2: precision-weighted, roughness-penalized smoothing of the per-cell fits.

The stage-1 estimates (estimate_cross_sections.py) are the global MLEs per cell,
but the weakly-identified parameters -- the dPlN upper-tail index, the mixture's
minority component -- sit on flat likelihood ridges, so their argmax slides a long
way between near-identical neighbouring cells at almost no likelihood cost. That
is under-determination, not error, so we borrow strength across neighbours.

For each parameter we solve, in the fitter's own theta coordinate (log alpha, nu,
logit w, ...), a Gaussian/Laplace approximation to the penalized MLE:

    minimise   Sum_c  w_c (theta_c - theta_hat_c)^2   +   lam * Sum_c r_c(theta)^2

w_c is the stored observed information (info_* columns) -- the Laplace weight, in
nats, kept on its ABSOLUTE scale (not normalized). It is near-zero along a ridge,
so there the penalty/neighbours set the value; it is ~1e4 where the parameter is
sharply pinned (nu, mu1), so those cells are effectively frozen and the well-
identified aggregate is preserved. lam is therefore an information threshold in the
same units: a parameter is borrowed from neighbours only where its own information
falls below ~lam; above that, the data wins.

The roughness r_c is the residual of a LOCAL LINEAR fit to the cell's NEIGHBORS
(the K nearest in age-cohort space): fit a plane to the neighbours, predict at the
cell, penalize the miss. On a 3-point line this is exactly the [1,-2,1] second
difference; over a K-neighbour 2D patch it is the wider-footprint, isotropic
generalization -- more global, and still trend-preserving (any planar nu/mu1
gradient is reproduced by the plane, so passes free; only curvature is charged).

Mode consistency (women): the two mixture components (the full-time vs part-time
story) must not cross or collapse across the grid. So instead of smoothing mu1 and
mu2 independently we smooth mu2 and the log-separation log(mu1 - mu2): mu1 is then
mu2 + exp(.) > mu2 at every cell by construction, and the separation itself is a
coherent smoothed surface. The gap gets a delta-method information weight.

Output feeds the next stage (a polynomial surface fit for extrapolation), which is
better posed on these precision-consistent surfaces than on the raw estimates.

  python code/cross_sections/smooth_params.py [--lam L] [--neighbors K]
    -> output/cross_sections/cross_section_params_smoothed.csv
       (+ param_heatmaps_{men,women}_smoothed.pdf/.png via param_visualization)
"""
import sys
from pathlib import Path

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.spatial import cKDTree
from scipy.sparse.linalg import spsolve

import crosssec_fit as cf
import param_visualization as pv

IN        = Path("output/cross_sections/cross_section_params.csv")
OUT       = Path("output/cross_sections/cross_section_params_smoothed.csv")
LAM       = 10.0    # smoothing strength = information threshold (nats); tune with --lam
NEIGHBORS = 5       # local-linear patch size (nearest neighbours in age-cohort space)
WFLOOR    = 1e-6    # min self-weight so ridge cells (info~0) stay solvable, neighbour-driven

# men: (param column, info column, theta transform). women handle mu1/mu2 via the gap
# reparameterization below; only these simple params go through the generic path.
# alpha is DELIBERATELY NOT smoothed: it is pinned in stage 1 by the uncapped-mean penalty
# (mean_pen), which lives in alpha's near-flat likelihood direction. Smoothing it here -- weighted
# by the pure-likelihood info_alpha, which reads that direction as unidentified -- would slide
# alpha off the moment (eroding the mean) and, because E[X] ~ 1/(alpha-1) is hyper-sensitive near
# the bound, a neighbour-pulled alpha ~= 1 blows the cell's mean up. So alpha passes through verbatim.
MEN   = [("beta", "info_beta", "log"),
         ("nu", "info_nu", "id"),        ("tau", "info_tau", "log")]
WOMEN_SIMPLE = [("sig1", "info_sig1", "logsig"), ("sig2", "info_sig2", "logsig"),
                ("w", "info_w", "logit")]


def to_theta(v, kind):
    if kind == "log":    return np.log(v)
    if kind == "logsig": return np.log(np.maximum(v - cf.SIG_FLOOR, 1e-6))
    if kind == "logit":  v = np.clip(v, 1e-6, 1 - 1e-6); return np.log(v / (1 - v))
    return np.asarray(v, dtype=float)                       # id


def from_theta(t, kind):
    if kind == "log":    return np.exp(t)
    if kind == "logsig": return cf.SIG_FLOOR + np.exp(t)
    if kind == "logit":  return 1.0 / (1.0 + np.exp(-t))
    return t


def local_linear_operator(ages, cohorts, K=None):
    """Sparse P whose row c is the residual of a local linear (planar) fit to cell
    c's K nearest neighbours, evaluated at c: theta_c - plane_pred_c. Reproduces any
    planar field exactly (trend-preserving); generalizes the [1,-2,1] 2nd difference
    to a wider, isotropic patch."""
    K = NEIGHBORS if K is None else K
    pts = np.column_stack([ages, cohorts]).astype(float)
    n = len(pts)
    _, idx = cKDTree(pts).query(pts, k=min(K + 1, n))       # K+1 includes self
    ii, jj, dat, r = [], [], [], 0
    for c in range(n):
        nb = [int(j) for j in np.atleast_1d(idx[c]) if j != c][:K]
        if not nb:
            continue
        Xnb = np.column_stack([np.ones(len(nb)), pts[nb, 0], pts[nb, 1]])
        xc  = np.array([1.0, pts[c, 0], pts[c, 1]])
        if len(nb) >= 3 and np.linalg.matrix_rank(Xnb) == 3:
            h = xc @ np.linalg.pinv(Xnb)                     # hat weights, sum to 1
        else:
            h = np.full(len(nb), 1.0 / len(nb))              # fall back to local mean
        ii.append(r); jj.append(c); dat.append(1.0)
        for w_, j in zip(h, nb):
            ii.append(r); jj.append(j); dat.append(-float(w_))
        r += 1
    return sparse.coo_matrix((dat, (ii, jj)), shape=(r, n)).tocsr()


def _solve(theta, w, lam, PtP):
    """One precision-weighted, roughness-penalized smooth of a single parameter."""
    w = np.where(np.isfinite(w) & (w > 0), w, 0.0)
    w = np.maximum(w, WFLOOR)
    A = (sparse.diags(w) + lam * PtP).tocsr()
    return spsolve(A, w * theta)


def smooth_sex(df, sex, lam):
    """Replace sex's parameter columns in df with their smoothed values."""
    sub = df[df["sex"] == sex]
    ages, cohorts = sub["age"].to_numpy(), (sub["year"] - sub["age"]).to_numpy()
    PtP = (lambda P: (P.T @ P).tocsr())(local_linear_operator(ages, cohorts))

    if sex == 1:                                             # men: 4 dPlN params, generic
        for name, infocol, kind in MEN:
            theta = to_theta(sub[name].to_numpy(dtype=float), kind)
            df.loc[sub.index, name] = from_theta(
                _solve(theta, sub[infocol].to_numpy(dtype=float), lam, PtP), kind)
        return df

    # women: smooth mu2 and log(mu1-mu2) so the two components stay ordered & distinct
    mu1, mu2 = sub["mu1"].to_numpy(dtype=float), sub["mu2"].to_numpy(dtype=float)
    gap = np.maximum(mu1 - mu2, 1e-3)
    i1 = np.maximum(sub["info_mu1"].to_numpy(dtype=float), 1e-9)
    i2 = np.maximum(sub["info_mu2"].to_numpy(dtype=float), 1e-9)
    info_gap = gap ** 2 / (1.0 / i1 + 1.0 / i2)             # delta method: info(log gap)
    mu2_s = _solve(mu2, i2, lam, PtP)
    gap_s = np.exp(_solve(np.log(gap), info_gap, lam, PtP))
    df.loc[sub.index, "mu2"] = mu2_s
    df.loc[sub.index, "mu1"] = mu2_s + gap_s               # > mu2 by construction
    for name, infocol, kind in WOMEN_SIMPLE:
        theta = to_theta(sub[name].to_numpy(dtype=float), kind)
        df.loc[sub.index, name] = from_theta(
            _solve(theta, sub[infocol].to_numpy(dtype=float), lam, PtP), kind)
    return df


def main(lam=LAM):
    df = pd.read_csv(IN)
    for sex in (1, 2):
        df = smooth_sex(df, sex, lam)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"wrote {len(df)} smoothed rows -> {OUT}  (lam={lam}, {NEIGHBORS} neighbours)")
    pv.main("both", OUT, "_smoothed")     # before/after: param_heatmaps_*_smoothed.png


if __name__ == "__main__":
    lam = LAM
    if "--lam" in sys.argv:
        lam = float(sys.argv[sys.argv.index("--lam") + 1])
    if "--neighbors" in sys.argv:
        NEIGHBORS = int(sys.argv[sys.argv.index("--neighbors") + 1])
    main(lam)
