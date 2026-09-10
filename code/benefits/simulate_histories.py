#!/usr/bin/env python
"""Synthetic earnings-history panels for the benefit-calculator validation, from TWO models
that share no parameters:

  ordinal  -- rank-preserving transform of a raw GKOS (2021) panel onto this project's OWN
              fitted per-(year, sex, age) cross-section marginals (dPlN for men, two-component
              lognormal mixture for women; `cross_sections/estimate_cross_sections.py`). Ranks
              only: no g(t) enters, because the ordinal transform is invariant to any
              additive age-varying shift (see `dynamics/plots/plot_gkos_ordinal.py`, which
              proves this for the raw GKOS process). The level and cross-sectional SHAPE at
              every age come entirely from the fitted surface; GKOS supplies only the
              within-age ranking of individuals (who stays high/low relative to peers) and
              the age-to-age persistence of that ranking.
  gcohort  -- the GKOS structural process with g(t) replaced by this project's re-estimated,
              cohort x sex lifecycle profile (`dynamics/estimate_g_cohort.py --mode smm-p50`,
              re-levelled and extrapolated -- see dynamics/relevel_g_cohort.py and CLAUDE.md).
              This is the "re-estimated CMS procedure" model: same u-process, same simulator,
              but the deterministic age profile is fitted to EPUF + GKSW medians and re-levelled
              to EPUF's own mean log, rather than left at GKOS's fixed men-only quadratic.

Both models draw from the SAME underlying nonemployment/dispersion process
(`gcohort_model.simulate_u`); they differ only in what turns u into a dollar level. Earnings
are ALWAYS zero before 1937 (no covered-earnings system existed) and whenever the simulated
person is nonemployed that year (u = -inf, which exponentiates to exactly 0 with no special
case). Nothing here touches `code/benefits/leg_*.py` or `master_file.py`: this module only
produces the (index_year, income_stream) pairs those functions are called with.

No CLI. Estimation/simulation only -- the driver is `code/benefits/run_agg_benefits.py`.
"""
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

sys.path.insert(0, "code/dynamics")          # run from the project root, per repo convention
sys.path.insert(0, "code/cross_sections")
import gcohort_model as E                    # noqa: E402
import extrapolate_g_cohort as X             # noqa: E402
import xs_model as XM                        # noqa: E402

XS_PARAMS_CSV = Path("output/cross_sections/cross_section_params_extrapolated.csv")
GCOHORT_PROFILE_CSV = Path("output/dynamics/g_cohort_smm_p50_relevelled_extrapolated.csv")
SEX_LABEL = {1: "male", 2: "female"}          # this project's sex code -> gcohort_model's label
FIRST_COVERED_YEAR = 1937                     # no covered earnings exist before this
N_GRID = 2001                                 # quantile-grid resolution for the ordinal model


# ------------------------------------------------------- ordinal model: fitted cross-sections
def load_xs_params(path=XS_PARAMS_CSV):
    """{(year, sex, age): row} for every fitted/extrapolated cross-section cell."""
    d = pd.read_csv(path)
    return {(int(r.year), int(r.sex), int(r.age)): r for r in d.itertuples()}


Z_SAFE = 20.0    # Mills-argument safety margin: erfcx(x) overflows double only past |x|~26.6


@lru_cache(maxsize=None)
def _dpln_grid(a, b, nu, tau):
    """Monotone (cdf, log-earnings) grid for the men's dPlN cell.

    nl_cdf's Mills-ratio terms overflow in float64 once a*tau - z or b*tau + z drops below
    about -27 (erfcx(x) ~ exp(x^2) diverges there): the term is analytically tiny in that
    limit (multiplied by a Gaussian phi(z) that vanishes even faster), but the naive product
    of an overflowing erfcx and an underflowing phi evaluates to NaN, not 0. Bounding z so
    BOTH Mills arguments stay above -Z_SAFE keeps every grid evaluation finite; z that far out
    is already indistinguishable from rank 0/1 in float64 regardless (ndtr saturates by
    z~8-9), so this loses no resolution any n_sim in the thousands could use."""
    z_lo, z_hi = -(b * tau + Z_SAFE), a * tau + Z_SAFE
    y = nu + tau * np.linspace(z_lo, z_hi, N_GRID)
    cdf = np.maximum.accumulate(XM.nl_cdf(y, a, b, nu, tau))
    return cdf, y


@lru_cache(maxsize=None)
def _mix_grid(mu1, mu2, s1, s2, w):
    """Monotone (cdf, log-earnings) grid for the women's lognormal-mixture cell. Both
    components are Gaussian in logs, so 10 sigma is generous on both sides."""
    lo = min(mu1, mu2) - 10.0 * max(s1, s2)
    hi = max(mu1, mu2) + 10.0 * max(s1, s2)
    y = np.linspace(lo, hi, N_GRID)
    cdf = np.maximum.accumulate(XM.mix_cdf(y, mu1, mu2, s1, s2, w))
    return cdf, y


def _invert(ranks, cdf, y):
    """np.interp needs the query clipped INTO the grid's own cdf range, or a rank landing
    outside the (already wide) precomputed span would silently extrapolate off the end of a
    monotone-but-finite array; clipping saturates at the grid edge instead."""
    r = np.clip(ranks, cdf[0], cdf[-1])
    return np.interp(r, cdf, y)


def simulate_ordinal(yob, sex, n_sim, rng, xs_params, ages):
    """(n_sim, len(ages)) nominal-dollar earnings panel for one (birth cohort, sex): a raw
    GKOS panel's within-age ranks, mapped onto the fitted cross-section marginal for the
    calendar year each age falls in. Zero wherever nonemployed (GKOS) or pre-1937."""
    ages = np.asarray(list(ages), dtype=int)
    u = E.simulate_u(rng, n_sim, ages=ages)
    earn = np.zeros_like(u)
    for j, a in enumerate(ages):
        y = yob + a
        if y < FIRST_COVERED_YEAR:
            continue
        row = xs_params.get((y, sex, int(a)))
        if row is None:                       # outside the fitted/extrapolated surface
            continue
        emp = np.isfinite(u[:, j])
        m = int(emp.sum())
        if m == 0:
            continue
        ranks = (rankdata(u[emp, j], method="average") - 0.5) / m
        if sex == 1:
            logy = _invert(ranks, *_dpln_grid(row.alpha, row.beta, row.nu, row.tau))
        else:
            logy = _invert(ranks, *_mix_grid(row.mu1, row.mu2, row.sig1, row.sig2, row.w))
        earn[emp, j] = np.exp(logy)
    return earn


# ------------------------------------------------------- gcohort model: re-estimated g(t)
def load_gcohort_profiles(path=GCOHORT_PROFILE_CSV):
    """{(sex_label, gkos_cohort): {g0, g1, g2, g3, h_young, h_old, [delta]}}. gkos_cohort =
    yob + 25, GKSW's own convention (see gcohort_model's module docstring)."""
    d = pd.read_csv(path)
    cols = [c for c in ("g0", "g1", "g2", "g3", "h_young", "h_old", "delta") if c in d.columns]
    return {(r.sex, int(r.cohort)): {k: getattr(r, k) for k in cols} for r in d.itertuples()}


def load_price_index(y0=FIRST_COVERED_YEAR, y1=2110):
    """Nominal dollars per BASE_YEAR (2013) dollar, {year: P(year)}. ONE call reused across
    every cohort/sex -- price_index() re-reads two workbooks per call."""
    return X.price_index(y0, y1)


def simulate_gcohort(yob, sex, n_sim, rng, profiles, price_index, ages):
    """(n_sim, len(ages)) nominal-dollar earnings panel: the GKOS process with g(t) replaced
    by this project's re-estimated, re-levelled cohort x sex profile. `--level epuf`
    re-levelling already targets EPUF's own mean log (see CLAUDE.md), so no wedge (`delta`)
    is added on top -- the relevelled/extrapolated CSV drops that column entirely."""
    ages = np.asarray(list(ages), dtype=int)
    u = E.simulate_u(rng, n_sim, ages=ages)
    coef = profiles[(SEX_LABEL[sex], yob + 25)]
    g = E.g_at(coef, ages) + coef.get("delta", 0.0)     # (len(ages),); delta is 0.0 if absent
    years = yob + ages
    # price_index only covers >= FIRST_COVERED_YEAR; years before that are zeroed below anyway,
    # so look them up AFTER masking, not before (a pre-1937 year is a KeyError, not a 0.0).
    logP = np.array([np.log(price_index[int(y)]) if y >= FIRST_COVERED_YEAR else 0.0
                     for y in years])
    logy = g[None, :] + u + logP[None, :]
    with np.errstate(over="ignore"):
        earn = np.exp(logy)                              # u = -inf -> earn = 0, no special case
    earn[:, years < FIRST_COVERED_YEAR] = 0.0
    return earn
