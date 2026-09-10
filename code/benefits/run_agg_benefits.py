#!/usr/bin/env python
"""Two-model comparison of average monthly benefit at award: does NOT touch EPUF data or
`code/benefits/leg_*.py` / `master_file.py`. It feeds `master_file.calcBenefits` with
SYNTHETIC earnings histories from two models that share no parameters (`simulate_histories.py`):

  ordinal  -- a raw GKOS panel's within-age ranks, transformed onto this project's own fitted
              cross-section marginals (dPlN men / lognormal-mixture women).
  gcohort  -- the GKOS process with g(t) replaced by this project's re-estimated,
              cohort x sex lifecycle profile (the "re-estimated CMS procedure").

For each birth cohort and sex, N_SIM synthetic people are built, claim at age 65 (= NRA for
every cohort here), and their INITIAL monthly benefit is averaged -- the same statistic and
claim-age convention as `validate_awards_epuf.py`'s real-EPUF validation, so the two are
directly comparable.

`calcBenefits` was verified (black-box, this project's own probing, not by editing it) to
return a correct-length, non-negative, non-NaN benefit stream for every claim age <= NRA and
every earnings profile tried, EXCEPT two pockets that are bugs in `leg_1952.py` /
`leg_1954.py` / `leg_1956.py` / `leg_1958.py`, not in this driver or its inputs:

  * claim year 1953 or 1954 -- `bb1952` always raises (`a1952` arity mismatch), for every
    earnings history without exception. Excluded outright (NaN), same as the original script.
  * claim years 1955-1960 with an empty 1937-1950 earnings slice -- an unbounded `while` loop
    in `a1952/a1954/a1956/a1958`. A synthetic person built here always has positive covered
    earnings somewhere in 1937-1950 whenever they are of working age then (both models put
    them at positive risk of earning something most years), so this is not expected to bind,
    but a per-person watchdog is kept anyway and any hang is skipped and counted.

Run from the project root:
    python code/benefits/run_agg_benefits.py [--n-sim N] [--jobs J] [--yob-min Y] [--yob-max Y]

Output: output/benefits/agg_benefit_award_sim.csv
"""
import argparse
import contextlib
import os
import signal
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # code/benefits, for master_file

OUT_CSV = Path("output/benefits/agg_benefit_award_sim.csv")

CLAIM_AGE = 65                       # = NRA for every cohort in range; matches validate_awards_epuf
YOB_MIN, YOB_MAX = 1887, 1942        # claim years 1952-2007, the ASS 6.A2 benchmark's fullest span
AGES = range(20, CLAIM_AGE)          # 20..64: the earnings years feeding the claim-65 award
PERSON_TIMEOUT = 0.1                 # seconds; ~1000x the observed non-hanging runtime
                                      # (<=0.13ms measured across this window) -- see the
                                      # leg_1952/54/56/58 hang note above
MODELS = ("ordinal", "gcohort")
_DEVNULL = open(os.devnull, "w")


class _Watchdog(Exception):
    pass


def _raise_watchdog(signum, frame):
    raise _Watchdog()


def _person_stream(earn_row, ages, yob):
    """Nominal-earnings list, index_year=1937, length = claim_year - 1937 -- the exact
    convention `master_file.calcBenefits` and `validate_awards_epuf.py` both expect."""
    claim = yob + CLAIM_AGE
    stream = [0.0] * (claim - 1937)
    for j, a in enumerate(ages):
        y = yob + a
        if y >= 1937:
            stream[y - 1937] = float(earn_row[j])
    return stream


def run_cell(task):
    """One (birth cohort, sex, model): simulate N_SIM histories, run each through
    calcBenefits, return the average initial award and the excluded counts."""
    yob, sex, model, n_sim, seed = task
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    with contextlib.redirect_stdout(_DEVNULL):
        from master_file import calcBenefits
    import simulate_histories as SH

    ages = list(AGES)
    claim = yob + CLAIM_AGE
    rng = np.random.default_rng(seed)

    if model == "ordinal":
        xs_params = _get_ordinal_inputs()
        earn = SH.simulate_ordinal(yob, sex, n_sim, rng, xs_params, ages)
    else:
        profiles, price_index = _get_gcohort_inputs()
        earn = SH.simulate_gcohort(yob, sex, n_sim, rng, profiles, price_index, ages)

    signal.signal(signal.SIGALRM, _raise_watchdog)
    benefits, n_err, n_to = [], 0, 0
    for i in range(n_sim):
        stream = _person_stream(earn[i], ages, yob)
        try:
            signal.setitimer(signal.ITIMER_REAL, PERSON_TIMEOUT)
            with contextlib.redirect_stdout(_DEVNULL):
                b = calcBenefits(1937, stream, yob, claim, claim, sex == 2)[0]
            signal.setitimer(signal.ITIMER_REAL, 0)
            benefits.append(b)
        except _Watchdog:
            signal.setitimer(signal.ITIMER_REAL, 0)
            n_to += 1
        except Exception:
            signal.setitimer(signal.ITIMER_REAL, 0)
            n_err += 1

    # calcBenefits legitimately returns 0 for someone not insured (a `q*` test that fails);
    # that is a real "no award" outcome, not an error, but it must NOT enter the average --
    # the ASS 6.A2 benchmark and validate_awards_epuf.py both average over AWARDED benefits
    # only. Averaging in the true zeros would understate the model as if they were errors.
    awarded = [b for b in benefits if b > 0]
    avg = float(np.mean(awarded)) if awarded else float("nan")
    return dict(yob=yob, sex=sex, model=model, claim_year=claim, avg_mb=avg,
                n_ok=len(benefits), n_awarded=len(awarded), n_uninsured=len(benefits) - len(awarded),
                n_err=n_err, n_timeout=n_to)


# Module-level caches so each worker process loads the (largish) parameter tables once,
# not once per (cohort, sex, model) task -- ProcessPoolExecutor workers are reused across
# ex.map() calls, so this actually pays off.
_ORDINAL_CACHE = None
_GCOHORT_CACHE = None


def _get_ordinal_inputs():
    global _ORDINAL_CACHE
    if _ORDINAL_CACHE is None:
        import simulate_histories as SH
        _ORDINAL_CACHE = SH.load_xs_params()
    return _ORDINAL_CACHE


def _get_gcohort_inputs():
    global _GCOHORT_CACHE
    if _GCOHORT_CACHE is None:
        import simulate_histories as SH
        _GCOHORT_CACHE = (SH.load_gcohort_profiles(), SH.load_price_index())
    return _GCOHORT_CACHE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-sim", type=int, default=2000,
                    help="synthetic people per (cohort, sex, model) cell")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--yob-min", type=int, default=YOB_MIN)
    ap.add_argument("--yob-max", type=int, default=YOB_MAX)
    ap.add_argument("--seed", type=int, default=20260909)
    args = ap.parse_args()

    seed_seq = np.random.SeedSequence(args.seed)
    tasks = [(yob, sex, model, args.n_sim, seed_seq.spawn(1)[0])
             for yob in range(args.yob_min, args.yob_max + 1)
             for sex in (1, 2)
             for model in MODELS]
    print(f"{len(tasks)} (cohort, sex, model) cells, n_sim={args.n_sim}, jobs={args.jobs}")

    rows = []
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for k, res in enumerate(ex.map(run_cell, tasks)):
            rows.append(res)
            if (k + 1) % 20 == 0 or k + 1 == len(tasks):
                print(f"  {k + 1}/{len(tasks)} cells", flush=True)

    df = pd.DataFrame(rows)
    n_excl = int(((df.n_err > 0) | (df.n_timeout > 0)).sum())
    if n_excl:
        by = df[(df.n_err > 0) | (df.n_timeout > 0)].groupby("claim_year")[["n_err", "n_timeout"]].sum()
        print(f"WARNING: {n_excl} cells had excluded persons (errors/timeouts), by claim year:")
        print(by.to_string())

    sex_name = {1: "men", 2: "women"}
    wide = df.pivot_table(index=["claim_year", "model"],
                          columns="sex",
                          values=["avg_mb", "n_ok", "n_awarded", "n_uninsured", "n_err", "n_timeout"])
    wide.columns = [f"{stat}_{sex_name[s]}" for stat, s in wide.columns]
    wide = wide.reset_index()

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    wide.to_csv(OUT_CSV, index=False, float_format="%.4f")
    print(f"wrote {OUT_CSV}  ({len(wide)} rows)")
    print(wide.loc[wide.claim_year.isin(range(1955, 2010, 10))].to_string(index=False))


if __name__ == "__main__":
    main()
