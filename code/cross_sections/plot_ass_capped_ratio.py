#!/usr/bin/env python
"""The cap's bite, from published aggregates alone: the ratio of ASS UNCAPPED to CAPPED
(taxable) aggregate covered earnings per year, 1937-2022. Per-worker denominators cancel,
so this is exactly (uncapped mean) / (capped mean) earnings per covered worker -- the
share of average earnings the taxable maximum hides. It is the motivation figure for
using external (GKSW) moments: whatever this ratio exceeds 1 by is invisible to any
estimator that only sees top-coded EPUF earnings.

  python code/cross_sections/plot_ass_capped_ratio.py
    -> output/cross_sections/plots/ass_uncapped_capped_ratio.pdf (+ .png)
"""
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ASS_XLSX = Path("raw_data/annual_statistical_supplement.xlsx")
OUT = Path("output/cross_sections/plots/ass_uncapped_capped_ratio")


def main():
    d = pd.read_excel(ASS_XLSX, sheet_name="data")
    tot = d["aggearn_tot_wage"].fillna(0) + d["aggearn_tot_se"].fillna(0)
    tax = d["aggearn_tax_wage"].fillna(0) + d["aggearn_tax_se"].fillna(0)
    m = (tot > 0) & (tax > 0)
    yr, ratio = d.loc[m, "year"].to_numpy(), (tot[m] / tax[m]).to_numpy()

    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    ax.plot(yr, ratio, color="#1a1a19", lw=2.0)
    ax.axhline(1.0, color="0.6", lw=0.8)
    # cap-regime marks: 1966+ ad hoc raises resume; 1975+ automatic wage indexation;
    # 1979-81 statutory ad hoc jumps complete the catch-up
    ytop = ax.get_ylim()[1]
    for y, lab in ((1966, "ad hoc cap raises resume"), (1975, "cap indexed to wages"),
                   (1981, "statutory catch-up ends")):
        ax.axvline(y, color="0.75", lw=0.8, ls=":")
        ax.text(y + 0.7, ytop - 0.01, lab, fontsize=7.5, color="0.4",
                rotation=90, va="top", ha="left")
    ax.set_xlabel("year")
    ax.set_ylabel("uncapped / capped mean earnings")
    ax.set_title("What the taxable maximum hides: ASS uncapped vs capped mean covered "
                 "earnings per worker", fontsize=11)
    ax.grid(True, lw=0.4, alpha=0.4)
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(f"{OUT}.{ext}", dpi=150)
    plt.close(fig)
    hi_y = int(yr[np.argmax(ratio)])
    print(f"wrote {OUT}.pdf (+ .png); ratio peaks {ratio.max():.2f} in {hi_y}, "
          f"latest {ratio[-1]:.2f} in {int(yr[-1])}")


if __name__ == "__main__":
    main()
