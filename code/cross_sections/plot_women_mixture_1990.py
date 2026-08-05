#!/usr/bin/env python
"""Histogram of 1990 female earnings with the fitted lognormal-mixture density overlaid.

Re-fits the two-component censored MLE (crosssec_fit.fit_mixture) and plots, on a
log-dollar axis: the raw-data density, the fitted mixture, and its two weighted
components. Vertical lines mark the $200 / $50,300 censoring thresholds; the mass
outside them (fit as censored, not as density) shows up as the two edge spikes.
Writes output/cross_sections/women_mixture_1990.pdf.
"""
import sys
sys.path.insert(0, "code/cross_sections")
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import crosssec_fit as cf

YEAR, SEX = 1990, 2


def comp_density(yy, mu, s):        # normal pdf on the log-earnings axis
    return np.exp(-np.log(s) - 0.5 * cf.LOG2PI - 0.5 * ((yy - mu) / s) ** 2)


def main():
    highc = cf.taxmax(YEAR) - cf.HIGH_MARGIN
    x = cf.load_earnings(YEAR, SEX)
    r = cf.fit_mixture(x, cf.LOWC, highc)
    mu1, mu2, s1, s2, w = r["mu1"], r["mu2"], r["sig1"], r["sig2"], r["w"]
    tlo, thi = np.log(cf.LOWC), np.log(highc)

    y = np.log(x)
    bins = np.linspace(np.log(120), np.log(55000), 90)
    yy = np.linspace(bins[0], bins[-1], 800)
    c1 = w * comp_density(yy, mu1, s1)
    c2 = (1 - w) * comp_density(yy, mu2, s2)

    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.hist(y, bins=bins, density=True, color="0.80", edgecolor="0.6",
            linewidth=0.3, label="raw EPUF data")
    ax.plot(yy, c1 + c2, color="C3", lw=2.2, label="fitted mixture")
    ax.plot(yy, c1, color="C0", lw=1.3, ls="--",
            label=f"upper comp (w={w:.2f}, med ${np.exp(mu1):,.0f})")
    ax.plot(yy, c2, color="C2", lw=1.3, ls="--",
            label=f"lower comp (w={1-w:.2f}, med ${np.exp(mu2):,.0f})")
    for t in (tlo, thi):
        ax.axvline(t, color="0.4", lw=1, ls=":")

    ax.set_ylim(0, 1.15 * (c1 + c2).max())
    ax.annotate("left-censored\n(<= $200)", xy=(tlo, ax.get_ylim()[1]*0.92),
                ha="center", va="top", fontsize=8, color="0.35")
    ax.annotate(f"right-censored\n(>= ${highc:,.0f})", xy=(thi, ax.get_ylim()[1]*0.92),
                ha="center", va="top", fontsize=8, color="0.35")

    ticks = [200, 500, 1000, 2000, 5000, 10000, 20000, 50000]
    ax.set_xticks(np.log(ticks))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${np.exp(v):,.0f}"))
    ax.set_xlabel("annual earnings (log scale)")
    ax.set_ylabel("density (per unit log earnings)")
    ax.set_title("1990 female earnings: raw EPUF data vs fitted lognormal mixture")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig("output/cross_sections/women_mixture_1990.pdf")
    fig.savefig("output/cross_sections/women_mixture_1990.png", dpi=150)
    print("wrote output/cross_sections/women_mixture_1990.pdf and .png")


if __name__ == "__main__":
    main()
