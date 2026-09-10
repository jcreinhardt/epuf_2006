#!/usr/bin/env python
"""EPUF's actual cross-section of earnings against the one CMS's process implies.

The dynamics section fits g(t) to published cohort x age MOMENTS.  This figure closes the loop
on the underlying DISTRIBUTION: it takes CMS's (JF 2025) income process exactly as they coded
it, forms the year-Y cross-section it implies, and lays it beside the EPUF microdata for that
same year -- same screen, same deflator, same age composition.

TWO FIGURES, one machine.  Default (--eras) is the diagnostic: log(model / EPUF) across the
percentiles, one panel per era and one line per age group, with a second row that nets each
line at its own median so the LEVEL error and the SHAPE error are separated.  --year Y instead
draws that single year in full -- both quantile functions in dollars, the model also shown
top-coded, and GKSW's published quantiles as a third series, which splits the gap into the
part that is a data difference and the part that is the process.

HOW THE MODEL CROSS-SECTION IS BUILT.  A cross-section mixes cohorts: at age a in year Y the
worker belongs to cohort c = Y - a + 25 (GKSW's convention, the year at age 25), so each age
draws its deterministic profile from a DIFFERENT one of CMS's cubics.  Three facts make this
cheap, safe, and comparable:

  * g enters the level multiplicatively and nothing downstream feeds back on it (the
    unemployment logit reads z, not earnings), so ONE simulated panel of the g-free part
    u = works * exp(hip + z + e - jensen) * (1-unemp)/(1-mean unemp) serves every cohort, and
    the cohort only multiplies it by exp(g_c(a)).
  * every evaluation point is IN-SAMPLE for its cubic.  Cohort c is evaluated at age a, i.e.
    at year Y, and the cubic was fitted on GKSW data covering that year.  So none of the wild
    late-cohort cubics (c_2007 has cons = -42.7, fitted on ~7 ages) is ever extrapolated here.
  * CMS's file starts at cohort 1949, so an early year has no profile for its OLD ages -- 1960
    reaches only age 36.  usable_ages cuts EPUF, the weights and the GKSW series to the same
    range, so an age-composition difference is never read as a distributional one.

UNITS.  CMS's profile is log(earnings / SSA average wage), earnings in thousands of 2013
dollars (create_lifecycle_income_parameters.do), so model dollars = ratio x ssa(Y) x 1000 with
ssa their own gksw2017.xlsx series.  In a cross-section every cell shares the year, so that is
one scalar for the whole figure.  EPUF is nominal and is deflated with GKSW's own PCE vintage
(guv_targets.load_deflator) -- the same one the published targets were built with.

WHAT IS HELD COMMON, so the remaining gap is about the distribution and not the setup: the
screen (GKSW's own, earnings >= 0.5 x 520 h x minimum wage, applied nominally to both sides
through the single definition guv_targets.sel0_threshold); the age composition (model ages are
weighted by EPUF's own screened counts); and the top code (EPUF is capped at the taxable
maximum, so the model is also shown capped, and the era grid simply stops each curve there --
above it EPUF's quantile function is flat by construction and the gap says nothing).

WHAT IT SHOWS, measured.  The model is ABOVE EPUF at every percentile, in every era, for both
sexes -- but not by a constant, which is the point:

  * the miss is smallest at the median (+0.13 to +0.32 log points) and explodes at the bottom
    (p10: +0.5 to +1.0).  Netted at the median the curve is a U, so conditional on earning the
    model's lower half is far too COMPRESSED and its upper half is too WIDE.  The mechanism is
    the nonemployment margin: CMS's shock puts the low mass at exactly zero, so the process
    has no part-year or marginal earners, and EPUF's bottom quartile is made of them.
  * it grows with AGE -- 1995 men, p50: +0.18 (25-34), +0.27 (35-44), +0.30 (45-55) -- and
    with the ERA, roughly doubling between 1960 and 1995 before flattening.
  * the participation margin is calibrated to 1978-2013 and does not travel.  The never-work
    share is a fixed 10%/20%, so for women in 1960 the model has 39% of the age cell without
    earnings against EPUF's 72%: it is simulating a modern female workforce in 1960.

HOW MUCH OF THAT IS THE PROCESS, not the data.  The --year figure answers this by drawing
GKSW's own published quantiles -- what CMS fitted to.  GKSW sits within 0.00-0.05 log points
of EPUF across the middle of the distribution, while the model sits +0.11 (1960 men) to +0.23
(1995 men) above GKSW at the median.  So the level error is CMS's own selection bias (their
gtilde is a LATENT profile, but nonemployment falls on low-z workers, so observed mean log
earnings sits above it -- plot_cms_selection.py), not a difference between EPUF and GKSW.

Run from the project root:
    python code/dynamics/plots/plot_cms_cross_section.py [--sex men|women] [--eras Y ...]
    python code/dynamics/plots/plot_cms_cross_section.py --year 1995 [--ages 25 55]
Output: output/dynamics/plots/cms_cross_section_eras_<sex>.{pdf,png}
        output/dynamics/plots/cms_cross_section_<year>.{pdf,png}
"""
import argparse
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

sys.path.insert(0, "code/cross_sections")    # run from the project root, per repo convention
from guv_targets import BASE_YEAR, load_deflator, load_guv, sel0_threshold

OUT = "output/dynamics/plots"
DB = "processed_data/ssa.duckdb"           # opened -readonly: several short queries per run,
                                           # and a write lock makes back-to-back ones race
LIFECYCLE = "replication_repos/CMS/datastore/derived/lifecycle_income"
GKSW_XLSX = "replication_repos/CMS/datastore/raw/lifecycle_income/orig/gksw2017.xlsx"

# --- GKOS parameters, verbatim from CMS's Simulation.m ------------------------------
# This module deliberately mirrors plot_cms_selection.py rather than importing
# gcohort_model: the object here is CMS's process AS RUN, including SigBeta = 0.196/10
# (a tenth of GKOS Table IV; gcohort_model.py carries the corrected 0.196) and
# CorrAlphaBeta = 0.786 (Table IV: 0.768).  --corrected swaps in GKOS's own values.
RHO_Z = 0.959
PROB_Z, MU_Z1, SIG_Z1, SIG_Z2 = 0.407, -0.085, 0.364, 0.069
SIG_Z = 0.714                                   # sd of the initial z draw
PROB_E, MU_E1, SIG_E1, SIG_E2 = 0.130, 0.271, 0.285, 0.037
SIG_ALPHA, SIG_BETA, CORR_AB = 0.300, 0.196 / 10, 0.786
GKOS_SIG_BETA, GKOS_CORR_AB = 0.196, 0.768      # Table IV, per decade of t
LAMBDA = 0.0001
PAR_A, PAR_B, PAR_C, PAR_D = -3.353, -0.859, -5.034, -2.895
MU_Z2 = -PROB_Z * MU_Z1 / (1 - PROB_Z)
MU_E2 = -PROB_E * MU_E1 / (1 - PROB_E)
ZERO_SHARE = {1: 0.10, 2: 0.20}                 # never-work shares (men, women)

SEXES = ((1, "Men"), (2, "Women"))
ERAS = (1960, 1975, 1995, 2005)
GROUPS = (((25, 34), "25-34", "#2a78d6"), ((35, 44), "35-44", "#eb6834"),
          ((45, 55), "45-55", "#7a5195"))
PCTS = np.arange(1, 100)
C_EPUF, C_MODEL, C_CAP, C_GKSW = "#1a1a19", "#eb6834", "#2a78d6", "#7a5195"


# ------------------------------------------------------------------ inputs
def cms_cubics(sex):
    """CMS's fitted cubic coefficients by cohort: {cohort: (b1, b2, b3, cons)}."""
    name = "male" if sex == 1 else "female"
    d = pd.read_stata(f"{LIFECYCLE}/lifecycle_income_{name}.dta")
    return {int(c.split("_")[1]): d[c].to_numpy() for c in d.columns}


def ssa_wage(year):
    """CMS's own SSA average-wage series, thousands of 2013 dollars (gksw2017.xlsx)."""
    s = pd.ExcelFile(GKSW_XLSX).parse("data_mean_2013d_impute")[["year", "ssa"]]
    v = s.loc[s["year"] == year, "ssa"]
    if v.empty or not np.isfinite(v.iloc[0]):
        raise SystemExit(f"no SSA average wage for {year} in gksw2017.xlsx")
    return float(v.iloc[0])


def usable_ages(year, sex, ages):
    """The ages both sides can speak to in year `year`, as (lo, hi).

    A cross-section at age a reads cohort c = year - a + 25, and CMS's file only holds
    c_1949..c_2009, so an early year loses its OLD ages: 1960 keeps 25-36 and nothing above.
    Comparing the model over the ages it covers against EPUF over 25-55 would put an age
    composition difference into the figure and read it as a distributional one, so the EPUF
    side, the weights and the GKSW curve are all cut to this range too."""
    have = set(cms_cubics(sex))
    ok = [a for a in range(ages[0], ages[1] + 1) if (year - a + 25) in have]
    if not ok:
        raise SystemExit(f"no CMS cohort covers {year} over ages {ages[0]}-{ages[1]}")
    return min(ok), max(ok)


def epuf_cells(year, sex, ages):
    """(age, earnings) for every positive EPUF earner in the (year, sex) slice."""
    q = ("SELECT a.year - d.yob AS age, a.earnings FROM annual a JOIN demographic d USING(id) "
         f"WHERE a.year={year} AND d.sex={sex} AND a.earnings>0 "
         f"AND a.year - d.yob BETWEEN {ages[0]} AND {ages[1]} ORDER BY age, a.earnings")
    out = subprocess.run(["duckdb", "-readonly", DB, "-noheader", "-csv", "-c", q],
                         capture_output=True, text=True, check=True).stdout
    d = np.loadtxt(out.splitlines(), delimiter=",", dtype=float)
    return d[:, 0].astype(int), d[:, 1]


def epuf_population(year, sex, ages):
    """Sampled individuals in each age cell, earnings or not -- the denominator that makes
    EPUF's nonemployment share comparable to the model's.  `annual` is a SPARSE panel, so an
    absent (id, year) is zero covered earnings, not missing; the count therefore comes from
    `demographic`.  It is an UPPER bound on nonemployment: it still holds people who died,
    emigrated, or worked only in noncovered jobs that year."""
    q = (f"SELECT {year} - yob AS age, count(*) FROM demographic WHERE sex={sex} "
         f"AND {year} - yob BETWEEN {ages[0]} AND {ages[1]} GROUP BY 1 ORDER BY 1")
    out = subprocess.run(["duckdb", "-readonly", DB, "-noheader", "-csv", "-c", q],
                         capture_output=True, text=True, check=True).stdout
    d = np.loadtxt(out.splitlines(), delimiter=",", dtype=float)
    return pd.Series(d[:, 1], index=d[:, 0].astype(int))


def gksw_pooled(year, sex, ages, weights, rng, m=40_000):
    """The PUBLISHED GKSW cross-section for the same year, pooled with the same age weights.

    Quantiles do not pool, so each age's own log-quantile function is rebuilt from its six
    published points (p10..p98, linear in log earnings between them, end-segment slope
    outside -- the same reconstruction plot_shape_gap.py uses), sampled at uniform ranks, and
    the draws are pooled.  Only percentiles 10-95 of the result are plotted, so the curve does
    not lean on the extended ends."""
    g = load_guv()
    g = g[(g.year == year) & (g.sex == sex) & g.age.between(*ages)]
    qs = np.array([0.10, 0.25, 0.50, 0.75, 0.90, 0.98])
    cols = ["p10", "p25", "p50", "p75", "p90", "p98"]
    vals, wts = [], []
    for _, r in g.iterrows():
        w = float(weights.get(int(r["age"]), 0.0))
        if w == 0:
            continue
        y = np.log(r[cols].to_numpy(dtype=float))
        u = rng.random(m)
        ly = np.interp(u, qs, y)                       # linear in log between the six points
        lo, hi = u < qs[0], u > qs[-1]                 # end-segment slopes outside them
        ly[lo] = y[0] + (u[lo] - qs[0]) * (y[1] - y[0]) / (qs[1] - qs[0])
        ly[hi] = y[-1] + (u[hi] - qs[-1]) * (y[-1] - y[-2]) / (qs[-1] - qs[-2])
        vals.append(np.exp(ly))
        wts.append(np.full(m, w / m))
    if not vals:
        return None
    return np.concatenate(vals), np.concatenate(wts)


def taxmax(year):
    """The top code, recoverable from the data as the year's maximum earnings."""
    q = f"SELECT MAX(earnings) FROM annual WHERE year={year}"
    return float(subprocess.run(["duckdb", "-readonly", DB, "-noheader", "-csv", "-c", q],
                                capture_output=True, text=True, check=True).stdout)


# ------------------------------------------------------------------ the process
def simulate_gfree(sex, ages, n, rng, corrected=False):
    """One panel of the g-FREE multiplier by age: {age: array of length n}.

    Y(age) = exp(g_cohort(age)) * u(age), and this returns u.  Everything is CMS's
    Simulation.m: mixture-of-normals AR(1) in z, mixture transitory e, HIP term alpha+beta*t,
    their cross-sectionally evaluated Jensen correction, a never-work group, and a
    state-dependent unemployment logit whose PAR_C = -5.034 puts nonemployment on LOW-z
    workers (which is why conditioning on positive earnings selects on the persistent
    component -- see plot_cms_selection.py)."""
    sig_beta = GKOS_SIG_BETA if corrected else SIG_BETA
    corr = GKOS_CORR_AB if corrected else CORR_AB
    cov = corr * SIG_ALPHA * sig_beta
    ab = rng.multivariate_normal([0, 0], [[SIG_ALPHA**2, cov], [cov, sig_beta**2]], n)
    alpha, beta = ab[:, 0], ab[:, 1]
    works = rng.random(n) > ZERO_SHARE[sex]
    z = SIG_Z * rng.standard_normal(n)

    out = {}
    for j, age in enumerate(range(25, ages[1] + 1)):
        t = (age - 24) / 10
        if j > 0:
            pick = rng.random(n) < PROB_Z
            z = RHO_Z * z + np.where(pick, MU_Z1 + SIG_Z1 * rng.standard_normal(n),
                                     MU_Z2 + SIG_Z2 * rng.standard_normal(n))
        pick = rng.random(n) < PROB_E
        e = np.where(pick, MU_E1 + SIG_E1 * rng.standard_normal(n),
                     MU_E2 + SIG_E2 * rng.standard_normal(n))
        odds = np.exp(PAR_A + PAR_B * t + PAR_C * z + PAR_D * z * t)
        prob_u = odds / (1 + odds)
        dur = np.minimum(1.0, rng.exponential(1 / LAMBDA, n))
        unemployed = np.where(rng.random(n) < prob_u, dur, 0.0)

        hip = alpha + beta * t
        ylog = hip + z + e - z.var() / 2 - hip.var() / 2 - e.var() / 2   # CMS Jensen term
        if age >= ages[0]:
            out[age] = works * np.exp(ylog) * (1 - unemployed) / (1 - unemployed.mean())
    return out


def model_cross_section(year, sex, ages, n, rng, corrected=False):
    """Model earnings in 2013 dollars, one array per age, for the year-Y cross-section."""
    cubics, scale = cms_cubics(sex), ssa_wage(year) * 1000.0
    u = simulate_gfree(sex, ages, n, rng, corrected)
    out = {}
    for age, mult in u.items():
        cohort = year - age + 25
        if cohort not in cubics:
            continue
        b1, b2, b3, cons = cubics[cohort]
        g = cons + b1 * age + b2 * age**2 + b3 * age**3
        out[age] = np.exp(g) * mult * scale
    return out


# ------------------------------------------------------------------ assembly
def wquantile(x, w, q):
    """Weighted quantiles (linear in the cumulative weight), for the composition reweighting."""
    o = np.argsort(x)
    x, w = x[o], w[o]
    c = np.cumsum(w) - 0.5 * w
    return np.interp(q, c / w.sum(), x)


def assemble(year, sex, ages, n, rng, corrected=False):
    """Both cross-sections in 2013 dollars on the common screen, plus what to report."""
    to2013 = load_deflator()[year]
    thresh = sel0_threshold(year)                       # nominal, GKSW's own screen
    cap = taxmax(year)
    ages = usable_ages(year, sex, ages)

    age_e, earn = epuf_cells(year, sex, ages)
    keep = earn >= thresh
    age_e, earn = age_e[keep], earn[keep]
    epuf = earn * to2013
    censored = float(np.mean(earn >= cap))
    counts = pd.Series(age_e).value_counts()
    pop = epuf_population(year, sex, ages)
    ebelow = 1.0 - counts.reindex(pop.index).fillna(0).sum() / pop.sum()

    mdl = model_cross_section(year, sex, ages, n, rng, corrected)
    vals, wts, dropped, tot = [], [], 0.0, 0.0
    for age, x in mdl.items():
        share = float(counts.get(age, 0))
        if share == 0:
            continue
        pos = x >= thresh * to2013                       # the same screen, in 2013 dollars
        dropped += (1.0 - pos.mean()) * share
        tot += share
        vals.append(x[pos])
        wts.append(np.full(pos.sum(), share / max(pos.sum(), 1)))
    model = np.concatenate(vals)
    mw = np.concatenate(wts)
    return dict(epuf=epuf, model=model, mw=mw, cap=cap * to2013, censored=censored,
                ebelow=ebelow, mbelow=dropped / tot, n=age_e.size, ages=ages,
                gksw=gksw_pooled(year, sex, ages, counts, rng))


def era_grid(a, rng):
    """Where the process misses, by era and age: the gap curve, and the gap netted at p50.

    Row 1 is log(model / EPUF) across the percentiles of each screened cross-section, one line
    per age group, cut off where EPUF hits the taxable maximum and the data stop being a
    distribution.  Row 2 subtracts each line's own median gap, which separates the two errors:
    whatever CMS's level is doing (the selection bias, +0.11 to +0.23 log points against their
    own GKSW target) shifts row 1 and cancels in row 2, so row 2 is the SHAPE conditional on
    earning -- what the process gets wrong about who earns what, given that they earn."""
    fig, axes = plt.subplots(2, len(a.eras), figsize=(3.1 * len(a.eras) + 0.9, 7.0),
                             sharex=True, sharey="row")
    sex = 1 if a.sex == "men" else 2
    for k, year in enumerate(a.eras):
        top, bot = axes[0, k], axes[1, k]
        notes = []
        for grp, glab, col in GROUPS:
            try:
                d = assemble(year, sex, grp, a.n, rng, a.corrected)
            except SystemExit:                       # no CMS cohort reaches these ages yet
                notes.append(f"{glab}: no CMS profile")
                continue
            qe = np.percentile(d["epuf"], PCTS)
            qm = wquantile(d["model"], d["mw"], PCTS / 100.0)
            gap = np.log(qm / qe)
            m = PCTS <= 100 * (1 - d["censored"])     # above the cap EPUF is flat by construction
            top.plot(PCTS[m], gap[m], color=col, lw=2.0)
            bot.plot(PCTS[m], gap[m] - gap[PCTS == 50][0], color=col, lw=2.0)
            if d["ages"] != grp:                      # the era truncates this group's ages
                notes.append(f"{glab} available only to {d['ages'][1]}")
            if grp == GROUPS[0][0]:
                notes.append(f"no earnings, 25-34: EPUF {d['ebelow']:.0%}, "
                             f"model {d['mbelow']:.0%}")
        for ax in (top, bot):
            ax.axhline(0, color="#888888", lw=0.9)
            ax.set_xlim(1, 99)
        top.set_title(str(year))
        top.text(0.97, 0.04, "\n".join(notes), transform=top.transAxes, fontsize=7.5,
                 color="#666666", va="bottom", ha="right")
        bot.set_xlabel("percentile")
        if k == 0:
            top.set_ylabel("log(model / EPUF)")
            bot.set_ylabel("same, netted at the median\n(shape alone)")
            top.legend(handles=[Line2D([], [], color=c, lw=2.0, label=l)
                                for _, l, c in GROUPS],
                       loc="upper right", frameon=False, fontsize=8, title="age",
                       title_fontsize=8)

    fig.suptitle(f"CMS process vs EPUF, {a.sex}: the miss is in the shape of the earnings "
                 f"distribution, and it grows with age", y=0.985)
    fig.text(0.5, 0.955, "Row 2 nets each line at its own median, leaving shape alone: above 0 at "
             "the bottom = the model's\nlower half is too compressed, above 0 at the top = its "
             "upper half is too wide.  Curves stop where\nEPUF reaches the taxable maximum, "
             "beyond which its quantiles are flat by construction.",
             ha="center", va="top", fontsize=8.5, color="#444444", linespacing=1.5)
    fig.tight_layout(rect=(0, 0, 1, 0.885))
    stem = f"{OUT}/cms_cross_section_eras_{a.sex}{a.tag}"
    fig.savefig(f"{stem}.pdf"); fig.savefig(f"{stem}.png", dpi=200)
    print(f"wrote {stem}.pdf / .png")


def one_year(a, rng):
    """One year in full: both quantile functions, plus GKSW published as the third series."""
    fig, axes = plt.subplots(2, 2, figsize=(11.0, 7.6), sharex=True,
                             gridspec_kw={"height_ratios": [2.1, 1]})
    for k, (sex, label) in enumerate(SEXES):
        d = assemble(a.year, sex, a.ages, a.n, rng, a.corrected)
        qe = np.percentile(d["epuf"], PCTS)
        qm = wquantile(d["model"], d["mw"], PCTS / 100.0)
        qc = wquantile(np.minimum(d["model"], d["cap"]), d["mw"], PCTS / 100.0)
        top, bot = axes[0, k], axes[1, k]
        pcut = 100 * (1 - d["censored"])
        for ax in (top, bot):
            ax.axvspan(pcut, 100, color="#cccccc", alpha=0.35, lw=0)
        top.plot(PCTS, qe, color=C_EPUF, lw=2.4, label="EPUF")
        top.plot(PCTS, qm, color=C_MODEL, lw=2.4, ls="--", label="CMS process")
        top.plot(PCTS, qc, color=C_CAP, lw=1.5, ls=":", label="CMS process, top-coded")
        if d["gksw"] is not None:
            gv, gw = d["gksw"]
            mid = (PCTS >= 10) & (PCTS <= 95)
            qg = wquantile(gv, gw, PCTS[mid] / 100.0)
            top.plot(PCTS[mid], qg, color=C_GKSW, lw=1.8, ls=(0, (6, 2)),
                     label="GKSW published (CMS's fitting target)")
            bot.plot(PCTS[mid], np.log(qg / qe[mid]), color=C_GKSW, lw=1.6, ls=(0, (6, 2)))
        top.axhline(d["cap"], color="#888888", lw=1.0, ls="-.")
        top.set_yscale("log")
        top.set_title(f"{label}, ages {d['ages'][0]}-{d['ages'][1]}, {a.year}")
        top.text(2, d["cap"] * 1.06, "taxable maximum", fontsize=8, color="#666666")
        top.text(0.03, 0.97,
                 f"n = {d['n']:,}   EPUF at the cap: {d['censored']:.1%}\n"
                 f"zero or below screen, share of the age cell:\n"
                 f"   EPUF {d['ebelow']:.1%}   model {d['mbelow']:.1%}",
                 transform=top.transAxes, va="top", fontsize=8.5, color="#444444")
        if k == 0:
            top.set_ylabel(f"earnings, {BASE_YEAR} $ (log scale)")
            bot.set_ylabel("log(series / EPUF)")
        top.legend(loc="lower right", frameon=False, fontsize=8.5)

        bot.axhline(0, color="#888888", lw=0.9)
        bot.plot(PCTS, np.log(qm / qe), color=C_MODEL, lw=2.0)
        bot.set_xlabel("percentile of the screened cross-section")
        bot.set_xlim(1, 99)
        bot.text(pcut - 1, bot.get_ylim()[1], "EPUF top-coded ->", fontsize=8,
                 color="#666666", va="top", ha="right")

    fig.suptitle(f"Cross-section of earnings in {a.year}: EPUF microdata vs the CMS process"
                 + (" (GKOS Table IV parameters)" if a.corrected else ""), y=0.985)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    stem = f"{OUT}/cms_cross_section_{a.year}{a.tag}"
    fig.savefig(f"{stem}.pdf"); fig.savefig(f"{stem}.png", dpi=200)
    print(f"wrote {stem}.pdf / .png")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--year", type=int, help="one year in full instead of the era grid")
    p.add_argument("--eras", type=int, nargs="+", default=list(ERAS))
    p.add_argument("--sex", choices=("men", "women"), default="men",
                   help="era grid only; the single-year figure shows both")
    p.add_argument("--ages", type=int, nargs=2, default=(25, 55), metavar=("LO", "HI"),
                   help="single-year figure only; the era grid uses its own age groups")
    p.add_argument("--n", type=int, default=100_000, help="simulated workers per age")
    p.add_argument("--seed", type=int, default=5)
    p.add_argument("--corrected", action="store_true",
                   help="GKOS Table IV sigma_beta/corr instead of CMS's coded values")
    p.add_argument("--tag", default="")
    a = p.parse_args()
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    one_year(a, rng) if a.year else era_grid(a, rng)


if __name__ == "__main__":
    main()
