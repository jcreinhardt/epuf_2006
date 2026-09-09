#!/usr/bin/env python
"""EPUF's earnings histogram in one year against the one OUR fitted g(t) implies.

Everything else in the dynamics section compares MOMENTS -- medians by cohort x age, the
aggregate.  This is the whole distribution, in the units the data come in, for a year at a
time: the histogram of positive covered earnings in EPUF, and the histogram the GKOS process
produces when it is driven by the g(t) this project estimates per (sex, cohort).

WHAT IS BEING PLOTTED, precisely.  For a cross-section year Y, a worker of age a belongs to
cohort c = Y - a + 25, so the model's earnings for that cell are

    log Y_i = g_{sex, c}(a) + u_i(a),        u = log(1-nu) + alpha + beta*t + z + eps

with g read from the fitted CSV through gcohort_model.g_at (hinges included, so ages outside
25-55 use the EPUF-identified extension) and u simulated by gcohort_model.simulate_u at the
CORRECTED GKOS parameters.  u is g-free and nothing downstream feeds back on the level, so ONE
panel over ages 20-70 serves every cohort and both sexes; only g changes from cell to cell.
A full-year nonemployment spell gives u = -inf, i.e. exactly zero earnings, which is why the
model's zero share is reported separately rather than shown in a histogram of log earnings.

AGGREGATION IS EPUF'S OWN.  Each (sex, age) cell enters the model histogram with the weight of
that cell among EPUF's positive earners in that year, so the mixture over cohorts and over the
two sexes is the data's, not a modelling choice.  What remains is the within-cell distribution
and the between-cell level -- which is what the figure is for.

THE PROCESS IS MALE-CALIBRATED for both sexes (only g(t) is fitted per sex), so the women's
panel carries every sex difference in dispersion and nonemployment risk inside g.  That is the
standing caveat of the whole dynamics section (gcohort_model.py), and this figure is where it
is most visible.

WHAT IT SHOWS, measured on g_cohort_smm_p50_relevelled_extrapolated.csv, ages 20-70, both
sexes at EPUF weights, conditional on positive earnings.  The two years fail DIFFERENTLY:

  * 1965 -- the body is too LOW and the tail too THIN.  Log gaps model minus EPUF: p25 -0.31,
    p50 -0.40, and 27% of the model clears the $27.6k (2013 $) cap against EPUF's 41%.  The
    censored p90 gap of +0.71 says the opposite and is an artefact: EPUF's p75 and p90 both
    SIT ON the cap, so only the share above it is informative there.
  * 1995 -- the body is nearly right and the bottom is far too high: p10 +0.69, p50 -0.16,
    p75 -0.12, p90 +0.02, with 8% of the model above the cap against EPUF's 6%.  The +0.69 at
    p10 is the nonemployment margin again: the process has no part-year or marginal earners,
    while EPUF's bottom decile is made of them.
  * the sub-$100 code makes the bottom failure exact and countable: 2.3% of EPUF's 1965
    earners and 0.8% of its 1995 earners are ON that code, against 0.2% and 0.0% of the
    model's.  The process barely produces anyone earning under $100 in a year.
  * in BOTH years the model has far too few people with no earnings at all -- 26% of the age
    cell against EPUF's 49% (1965) and 39% (1995).  The nonemployment logit is GKOS's, fitted
    on 1978-2013 men, and only g(t) is re-estimated here, so nothing in the pipeline can move
    it: the 1965 panel is running a modern participation margin in 1965.

THE MODEL IS PUT THROUGH EPUF'S DISCLOSURE PROTECTION before it is compared (`disclose`), so
both histograms carry the same artefacts and the difference between them is the process.  The
rule was RECOVERED FROM THE DATA rather than assumed:

  | true nominal amount | what EPUF records |
  |---|---|
  | < $100            | one number, the year's sub-$100 mean ($46 in 1951 rising to $58 in 2006) |
  | $100 - $999       | random-rounded to a multiple of $25 |
  | $1,000 - $49,999  | random-rounded to a multiple of $100 |
  | >= $50,000        | random-rounded to a multiple of $1,000 |
  | rounds up to the cap without reaching it | one number, that group's mean |
  | >= the cap        | the cap |

  The $50,000 step is exact and nominal, checked in 1990 / 2000 / 2006 (below it 11% of values
  are multiples of $1,000, the chance rate; at and above it, 100%).  The two code VALUES are
  read out of EPUF per year instead of recomputed, so they are the data's own constants.  The
  function is a fixed point on EPUF's recorded values (100.0% unchanged) and preserves the
  mean of a smooth input below the cap to 4e-4.

  It matters for the two ends only, which is itself the result: disclosed and undisclosed model
  curves are indistinguishable through the middle (checked; `prepare` still returns the
  undisclosed shares as `undisc` if you want to draw it), so the mid-range gap is the process,
  not the protection.

BIN WIDTH IS SET BY THE ROUNDING GRID, not by taste -- see BINS.  At $1,700 nominal in 1965
consecutive recordable values are 0.056 log apart, so a 90-bin histogram catches one grid
point in some bins and two in others and BOTH series come out as a factor-of-two sawtooth.

ONE FEATURE THAT IS NOT MODEL ERROR: the SCREEN line marks GKSW's sel0 threshold (0.5 x 520 h
x minimum wage), the cut every moment-fitting figure in this section conditions on.  Nothing
here is screened: the point is to see the mass the screen normally hides.

HOW IT IS DRAWN, since a few of the choices are load-bearing rather than cosmetic:

  * y is the SHARE of earners in each band, not a density -- a share is the quantity a reader
    can check against the annotations ("41% at the cap"), and with equal-width log bins it is
    proportional to the density anyway.
  * the two point masses (the cap, the sub-$100 code) run PAST the top of the plot on purpose:
    scaling to them flattens the body, which is the part being compared.  Each is labelled with
    the share it carries, on both sides, so nothing is hidden by the clipping.
  * both panels share one y-scale.  Small multiples that do not are not comparable.
  * colours are slots 1 and 2 of the house categorical palette, unmodified and in fixed order:
    the data is the subject (slot 1), the model the comparison (slot 2).
  * the axis stops just past the highest cap: once both series are top-coded nothing lives
    above it, and the two panels keep ONE x-range so a position means the same dollars in both.
  * the direct labels go where the two lines are FURTHEST APART and at least 0.9 log below the
    cap, so they never land on a clipped spike or inside its callout; the cap callout is anchored
    to the panel corner so a long label cannot overflow whatever year is plotted.

Run from the project root:
    python code/dynamics/plots/plot_epuf_vs_model_hist.py [--years 1965 1995] [--fits CSV]
Output: output/dynamics/plots/epuf_vs_model_hist.{pdf,png}
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

sys.path.insert(0, "code/dynamics")          # run from the project root, per repo convention
sys.path.insert(0, "code/cross_sections")
import gcohort_model as E
from guv_targets import BASE_YEAR, load_deflator, sel0_threshold

OUT = "output/dynamics/plots"
DB = "processed_data/ssa.duckdb"             # -readonly: several short queries, no writes
FITS = "output/dynamics/g_cohort_smm_p50_relevelled_extrapolated.csv"
SEXES = ((1, "male", "Men"), (2, "female", "Women"))

# Palette: slots 1 and 2 of the dataviz reference instance, unmodified and in fixed order
# (their CVD and normal-vision separation is validated there; do not re-step them).  Data is
# the subject, so it takes slot 1; the model is the comparison, slot 2.  The undisclosed model
# is the SAME entity under a different treatment, so it keeps the model's hue and separates by
# dash -- a third hue would claim it is a third thing.
C_DATA, C_MODEL = "#2a78d6", "#eb6834"
INK, INK_2, INK_3 = "#0b0b0b", "#52514e", "#8a8984"
GRID = "#e7e6e2"
# Bin width is set by the ROUNDING GRID, not by taste.  EPUF stores 1965 earnings on a $100
# grid, so at $1,700 nominal ($10k of 2013 $) consecutive values are 0.056 log apart: with 90
# bins (width 0.104) each bin catches one grid point or two, and both histograms come out as a
# factor-of-two sawtooth.  46 bins put >= 4 grid points in every bin over the visible range.
BINS = np.linspace(np.log(200.0), np.log(2e6), 46)      # log 2013 dollars


def duck(q):
    out = subprocess.run(["duckdb", "-readonly", DB, "-csv", "-c", q],
                         capture_output=True, text=True, check=True).stdout
    return pd.read_csv(pd.io.common.StringIO(out))


def epuf(year, ages):
    """Positive covered earnings by (sex, age), and the age-cell populations behind them."""
    e = duck(f"SELECT d.sex, a.year - d.yob AS age, a.earnings FROM annual a "
             f"JOIN demographic d USING(id) WHERE a.year={year} AND d.sex IS NOT NULL "
             f"AND a.earnings>0 AND a.year - d.yob BETWEEN {ages[0]} AND {ages[1]}")
    pop = duck(f"SELECT sex, count(*) AS pop FROM demographic WHERE sex IS NOT NULL "
               f"AND {year} - yob BETWEEN {ages[0]} AND {ages[1]} GROUP BY 1")
    return e, pop.set_index("sex")["pop"]


# ------------------------------------------------------- EPUF's disclosure protection
# Recovered from the data itself, not assumed (the scan is in the docstring): the recorded
# value is the true one random-rounded to a base that steps at $1,000 and $50,000 NOMINAL,
# with a single code below $100, a collapse value for anything that rounds up to the cap
# without reaching it, and the cap itself on top.  The two code VALUES are read out of EPUF
# per year rather than recomputed, so they are the data's own constants.
ROUND_STEPS = ((1_000.0, 25.0), (50_000.0, 100.0), (np.inf, 1_000.0))
CODE_LO_MAX = 100.0            # below this EPUF stores one number: the sub-$100 mean


def epuf_codes(year):
    """(cap, sub-$100 code, near-cap collapse value or None) for `year`, read from EPUF."""
    cap = float(duck(f"SELECT MAX(earnings) AS m FROM annual WHERE year={year}")["m"][0])
    lo = duck(f"SELECT earnings, count(*) n FROM annual WHERE year={year} AND earnings>0 "
              f"AND earnings<{CODE_LO_MAX:.0f} GROUP BY 1 ORDER BY n DESC LIMIT 1")
    # the collapse value is the one near-cap amount that is NOT on the rounding grid
    base = base_of(np.array([cap]))[0]
    c = duck(f"SELECT earnings, count(*) n FROM annual WHERE year={year} "
             f"AND earnings > {cap - 5 * base} AND earnings < {cap} "
             f"AND earnings % {base:.0f} <> 0 GROUP BY 1 ORDER BY n DESC LIMIT 1")
    return cap, float(lo["earnings"][0]), (float(c["earnings"][0]) if len(c) else None)


def base_of(x):
    """The rounding base EPUF uses at each nominal amount."""
    b = np.full(np.shape(x), ROUND_STEPS[-1][1], float)
    for hi, step in reversed(ROUND_STEPS[:-1]):
        b[np.asarray(x) < hi] = step
    return b


def disclose(x, year, rng, codes=None):
    """Put nominal dollars through EPUF's disclosure protection, in EPUF's order.

    Random rounding is STOCHASTIC and unbiased -- down with probability 1 - frac, up with
    probability frac -- so the mean survives and only the fine structure is destroyed, which
    is the point of the scheme and the reason a deterministic round would not reproduce it.

    CHECKED two ways, which is how the bases and thresholds above were pinned down: run on
    EPUF's OWN values it is a fixed point (100.0% unchanged in 1965 and 1995 -- every recorded
    amount already sits on the grid this function would put it on), and on a smooth lognormal
    input it preserves the mean below the cap to 4e-4 (1965) and 4e-7 (1995)."""
    cap, code_lo, collapse = codes if codes else epuf_codes(year)
    x = np.asarray(x, float)
    b = base_of(x)
    q, frac = np.divmod(x / b, 1.0)
    out = b * (q + (rng.random(x.size) < frac))
    if collapse is not None:                      # rounds up to the cap without reaching it
        out[(x < cap) & (out >= cap)] = collapse
        out[x == collapse] = collapse             # already collapsed: a fixed point
    out[x >= cap] = cap
    out[x < CODE_LO_MAX] = code_lo
    return out


def model_draws(year, weights, fits, u, ages):
    """(log earnings, weights) for the model cross-section, cells weighted as in EPUF.

    Returns log 2013 dollars with the zeros dropped, plus the zero share, so the histogram and
    the reported nonemployment share come from the same draws."""
    vals, wts, zero, tot = [], [], 0.0, 0.0
    for sex, tag, _ in SEXES:
        f = fits[fits["sex"] == tag].set_index("cohort")
        for age in range(ages[0], ages[1] + 1):
            w = float(weights.get((sex, age), 0.0))
            if w == 0:
                continue
            cohort = year - age + 25
            if cohort not in f.index:
                raise SystemExit(f"no fitted g for {tag} cohort {cohort}; extrapolate further")
            g = float(E.g_at(f.loc[cohort], [age])[0])
            x = g + u[:, E.sim_jj(age)]
            ok = np.isfinite(x)                        # -inf = a full-year spell, i.e. zero
            zero += (1.0 - ok.mean()) * w
            tot += w
            vals.append(x[ok])
            wts.append(np.full(int(ok.sum()), w / max(int(ok.sum()), 1)))
    return np.concatenate(vals), np.concatenate(wts), zero / tot


def prepare(year, a, u, fits, rng):
    """Everything one panel needs, in shares per bin -- no drawing, so both panels can be put
    on a common y-scale before either is drawn (small multiples are only comparable if they
    are)."""
    to2013 = load_deflator()[year]
    e, pop = epuf(year, a.ages)
    cap, code_lo, collapse = epuf_codes(year)
    w = e.groupby(["sex", "age"]).size()
    x, mw, zero = model_draws(year, w, fits, u, a.ages)
    xd = np.log(disclose(np.exp(x) / to2013, year, rng, (cap, code_lo, collapse)) * to2013)
    le = np.log(e["earnings"].to_numpy(dtype=float) * to2013)
    lcap = np.log(cap * to2013)

    def share(v, wt):
        h, _ = np.histogram(v, bins=BINS, weights=wt)
        return h / h.sum() * 100.0

    d = dict(year=year, lcap=lcap, cap=cap, code_lo=code_lo, n=len(e),
             data=share(le, None), model=share(xd, mw), undisc=share(x, mw),
             at_cap=float((e["earnings"] >= cap).mean()),
             m_at_cap=float(np.average(x >= lcap, weights=mw)),
             coded=float((e["earnings"] == code_lo).mean()),
             m_coded=float(np.average(np.exp(xd) <= code_lo * to2013 * 1.001, weights=mw)),
             no_earn=1.0 - len(e) / float(pop.sum()), m_no_earn=zero)
    # medians of the SAME values the curves are drawn from -- so the rule and the histogram
    # tell one story.  EPUF's is unweighted (one row per earner); the model's is weighted by
    # the (sex, age) cell shares that mix its draws.
    o = np.argsort(xd)
    cw = np.cumsum(mw[o])
    d["med_data"] = float(np.median(le))
    d["med_model"] = float(xd[o][np.searchsorted(cw, 0.5 * cw[-1])])

    # the spikes are point masses; the body is what the eye should be scaled to
    body = (BINS[1:] <= lcap) & (BINS[:-1] > BINS[0])
    d["body_max"] = max(d["data"][body].max(), d["model"][body].max())
    return d


def stair(ax, y, **kw):
    """A step outline over BINS (the last value repeated so the final bin closes)."""
    return ax.step(BINS, np.append(y, y[-1]), where="post", **kw)[0]


def draw(ax, d, ymax):
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=GRID, lw=0.8, ls="-")          # solid hairlines, recessive
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK_3, length=3, width=0.8, labelsize=9)

    for key, col in (("med_data", C_DATA), ("med_model", C_MODEL)):
        ax.axvline(d[key], color=col, lw=1.4, ls=(0, (4, 2.5)), zorder=1)   # median
    ax.fill_between(BINS, np.append(d["data"], d["data"][-1]), step="post",
                    color=C_DATA, alpha=0.10, lw=0)
    stair(ax, d["data"], color=C_DATA, lw=2.0)
    stair(ax, d["model"], color=C_MODEL, lw=2.0)

    ax.tick_params(axis="y", length=0)
    ax.set_xticks(np.log([1e3, 1e4, 1e5]), ["$1k", "$10k", "$100k"])
    ax.set_xticks(np.log([3e2, 3e3, 3e4]), minor=True)
    ax.set_ylim(0, ymax)                     # limits LAST: set_xticks widens the view to
    ax.set_xlim(BINS[0], np.log(1.5e5))      # include a tick outside it

    ax.set_title(f"{d['year']}", loc="left", fontsize=13, fontweight="bold", color=INK, pad=8)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--years", type=int, nargs="+", default=(1965, 1995))
    p.add_argument("--fits", default=FITS)
    p.add_argument("--ages", type=int, nargs=2, default=(20, 70), metavar=("LO", "HI"))
    p.add_argument("--n", type=int, default=200_000, help="simulated workers")
    p.add_argument("--seed", type=int, default=5)
    p.add_argument("--tag", default="")
    a = p.parse_args()
    os.makedirs(OUT, exist_ok=True)

    fits = pd.read_csv(a.fits)
    rng = np.random.default_rng(a.seed)
    u = E.simulate_u(rng, a.n, E.SIM_AGES)
    panels = [prepare(y, a, u, fits, rng) for y in a.years]
    # scaled to the BODY: the point masses at the cap and on the sub-$100 code run past the
    # top rather than flattening the distributions the figure exists to compare
    ymax = 1.16 * max(d["body_max"] for d in panels)

    plt.rcParams.update({"font.family": "sans-serif", "axes.labelcolor": INK_2,
                         "text.color": INK, "figure.facecolor": "#fcfcfb",
                         "axes.facecolor": "#fcfcfb"})
    fig, axes = plt.subplots(1, len(panels), figsize=(5.9 * len(panels), 4.6), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, d in zip(axes, panels):
        draw(ax, d, ymax)
    axes[0].set_ylabel("share of earners in each band, %", fontsize=9.5, color=INK_2)

    fig.legend(handles=[Line2D([], [], color=C_DATA, lw=2.0, label="EPUF microdata"),
                        Line2D([], [], color=C_MODEL, lw=2.0,
                               label="model, EPUF disclosure applied")],
               loc="lower center", bbox_to_anchor=(0.5, 0.005), frameon=False, ncol=2,
               fontsize=10, handlelength=2.2, columnspacing=2.4, labelcolor=INK_2)

    fig.subplots_adjust(left=0.075, right=0.985, top=0.945, bottom=0.135, wspace=0.06)
    stem = f"{OUT}/epuf_vs_model_hist{a.tag}"
    fig.savefig(f"{stem}.pdf"); fig.savefig(f"{stem}.png", dpi=200)
    print(f"wrote {stem}.pdf / .png")


if __name__ == "__main__":
    main()
