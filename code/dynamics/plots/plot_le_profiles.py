#!/usr/bin/env python
"""GKOS's own targeted moment, checked against EPUF: earnings by age within lifetime-earnings
groups.

Of the seven blocks of moments GKOS (2021) match, only ONE says anything about the level of
earnings by age -- their set 2, "average dollar earnings at 8 points over the life cycle for
different LE groups" (Appendix D.1).  Everything else is growth rates, impulse responses, a
within-cohort variance profile and an employment CDF.  So this is the moment to check our
fitted g(t) against: if the model misses here, it misses the one thing the process was asked
to get right about levels.

WHAT IS COMPUTED, identically on both sides:

  1. lifetime earnings LE = MEAN real earnings over ages 25-60, GKOS's own window, with
     nonemployment years entering as zeros (EPUF's `annual` is a sparse panel, so a missing
     person-year is a zero, not a gap);
  2. the p25 / p50 / p75 points of the LE distribution, each taken as a BAND of +/- 2
     percentiles so an average has people in it;
  3. mean earnings by age within each band -- again with zeros in, since "average dollar
     earnings" is what the target is.

ONE COHORT, chosen by coverage rather than by hand (`pick_cohort`).  A lifecycle profile needs
the whole lifecycle from one birth year: EPUF runs 1951-2006, so ages 25-60 are complete only
for yob 1926-1946 and ages 20-70 only for yob 1931-1936.  Requiring in addition that the
cohort's g(t) be DIRECTLY FITTED rather than extrapolated (`source == "fit"`, cohorts
1957-1983, i.e. yob 1932-1958) leaves yob 1932-1936, and the largest of those is picked.

THE TOP CODE IS THE REASON THIS NEEDS CARE.  EPUF earnings are capped at the taxable maximum,
which binds on 40%+ of men in the 1950s and 60s -- exactly the ages 25-35 of the cohort this
figure can use.  So a p75 lifetime-earnings profile built from EPUF is a profile of CAPPED
earnings, and the model must be capped the same way or the comparison is meaningless.  The
model therefore goes through EPUF's own disclosure protection year by year
(`epuf_disclosure.disclose`) BEFORE its lifetime earnings are computed and ranked, so both
sides rank people on the same censored measure and average the same censored dollars.

WHAT THAT LEAVES UNCOMPARABLE, and cannot be fixed here:
  * mortality and emigration.  EPUF has no death indicator, so a man who dies at 40 stays in
    the sample with 20 years of zeros and ranks low in LE; the model has no mortality at all.
    This pushes EPUF's low-LE profiles down relative to the model's.
  * attachment.  Both sides keep only people with at least one positive year in 25-60, which
    is the closest thing to GKOS's "some labour-market attachment" available in EPUF.
  * men only, because GKOS estimate on men and the process parameters are theirs.

THE p25 PROFILE FALLS IN EPUF BECAUSE OF NONEMPLOYMENT, NOT WAGES -- measured, not assumed
(cohort yob 1932, +/-2pt band).  EPUF's p25 group has 19% zero years at age 25, rising to 80%
by 60; earnings CONDITIONAL ON WORKING actually rise across the same span, $2.4k to $7.9k.  So
the average-dollar profile GKOS target collapses because low-lifetime earners increasingly
stop earning covered wages at all -- disability, incarceration, informal work, or death
manifesting as zero years, none of which EPUF flags directly -- not because their wages fall.
The model's own p25 zero-share moves the same direction but far less: 23% at 25, plateauing
near 44% by 45-60.  GKOS's nonemployment logit is a single 1978-2013 male estimate with no
channel for a specific subpopulation's exit becoming near-permanent, so it cannot reproduce
this -- and it is the reason the model's p25 line sits well ABOVE EPUF's after age 40, despite
both processes pointing the same direction.

Run from the project root:
    python code/dynamics/plots/plot_le_profiles.py [--yob YYYY] [--fits CSV] [--band 2]
Output: output/dynamics/plots/le_profiles.{pdf,png}
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

sys.path.insert(0, "code/dynamics")          # run from the project root, per repo convention
sys.path.insert(0, "code/cross_sections")
import gcohort_model as E
from epuf_disclosure import disclose, duck, epuf_codes_many
from guv_targets import BASE_YEAR, load_deflator

OUT = "output/dynamics/plots"
FITS = "output/dynamics/g_cohort_smm_p50_relevelled_extrapolated.csv"
LE_AGES = (25, 60)                            # GKOS's own lifetime-earnings window
PCTS = (25, 50, 75)
# Palette: slots 1-3 of the dataviz reference instance, in fixed order.  Identity here is the
# LE GROUP, so it takes the hues; the source (EPUF vs model) is a line style, because it is
# the same three groups measured two ways rather than six different things.
C_PCT = {25: "#2a78d6", 50: "#eb6834", 75: "#1baf7a"}
INK, INK_2, INK_3 = "#0b0b0b", "#52514e", "#8a8984"
GRID = "#e7e6e2"


def pick_cohort(fits):
    """The birth year with the most complete lifecycle in EPUF and a directly fitted g(t)."""
    span = duck("SELECT min(year) AS lo, max(year) AS hi FROM annual")
    lo, hi = int(span["lo"][0]), int(span["hi"][0])
    fitted = set(fits.loc[fits["source"] == "fit", "cohort"] - 25)
    n = duck("SELECT yob, count(*) AS n FROM demographic WHERE sex=1 GROUP BY 1").set_index("yob")
    best, best_key = None, None
    for yob in sorted(fitted):
        ages = [a for a in range(20, 71) if lo <= yob + a <= hi]
        if not set(range(LE_AGES[0], LE_AGES[1] + 1)) <= set(ages):
            continue                          # the LE window itself must be complete
        key = (len(ages), int(n["n"].get(yob, 0)))
        if best_key is None or key > best_key:
            best, best_key = yob, key
    if best is None:
        raise SystemExit("no cohort has a complete 25-60 window and a fitted g(t)")
    return best, best_key


def epuf_panel(yob, ages):
    """Real 2013-dollar earnings by (id, age) for one male cohort, zeros filled in.

    `annual` is sparse, so the zeros are created here rather than read: every man in
    `demographic` gets a row for every age in the window."""
    a0, a1 = ages
    q = (f"SELECT d.id, a.year - d.yob AS age, a.earnings FROM demographic d "
         f"LEFT JOIN annual a ON a.id = d.id AND a.year - d.yob BETWEEN {a0} AND {a1} "
         f"WHERE d.sex = 1 AND d.yob = {yob}")
    e = duck(q).dropna(subset=["age"])
    e["age"] = e["age"].astype(int)
    defl = load_deflator()
    e["real"] = e["earnings"].astype(float) * e["age"].map(lambda a: defl[yob + a])
    wide = e.pivot_table(index="id", columns="age", values="real", aggfunc="sum")
    ids = duck(f"SELECT id FROM demographic WHERE sex=1 AND yob={yob}")["id"]
    return wide.reindex(ids).reindex(columns=range(a0, a1 + 1)).fillna(0.0)


def model_panel(yob, ages, fits, n, rng):
    """The same panel from the model: one simulated man per row, EPUF's disclosure applied.

    g is read at the cohort's own fitted coefficients and enters as a level shift on log
    earnings, so the u panel is drawn once and shared across ages."""
    cohort = yob + 25
    row = fits[(fits["sex"] == "male") & (fits["cohort"] == cohort)]
    if row.empty:
        raise SystemExit(f"no fitted g for male cohort {cohort}")
    row = row.iloc[0]
    a0, a1 = ages
    span = np.arange(a0, a1 + 1)
    u = E.simulate_u(rng, n, E.SIM_AGES)
    g = E.g_at(row, span)
    defl = load_deflator()
    codes = epuf_codes_many([yob + a for a in span])   # three queries, not three per year
    out = np.zeros((n, span.size))
    for j, age in enumerate(span):
        year = yob + age
        x = np.exp(g[j] + u[:, E.sim_jj(age)])          # real 2013 $, zero where u = -inf
        nominal = x / defl[year]
        pos = nominal > 0
        rec = np.zeros(n)
        rec[pos] = disclose(nominal[pos], year, rng, codes[year]) * defl[year]
        out[:, j] = rec
    return pd.DataFrame(out, columns=span)


def le_profiles(panel, band):
    """Mean earnings by age for the +/- `band` percentile groups around p25, p50 and p75.

    Lifetime earnings rank people; the profile is then a plain mean within the band, zeros
    included, which is the quantity GKOS target.  Also returns the zero-share by age per band,
    the diagnostic that separates "earnings fell" from "people stopped earning"."""
    win = [c for c in panel.columns if LE_AGES[0] <= c <= LE_AGES[1]]
    le = panel[win].mean(axis=1)
    keep = (panel[win] > 0).any(axis=1)                 # some labour-market attachment
    le = le[keep]
    panel = panel.loc[keep]
    rank = le.rank(pct=True) * 100
    groups = {p: panel[(rank >= p - band) & (rank <= p + band)] for p in PCTS}
    return ({p: g.mean(axis=0) for p, g in groups.items()},
            {p: (g == 0).mean(axis=0) for p, g in groups.items()}, len(le))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--yob", type=int, help="override the coverage-based cohort choice")
    p.add_argument("--fits", default=FITS)
    p.add_argument("--band", type=float, default=2.0, help="half-width of each LE group, pct")
    p.add_argument("--n", type=int, default=200_000, help="simulated men")
    p.add_argument("--seed", type=int, default=5)
    p.add_argument("--tag", default="")
    a = p.parse_args()
    os.makedirs(OUT, exist_ok=True)

    fits = pd.read_csv(a.fits)
    yob = a.yob or pick_cohort(fits)[0]
    rng = np.random.default_rng(a.seed)

    ed = epuf_panel(yob, LE_AGES)
    md = model_panel(yob, LE_AGES, fits, a.n, rng)
    e_prof, e_zero, e_n = le_profiles(ed, a.band)
    m_prof, m_zero, m_n = le_profiles(md, a.band)
    lo, hi = LE_AGES
    for p in PCTS:
        print(f"p{p}: EPUF ${e_prof[p].mean():8,.0f}  model ${m_prof[p].mean():8,.0f}  "
              f"ratio {m_prof[p].mean() / e_prof[p].mean():.3f}   (mean over ages)")
        print(f"      zero share age {lo}->{(lo + hi) // 2}->{hi}:  "
              f"EPUF {e_zero[p][lo]:.0%}->{e_zero[p][(lo+hi)//2]:.0%}->{e_zero[p][hi]:.0%}   "
              f"model {m_zero[p][lo]:.0%}->{m_zero[p][(lo+hi)//2]:.0%}->{m_zero[p][hi]:.0%}")

    plt.rcParams.update({"font.family": "sans-serif", "text.color": INK,
                         "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
    fig, ax = plt.subplots(figsize=(8.2, 5.3))
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=GRID, lw=0.8, ls="-")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK_3, length=3, width=0.8, labelsize=9)

    for p in PCTS:
        ax.plot(e_prof[p].index, e_prof[p].to_numpy(), color=C_PCT[p], lw=2.0)
        ax.plot(m_prof[p].index, m_prof[p].to_numpy(), color=C_PCT[p], lw=2.0,
                ls=(0, (4, 2.5)))
    ax.set_xlabel("age", fontsize=9.5, color=INK_2)
    ax.set_ylabel(f"mean earnings, {BASE_YEAR} $", fontsize=9.5, color=INK_2)
    ax.yaxis.set_major_formatter(lambda v, _: f"${v/1000:,.0f}k")
    ax.set_xlim(LE_AGES[0], LE_AGES[1])
    ax.set_ylim(bottom=0)

    # Two encodings, two legend rows -- color carries the LE group (the identity that matters,
    # 3 series), line style carries the source (EPUF vs model, the same 3 series measured two
    # ways).  Splitting them is also what keeps a 5-entry legend from overflowing the figure
    # width and clipping its own first label (measured: one 5-item row did, at any reasonable
    # font size).
    id_handles = [Line2D([], [], color=C_PCT[p], lw=2.2, label=f"p{p} of lifetime earnings")
                  for p in PCTS]
    src_handles = [Line2D([], [], color=INK_3, lw=2.0, label="EPUF"),
                   Line2D([], [], color=INK_3, lw=2.0, ls=(0, (4, 2.5)), label="model")]
    leg1 = fig.legend(handles=id_handles, loc="lower center", bbox_to_anchor=(0.5, 0.085),
                      frameon=False, ncol=3, fontsize=9.5, handlelength=2.2,
                      columnspacing=1.8, labelcolor=INK_2)
    fig.add_artist(leg1)
    fig.legend(handles=src_handles, loc="lower center", bbox_to_anchor=(0.5, 0.01),
               frameon=False, ncol=2, fontsize=9.5, handlelength=2.2, columnspacing=1.8,
               labelcolor=INK_2)
    fig.subplots_adjust(left=0.105, right=0.975, top=0.965, bottom=0.235)
    stem = f"{OUT}/le_profiles{a.tag}"
    fig.savefig(f"{stem}.pdf"); fig.savefig(f"{stem}.png", dpi=200)
    print(f"cohort yob {yob} (GKSW cohort {yob + 25}); EPUF n = {e_n:,}, model n = {m_n:,}")
    print(f"wrote {stem}.pdf / .png")


if __name__ == "__main__":
    main()
