#!/usr/bin/env python
"""Histogram of one (age, cohort, sex) earnings cross-section with its fitted density.

Re-fits the censored MLE from crosssec_fit for a single cell -- one birth cohort
observed at one age (so year = cohort + age), one sex -- and plots on a log-dollar
axis: the raw-data density, the fitted model, and -- for the women's mixture --
its two weighted components. Vertical lines mark the $200 / taxmax-$1000 censoring
thresholds; the mass outside them (fit as censored, not as density) shows up as
the two edge spikes.

Men are fit with the double Pareto-lognormal (a single Normal-Laplace density),
women with the two-component lognormal mixture -- the pairing from crosssec_fit.

  python code/cross_sections/plot_cross_section.py [age] [cohort] [sex]
    age defaults to 40, cohort to 1950, sex to 2 (female); sex accepts 1/2 or
    male/female. (age 40, cohort 1950 -> year 1990.)
    -> output/cross_sections/<women_mixture|men_dpln>_c<cohort>_a<age>.pdf (+ .png)
"""
import sys
sys.path.insert(0, "code/cross_sections")
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import crosssec_fit as cf

# per-sex plumbing: fitter, human label, model name, output-file tag
FIT        = {1: cf.fit_dpln, 2: cf.fit_mixture}
LABEL      = {1: "male",      2: "female"}
MODEL_NAME = {1: "double Pareto-lognormal", 2: "lognormal mixture"}
FILE_TAG   = {1: "men_dpln",  2: "women_mixture"}


def comp_density(yy, mu, s):        # normal pdf on the log-earnings axis
    return np.exp(-np.log(s) - 0.5 * cf.LOG2PI - 0.5 * ((yy - mu) / s) ** 2)


def fitted_curves(yy, sex, r):
    """Total fitted density on the log axis, plus any weighted components to draw
    as dashed lines (empty for the single-density dPlN)."""
    if sex == 2:                                            # lognormal mixture
        mu1, mu2, s1, s2, w = r["mu1"], r["mu2"], r["sig1"], r["sig2"], r["w"]
        c1 = w * comp_density(yy, mu1, s1)
        c2 = (1 - w) * comp_density(yy, mu2, s2)
        comps = [(f"upper comp (w={w:.2f}, med ${np.exp(mu1):,.0f})", c1, "C0"),
                 (f"lower comp (w={1-w:.2f}, med ${np.exp(mu2):,.0f})", c2, "C2")]
        return c1 + c2, comps
    dens = np.exp(cf.nl_logpdf(yy, r["alpha"], r["beta"], r["nu"], r["tau"]))  # dPlN
    return dens, []


def plot_cross_section(age=40, cohort=1950, sex=2):
    """Fit and plot the (age, cohort, sex) earnings cross-section (year = cohort + age).

    Returns the path of the PDF written under output/cross_sections/."""
    year = cohort + age
    highc = cf.taxmax(year) - cf.HIGH_MARGIN
    x = cf.load_earnings(year, sex, age=age)
    r = FIT[sex](x, cf.LOWC, highc)
    tlo, thi = np.log(cf.LOWC), np.log(highc)

    y = np.log(x)
    bins = np.linspace(np.log(120), np.log(highc * 1.1), 90)
    yy = np.linspace(bins[0], bins[-1], 800)
    total, comps = fitted_curves(yy, sex, r)

    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.hist(y, bins=bins, density=True, color="0.80", edgecolor="0.6",
            linewidth=0.3, label="raw EPUF data")
    ax.plot(yy, total, color="C3", lw=2.2, label=f"fitted {MODEL_NAME[sex]}")
    for lab, curve, col in comps:
        ax.plot(yy, curve, color=col, lw=1.3, ls="--", label=lab)
    for t in (tlo, thi):
        ax.axvline(t, color="0.4", lw=1, ls=":")

    ax.set_ylim(0, 1.15 * total.max())
    ax.annotate("left-censored\n(<= $200)", xy=(tlo, ax.get_ylim()[1]*0.92),
                ha="center", va="top", fontsize=8, color="0.35")
    ax.annotate(f"right-censored\n(>= ${highc:,.0f})", xy=(thi, ax.get_ylim()[1]*0.92),
                ha="center", va="top", fontsize=8, color="0.35")

    ticks = [t for t in (200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 90000)
             if t <= highc]
    ax.set_xticks(np.log(ticks))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${np.exp(v):,.0f}"))
    ax.set_xlabel("annual earnings (log scale)")
    ax.set_ylabel("density (per unit log earnings)")
    ax.set_title(f"cohort {cohort} at age {age} (year {year}), {LABEL[sex]}, N={x.size:,}: "
                 f"raw EPUF data vs fitted {MODEL_NAME[sex]}")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    pdf = f"output/cross_sections/{FILE_TAG[sex]}_c{cohort}_a{age}.pdf"
    fig.savefig(pdf)
    fig.savefig(f"output/cross_sections/{FILE_TAG[sex]}_c{cohort}_a{age}.png", dpi=150)
    plt.close(fig)
    print(f"wrote {pdf} and .png")
    return pdf


def _parse_sex(tok):
    key = {"1": 1, "male": 1, "men": 1, "m": 1,
           "2": 2, "female": 2, "women": 2, "f": 2}
    if tok.lower() not in key:
        sys.exit(f"sex must be one of 1/2/male/female, got {tok!r}")
    return key[tok.lower()]


if __name__ == "__main__":
    age    = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    cohort = int(sys.argv[2]) if len(sys.argv) > 2 else 1950
    sex    = _parse_sex(sys.argv[3]) if len(sys.argv) > 3 else 2
    plot_cross_section(age, cohort, sex)
