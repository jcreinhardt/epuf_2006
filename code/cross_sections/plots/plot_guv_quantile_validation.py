#!/usr/bin/env python
"""DATA-vs-DATA validation: GKSW sel0 quantiles against the SAME quantiles computed
directly from the EPUF microdata -- no fitted model anywhere. This isolates the
data-concept wedge (covered earnings vs W-2 commerce-and-industry, 1% CWHS vs 1% EPUF
frames) from parametric-family misspecification, which the model-vs-data comparison
(plot_guv_comparison.py) necessarily mixes together.

EPUF side, per (year, sex, age) cell, years 1957-2006 x ages 25-55:
  - the exact sel0 screen: keep earnings >= 260 x nominal minwage(year) (GKSW's own
    minimum-wage matrix; the same-year deflator cancels, so the nominal form is exact);
  - empirical quantiles of the screened NOMINAL earnings (quantile_disc, the lower order
    statistic, matching the do-file's r[ceil((n/100)*_N)]), deflated per cell to real
    2013$ with the GKSW PCE matrix -- deflation before aggregation, as in the guv files.

CENSORING RULE (the reason this needs care): EPUF earnings are top-coded at the taxable
maximum, so an empirical quantile is only observed where it falls BELOW the cap. A cell's
quantile counts as censored when it lands within HIGH_MARGIN ($1,000) of the year's cap
-- inside the near-cap pile-up, same margin as the fits. Aggregation is by cohort with
equal cell weights, but ONLY COMPLETE COHORTS enter: a cohort is used only where its
ENTIRE 31-cell age range 25-55 is available, and (for the EPUF side) entirely
uncensored. Window-truncated edge cohorts, which are observed at a partial age range,
are dropped outright on BOTH sides -- a partial average has a different age composition
and is not comparable across cohorts (the young-edge cohorts previously made p98 look
computable purely because they average ages 25-27 only). Consequently the GKSW line
covers cohorts 1957-1983 (complete within their 1957-2013 window; above-cap earnings
imputed, so never censored) and the EPUF line covers cohorts 1957-1976 (complete within
1957-2006) minus any cohort with a censored cell -- so p10 survives everywhere while
higher quantiles exist only where all 31 ages clear the cap, and prime-age-censored
quantiles (men's p90/p98) disappear entirely rather than pretending.

Bottom side needs no rule: the screen (>= $260 in 1957) sits above EPUF's $200
bottom-code throughout 1957-2006, so low quantiles of the screened sample are always
observed. GKSW's p99.999 winsorization cannot touch p98 either.

  python code/cross_sections/plots/plot_guv_quantile_validation.py
    -> output/cross_sections/plots/guv_quantile_validation_{men,women}.pdf (+ .png)
       output/cross_sections/guv_quantile_validation_cohort_means.csv
"""
import subprocess
import sys
from io import StringIO
from pathlib import Path

sys.path[:0] = ["code/cross_sections", "code/cross_sections/plots"]   # run from project root
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import crosssec_fit as cf
from guv_targets import load_guv, load_deflator, min_wage, QUANTS, QCOLS

YEARS = (1957, 2006)      # EPUF in-sample years inside the guv window
AGES  = (25, 55)
OUT_DIR  = Path("output/cross_sections")
PLOT_DIR = Path("output/cross_sections/plots")


def epuf_quantiles():
    """Empirical per-cell quantiles of screened EPUF earnings + the year's cap, via the
    duckdb CLI (repo convention). quantile_disc = lower order statistic, as in the do-file."""
    mw_vals = ", ".join(f"({y}, {260.0 * min_wage(y)})"
                        for y in range(YEARS[0], YEARS[1] + 1))
    qcols = ", ".join(f"quantile_disc(a.earnings, {q}) AS {c}"
                      for q, c in zip(QUANTS, QCOLS))
    q = (f"WITH mw(year, thr) AS (VALUES {mw_vals}), "
         "cap AS (SELECT year, MAX(earnings) AS taxmax FROM annual GROUP BY year) "
         "SELECT a.year, d.sex, a.year - d.yob AS age, COUNT(*) AS n, "
         f"ANY_VALUE(cap.taxmax) AS taxmax, {qcols} "
         "FROM annual a JOIN demographic d USING(id) "
         "JOIN mw ON mw.year = a.year JOIN cap ON cap.year = a.year "
         f"WHERE d.sex IN (1, 2) AND a.year - d.yob BETWEEN {AGES[0]} AND {AGES[1]} "
         "AND a.earnings >= mw.thr "
         "GROUP BY 1, 2, 3 ORDER BY 1, 2, 3")
    out = subprocess.run(["duckdb", "-readonly", cf.DB, "-csv", "-c", q],
                         capture_output=True, text=True, check=True).stdout
    return pd.read_csv(StringIO(out))


def main():
    nages = AGES[1] - AGES[0] + 1
    guv_all = load_guv()                 # full 1957-2013 grid, for the GKSW line
    guv = guv_all[(guv_all["year"] >= YEARS[0]) & (guv_all["year"] <= YEARS[1])]
    ep = epuf_quantiles()
    defl = load_deflator()
    fac = ep["year"].map(defl)

    for c in QCOLS:                      # censor flags on NOMINAL values, then deflate
        ep[f"{c}_cens"] = ep[c] >= ep["taxmax"] - cf.HIGH_MARGIN
        ep[c] = ep[c] * fac

    merged = guv[["year", "sex", "age", "cohort"] + QCOLS].rename(
        columns={c: f"{c}_guv" for c in QCOLS}).merge(
        ep.rename(columns={c: f"{c}_epuf" for c in QCOLS}),
        on=["year", "sex", "age"], how="inner")
    print(f"{len(merged)} matched cells "
          f"(guv window cells in {YEARS[0]}-{YEARS[1]}: {len(guv)})")

    # COMPLETE cohorts only (all 31 ages), equal-weight means. GKSW: complete within
    # its own 1957-2013 grid. EPUF: complete within 1957-2006 AND -- per quantile --
    # no contributing cell censored at the cap.
    recs = {}
    for (sex, cohort), grp in guv_all.groupby(["sex", "cohort"]):
        if len(grp) < nages:
            continue
        rec = recs[(sex, cohort)] = {"sex": sex, "cohort": cohort, "ncells": len(grp)}
        for c in QCOLS:
            rec[f"{c}_guv"] = grp[c].mean()
            rec[f"{c}_epuf"] = np.nan
    for (sex, cohort), grp in merged.groupby(["sex", "cohort"]):
        if len(grp) < nages or (sex, cohort) not in recs:
            continue
        for c in QCOLS:
            if not grp[f"{c}_cens"].any():
                recs[(sex, cohort)][f"{c}_epuf"] = grp[f"{c}_epuf"].mean()
    agg = pd.DataFrame(recs.values()).sort_values(["sex", "cohort"])
    agg.to_csv(OUT_DIR / "guv_quantile_validation_cohort_means.csv", index=False)

    for sex, name in ((1, "men"), (2, "women")):
        d = agg[agg["sex"] == sex]
        for c in QCOLS:
            kept = d[d[f"{c}_epuf"].notna()]["cohort"]
            span = f"{int(kept.min())}-{int(kept.max())} ({len(kept)})" if len(kept) else "none"
            print(f"  {name} {c}: cohorts kept {span}")
        plot_sex(d, name)


def plot_sex(d, name):
    BLUE, GREEN = "#2a78d6", "#1e9e64"        # GKSW keeps its comparison-figure color
    # only quantiles ever observed in EPUF under the complete-cohort rule: p98 never is
    # (no cohort clears the cap at all 31 ages), and neither is men's p90
    show = [c for c in QCOLS[:-1] if not (name == "men" and c == "p90")]
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.5))
    for ax, c in zip(axes.flat, show):
        ax.plot(d["cohort"], d[f"{c}_guv"], color=BLUE, lw=1.8,
                marker="o", ms=2.6, label="GKSW sel0 (published)")
        ax.plot(d["cohort"], d[f"{c}_epuf"], color=GREEN, lw=1.8, ls="--",
                marker="s", ms=2.6, label="EPUF empirical, same screen")
        ax.set_title(f"{c} of earnings (real 2013 $)", fontsize=11)
        ax.tick_params(labelsize=9)
        ax.grid(True, lw=0.4, alpha=0.4)
        ax.set_ylim(bottom=0)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    for ax in axes.flat[len(show):]:
        ax.axis("off")
    axes.flat[len(show)].legend(handles, labels, loc="center", fontsize=11, frameon=False)
    fig.suptitle(f"GKSW sel0 quantiles vs raw EPUF quantiles -- {name}\n"
                 "COMPLETE cohorts only: every point averages the full age range 25-55 "
                 "(GKSW within 1957-2013, EPUF within 1957-2006);\nEPUF additionally "
                 "requires no cell censored at the taxable maximum; level gaps = "
                 "data-concept wedge",
                 fontsize=12)
    fig.supxlabel("cohort (year turning age 25)", fontsize=11)
    fig.tight_layout(rect=(0, 0.01, 1, 0.91))
    for ext in ("pdf", "png"):
        fig.savefig(PLOT_DIR / f"guv_quantile_validation_{name}.{ext}", dpi=150)
    plt.close(fig)
    print(f"wrote {PLOT_DIR}/guv_quantile_validation_{name}.pdf (+ .png)")


if __name__ == "__main__":
    main()
