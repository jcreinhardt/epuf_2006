"""The GKOS (2021) earnings process with a richer NONEMPLOYMENT block: state dependence by sex, and an absorbing
exit state. Library only (no CLI); `estimate_nonemp.py` fits it.

Everything about EARNINGS is GKOS's benchmark, untouched (gcohort_model: z AR(1) with mixture innovations, HIP
(alpha, beta), transitory mixture eps) with this project's re-estimated, re-levelled g(t). What changes is who has
zero earnings. Each year a person is in one of three states, employed (E), temporarily not employed (N), or
absorbed (A), and the order of events at age a (t = (a-24)/10) is:

  1. death (TR2023 period life tables, uniform, as in transition_rates.py): zero from the year after death on;
  2. ABSORBING EXIT -- retirement / incapacitation / leaving covered work for good:
         h(a, z) = logistic(k_sex + k_t*t + k_t2*t^2 + k_55*(a-55)_+/10 + k_62*(a-62)_+/10 + k_z*z)
     once absorbed, zero earnings in every later year;
  3. TEMPORARY NONEMPLOYMENT, GKOS's logit with the intercept made a function of SEX x LAST YEAR'S STATUS:
         p(a, z, s, e_{a-1}) = logistic(a_{s, e_{a-1}} + b*t + (c + d*t)*x),  (b, c, d) = GKOS's,
     where the index x is GKOS's z with two optional changes,
         x = min(z, zbar_s) + kappa*(alpha + beta*t):
     a CAP (above zbar_s everybody faces the same probability; zbar = inf is GKOS) and a loading on the HIP
     component alpha + beta*t (kappa = 0 is GKOS). The state space of the block is (z, alpha, beta, e_{a-1});
  4. earnings exp(g(t) + alpha + beta*t + z + eps) if none of the above, else zero.

GKOS is nested: a_{s,E} = a_{s,N} = -3.353 and k -> -inf. The status at 19, e_19, is an initial condition the
lagged intercept needs: not employed with probability logistic(pi_s), or, if pi_s is NaN, by one burn-in year --
the temporary logit at age 19 with the EMPLOYED intercept and z at 20 (`p_init`), which adds no parameter.

All randomness is drawn ONCE (`draw_shocks`) and held fixed across parameter values (common random numbers), so the
simulated moments are a deterministic function of theta.
"""
import numpy as np

NAMES = ["a_m_E", "a_m_N", "a_f_E", "a_f_N",            # temporary-nonemployment intercepts: sex x lagged status
         "k_m", "k_f", "k_t", "k_55", "k_62", "k_z",      # absorbing-exit hazard
         "pi_m", "pi_f",                                   # logit P(not employed at 19)
         "k_t2",                                            # hazard: quadratic age term
         "kappa", "zbar_m", "zbar_f"]                        # index: HIP loading, cap on z by sex (appended, so
                                                            # shorter parameter files pad with GKOS_START)
A0, A1 = 20, 65


def logistic(x):
    return 1.0 / (1.0 + np.exp(-x))


def draw_shocks(E, n, ages, seed):
    """Every random number the simulation uses, (n, T) unless noted. E = gcohort_model."""
    rng = np.random.default_rng(seed)
    T = len(ages)
    cov = E.CORR_AB * E.SIG_A * E.SIG_B
    ab = rng.multivariate_normal([0, 0], [[E.SIG_A ** 2, cov], [cov, E.SIG_B ** 2]], n)
    z = np.empty((n, T))
    z[:, 0] = E.entry_sd(int(ages[0])) * rng.standard_normal(n)
    for j in range(1, T):
        pick = rng.random(n) < E.P_Z
        z[:, j] = E.RHO * z[:, j - 1] + np.where(pick, E.MU_Z1 + E.SIG_Z1 * rng.standard_normal(n),
                                                 E.MU_Z2 + E.SIG_Z2 * rng.standard_normal(n))
    pick = rng.random((n, T)) < E.P_E
    eps = np.where(pick, E.MU_E1 + E.SIG_E1 * rng.standard_normal((n, T)),
                   E.MU_E2 + E.SIG_E2 * rng.standard_normal((n, T)))
    return dict(alpha=ab[:, 0], beta=ab[:, 1], z=z, eps=eps, u_nu=rng.random((n, T)), u_abs=rng.random((n, T)),
                u_mort=rng.random((n, T)), u_init=rng.random(n))


def employment(theta, sh, sex, ages, q, E):
    """(n, T) bool employed, given parameters, the fixed shocks and q(x) at ages."""
    th = dict(zip(NAMES, theta))
    s = "m" if sex == 1 else "f"
    p = dict(a_E=th[f"a_{s}_E"], a_N=th[f"a_{s}_N"], k=th[f"k_{s}"], k_t=th["k_t"], k_55=th["k_55"],
             k_62=th["k_62"], k_z=th["k_z"], pi=th[f"pi_{s}"], k_t2=th["k_t2"], kappa=th["kappa"],
             zbar=th[f"zbar_{s}"])
    return employment_one(p, sh, ages, q, E)


def employment_one(p, sh, ages, q, E, b=None, c=None, d=None):
    """One sex, parameters as a dict (a_E, a_N, k, k_t, k_t2, k_55, k_62, k_z, pi, kappa, zbar). Both logits load on
    the index x = min(z, zbar) + kappa*(alpha + beta*t) (kappa = 0, zbar = inf: GKOS's z). b, c, d default to
    GKOS's temporary-nonemployment slopes."""
    b = E.NU_B if b is None else b
    c = E.NU_C if c is None else c
    d = E.NU_D if d is None else d
    t = (np.asarray(ages, float) - 24.0) / 10.0
    z = np.minimum(sh["z"], p.get("zbar", np.inf)) \
        + p.get("kappa", 0.0) * (sh["alpha"][:, None] + sh["beta"][:, None] * t[None, :])
    n, T = z.shape
    dies = sh["u_mort"] < q[None, :]
    alive = np.cumsum(np.concatenate([np.zeros((n, 1), bool), dies[:, :-1]], 1), 1) == 0
    age = np.asarray(ages, float)
    haz = logistic(p["k"] + p["k_t"] * t[None, :] + p.get("k_t2", 0.0) * t[None, :] ** 2
                   + p["k_55"] * np.maximum(age - 55, 0)[None, :] / 10
                   + p["k_62"] * np.maximum(age - 62, 0)[None, :] / 10 + p["k_z"] * z)
    absorbed = np.cumsum(sh["u_abs"] < haz, 1) > 0
    prev = ~(sh["u_init"] < p_init(p, z, b, c, d))  # employed at 19?
    emp = np.empty((n, T), bool)
    for j in range(T):
        a = np.where(prev, p["a_E"], p["a_N"])
        nu = sh["u_nu"][:, j] < logistic(a + b * t[j] + (c + d * t[j]) * z[:, j])
        emp[:, j] = ~nu & ~absorbed[:, j] & alive[:, j]
        prev = emp[:, j]
    return emp


def p_init(p, z, b, c, d):
    """P(not employed at 19): logistic(pi), or with pi = NaN one burn-in year from 'employed at 18' (z at 20)."""
    if not np.isnan(p["pi"]):
        return logistic(p["pi"])
    t19 = (19 - 24.0) / 10
    return logistic(p["a_E"] + b * t19 + (c + d * t19) * z[:, 0])


def earnings(theta, sh, sex, ages, q, E, g, logP):
    """(n, T) nominal earnings; g and logP are (T,) for this cohort x sex."""
    emp = employment(theta, sh, sex, ages, q, E)
    t = (np.asarray(ages, float) - 24.0) / 10.0
    logy = (g + logP)[None, :] + sh["alpha"][:, None] + sh["beta"][:, None] * t[None, :] + sh["z"] + sh["eps"]
    return np.where(emp, np.exp(logy), 0.0)


GKOS_START = dict(a_m_E=-3.353, a_m_N=-3.353, a_f_E=-3.353, a_f_N=-3.353,
                  k_m=-12.0, k_f=-12.0, k_t=0.0, k_55=0.0, k_62=0.0, k_z=0.0, pi_m=0.0, pi_f=0.0, k_t2=0.0,
                  kappa=0.0, zbar_m=np.inf, zbar_f=np.inf)
