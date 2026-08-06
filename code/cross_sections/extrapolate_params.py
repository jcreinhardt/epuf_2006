#!/usr/bin/env python
"""Stage 3: polynomial extrapolation of the parameter surfaces to every birth cohort needed
for cross-sections over a target year range (default 1937-2100).

The penalized fits (iterate_fit_smooth.py) only cover cohorts the data see -- ~1880-1991.
To synthesize cross-sections for years 1937-2100 we need cohorts 1860-2085 (year-age over
age 15-77), so ~20 cohorts backward and ~94 forward are pure extrapolation. Per parameter we
fit a polynomial that is HIGH-order in age (fully interpolated) and LINEAR in cohort (the
extrapolated axis), then continue it past the data by a per-parameter tail rule.

Three design choices, each load-bearing:

  * ROTATE to the (age, year) frame.  cohort = year - age, so the raw (age, cohort) data is a
    PARALLELOGRAM (its off-diagonal corners are years outside 1951-2006). The shear to
    (age, year) squares it into the FULL rectangle age x [1951, 2006] -- every age spans the
    same years -- so a TENSOR basis (independent age/year degrees) is well-posed and the
    forward/back extrapolation is purely along year (= cohort at fixed age), one tail per age.

  * LINEAR in cohort.  A quadratic-in-cohort fit necessarily has an interior extremum, and
    over a 94-year forward reach its tail either crashes to a degenerate value (a concave
    parameter past its in-sample peak) or accelerates off (convex). Linear removes the
    turnaround -- the surface keeps moving in one direction, exactly the intent -- at a small
    in-sample cost. The cohort slope may still vary smoothly with age (the age x year tensor
    terms), it just cannot bend along cohort.

  * PER-PARAMETER TAIL beyond coverage.  The location parameters carry real earnings growth,
    so nu / mu1 / mu2 CONTINUE the linear cohort trend out to 2085. The shape parameters
    (tail indices alpha/beta, dispersions tau/sig1/sig2, mixing weight w) would drift to
    implausible values over 94 years of any nonzero slope, so beyond the last covered cohort
    they are held CONSTANT at the fitted (smoothed) edge level -- the value at the last data
    year for that age. In-sample both kinds use the fitted line; only the extrapolation differs.

Regimes: the retirement regime-switch is a real discontinuity, so each parameter is fit
SEPARATELY on the pre- and post-retirement age blocks (cut 65 men / 60 women) -- clean
horizontal cuts in the (age, year) frame -- and the surfaces may jump at the cut. Women's two
mixture means are carried as the ordered gap reparam (mu2, log(mu1-mu2)) so the components
never cross. mu2 trends, but the log-gap is held FLAT past coverage (a shape feature, and a
trending log-gap would grow the separation EXPONENTIALLY): so mu1 = mu2 + exp(gap_edge) trends
PARALLEL to mu2 -- a linear trend, always above mu2, and bounded.

  python code/cross_sections/extrapolate_params.py [--y0 1937] [--y1 2100] [--preview]
    -> output/cross_sections/cross_section_params_extrapolated.csv
"""
import sys
from pathlib import Path

sys.path.insert(0, "code/cross_sections")   # run from project root, per repo convention
import numpy as np
import pandas as pd

import crosssec_fit as cf    # SIG_MIN: the mixture sigma floor used when fitting
import smooth_params as sp   # to_theta / from_theta share the fitters' theta coordinates

IN   = Path("output/cross_sections/cross_section_params_iterated.csv")
OUT  = Path("output/cross_sections/cross_section_params_extrapolated.csv")
Y0, Y1 = 1937, 2100          # target year range for the synthesized cross-sections
DATA_Y0, DATA_Y1 = None, None   # data year span, filled from the input (constant-tail anchors)

# per sex: (label, retirement cut, [(param, theta transform, tail)]). tail = "trend" (continue
# the linear cohort slope, for location/growth params) or "flat" (hold constant beyond the
# covered cohorts, for bounded shape params). Women carry the ordered gap reparam
# (mu2, loggap=log(mu1-mu2)); mu1 is reconstructed as mu2 + exp(loggap), both trending.
SPEC = {
    1: ("men", 65, [("alpha", "log", "flat"), ("beta", "log", "flat"),
                    ("nu", "id", "trend"),    ("tau", "log", "flat")]),
    2: ("women", 60, [("mu2", "id", "trend"),   ("loggap", "raw", "flat"),
                      ("sig1", "logsig", "flat"), ("sig2", "logsig", "flat"),
                      ("w", "logit", "flat")]),
}
AGE_DEG = {"pre": 4, "post": 3}   # age polynomial degree by regime (wide pre / narrow post)


def to_theta(v, kind):
    return v if kind == "raw" else sp.to_theta(v, kind)


def from_theta(t, kind):
    return t if kind == "raw" else sp.from_theta(t, kind)


class PolyFit:
    """One parameter, one regime: tensor polynomial, degree deg_a in age and LINEAR in year,
    in scaled coordinates. `trend` continues the cohort line past the data; otherwise the
    year is clamped to the data span so the extrapolation is flat at the fitted edge level."""

    def __init__(self, age, year, z, deg_a, tail):
        self.am, self.asd = age.mean(), age.std()
        self.ym, self.ysd = year.mean(), year.std()
        self.deg_a, self.trend = deg_a, (tail == "trend")
        X = self._design(self._sa(age), self._sy(year))
        self.coef, *_ = np.linalg.lstsq(X, z, rcond=None)
        pred = X @ self.coef
        self.r2 = 1.0 - ((z - pred) ** 2).sum() / max(((z - z.mean()) ** 2).sum(), 1e-12)

    def _sa(self, a):
        return (np.asarray(a, float) - self.am) / self.asd

    def _sy(self, y):
        return (np.asarray(y, float) - self.ym) / self.ysd

    def _design(self, a_s, y_s):
        # age^i for i=0..deg_a, and age^i * year (linear in year) -> cohort slope varies with age
        cols = [a_s ** i for i in range(self.deg_a + 1)]
        cols += [(a_s ** i) * y_s for i in range(self.deg_a + 1)]
        return np.column_stack(cols)

    def predict(self, age, year):
        yq = np.asarray(year, float)
        if not self.trend:                                    # flat tail: clamp to data years
            yq = np.clip(yq, DATA_Y0, DATA_Y1)
        return self._design(self._sa(age), self._sy(yq)) @ self.coef


def fit_sex(df, sex):
    label, cut, params = SPEC[sex]
    sub = df[df["sex"] == sex].copy()
    sub["cohort"] = sub["year"] - sub["age"]
    if any(p == "loggap" for p, _, _ in params):
        sub["loggap"] = np.log(np.maximum(sub["mu1"] - sub["mu2"], 1e-3))
    fits = {}
    for reg, m in [("pre", sub["age"] < cut), ("post", sub["age"] >= cut)]:
        d = sub[m]
        for name, kind, tail in params:
            z = to_theta(d[name].to_numpy(float), kind)
            fits[(reg, name)] = PolyFit(d["age"].to_numpy(float), d["year"].to_numpy(float),
                                        z, AGE_DEG[reg], tail)
    return label, cut, params, fits


def build_grid(sex, cut, params, fits, y0, y1):
    """Every (age, year) cell over the model's age support x [y0, y1], filled from the
    regime-appropriate fit and back-transformed to natural units."""
    a_hi = 77 if sex == 1 else 74
    ages, years = np.arange(15, a_hi + 1), np.arange(y0, y1 + 1)
    AA, YY = (v.ravel() for v in np.meshgrid(ages, years))
    out = pd.DataFrame({"year": YY, "sex": sex, "age": AA})
    out["cohort"] = out["year"] - out["age"]
    for name, kind, _tail in params:
        vals = np.empty(len(out))
        for reg, m in [("pre", AA < cut), ("post", AA >= cut)]:
            vals[m] = from_theta(fits[(reg, name)].predict(AA[m], YY[m]), kind)
        if name in ("sig1", "sig2"):          # keep the fit's sigma floor out of sample too
            vals = np.maximum(vals, cf.SIG_MIN)
        out[name] = vals
    if sex == 2:                                              # ordered means from the gap reparam
        out["mu1"] = out["mu2"] + np.exp(out.pop("loggap"))
    return out


def main(y0=Y0, y1=Y1, preview=False):
    global DATA_Y0, DATA_Y1
    df = pd.read_csv(IN)
    DATA_Y0, DATA_Y1 = float(df["year"].min()), float(df["year"].max())
    frames, report = [], []
    for sex in (1, 2):
        label, cut, params, fits = fit_sex(df, sex)
        for (reg, name), f in fits.items():
            tail = next(t for p, _, t in params if p == name)
            report.append((label, reg, name, tail, f.r2))
        frames.append(build_grid(sex, cut, params, fits, y0, y1))
    full = pd.concat(frames, ignore_index=True)
    full["model"] = np.where(full["sex"] == 1, "dpln", "mixture")
    cols = ["year", "sex", "age", "cohort", "model",
            "alpha", "beta", "nu", "tau", "mu1", "mu2", "sig1", "sig2", "w"]
    full = full.reindex(columns=cols)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    full.to_csv(OUT, index=False)

    print(f"{'sex':6s} {'regime':5s} {'param':7s} {'tail':6s} {'R2':>6s}")
    print("-" * 36)
    for r in report:
        print(f"{r[0]:6s} {r[1]:5s} {r[2]:7s} {r[3]:6s} {r[4]:6.3f}")
    print(f"\nwrote {len(full)} rows -> {OUT}  (years {y0}-{y1}, "
          f"cohorts {int(full.cohort.min())}-{int(full.cohort.max())})")
    if preview:
        import extrapolate_preview as pv
        pv.render(df, full, DATA_Y0, DATA_Y1)


if __name__ == "__main__":
    kw = {}
    for flag, key, cast in [("--y0", "y0", int), ("--y1", "y1", int)]:
        if flag in sys.argv:
            kw[key] = cast(sys.argv[sys.argv.index(flag) + 1])
    kw["preview"] = "--preview" in sys.argv
    main(**kw)
