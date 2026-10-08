#!/usr/bin/env python
"""Entry into covered work and what follows: the distribution of the age at the first positive covered-earnings year
(20-30), and average lifetime earnings by that age. EPUF against GKOS and the modified model, one birth cohort,
both sexes.

Entry age is the first positive year within the 20-65 window on both sides (the models simulate earnings from 20).
The default cohort is 1937: military pay is covered from 1957, the year it turned 20, so a first positive year at
20+ really is late entry -- unlike the 1932 cohort, whose men were 18-21 in 1950-53 (Korean War service, uncovered).
The model parameters come from the cohort `--params-yob` (default: the same cohort); with another cohort's
parameters the figure is out of sample and its file name carries `_p<params-yob>`.

Lifetime earnings: real (2013$) covered earnings summed over ages 20-65, zeros included (the dead too), CAPPED at
each year's taxable maximum on both sides -- EPUF's values are capped, so the model is capped the same way.
Base: everybody with any covered earnings at 20-65 (as in transition_rates.py).

Run from the project root:
    python code/dynamics/plots/plot_entry_age.py [--yob 1937] [--model absq_alpha] [--params-yob 1932]
Output: output/dynamics/plots/transition_entry_age_yob<YOB>[_p<PARAMS-YOB>].{png,pdf}
"""
import argparse
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PROJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(PROJ, "code", "dynamics"))
import estimate_nonemp as EN  # noqa: E402
import nonemp_model as NM  # noqa: E402
import transition_rates as TR  # noqa: E402
from plot_transition_rates import STYLE  # noqa: E402

A0, A1 = TR.A0, TR.A1
AGES = list(range(20, 31))


def summarise(E, cap, real):
    """E (n, 46) nominal earnings, anybody with a positive year -> share and mean capped lifetime earnings ($k) by
    entry age 20-30, plus the share entering after 30."""
    E = np.minimum(E[(E > 0).any(1)], cap[None, :])
    entry = A0 + np.argmax(E > 0, 1)
    life = (E / real[None, :]).sum(1)
    return pd.DataFrame({"share": [np.mean(entry == a) for a in AGES],
                         "mean": [life[entry == a].mean() / 1000 if (entry == a).any() else np.nan for a in AGES]},
                        index=AGES), np.mean(entry > 30)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yob", type=int, default=1937)
    ap.add_argument("--model", default="absq_alpha", choices=[k for k in EN.SPECS if k != "full"])
    ap.add_argument("--params-yob", type=int, default=None,
                    help="cohort the --model parameters were estimated on (default: --yob)")
    ap.add_argument("--n-sim", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=20261006)
    ap.add_argument("--root", default=TR.ROOT_DEFAULT)
    args = ap.parse_args()
    args.params_yob = args.params_yob or args.yob
    out = os.path.join(PROJ, "output", "dynamics", "plots", f"transition_entry_age_yob{args.yob}"
                       + ("" if args.params_yob == args.yob else f"_p{args.params_yob}"))
    P = EN.Problem(args.root, args.yob, args.n_sim, args.seed)
    est = pd.read_csv(os.path.join(PROJ, "output", "dynamics",
                                   f"nonemp_params_yob{args.params_yob}_{args.model}.csv")).estimate.to_numpy()
    models = {"gcohort": EN.expand([-3.353, -3.353], "sexint"), args.model: EN.expand(est, args.model)}
    series = (("epuf", STYLE["epuf"]), ("gcohort", STYLE["gcohort"]), (args.model, STYLE[args.model]))

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
    rows = []
    x = np.arange(len(AGES))
    for k, sex in enumerate((1, 2)):
        S, late = {}, {}
        S["epuf"], late["epuf"] = summarise(P.data_E[sex], P.thr, P.real)
        for name, th in models.items():
            E = NM.earnings(th, P.shocks[sex], sex, P.ages, P.q[sex], P.E, P.g[sex], P.logP)
            S[name], late[name] = summarise(E, P.thr, P.real)
        ax = axes[0, k]
        for i, (name, st) in enumerate(series):
            ax.bar(x + (i - 1) * 0.27, S[name]["share"], 0.27, color=st["color"], label=st["label"], alpha=0.9)
        ax.set_title(["Men", "Women"][k] + f", born {args.yob}", loc="left", fontsize=13)
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        ax.text(0.98, 0.55, "entering after 30:\n" + "\n".join(f"{st['label']} {late[n]:.0%}" for n, st in series),
                transform=ax.transAxes, ha="right", va="top", fontsize=8.5, color="#3d3d3d")
        ax = axes[1, k]
        for name, st in series:
            ax.plot(x, S[name]["mean"], color=st["color"], marker=st["marker"], ms=5, lw=2.2, label=st["label"])
        ax.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}k")
        ax.set_ylim(bottom=0)
        ax.set_xticks(x)
        ax.set_xticklabels([str(a) for a in AGES])
        for a in AGES:
            rows.append(dict(sex=sex, entry=a, **{f"share_{n}": S[n].share[a] for n, _ in series},
                             **{f"life_{n}": S[n]["mean"][a] for n, _ in series}))
    for ax in axes.flat:
        ax.spines[["top", "right"]].set_visible(False)
        ax.yaxis.grid(True, color="#dcdcdc")
        ax.set_axisbelow(True)
    axes[0, 0].set_ylabel("Share of people (any covered earnings at 20–65)")
    axes[1, 0].set_ylabel("Mean lifetime earnings 20–65, capped, 2013$")
    for ax in axes[1]:
        ax.set_xlabel("Age at the first year with covered earnings (20–65 window)")
    axes[0, 0].legend(frameon=False, fontsize=9, loc="upper right")
    axes[1, 1].legend(frameon=False, fontsize=9)
    fig.suptitle(f"Entry into covered work and lifetime earnings by entry age; model parameters from the "
                 f"{args.params_yob} cohort", x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(out + ".png", dpi=150)
    fig.savefig(out + ".pdf")
    pd.set_option("display.width", 200)
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    print("wrote", out + ".png")


if __name__ == "__main__":
    main()
