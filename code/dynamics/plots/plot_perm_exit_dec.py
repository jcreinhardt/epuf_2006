#!/usr/bin/env python
"""Permanent exits by age, EPUF against a model whose exits are split by what keeps the person out.

A permanent exit at a: employed at a-1, never employed again through 65 (base: everybody with any covered year at
20-65, as in transition_rates.py). The model's exits are decomposed into three causes, which overlap, so the split is
ORDERED:
  nu  temporary-nonemployment draws alone keep the person out (nu = 1 in every remaining year along the realised path);
  D   death, not already covered by nu;
  A   the absorbing exit state (nonemp_model.py), not covered by nu or D.
The three parts sum to the model's total. Models without an absorbing state (sexint, sexlag_add, sexlag) have A = 0.

The model is simulated through nonemp_model.py with estimate_nonemp.py's draws, so the GKOS line here is GKOS +
mortality on those draws (same process as transition_rates.model_matrix, different random numbers).

Run from the project root:
    python code/dynamics/plots/plot_perm_exit_dec.py --model {gkos,sexint,sexlag_add,sexlag,sexlag_abs,sexlag_absq,sexlag_abs55,absq_alpha,absq_zcap,nonemp} [--yob 1932]
Output: output/dynamics/plots/transition_perm_exit_dec_yob<YOB>{,_<model>}.{png,pdf}
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

DARK, GRID = "#3d3d3d", "#dcdcdc"
A0, A1 = TR.A0, TR.A1
MODEL = {"gkos": ("GKOS model", None),
         "sexint": ("GKOS + sex-specific intercept", "nonemp_params_yob{yob}_sexint.csv"),
         "sexlag_add": ("GKOS + sex + last-year-status intercept", "nonemp_params_yob{yob}_sexlag_add.csv"),
         "sexlag": ("GKOS + sex x last-year-status intercept", "nonemp_params_yob{yob}_sexlag.csv"),
         "sexlag_abs": ("Modified GKOS, linear exit", "nonemp_params_yob{yob}_sexlag_abs.csv"),
         "sexlag_absq": ("Modified GKOS, no alpha term", "nonemp_params_yob{yob}_sexlag_absq.csv"),
         "sexlag_abs55": ("Modified GKOS, exit kink at 55", "nonemp_params_yob{yob}_sexlag_abs55.csv"),
         "absq_alpha": ("Modified GKOS", "nonemp_params_yob{yob}_absq_alpha.csv"),
         "absq_zcap": ("Modified GKOS + cap on z", "nonemp_params_yob{yob}_absq_zcap.csv"),
         "nonemp": ("New nonemployment model", "nonemp_params_yob{yob}_ms_persist.csv")}
EPUF_COL = "#8a8a8a"                       # plot_transition_rates.STYLE: EPUF grey, each model in its own hue
PART = {"nu": "repeated temporary draws (ν), counted first",
        "D": "death (D), not covered by ν",
        "A": "absorbing exit (A), not covered by ν or D"}
SHADES = {"gkos": {"nu": "#f6b88f", "D": "#D55E00"},
          "sexint": {"nu": "#9fdcc6", "D": "#009E73"},
          "sexlag_add": {"nu": "#ecc2db", "D": "#CC79A7"},
          "sexlag": {"nu": "#a6cde8", "D": "#0072B2"},
          "sexlag_abs": {"nu": "#cfe9f8", "D": "#56B4E9", "A": "#1f6f99"},
          "sexlag_absq": {"nu": "#cfe9f8", "D": "#56B4E9", "A": "#1f6f99"},
          "sexlag_abs55": {"nu": "#cfe9f8", "D": "#56B4E9", "A": "#1f6f99"},
          "absq_alpha": {"nu": "#cfe9f8", "D": "#56B4E9", "A": "#1f6f99"},
          "absq_zcap": {"nu": "#cfe9f8", "D": "#56B4E9", "A": "#1f6f99"},
          "nonemp": {"nu": "#c6dbef", "D": "#6baed6", "A": "#0072B2"}}


def theta(model, yob):
    if model == "gkos":
        return EN.expand([-3.353, -3.353], "sexint")
    est = pd.read_csv(os.path.join(PROJ, "output", "dynamics", MODEL[model][1].format(yob=yob))).estimate
    return EN.expand(est.to_numpy(), "full" if model == "nonemp" else model)


def last_emp(w):
    return A0 + (w.shape[1] - 1 - np.argmax(w[:, ::-1], 1))


def model_parts(P, th, sex, ages):
    p = dict(zip(NM.NAMES, th))
    s = "m" if sex == 1 else "f"
    sh, q, E = P.shocks[sex], P.q[sex], P.E
    emp = NM.employment(th, sh, sex, P.ages, q, E)
    n, _ = emp.shape
    dies = sh["u_mort"] < q[None, :]
    dead = np.cumsum(np.concatenate([np.zeros((n, 1), bool), dies[:, :-1]], 1), 1) > 0   # zero from the year after
    t = (P.ages - 24.0) / 10
    one = dict(pi=p[f"pi_{s}"], a_E=p[f"a_{s}_E"])
    prev = np.concatenate([~(sh["u_init"] < NM.p_init(one, sh["z"], E.NU_B, E.NU_C, E.NU_D))[:, None], emp[:, :-1]], 1)
    nu = sh["u_nu"] < NM.logistic(np.where(prev, p[f"a_{s}_E"], p[f"a_{s}_N"]) + E.NU_B * t
                                  + (E.NU_C + E.NU_D * t) * sh["z"])
    keep = emp.any(1)
    emp, dead, nu = emp[keep], dead[keep], nu[keep]
    last = last_emp(emp)
    first_dead = np.where(dead.any(1), A0 + np.argmax(dead, 1), 99)
    exited = last < A1
    nu_rest = np.array([ex and nu[i, l - A0 + 1:].all() for i, (l, ex) in enumerate(zip(last, exited))])
    cause = np.where(~exited, "none", np.where(nu_rest, "nu", np.where(first_dead <= A1, "D", "A")))
    return {c: np.array([((last == a - 1) & (cause == c)).mean() for a in ages]) for c in PART}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gkos", choices=tuple(MODEL))
    ap.add_argument("--yob", type=int, default=1932)
    ap.add_argument("--n-sim", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=20261006)
    ap.add_argument("--root", default=TR.ROOT_DEFAULT)
    args = ap.parse_args()
    out = os.path.join(PROJ, "output", "dynamics", "plots",
                       f"transition_perm_exit_dec_yob{args.yob}" + ("" if args.model == "gkos" else f"_{args.model}"))
    P = EN.Problem(args.root, args.yob, args.n_sim, args.seed)          # reads or builds the input cache
    th = theta(args.model, args.yob)
    ages = np.arange(A0 + 1, A1 + 1)

    fig, axes = plt.subplots(2, 2, figsize=(11, 8.2), sharex=True)
    rows = []
    for k, sex in enumerate((1, 2)):
        parts = model_parts(P, th, sex, ages)
        show = [c for c in PART if parts[c].sum() > 0]
        last = last_emp(P.data_E[sex] > 0)
        d = np.array([(last == a - 1).mean() for a in ages])
        for i, cum in enumerate((False, True)):
            ax = axes[i, k]
            ax.stackplot(ages, *[np.cumsum(parts[c]) if cum else parts[c] for c in show],
                         colors=[SHADES[args.model][c] for c in show], labels=[f"Model: {PART[c]}" for c in show],
                         alpha=0.9)
            ax.plot(ages, np.cumsum(d) if cum else d, color=EPUF_COL, marker="o", ms=4, lw=2.4, label="EPUF")
        for c in show:
            rows.append(dict(sex=sex, part=c, **{f"by{b}": parts[c][ages <= b].sum() for b in (45, 55, 62, 65)}))
        rows.append(dict(sex=sex, part="model total",
                         **{f"by{b}": sum(parts[c][ages <= b].sum() for c in PART) for b in (45, 55, 62, 65)}))
        rows.append(dict(sex=sex, part="EPUF", **{f"by{b}": d[ages <= b].sum() for b in (45, 55, 62, 65)}))
        axes[0, k].set_title(["Men", "Women"][k] + f", born {args.yob}", loc="left", fontsize=13)
    for ax in axes.flat:
        ax.spines[["top", "right"]].set_visible(False)
        ax.yaxis.grid(True, color=GRID)
        ax.set_axisbelow(True)
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        ax.set_ylim(bottom=0)
        ax.set_xlim(A0 + 1, A1)
    for ax in axes[1]:
        ax.set_xlabel("Age a (last covered year is a-1, none afterwards through 65)")
        ax.set_ylim(0, 1)
    axes[0, 0].set_ylabel("Share of people exiting for good at a")
    axes[1, 0].set_ylabel("Cumulative share exited for good")
    axes[0, 0].legend(frameon=False, fontsize=9.5, loc="upper left")
    order = "ν, then D" if args.model in ("gkos", "sexint", "sexlag_add", "sexlag") else "ν, then D, then A"
    fig.suptitle(f"Permanent exits: EPUF vs {MODEL[args.model][0]}, split by what keeps the person out "
                 f"(ordered: {order})", x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(out + ".png", dpi=150)
    fig.savefig(out + ".pdf")
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    print("wrote", out + ".png")


if __name__ == "__main__":
    main()
