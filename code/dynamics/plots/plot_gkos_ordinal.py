#!/usr/bin/env python
"""Ordinal-transform experiment on the GKOS (2021) benchmark process.

Simulates the process twice with IDENTICAL shock draws (one panel of u from
gcohort_model.simulate_u) under two deterministic profiles:

  g_bench(t) = 2.581 + 0.812 t - 0.185 t^2     (GKOS's own, Table D.III)
  g_flat(t)  = 2.581                           (no lifecycle growth)

Each panel is then ordinally transformed age by age: positive earnings are replaced by the
same-rank quantile of a lognormal target with log-mean g_bench(t) and log-variance rising
linearly from 0.50 at age 25 to 1.10 at age 60 (the within-cohort variance profile of GKOS
Fig. D.3); zeros stay zero.  Because g(t) is a within-age additive constant in logs and
nothing in the process feeds back on the level, within-age ranks are invariant to g, so the
two transformed panels are identical element by element -- asserted -- while the raw
panels' moments differ.  The figures show GKOS-style moments for all four panels.

Run from the project root:  python code/dynamics/plots/plot_gkos_ordinal.py
Output: output/dynamics/plots/gkos_ordinal_transform_moments.{pdf,png}  (2 x 3 panels)
        output/dynamics/plots/gkos_ordinal_slide.{pdf,png}              (slide cut)
"""
import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import norm

sys.path.insert(0, "code/dynamics")          # run from the project root, per repo convention
import gcohort_model as E

OUT = "output/dynamics/plots"
N = 50_000
AGES = np.arange(25, 61)                      # GKOS working span
T = E.tt(AGES)
G_BENCH = E.basis(T, 3) @ E.G_GKOS
G_FLAT = np.full_like(T, E.G_GKOS[0])
TARGET_MU = G_BENCH
TARGET_VAR = 0.50 + (1.10 - 0.50) * (AGES - 25) / (60 - 25)


def earnings(g, u):
    """Levels Y = exp(g(t) + u); a full-year nonemployment spell (u = -inf) is a zero."""
    return np.exp(g[None, :] + u)


def ordinal_transform(Y):
    """Per age: map positive earnings to same-rank lognormal target quantiles."""
    out = np.zeros_like(Y)
    for j in range(AGES.size):
        pos = Y[:, j] > 0
        n = pos.sum()
        ranks = np.empty(n)
        ranks[np.argsort(Y[pos, j], kind="stable")] = np.arange(1, n + 1)
        out[pos, j] = np.exp(TARGET_MU[j] + np.sqrt(TARGET_VAR[j]) * norm.ppf((ranks - 0.5) / n))
    return out


# --- GKOS-style moments -------------------------------------------------------

def growth_by_re(Y, nbins=40):
    """Quantile moments of 5-year log growth by recent-earnings percentile: base ages 30..50,
    RE = mean of the previous 5 years' levels (incl. zeros) ranked within base age, growth
    requires positive earnings at t and t+5."""
    re_pct, dy = [], []
    for j in np.where((AGES >= 30) & (AGES <= 50))[0]:
        re = Y[:, j - 5:j].mean(axis=1)
        ok = (re > 0) & (Y[:, j] > 0) & (Y[:, j + 5] > 0)
        r = np.empty(ok.sum())
        r[np.argsort(re[ok], kind="stable")] = np.arange(ok.sum())
        re_pct.append(np.floor(r / ok.sum() * nbins))
        dy.append(np.log(Y[ok, j + 5]) - np.log(Y[ok, j]))
    re_pct, dy = np.concatenate(re_pct), np.concatenate(dy)
    std, kel, cs = np.full((3, nbins), np.nan)
    for b in range(nbins):
        d = dy[re_pct == b]
        p = np.percentile(d, [2.5, 10, 25, 50, 75, 90, 97.5])
        std[b] = d.std()
        kel[b] = (p[5] + p[1] - 2 * p[3]) / (p[5] - p[1])
        cs[b] = (p[6] - p[0]) / (p[4] - p[2]) - 2.91
    return std, kel, cs


def lifetime_growth(Y, nbins=100):
    """log(avg Y at 51-55 / avg Y at 25-29) by lifetime-earnings percentile bin."""
    order = np.argsort(Y.mean(axis=1), kind="stable")
    lo, hi = np.where(AGES <= 29)[0], np.where((AGES >= 51) & (AGES <= 55))[0]
    out = np.full(nbins, np.nan)
    for b, idx in enumerate(np.array_split(order, nbins)):
        y0, y1 = Y[np.ix_(idx, lo)].mean(), Y[np.ix_(idx, hi)].mean()
        if y0 > 0 and y1 > 0:
            out[b] = np.log(y1) - np.log(y0)
    return out


def all_moments(Y):
    std, kel, cs = growth_by_re(Y)
    pos = [np.log(Y[Y[:, j] > 0, j]) for j in range(AGES.size)]
    return {"logmean": np.array([p.mean() for p in pos]),
            "logvar": np.array([p.var() for p in pos]),
            "std5": std, "kelley5": kel, "cs5": cs, "ltg": lifetime_growth(Y)}


def main():
    os.makedirs(OUT, exist_ok=True)
    u = E.simulate_u(np.random.default_rng(20260807), N, AGES)
    Y_bench, Y_flat = earnings(G_BENCH, u), earnings(G_FLAT, u)
    Yt_bench, Yt_flat = ordinal_transform(Y_bench), ordinal_transform(Y_flat)
    diff = np.abs(Yt_bench - Yt_flat).max()
    print(f"max |transformed(bench) - transformed(flat)| = {diff:.3e}")
    assert diff == 0.0, "transformed panels should be identical"

    mom = {k: all_moments(Y) for k, Y in [("raw bench", Y_bench), ("raw flat", Y_flat),
                                          ("transf bench", Yt_bench), ("transf flat", Yt_flat)]}
    style = {"raw bench": dict(color="0.45", ls="-", lw=2.2),
             "raw flat": dict(color="0.45", ls="--", lw=1.4),
             "transf bench": dict(color="#1f77b4", ls="-", lw=2.6),
             "transf flat": dict(color="#ff7f0e", ls=(0, (2, 3)), lw=1.6)}
    panels = [("logmean", "Mean log earnings by age", AGES, "age"),
              ("logvar", "Within-cohort variance of log earnings", AGES, "age"),
              ("std5", r"Std. dev. of $\Delta^5 \log Y$", None, "RE percentile"),
              ("kelley5", r"Kelley skewness of $\Delta^5 \log Y$", None, "RE percentile"),
              ("cs5", r"Crow-Siddiqui excess kurtosis of $\Delta^5 \log Y$", None, "RE percentile"),
              ("ltg", r"Lifetime growth $\log \bar Y_{51-55} - \log \bar Y_{25-29}$",
               None, "lifetime-earnings percentile")]
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for ax, (key, title, xs, xlab) in zip(axes.ravel(), panels):
        for name, m in mom.items():
            v = m[key]
            ax.plot(xs if xs is not None else np.linspace(0, 100, v.size), v, label=name,
                    **style[name])
        ax.set_title(title, fontsize=10)
        ax.set_xlabel(xlab, fontsize=9)
        ax.tick_params(labelsize=8)
    axes[0, 0].legend(fontsize=8, frameon=False)
    fig.suptitle("GKOS benchmark process, two g(t) profiles, raw vs. ordinally transformed  "
                 f"(transformed panels identical: max diff = {diff:.0e})", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    for ext in ("pdf", "png"):
        fig.savefig(f"{OUT}/gkos_ordinal_transform_moments.{ext}", dpi=200)
    plt.close(fig)

    # Slide cut: one moment the shift moves (the mean) and one it does not own (lifetime
    # growth by lifetime-earnings percentile).
    slide_rc = {"font.size": 14, "axes.titlesize": 16, "axes.labelsize": 14,
                "xtick.labelsize": 13, "ytick.labelsize": 13, "legend.fontsize": 11}
    sstyle = {"raw bench": dict(color="0.55", ls="-", lw=2.0),
              "raw flat": dict(color="0.55", ls="--", lw=1.6),
              "transf bench": dict(color="#2a78d6", ls="-", lw=2.8),
              "transf flat": dict(color="#eb6834", ls=(0, (2, 3)), lw=2.2)}
    with plt.rc_context(slide_rc):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.6, 3.1))
        for name, m in mom.items():
            ax1.plot(AGES, m["logmean"], label=name, **sstyle[name])
            ax2.plot(np.linspace(0, 100, m["ltg"].size), m["ltg"], label=name, **sstyle[name])
        ax1.set_title("Mean log earnings")
        ax1.set_xlabel("age")
        ax2.set_title("Lifetime growth")
        ax2.set_xlabel("lifetime-earnings percentile")
        ax2.legend(frameon=False, loc="lower right")
        fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(f"{OUT}/gkos_ordinal_slide.{ext}", dpi=200)
    print(f"wrote {OUT}/gkos_ordinal_transform_moments and gkos_ordinal_slide .pdf/.png")


if __name__ == "__main__":
    main()
