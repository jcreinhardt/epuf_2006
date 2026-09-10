#!/usr/bin/env python
"""EPUF's disclosure protection, as a function -- so a model can be compared to EPUF like for
like instead of against artefacts.

SSA does not publish EPUF earnings as recorded.  Every amount is random-rounded, everything
under $100 is replaced by one number, amounts that round up to the taxable maximum without
reaching it are replaced by another, and the maximum itself is a hard top code.  A model
compared against that raw will "miss" a spike at $47 and a pile at the cap that are not
economics.  `disclose` puts model dollars through the same mill.

THE RULE WAS RECOVERED FROM THE DATA, not assumed:

  | true nominal amount | what EPUF records |
  |---|---|
  | < $100            | one number, the year's sub-$100 mean ($46 in 1951 rising to $58 in 2006) |
  | $100 - $999       | random-rounded to a multiple of $25 |
  | $1,000 - $49,999  | random-rounded to a multiple of $100 |
  | >= $50,000        | random-rounded to a multiple of $1,000 |
  | rounds up to the cap without reaching it | one number, that group's mean |
  | >= the cap        | the cap |

The $50,000 step is exact and nominal, checked in 1990 / 2000 / 2006: below it 11% of values
are multiples of $1,000 -- the chance rate -- and at and above it, 100%.  The two code VALUES
are read out of EPUF per year (`epuf_codes`) rather than recomputed, so they are the data's own
constants and no year needs a hand-maintained table.

CHECKED two ways, which is how the bases and thresholds were pinned down: run on EPUF's OWN
values the function is a fixed point (100.0% unchanged in 1965 and 1995 -- every recorded
amount already sits on the grid it would put it on), and on a smooth lognormal input it
preserves the mean below the cap to 4e-4 (1965) and 4e-7 (1995).

It matters for the two ends only: disclosed and undisclosed model curves are indistinguishable
through the middle of the distribution, so a mid-range gap between a model and EPUF is the
model, not the protection.

This lives in the section root rather than in the figure that first needed it, per the repo's
estimation-vs-figures rule: it is a data transformation, several scripts need it, and a plot
script importing another plot script is how that rule gets broken by accretion.
"""
import io
import subprocess

import numpy as np
import pandas as pd

DB = "processed_data/ssa.duckdb"           # opened -readonly: several short queries per run,
                                           # and a write lock makes back-to-back ones race
ROUND_STEPS = ((1_000.0, 25.0), (50_000.0, 100.0), (np.inf, 1_000.0))
CODE_LO_MAX = 100.0            # below this EPUF stores one number: the sub-$100 mean


def duck(q):
    """One read-only DuckDB query -> DataFrame."""
    out = subprocess.run(["duckdb", "-readonly", DB, "-csv", "-c", q],
                         capture_output=True, text=True, check=True).stdout
    return pd.read_csv(io.StringIO(out))


def taxmax(year):
    """The top code, recoverable from the data as the year's maximum recorded earnings."""
    return float(duck(f"SELECT MAX(earnings) AS m FROM annual WHERE year={int(year)}")["m"][0])


def base_of(x):
    """The rounding base EPUF uses at each nominal amount."""
    b = np.full(np.shape(x), ROUND_STEPS[-1][1], float)
    for hi, step in reversed(ROUND_STEPS[:-1]):
        b[np.asarray(x) < hi] = step
    return b


def epuf_codes(year):
    """(cap, sub-$100 code, near-cap collapse value or None) for `year`, read from EPUF."""
    cap = taxmax(year)
    lo = duck(f"SELECT earnings, count(*) n FROM annual WHERE year={int(year)} AND earnings>0 "
              f"AND earnings<{CODE_LO_MAX:.0f} GROUP BY 1 ORDER BY n DESC LIMIT 1")
    base = base_of(np.array([cap]))[0]        # the collapse value is the one near-cap amount
    c = duck(f"SELECT earnings, count(*) n FROM annual WHERE year={int(year)} "   # off the grid
             f"AND earnings > {cap - 5 * base} AND earnings < {cap} "
             f"AND earnings % {base:.0f} <> 0 GROUP BY 1 ORDER BY n DESC LIMIT 1")
    return cap, float(lo["earnings"][0]), (float(c["earnings"][0]) if len(c) else None)


def epuf_codes_many(years):
    """`epuf_codes` for a whole span in THREE queries instead of three per year.

    A lifecycle panel needs 36-51 years of codes, and each duckdb call spawns a process against
    a 1.7 GB database: done year by year that is ~150 spawns and minutes of wall time."""
    lo, hi = int(min(years)), int(max(years))
    caps = duck(f"SELECT year, MAX(earnings) AS cap FROM annual WHERE year BETWEEN {lo} AND {hi} "
                f"GROUP BY 1")
    code = duck(f"SELECT year, arg_max(earnings, n) AS code_lo FROM ("
                f"  SELECT year, earnings, count(*) AS n FROM annual WHERE earnings>0 "
                f"  AND earnings<{CODE_LO_MAX:.0f} AND year BETWEEN {lo} AND {hi} GROUP BY 1,2"
                f") GROUP BY 1")
    coll = duck(f"WITH b AS (SELECT year, cap, CASE WHEN cap<1000 THEN 25 "
                f"                 WHEN cap<50000 THEN 100 ELSE 1000 END AS base FROM ("
                f"    SELECT year, MAX(earnings) AS cap FROM annual "
                f"    WHERE year BETWEEN {lo} AND {hi} GROUP BY 1)), "
                f"     c AS (SELECT a.year, a.earnings, count(*) AS n FROM annual a "
                f"           JOIN b ON b.year = a.year "
                f"           WHERE a.earnings > b.cap - 5*b.base AND a.earnings < b.cap "
                f"             AND a.earnings % b.base <> 0 GROUP BY 1,2) "
                f"SELECT year, arg_max(earnings, n) AS collapse FROM c GROUP BY 1")
    d = (caps.merge(code, on="year", how="left").merge(coll, on="year", how="left")
              .set_index("year"))
    return {int(y): (float(r["cap"]), float(r["code_lo"]),
                     None if pd.isna(r["collapse"]) else float(r["collapse"]))
            for y, r in d.iterrows()}


def disclose(x, year, rng, codes=None):
    """Put nominal dollars through EPUF's disclosure protection, in EPUF's order.

    Random rounding is STOCHASTIC and unbiased -- down with probability 1 - frac, up with
    probability frac -- so the mean survives and only the fine structure is destroyed, which
    is the point of the scheme and the reason a deterministic round would not reproduce it."""
    cap, code_lo, collapse = codes if codes else epuf_codes(year)
    x = np.asarray(x, float)
    b = base_of(x)
    q, frac = np.divmod(x / b, 1.0)
    out = b * (q + (rng.random(x.size) < frac))
    if collapse is not None:                      # rounds up to the cap without reaching it
        out[(x < cap) & (out >= cap)] = collapse
        out[x == collapse] = collapse             # already collapsed: a fixed point
    out[x >= cap] = cap
    out[x < CODE_LO_MAX] = code_lo
    return out
