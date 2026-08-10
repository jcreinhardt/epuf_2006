#!/usr/bin/env python
"""Histogram of one (age, cohort, sex) earnings cross-section with its fitted density.

Plots, on a log-dollar axis: the raw EPUF data density for one birth cohort observed at one
age (so year = cohort + age) and one sex, the fitted model density, and -- for the women's
mixture -- its two weighted components. Vertical lines mark the $200 / taxmax-$1000 censoring
thresholds; the mass outside them (fit as censored, not as density) shows up as the two edge
spikes. A box reports the fitted parameters, the censored shares, and the implied uncapped
mean E[X].

Men are fit with the double Pareto-lognormal (a single Normal-Laplace density), women with
the two-component lognormal mixture -- the pairing from crosssec_fit.

By default the parameters come from the PIPELINE output (the joint smoothed-constrained
solve), so the curve drawn is the one the rest of the project actually uses. `--refit` runs
a standalone unconstrained MLE for the cell instead, which is the original behaviour of this
script and is useful for seeing what the smoothing and the mean constraint changed;
`--refit --overlay` draws both.

  python code/cross_sections/plot_cross_section.py [age] [cohort] [sex]
    age defaults to 40, cohort to 1950, sex to 2 (female); sex accepts 1/2 or male/female.
    (age 40, cohort 1950 -> year 1990.)  --year Y sets the year directly (cohort = Y - age).
    -> output/cross_sections/<women_mixture|men_dpln>_c<cohort>_a<age>.pdf (+ .png)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

import crosssec_fit as cf

PARAMS = Path("output/cross_sections/cross_section_params_smoothed.csv")

# per-sex plumbing: fitter, human label, model name, output-file tag
FIT        = {1: cf.fit_dpln, 2: cf.fit_mixture}
LABEL      = {1: "male",      2: "female"}
MODEL_NAME = {1: "double Pareto-lognormal", 2: "lognormal mixture"}
FILE_TAG   = {1: "men_dpln",  2: "women_mixture"}


def comp_density(yy, mu, s):        # normal pdf on the log-earnings axis
    return np.exp(-np.log(s) - 0.5 * cf.LOG2PI - 0.5 * ((yy - mu) / s) ** 2)


def fitted_curves(yy, sex, r):
    """Total fitted density on the log axis, plus any weighted components to draw as dashed
    lines (empty for the single-density dPlN). The mixture components are labelled by their
    own median and weight rather than as 'upper'/'lower': which component is the high one
    swaps across cells (the documented regime flip), so a fixed label would be wrong half
    the time."""
    if sex == 2:                                            # lognormal mixture
        mu1, mu2, s1, s2, w = r["mu1"], r["mu2"], r["sig1"], r["sig2"], r["w"]
        c1 = w * comp_density(yy, mu1, s1)
        c2 = (1 - w) * comp_density(yy, mu2, s2)
        comps = [(f"comp 1 (w={w:.2f}, med ${np.exp(mu1):,.0f})", c1, "C0"),
                 (f"comp 2 (w={1-w:.2f}, med ${np.exp(mu2):,.0f})", c2, "C2")]
        return c1 + c2, comps
    dens = np.exp(cf.nl_logpdf(yy, r["alpha"], r["beta"], r["nu"], r["tau"]))  # dPlN
    # the Normal-Laplace pdf overflows to +inf far into the lower tail (the Mills ratio blows
    # up where the density is negligible anyway); zero those out or the y-limit is inf.
    return np.nan_to_num(dens, nan=0.0, posinf=0.0, neginf=0.0), []


def param_text(sex, r):
    """Fitted parameters + implied uncapped mean, for the on-figure box."""
    if sex == 1:
        m = cf.dpln_mean(r["alpha"], r["beta"], r["nu"], r["tau"])
        mtxt = "infinite (α≤1)" if not np.isfinite(m) else f"${m:,.0f}"
        return (f"α = {r['alpha']:.3f}   β = {r['beta']:.3f}\n"
                f"ν = {r['nu']:.3f}   τ = {r['tau']:.3f}\n"
                f"E[X] uncapped = {mtxt}")
    m = cf.mix_mean(r["mu1"], r["mu2"], r["sig1"], r["sig2"], r["w"])
    return (f"μ₁ = {r['mu1']:.3f}   σ₁ = {r['sig1']:.3f}\n"
            f"μ₂ = {r['mu2']:.3f}   σ₂ = {r['sig2']:.3f}\n"
            f"w = {r['w']:.3f}\n"
            f"E[X] uncapped = ${m:,.0f}")


def pipeline_row(year, sex, age, params=PARAMS):
    """The fitted cell from the pipeline CSV, as a plain dict. Errors loudly rather than
    silently re-fitting: a cell missing here means it fell below the MIN_N cutoff or the
    year is outside the estimation span, and quietly substituting a different estimator
    would make the figure disagree with everything else in the project."""
    if not params.exists():
        sys.exit(f"{params} not found -- run estimate_cross_sections.py, or pass --refit")
    d = pd.read_csv(params)
    hit = d[(d["year"] == year) & (d["sex"] == sex) & (d["age"] == age)]
    if hit.empty:
        yrs = f"{int(d['year'].min())}-{int(d['year'].max())}"
        sys.exit(f"no fitted cell for year={year} sex={sex} age={age} in {params.name} "
                 f"(estimated years {yrs}; cells under the min-N cutoff are absent). "
                 f"Use --refit to fit this cell standalone.")
    return hit.iloc[0].to_dict()


def plot_cross_section(age=40, cohort=1950, sex=2, refit=False, overlay=False):
    """Plot the (age, cohort, sex) earnings cross-section (year = cohort + age).

    Returns the path of the PDF written under output/cross_sections/."""
    year = cohort + age
    x = cf.load_earnings(year, sex, age=age)
    if x.size == 0:
        sys.exit(f"no EPUF observations for year={year} sex={sex} age={age}")

    if refit or overlay:
        highc_fit = cf.taxmax(year) - cf.HIGH_MARGIN
        fitted = FIT[sex](x, cf.LOWC, highc_fit)
    if refit and not overlay:
        r, highc, src = fitted, highc_fit, "standalone MLE (unsmoothed, unconstrained)"
    else:
        r = pipeline_row(year, sex, age)
        highc = float(r["highc"])
        src = "joint smoothed-constrained solve"

    tlo, thi = np.log(cf.LOWC), np.log(highc)
    y = np.log(x)
    bins = np.linspace(np.log(120), np.log(highc * 1.1), 90)
    yy = np.linspace(bins[0], bins[-1], 800)
    total, comps = fitted_curves(yy, sex, r)

    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.hist(y, bins=bins, density=True, color="0.80", edgecolor="0.6",
            linewidth=0.3, label="raw EPUF data")
    ax.plot(yy, total, color="C3", lw=2.2, label=f"fitted {MODEL_NAME[sex]} — {src}")
    for lab, curve, col in comps:
        ax.plot(yy, curve, color=col, lw=1.3, ls="--", label=lab)
    if overlay:
        alt, _ = fitted_curves(yy, sex, fitted)
        ax.plot(yy, alt, color="C1", lw=1.5, ls="-.", label="standalone MLE (unsmoothed)")
        total = np.maximum(total, alt)
    for t in (tlo, thi):
        ax.axvline(t, color="0.4", lw=1, ls=":")

    # scaled to the fitted density, so the two censoring spikes are deliberately clipped:
    # that mass enters the likelihood as censored, not as density, and letting it set the
    # y-limit would flatten the part of the picture the fit is actually about.
    ax.set_ylim(0, 1.15 * total.max())
    ax.annotate("left-censored\n(≤ $200)", xy=(tlo, ax.get_ylim()[1] * 0.55),
                ha="center", va="top", fontsize=8, color="0.35")
    ax.annotate(f"right-censored\n(≥ ${highc:,.0f})", xy=(thi, ax.get_ylim()[1] * 0.55),
                ha="right", va="top", fontsize=8, color="0.35")

    n_lo = int((x <= cf.LOWC).sum()); n_hi = int((x >= highc).sum())
    box = (param_text(sex, r) +
           f"\ncensored: {n_lo/x.size:.1%} low, {n_hi/x.size:.1%} high")
    ax.text(0.985, 0.97, box, transform=ax.transAxes, ha="right", va="top", fontsize=8.5,
            family="monospace",
            bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="0.7", alpha=0.9))

    ticks = [t for t in (200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 90000)
             if t <= highc]
    ax.set_xticks(np.log(ticks))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${np.exp(v):,.0f}"))
    ax.set_xlabel("annual earnings (log scale)")
    ax.set_ylabel("density (per unit log earnings)")
    ax.set_title(f"cohort {cohort} at age {age} (year {year}), {LABEL[sex]}, N={x.size:,}: "
                 f"raw EPUF data vs fitted {MODEL_NAME[sex]}", fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout()
    stem = f"output/cross_sections/{FILE_TAG[sex]}_c{cohort}_a{age}"
    fig.savefig(stem + ".pdf"); fig.savefig(stem + ".png", dpi=150)
    plt.close(fig)
    print(f"wrote {stem}.pdf and .png")
    return stem + ".pdf"


def _parse_sex(tok):
    key = {"1": 1, "male": 1, "men": 1, "m": 1,
           "2": 2, "female": 2, "women": 2, "f": 2}
    if tok.lower() not in key:
        sys.exit(f"sex must be one of 1/2/male/female, got {tok!r}")
    return key[tok.lower()]


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("age", nargs="?", type=int, default=40)
    p.add_argument("cohort", nargs="?", type=int, default=1950)
    p.add_argument("sex", nargs="?", default="2")
    p.add_argument("--year", type=int, help="set the year directly (cohort = year - age)")
    p.add_argument("--refit", action="store_true",
                   help="fit this cell standalone instead of reading the pipeline CSV")
    p.add_argument("--overlay", action="store_true",
                   help="draw the standalone fit alongside the pipeline one")
    a = p.parse_args()
    cohort = (a.year - a.age) if a.year is not None else a.cohort
    plot_cross_section(a.age, cohort, _parse_sex(a.sex), refit=a.refit, overlay=a.overlay)


if __name__ == "__main__":
    main()
