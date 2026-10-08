#!/usr/bin/env python
"""Employment dynamics, EPUF against the earnings model (`transition_rates.py`): rows = ages 30 / 45 / 55,
columns = men | women, same style as the 2026-10-02 employment figures. One continuous line per source over
rank (exit, persist) or over the earnings change a-h -> a (chg_arc, chg_abs). Bins of fewer than MIN_N people are
not drawn.

Run from the project root:
    python code/dynamics/plots/plot_transition_rates.py [--yob 1932]
Output: output/dynamics/plots/transition_{exit,persist,cumrank,chg_arc,chg_abs}_h{1,5}_yob<YOB>[_basepast].{png,pdf}
"""
import argparse
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DARK, GRID = "#3d3d3d", "#dcdcdc"
STYLE = {"epuf": dict(color="#8a8a8a", marker="o", label="EPUF"),
         "gcohort": dict(color="#D55E00", marker="s", label="GKOS model"),
         "nonemp": dict(color="#0072B2", marker="^", label="New nonemployment model"),
         "sexint": dict(color="#009E73", marker="D", label="GKOS + sex-specific intercept"),
         "sexlag_add": dict(color="#CC79A7", marker="v", label="GKOS + sex + last-year-status intercept"),
         "sexlag": dict(color="#0072B2", marker="P", label="GKOS + sex x last-year-status intercept"),
         "sexlag_abs": dict(color="#56B4E9", marker="X", label="Modified GKOS, linear exit"),
         "sexlag_absq": dict(color="#56B4E9", marker="X", label="Modified GKOS, no alpha term"),
         "sexlag_abs55": dict(color="#56B4E9", marker="X", label="Modified GKOS, exit kink at 55"),
         "absq_alpha": dict(color="#56B4E9", marker="X", label="Modified GKOS"),
         "absq_zcap": dict(color="#56B4E9", marker="X", label="Modified GKOS + cap on z"),
         "absq_alpha_entry": dict(color="#CC79A7", marker="^", label="Modified GKOS + entry margin (ad hoc)"),
         "absq_ten": dict(color="#009E73", marker="D", label="Tenure ramp, no α term"),
         "absq_grad": dict(color="#009E73", marker="D", label="Dummy + tenure gradient, no α term"),
         "absq_hyp": dict(color="#009E73", marker="D", label="Dummy + bounded tenure gradient, no α term"),
         "alpha_grad": dict(color="#CC79A7", marker="v", label="Modified GKOS + tenure gradient")}
SOURCES = ["epuf", "gcohort"]       # main() appends the --new model when estimate_nonemp.py's CSV exists
LW, MS, MIN_N = 2.4, 5.5, 20
plt.rcParams.update({"font.size": 12, "text.color": DARK, "axes.labelcolor": DARK, "axes.edgecolor": DARK,
                     "xtick.color": DARK, "ytick.color": DARK, "axes.titlecolor": DARK})
SEX = {1: "Men", 2: "Women"}
SPEC = {"exit": dict(ylab="Share not employed {h}", rank="current earnings", pop="everybody",
                     xlab="Rank in current earnings (percentile among those employed below the max)"),
        "persist": dict(ylab="Share not employed {h}", rank="cumulative real earnings to date",
                        pop="not employed at that age",
                        xlab="Rank in cumulative real earnings to date (percentile)"),
        "cumrank": dict(ylab="Share not employed {h}", pop="everybody",
                        xlab="Rank in cumulative real earnings to date (percentile)"),
        "chg_arc": dict(ylab="Share not employed {h}", pop="not at zero earnings in both years, not at the taxable max in either",
                        xlab="Earnings change over the previous {hy}, arc-percent"),
        "chg_abs": dict(ylab="Share not employed {h}", pop="not at zero earnings in both years, not at the taxable max in either",
                        xlab="Earnings change over the previous {hy}, real 2013$ (symlog)")}


def fig_one(d, stat, h, yob, out, sfx=""):
    sp = SPEC[stat]
    when = "next year" if h == 1 else f"{h} years later"
    hy = "year" if h == 1 else f"{h} years"
    fig, axes = plt.subplots(3, 2, figsize=(11, 11), sharey=True, sharex=True)
    for i, a in enumerate((30, 45, 55)):
        for k, sex in enumerate((1, 2)):
            ax = axes[i, k]
            for src in SOURCES:
                t = d[(d.stat == stat) & (d.h == h) & (d.sex == sex) & (d.source == src) & (d.age == a)
                      & (d.n >= MIN_N)].sort_values("x")
                if stat in ("exit", "chg_arc"):          # bunched masses / switches: own points, not connected
                    ln = t[t.group == "line"]
                    ax.plot(0.06 + 0.88 * ln.x if stat == "exit" else ln.x, ln.share, lw=LW, ms=MS, **STYLE[src])
                    for g in ("zero", "cap", "out", "in"):
                        pt = t[t.group == g]
                        ax.plot(pt.x, pt.share, ls="none", ms=MS + 2, color=STYLE[src]["color"],
                                marker=STYLE[src]["marker"])
                else:
                    ax.plot(t.x, t.share, lw=LW, ms=MS, **STYLE[src])
            ax.set_title(f"{SEX[sex]}, age {a}", fontsize=13, loc="left")
            ax.set_ylim(-0.02, 1.02)
            ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
            ax.spines[["top", "right"]].set_visible(False)
            ax.set_axisbelow(True)
            ax.yaxis.grid(True, color=GRID, lw=1.0)
            if stat == "exit":
                ax.set_xlim(-0.12, 1.12)
                ax.set_xticks([0, 0.06 + 0.88 * 0.25, 0.5, 0.06 + 0.88 * 0.75, 1.0])
                ax.set_xticklabels(["No earnings\n(not employed)", "25", "50", "75", "At taxable\nmaximum"],
                                   fontsize=9.5)
            elif stat in ("persist", "cumrank"):
                ax.set_xlim(0, 1)
                ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
                ax.set_xticklabels(["0", "25", "50", "75", "100"])
            elif stat == "chg_arc":
                ax.set_xlim(-2.25, 2.25)
                ax.set_xticks([-2, -1, 0, 1, 2])
                ax.set_xticklabels(["-2\n(stopped)", "-1", "0", "1", "+2\n(started)"])
                ax.axvline(0, color=GRID, lw=1.0, zorder=0)
            else:
                ax.set_xscale("symlog", linthresh=250, linscale=0.4)
                ax.set_xlim(-2e5, 2e5)
                ax.set_xticks([-1e5, -1e4, -1e3, 0, 1e3, 1e4, 1e5])
                ax.set_xticklabels(["-100k", "-10k", "-1k", "0", "1k", "10k", "100k"])
                ax.axvline(0, color=GRID, lw=1.0, zorder=0)
            if i == 0 and k == 0:
                ax.legend(frameon=False, loc="best", handlelength=2.4)
        axes[i, 0].set_ylabel(sp["ylab"].format(h=when))
    for ax in axes[-1]:
        ax.set_xlabel(sp["xlab"].format(hy=hy), fontsize=10.5)
    fig.suptitle(f"Born {yob}, {sp['pop']}", x=0.01, ha="left", fontsize=13)
    fig.tight_layout()
    path = out / f"transition_{stat}_h{h}_yob{yob}{sfx}"
    fig.savefig(f"{path}.pdf")
    fig.savefig(f"{path}.png", dpi=150)
    plt.close(fig)
    print(f"wrote {path}.png")


def fig_yrs_hist(d, yob, out, sfx=""):
    """Histogram of the number of years 20-65 with positive earnings, EPUF vs model, men | women."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    for ax, sex in zip(axes, (1, 2)):
        for src in SOURCES:
            t = d[(d.stat == "yrs_hist") & (d.sex == sex) & (d.source == src)].sort_values("x")
            edges = np.append(t.x.to_numpy() - 0.5, t.x.iloc[-1] + 0.5)
            lab = f"{STYLE[src]['label']} (mean {(t.x * t.share).sum():.0f} yrs)"
            if src == "epuf":
                ax.stairs(t.share.to_numpy(), edges, fill=True, color="#c8c8c8", label=lab)
            else:
                ax.stairs(t.share.to_numpy(), edges, color=STYLE[src]["color"], lw=2.6, label=lab)
        ax.set_title(f"{SEX[sex]}, born {yob}", fontsize=13, loc="left")
        ax.set_xlim(0, 47)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color=GRID, lw=1.0)
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        ax.set_xlabel("Years worked, ages 20-65")
        ax.legend(frameon=False, loc="upper left", fontsize=10)
    axes[0].set_ylabel("Share of persons")
    fig.suptitle(f"Born {yob}, everybody with any earnings at 20-65", x=0.01, ha="left", fontsize=13)
    fig.tight_layout()
    path = out / f"transition_yrs_hist_yob{yob}{sfx}"
    fig.savefig(f"{path}.pdf")
    fig.savefig(f"{path}.png", dpi=150)
    plt.close(fig)
    print(f"wrote {path}.png")


def fig_byage(d, yob, out, sfx=""):
    """Share EMPLOYED at each age 20-65, everybody in the base (pooled over the byage_lq quartiles, n-weighted)."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    for ax, sex in zip(axes, (1, 2)):
        for src in SOURCES:
            t = d[(d.stat == "byage_lq") & (d.sex == sex) & (d.source == src)]
            t = t.assign(w=t.share * t.n).groupby("x").agg(w=("w", "sum"), n=("n", "sum"))
            ax.plot(t.index, 1 - t.w / t.n, lw=LW, ms=MS - 2, **STYLE[src])
        ax.set_title(f"{SEX[sex]}, born {yob}", fontsize=13, loc="left")
        ax.set_xlim(19, 66)
        _style(ax)
        ax.set_xlabel("Age")
    axes[0].set_ylabel("Share employed")
    axes[0].legend(frameon=False, loc="best", handlelength=2.4)
    fig.suptitle(f"Born {yob}, everybody with any earnings at 20-65", x=0.01, ha="left", fontsize=13)
    fig.tight_layout()
    path = out / f"transition_byage_yob{yob}{sfx}"
    fig.savefig(f"{path}.pdf")
    fig.savefig(f"{path}.png", dpi=150)
    plt.close(fig)
    print(f"wrote {path}.png")


def fig_lifetime(d, yob, out, sfx=""):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    for ax, sex in zip(axes, (1, 2)):
        for src in SOURCES:
            t = d[(d.stat == "lifetime") & (d.sex == sex) & (d.source == src) & (d.n >= MIN_N)].sort_values("x")
            ax.plot(t.x, 1 - t.share, lw=LW, ms=MS, **STYLE[src])
        ax.set_title(f"{SEX[sex]}, born {yob}", fontsize=13, loc="left")
        ax.set_xlim(0, 1)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_xticklabels(["0", "25", "50", "75", "100"])
        ax.set_ylim(-0.02, 1.02)
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color=GRID, lw=1.0)
        ax.set_xlabel("Rank in real earnings summed over ages 20-65 (percentile)", fontsize=10.5)
    axes[0].set_ylabel("Share of ages 20-65 employed")
    axes[0].legend(frameon=False, loc="best", handlelength=2.4)
    fig.suptitle(f"Born {yob}, everybody with any earnings at 20-65", x=0.01, ha="left", fontsize=13)
    fig.tight_layout()
    path = out / f"transition_lifetime_yob{yob}{sfx}"
    fig.savefig(f"{path}.pdf")
    fig.savefig(f"{path}.png", dpi=150)
    plt.close(fig)
    print(f"wrote {path}.png")


def _style(ax):
    ax.set_ylim(-0.02, 1.02)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=GRID, lw=1.0)


def fig_fwd(d, yob, out, sfx=""):
    """Share of the remaining ages a+1..65 not employed, against cumulative real earnings rank at a."""
    fig, axes = plt.subplots(3, 2, figsize=(11, 11), sharey=True, sharex=True)
    for i, a in enumerate((30, 45, 55)):
        for k, sex in enumerate((1, 2)):
            ax = axes[i, k]
            for src in SOURCES:
                t = d[(d.stat == "fwd") & (d.sex == sex) & (d.source == src) & (d.age == a)
                      & (d.n >= MIN_N)].sort_values("x")
                ax.plot(t.x, t.share, lw=LW, ms=MS, **STYLE[src])
            ax.set_title(f"{SEX[sex]}, age {a}: share of ages {a + 1}-65 not employed", fontsize=12, loc="left")
            ax.set_xlim(0, 1)
            ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
            ax.set_xticklabels(["0", "25", "50", "75", "100"])
            _style(ax)
            if i == 0 and k == 0:
                ax.legend(frameon=False, loc="best", handlelength=2.4)
        axes[i, 0].set_ylabel("Share of remaining years not employed")
    for ax in axes[-1]:
        ax.set_xlabel("Rank in cumulative real earnings, ages 20 to a (percentile)", fontsize=10.5)
    fig.suptitle(f"Born {yob}, everybody", x=0.01, ha="left", fontsize=13)
    fig.tight_layout()
    path = out / f"transition_fwd_yob{yob}{sfx}"
    fig.savefig(f"{path}.pdf")
    fig.savefig(f"{path}.png", dpi=150)
    plt.close(fig)
    print(f"wrote {path}.png")


DEC = {"exit": ("o", "never employed again by 60"), "again": ("^", "employed again at least one year by 60")}


def fig_fwd_dec(d, yob, out, sfx=""):
    """Share of ages a+1..60 not employed, split by whether the person exits for good, re-enters weakly or strongly."""
    from matplotlib.lines import Line2D
    fig, axes = plt.subplots(3, 2, figsize=(11, 11.5), sharey=True, sharex=True)
    for i, a in enumerate((30, 45, 55)):
        for k, sex in enumerate((1, 2)):
            ax = axes[i, k]
            for src in SOURCES:
                c = STYLE[src]["color"]
                t = d[(d.stat == "fwd_dec") & (d.sex == sex) & (d.source == src) & (d.age == a)]
                for g, (mk, _) in DEC.items():
                    u = t[t.group == g].sort_values("x")
                    ax.plot(u.x, u.share, lw=LW - 0.8, ms=MS, marker=mk, color=c, mfc=c if src == "epuf" else "white")
            ax.set_title(f"{SEX[sex]}, age {a}: ages {a + 1}-60", fontsize=12, loc="left")
            ax.set_xlim(0, 1)
            ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
            ax.set_xticklabels(["0", "25", "50", "75", "100"])
            _style(ax)
        axes[i, 0].set_ylabel("Share of remaining years not employed")
    hs = [Line2D([], [], color=STYLE[s]["color"], lw=LW - 0.8, label=STYLE[s]["label"]) for s in SOURCES]
    hs += [Line2D([], [], color=DARK, ls="none", marker=mk, ms=MS, label=lab) for mk, lab in DEC.values()]
    axes[0, 0].legend(handles=hs, frameon=False, loc="upper right", fontsize=9.5)
    for ax in axes[-1]:
        ax.set_xlabel("Rank in cumulative real earnings, ages 20 to a (percentile)", fontsize=10.5)
    fig.suptitle(f"Born {yob}; non-employed years a+1..60 split by later employment (the two parts sum to the total)",
                 x=0.01, ha="left", fontsize=12.5)
    fig.tight_layout()
    path = out / f"transition_fwd_dec_yob{yob}{sfx}"
    fig.savefig(f"{path}.pdf")
    fig.savefig(f"{path}.png", dpi=150)
    plt.close(fig)
    print(f"wrote {path}.png")


def fig_byage_lq(d, yob, out, sfx="", stat="byage_lq"):
    """By age, one panel per lifetime-earnings quartile (rows) and sex (columns): share not employed (byage_lq) or
    mean number of future entries + exits between a and 65 (trans_fut_lq)."""
    ylab = {"byage_lq": "Share not employed", "trans_fut_lq": "Entries + exits, age a to 65"}[stat]
    fig, axes = plt.subplots(4, 2, figsize=(11, 13.5), sharey=True, sharex=True)
    for i in range(4):
        for k, sex in enumerate((1, 2)):
            ax = axes[i, k]
            for src in SOURCES:
                t = d[(d.stat == stat) & (d.group == f"q{i + 1}") & (d.sex == sex)
                      & (d.source == src)].sort_values("x")
                ax.plot(t.x, t.share, lw=LW, ms=MS - 2, **STYLE[src])
            ax.set_title(f"{SEX[sex]}, lifetime-earnings quartile {i + 1}", fontsize=12, loc="left")
            ax.set_xlim(19, 66)
            _style(ax)
            if stat == "trans_fut_lq":
                ax.set_ylim(0, 7.5)
                ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}")
            if i == 0 and k == 0:
                ax.legend(frameon=False, loc="best", handlelength=2.4)
        axes[i, 0].set_ylabel(ylab)
    for ax in axes[-1]:
        ax.set_xlabel("Age")
    fig.suptitle(f"Born {yob}; quartiles of real earnings summed over ages 20-65 (Q1 = lowest)",
                 x=0.01, ha="left", fontsize=13)
    fig.tight_layout()
    path = out / f"transition_{stat}_yob{yob}{sfx}"
    fig.savefig(f"{path}.pdf")
    fig.savefig(f"{path}.png", dpi=150)
    plt.close(fig)
    print(f"wrote {path}.png")


EVT = {"drop": "drop, arc-percent change in (-2, -1]", "rise": "rise, arc-percent change in [1, 2)"}


def fig_evt_after(d, yob, out, sfx=""):
    """EPUF only (the model has almost no such events): what follows a large interior change at a <= 60."""
    lines = (("evt_next", "-", "o", "employed at a+1"),
             ("evt_next5", "--", "s", "share of years a+1..a+5 employed"),
             ("evt_none5", ":", "^", "employed in none of a+1..a+5"))
    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5), sharex=True, sharey=True)
    for i, g in enumerate(("drop", "rise")):
        for k, sex in enumerate((1, 2)):
            ax = axes[i, k]
            for stat, ls, mk, lab in lines:
                t = d[(d.stat == stat) & (d.group == g) & (d.sex == sex) & (d.source == "epuf")
                      & (d.age <= 60)].sort_values("x")
                ax.plot(t.x, t.share, ls=ls, marker=mk, lw=LW - 0.6, ms=MS - 2, color=DARK, label=lab)
            ax.set_title(f"{SEX[sex]}: one-year {EVT[g]}", fontsize=11.5, loc="left")
            ax.set_xlim(20, 61)
            _style(ax)
            if i == 1 and k == 0:
                ax.legend(frameon=False, loc="center left", fontsize=10, handlelength=2.6)
        axes[i, 0].set_ylabel("Share", fontsize=10.5)
    for ax in axes[-1]:
        ax.set_xlabel("Age at the change (age a, change from a-1 to a)")
    fig.suptitle(f"EPUF, born {yob}; nobody at the taxable max in either year; ages with 5 observed years after",
                 x=0.01, ha="left", fontsize=12.5)
    fig.tight_layout()
    path = out / f"transition_evt_next_yob{yob}{sfx}"
    fig.savefig(f"{path}.pdf")
    fig.savefig(f"{path}.png", dpi=150)
    plt.close(fig)
    print(f"wrote {path}.png")


TRANS = {"trans_cum": "Rank in cumulative real earnings, ages 20 to a (percentile)",
         "trans_cur": "Rank in current earnings at a\n(percentile among those employed below the max)"}


def _trans_panel(ax, d, stat, sex, a, cur):
    """Entries + exits as ONE count per person (both are on the same bins, so they add). With `cur`, the not
    employed (x=0) and the earners at the taxable max (x=1) are separate unconnected points."""
    for src in SOURCES:
        t = d[(d.stat == stat) & (d.sex == sex) & (d.source == src) & (d.age == a) & (d.n >= MIN_N)]
        g = t.group.str.split(":").str[1]
        ln = t[g == "line"].groupby("x").share.sum()
        ax.plot(0.06 + 0.88 * ln.index if cur else ln.index, ln.values, lw=LW, ms=MS, **STYLE[src])
        if cur:
            for grp in ("zero", "cap"):
                pt = t[g == grp].groupby("x").share.sum()
                ax.plot(pt.index, pt.values, ls="none", ms=MS + 2, color=STYLE[src]["color"],
                        marker=STYLE[src]["marker"])


def _trans_axes(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=GRID, lw=1.0)


def _ylim_from_zero(axes):
    """Shared y from 0 to the largest value drawn in ANY panel (set_ylim inside the loop freezes the top)."""
    top = max(l.get_ydata().max() for ax in axes.flat for l in ax.get_lines() if len(l.get_ydata()))
    axes.flat[0].set_ylim(0, 1.05 * top)


def fig_trans(d, stat, yob, out, sfx=""):
    cur = stat == "trans_cur"
    fig, axes = plt.subplots(3, 2, figsize=(11, 11), sharey=True, sharex=True)
    for i, a in enumerate((30, 45, 55)):
        for k, sex in enumerate((1, 2)):
            ax = axes[i, k]
            _trans_panel(ax, d, stat, sex, a, cur)
            ax.set_title(f"{SEX[sex]}, age {a}: transitions over ages {a}-65", fontsize=12, loc="left")
            _trans_axes(ax)
            if cur:
                ax.set_xlim(-0.12, 1.12)
                ax.set_xticks([0, 0.06 + 0.88 * 0.25, 0.5, 0.06 + 0.88 * 0.75, 1.0])
                ax.set_xticklabels(["No earnings\n(not employed)", "25", "50", "75", "At taxable\nmaximum"],
                                   fontsize=9.5)
            else:
                ax.set_xlim(0, 1)
                ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
                ax.set_xticklabels(["0", "25", "50", "75", "100"])
            if i == 0 and k == 0:
                ax.legend(frameon=False, loc="best", handlelength=2.4)
        axes[i, 0].set_ylabel("Entries + exits per person")
    _ylim_from_zero(axes)
    for ax in axes[-1]:
        ax.set_xlabel(TRANS[stat], fontsize=10.5)
    fig.suptitle(f"Born {yob}; entries (0 -> employed) and exits (employed -> 0) counted together",
                 x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    path = out / f"transition_{stat}_yob{yob}{sfx}"
    fig.savefig(f"{path}.pdf")
    fig.savefig(f"{path}.png", dpi=150)
    plt.close(fig)
    print(f"wrote {path}.png")


def fig_trans_life(d, yob, out, sfx=""):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    for ax, sex in zip(axes, (1, 2)):
        _trans_panel(ax, d, "trans_life", sex, 65, False)
        ax.set_title(f"{SEX[sex]}, born {yob}", fontsize=13, loc="left")
        ax.set_xlim(0, 1)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_xticklabels(["0", "25", "50", "75", "100"])
        _trans_axes(ax)
        ax.set_xlabel("Rank in real earnings summed over ages 20-65 (percentile)", fontsize=10.5)
    axes[0].set_ylabel("Entries + exits per person, ages 20-65")
    _ylim_from_zero(axes)
    axes[0].legend(frameon=False, loc="best", handlelength=2.4)
    fig.suptitle(f"Born {yob}; entries and exits counted together", x=0.01, ha="left", fontsize=13)
    fig.tight_layout()
    path = out / f"transition_trans_life_yob{yob}{sfx}"
    fig.savefig(f"{path}.pdf")
    fig.savefig(f"{path}.png", dpi=150)
    plt.close(fig)
    print(f"wrote {path}.png")


def fig_events(d, yob, out, sfx=""):
    """Large interior one-year changes by age: incidence (evt_age)."""
    for stat, ylab, fmt in (("evt_age", "Share of people with such a change at this age", "{v:.1%}"),):
        fig, axes = plt.subplots(2, 2, figsize=(11, 8.5), sharex=True, sharey=(stat == "evt_next"))
        for i, g in enumerate(("drop", "rise")):
            for k, sex in enumerate((1, 2)):
                ax = axes[i, k]
                for src in SOURCES:
                    t = d[(d.stat == stat) & (d.group == g) & (d.sex == sex) & (d.source == src)].sort_values("x")
                    if stat == "evt_next":
                        t = t[t.n >= MIN_N]
                    if stat == "evt_age":
                        ax.step(t.x, t.share, where="mid", lw=LW - 0.4, color=STYLE[src]["color"],
                                label=STYLE[src]["label"])
                    else:
                        ax.plot(t.x, t.share, lw=LW, ms=MS - 2, **STYLE[src])
                ax.set_title(f"{SEX[sex]}: one-year {EVT[g]}", fontsize=11.5, loc="left")
                ax.set_xlim(20, 65)
                ax.spines[["top", "right"]].set_visible(False)
                ax.set_axisbelow(True)
                ax.yaxis.grid(True, color=GRID, lw=1.0)
                ax.yaxis.set_major_formatter(lambda v, _, f=fmt: f.format(v=v))
                if stat == "evt_age":
                    ax.set_ylim(bottom=0)
                else:
                    ax.set_ylim(-0.02, 1.02)
                if i == 0 and k == 0:
                    ax.legend(frameon=False, loc="best", handlelength=2.4)
            axes[i, 0].set_ylabel(ylab, fontsize=10.5)
        for ax in axes[-1]:
            ax.set_xlabel("Age at the change (age a, change from a-1 to a)")
        fig.suptitle(f"Born {yob}; nobody at the taxable max in either year", x=0.01, ha="left", fontsize=13)
        fig.tight_layout()
        path = out / f"transition_{stat}_yob{yob}{sfx}"
        fig.savefig(f"{path}.pdf")
        fig.savefig(f"{path}.png", dpi=150)
        plt.close(fig)
        print(f"wrote {path}.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yob", type=int, default=1932)
    ap.add_argument("--base", default="window", choices=("window", "past"))
    ap.add_argument("--no-mortality", action="store_true", help="plot the _nomort CSV")
    ap.add_argument("--new", default="none", choices=("nonemp", "sexint", "sexlag_add", "sexlag", "sexlag_abs", "sexlag_absq", "sexlag_abs55", "absq_alpha",
                             "absq_zcap", "absq_alpha_entry", "absq_ten", "absq_grad", "absq_hyp", "alpha_grad", "none"),
                    help="third line: an estimate_nonemp.py spec (figures get the suffix _<spec>, except the "
                         "12-parameter nonemp), or none")
    args = ap.parse_args()
    sfx = ("" if args.base == "window" else "_basepast") + ("_nomort" if args.no_mortality else "")
    d = pd.read_csv(f"output/dynamics/transition_rates_yob{args.yob}{sfx}.csv")
    new = Path(f"output/dynamics/transition_rates_yob{args.yob}_{args.new}.csv")
    if args.new != "none" and new.exists() and not sfx:
        d = pd.concat([d, pd.read_csv(new)], ignore_index=True)
        SOURCES.append(args.new)
        if args.new != "nonemp":
            sfx = f"_{args.new}"
    out = Path("output/dynamics/plots")
    out.mkdir(parents=True, exist_ok=True)
    for stat in ("exit", "persist", "cumrank", "chg_arc", "chg_abs"):
        for h in (1, 5):
            fig_one(d, stat, h, args.yob, out, sfx)
    fig_lifetime(d, args.yob, out, sfx)
    fig_byage(d, args.yob, out, sfx)
    fig_yrs_hist(d, args.yob, out, sfx)
    fig_fwd(d, args.yob, out, sfx)
    fig_byage_lq(d, args.yob, out, sfx)
    fig_byage_lq(d, args.yob, out, sfx, stat="trans_fut_lq")
    fig_fwd_dec(d, args.yob, out, sfx)
    fig_events(d, args.yob, out, sfx)
    fig_evt_after(d, args.yob, out, sfx)
    fig_trans(d, "trans_cum", args.yob, out, sfx)
    fig_trans(d, "trans_cur", args.yob, out, sfx)
    fig_trans_life(d, args.yob, out, sfx)


if __name__ == "__main__":
    main()
