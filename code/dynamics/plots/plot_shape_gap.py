#!/usr/bin/env python
"""Where the level error lives: the shape of log earnings, model vs GKSW, ages 25-55.

The model can be made to match the median OR the mean of log earnings, not both, and the
difference is worth ~0.17 log points on the level.  This figure says why, in two views of the
same mean-log-matched fit (so the level is netted out and only shape is left).

Left column -- SPREADS by age, in log points, data solid and model dashed.  The data's lower
half (p50-p10) is flat in age; the model's fans out from 0.79 to 1.31.  The data's upper half
(p90-p50) grows 0.53 -> 0.93; the model's runs ~0.4 above it at every age.  So the model's
dispersion is roughly symmetric in logs where the data's is one-sided, and it is the UPPER
half that is too wide -- which is the half E[e^x] is made of.

Right column -- CONTRIBUTION to E[Y | Y >= Ymin] by rank bin.  "data-shaped" is the model's
own draws mapped rank-preservingly onto the published log percentiles (piecewise linear
between p10..p98, end-segment slope outside), so it differs from the model by shape alone.
The excess sits entirely above p75 and is partly offset below it.

Run from the project root:
    python code/dynamics/plots/plot_shape_gap.py [--fits CSV]
Output: output/dynamics/plots/shape_gap.{pdf,png}
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

OUT = "output/dynamics/plots"
QS = np.array(E.QUANTS)
EDGES = np.array([0.0, .10, .25, .50, .75, .90, .98, 1.0])
BINS = ["0-10", "10-25", "25-50", "50-75", "75-90", "90-98", "98-100"]
SPREADS = (("p50", "p10", "#2a78d6"), ("p90", "p50", "#eb6834"), ("p98", "p90", "#7a5195"))


def cells(fit, tails):
    """Per (sex, cohort, age): the model's truncated log-earnings draws and the data vector."""
    for label, _ in E.SEXES:
        tgt = E.load_moments(label, "sel0")
        for _, r in fit[fit.sex == label].iterrows():
            c = int(r.cohort)
            ages = np.array([a for a in E.AGES if (c, a) in tgt])
            if ages.size < E.AGES.size:          # complete 25-55 spans only
                continue
            g = E.g_at(r, ages)
            for a, gi, j, cut in zip(ages, g, E.sim_jj(ages), E.logymin(c, ages) - g):
                v = tails[j]
                yield label, c, a, gi + v[np.searchsorted(v, cut, side="left"):], tgt[(c, a)]


def data_shaped(w, dq):
    """`w` mapped rank-preservingly onto the published log percentiles `dq`."""
    mq = np.quantile(w, QS)
    x = np.interp(w, mq, dq)
    lo = (dq[1] - dq[0]) / (mq[1] - mq[0])
    hi = (dq[-1] - dq[-2]) / (mq[-1] - mq[-2])
    x = np.where(w < mq[0], dq[0] + lo * (w - mq[0]), x)
    return np.where(w > mq[-1], dq[-1] + hi * (w - mq[-1]), x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fits", default="output/dynamics/g_cohort_smm_p50_relevelled.csv",
                    help="a mean-log-matched fit, so the panels show shape and not level")
    ap.add_argument("--n", type=int, default=400_000)
    ap.add_argument("--seed", type=int, default=20260821)
    ap.add_argument("--outdir", default=OUT)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    u = E.simulate_u(np.random.default_rng(a.seed), a.n, E.SIM_AGES)
    tails = [np.sort(u[np.isfinite(u[:, j]), j]) for j in range(u.shape[1])]
    fit = pd.read_csv(a.fits)

    sp, con = [], []
    for label, c, age, w, dv in cells(fit, tails):
        mq = dict(zip(E.MOMENTS[4:], np.quantile(w, QS)))
        dq = dict(zip(E.MOMENTS[4:], dv[4:]))
        sp.append(dict(sex=label, age=age,
                       **{f"{hi}-{lo}_{k}": q[hi] - q[lo] for hi, lo, _ in SPREADS
                          for k, q in (("data", dq), ("model", mq))}))
        x = data_shaped(w, dv[4:])
        k = (EDGES * w.size).astype(int)
        con += [dict(sex=label, bin=b, model=np.exp(w[i:j]).sum() / w.size,
                     data=np.exp(x[i:j]).sum() / w.size)
                for i, j, b in zip(k[:-1], k[1:], BINS)]
    sp, con = pd.DataFrame(sp), pd.DataFrame(con)

    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    for i, sex in enumerate(("male", "female")):
        axl, axr = axes[i]
        s = sp[sp.sex == sex].groupby("age").mean(numeric_only=True)
        for hi, lo, col in SPREADS:
            axl.plot(s.index, s[f"{hi}-{lo}_data"], color=col, lw=1.8, label=f"{hi}-{lo} data")
            axl.plot(s.index, s[f"{hi}-{lo}_model"], color=col, lw=1.6, ls="--",
                     label=f"{hi}-{lo} model")
        axl.set_xlabel("age")
        axl.set_ylabel(f"{sex}: spread of log earnings")
        axl.legend(fontsize=7, frameon=False, ncol=3)

        b = con[con.sex == sex].groupby("bin").mean(numeric_only=True).loc[BINS] / 1e3
        x = np.arange(len(BINS))
        axr.bar(x - .2, b.model, .4, color="#eb6834", label="model")
        axr.bar(x + .2, b.data, .4, color="0.35", label="data-shaped (same ranks)")
        axr.set_xticks(x, BINS, fontsize=7)
        axr.set_xlabel("rank bin of log earnings (percentile)")
        axr.set_ylabel(f"{sex}: contribution to E[Y] ($k, 2013)")
        axr.legend(fontsize=7, frameon=False)
        axr.set_title(f"E[Y] model / data-shaped = {b.model.sum() / b.data.sum():.3f}",
                      fontsize=8, loc="right")
        for ax in (axl, axr):
            ax.tick_params(labelsize=8)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
    fig.suptitle("log-earnings shape, model vs GKSW sel0, ages 25-55, level netted out",
                 fontsize=10)
    fig.tight_layout()
    path = os.path.join(a.outdir, "shape_gap")
    for ext in ("pdf", "png"):
        fig.savefig(f"{path}.{ext}", dpi=200, bbox_inches="tight")
    print(f"wrote {path}.pdf/.png")


if __name__ == "__main__":
    main()
