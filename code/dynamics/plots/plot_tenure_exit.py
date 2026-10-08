#!/usr/bin/env python
"""Share employed at a by years CONTINUOUSLY employed before a (`tenure_exit.py`): everybody at ages 30 / 45 / 55,
x = the length of the employment spell ending at a-1 (0 = not employed at a-1, a-20 = employed every year since
20), y = share employed at a. EPUF vs the GKOS model vs the estimated specs; rows = men | women, columns = ages.
Bins of fewer than MIN_N EPUF people are not drawn. A second pair of figures (tenure_exit_lq_{men,women}) repeats
the panels within quartiles of lifetime earnings (rows), where the attachment question of the findings doc lives;
there tenures beyond 15 are pooled into one '16+' point (n-weighted).

Run from the project root:
    python code/dynamics/plots/plot_tenure_exit.py [--yob 1937] [--specs absq_alpha ...] [--tag _x]
Output: output/dynamics/plots/tenure_exit_yob<YOB><tag>.{png,pdf}
        output/dynamics/plots/tenure_exit_lq_{men,women}_yob<YOB><tag>.{png,pdf}
"""
import argparse
import os

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PROJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(PROJ, "output", "dynamics", "plots")
DARK, GRID = "#3d3d3d", "#dcdcdc"
STYLE = {"epuf": dict(color="#8a8a8a", marker="o", label="EPUF"),
         "gcohort": dict(color="#D55E00", marker="s", label="GKOS model"),
         "absq_alpha": dict(color="#56B4E9", marker="X", label="Modified GKOS"),
         "sexlag_absq": dict(color="#0072B2", marker="P", label="Modified GKOS, no α term"),
         "absq_ten": dict(color="#009E73", marker="D", label="Tenure ramp, no α term"),
         "absq_ewma": dict(color="#CC79A7", marker="v", label="Attachment stock, no α term")}
SEX = {1: "Men", 2: "Women"}
MIN_N = 30
plt.rcParams.update({"font.size": 11, "text.color": DARK, "axes.labelcolor": DARK, "axes.edgecolor": DARK,
                     "xtick.color": DARK, "ytick.color": DARK, "axes.titlecolor": DARK})


def draw(d, specs, yob, tag):
    fig, axes = plt.subplots(2, 3, figsize=(14, 7.6))
    for r, sex in enumerate((1, 2)):
        for c, a in enumerate((30, 45, 55)):
            ax = axes[r, c]
            p = d[(d.sex == sex) & (d.age == a)]
            keep = p[(p.source == "epuf") & (p.n >= MIN_N)].x
            for src in ["epuf", "gcohort"] + list(specs):
                st = STYLE.get(src, dict(color="#000000", marker=".", label=src))
                q = p[(p.source == src) & p.x.isin(keep)].sort_values("x")
                ax.plot(q.x, q.share, color=st["color"], marker=st["marker"], ms=4.5, lw=1.6, label=st["label"],
                        zorder=3 if src == "epuf" else 2)
            ax.set_xlim(-0.5, a - 20 + 0.5)
            ax.set_ylim(0, 1)
            ax.grid(True, color=GRID, lw=0.7)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
            ax.set_title(f"{SEX[sex]}, age {a}", loc="left", fontsize=11)
            if c == 0:
                ax.set_ylabel("Share employed at a")
            if r == 1:
                ax.set_xlabel("Years continuously employed before a" + (" (0: not employed at a−1)" if c == 1 else ""))
    axes[0, 0].legend(fontsize=9, frameon=False, loc="lower right")
    fig.suptitle(f"Employment at a by the length of the employment spell coming into a, cohort {yob}",
                 fontsize=12, color=DARK, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"tenure_exit_yob{yob}{tag}.{ext}"), dpi=150)
    plt.close(fig)


def pooled(s, xmax):
    """Pool x > xmax into one point at xmax + 1 (n-weighted)."""
    s = s.assign(x=np.minimum(s.x, xmax + 1), w=s.share * s.n)
    w = s.groupby("x", as_index=False).agg(w=("w", "sum"), n=("n", "sum"))
    return w.assign(share=w.w / w.n).sort_values("x")


def draw_lq(d, sex, specs, yob, tag, xmax=15):
    fig, axes = plt.subplots(4, 3, figsize=(14, 12.5), sharey=True)
    for r, qq in enumerate(("q1", "q2", "q3", "q4")):
        for c, a in enumerate((30, 45, 55)):
            ax = axes[r, c]
            p = d[(d.stat == "tenure_lq") & (d.sex == sex) & (d.age == a) & (d.group == qq)]
            ref = pooled(p[p.source == "epuf"], xmax)
            keep = ref[ref.n >= MIN_N].x
            for src in ["epuf", "gcohort"] + list(specs):
                st = STYLE.get(src, dict(color="#000000", marker=".", label=src))
                q = pooled(p[p.source == src], xmax)
                q = q[q.x.isin(keep)]
                ax.plot(q.x, q.share, color=st["color"], marker=st["marker"], ms=4.5, lw=1.6, label=st["label"],
                        zorder=3 if src == "epuf" else 2)
            hi = min(a - 20, xmax + 1)
            ax.set_xlim(-0.5, hi + 0.5)
            if a - 20 > xmax:
                ax.set_xticks(list(range(0, xmax, 5)) + [xmax + 1])
                ax.set_xticklabels([str(v) for v in range(0, xmax, 5)] + [f"{xmax + 1}+"])
            ax.set_ylim(0, 1)
            ax.grid(True, color=GRID, lw=0.7)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
            ax.set_title(f"{SEX[sex]}, lifetime-earnings {qq.upper()}, age {a}", loc="left", fontsize=10.5)
            if c == 0:
                ax.set_ylabel("Share employed at a")
            if r == 3:
                ax.set_xlabel("Years continuously employed before a" + (" (0: not employed at a−1)" if c == 1 else ""))
    axes[0, 0].legend(fontsize=9, frameon=False, loc="lower right")
    fig.suptitle(f"Employment at a by the length of the employment spell coming into a, within lifetime-earnings "
                 f"quartiles, {SEX[sex].lower()}, cohort {yob}", fontsize=12, color=DARK, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"tenure_exit_lq_{SEX[sex].lower()}_yob{yob}{tag}.{ext}"), dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yob", type=int, default=1937)
    ap.add_argument("--specs", nargs="+", default=["absq_alpha"])
    ap.add_argument("--tag", default=None, help="output-name suffix (default: '' for absq_alpha alone, else the specs)")
    args = ap.parse_args()
    d = pd.read_csv(os.path.join(PROJ, "output", "dynamics", f"tenure_exit_yob{args.yob}.csv"))
    os.makedirs(OUT, exist_ok=True)
    tag = args.tag if args.tag is not None else ("" if args.specs == ["absq_alpha"] else "_" + "_".join(args.specs))
    draw(d[d.stat == "tenure"], args.specs, args.yob, tag)
    print("wrote", f"tenure_exit_yob{args.yob}{tag}.png")
    for sex in (1, 2):
        draw_lq(d, sex, args.specs, args.yob, tag)
        print("wrote", f"tenure_exit_lq_{SEX[sex].lower()}_yob{args.yob}{tag}.png")


if __name__ == "__main__":
    main()
