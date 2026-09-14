#!/usr/bin/env python
"""The SMOOTH_FRAC calibration curve: held-out likelihood against smoothing strength.

Reads calibrate_smooth_frac.py's two CSVs -- the per-(fold, frac) summary and the per-year
held-out detail -- and checks that the detail reproduces the summary before drawing anything.

WHY THE CURVE IS SPLIT BY ERA. 1957-2006 is the pre-registered window; the adopted SMOOTH_FRAC
was read on 1980-2006, and estimate_cross_sections.py records why the two differ and which was
taken (the constraint's Jensen ceiling decided it). MEASURED on the first grid points: the total over every year is
dominated by 1951-56, six years holding 6% of the held-out observations, in which men's upper
tail alpha is unidentified under a cap 70-75% of prime-age men exceed. Stage-0 basins there sit
0.2 nats apart (5-10 nats later) while disagreeing on log alpha by up to 6; the roughness
penalty spends ~half its budget pulling those arbitrary alphas together, and through the dPlN's
coupling that moves S(cap), which the censored likelihood weighs heavily. So in those years the
held-out number measures how arbitrary alpha is, not the bias-variance trade the criterion exists
to price -- light smoothing lost +284 nats per million held-out obs there while winning 24 of 27
years after 1980. 1951-56 also carry no GKSW targets and eta ~ 8. The fix for those years is
CLAUDE.md open item 3 (men's tail slot as a functional, not raw log alpha), not a criterion.

TOP, side by side on one shared y-axis: held-out negll of each fold's test half above that
fold's best grid point (gray), and the two folds summed (accent) -- LEFT over 1957-2006, the
pre-registered window; RIGHT over 1980-2006, the least-censored years. Each rings its own rule
pick (the smallest fraction within the folds' noise band). The ADOPTED value is drawn as its own
accent line, read from estimate_cross_sections.SMOOTH_FRAC, so the figure cannot drift from what
production uses. BOTTOM, one measure per panel on the same x-axis: rho0, men's log-alpha
roughness, years left at eta = 0, the in-sample uncapped ratio, the GKSW criterion Sum n Q, and
how many 1980-2006 years prefer each fraction to no smoothing at all.

smooth_frac = 0 has no place on a log axis: it is an unconnected marker one step left of the
smallest positive fraction, behind a break glyph drawn on the spine only. The top y-axis is
symlog, because the best point is 0 by construction and the grid's ends can sit orders of
magnitude above it.

Run from the project root:
    python code/cross_sections/plots/plot_smooth_frac_calibration.py [--csv CSV] [--by-year CSV] [--out STEM]
Output: output/cross_sections/plots/smooth_frac_calibration.{png,pdf}
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, NullLocator

sys.path.insert(0, "code/cross_sections")    # run from the project root, per repo convention
from calibrate_smooth_frac import DECIDE_FROM, INFORMATIVE_FROM, decide   # noqa: E402 -- ONE definition
from estimate_cross_sections import SMOOTH_FRAC as ADOPTED                  # noqa: E402 -- what production uses

CSV = "output/cross_sections/smooth_frac_calibration.csv"
BY_YEAR = "output/cross_sections/smooth_frac_calibration_by_year.csv"
OUT = "output/cross_sections/plots/smooth_frac_calibration"
PREVIOUS = 1e-4                     # the fraction this calibration replaced, marked for context

# Validated (dataviz validate_palette.py, light, on SURFACE): the accent passes every categorical
# check; the de-emphasis gray clears 3:1 as a mark (3.50:1). Text never wears the accent.
SURFACE, ACCENT, GRAY = "#fcfcfb", "#2a78d6", "#898781"
INK, INK2, GRID, AXIS = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7"


def xpos(fracs):
    """Map fractions to plotted x: positives as they are, 0 one grid step left of the smallest."""
    pos = sorted(f for f in fracs if f > 0)
    zero_at = pos[0] / 10 ** 0.75 if pos else 1e-6
    return {f: (f if f > 0 else zero_at) for f in fracs}, zero_at, pos


def style(ax, zero_at, pos, has_zero):
    ax.set_facecolor(SURFACE)
    ax.set_xscale("log")
    ticks = ([zero_at] if has_zero else []) + [p for p in pos if np.isclose(np.log10(p) % 1, 0)]
    ax.set_xticks(ticks, ["0" if t == zero_at else f"{t:.0e}".replace("e-0", "e-") for t in ticks])
    ax.xaxis.set_minor_locator(NullLocator())
    ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
    ax.tick_params(colors=GRAY, labelcolor=INK2, labelsize=8, length=3)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
        ax.spines[side].set_linewidth(0.6)
    lo = zero_at if has_zero else (pos[0] if pos else 1e-6)
    ax.set_xlim(lo / 10 ** 0.35, (pos[-1] if pos else 1) * 10 ** 0.35)
    if has_zero and pos:
        # The break lives ON THE SPINE and nowhere else: nothing is painted over the plot area.
        xb, tr = np.sqrt(zero_at * pos[0]), ax.get_xaxis_transform()
        w = 10 ** 0.045
        ax.plot([xb / w, xb * w], [0, 0], transform=tr, color=SURFACE, lw=2.4, zorder=6,
                clip_on=False, solid_capstyle="butt")
        for dx in (1 / w, w):
            ax.plot([xb * dx / 10 ** 0.02, xb * dx * 10 ** 0.02], [-0.018, 0.018], transform=tr,
                    color=AXIS, lw=0.8, zorder=7, clip_on=False)


def series(ax, fracs, y, X, accent, log=False):
    """A line across the POSITIVE fractions only; smooth_frac = 0 is an unconnected marker. On
    a log y-axis non-positive values are dropped rather than sent to -inf."""
    fr, y = np.asarray(fracs, float), np.asarray(y, float)
    ok = np.isfinite(y) & (y > 0 if log else np.ones_like(y, bool))
    kw = dict(color=ACCENT, lw=1.8, zorder=3) if accent else dict(color=GRAY, lw=1.0, zorder=2)
    mk = dict(marker="o", ms=5 if accent else 3.5, mec=SURFACE, mew=0.8)
    p = ok & (fr > 0)
    ax.plot([X[f] for f in fr[p]], y[p], **kw, **mk)
    z = ok & (fr == 0)
    if z.any():
        ax.plot([X[0.0]], y[z][:1], linestyle="none", color=kw["color"], zorder=kw["zorder"], **mk)


def criterion(by, years):
    """Held-out negll over `years`: each fold and the fold sum, each above its own best point."""
    w = by[by.year.isin(years)].groupby(["smooth_frac", "fold"]).heldout_negll.sum().unstack("fold")
    per_fold = w - w.min()
    both = w.dropna()
    total = (both.sum(axis=1) - both.sum(axis=1).min()) if w.shape[1] > 1 and len(both) else None
    pick = total if total is not None else per_fold.iloc[:, 0].dropna()
    return per_fold, total, float(pick.idxmin()), pick


def top_panel(ax, crit, X, zero_at, pos, has_zero, title, mark=None, mark_label=None):
    """`mark` overrides the ringed point: the deciding panel rings the CHOSEN fraction (the
    pre-registered rule's pick), which need not be the raw argmin."""
    per_fold, total, best, pick = crit
    if mark is not None:
        best = mark
    for f in per_fold.columns:
        s = per_fold[f].dropna()
        series(ax, s.index, s.values, X, accent=False)
    if total is not None:
        series(ax, total.index, total.values, X, accent=True)
    style(ax, zero_at, pos, has_zero)
    yb = float(pick.loc[best])
    ax.plot([X[best]], [yb], "o", ms=11, mfc="none", mec=ACCENT, mew=1.6, zorder=6)
    ax.annotate(mark_label or f"best  {best:g}", (X[best], yb), xytext=(10, 14),
                textcoords="offset points", fontsize=9, color=INK)
    if PREVIOUS in X and not np.isclose(best, PREVIOUS):
        ax.axvline(X[PREVIOUS], color=AXIS, lw=0.8, zorder=1)
        ax.annotate("previous default", (X[PREVIOUS], 1), xycoords=("data", "axes fraction"),
                    xytext=(4, -12), textcoords="offset points", fontsize=8, color=INK2)
    ax.set_title(title, loc="left", fontsize=10.5, color=INK)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=CSV)
    ap.add_argument("--by-year", default=BY_YEAR)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    d, by = pd.read_csv(a.csv), pd.read_csv(a.by_year)

    # Draw only (fold, frac) present in BOTH files, and say which summary rows lack detail.
    kd, kb = set(zip(d.fold, d.smooth_frac)), set(zip(by.fold, by.smooth_frac))
    no_detail = sorted(kd - kb)
    d = d[np.array([k in kb for k in zip(d.fold, d.smooth_frac)])]
    by = by[np.array([k in kd for k in zip(by.fold, by.smooth_frac)])]
    if no_detail:
        print(f"NOTE: {len(no_detail)} summary row(s) have no per-year detail yet and are not drawn: {no_detail}")

    # REPRODUCTION: the per-year detail must sum to the sweep's own totals, or it is not the same run.
    agg = by.groupby(["fold", "smooth_frac"]).agg(tot=("heldout_negll", "sum"), nobs=("n_test", "sum"))
    chk = d.set_index(["fold", "smooth_frac"])[["heldout_negll", "heldout_nobs"]].join(agg)
    mismatch = chk[~np.isclose(chk.tot, chk.heldout_negll, rtol=0, atol=1e-2) | (chk.nobs != chk.heldout_nobs)]
    if len(mismatch):
        print(f"WARNING: per-year detail does NOT reproduce the sweep for {list(mismatch.index)}")

    # PAIRING: within a fold every grid point must be scored on the same held-out observations,
    # overall and year by year, or differences between points are partly noise.
    folds = sorted(d.fold.unique())
    unpaired = sorted({int(f) for f, g in d.groupby("fold")
                       if g.heldout_nobs.nunique() > 1 or (g.heldout_bad_cells > 0).any()}
                      | {int(f) for (f, _), n in by.groupby(["fold", "year"]).n_test.nunique().items() if n > 1})
    if unpaired:
        print(f"WARNING: fold(s) {unpaired} are NOT paired -- held-out counts differ across grid points")

    fracs = sorted(d.smooth_frac.unique())
    X, zero_at, pos = xpos(fracs)
    has_zero = 0.0 in fracs
    years = sorted(by.year.unique())
    pre = criterion(by, [y for y in years if y >= DECIDE_FROM])
    inf = criterion(by, [y for y in years if y >= INFORMATIVE_FROM])
    # The rule needs both folds (its noise band IS their disagreement); with one fold each panel can
    # only ring its raw argmin, and says so.
    two = len(folds) == 2
    rule = decide(by, DECIDE_FROM) if two else None
    rule_inf = decide(by, INFORMATIVE_FROM) if two else None
    pick_pre = rule["chosen"] if two else pre[2]
    pick_inf = rule_inf["chosen"] if two else inf[2]

    fig = plt.figure(figsize=(13, 7.8), facecolor=SURFACE)
    gs = fig.add_gridspec(2, 6, height_ratios=[1.3, 1], hspace=0.45, wspace=0.5)
    left = fig.add_subplot(gs[0, :3])
    right = fig.add_subplot(gs[0, 3:], sharey=left)
    for ax in (left, right):
        ax.set_yscale("symlog", linthresh=10)
    kind = "rule pick" if two else "raw best (one fold)"
    top_panel(left, pre, X, zero_at, pos, has_zero,
              f"Pre-registered window: {DECIDE_FROM}–{years[-1]}", mark=pick_pre, mark_label=f"{kind}  {pick_pre:g}")
    top_panel(right, inf, X, zero_at, pos, has_zero,
              f"Least censoring: {INFORMATIVE_FROM}–{years[-1]}", mark=pick_inf, mark_label=f"{kind}  {pick_inf:g}")
    for ax in (left, right):
        if ADOPTED in X:
            ax.axvline(X[ADOPTED], color=ACCENT, lw=1.2, alpha=0.6, zorder=1)
            ax.annotate(f"adopted  {ADOPTED:g}", (X[ADOPTED], 1), xycoords=("data", "axes fraction"),
                        xytext=(4, -26), textcoords="offset points", fontsize=8.5, color=INK)
    left.set_ylabel("held-out negll above best (nats, symlog)", fontsize=9, color=INK)
    best = ADOPTED if ADOPTED in X else pick_pre           # bottom-row guides follow what production uses

    # years in the deciding window that prefer each fraction to no smoothing at all
    g = by.groupby(["smooth_frac", "year"]).agg(v=("heldout_negll", "sum"), nf=("fold", "nunique"))
    g = g[g.nf == len(folds)].v.unstack("year")
    wins = None
    if has_zero and len(g) > 1:
        delta = g.sub(g.loc[0.0], axis=1)[[c for c in g.columns if c >= INFORMATIVE_FROM]]
        wins = (delta < 0).sum(axis=1).drop(index=0.0)
        n_dec = int(delta.notna().sum(axis=1).max())

    panels = [("rho0", "rho0\nimplied", "log"),
              ("alpha_rough_men", "men: log-alpha\nroughness", None),
              ("eta0_years", "years left\nat eta = 0", None),
              ("unc_ratio_mean", "in-sample\nuncapped / ASS", None),
              ("gmm_nq", "GKSW criterion\nSum n Q", None),
              ("wins", f"years {INFORMATIVE_FROM}+ beating\nno smoothing", None)]
    for k, (col, title, yscale) in enumerate(panels):
        ax = fig.add_subplot(gs[1, k])
        if yscale:
            ax.set_yscale(yscale)
        if col == "wins":
            if wins is not None and len(wins):
                series(ax, wins.index, wins.values, X, accent=True)
                ax.axhline(n_dec / 2, color=AXIS, lw=0.8, zorder=1)
                ax.set_ylim(-0.5, n_dec + 0.5)
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        else:
            for f in folds:
                s = d[d.fold == f].sort_values("smooth_frac")
                series(ax, s.smooth_frac, s[col].values, X, accent=False, log=bool(yscale))
            if len(folds) > 1:
                m = d.groupby("smooth_frac")[col].mean()
                series(ax, m.index, m.values, X, accent=True, log=bool(yscale))
        if col == "unc_ratio_mean":
            lo_ = d.groupby("smooth_frac").unc_ratio_min.min()
            hi_ = d.groupby("smooth_frac").unc_ratio_max.max()
            pp = lo_.index > 0
            ax.fill_between([X[v] for v in lo_.index[pp]], lo_.values[pp], hi_.values[pp],
                            color=ACCENT, alpha=0.10, lw=0, zorder=1)
            if has_zero:
                ax.plot([X[0.0]] * 2, [lo_.loc[0.0], hi_.loc[0.0]], color=ACCENT, alpha=0.25,
                        lw=3, solid_capstyle="butt", zorder=1)
            ax.axhline(1.0, color=AXIS, lw=0.8, zorder=1)
        style(ax, zero_at, pos, has_zero)
        if not yscale and col != "wins":
            ax.ticklabel_format(axis="y", useOffset=False, style="plain")
        if col == "eta0_years":
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            ax.set_ylim(-0.4, max(float(d[col].max()), 3.0) + 0.6)
        ax.axvline(X[best], color=ACCENT, lw=0.8, alpha=0.5, zorder=1)
        ax.set_title(title, loc="left", fontsize=8.5, color=INK)
        ax.set_xlabel("SMOOTH_FRAC", fontsize=8, color=INK2)

    handles = [plt.Line2D([], [], color=GRAY, lw=1.0, marker="o", ms=3.5, mec=SURFACE, label="each fold")]
    if len(folds) > 1:
        handles.append(plt.Line2D([], [], color=ACCENT, lw=1.8, marker="o", ms=5, mec=SURFACE,
                                  label="both folds (summed on top, mean below)"))
    fig.legend(handles=handles, loc="upper right", frameon=False, fontsize=9, labelcolor=INK,
               bbox_to_anchor=(0.985, 0.995))
    on_grid = ADOPTED in X
    notes = [f"source: {os.path.basename(a.csv)} + {os.path.basename(a.by_year)}", f"folds {list(folds)}",
             f"lam={d.lam.iloc[0]}",
             "paired" if not unpaired else f"NOT PAIRED: fold(s) {unpaired}",
             "detail reproduces sweep" if not len(mismatch) else "DETAIL DOES NOT REPRODUCE SWEEP",
             f"rule picks {pick_pre:g} ({DECIDE_FROM}+) / {pick_inf:g} ({INFORMATIVE_FROM}+)",
             f"ADOPTED SMOOTH_FRAC {ADOPTED:g}" + ("" if on_grid else " -- NOT ON THE GRID")]
    if rule and (rule["edge"] or rule_inf["edge"]):
        notes.append("** EDGE: an optimum is not located **")
    if no_detail:
        notes.append(f"{len(no_detail)} point(s) awaiting detail")
    flagged = bool(unpaired or len(mismatch) or no_detail or not on_grid
                   or (rule and (rule["edge"] or rule_inf["edge"])))
    fig.text(0.01, 0.005, "   ".join(notes), fontsize=7, color=INK if flagged else GRAY)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(f"{a.out}.{ext}", dpi=200, bbox_inches="tight", facecolor=SURFACE)
    print(f"wrote {a.out}.png/.pdf   rule picks {pick_pre:g} ({DECIDE_FROM}+), {pick_inf:g} ({INFORMATIVE_FROM}+); adopted {ADOPTED:g}"
          + ("" if len(folds) > 1 else "   (single fold -- not yet a calibration)"))
    if wins is not None:
        print("   years beating no smoothing: " + ", ".join(f"{f:g}: {int(v)}/{n_dec}" for f, v in wins.items()))


if __name__ == "__main__":
    main()
