#!/usr/bin/env python
"""Preview for extrapolate_params: per parameter, the extrapolated (age x cohort) surface
with the observed-data footprint boxed, and cohort-profile slices at a young/prime/old age
overlaying the raw penalized points, the in-sample fit, and the linear tail."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("/private/tmp/claude-1919569421/-Users-jr2728-PhD-projects-epuf-2006/"
           "36722a59-b22f-4dad-aa02-e622040fd9a6/scratchpad")
PARAMS = {1: (["alpha", "beta", "nu", "tau"], 65),
          2: (["mu1", "mu2", "sig1", "sig2", "w"], 60)}


def _grid(df, sex, p):
    s = df[df.sex == sex].copy()
    g = s.pivot_table(index="cohort", columns="age", values=p, aggfunc="first")
    return g


def render(raw, full, dy0, dy1):
    for sex, (params, cut) in PARAMS.items():
        lab = "men" if sex == 1 else "women"
        r = raw[raw.sex == sex].copy(); r["cohort"] = r.year - r.age
        f = full[full.sex == sex]
        n = len(params)
        fig, ax = plt.subplots(n, 2, figsize=(13, 2.9 * n), constrained_layout=True,
                               squeeze=False, gridspec_kw={"width_ratios": [1.15, 1]})
        a_lo, a_hi = int(f.age.min()), int(f.age.max())
        ages_slice = [a_lo + 5, (a_lo + a_hi) // 2, a_hi - 3]
        for i, p in enumerate(params):
            G = _grid(f, sex, p)
            lo, hi = np.nanpercentile(r[p], 2), np.nanpercentile(r[p], 98)
            im = ax[i][0].imshow(G.to_numpy(float), origin="lower", aspect="auto",
                                 extent=[G.columns.min(), G.columns.max(),
                                         G.index.min(), G.index.max()],
                                 vmin=lo, vmax=hi, cmap="viridis")
            # data footprint: cohort = year-age for observed years, over the age range
            aa = np.array([a_lo, a_hi])
            for yb in (dy0, dy1):
                ax[i][0].plot(aa, yb - aa, "w--", lw=0.8, alpha=0.7)
            ax[i][0].axvline(cut, color="r", lw=0.6, alpha=0.5)
            ax[i][0].set_ylabel(f"{p}\n\ncohort"); ax[i][0].set_xlabel("age")
            if i == 0:
                ax[i][0].set_title(f"{lab}: extrapolated surface\n(dashed = data years "
                                   f"{int(dy0)}-{int(dy1)}, red = regime cut)", fontsize=10)
            fig.colorbar(im, ax=ax[i][0], fraction=0.046, pad=0.02)

            for a in ages_slice:
                fa = f[f.age == a].sort_values("cohort")
                ra = r[r.age == a].sort_values("cohort")
                line, = ax[i][1].plot(fa.cohort, fa[p], lw=1.3, label=f"age {a}")
                ax[i][1].scatter(ra.cohort, ra[p], s=6, color=line.get_color(), alpha=0.5)
            # mark where the tail takes over (last data cohort per shown age varies; show band)
            ax[i][1].axvspan(dy1 - a_hi, dy1 - a_lo, color="grey", alpha=0.06)
            ax[i][1].set_ylabel(p); ax[i][1].set_xlabel("cohort")
            ax[i][1].set_ylim(lo - 0.15 * abs(hi - lo), hi + 0.15 * abs(hi - lo))
            if i == 0:
                ax[i][1].set_title("cohort slices: points=penalized data, line=fit+tail",
                                   fontsize=10)
                ax[i][1].legend(fontsize=8, loc="best")
        fig.suptitle(f"{lab}: shape-constrained extrapolation", fontsize=13)
        fp = OUT / f"extrapolate_{lab}.png"
        fig.savefig(fp, dpi=125); plt.close(fig); print("wrote", fp)
