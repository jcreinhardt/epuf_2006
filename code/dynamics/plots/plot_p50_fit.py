#!/usr/bin/env python
"""The two-block p50 fit, one cohort, men and women: what each source says and what the
model says about it.

Four series per panel, which is the whole design in one picture:

  GKSW p50      the published median, ages 25-55 -- the in-span target
  EPUF p50      the same statistic on EPUF, ages 20-70 -- the out-of-span target, and the
                only data outside the GKSW window
  model         g(t) + Q50(u | u >= log(Ymin) - g(t)), the model's own median: it should
                lie on the GKSW points in-span
  model + delta the same curve shifted by the fitted wedge intercept: it should lie on the
                EPUF points, in-span AND out

If the design works, each model curve tracks its own source and the vertical distance
between the two curves is constant, because delta is one number per block.  Where the two
data series are NOT a constant apart, that is the part of the EPUF-GKSW wedge a single
intercept cannot absorb.  The shaded band is the GKSW span; outside it g is the quadratic
plus a one-sided hinge, and the EPUF points are the only thing holding it down.

Run from the project root:
    python code/dynamics/plots/plot_p50_fit.py [--cohort 1970] [--fits CSV]
Output: output/dynamics/plots/p50_fit_<cohort>.{pdf,png}
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "code/dynamics")          # run from the project root, per repo convention
import gcohort_model as E
import epuf_targets as P
import gcohort_epuf as G

OUT = "output/dynamics/plots"
C_GKSW, C_EPUF, C_MODEL, C_SHIFT = "#1a1a19", "#2a78d6", "#eb6834", "#7a5195"


def model_median(row, ages, vs):
    """g(t) + Q50(u | u >= log(Ymin) - g(t)) at `ages`; g via the shared hinge-aware
    evaluator, so this draws exactly what the estimator fitted."""
    g = E.g_at(row, ages)
    lym = E.logymin(int(row.cohort), ages)
    return np.array([gi + G.cond_median(vs[j], ci - gi)
                     for j, gi, ci in zip(E.sim_jj(ages), g, lym)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", type=int, default=1970)
    ap.add_argument("--fits", default="output/dynamics/g_cohort_smm_p50.csv")
    ap.add_argument("--n", type=int, default=200_000)
    ap.add_argument("--seed", type=int, default=20260821)
    ap.add_argument("--degree", type=int, default=2)
    ap.add_argument("--outdir", default=OUT)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    c = args.cohort

    u = E.simulate_u(np.random.default_rng(args.seed), args.n, E.SIM_AGES)
    vs = [np.sort(u[np.isfinite(u[:, j]), j]) for j in range(u.shape[1])]
    fits = pd.read_csv(args.fits)
    ep = P.load_p50()

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), sharey=False)
    for ax, sex in zip(axes, ("male", "female")):
        row = fits[(fits.sex == sex) & (fits.cohort == c)].iloc[0]
        tgt = E.load_moments(sex, "sel0")
        ga = np.array(sorted(a for cc, a in tgt if cc == c))
        gy = np.array([tgt[(c, a)][E.MOMENTS.index("p50")] for a in ga])
        e = ep[(ep.sex == sex) & (ep.cohort == c) & ep.usable]

        ages = E.SIM_AGES
        m = model_median(row, ages, vs)
        ax.axvspan(E.KNOTS[0], E.KNOTS[1], color="0.93", zorder=0)
        ax.plot(ages, m, color=C_MODEL, lw=2.0, zorder=3, label="model median")
        ax.plot(ages, m + row.delta, color=C_SHIFT, lw=2.0, ls=(0, (4, 2)), zorder=3,
                label=f"model median + $\\delta$ ({row.delta:+.3f})")
        ax.plot(ga, gy, "o", ms=5, mfc="none", mew=1.3, color=C_GKSW, zorder=4,
                label="GKSW p50 (target, 25-55)")
        ax.plot(e.age, e.p50, "s", ms=4, mfc="none", mew=1.1, color=C_EPUF, zorder=4,
                label="EPUF p50 (target, 20-70)")
        ax.set_title(f"{'Men' if sex == 'male' else 'Women'}   "
                     f"$h_{{young}}$ {row.h_young:+.2f}, $h_{{old}}$ {row.h_old:+.2f}"
                     + ("  (h_old pooled)" if row.h_old_filled else ""), fontsize=10)
        ax.set_xlabel("age")
        ax.set_ylabel("median log earnings (2013 $)")
        ax.legend(frameon=False, fontsize=8, loc="lower right")
        ax.tick_params(labelsize=8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    fig.suptitle(f"cohort {c} (age 25 in {c}): median log earnings, both target sources; "
                 f"shaded = the GKSW span", fontsize=10)
    fig.tight_layout()
    path = os.path.join(args.outdir, f"p50_fit_{c}")
    for ext in ("pdf", "png"):
        fig.savefig(f"{path}.{ext}", dpi=200, bbox_inches="tight")
    print(f"wrote {path}.pdf/.png")


if __name__ == "__main__":
    main()
