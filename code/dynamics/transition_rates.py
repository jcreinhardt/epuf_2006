#!/usr/bin/env python
"""Employment DYNAMICS of one birth cohort, EPUF against the earnings model: who stops working, who comes back.

Six statistics, each at ages 30 / 45 / 55 and horizons h = 1 and 5 years, by sex. All are the share NOT employed
(zero covered earnings) at a+h:

  exit     everybody at age a: the not employed (x=0) and the earners at the taxable max (x=1) are separate points
           (bunched masses); the rest are 20 equal-count bins of current-earnings rank (random tie-break, since
           EPUF is random-rounded)
  persist  the not employed at a, on one line of CUMULATIVE real (2013$) earnings 20..a-1 (never worked at the bottom)
  lifetime share of ages 20..65 not employed, against real earnings 20..65 (one line)
  cumrank  everybody at a, one line of cumulative real earnings 20..a, NOT conditioned on employment
  chg_arc  everybody not at zero in BOTH a-h and a and not at the taxable max in EITHER, by the arc-percent change a-h -> a, (y1-y0)/((y1+y0)/2) in
           [-2, 2]; exactly -2 (employed -> out) and +2 (out -> employed) are bins of their own
  chg_abs  the same people by the change in real 2013$, a centre bin |d| < $250 and 12 geometric bins per side
           (ratio 1.7), x = signed bin midpoint; meant for a symlog axis

Plus three that are not transitions:
  fwd      everybody at a, one line of cumulative real earnings 20..a; y = share of the remaining ages a+1..65 not
           employed
  byage_lq share not employed at each age 20..65, by quartile (q1..q4) of real earnings summed over 20..65
  agg      share of all person-years 20..65 not employed
  yrs_hist distribution of the number of years 20..65 with positive earnings (1..46)
  evt_age / evt_next  large interior one-year changes (arc in (-2,-1] "drop", [1,2) "rise") by age: incidence per
           person in the base, and the share EMPLOYED the year after
  evt_next5 / evt_none5  the same events at a <= 60: share of the years a+1..a+5 employed / share employed in none
  trans_fut_lq  mean number of future status switches (entries + exits) between a and 65, by age a and
           lifetime-earnings quartile
  fwd_dec  share of ages a+1..60 not employed by cumulative-earnings rank at a, split into people who never work
           again by 60 ('exit') or work again at least one of those years ('again'); the parts sum to 'total'
  evt_base share of the base in the one-year change sample at a (denominator for tail masses)
  trans_cum / trans_cur / trans_life  counts of entries (0->1) and exits (1->0): over a..65 by cumulative-earnings
           rank or by current earnings at a (zero / line / cap), and over 20..65 by lifetime-earnings rank

MORTALITY (model only; EPUF has it built in): uniform, i.e. not related to earnings, from age 20, q(x) read
diagonally off the TR2023 historical period life tables (q at age x from the year yob+x table). The dead have zero
earnings from the year after death on. `--no-mortality` turns it off (output suffix `_nomort`).

"Employed" = positive covered earnings.

SAME CODE FOR BOTH SOURCES (`analyze`): the model is `run_microsim.simulate_cell` (re-estimated g(t), no
coverage layer, no mortality), EPUF is the `annual` table zero-filled. "At the taxable max" is `earn >= thr(year)`,
thr = EPUF's near-cap collapse value if the year has one, else the cap (`epuf_disclosure`), applied to both.

BASE (both sources, as in `employment_by_age.py`): persons with positive earnings in at least one year of ages
20..65. EPUF has no never-covered people and no deaths; the model has neither. Consequences: the persistence of the
"never employed so far" point is pushed up by construction (they must work later), and EPUF's dying people look
like permanent exits while the model's never leave.

Run from anywhere; the data/model inputs live under --root (default: the earnings-microsimulation worktree, where
`run_microsim.py` and its g(t) CSVs are; they are not on this branch):
    python code/dynamics/transition_rates.py [--yob 1932] [--n-sim 20000]
Output: output/dynamics/transition_rates_yob<YOB>.csv
        (stat, h, sex, source, age, group, x, share, n)
"""
import argparse
import contextlib
import io
import os
import subprocess
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "output", "dynamics")
ROOT_DEFAULT = os.path.join(os.path.expanduser("~/PhD/projects/epuf_2006"), ".claude", "worktrees",
                            "earnings-microsimulation-87c389")
A0, A1 = 20, 65
AGES_OUT = (30, 45, 55)
HORIZONS = (1, 5)
NBIN = 20


def threshold(years):
    """year -> nominal amount at or above which an EPUF value is 'at the taxable maximum'."""
    import epuf_disclosure as ED
    codes = ED.epuf_codes_many(list(years))
    return np.array([codes[y][2] if codes[y][2] is not None else codes[y][0] for y in years])


def epuf_matrix(yob):
    """(sex[n], nominal earnings[n, ages A0..A1]) zero-filled, for persons with any positive year in the window."""
    q = f"""COPY (SELECT d.id, d.sex, a.year - d.yob AS age, a.earnings FROM annual a JOIN demographic d USING (id)
          WHERE d.yob = {yob} AND d.sex IN (1, 2) AND a.earnings > 0 AND a.year - d.yob BETWEEN {A0} AND {A1})
          TO '/dev/stdout' (FORMAT CSV, HEADER TRUE);"""
    d = pd.read_csv(io.StringIO(subprocess.run(["duckdb", "-readonly", "processed_data/ssa.duckdb", "-c", q],
                                               capture_output=True, text=True, check=True).stdout))
    w = d.pivot_table(index="id", columns="age", values="earnings", aggfunc="sum").reindex(
        columns=range(A0, A1 + 1)).fillna(0.0)
    sex = d.groupby("id").sex.first().loc[w.index].to_numpy()
    return sex, w.to_numpy()


def cohort_qx(yob, sex):
    """q(x), ages A0..A1, for one birth cohort, read diagonally off the TR2023 historical PERIOD life tables
    (Social Security area): q at age x is the year yob+x table's."""
    f = f"raw_data/demographics/PerLifeTables_{'M' if sex == 1 else 'F'}_Hist_TR2023.csv"
    t = pd.read_csv(f, skiprows=4, usecols=[0, 1, 2], names=["year", "x", "q"], header=None,
                    dtype=str).dropna()
    t = t[t.year.str.strip().str.isdigit()].astype({"year": int, "x": int, "q": float})
    q = t.set_index(["year", "x"]).q
    return np.array([q[(yob + x, x)] for x in range(A0, A1 + 1)])


def model_matrix(RM, yob, sex, n_sim, seed, mortality=True):
    rng = np.random.default_rng([seed, yob, sex])
    ages, earn = RM.simulate_cell(yob, sex, "gcohort", n_sim, rng, yob + A1 + 1, "none")
    assert list(ages) == list(range(A0, A1 + 1))
    if mortality:
        # uniform (not earnings-related) mortality, alive at A0: someone dying at age x keeps that year's earnings
        # and has zero from x+1 on, as EPUF records a dead person
        q = cohort_qx(yob, sex)
        dies = rng.random(earn.shape) < q[None, :]
        alive = np.cumsum(np.concatenate([np.zeros((earn.shape[0], 1)), dies[:, :-1]], 1), 1) == 0
        earn = earn * alive
    return earn[(earn > 0).any(1)]


def bins(score, nbin, rng):
    """Equal-count bin index and mean rank in (0,1) of each bin; random tie-break."""
    order = np.lexsort((rng.random(score.size), score))
    r = np.empty(score.size)
    r[order] = (np.arange(score.size) + 0.5) / score.size
    b = np.minimum((r * nbin).astype(int), nbin - 1)
    return b


def analyze(E, thr, real, source, sex, rng, base_rule="window"):
    rows = []
    E_all = E
    for a in AGES_OUT:
        j = a - A0
        # 'window': ever positive in 20..65 (looks FORWARD past a); 'past': ever positive in 20..a (no look-ahead)
        E = E_all if base_rule == "window" else E_all[E_all[:, :j + 1].any(1)]
        e = E[:, j]
        base = e == 0
        cum_all = (E[:, :j] / real[:j]).sum(1)         # real (2013$) earnings 20..a-1
        for h in HORIZONS:
            out = E[:, j + h] > 0
            # exit: everybody at a. x=0 = not employed, x=1 = at the taxable max (both are bunched masses and are
            # separate groups); the line is the rest, ranked by current earnings
            capped = e >= thr[j]
            zero = e == 0
            mid = ~zero & ~capped
            for g, m, x in (("zero", zero, 0.0), ("cap", capped, 1.0)):
                rows.append(("exit", h, sex, source, a, g, x, 1 - out[m].mean() if m.any() else np.nan, int(m.sum())))
            b = bins(e[mid], NBIN, rng)
            for k in range(NBIN):
                m = b == k
                rows.append(("exit", h, sex, source, a, "line", (k + 0.5) / NBIN, 1 - out[mid][m].mean(), int(m.sum())))
            # persist: the not employed at a, one rank line in cumulative real earnings (never worked at the bottom)
            b2 = bins(cum_all[base], NBIN, rng)
            o2 = out[base]
            for k in range(NBIN):
                m = b2 == k
                rows.append(("persist", h, sex, source, a, "line", (k + 0.5) / NBIN, 1 - o2[m].mean(), int(m.sum())))
            # cumrank: EVERYBODY at a on one line of cumulative real earnings 20..a (not conditioned on employment)
            b3 = bins(cum_all + e / real[j], NBIN, rng)
            for k in range(NBIN):
                m = b3 == k
                rows.append(("cumrank", h, sex, source, a, "line", (k + 0.5) / NBIN, 1 - out[m].mean(), int(m.sum())))
            rows += change_rows(E, thr, real, a, h, source, sex)
        # fwd: everybody at a, one line of cumulative real earnings 20..a; y = share of the REMAINING ages a+1..65
        # not employed
        b4 = bins(cum_all + e / real[j], NBIN, rng)
        rest = (E[:, j + 1:] <= 0).mean(1)
        for k in range(NBIN):
            m = b4 == k
            rows.append(("fwd", 0, sex, source, a, "line", (k + 0.5) / NBIN, rest[m].mean(), int(m.sum())))
        rows += fwd_decomp_rows(E, real, a, source, sex, rng)
    rows += lifetime_rows(E_all, real, source, sex, rng)
    rows += quartile_rows(E_all, real, source, sex, rng)
    rows += event_rows(E_all, thr, real, source, sex)
    rows += transition_rows(E_all, thr, real, source, sex, rng)
    ne = E_all <= 0
    rows.append(("agg", 0, sex, source, A1, "all", np.nan, ne.mean(), int(ne.shape[0])))
    yrs = (~ne).sum(1)                                   # years with positive earnings, 20..65
    rows += [("yrs_hist", 0, sex, source, A1, "all", float(y), (yrs == y).mean(), int((yrs == y).sum()))
             for y in range(1, ne.shape[1] + 1)]
    return rows


def event_rows(E, thr, real, source, sex):
    """Large interior one-year changes a-1 -> a, by the age a at which they happen (same sample rule as chg_arc:
    nobody at the taxable max in either year).
      drop: arc in (-2, -1]   rise: arc in [1, 2)
    evt_age:  share = events at a / persons in the base, n = events
    evt_next: share = EMPLOYED at a+1 among the events at a, n = events"""
    rows = []
    for a in range(A0 + 1, A1):
        j = a - A0
        y0, y1 = E[:, j - 1] / real[j - 1], E[:, j] / real[j]
        ok = ((y0 > 0) | (y1 > 0)) & (E[:, j - 1] < thr[j - 1]) & (E[:, j] < thr[j])
        arc = np.where(ok, (y1 - y0) / np.maximum((y1 + y0) / 2, 1e-12), np.nan)
        nxt = E[:, j + 1] > 0
        rows.append(("evt_base", 0, sex, source, a, "sample", float(a), ok.mean(), int(ok.sum())))
        for g, m in (("drop", (arc > -2 + 1e-9) & (arc <= -1)), ("rise", (arc >= 1) & (arc < 2 - 1e-9))):
            rows.append(("evt_age", 0, sex, source, a, g, float(a), m.mean(), int(m.sum())))
            rows.append(("evt_next", 1, sex, source, a, g, float(a), nxt[m].mean() if m.any() else np.nan,
                         int(m.sum())))
            if a + 5 <= A1 and m.any():                      # all five following years observed
                emp5 = E[m][:, j + 1:j + 6] > 0
                rows.append(("evt_next5", 5, sex, source, a, g, float(a), emp5.mean(), int(m.sum())))
                rows.append(("evt_none5", 5, sex, source, a, g, float(a), (~emp5.any(1)).mean(), int(m.sum())))
    return rows


def transitions(E, j0, j1):
    """Per person: (# entries 0->1, # exits 1->0) between consecutive ages j0..j1 (column indices)."""
    w = E[:, j0:j1 + 1] > 0
    return (~w[:, :-1] & w[:, 1:]).sum(1), (w[:, :-1] & ~w[:, 1:]).sum(1)


def transition_rows(E, thr, real, source, sex, rng):
    """Counts of labour-market entries / exits.
      trans_cum  ages a..65, by rank in cumulative real earnings 20..a           (one line)
      trans_cur  ages a..65, by current earnings at a: zero / line / cap         (exit-plot layout)
      trans_life ages 20..65, by rank in real earnings summed over 20..65        (one line)
    share = mean count per person; group = '<entries|exits>:<zero|line|cap>'."""
    rows = []
    for a in AGES_OUT:
        j = a - A0
        ent, ext = transitions(E, j, E.shape[1] - 1)
        e = E[:, j]
        b = bins((E[:, :j + 1] / real[:j + 1]).sum(1), NBIN, rng)
        zero, capped = e == 0, e >= thr[j]
        mid = ~zero & ~capped
        bm = bins(e[mid], NBIN, rng)
        for kind, c in (("entries", ent), ("exits", ext)):
            for k in range(NBIN):
                rows.append(("trans_cum", 0, sex, source, a, f"{kind}:line", (k + 0.5) / NBIN, c[b == k].mean(),
                             int((b == k).sum())))
                rows.append(("trans_cur", 0, sex, source, a, f"{kind}:line", (k + 0.5) / NBIN, c[mid][bm == k].mean(),
                             int((bm == k).sum())))
            for g, m, x in (("zero", zero, 0.0), ("cap", capped, 1.0)):
                rows.append(("trans_cur", 0, sex, source, a, f"{kind}:{g}", x, c[m].mean() if m.any() else np.nan,
                             int(m.sum())))
    ent, ext = transitions(E, 0, E.shape[1] - 1)
    b = bins((E / real).sum(1), NBIN, rng)
    for kind, c in (("entries", ent), ("exits", ext)):
        for k in range(NBIN):
            rows.append(("trans_life", 0, sex, source, A1, f"{kind}:line", (k + 0.5) / NBIN, c[b == k].mean(),
                         int((b == k).sum())))
    return rows


def quartile_rows(E, real, source, sex, rng):
    """Share not employed at each age 20..65, separately by quartile of lifetime real earnings 20..65."""
    q = bins((E / real).sum(1), 4, rng)
    ne = E <= 0
    rows = [("byage_lq", 0, sex, source, A0 + j, f"q{k + 1}", float(A0 + j), ne[q == k, j].mean(), int((q == k).sum()))
            for k in range(4) for j in range(E.shape[1])]
    # trans_fut_lq: mean number of FUTURE status switches (entries + exits) between a and 65, at each age a 20..64
    sw = (ne[:, 1:] != ne[:, :-1]).astype(int)          # column j: switch between ages A0+j and A0+j+1
    fut = sw[:, ::-1].cumsum(1)[:, ::-1]
    rows += [("trans_fut_lq", 0, sex, source, A0 + j, f"q{k + 1}", float(A0 + j), fut[q == k, j].mean(),
              int((q == k).sum())) for k in range(4) for j in range(sw.shape[1])]
    return rows


FWD_END = 60


def fwd_decomp_rows(E, real, a, source, sex, rng):
    """Share of the remaining ages a+1..FWD_END not employed, by cumulative-earnings rank at a, split by how much the
    person works again over a+1..FWD_END: 'exit' never, 'again' at least one year. Each part is
    (non-employed years of that group) / (all people x all remaining years), so the two sum to 'total'."""
    j, j1 = a - A0, FWD_END - A0
    b = bins((E[:, :j + 1] / real[:j + 1]).sum(1), NBIN, rng)
    emp = E[:, j + 1:j1 + 1] > 0
    yrs = emp.sum(1)
    ne_share = 1 - emp.mean(1)
    grp = {"exit": yrs == 0, "again": yrs >= 1}
    rows = []
    for k in range(NBIN):
        m = b == k
        rows.append(("fwd_dec", 0, sex, source, a, "total", (k + 0.5) / NBIN, ne_share[m].mean(), int(m.sum())))
        for g, gm in grp.items():
            rows.append(("fwd_dec", 0, sex, source, a, g, (k + 0.5) / NBIN, (ne_share * gm)[m].mean(), int(m.sum())))
    return rows


def lifetime_rows(E, real, source, sex, rng):
    """Share of ages 20..65 NOT employed, against lifetime real earnings 20..65 (one line, 20 equal-count bins)."""
    cum = (E / real).sum(1)
    nonemp = (E <= 0).mean(1)
    b = bins(cum, NBIN, rng)
    return [("lifetime", 0, sex, source, A1, "line", (k + 0.5) / NBIN, nonemp[b == k].mean(), int((b == k).sum()))
            for k in range(NBIN)]


ARC_W = 0.2
ABS_LO, ABS_STEP, ABS_NB = 250.0, 1.7, 12


def change_rows(E, thr, real, a, h, source, sex):
    """Not employed at a+h against the income change a-h -> a (everyone not at zero in BOTH years).

    chg_arc: arc-percent, (y1-y0)/((y1+y0)/2) in [-2, 2]; exactly -2 (employed -> out) and +2 (out -> employed) are
             their own bins, the interior is 20 bins of width 0.2.
    chg_abs: y1-y0 in real 2013$; a centre bin |d| < ABS_LO, then ABS_NB geometric bins per side (ratio ABS_STEP);
             x is the signed bin midpoint (0 for the centre bin). Plotted on a symlog axis.
    """
    j = a - A0
    y0, y1 = E[:, j - h] / real[j - h], E[:, j] / real[j]
    capped = (E[:, j - h] >= thr[j - h]) | (E[:, j] >= thr[j])      # at the taxable max in EITHER year: dropped
    keep = ((y0 > 0) | (y1 > 0)) & ~capped
    out = (E[:, j + h] <= 0)[keep]
    y0, y1 = y0[keep], y1[keep]
    arc = (y1 - y0) / ((y1 + y0) / 2)
    ib = np.clip(np.floor((arc + 2) / ARC_W + 1e-9).astype(int), 0, int(round(4 / ARC_W)) - 1)
    ib = np.where(arc <= -2 + 1e-9, -1, np.where(arc >= 2 - 1e-9, int(round(4 / ARC_W)), ib))
    rows = []
    for k in range(-1, int(round(4 / ARC_W)) + 1):
        m = ib == k
        x = -2.0 if k == -1 else 2.0 if k == int(round(4 / ARC_W)) else -2 + (k + 0.5) * ARC_W
        if m.any():
            g = "out" if k == -1 else "in" if k == int(round(4 / ARC_W)) else "line"
            rows.append(("chg_arc", h, sex, source, a, g, x, out[m].mean(), int(m.sum())))
    d = y1 - y0
    edges = ABS_LO * ABS_STEP ** np.arange(ABS_NB + 1)
    mag = np.abs(d)
    kb = np.where(mag < ABS_LO, -1, np.minimum(np.searchsorted(edges, mag, side="right") - 1, ABS_NB - 1))
    for sgn in (-1, 0, 1):
        for k in range(-1, ABS_NB):
            if (sgn == 0) != (k == -1):
                continue
            m = (kb == k) & ((np.sign(d) == sgn) if sgn else True)
            if m.any():
                x = 0.0 if k == -1 else sgn * np.sqrt(edges[k] * edges[k + 1])
                rows.append(("chg_abs", h, sex, source, a, "line", x, out[m].mean(), int(m.sum())))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yob", type=int, default=1932)
    ap.add_argument("--n-sim", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=20261006)
    ap.add_argument("--base", choices=("window", "past"), default="window",
                    help="who is in the base: ever positive in 20..65 (default) or ever positive in 20..a")
    ap.add_argument("--no-mortality", action="store_true",
                    help="model without deaths (default: uniform TR2023 cohort mortality from age 20)")
    ap.add_argument("--root", default=ROOT_DEFAULT, help="checkout holding processed_data/ and run_microsim.py")
    ap.add_argument("--out", default=OUT_DEFAULT)
    args = ap.parse_args()

    sys.path.insert(0, HERE)
    sys.path.insert(0, os.path.join(args.root, "code", "benefits"))
    os.chdir(args.root)                                   # every loader below reads root-relative paths
    with contextlib.redirect_stdout(io.StringIO()):
        import run_microsim as RM
        price = RM.RA._get_gcohort_inputs()[1]
    years = list(range(args.yob + A0, args.yob + A1 + 1))
    thr = threshold(years)
    real = np.array([price[y] for y in years])           # nominal $ per 2013 $

    rng = np.random.default_rng(args.seed)
    rows = []
    sex_e, E_e = epuf_matrix(args.yob)
    for sex in (1, 2):
        rows += analyze(E_e[sex_e == sex], thr, real, "epuf", sex, rng, args.base)
        rows += analyze(model_matrix(RM, args.yob, sex, args.n_sim, args.seed, not args.no_mortality), thr, real,
                        "gcohort", sex, rng, args.base)
    d = pd.DataFrame(rows, columns=["stat", "h", "sex", "source", "age", "group", "x", "share", "n"])
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"transition_rates_yob{args.yob}" + ("" if args.base == "window" else "_basepast")
                        + ("_nomort" if args.no_mortality else "") + ".csv")
    d.to_csv(path, index=False, float_format="%.5f")
    print("wrote", path)
    print(d.groupby(["stat", "source"]).n.sum().unstack())


if __name__ == "__main__":
    main()
