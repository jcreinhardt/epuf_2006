#!/usr/bin/env python
"""Histogram of 1990 female earnings with the fitted lognormal-mixture density overlaid.

Re-fits the two-component censored MLE (see fit_lognorm_mix_women_1990.py) and plots,
on a log-dollar axis: the raw-data density, the fitted mixture, and its two weighted
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
from scipy.optimize import minimize
import fit_lognorm_mix_women_1990 as M


def fit(x):
    low, high = x <= M.LOWC, x >= M.HIGHC
    inter = ~(low | high)
    yi = np.log(x[inter])
    negll = M.make_negll(yi, int(low.sum()), int(high.sum()))
    m, s = yi.mean(), yi.std()
    best = None
    for w0 in (0.3, 0.5, 0.7):
        for d in (0.4, 0.9):
            ls = np.log(max(0.7 * s - M.SIG_FLOOR, 1e-3))
            theta0 = [m + d * s, m - d * s, ls, ls, np.log(w0 / (1 - w0))]
            res = minimize(negll, theta0, method="L-BFGS-B")
            if best is None or res.fun < best.fun:
                best = res
    mu1, mu2, s1, s2, w = M.unpack(best.x)
    if mu1 < mu2:
        mu1, mu2, s1, s2, w = mu2, mu1, s2, s1, 1 - w
    return mu1, mu2, s1, s2, w


def main():
    x = M.load_earnings()
    mu1, mu2, s1, s2, w = fit(x)
    tlo, thi = np.log(M.LOWC), np.log(M.HIGHC)

    y = np.log(x)
    bins = np.linspace(np.log(120), np.log(55000), 90)
    yy = np.linspace(bins[0], bins[-1], 800)
    c1 = w * np.exp(M.comp_logpdf(yy, mu1, s1))
    c2 = (1 - w) * np.exp(M.comp_logpdf(yy, mu2, s2))

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
    ax.annotate("right-censored\n(>= $50,300)", xy=(thi, ax.get_ylim()[1]*0.92),
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
