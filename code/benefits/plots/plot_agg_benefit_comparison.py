#!/usr/bin/env python
"""Average monthly benefit at award: TWO synthetic earnings models through
`master_file.calcBenefits` against ASS 2008 Table 6.A2's average PIA of new retired-worker
awards -- same claim-at-65 convention, same statistic (mean of the benefit awarded to people
who claim that year, sex by sex), as `validate_awards_epuf.py`'s real-EPUF validation.

  ordinal  -- a raw GKOS panel's within-age ranks, transformed onto this project's own fitted
              cross-section marginals (dPlN men / lognormal-mixture women).
  gcohort  -- the GKOS process with g(t) replaced by this project's re-estimated,
              re-levelled cohort x sex lifecycle profile (the "re-estimated CMS procedure").

BENCHMARK COLUMN: PIA, not the actually-paid benefit. Table 6.A2 carries two statistics per
sex -- `avg_pia` (the benefit-formula amount at Normal Retirement Age, before any age
adjustment) and `avg_mb_rw` (what new awardees are actually PAID: PIA times each person's own
early/delayed-claiming adjustment). Every simulated person here claims at exactly 65, which is
NRA for essentially the whole 1887-1942 cohort range, so the model computes a PIA-equivalent.
`avg_mb_rw` instead reflects the real population's mix of claiming ages, and is 0% below PIA
before early retirement existed (women: pre-1956, men: pre-1961) rising to 6-14% below it once
early claiming became common -- comparing our claim-at-65 model against `avg_mb_rw` would have
attributed a real, growing, and well-understood claiming-behavior effect to the earnings
models instead. `avg_pia` is the like-for-like column.

Both models draw on the EXTRAPOLATED parameter surfaces for calendar years 1937-1950, not
the directly-fitted ones: the joint solve (`cross_section_params_smoothed.csv`) only covers
1951-2006, so the ordinal model's marginals for 1937-1950 come from
`cross_section_params_extrapolated.csv` (`extrapolate_params.py`'s backward extrapolation,
alpha-calibrated per year against the same ASS benchmark -- see CLAUDE.md); the gcohort
profile is `g_cohort_smm_p50_relevelled_extrapolated.csv` for the same reason on its side
(cohorts outside the 1957-1983 fitted window). `simulate_histories.py` already points at
both "_extrapolated" files -- see its module docstring -- so this is a property of the
inputs, not a flag here.

Four SEPARATE figures (not four panels of one figure), by design (a level comparison and a
ratio comparison read differently -- one needs a log axis, the other a y=1 reference line --
and men/women sit at different levels throughout, so overlaying them buries the ratio
comparison the level panel is least useful for):

  agg_benefit_award_level_men.{pdf,png}    average monthly benefit (PIA) at award, men
  agg_benefit_award_level_women.{pdf,png}  average monthly benefit (PIA) at award, women
  agg_benefit_award_ratio_men.{pdf,png}    model / ASS 6.A2 PIA, men
  agg_benefit_award_ratio_women.{pdf,png}  model / ASS 6.A2 PIA, women

Benchmark row selection: Table 6.A2 splits several years into two periods around a mid-year
benefit increase (e.g. 1983 "Jan.-Nov." vs "Dec."). The model applies NO COLA in the award
year itself (`reference_year == retirement_year` in every call here, as in
validate_awards_epuf.py), so the PRE-increase period is the like-for-like benchmark row --
the original script's `.groupby('year').last()` instead keeps the POST-increase row, which
biases model/benchmark down by ~2pp on average over 1983-2006 (measured separately). This
script uses `.first()` for that reason.

Run from the project root:
    python code/benefits/plots/plot_agg_benefit_comparison.py [--sim-csv CSV]
Output: output/benefits/plots/agg_benefit_award_{level,ratio}_{men,women}.{pdf,png}
"""
import argparse
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SIM_CSV = Path("output/benefits/agg_benefit_award_sim.csv")
BENCH_6A2 = Path("raw_data/supplement_2008_table_6A2_avg_benefit.csv")
OUT_DIR = Path("output/benefits/plots")

# this repo's own model/benchmark palette (plot_agg_tax_total.py): dark benchmark, bright models
C_BENCH, C_ORDINAL, C_GCOHORT = "#1a1a19", "#2a78d6", "#eb6834"
MODEL_STYLE = {"ordinal": dict(color=C_ORDINAL, label="ordinal transform"),
               "gcohort": dict(color=C_GCOHORT, label="re-est. g(t) (dynamics)")}
GAP_LO, GAP_HI = 1952.5, 1954.5   # claim years 1953-54: excluded, see module docstring


def load_benchmark():
    """ASS 2008 Table 6.A2 average PIA of new retired-worker awards, men & women -- the
    benefit-formula amount at NRA, before any actuarial adjustment for the age actually
    claimed. That is the like-for-like comparator for this model: every simulated person
    claims at exactly 65 (= NRA for the great majority of the cohort range here), so the
    model computes a PIA-equivalent, not the population's actually-PAID average (`avg_mb_rw`),
    which bakes in the real mix of claiming ages and runs 0-14% below PIA once early
    retirement is available (women from 1956, men from 1961) -- see the conversation that
    established this. Split-year rows keep the PRE-increase ("first") period -- see module
    docstring."""
    b = pd.read_csv(BENCH_6A2).groupby("year").first()
    return b[["avg_pia_men", "avg_pia_women"]].rename(
        columns={"avg_pia_men": "men", "avg_pia_women": "women"})


def _mark_gap(ax):
    ax.axvspan(GAP_LO, GAP_HI, color="0.85", zorder=0)
    ax.annotate("1953-54 excluded\n(leg_1952 arity bug)", xy=(0.5 * (GAP_LO + GAP_HI), 0.02),
                xycoords=("data", "axes fraction"), ha="center", va="bottom",
                fontsize=7, color="0.4")


def _finish(fig, ax, out_path):
    ax.set_xlabel("award year")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(f"{out_path}.pdf")
    fig.savefig(f"{out_path}.png", dpi=150)
    plt.close(fig)
    print(f"wrote {out_path}.pdf (+ .png)")


def level_figure(sim, bench, sex, out_path):
    fig, ax = plt.subplots(figsize=(7, 5))
    _mark_gap(ax)
    for model in ("ordinal", "gcohort"):
        d = sim[sim.model == model].sort_values("claim_year")
        ax.plot(d.claim_year, d[f"avg_mb_{sex}"], color=MODEL_STYLE[model]["color"],
                lw=1.4, marker=".", ms=4, label=MODEL_STYLE[model]["label"])
    ax.plot(bench.index, bench[sex], "o", color=C_BENCH, ms=3.5, label="ASS 6.A2 PIA")
    ax.set_yscale("log")
    ax.set_ylabel("average monthly benefit (PIA) at award (nominal $)")
    ax.set_title(f"Average monthly benefit (PIA) at award, {sex}")
    _finish(fig, ax, out_path)


def ratio_figure(sim, bench, sex, out_path):
    fig, ax = plt.subplots(figsize=(7, 5))
    _mark_gap(ax)
    ax.axhline(1.0, color=C_BENCH, lw=1.0, zorder=1)
    for model in ("ordinal", "gcohort"):
        d = sim[sim.model == model].sort_values("claim_year").set_index("claim_year")
        common = d.index.intersection(bench.index)
        ratio = d.loc[common, f"avg_mb_{sex}"] / bench.loc[common, sex]
        ax.plot(common, ratio, color=MODEL_STYLE[model]["color"],
                lw=1.4, marker=".", ms=4, label=MODEL_STYLE[model]["label"])
    ax.set_ylabel("model / ASS 6.A2 PIA (ratio)")
    ax.set_title(f"Average monthly benefit (PIA) at award: model / benchmark, {sex}")
    _finish(fig, ax, out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim-csv", default=str(SIM_CSV))
    args = ap.parse_args()

    sim = pd.read_csv(args.sim_csv)
    bench = load_benchmark()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for sex in ("men", "women"):
        level_figure(sim, bench, sex, OUT_DIR / f"agg_benefit_award_level_{sex}")
        ratio_figure(sim, bench, sex, OUT_DIR / f"agg_benefit_award_ratio_{sex}")


if __name__ == "__main__":
    main()
