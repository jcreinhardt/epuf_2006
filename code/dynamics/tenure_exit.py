#!/usr/bin/env python
"""Attachment by PAST attachment: at ages 30 / 45 / 55, everybody in the cohort by how many years they were
CONTINUOUSLY employed coming into that age -- the length of the employment spell ending at a-1 (0 if not employed
at a-1, up to a-20 if employed every year from 20) -- and, for each value, the share employed at a. EPUF and the
models on the same base, both sexes. The input to the choice of a tenure term in the temporary-nonemployment logit
(what the logit at age a sees is exactly this history).

Rows carry the same columns as transition_rates.analyze (stat, h, sex, source, age, group, x, share, n):
stat 'tenure', h 1, group 'all', x = years continuously employed before a, share = employed at a; and 'tenure_lq',
the same within quartiles (q1..q4) of real earnings summed over 20..65 (the doc's lifetime-earnings quartiles).

Base, both sources: persons with positive earnings in at least one year of 20..65 (estimate_nonemp.Problem). The
models are NOT put through EPUF's disclosure (only employment status enters).

Run from the project root (needs processed_data/nonemp_inputs_yob<YOB>.npz, written by estimate_nonemp.py):
    python code/dynamics/tenure_exit.py [--yob 1937] [--specs absq_alpha ...] [--n-sim 100000]
Output: output/dynamics/tenure_exit_yob<YOB>.csv   (sources: epuf, gcohort, and every --specs model)
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import estimate_nonemp as EN  # noqa: E402
import transition_rates as TR  # noqa: E402

OUT_DEFAULT = EN.OUT_DEFAULT
AGES = TR.AGES_OUT


def tenure_before(emp, j):
    """Years continuously employed up to column j-1: 0 if not employed at j-1, else the length of the employed
    spell ending at j-1 (emp: (n, T) bool)."""
    L = np.zeros(emp.shape[0], int)
    unbroken = np.ones(emp.shape[0], bool)
    for i in range(j - 1, -1, -1):
        unbroken &= emp[:, i]
        L += unbroken
    return L


def tenure_rows(E, real, source, sex, rng):
    emp = E > 0
    qv = TR.bins((E / real).sum(1), 4, rng)
    rows = []
    for a in AGES:
        j = a - TR.A0
        L = tenure_before(emp, j)
        for x in range(0, j + 1):
            m = L == x
            if m.any():
                rows.append(("tenure", 1, sex, source, a, "all", float(x), emp[m, j].mean(), int(m.sum())))
            for k in range(4):
                mk = m & (qv == k)
                if mk.any():
                    rows.append(("tenure_lq", 1, sex, source, a, f"q{k + 1}", float(x), emp[mk, j].mean(),
                                 int(mk.sum())))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yob", type=int, default=1937)
    ap.add_argument("--specs", nargs="+", default=["absq_alpha"],
                    help="estimated specs to simulate (nonemp_params_yob<YOB>_<spec>.csv each)")
    ap.add_argument("--n-sim", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=20261006)
    ap.add_argument("--out", default=OUT_DEFAULT)
    args = ap.parse_args()

    P = EN.Problem("/nonexistent", args.yob, args.n_sim, args.seed, "auto")
    theta = {"gcohort": EN.expand(EN.GKOS[args.specs[0]], args.specs[0])}
    for spec in args.specs:
        est = pd.read_csv(os.path.join(args.out, f"nonemp_params_yob{args.yob}_{spec}.csv")).set_index("parameter")
        theta[spec] = EN.expand([est.estimate[k] for k in EN.SPECS[spec]], spec)
    rows = []
    rng = np.random.default_rng(args.seed)
    for sex in (1, 2):
        rows += tenure_rows(P.data_E[sex], P.real, "epuf", sex, rng)
        for src, th in theta.items():
            rows += tenure_rows(P.sim_E(th, sex), P.real, src, sex, rng)
        print(f"sex {sex}: EPUF n = {P.data_E[sex].shape[0]:,}", flush=True)
    d = pd.DataFrame(rows, columns=["stat", "h", "sex", "source", "age", "group", "x", "share", "n"])
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"tenure_exit_yob{args.yob}.csv")
    d.to_csv(path, index=False, float_format="%.6g")
    print("wrote", path)
    for sex in (1, 2):
        print(f"\nsex {sex}: share employed at a by years continuously employed before a (EPUF n in last columns)")
        u = d[(d.stat == "tenure") & (d.sex == sex) & (d.x <= 12)]
        t = u.pivot_table(index="x", columns=["age", "source"], values="share")
        n = u[u.source == "epuf"].pivot_table(index="x", columns="age", values="n")
        t.columns = [f"{a}_{s[:5]}" for a, s in t.columns]
        for a in AGES:
            t[f"n{a}"] = n[a].fillna(0).astype(int)
        print(t.round(3).to_string())


if __name__ == "__main__":
    main()
