#!/usr/bin/env python
"""GKOS (2021) Figure 12 -- "estimated model versus data: key moments" -- on one EPUF cohort, one figure per sex:
EPUF, the GKOS process (+ mortality) and the modified nonemployment model on the same six panels
(`gkos_moments.py` computes the statistics; this only draws them).

  (a) standard deviation, (b) skewness, (c) kurtosis of the five-year arc-percent change by recent-earnings
      percentile (13 GKOS groups, averaged over the six 5-year age bins 25-54);
  (d) log average earnings growth 25 -> 55 by lifetime-earnings group (15 GKOS groups);
  (e) CDF of total years employed over 25-60;
  (f) within-cohort variance of log earnings by age.

A second figure, gkos_logy_moments_*, is the lifecycle of the cross-sectional moments of log earnings among
workers (mean, sd, skewness, kurtosis by age 20-65, both sexes), the capped counterpart of GKSW's moments.

Run from the project root:
    python code/dynamics/plots/plot_gkos_fig12.py [--yob 1937] [--spec absq_alpha]
Output: output/dynamics/plots/gkos_fig12_{men,women}_yob<YOB>_<spec>.{png,pdf}
        output/dynamics/plots/gkos_logy_moments_yob<YOB>_<spec>.{png,pdf}
"""
import argparse
import os

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PROJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUT = os.path.join(PROJ, "output", "dynamics", "plots")
DARK, GRID = "#3d3d3d", "#dcdcdc"
# the same encoding as plot_transition_rates.STYLE (copied, not imported: one plot script should not load another)
STYLE = {"epuf": dict(color="#8a8a8a", marker="o", label="EPUF"),
         "gcohort": dict(color="#D55E00", marker="s", label="GKOS model"),
         "model": dict(color="#56B4E9", marker="X", label="Modified GKOS")}
SEX = {1: "men", 2: "women"}
PANELS = [("arc_sd", "(a) Standard deviation", "percentile of recent earnings", "sd of 2(Y$_{t+5}$−Y$_t$)/(Y$_{t+5}$+Y$_t$)"),
          ("arc_skew", "(b) Skewness", "percentile of recent earnings", "skewness of 2(Y$_{t+5}$−Y$_t$)/(Y$_{t+5}$+Y$_t$)"),
          ("arc_kurt", "(c) Kurtosis", "percentile of recent earnings", "kurtosis of 2(Y$_{t+5}$−Y$_t$)/(Y$_{t+5}$+Y$_t$)"),
          ("le_growth", "(d) Lifecycle earnings growth", "percentile of lifetime earnings",
           "log average earnings growth, age 25 to 55"),
          ("emp_cdf", "(e) Lifetime nonemployment distribution", "total years employed, ages 25–60", "employment CDF"),
          ("var_log", "(f) Variance of log earnings", "age", "within-cohort variance of log earnings")]


def draw(d, sex, spec, title, note):
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 8.4))
    for ax, (panel, ttl, xl, yl) in zip(axes.ravel(), PANELS):
        p = d[(d.panel == panel) & (d.sex == sex)]
        for src in ("epuf", "gcohort", spec):
            s = p[p.source == src].sort_values("x")
            st = STYLE["model"] if src == spec else STYLE[src]
            ax.plot(s.x, s.value, color=st["color"], marker=st["marker"], ms=4 if panel != "emp_cdf" else 3,
                    lw=1.6 if src == "epuf" else 1.3, label=st["label"], zorder=3 if src == "epuf" else 2)
        if panel == "le_growth":
            ax.axhline(0, color=DARK, lw=0.8, ls="--")
        if panel == "emp_cdf":
            ax.set_ylim(0, 1)
        ax.set_title(ttl, fontsize=11, loc="left", color=DARK)
        ax.set_xlabel(xl, fontsize=9, color=DARK)
        ax.set_ylabel(yl, fontsize=9, color=DARK)
        ax.grid(True, color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.tick_params(labelsize=8.5, colors=DARK)
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, frameon=False, fontsize=10, bbox_to_anchor=(0.5, 0.0))
    fig.text(0.01, 0.985, title, fontsize=12.5, color=DARK, ha="left", va="top")
    fig.text(0.01, 0.958, note, fontsize=9.5, color="#6a6a6a", ha="left", va="top", linespacing=1.4)
    fig.tight_layout(rect=(0, 0.05, 1, 0.915))
    return fig


MOMENTS = [("logy_mean", "mean of log earnings (2013$)"), ("logy_sd", "sd of log earnings"),
           ("logy_skew", "skewness of log earnings"), ("logy_kurt", "kurtosis of log earnings")]


def draw_logy(d, spec, yob, cap):
    fig, axes = plt.subplots(2, 4, figsize=(15, 7.2))
    for r, sex in enumerate((1, 2)):
        for c, (panel, yl) in enumerate(MOMENTS):
            ax = axes[r, c]
            p = d[(d.panel == panel) & (d.sex == sex)]
            for src in ("epuf", "gcohort", spec):
                s = p[p.source == src].sort_values("x")
                st = STYLE["model"] if src == spec else STYLE[src]
                ax.plot(s.x, s.value, color=st["color"], marker=st["marker"], ms=3, lw=1.5 if src == "epuf" else 1.2,
                        label=st["label"], zorder=3 if src == "epuf" else 2)
            ax.set_title(f"{SEX[sex].capitalize()}: {yl}", fontsize=10.5, loc="left", color=DARK)
            ax.set_xlabel("age", fontsize=9, color=DARK)
            ax.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            ax.tick_params(labelsize=8.5, colors=DARK)
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, frameon=False, fontsize=10, bbox_to_anchor=(0.5, 0.0))
    fig.text(0.01, 0.985, f"Cross-sectional moments of log earnings among workers by age, EPUF {yob} cohort",
             fontsize=12.5, color=DARK, ha="left", va="top")
    fig.text(0.01, 0.958, "Among earnings at or above GKOS's minimum threshold; all three series capped at the taxable maximum "
             f"(EPUF men at the cap: {cap[25]:.0%} at 25, {cap[35]:.0%} at 35, {cap[45]:.0%} at 45, {cap[55]:.0%} at 55).",
             fontsize=9.5, color="#6a6a6a", ha="left", va="top")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    return fig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yob", type=int, default=1937)
    ap.add_argument("--spec", default="absq_alpha")
    a = ap.parse_args()
    d = pd.read_csv(os.path.join(PROJ, "output", "dynamics", f"gkos_fig12_yob{a.yob}_{a.spec}.csv"))
    os.makedirs(OUT, exist_ok=True)
    cap = d[(d.panel == "cap_share") & (d.source == "epuf")]
    for sex in (1, 2):
        c = cap[cap.sex == sex].set_index("age").value
        title = f"GKOS (2021) Figure 12 on the EPUF {a.yob} cohort, {SEX[sex]}"
        note = (f"All three series are capped at the taxable maximum, the models through EPUF's disclosure rule; "
                f"EPUF share at the cap: {c[25]:.0%} at 25, {c[35]:.0%} at 35, {c[45]:.0%} at 45, {c[55]:.0%} at 55.\n"
                f"(a)–(c): five-year changes, ages 25–54 at t−1 pooled; (d), (e): GKOS's lifetime-earnings samples, "
                f"ages 25–60; (f): among earnings at or above GKOS's minimum threshold.")
        fig = draw(d, sex, a.spec, title, note)
        stem = os.path.join(OUT, f"gkos_fig12_{SEX[sex]}_yob{a.yob}_{a.spec}")
        fig.savefig(stem + ".png", dpi=170)
        fig.savefig(stem + ".pdf")
        plt.close(fig)
        print("wrote", stem + ".png")
    if (d.panel == "logy_mean").any():
        c = cap[cap.sex == 1].set_index("age").value
        fig = draw_logy(d, a.spec, a.yob, c)
        stem = os.path.join(OUT, f"gkos_logy_moments_yob{a.yob}_{a.spec}")
        fig.savefig(stem + ".png", dpi=170); fig.savefig(stem + ".pdf"); plt.close(fig)
        print("wrote", stem + ".png")


if __name__ == "__main__":
    main()
