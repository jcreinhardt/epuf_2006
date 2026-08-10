"""Ordinal-transform experiment on the GKOS (2021) benchmark earnings process.

Simulates the benchmark process (Table IV spec 6 + appendix Table D.III) twice with
IDENTICAL shock draws but two different deterministic profiles g(t):

  g_bench(t) = 2.581 + 0.812 t - 0.185 t^2,  t = (age-24)/10   (GKOS estimate)
  g_flat(t)  = 2.581                                            (no lifecycle growth)

Each panel is then ordinally transformed age by age: positive earnings are replaced
by the same-rank quantile of a lognormal target with log-mean g_bench(t) and log-
variance rising linearly from 0.50 at age 25 to 1.10 at age 60 (mimicking the
within-cohort variance profile in GKOS Fig. D.3). Zeros (nonemployment) stay zero.

Because g(t) is a within-age additive constant in logs and no component of the
process feeds back on the earnings level, within-age ranks are invariant to g(t),
so the two transformed panels should be *identical element by element*. The script
verifies that and plots GKOS-style estimation moments for raw and transformed
panels side by side.

Run from the project root:  python code/dynamics/simulate_gkos_ordinal.py
Output: output/dynamics/gkos_ordinal_transform_moments.{pdf,png}
"""

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import norm

OUT = "output/dynamics"

# --- GKOS benchmark parameters (Table IV spec 6; Table D.III) -----------------
RHO = 0.959
P_Z, MU_Z1, SIG_Z1, SIG_Z2 = 0.407, -0.085, 0.364, 0.069
MU_Z2 = -P_Z * MU_Z1 / (1 - P_Z)
SIG_Z0 = 0.714
P_E, MU_E1, SIG_E1, SIG_E2 = 0.130, 0.271, 0.285, 0.037
MU_E2 = -P_E * MU_E1 / (1 - P_E)
SIG_A, SIG_B, CORR_AB = 0.300, 0.196 / 10, 0.768
LAMBDA = 0.0001
NU_A, NU_B, NU_C, NU_D = -3.353, -0.859, -5.034, -2.895
G0, G1, G2 = 2.581, 0.812, -0.185

N = 50_000
AGES = np.arange(25, 61)                      # 25..60, GKOS working span
T = (AGES - 24) / 10                          # normalized age

# Lognormal targets for the ordinal transform (same targets for both panels)
TARGET_MU = G0 + G1 * T + G2 * T**2           # log-mean matches GKOS g(t)
TARGET_VAR = 0.50 + (1.10 - 0.50) * (AGES - 25) / (60 - 25)


def g_bench(t):
    return G0 + G1 * t + G2 * t**2


def g_flat(t):
    return np.full_like(t, G0)


def simulate_common(rng):
    """Draw the g-free part of log earnings x_ia and nonemployment nu_ia once."""
    cov = CORR_AB * SIG_A * SIG_B
    ab = rng.multivariate_normal([0, 0], [[SIG_A**2, cov], [cov, SIG_B**2]], N)
    alpha, beta = ab[:, 0], ab[:, 1]

    x = np.empty((N, AGES.size))
    nu = np.empty((N, AGES.size))
    z = SIG_Z0 * rng.standard_normal(N)
    for j, t in enumerate(T):
        if j > 0:
            pick = rng.random(N) < P_Z
            eta = np.where(pick, MU_Z1 + SIG_Z1 * rng.standard_normal(N),
                           MU_Z2 + SIG_Z2 * rng.standard_normal(N))
            z = RHO * z + eta
        pick = rng.random(N) < P_E
        eps = np.where(pick, MU_E1 + SIG_E1 * rng.standard_normal(N),
                       MU_E2 + SIG_E2 * rng.standard_normal(N))
        xi = NU_A + NU_B * t + NU_C * z + NU_D * t * z
        p_nu = 1 / (1 + np.exp(-xi))
        hit = rng.random(N) < p_nu
        dur = np.minimum(1.0, rng.exponential(1 / LAMBDA, N))
        nu[:, j] = np.where(hit, dur, 0.0)
        x[:, j] = alpha + beta * t + z + eps
    return x, nu


def earnings(gfun, x, nu):
    """Levels Y_ia = (1-nu) * exp(g(t) + x)."""
    return (1 - nu) * np.exp(gfun(T)[None, :] + x)


def ordinal_transform(Y):
    """Per age: map positive earnings to same-rank lognormal target quantiles."""
    out = np.zeros_like(Y)
    for j in range(AGES.size):
        pos = Y[:, j] > 0
        n = pos.sum()
        ranks = np.empty(n)
        ranks[np.argsort(Y[pos, j], kind="stable")] = np.arange(1, n + 1)
        u = (ranks - 0.5) / n
        out[pos, j] = np.exp(TARGET_MU[j] + np.sqrt(TARGET_VAR[j]) * norm.ppf(u))
    return out


# --- GKOS-style moments -------------------------------------------------------

def logmean_by_age(Y):
    return np.array([np.log(Y[Y[:, j] > 0, j]).mean() for j in range(AGES.size)])


def logvar_by_age(Y):
    return np.array([np.log(Y[Y[:, j] > 0, j]).var() for j in range(AGES.size)])


def growth_by_re(Y, nbins=40):
    """Quantile moments of 5-year log growth by recent-earnings percentile.

    Base ages 30..50; RE = mean of the previous 5 years' levels (incl. zeros),
    ranked within base age; growth requires positive earnings at t and t+5.
    """
    re_pct, dy = [], []
    for j in np.where((AGES >= 30) & (AGES <= 50))[0]:
        re = Y[:, j - 5:j].mean(axis=1)
        ok = (re > 0) & (Y[:, j] > 0) & (Y[:, j + 5] > 0)
        r = np.empty(ok.sum())
        r[np.argsort(re[ok], kind="stable")] = np.arange(ok.sum())
        re_pct.append(np.floor(r / ok.sum() * nbins))
        dy.append(np.log(Y[ok, j + 5]) - np.log(Y[ok, j]))
    re_pct, dy = np.concatenate(re_pct), np.concatenate(dy)

    std, kel, cs = np.full((3, nbins), np.nan)
    for b in range(nbins):
        d = dy[re_pct == b]
        p = np.percentile(d, [2.5, 10, 25, 50, 75, 90, 97.5])
        std[b] = d.std()
        kel[b] = (p[4 + 1] + p[1] - 2 * p[3]) / (p[5] - p[1])
        cs[b] = (p[6] - p[0]) / (p[4] - p[2]) - 2.91
    return std, kel, cs


def lifetime_growth(Y, nbins=100):
    """log(avg Y at 51-55 / avg Y at 25-29) by lifetime-earnings percentile bin."""
    le = Y.mean(axis=1)
    order = np.argsort(le, kind="stable")
    bins = np.array_split(order, nbins)
    lo = np.where(AGES <= 29)[0]
    hi = np.where((AGES >= 51) & (AGES <= 55))[0]
    out = np.full(nbins, np.nan)
    for b, idx in enumerate(bins):
        y0, y1 = Y[np.ix_(idx, lo)].mean(), Y[np.ix_(idx, hi)].mean()
        if y0 > 0 and y1 > 0:
            out[b] = np.log(y1) - np.log(y0)
    return out


def all_moments(Y):
    std, kel, cs = growth_by_re(Y)
    return {"logmean": logmean_by_age(Y), "logvar": logvar_by_age(Y),
            "std5": std, "kelley5": kel, "cs5": cs, "ltg": lifetime_growth(Y)}


def main():
    rng = np.random.default_rng(20260807)
    x, nu = simulate_common(rng)                 # one set of draws for both g's

    Y_bench, Y_flat = earnings(g_bench, x, nu), earnings(g_flat, x, nu)
    Yt_bench, Yt_flat = ordinal_transform(Y_bench), ordinal_transform(Y_flat)

    diff = np.abs(Yt_bench - Yt_flat).max()
    print(f"max |transformed(bench) - transformed(flat)| = {diff:.3e}")
    assert diff == 0.0, "transformed panels should be identical"

    mom = {k: all_moments(Y) for k, Y in
           [("raw bench", Y_bench), ("raw flat", Y_flat),
            ("transf bench", Yt_bench), ("transf flat", Yt_flat)]}

    style = {"raw bench":    dict(color="0.45", ls="-",  lw=2.2),
             "raw flat":     dict(color="0.45", ls="--", lw=1.4),
             "transf bench": dict(color="#1f77b4", ls="-",  lw=2.6),
             "transf flat":  dict(color="#ff7f0e", ls=(0, (2, 3)), lw=1.6)}
    panels = [
        ("logmean", "Mean log earnings by age", AGES, "age"),
        ("logvar", "Within-cohort variance of log earnings", AGES, "age"),
        ("std5", r"Std. dev. of $\Delta^5 \log Y$", None, "RE percentile"),
        ("kelley5", r"Kelley skewness of $\Delta^5 \log Y$", None, "RE percentile"),
        ("cs5", r"Crow-Siddiqui excess kurtosis of $\Delta^5 \log Y$", None, "RE percentile"),
        ("ltg", r"Lifetime growth $\log \bar Y_{51-55} - \log \bar Y_{25-29}$",
         None, "lifetime-earnings percentile"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for ax, (key, title, xs, xlab) in zip(axes.ravel(), panels):
        for name, m in mom.items():
            v = m[key]
            xv = xs if xs is not None else np.linspace(0, 100, v.size)
            ax.plot(xv, v, label=name, **style[name])
        ax.set_title(title, fontsize=10)
        ax.set_xlabel(xlab, fontsize=9)
        ax.tick_params(labelsize=8)
    axes[0, 0].legend(fontsize=8, frameon=False)
    fig.suptitle("GKOS benchmark process, two g(t) profiles, raw vs. ordinally "
                 f"transformed  (transformed panels identical: max diff = {diff:.0e})",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    for ext in ("pdf", "png"):
        fig.savefig(f"{OUT}/gkos_ordinal_transform_moments.{ext}", dpi=200)
    print(f"wrote {OUT}/gkos_ordinal_transform_moments.pdf/.png")

    # Slide cut: the mean panel and the lifetime-growth panel only. The point needs one
    # moment the shift moves (the mean) and one it does not own (lifetime growth by
    # lifetime-earnings percentile): raw panels differ across g(t), transformed overlap
    # exactly. Slide type sizes; series colors from the validated palette.
    slide_rc = {"font.size": 14, "axes.titlesize": 16, "axes.labelsize": 14,
                "xtick.labelsize": 13, "ytick.labelsize": 13, "legend.fontsize": 11}
    sstyle = {"raw bench":    dict(color="0.55", ls="-",  lw=2.0),
              "raw flat":     dict(color="0.55", ls="--", lw=1.6),
              "transf bench": dict(color="#2a78d6", ls="-", lw=2.8),
              "transf flat":  dict(color="#eb6834", ls=(0, (2, 3)), lw=2.2)}
    with plt.rc_context(slide_rc):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.6, 3.1))
        for name, m in mom.items():
            ax1.plot(AGES, m["logmean"], label=name, **sstyle[name])
            v = m["ltg"]
            ax2.plot(np.linspace(0, 100, v.size), v, label=name, **sstyle[name])
        ax1.set_title("Mean log earnings")
        ax1.set_xlabel("age")
        ax2.set_title("Lifetime growth")
        ax2.set_xlabel("lifetime-earnings percentile")
        ax2.legend(frameon=False, loc="lower right")
        fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(f"{OUT}/gkos_ordinal_slide.{ext}", dpi=200)
    print(f"wrote {OUT}/gkos_ordinal_slide.pdf/.png")


if __name__ == "__main__":
    main()
