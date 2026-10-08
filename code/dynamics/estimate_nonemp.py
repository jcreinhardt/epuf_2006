#!/usr/bin/env python
"""SMM for the nonemployment block of `nonemp_model.py` (state-dependent intercepts by sex x last year's status, plus
an absorbing exit hazard), against the EPUF moments behind the transition figures (`transition_rates.analyze`), one
birth cohort, both sexes jointly.

MOMENTS: every statistic drawn in the findings doc EXCEPT the arc-percent ones (chg_arc, and the large-arc-change
events evt_*), entries and exits always summed into one count:

  block a  exit h1, exit h5, cumrank h1, cumrank h5
  block b  persist h1, persist h5, chg_abs h1, chg_abs h5
  block c  lifetime, yrs_hist, byage_lq, fwd, fwd_dec (exit/again), trans_cum    [overview folded in here:
           employment by lifetime earnings IS the age-profile-vs-earnings question]
  block d  trans_cur, trans_life, trans_fut_lq
Employment by age (byage) is NOT a target: it is the weighted average of byage_lq, so it would count that twice.

WEIGHTS (`--weights`): diagonal, and in every scheme each block carries 1/4, each figure an equal share of its block,
and each moment within a figure an equal share of the figure (bins with fewer than MIN_N data observations dropped):

  spread GKOS's scaled arc-percent deviation per moment, arc(x, y) = (x - y) / (0.5 (|x| + |y|) + psi_f),
       psi_f = the 10th percentile of |data moments| in the figure (GKOS 2021, App. D.3: keeps near-zero moments from
       exploding). Each FIGURE is then divided by ONE scale, the spread inherent in its own data: the root mean square
       over its moments of arc(data_m, mean of the figure's data moments), both sexes pooled. So a figure's term is
       its mean squared arc-percent miss relative to how much the figure itself varies, and every moment within a
       figure counts equally. Measures the figure's variation, not its sampling uncertainty.
  gkos GKOS's scaled arc-percent deviation per moment (as in spread), and each figure divided by ITS OWN LOSS AT
       GKOS + mortality (the mean squared arc-percent deviation over the figure's moments at a = -3.353 for both
       sexes). So every figure enters as the ratio of its loss to GKOS's loss on it, J(GKOS) = 1, and a figure's
       contribution is (its block/figure weight) x (how much of GKOS's miss on it remains).
  gkospp  the pp moments with plain differences, and each FIGURE x SEX divided by its own loss at GKOS + mortality
       (mean squared pp gap over that figure's moments for that sex at a = -3.353). Each figure x sex enters as the
       share of GKOS's miss on it that remains, sexes half of each figure, so J(GKOS) = 1. Within a figure x sex the
       units cancel, so only the within-figure transforms of `pp` matter.
  arc  as spread, but the figure's scale is the median bootstrap sd of the arc-percent deviation (sampling noise):
       precise figures then dominate, as under sd.
  pp   (default) ONE common unit for every figure, percentage points of a share. Shares are used as they are; the
       counts are annualised into a share -- trans_cum / trans_cur / trans_fut_lq (switches between a and 65) divided
       by 65-a, trans_life (20..65) by 45 -- and yrs_hist becomes its CDF. J = mean squared gap in pp, per figure.
  mad  the pp moments, each figure divided by the robust spread of its own data moments (1.4826 x MAD across bins,
       both sexes pooled), so a figure's term is its gap relative to how much the figure varies.
  sd   each moment divided by its own bootstrap sd (60 person-level replications, floored at a quarter of the
       figure's median): a mean squared t-statistic. Precise figures then dominate J whatever their nominal weight.

Common random numbers (`nonemp_model.draw_shocks`). Default: Nelder-Mead from --start, restarted --rounds times with a
halved simplex. `--tiktak N` instead runs the TikTak multistart of Arnoud, Guvenen and Kleineberg (2022) (`tiktak.py`):
N Sobol' points over BOUNDS, the best --keep as seeds (default one batch of --workers), parallel local searches
(--local nm|powell) each started from a convex combination of its seed and the incumbent, the weight rising as
(i/keep)^--gamma, until the last two different incumbents agree to --tol, then a tight polish. Every local minimum
found is written to nonemp_tiktak_yob<YOB><tag>.csv (AGK's wisdom file), so the local optima the objective has are on
record, not just the best one.

SPECS (`--spec`): `full` is the 12-parameter model above. `sexint` is GKOS + mortality with ONE change, the temporary
nonemployment intercept made sex-specific (a_m, a_f; no lagged status, no absorbing state, b/c/d still GKOS's): two
parameters, nested in `full` as a_{s,E} = a_{s,N} = a_s and k -> -inf. Its outputs carry the suffix `_sexint`.
Two specs add LAST YEAR'S STATUS to that intercept, still with no absorbing state and GKOS's b/c/d:
  sexlag_add  a_{s,e} = a_s + g_N * 1[not employed last year]   (sex and status additively separable; 3 parameters)
  sexlag      a_{s,e} free for each sex x status                 (full interaction; 4 parameters)
Their status at 19 comes from one burn-in year (nonemp_model.p_init), so no initial-condition parameter.
  sexlag_abs  sexlag_add plus a PERMANENT EXIT: each year from 20, logistic(k + k_t t) moves a person into the
              absorbing state (zero earnings through 65), the same for both sexes and independent of z (5 parameters;
              k_55 = k_62 = k_z = 0 in nonemp_model's hazard)
  sexlag_absq   sexlag_abs with a quadratic age term in the exit, logistic(k + k_t t + k_t2 t^2)   (6 parameters)
  sexlag_abs55  sexlag_abs with a kink at 55, logistic(k + k_t t + k_55 (age-55)_+/10)             (6 parameters)
Two extensions of sexlag_absq change what the temporary logit loads on (nonemp_model: x = min(z, zbar_s) + kappa (alpha + beta t)):
  absq_alpha    + kappa, a loading on the HIP component alpha + beta t                             (7 parameters)
  absq_zcap     + zbar_m, zbar_f, a cap on z per sex: above it everybody faces the same probability (8 parameters)
Two more replace the last-year's-status DUMMY of sexlag_absq by past attachment (nonemp_model.attachment; no kappa):
  absq_ten      + ten_K: the intercept is a_s + g_N (1 - min(L, ten_K)/ten_K), L = consecutive years employed up to
                last year (a ramp; ten_K <= 1 is the dummy)                                        (7 parameters)
  absq_ewma     + ten_delta: a_s + g_N (1 - A), A = ten_delta A_{-1} + (1 - ten_delta) e_{-1}, an exponentially
                weighted employment history that years out erode as years in build it (0 = dummy) (7 parameters)
  absq_ten3     the ramp with its cap FIXED at 3 years                                             (6 parameters)
  absq_rho      + ten_rho: the dummy kept, and the earnings slope attenuated with tenure,
                (c + d t) x (1 - ten_rho min(L, 10)/10)                                           (7 parameters)
  alpha_rho     absq_alpha + ten_rho (the fixed effect and the attenuation together)               (8 parameters)
  absq_grad     + ten_gam: the dummy kept (step at 0 -> 1) and a gradient after it, - ten_gam log(L)/log(10),
                ten_gam = the gain in attachment at ten years of tenure (0 = dummy)                (7 parameters)
  absq_hyp      + ten_hyp: the same with the bounded shape - ten_hyp (1 - 1/L)                     (7 parameters)
  alpha_grad    absq_alpha + ten_gam (fixed effect and gradient together)                          (8 parameters)

Run from anywhere. The data inputs come from the database and microsimulation under --root the first time and are
cached to processed_data/nonemp_inputs_yob<YOB>.npz (`Problem`); a checkout with that file and no database (the
cluster) runs from the file; estimate_nonemp.sbatch is the Slurm wrapper. Nothing else here touches the database.
    python code/dynamics/estimate_nonemp.py [--yob 1932] [--n-sim 20000] [--maxfev 2500]
        python code/dynamics/estimate_nonemp.py --spec sexint [--weights pp|mad|sd]
Output: output/dynamics/nonemp_params_yob<YOB>.csv            (parameter, start, estimate)
        output/dynamics/nonemp_fit_yob<YOB>.csv               (block, figure, J GKOS+mortality, J fitted)
        output/dynamics/nonemp_moments_yob<YOB>.csv           (data moments, bootstrap sd, weight)
        output/dynamics/transition_rates_yob<YOB>_nonemp.csv  (the fitted model through transition_rates.analyze)
        (--spec sexint: the same files with _sexint, and transition_rates_yob<YOB>_sexint.csv;
         a non-default --weights adds _w<scheme>)
"""
import argparse
import contextlib
import io
import os
import sys
import time

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")          # one thread per process: tiktak forks workers
import numpy as np
import pandas as pd
from scipy.optimize import minimize

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nonemp_model as NM  # noqa: E402
import tiktak as TK  # noqa: E402
import transition_rates as TR  # noqa: E402

OUT_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "output", "dynamics")
BLOCKS = {"a": [("exit", 1), ("exit", 5), ("cumrank", 1), ("cumrank", 5)],
          "b": [("persist", 1), ("persist", 5), ("chg_abs", 1), ("chg_abs", 5)],
          "c": [("lifetime", 0), ("yrs_hist", 0), ("byage_lq", 0), ("fwd", 0), ("fwd_dec", 0), ("trans_cum", 0)],
          "d": [("trans_cur", 0), ("trans_life", 0), ("trans_fut_lq", 0)]}
FIG2BLOCK = {f: b for b, fs in BLOCKS.items() for f in fs}
MIN_N = 50
B_BOOT = 60
SPECS = {"full": NM.NAMES, "sexint": ["a_m", "a_f"], "sexlag_add": ["a_m", "a_f", "g_N"],
         "sexlag": ["a_m_E", "a_m_N", "a_f_E", "a_f_N"], "sexlag_abs": ["a_m", "a_f", "g_N", "k", "k_t"],
         "sexlag_absq": ["a_m", "a_f", "g_N", "k", "k_t", "k_t2"], "sexlag_abs55": ["a_m", "a_f", "g_N", "k", "k_t", "k_55"],
         "absq_alpha": ["a_m", "a_f", "g_N", "k", "k_t", "k_t2", "kappa"],
         "absq_zcap": ["a_m", "a_f", "g_N", "k", "k_t", "k_t2", "zbar_m", "zbar_f"],
         "absq_ten": ["a_m", "a_f", "g_N", "k", "k_t", "k_t2", "ten_K"],
         "absq_ewma": ["a_m", "a_f", "g_N", "k", "k_t", "k_t2", "ten_delta"],
         "absq_ten3": ["a_m", "a_f", "g_N", "k", "k_t", "k_t2"],
         "absq_rho": ["a_m", "a_f", "g_N", "k", "k_t", "k_t2", "ten_rho"],
         "alpha_rho": ["a_m", "a_f", "g_N", "k", "k_t", "k_t2", "kappa", "ten_rho"],
         "absq_grad": ["a_m", "a_f", "g_N", "k", "k_t", "k_t2", "ten_gam"],
         "absq_hyp": ["a_m", "a_f", "g_N", "k", "k_t", "k_t2", "ten_hyp"],
         "alpha_grad": ["a_m", "a_f", "g_N", "k", "k_t", "k_t2", "kappa", "ten_gam"]}
ABSQ = [-6.243, 0.875, 0.820, -4.881, -1.828, 0.601]            # the sexlag_absq estimates (2026-10-07)
START = {"sexint": [-3.353, -3.353], "sexlag_add": [-3.827, 2.031, 0.0], "sexlag": [-3.827, -3.827, 2.031, 2.031],
         "sexlag_abs": [-4.117, 1.880, 1.267, -5.5, 0.3],
         "sexlag_absq": [-6.182, 0.890, 0.800, -5.087, -0.248, 0.0], "sexlag_abs55": [-6.182, 0.890, 0.800, -5.087, -0.248, 0.0],
         "absq_alpha": ABSQ + [0.0], "absq_zcap": ABSQ + [2.0, 2.0],
         "absq_ten": ABSQ + [3.0], "absq_ewma": ABSQ + [0.5], "absq_ten3": ABSQ,
         "absq_rho": ABSQ + [0.3], "alpha_rho": [-5.813, -0.059, 1.374, -6.286, -1.783, 0.688, 0.492, 0.3],
         "absq_grad": ABSQ + [0.5], "absq_hyp": ABSQ + [0.5],
         "alpha_grad": [-5.813, -0.059, 1.374, -6.286, -1.783, 0.688, 0.492, 0.5]}
# search box for --tiktak, per free parameter (intercepts in logit units; k_t per decade of age)
BOUNDS = {"a_m": (-9.0, 0.0), "a_f": (-4.0, 5.0), "g_N": (-2.0, 5.0), "k": (-10.0, -2.0), "k_t": (-2.0, 2.0),
          "k_t2": (-1.0, 1.0), "k_55": (-2.0, 8.0), "kappa": (-1.0, 3.0), "zbar_m": (-2.0, 2.0), "zbar_f": (-2.0, 2.0),
          "ten_K": (1.0, 15.0), "ten_delta": (0.0, 0.95), "ten_rho": (0.0, 1.0), "ten_gam": (-1.0, 4.0),
          "ten_hyp": (-1.0, 6.0),
          "a_m_E": (-9.0, 0.0), "a_m_N": (-9.0, 3.0), "a_f_E": (-4.0, 5.0), "a_f_N": (-4.0, 6.0)}
GKOS = {"sexint": [-3.353] * 2, "sexlag_add": [-3.353, -3.353, 0.0], "sexlag": [-3.353] * 4,
        "sexlag_abs": [-3.353, -3.353, 0.0, -50.0, 0.0], "sexlag_absq": [-3.353, -3.353, 0.0, -50.0, 0.0, 0.0],
        "sexlag_abs55": [-3.353, -3.353, 0.0, -50.0, 0.0, 0.0], "absq_alpha": [-3.353, -3.353, 0.0, -50.0, 0.0, 0.0, 0.0],
        "absq_zcap": [-3.353, -3.353, 0.0, -50.0, 0.0, 0.0, 50.0, 50.0],
        "absq_ten": [-3.353, -3.353, 0.0, -50.0, 0.0, 0.0, 1.0], "absq_ewma": [-3.353, -3.353, 0.0, -50.0, 0.0, 0.0, 0.0],
        "absq_ten3": [-3.353, -3.353, 0.0, -50.0, 0.0, 0.0], "absq_rho": [-3.353, -3.353, 0.0, -50.0, 0.0, 0.0, 0.0],
        "alpha_rho": [-3.353, -3.353, 0.0, -50.0, 0.0, 0.0, 0.0, 0.0],
        "absq_grad": [-3.353, -3.353, 0.0, -50.0, 0.0, 0.0, 0.0], "absq_hyp": [-3.353, -3.353, 0.0, -50.0, 0.0, 0.0, 0.0],
        "alpha_grad": [-3.353, -3.353, 0.0, -50.0, 0.0, 0.0, 0.0, 0.0]}


def expand(v, spec):
    """Free parameters of `spec` -> the full 12-vector nonemp_model.employment takes."""
    if spec == "full":
        v = np.asarray(v, float)
        return np.concatenate([v, [NM.GKOS_START[k] for k in NM.NAMES[v.size:]]])   # shorter files: GKOS defaults
    th = dict(NM.GKOS_START, k_m=-50.0, k_f=-50.0)          # absorbing hazard off (logistic(-50) ~ 2e-22)
    if spec == "sexint":
        th.update(a_m_E=v[0], a_m_N=v[0], a_f_E=v[1], a_f_N=v[1])
    elif spec in ("sexlag_add", "sexlag_abs", "sexlag_absq", "sexlag_abs55", "absq_alpha", "absq_zcap", "absq_ten",
                  "absq_ewma", "absq_ten3", "absq_rho", "alpha_rho", "absq_grad", "absq_hyp", "alpha_grad"):
        th.update(a_m_E=v[0], a_m_N=v[0] + v[2], a_f_E=v[1], a_f_N=v[1] + v[2], pi_m=np.nan, pi_f=np.nan)
        if spec != "sexlag_add":                            # permanent exit logistic(k + k_t t [+ ...]), both sexes
            th.update(k_m=v[3], k_f=v[3], k_t=v[4])
        if spec in ("sexlag_absq", "absq_alpha", "absq_zcap", "absq_ten", "absq_ewma", "absq_ten3", "absq_rho",
                    "alpha_rho", "absq_grad", "absq_hyp", "alpha_grad"):
            th.update(k_t2=v[5])
        elif spec == "sexlag_abs55":
            th.update(k_55=v[5])
        if spec == "absq_alpha":
            th.update(kappa=v[6])
        elif spec == "absq_zcap":
            th.update(zbar_m=v[6], zbar_f=v[7])
        elif spec == "absq_ten":
            th.update(ten_K=v[6])
        elif spec == "absq_ewma":
            th.update(ten_delta=v[6])
        elif spec == "absq_ten3":
            th.update(ten_K=3.0)
        elif spec == "absq_rho":
            th.update(ten_rho=v[6])
        elif spec == "alpha_rho":
            th.update(kappa=v[6], ten_rho=v[7])
        elif spec == "absq_grad":
            th.update(ten_gam=v[6])
        elif spec == "absq_hyp":
            th.update(ten_hyp=v[6])
        elif spec == "alpha_grad":
            th.update(kappa=v[6], ten_gam=v[7])
    else:
        th.update(dict(zip(SPECS["sexlag"], v)), pi_m=np.nan, pi_f=np.nan)
    return np.array([th[k] for k in NM.NAMES])


def key_x(x):
    """Bin key: 5 significant figures, coarser than the CSV's %.6g, so a written-and-read key equals a fresh one."""
    return pd.Series([float(f"{v:.5g}") for v in x], index=getattr(x, "index", None))


def moment_frame(E, thr, real, sex, seed=7):
    """transition_rates.analyze -> the moment vector (indexed stat, h, sex, age, group, x) with n."""
    d = pd.DataFrame(TR.analyze(E, thr, real, "x", sex, np.random.default_rng(seed)),
                     columns=["stat", "h", "sex", "source", "age", "group", "x", "share", "n"])
    d = d[d.stat.isin({s for s, _ in FIG2BLOCK} | {"trans_cum", "trans_cur", "trans_life"})].drop(columns="source")
    d = d[~((d.stat == "fwd_dec") & (d.group == "total"))]
    tr = d.stat.isin(["trans_cum", "trans_cur", "trans_life"])
    t = d[tr].assign(group=d[tr].group.str.split(":").str[1])          # entries + exits -> one count
    t = t.groupby(["stat", "h", "sex", "age", "group", "x"], as_index=False).agg(share=("share", "sum"),
                                                                                n=("n", "first"))
    q = d[d.stat == "byage_lq"]                                          # overall employment by age
    by = q.assign(w=q.share * q.n).groupby(["h", "sex", "age", "x"], as_index=False).agg(w=("w", "sum"),
                                                                                       n=("n", "sum"))
    by = by.assign(stat="byage", group="all", share=by.w / by.n).drop(columns="w")
    d = pd.concat([d[~tr], t, by], ignore_index=True)
    d["x"] = key_x(d.x)         # bin keys must survive the CSV round trip (chg_abs midpoints are irrational)
    return d.set_index(["stat", "h", "sex", "age", "group", "x"])


def cache_path(yob):
    return os.path.join(os.path.dirname(os.path.dirname(HERE)), "processed_data", f"nonemp_inputs_yob{yob}.npz")


class Problem:
    """Everything one cohort's estimation needs. The data inputs (EPUF matrix, cap thresholds, price index, g(t),
    q(x)) come from the DuckDB and the microsimulation under `root`, and are cached to `cache` (an .npz; "auto" =
    cache_path(yob), None = never) so a checkout without the database -- the cluster -- can run from the file alone.
    Delete the file to rebuild it after re-estimating g(t). The GKOS process constants come from this repo's
    gcohort_model either way."""

    def __init__(self, root, yob, n_sim, seed, cache="auto"):
        import gcohort_model as E                               # code/dynamics is on sys.path (HERE)
        self.E = E
        self.yob = yob
        self.ages = np.arange(TR.A0, TR.A1 + 1)
        path = cache_path(yob) if cache == "auto" else cache
        if path and os.path.exists(path):
            z = np.load(path)
            self.thr, self.real = z["thr"], z["real"]
            self.g = {s: z[f"g{s}"] for s in (1, 2)}
            self.q = {s: z[f"q{s}"] for s in (1, 2)}
            self.data_E = {s: z[f"E{s}"] for s in (1, 2)}
        else:
            if not os.path.isdir(root):
                raise FileNotFoundError(f"no input cache at {path} and no checkout with the database at {root}")
            sys.path.insert(0, os.path.join(root, "code", "benefits"))
            os.chdir(root)
            with contextlib.redirect_stdout(io.StringIO()):
                import run_microsim as RM
                profiles, price = RM.RA._get_gcohort_inputs()
            import simulate_histories as SH
            years = list(yob + self.ages)
            self.thr = TR.threshold(years)
            self.real = np.array([price[y] for y in years])
            self.g = {s: E.g_at(profiles[(SH.SEX_LABEL[s], yob + 25)], self.ages) for s in (1, 2)}
            self.q = {s: TR.cohort_qx(yob, s) for s in (1, 2)}
            sex_e, E_e = TR.epuf_matrix(yob)
            self.data_E = {s: E_e[sex_e == s] for s in (1, 2)}
            if path:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                np.savez_compressed(path, thr=self.thr, real=self.real, g1=self.g[1], g2=self.g[2],
                                    q1=self.q[1], q2=self.q[2], E1=self.data_E[1], E2=self.data_E[2])
                print("wrote", path)
        self.logP = np.log(self.real)
        self.shocks = {s: NM.draw_shocks(self.E, n_sim, self.ages, [seed, yob, s]) for s in (1, 2)}

    def sim_E(self, theta, sex):
        E = NM.earnings(theta, self.shocks[sex], sex, self.ages, self.q[sex], self.E, self.g[sex], self.logP)
        return E[(E > 0).any(1)]

    def sim_moments(self, theta):
        return pd.concat([moment_frame(self.sim_E(theta, s), self.thr, self.real, s) for s in (1, 2)])

    def data_moments(self, rng):
        """Data moments, bootstrap sd (level and arc-percent) and the sd-scheme weights."""
        m = pd.concat([moment_frame(self.data_E[s], self.thr, self.real, s) for s in (1, 2)])
        boots = []
        for b in range(B_BOOT):
            bs = []
            for s in (1, 2):
                X = self.data_E[s]
                bs.append(moment_frame(X[rng.integers(0, len(X), len(X))], self.thr, self.real, s).share)
            boots.append(pd.concat(bs).rename(b))
        B = pd.concat(boots, axis=1).reindex(m.index)
        m = m.assign(sd=B.std(axis=1))
        fig = list(zip(m.index.get_level_values("stat"), m.index.get_level_values("h")))
        m = m[(m.n >= MIN_N) & m.sd.notna() & np.array([f in FIG2BLOCK for f in fig])].copy()
        fig = list(zip(m.index.get_level_values("stat"), m.index.get_level_values("h")))
        m["block"] = [FIG2BLOCK[f] for f in fig]
        m["figure"] = [f"{s}_h{h}" for s, h in fig]
        med = m.groupby("figure").sd.transform("median")
        m["sd_used"] = np.maximum(m.sd, np.maximum(0.25 * med, 1e-4))
        nfig = m.groupby("block").figure.transform("nunique")
        nmom = m.groupby("figure").share.transform("size")
        m["weight"] = 0.25 / nfig / nmom / m.sd_used ** 2
        m["psi"] = m.groupby("figure").share.transform(lambda x: x.abs().quantile(0.1))
        B, d, psi = B.reindex(m.index), m.share.to_numpy()[:, None], m.psi.to_numpy()[:, None]
        m["arc_sd"] = ((B - d) / (0.5 * (B.abs() + np.abs(d)) + psi)).std(axis=1)
        return m


def to_pp(m):
    """Every moment in share units: counts of switches annualised, the years-worked histogram as a CDF."""
    m = m.copy()
    stat = m.index.get_level_values("stat")
    age = m.index.get_level_values("age").to_numpy(float)
    fwd = np.isin(stat, ["trans_cum", "trans_cur", "trans_fut_lq"])
    m.loc[fwd, "share"] = m.share[fwd] / (TR.A1 - age[fwd])
    m.loc[stat == "trans_life", "share"] = m.share[stat == "trans_life"] / (TR.A1 - TR.A0 - 1)
    yh = m[stat == "yrs_hist"].sort_index(level="x")
    m.loc[yh.index, "share"] = yh.share.groupby(level="sex").cumsum()
    return m


def set_weights(md, scheme):
    """md (data moments as written by data_moments) -> target and weight for `scheme`."""
    md = md[md.figure.isin({f"{s}_h{h}" for s, h in FIG2BLOCK})].copy()
    nfig = md.groupby("block").figure.transform("nunique")
    nmom = md.groupby("figure").share.transform("size")
    if scheme == "gkospp":
        md["target"] = to_pp(md).share
        md["weight"] = 0.25 / nfig / nmom          # main() rescales each figure x sex by its loss at GKOS
        return md
    if scheme in ("arc", "spread", "gkos"):
        md["target"] = md.share
        if scheme == "gkos":
            scale = 1.0                         # main() divides each figure by its loss at GKOS (needs a simulation)
        elif scheme == "arc":
            scale = md.groupby("figure").arc_sd.transform("median")
        else:
            mean = md.groupby("figure").share.transform("mean")
            arc = (md.share - mean) / (0.5 * (md.share.abs() + mean.abs()) + md.psi)
            scale = np.sqrt((arc ** 2).groupby(md.figure).transform("mean"))
        md["weight"] = 0.25 / nfig / nmom / scale ** 2
        return md
    md = md.drop(columns="psi", errors="ignore")
    if scheme == "sd":
        md["target"], scale = md.share, md.sd_used
    else:
        yh = md.index.get_level_values("stat") == "yrs_hist"
        assert yh.sum() == 2 * (TR.A1 - TR.A0 + 1), "the CDF needs every years-worked bin"
        md["target"] = to_pp(md).share
        if scheme == "pp":
            scale = 0.01                                        # J in squared percentage points
        else:
            mad = md.groupby("figure").target.transform(lambda x: 1.4826 * (x - x.median()).abs().median())
            scale = mad
    md["weight"] = 0.25 / nfig / nmom / scale ** 2
    return md


def objective_parts(m_data, m_sim):
    """m_sim must already be in m_data's units (to_pp for the pp / mad schemes). A `psi` column in m_data (arc
    scheme) makes the deviation arc-percent."""
    sim = m_sim.share.reindex(m_data.index)
    ok = sim.notna()
    dev = sim - m_data.target
    if "psi" in m_data:
        dev = dev / (0.5 * (sim.abs() + m_data.target.abs()) + m_data.psi)
    r2 = m_data.weight * dev ** 2
    # a bin the model leaves empty is skipped; its weight is re-spread so J stays comparable across theta
    return r2[ok], ok


def objective(m_data, m_sim):
    r2, ok = objective_parts(m_data, m_sim)
    return r2.sum() * m_data.weight.sum() / m_data.weight[ok].sum()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yob", type=int, default=1932)
    ap.add_argument("--n-sim", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=20261006)
    ap.add_argument("--maxfev", type=int, default=2500)
    ap.add_argument("--spec", default="full", choices=tuple(SPECS))
    ap.add_argument("--weights", default="pp", choices=("gkospp", "gkos", "spread", "arc", "pp", "mad", "sd"))
    ap.add_argument("--start", default=None, help="comma-separated start vector in the spec's order (robustness runs)")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--step", type=float, default=0.5, help="initial simplex step, halved each round")
    ap.add_argument("--tag", default="", help="suffix for the output files; a tagged run writes only params + fit")
    ap.add_argument("--tiktak", type=int, default=0, help="Sobol' points for the TikTak multistart (0: single start)")
    ap.add_argument("--keep", type=int, default=0, help="seeds kept after the Sobol' stage (0: one batch of --workers)")
    ap.add_argument("--workers", type=int,
                    default=int(os.environ.get("SLURM_CPUS_PER_TASK", "0")) or max(1, os.cpu_count() - 1))
    ap.add_argument("--local", default="nm", choices=("nm", "powell"))
    ap.add_argument("--gamma", type=float, default=0.25, help="theta_i = (i/keep)^gamma; AGK use 0.5, smaller is steeper")
    ap.add_argument("--tol", type=float, default=1e-2, help="local-search tolerance (f and theta) and the Z* stopping rule")
    ap.add_argument("--local-maxfev", type=int, default=120)
    ap.add_argument("--budget", type=float, default=300.0, help="seconds for the global stage")
    ap.add_argument("--root", default=TR.ROOT_DEFAULT, help="checkout with the database; unused once --cache exists")
    ap.add_argument("--cache", default="auto", help="inputs .npz (see Problem); 'auto' = processed_data/, 'none' = off")
    ap.add_argument("--out", default=OUT_DEFAULT)
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)

    P = Problem(args.root, args.yob, args.n_sim, args.seed, None if args.cache == "none" else args.cache)
    mpath = os.path.join(out, f"nonemp_moments_yob{args.yob}.csv")
    if os.path.exists(mpath) and "arc_sd" in pd.read_csv(mpath, nrows=1):
        md = pd.read_csv(mpath).assign(x=lambda t: key_x(t.x)).set_index(["stat", "h", "sex", "age", "group", "x"])
        print("read", mpath)
    else:
        t0 = time.time()
        md = P.data_moments(np.random.default_rng(args.seed))
        md.reset_index().to_csv(mpath, index=False, float_format="%.12g")   # bin keys: see key_x
        print(f"wrote {mpath} ({len(md)} moments, bootstrap {time.time() - t0:.0f}s)")
    md = set_weights(md, args.weights)
    print(md.groupby(["block", "figure"]).size().to_string())
    prep = to_pp if args.weights in ("pp", "mad", "gkospp") else (lambda m: m)  # noqa: E731

    names = SPECS[args.spec]
    if args.spec == "full":
        gkos = np.array([NM.GKOS_START[k] for k in NM.NAMES])
        start = np.array([dict(a_m_E=-3.6, a_m_N=1.0, a_f_E=-3.0, a_f_N=1.5, k_m=-6.0, k_f=-6.0, k_t=0.3, k_55=1.0,
                               k_62=2.0, k_z=-1.0, pi_m=0.0, pi_f=0.0, k_t2=0.0, kappa=0.0, zbar_m=np.inf,
                               zbar_f=np.inf)[k] for k in NM.NAMES])
    else:
        gkos = np.array(GKOS[args.spec])
        start = np.array(START[args.spec])
    tag = ("" if args.spec == "full" else "_" + args.spec) + ("" if args.weights == "pp" else "_w" + args.weights) \
        + args.tag
    if args.start:
        start = np.array([float(v) for v in args.start.split(",")])
        assert start.size == len(names)
    if args.weights == "gkos":                              # each figure relative to its own loss at GKOS
        r2, ok = objective_parts(md, prep(P.sim_moments(expand(gkos, args.spec))))
        assert ok.all(), "GKOS leaves a targeted bin empty"
        md["weight"] = md.weight / r2.groupby(md.figure).transform("sum") * md.groupby("figure").weight.transform("sum")
    if args.weights == "gkospp":                            # each figure x sex relative to its own loss at GKOS
        r2, ok = objective_parts(md, prep(P.sim_moments(expand(gkos, args.spec))))
        assert ok.all(), "GKOS leaves a targeted bin empty"
        fs = [md.figure, md.index.get_level_values("sex")]
        md["weight"] = md.weight * 0.5 * md.groupby("figure").weight.transform("sum") / r2.groupby(fs).transform("sum")
    J = lambda v: objective(md, prep(P.sim_moments(expand(v, args.spec))))  # noqa: E731
    best = {"J": np.inf, "n": 0}

    def f(th):
        v = J(th)
        best["n"] += 1
        if v < best["J"]:
            best["J"], best["th"] = v, th.copy()
            print(f"  eval {best['n']:5d}  J = {v:.4f}  " + " ".join(f"{x:+.3f}" for x in th), flush=True)
        return v

    print(f"J at GKOS (+ mortality): {J(gkos):.4f}; at start: {J(start):.4f}", flush=True)
    th = start
    if args.tiktak:
        assert args.spec != "full", "BOUNDS cover the reduced specs only"
        lo, hi = map(np.array, zip(*[BOUNDS[k] for k in names]))
        th, Jbest, hist = TK.tiktak(J, lo, hi, n_sobol=args.tiktak, n_keep=args.keep, workers=args.workers,
                                    local=args.local, gamma=args.gamma, tol=args.tol, maxfev=args.local_maxfev,
                                    budget=args.budget, seed=args.seed, log=lambda m: print(m, flush=True))
        best.update(J=Jbest, th=th)
        w = pd.DataFrame([dict(stage=h["stage"], theta=h["theta"], f=h["f"], nfev=h["nfev"],
                               **{k: v for k, v in zip(names, h["x"])},
                               **{"start_" + k: v for k, v in zip(names, h["start"])}) for h in hist])
        w.sort_values("f").to_csv(os.path.join(out, f"nonemp_tiktak_yob{args.yob}{tag}.csv"), index=False,
                                  float_format="%.5f")
        print(w.sort_values("f").head(12).round(4).to_string(index=False))
    for rnd in range(0 if args.tiktak else args.rounds):
        # explicit initial simplex: scipy's default steps 5% of each value (0.00025 for a zero), which leaves
        # parameters that start at 0 essentially fixed. Each round restarts from the best point with a smaller step.
        step = args.step * 0.5 ** rnd
        simplex = np.vstack([th] + [th + step * np.eye(th.size)[i] for i in range(th.size)])
        res = minimize(f, th, method="Nelder-Mead",
                       options=dict(maxfev=args.maxfev, xatol=1e-3, fatol=1e-4, adaptive=True,
                                    initial_simplex=simplex))
        th = best["th"]
        print(f"round {rnd}: {res.message} J = {best['J']:.4f}", flush=True)

    pd.DataFrame({"parameter": names, "gkos": gkos, "start": start, "estimate": th}).to_csv(
        os.path.join(out, f"nonemp_params_yob{args.yob}{tag}.csv"), index=False, float_format="%.5f")
    fit = []
    for lab, t_ in (("gkos_mort", gkos), ("fitted", th)):
        r2, ok = objective_parts(md, prep(P.sim_moments(expand(t_, args.spec))))
        fit.append(r2.groupby([md.block[ok], md.figure[ok]]).sum().rename(lab))
    fit = pd.concat(fit, axis=1)
    fit.loc[("all", "all"), :] = fit.sum()
    fit.reset_index().rename(columns={"level_0": "block", "level_1": "figure"}).to_csv(
        os.path.join(out, f"nonemp_fit_yob{args.yob}{tag}.csv"), index=False, float_format="%.5f")
    print(fit.round(4).to_string())
    if args.tag:
        return
    src = "nonemp" if args.spec == "full" else args.spec

    rng = np.random.default_rng(args.seed)                   # the fitted model through the SAME statistics code
    rows = []
    for s in (1, 2):
        rows += TR.analyze(P.sim_E(expand(th, args.spec), s), P.thr, P.real, src, s, rng)
    d = pd.DataFrame(rows, columns=["stat", "h", "sex", "source", "age", "group", "x", "share", "n"])
    path = os.path.join(out, f"transition_rates_yob{args.yob}_{src}{tag[len(src) + 1:] if args.spec != 'full' else ''}.csv")
    d.to_csv(path, index=False, float_format="%.5f")
    print("wrote", path)


if __name__ == "__main__":
    main()
