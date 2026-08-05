#!/usr/bin/env python3
"""Replicate the "Final EPUF" line of Chart 4 in Compson (2012), RS Note 2012-01.

Chart 4 plots the percentage-point shortfall of two EPUF earnings measures
relative to the Annual Statistical Supplement's taxable-earnings totals:

  * "Final EPUF"           -- capped taxable earnings (what EPUF distributes)
  * "underlying EPUF sample" -- uncapped taxable earnings (not in the public file)

Only the *final* (capped) series is recoverable from the public EPUF, so this
script reproduces the red "Final EPUF" line:

    pp_diff(t) = (Supplement_t - EPUF_capped_t) / Supplement_t * 100

where EPUF_capped_t = 100 * SUM(annual.earnings) (the 1% sample scaled to 100%).

Reads the shared ssa.duckdb via the duckdb CLI (no python duckdb module needed)
and writes output/ssa_replication/chart4_replication.pdf.

Run from the epuf_2006/ project root:
    python code/ssa_replication/plot_chart4_replication.py
"""

from __future__ import annotations

import io
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "processed_data" / "ssa.duckdb"
OUT = ROOT / "output" / "ssa_replication" / "chart4_replication.pdf"

QUERY = """
SELECT s.year AS year,
       (s.reported_taxable_musd - SUM(a.earnings) * 100 / 1e6)
           / s.reported_taxable_musd * 100 AS final_epuf_pp_diff
FROM annual a
JOIN supplement_4b1 s USING (year)
WHERE s.year BETWEEN 1951 AND 2006
GROUP BY s.year, s.reported_taxable_musd
ORDER BY s.year;
"""


def load() -> pd.DataFrame:
    proc = subprocess.run(
        ["duckdb", "-readonly", "-csv", "-c", QUERY, str(DB)],
        capture_output=True, text=True, check=True,
    )
    return pd.read_csv(io.StringIO(proc.stdout))


def main() -> None:
    df = load()

    fig, ax = plt.subplots(figsize=(7.0, 3.05))
    ax.plot(df["year"], df["final_epuf_pp_diff"],
            color="#d62728", linewidth=1.8, label="Final EPUF")

    ax.set_ylim(-0.5, 4.5)
    ax.set_xlim(1951, 2006)
    ax.set_xticks(range(1951, 2007, 5))
    ax.set_yticks([-0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5])
    ax.set_xlabel("Year")
    ax.set_ylabel("Percent")
    ax.grid(axis="y", color="0.85", linewidth=0.6)
    ax.axhline(0, color="0.6", linewidth=0.6)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    # annotate the line the way the original chart does
    ax.annotate("Final EPUF", xy=(1969, 3.2), color="#d62728",
                fontsize=11, fontweight="bold")

    fig.subplots_adjust(left=0.075, right=0.965, top=0.98, bottom=0.135)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT)
    print(f"wrote {OUT}  ({len(df)} years, "
          f"{df['final_epuf_pp_diff'].iloc[0]:.2f}% -> "
          f"{df['final_epuf_pp_diff'].iloc[-1]:.2f}%)")


if __name__ == "__main__":
    main()
