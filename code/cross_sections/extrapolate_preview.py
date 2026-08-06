#!/usr/bin/env python
"""Preview for extrapolate_params (anchor + wage-driven method): per parameter, the
extrapolated (age x cohort) surface with the observed-data footprint dashed, and
cohort-profile slices at a young/prime/old age overlaying the iterated in-sample
points, the kept in-sample line, and the wage-driven / frozen extrapolation."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("/private/tmp/claude-1919569421/-Users-jr2728-PhD-projects-epuf-2006/"
           "36722a59-b22f-4dad-aa02-e622040fd9a6/scratchpad")
PARAMS = {1: (["nu", "alpha", "beta", "tau"], 77),
          2: (["mu1", "mu2", "sig1", "sig2", "w"], 74)}
LOC = {"nu", "mu1", "mu2"}          # wage-driven (trend); the rest are frozen


def _grid(df, sex, p):
    s = df[df.sex == sex]
    return s.pivot_table(index="cohort", columns="age", values=p, aggfunc="first")


def render(raw, full, dy0, dy1):
    for sex, (params, a_hi) in PARAMS.items():
        lab = "men" if sex == 1 else "women"
        r = raw[raw.sex == sex].copy(); r["cohort"] = r.year - r.age
        f = full[full.sex == sex]
        n = len(params)
        fig, ax = plt.subplots(n, 2, figsize=(13, 2.9 * n), constrained_layout=True,
                               squeeze=False, gridspec_kw={"width_ratios": [1.15, 1]})
        a_lo = int(f.age.min())
        ages_slice = [a_lo + 5, (a_lo + a_hi) // 2, a_hi - 3]
        for i, p in enumerate(params):
            G = _grid(f, sex, p)
            lo, hi = np.nanpercentile(r[p], 2), np.nanpercentile(r[p], 98)
            im = ax[i][0].imshow(G.to_numpy(float), origin="lower", aspect="auto",
                                 extent=[G.columns.min(), G.columns.max(),
                                         G.index.min(), G.index.max()],
                                 vmin=lo, vmax=hi, cmap="viridis")
            aa = np.array([a_lo, a_hi])
            for yb in (dy0, dy1):
                ax[i][0].plot(aa, yb - aa, "w--", lw=0.8, alpha=0.7)
            tag = "wage-driven" if p in LOC else "frozen 2000-04"
            ax[i][0].set_ylabel(f"{p} ({tag})\n\ncohort"); ax[i][0].set_xlabel("age")
            if i == 0:
                ax[i][0].set_title(f"{lab}: extrapolated surface "
                                   f"(dashed = data years {int(dy0)}-{int(dy1)})", fontsize=10)
            fig.colorbar(im, ax=ax[i][0], fraction=0.046, pad=0.02)

            for a in ages_slice:
                fa = f[f.age == a].sort_values("cohort")
                ra = r[r.age == a].sort_values("cohort")
                line, = ax[i][1].plot(fa.cohort, fa[p], lw=1.3, label=f"age {a}")
                ax[i][1].scatter(ra.cohort, ra[p], s=6, color=line.get_color(), alpha=0.5)
            ax[i][1].axvspan(dy0 - a_hi, dy1 - a_lo, color="grey", alpha=0.06)
            ax[i][1].set_ylabel(p); ax[i][1].set_xlabel("cohort")
            ax[i][1].set_ylim(lo - 0.15 * abs(hi - lo), hi + 0.15 * abs(hi - lo))
            if i == 0:
                ax[i][1].set_title("cohort slices: points=iterated, line=kept+extrapolation",
                                   fontsize=10)
                ax[i][1].legend(fontsize=8, loc="best")
        fig.suptitle(f"{lab}: anchor + wage-driven extrapolation", fontsize=13)
        fp = OUT / f"extrapolate_{lab}.png"
        fig.savefig(fp, dpi=125); plt.close(fig); print("wrote", fp)
