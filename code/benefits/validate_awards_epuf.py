#!/usr/bin/env python
"""First-pass aggregate validation of the benefit calculator: claim-at-NRA awards.

For every EPUF person in birth cohorts 1887-1941 (with sex recorded), build the
taxable earnings history 1937..age-64 and compute the INITIAL retired-worker
monthly benefit under the law in force in the award year, assuming everyone
claims at 65 (= NRA for all these cohorts; the 1938-41 cohorts' NRA of 65 plus
2-8 months is handled inside b_modern as a small early-claim reduction). The
award-year framing needs no mortality assumptions: model award counts, average
monthly benefits, and the awarded-benefit distribution scale by x100 (EPUF is a
1% sample) and compare against the published series

  raw_data/supplement_2008_table_6A1_awards.csv      ASS 2008 Table 6.A1
      number of retired-worker awards, annual 1940-2007
  raw_data/supplement_2008_table_6A2_avg_benefit.csv ASS 2008 Table 6.A2
      average monthly benefit awarded to retired workers by sex,
      selected years 1940-2007 (annual from 1980; split rows where a
      mid-year benefit increase applies -- the last period is used here)

both extracted from https://www.ssa.gov/policy/docs/statcomps/supplement/2008/6a.html
(SSA's edge blocks non-browser fetches; the tables were pulled via a real browser,
same workaround as the committed 4.B1 source HTML).

Earnings input per person: 1937-1950 is `agg_earn_3750` spread UNIFORMLY over the
14 years (EPUF only records the pre-1951 aggregate); 1951+ is the sparse `annual`
panel zero-filled. The uniform spread matters only through insured status and the
pre-1951 slices of the old AMW formulas -- the recorded `qc_3750` quarters are NOT
used because the leg_* q-functions re-derive quarters from earnings.

Known first-pass caveats, all of which push model vs benchmark apart:
  * everyone claims at 65: actual awards from ~1962 on are dominated by reduced
    62-64 claims, so the model's average benefit should sit ABOVE the published
    average (no early-retirement reduction) and award timing shifts by up to
    3 years;
  * actual awards in year Y draw from several cohorts; the model's year-Y awards
    are exactly cohort Y-65;
  * EPUF samples people with covered earnings -- never-insured people are thin,
    but so are pre-1951-only careers (uniform spread understates their AMW);
  * the delayed-retirement branch of b_modern is never hit (claim == NRA), so
    the known qmodern-arity bug there does not bite;
  * the 1952-1960 a-functions can loop forever on marginally-insured people
    (see _Watchdog below); such persons are skipped and counted in the
    `skipped_timeout` output column, which depresses model awards for claim
    years ~1953-1961.

Run from the project root:

    python code/benefits/validate_awards_epuf.py [--jobs N]

Outputs:
    processed_data/benefits_awards_input.parquet   (intermediate, regenerated)
    output/benefits/awards_validation.csv
    output/benefits/plots/awards_validation.pdf (+ .png)
"""
import argparse
import contextlib
import os
import signal
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DB = "processed_data/ssa.duckdb"
PARQUET = Path("processed_data/benefits_awards_input.parquet")
BENCH_6A1 = Path("raw_data/supplement_2008_table_6A1_awards.csv")
BENCH_6A2 = Path("raw_data/supplement_2008_table_6A2_avg_benefit.csv")
OUT_CSV = Path("output/benefits/awards_validation.csv")
OUT_FIG = Path("output/benefits/plots/awards_validation")

CLAIM_AGE = 65          # = NRA for every cohort born through 1941
YOB_MIN, YOB_MAX = 1887, 1941   # award years 1952-2006
SAMPLE_SCALE = 100      # EPUF is a 1% sample

EXTRACT_SQL = f"""
COPY (
    SELECT d.id, d.yob, d.sex,
           coalesce(d.agg_earn_3750, 0) AS agg3750,
           list(a.year ORDER BY a.year)     AS years,
           list(a.earnings ORDER BY a.year) AS earns
    FROM demographic d
    LEFT JOIN annual a
           ON a.id = d.id AND a.year < d.yob + {CLAIM_AGE}
    WHERE d.yob BETWEEN {YOB_MIN} AND {YOB_MAX}
      AND d.sex IN (1, 2)
    GROUP BY d.id, d.yob, d.sex, d.agg_earn_3750
) TO '{PARQUET}' (FORMAT PARQUET);
"""


def extract_input():
    PARQUET.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["duckdb", DB], input=EXTRACT_SQL, text=True, check=True,
                   capture_output=True)
    print(f"extracted -> {PARQUET}")


PERSON_TIMEOUT = 0.3    # seconds; see _Watchdog below

class _Watchdog(Exception):
    """Raised when one person's calcBenefits exceeds PERSON_TIMEOUT.

    The 1952-1960 a-functions contain an unbounded `while not qXXXX(...)`
    qualification-year search that never terminates for people who pass the
    outer (full-stream) insured test but fail the inner one on the 1951-sliced
    stream -- ~12% of the cohorts claiming 1953-1961 in a profiling sample.
    Rather than patch the calculator, the driver skips such persons and reports
    them per claim year (column `skipped_timeout`); typical persons finish in
    ~1-20 ms, so 0.3 s is a pure hang detector, not a load shedder.
    """

def person_benefit(calc, yob, sex, agg3750, years, earns):
    """Initial monthly benefit at claim (claim year = yob + CLAIM_AGE);
    nan on error, -1.0 on watchdog timeout."""
    claim = yob + CLAIM_AGE
    n = claim - 1937
    stream = [0.0] * n
    pre = agg3750 / 14.0
    for i in range(min(14, n)):          # 1937-1950 uniform spread
        stream[i] = pre
    if years is not None:
        for y, e in zip(years, earns):
            if y is None or (isinstance(y, float) and np.isnan(y)):
                continue          # LEFT JOIN null row (person has no annual records)
            y = int(y)
            if 1951 <= y < claim:
                stream[y - 1937] = float(e)
    try:
        signal.setitimer(signal.ITIMER_REAL, PERSON_TIMEOUT)
        b = calc(1937, stream, yob, claim, claim, sex == 2)[0]
        signal.setitimer(signal.ITIMER_REAL, 0)
        return b
    except _Watchdog:
        return -1.0
    except Exception:
        signal.setitimer(signal.ITIMER_REAL, 0)
        return float("nan")


def _raise_watchdog(signum, frame):
    raise _Watchdog()


def run_chunk(rows):
    """rows: list of (yob, sex, agg3750, years, earns). Returns list of benefits."""
    from master_file import calcBenefits   # imported in the worker process
    signal.signal(signal.SIGALRM, _raise_watchdog)
    out = []
    with open(os.devnull, "w") as devnull, contextlib.redirect_stdout(devnull):
        for yob, sex, agg3750, years, earns in rows:
            out.append(person_benefit(calcBenefits, yob, sex, agg3750, years, earns))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--reuse-parquet", action="store_true",
                    help="skip the DuckDB extraction if the parquet already exists")
    args = ap.parse_args()

    if not (args.reuse_parquet and PARQUET.exists()):
        extract_input()
    df = pd.read_parquet(PARQUET)
    print(f"{len(df):,} persons, cohorts {YOB_MIN}-{YOB_MAX}")

    rows = list(zip(df["yob"].tolist(), df["sex"].tolist(), df["agg3750"].tolist(),
                    df["years"].tolist(), df["earns"].tolist()))
    chunks = [rows[i:i + 20000] for i in range(0, len(rows), 20000)]
    benefits = []
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for k, res in enumerate(ex.map(run_chunk, chunks)):
            benefits.extend(res)
            if (k + 1) % 5 == 0 or k + 1 == len(chunks):
                print(f"  {k + 1}/{len(chunks)} chunks", flush=True)
    df["benefit"] = benefits
    df["claim_year"] = df["yob"] + CLAIM_AGE

    n_err = int(df["benefit"].isna().sum())
    if n_err:
        by_year = df[df["benefit"].isna()]["claim_year"].value_counts().sort_index()
        print(f"WARNING: {n_err} persons raised inside calcBenefits "
              f"(by claim year: {by_year.to_dict()})")
    timed_out = df["benefit"] == -1.0
    n_to = int(timed_out.sum())
    if n_to:
        print(f"WARNING: {n_to} persons ({100 * n_to / len(df):.2f}%) hit the "
              f"{PERSON_TIMEOUT}s watchdog (unbounded qualification loop in the "
              f"1952-1960 a-functions) and are excluded from awards")

    aw = df[df["benefit"] > 0]
    g = aw.groupby("claim_year")["benefit"]

    def sexavg(sex):
        return (aw[aw["sex"] == sex].groupby("claim_year")["benefit"].mean())

    res = pd.DataFrame({
        "persons_in_cohort": df.groupby("claim_year").size(),
        "skipped_timeout": timed_out.groupby(df["claim_year"]).sum(),
        "model_awards": g.size() * SAMPLE_SCALE,
        "model_avg_mb": g.mean(),
        "model_avg_mb_men": sexavg(1),
        "model_avg_mb_women": sexavg(2),
        "model_p10": g.quantile(0.10), "model_p25": g.quantile(0.25),
        "model_p50": g.quantile(0.50), "model_p75": g.quantile(0.75),
        "model_p90": g.quantile(0.90),
    })
    res.index.name = "year"
    res["persons_in_cohort"] *= SAMPLE_SCALE
    res["skipped_timeout"] = res["skipped_timeout"].fillna(0).astype(int) * SAMPLE_SCALE

    b1 = pd.read_csv(BENCH_6A1).set_index("year")
    res = res.join(b1["awards_retired_workers"].rename("bench_awards"))
    # 6.A2: keep the LAST period of each year (post mid-year benefit increase,
    # i.e. the law the model applies to the award year)
    b2 = pd.read_csv(BENCH_6A2).groupby("year").last()
    res = res.join(b2[["avg_mb_rw_all", "avg_mb_rw_men", "avg_mb_rw_women"]]
                   .rename(columns={"avg_mb_rw_all": "bench_avg_mb",
                                    "avg_mb_rw_men": "bench_avg_mb_men",
                                    "avg_mb_rw_women": "bench_avg_mb_women"}))
    res["awards_ratio"] = res["model_awards"] / res["bench_awards"]
    res["avg_mb_ratio"] = res["model_avg_mb"] / res["bench_avg_mb"]

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT_CSV, float_format="%.2f")
    print(f"wrote {OUT_CSV}")

    cols = ["model_awards", "bench_awards", "awards_ratio",
            "model_avg_mb", "bench_avg_mb", "avg_mb_ratio"]
    show = res.loc[res.index.isin(range(1955, 2010, 5)), cols]
    print(show.to_string(float_format=lambda v: f"{v:,.2f}"))

    # ---- figure -------------------------------------------------------------
    OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    ax = axes[0]
    ax.plot(res.index, res["bench_awards"] / 1e6, color="0.3", lw=1.5,
            label="ASS 6.A1 (all claim ages)")
    ax.plot(res.index, res["model_awards"] / 1e6, color="tab:red", lw=1.5,
            label="model (claim at NRA)")
    ax.set_title("Retired-worker awards per year")
    ax.set_ylabel("millions")
    ax.legend(frameon=False, fontsize=8)

    ax = axes[1]
    for sfx, color in (("", "0.2"), ("_men", "tab:blue"), ("_women", "tab:orange")):
        lbl = sfx.strip("_") or "all"
        ax.plot(res.index, res[f"model_avg_mb{sfx}"], color=color, lw=1.2,
                label=f"model {lbl}")
        ax.plot(res.index, res[f"bench_avg_mb{sfx}"], "o", color=color, ms=3,
                label=f"ASS 6.A2 {lbl}")
    ax.set_yscale("log")
    ax.set_title("Average monthly benefit at award (nominal $)")
    ax.legend(frameon=False, fontsize=7, ncol=2)

    ax = axes[2]
    ax.axhline(1.0, color="0.7", lw=0.8)
    ax.plot(res.index, res["awards_ratio"], color="tab:red", lw=1.2, label="awards")
    ax.plot(res.index, res["avg_mb_ratio"], color="0.2", lw=1.2, label="avg benefit")
    ax.plot(res.index, res["model_avg_mb_men"] / res["bench_avg_mb_men"],
            color="tab:blue", lw=0.9, alpha=0.7, label="avg benefit, men")
    ax.plot(res.index, res["model_avg_mb_women"] / res["bench_avg_mb_women"],
            color="tab:orange", lw=0.9, alpha=0.7, label="avg benefit, women")
    ax.set_title("model / benchmark")
    ax.legend(frameon=False, fontsize=8)

    for ax in axes:
        ax.set_xlabel("award year")
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Claim-at-NRA award validation: EPUF histories through the benefit calculator "
                 "vs ASS 2008 Tables 6.A1/6.A2", fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{OUT_FIG}.pdf")
    fig.savefig(f"{OUT_FIG}.png", dpi=150)
    print(f"wrote {OUT_FIG}.pdf (+ .png)")


if __name__ == "__main__":
    main()
