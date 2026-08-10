#!/usr/bin/env python
"""Selection bias in the CMS (JF 2025) earnings process: observed mean log earnings
does NOT equal the gtilde(t) profile the process is built to hit.

CMS replace GKOS's latent g(t) with a cohort x gender cubic fitted to GKSW (2017) mean
log earnings, then simulate

    Y = Works * exp(Y_log) * (1 - Unemployed) / (1 - mean(Unemployed))
    Y_log = gtilde(age) + alpha + beta*t + z + e
            - var(z)/2 - var(alpha + beta*t)/2 - var(e)/2        (their Jensen term)

Everything here mirrors source/derived/simulation/{Simulation,IncomeShockFun}.m in the
replication package: the same GKOS parameters, the same cross-sectionally-evaluated
variance terms, the same 10%/20% never-work shares, and the same state-dependent
unemployment logit.

THE POINT: Unemployed is drawn with probability logit(a + b t + c z + d z t), c = -5.034,
so nonemployment falls on LOW-z workers. Conditioning on positive earnings therefore
selects on the persistent component, and E[log Y | observed] sits ABOVE gtilde by that
selection term -- a wedge no level correction can remove, because gtilde is a LATENT
profile while the data moment is measured on survivors.

Run from the project root:  python code/dynamics/simulate_cms_selection.py
Output: output/dynamics/cms_selection_bias.{pdf,png}
"""
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "output/dynamics"
LIFECYCLE = "replication_repos/CMS/datastore/derived/lifecycle_income"

# --- GKOS parameters, verbatim from Simulation.m -----------------------------
RHO_Z = 0.959
PROB_Z, MU_Z1, SIG_Z1, SIG_Z2 = 0.407, -0.085, 0.364, 0.069
SIG_Z = 0.714                                   # sd of the initial z draw
PROB_E, MU_E1, SIG_E1, SIG_E2 = 0.130, 0.271, 0.285, 0.037
SIG_ALPHA, SIG_BETA, CORR_AB = 0.300, 0.196 / 10, 0.786
LAMBDA = 0.0001
PAR_A, PAR_B, PAR_C, PAR_D = -3.353, -0.859, -5.034, -2.895
MU_Z2 = -PROB_Z * MU_Z1 / (1 - PROB_Z)
MU_E2 = -PROB_E * MU_E1 / (1 - PROB_E)
ZERO_SHARE = {1: 0.10, 2: 0.20}                 # never-work shares (men, women)

# create_year_for_each_age sets year = cohort + age - 25, and the merge onto the SSA average
# keeps only matched years, so most "cohorts" are fitted on a PARTIAL age range. Cohorts
# 1957-1983 are the ones with all 31 ages present; 1960 sits comfortably inside that.
COHORT = 1960
SEX = 2                                         # women
AGES = np.arange(25, 56)
GKSW = "replication_repos/CMS/datastore/raw/lifecycle_income/orig/gksw2017.xlsx"
N = 200_000
SLIDE_RC = {"font.size": 14, "axes.titlesize": 17, "axes.labelsize": 14,
            "xtick.labelsize": 13, "ytick.labelsize": 13, "legend.fontsize": 12}


def gtilde(sex, cohort=COHORT):
    """CMS's deterministic profile: cons + b1*age + b2*age^2 + b3*age^3.

    Simulation.m rescales trend2 by 10 and trend3 by 100 and then divides age^2 by 10 and
    age^3 by 100, so the rescalings cancel and this is exactly the fitted cubic from
    create_lifecycle_income_parameters.do (which regresses on age, age^2, age^3)."""
    name = "male" if sex == 1 else "female"
    b = pd.read_stata(f"{LIFECYCLE}/lifecycle_income_{name}.dta")[f"c_{cohort}"].to_numpy()
    b1, b2, b3, cons = b
    return cons + b1 * AGES + b2 * AGES**2 + b3 * AGES**3


def gksw_points(sex=SEX, cohort=COHORT):
    """The raw GKSW (2017) profile the cubic is fitted to, rebuilt exactly as the .do does:
    year = cohort + age - 25, earnings = exp(log)/1000, then divided by the SSA average
    earnings of that year and logged."""
    name = "male" if sex == 1 else "female"
    x = pd.ExcelFile(GKSW)
    ssa = x.parse("data_mean_2013d_impute")[["year", "ssa"]]
    d = x.parse(f"{name}_3")[["age", f"c_{cohort}"]].rename(columns={f"c_{cohort}": "logY"})
    d["year"] = cohort + d["age"] - 25
    d = d.merge(ssa, on="year", how="inner").dropna()
    return d["age"].to_numpy(), np.log(np.exp(d["logY"]) / 1000 / d["ssa"]).to_numpy()


def simulate(sex, rng):
    """Return observed mean log earnings by age under CMS's process."""
    cov = CORR_AB * SIG_ALPHA * SIG_BETA
    ab = rng.multivariate_normal([0, 0], [[SIG_ALPHA**2, cov], [cov, SIG_BETA**2]], N)
    alpha, beta = ab[:, 0], ab[:, 1]
    works = rng.random(N) > ZERO_SHARE[sex]

    g = gtilde(sex)
    z = SIG_Z * rng.standard_normal(N)
    obs_meanlog = np.empty(AGES.size)

    for j, age in enumerate(AGES):
        t = (age - 24) / 10
        if j > 0:                                        # AR(1) with mixture innovations
            pick = rng.random(N) < PROB_Z
            z = RHO_Z * z + np.where(pick, MU_Z1 + SIG_Z1 * rng.standard_normal(N),
                                     MU_Z2 + SIG_Z2 * rng.standard_normal(N))
        pick = rng.random(N) < PROB_E
        e = np.where(pick, MU_E1 + SIG_E1 * rng.standard_normal(N),
                     MU_E2 + SIG_E2 * rng.standard_normal(N))

        # state-dependent unemployment: PROB rises as z FALLS (PAR_C < 0)
        odds = np.exp(PAR_A + PAR_B * t + PAR_C * z + PAR_D * z * t)
        prob_u = odds / (1 + odds)
        dur = np.minimum(1.0, rng.exponential(1 / LAMBDA, N))
        unemployed = np.where(rng.random(N) < prob_u, dur, 0.0)

        hip = alpha + beta * t
        y_log = (g[j] + hip + z + e
                 - z.var() / 2 - hip.var() / 2 - e.var() / 2)      # CMS Jensen term
        Y = works * np.exp(y_log) * (1 - unemployed) / (1 - unemployed.mean())

        pos = Y > 0
        obs_meanlog[j] = np.log(Y[pos]).mean()
    return g, obs_meanlog


def main():
    rng = np.random.default_rng(5)
    g, obs = simulate(SEX, rng)
    ages_raw, y_raw = gksw_points()

    with plt.rc_context(SLIDE_RC):
        fig, ax = plt.subplots(figsize=(5.2, 2.24))
        ax.plot(AGES, obs, color="#eb6834", lw=2.8, ls=":")
        ax.plot(AGES, g, color="#1a1a19", lw=2.4)
        ax.scatter(ages_raw, y_raw, s=26, facecolor="none", edgecolor="#1a1a19",
                   linewidths=1.2, zorder=3)
        # direct labels rather than a legend box: the legend row costs ~a third of the
        # canvas height, and on a slide that is the height the curves need.
        ax.set_xlim(24.5, 63)
        ax.text(56.2, obs[-1], "CMS", color="#eb6834", va="center", fontsize=13,
                fontweight="bold")
        ax.text(56.2, g[-1], "target", color="#1a1a19", va="center", fontsize=13,
                fontweight="bold")
        ax.set_xticks([25, 30, 35, 40, 45, 50, 55])
        ax.set_xlabel("age")
        ax.set_ylabel("log earnings")
        ax.margins(y=0.10)
        fig.tight_layout()
    fig.savefig(f"{OUT}/cms_selection_bias.pdf")
    fig.savefig(f"{OUT}/cms_selection_bias.png", dpi=150)
    plt.close(fig)
    print(f"wrote {OUT}/cms_selection_bias.pdf and .png  "
          f"(women, cohort {COHORT}, {len(ages_raw)} data points, N={N})")

    d = obs - g
    print(f"\n{'age':>4} {'target':>8} {'CMS obs':>9} {'gap':>7}")
    for j in range(0, AGES.size, 5):
        print(f"{AGES[j]:>4} {g[j]:>8.3f} {obs[j]:>9.3f} {d[j]:>+7.3f}")
    print(f"\ngap {d.min():+.3f} .. {d.max():+.3f} log points (mean {d.mean():+.3f})")
    print(f"cubic vs raw data: max |resid| = {np.abs(np.interp(ages_raw, AGES, g) - y_raw).max():.3f}")


if __name__ == "__main__":
    main()
