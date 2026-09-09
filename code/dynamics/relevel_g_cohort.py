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

The re-levelled profile describes GKSW's population, so the `delta` column -- the wedge in the
MEDIAN -- no longer converts it to EPUF's, and is dropped.  The EPUF-vs-GKSW wedge is
statistic-dependent (-0.063 in the median but -0.164 in the mean, for men), which is itself
worth remembering: any bridge between the two sources is only valid for the statistic it was
estimated on.  Run the aggregate on this file with `--universe gksw`.

Run from the project root:
    python code/dynamics/relevel_g_cohort.py [--fits CSV] [--sel sel0]
Output: <stem>_relevelled.csv
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "code/dynamics")          # run from the project root, per repo convention
import gcohort_model as E


def shift_for(row, ages, target, tables, iters=200):
    """The scalar added to g0 that makes the model's mean log match `target` on average."""
    g0 = E.g_at(row, ages)
    jj, lym = E.sim_jj(ages), E.logymin(int(row.cohort), ages)
    s = 0.0
    for _ in range(iters):
        g = g0 + s
        m = np.array([gi + E.cond_mean(tables[j], ci - gi)
                      for j, gi, ci in zip(jj, g, lym)])
        step = float(np.mean(target - m))
        s += step
        if abs(step) < 1e-12:
            break
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits", default="output/dynamics/g_cohort_smm_p50.csv")
    ap.add_argument("--sel", default="sel0")
    ap.add_argument("--n", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=20260821)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    u = E.simulate_u(np.random.default_rng(args.seed), args.n, E.SIM_AGES)
    tables = E.suffix_tables(u, order=2)
    d = pd.read_csv(args.fits)
    d["relevel_shift"] = np.nan
    for sex in ("female", "male"):
        tgt = E.load_moments(sex, args.sel)
        for i, row in d[d.sex == sex].iterrows():
            c = int(row.cohort)
            ages = np.array(sorted(a for cc, a in tgt if cc == c))
            y = np.array([tgt[(c, a)][0] for a in ages])
            s = shift_for(row, ages, y, tables)
            d.loc[i, "g0"] = row.g0 + s
            d.loc[i, "relevel_shift"] = s
    d["g0_raw"] = [E.uncentre(r)[0] for r in d[["g0", "g1", "g2", "g3"]].to_numpy(float)]
    d = d.drop(columns=[c for c in ("delta", "se_delta") if c in d.columns])

    out = args.out or args.fits.replace(".csv", "_relevelled.csv")
    d.to_csv(out, index=False, float_format="%.6f")
    print(f"wrote {out}  ({len(d)} blocks; `delta` dropped -- this profile is GKSW-levelled, "
          f"so run the aggregate with --universe gksw)")
    for sex in ("male", "female"):
        v = d[d.sex == sex]["relevel_shift"]
        print(f"  {sex:6s} g0 shift to hit meanlog: median {v.median():+.3f}, "
              f"range {v.min():+.3f} to {v.max():+.3f} log points")


if __name__ == "__main__":
    main()
