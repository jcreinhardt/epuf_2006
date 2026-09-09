#!/usr/bin/env python
"""Re-level a fitted g(t) so the model reproduces the published MEAN of log earnings, keeping
the fitted shape exactly.

WHY THIS STEP EXISTS.  The GKOS process cannot match the mean and the median of log earnings
at the same time: MEASURED over ages 25-55 and cohorts 1957-1983, its mean-minus-median is
+0.03 where the data's is -0.10 to -0.20, so the two targets sit 0.17 log points apart.  A fit
is therefore forced to choose, and the choice has consequences that split cleanly:

  * the MEDIAN is the right target for SHAPE.  It is robust to EPUF's top code, which is what
    lets EPUF discipline ages 20-70 at all (--mode smm-p50), and its EPUF-vs-GKSW wedge is
    small and flat in age (-0.063 men, slope -0.004/decade), so one intercept bridges it.
  * the MEAN is the right target for LEVEL.  Aggregate earnings are E[e^g] E[e^u], so a level
    fitted to the median inherits the whole skewness error: MEASURED, the p50 fit's model mean
    log sits +0.171 above the data, and the aggregate overshoots by about exp(0.171) on top of
    everything else.

Since g0 is a pure intercept and the hinges and curvature are shape, the two separate exactly.
This script keeps the shape a --mode smm-p50 fit learned from EPUF outside 25-55, and moves
only g0, per (sex, cohort), so that

    mean over the target ages of [ g(t) + E[u | u >= log(Ymin) - g(t)] - meanlog_data ] = 0.

The cut moves with g0, so this is a fixed point rather than a subtraction, solved by the same
cheap functional iteration the OLS bridge uses.  It is NOT a free re-fit: one scalar per block
against one published moment per block, and every other coefficient is untouched.

WHICH POPULATION THE LEVEL COMES FROM -- `--level`, and it is worth more than the choice of
functional.  `--level gksw` (the original) targets the published GKSW mean log.  But GKSW is
commerce-and-industry W-2 wages and the aggregate benchmark is ASS covered earnings over ALL
covered workers, and the EPUF-vs-GKSW wedge is statistic-dependent -- -0.063 in the MEDIAN but
-0.164 in the MEAN, for men -- so a level set from GKSW's mean lands the covered population's
level about 0.19 log points high.  MEASURED cell by cell against EPUF with EPUF's own worker
counts, that is the whole of the error: model/EPUF taxable 1.060, of which LEVEL is 1.195 and
shape 0.887 (`plots/plot_level_shape_decomp.py`).

`--level epuf` therefore targets EPUF's own mean log instead, over positive earners with no
sel0 screen, because ASS's universe is all covered workers.  EPUF is top-coded, so the MODEL IS
CLIPPED AT THE SAME CAP and the moment is mean log min(Y, C) on both sides: the top code then
cancels rather than biasing the target down.  The shape still comes entirely from the medians;
only g0 moves, exactly as with `--level gksw`.

The `delta` column -- the wedge in the MEDIAN -- does not convert either re-levelled profile
between populations, so it is dropped.  Run the aggregate with `--universe gksw` (which adds no
offset) in both cases.

Run from the project root:
    python code/dynamics/relevel_g_cohort.py [--fits CSV] [--level gksw|epuf] [--sel sel0]
Output: <stem>_relevelled.csv
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "code/dynamics")          # run from the project root, per repo convention
import gcohort_model as E
import epuf_targets as T


def prefix_tables(u):
    """Per age: (sorted finite u, prefix sums of u).  The capped mean log needs the mass BELOW
    the cut, which is the one thing `gcohort_model.suffix_tables` does not carry."""
    out = []
    for j in range(u.shape[1]):
        v = np.sort(u[np.isfinite(u[:, j]), j])
        out.append((v, np.concatenate([[0.0], np.cumsum(v)])))
    return out


def solve_shift(model, target, w, iters=200, tol=1e-12):
    """The scalar added to g0 driving the w-weighted mean of `model(s) - target` to zero.

    A fixed point, not a subtraction: both moments read the distribution at a cut that moves
    with g0, so the shift does not pass through one for one.  It converges in a few steps
    because the derivative is within a hair of 1 either way.
    """
    s = 0.0
    for _ in range(iters):
        step = float(np.average(target - model(s), weights=w))
        s += step
        if abs(step) < tol:
            break
    return s


def shift_gksw(row, ages, target, tables):
    """Match the published UNCAPPED mean log on the sel0-screened cells."""
    g0 = E.g_at(row, ages)
    jj, lym = E.sim_jj(ages), E.logymin(int(row.cohort), ages)
    model = lambda s: np.array([gi + s + E.cond_mean(tables[j], ci - gi - s)
                                for j, gi, ci in zip(jj, g0, lym)])
    return solve_shift(model, target, np.ones(ages.size))


def shift_epuf(row, ages, target, logcap, n, pre):
    """Match EPUF's mean log with the model clipped at the SAME cap, so the top code cancels."""
    g0 = E.g_at(row, ages)

    def model(s):
        out = np.empty(ages.size)
        for i, (j, gi, lc) in enumerate(zip(E.sim_jj(ages), g0 + s, logcap)):
            v, cv = pre[j]
            k = int(np.searchsorted(v, lc - gi))
            out[i] = (gi * k + cv[k] + lc * (v.size - k)) / v.size
        return out

    return solve_shift(model, target, n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits", default="output/dynamics/g_cohort_smm_p50.csv")
    ap.add_argument("--level", choices=["gksw", "epuf"], default="epuf",
                    help="population the LEVEL is taken from: the published GKSW mean log, or "
                         "EPUF's own mean log with the model clipped at the same top code. "
                         "The aggregate benchmark is ASS covered earnings, EPUF's universe.")
    ap.add_argument("--level-ages", nargs=2, type=int, default=[25, 55], metavar=("LO", "HI"),
                    help="ages the level is read on; the default keeps it inside the span the "
                         "shape was fitted to, so out-of-span shape error cannot leak into g0")
    ap.add_argument("--sel", default="sel0")
    ap.add_argument("--n", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=20260821)
    ap.add_argument("--min-ages", type=int, default=10,
                    help="ages a block needs before its level is re-read (--level epuf)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    u = E.simulate_u(np.random.default_rng(args.seed), args.n, E.SIM_AGES)
    tables = E.suffix_tables(u, order=2)
    pre = prefix_tables(u)
    lo, hi = args.level_ages
    ep = T.load_meanlog_capped() if args.level == "epuf" else None
    d = pd.read_csv(args.fits)
    d["relevel_shift"] = np.nan
    skipped = []
    for sex in ("female", "male"):
        tgt = E.load_moments(sex, args.sel)
        blk = {} if ep is None else {int(c): g for c, g in ep[ep.sex == sex].groupby("cohort")}
        for i, row in d[d.sex == sex].iterrows():
            c = int(row.cohort)
            if args.level == "gksw":
                ages = np.array([a for cc, a in tgt if cc == c])
                ages.sort()
                ages = ages[(ages >= lo) & (ages <= hi)]
                if ages.size == 0:
                    skipped.append((sex, c))
                    continue
                s = shift_gksw(row, ages, np.array([tgt[(c, a)][0] for a in ages]), tables)
            else:
                g = blk.get(c)
                g = None if g is None else g[g.age.between(lo, hi)]
                if g is None or len(g) < args.min_ages:
                    skipped.append((sex, c))
                    continue
                s = shift_epuf(row, g.age.to_numpy(int), g.meanlog.to_numpy(float),
                               g.logcap.to_numpy(float), g.n.to_numpy(float), pre)
            d.loc[i, "g0"] = row.g0 + s
            d.loc[i, "relevel_shift"] = s
    if skipped:
        print(f"  {len(skipped)} block(s) left un-relevelled for want of a target: "
              f"{skipped[:6]}{' ...' if len(skipped) > 6 else ''}")
    d["g0_raw"] = [E.uncentre(r)[0] for r in d[["g0", "g1", "g2", "g3"]].to_numpy(float)]
    d = d.drop(columns=[c for c in ("delta", "se_delta") if c in d.columns])

    out = args.out or args.fits.replace(".csv", "_relevelled.csv")
    d.to_csv(out, index=False, float_format="%.6f")
    print(f"wrote {out}  ({len(d)} blocks, level from {args.level.upper()} over ages "
          f"{lo}-{hi}; `delta` dropped, so run the aggregate with --universe gksw)")
    for sex in ("male", "female"):
        v = d[d.sex == sex]["relevel_shift"]
        print(f"  {sex:6s} g0 shift to hit meanlog: median {v.median():+.3f}, "
              f"range {v.min():+.3f} to {v.max():+.3f} log points")


if __name__ == "__main__":
    main()
