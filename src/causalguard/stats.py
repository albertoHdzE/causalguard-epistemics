"""Statistics owner: world-clustered paired estimates, bootstrap, design simulation.

Unit of independence: the generated WORLD.  Every function here takes one value
per world (already averaged over that world's queries/budgets/seeds); rows are
never resampled.  Stratum weights are EQUAL across strata (prespecified).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


def stratified_mean(values: np.ndarray, strata: np.ndarray) -> float:
    """Equal-weight mean of per-stratum means."""
    labels = np.unique(strata)
    return float(np.mean([values[strata == s].mean() for s in labels]))


def stratified_se(values: np.ndarray, strata: np.ndarray) -> float:
    labels = np.unique(strata)
    K = len(labels)
    var = 0.0
    for s in labels:
        v = values[strata == s]
        var += (v.var(ddof=1) / len(v)) if len(v) > 1 else 0.0
    return math.sqrt(var) / K


@dataclass(frozen=True)
class BootResult:
    estimate: float
    lo: float
    hi: float
    se: float
    n_worlds: int
    n_strata: int
    replicates: int
    seed: int

    def to_json(self) -> dict:
        return self.__dict__.copy()


def paired_cluster_bootstrap(deltas, strata, replicates: int = 5000, seed: int = 20261109,
                             alpha: float = 0.05) -> BootResult:
    """Stratified paired cluster bootstrap of the equal-weight stratified mean of per-world deltas.

    ``deltas[w]`` must already be the paired within-world difference (method A - method B)
    averaged over that world's query grid; worlds are resampled with replacement within
    each stratum.  Percentile interval."""
    d = np.asarray(deltas, dtype=float)
    s = np.asarray(strata)
    if len(d) == 0 or len(d) != len(s):
        raise ValueError("need one delta and one stratum per world")
    if np.isnan(d).any():
        raise ValueError("NaN delta: apply the prespecified missing-output rule before bootstrapping")
    labels = np.unique(s)
    idx = [np.nonzero(s == lab)[0] for lab in labels]
    rng = np.random.default_rng(seed)
    est = stratified_mean(d, s)
    boots = np.empty(replicates)
    for b in range(replicates):
        means = []
        for ix in idx:
            pick = rng.integers(0, len(ix), len(ix))
            means.append(d[ix[pick]].mean())
        boots[b] = np.mean(means)
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    return BootResult(est, float(lo), float(hi), float(boots.std(ddof=1)), len(d), len(labels), replicates, seed)


def bootstrap_coverage(population: np.ndarray, strata: np.ndarray, n_per_stratum: int, sims: int = 400,
                       replicates: int = 1000, seed: int = 7) -> dict:
    """Coverage of the bootstrap interval when sampling worlds from a known finite population."""
    rng = np.random.default_rng(seed)
    labels = np.unique(strata)
    truth = stratified_mean(population, strata)
    hits = 0
    widths = []
    for _i in range(sims):
        ds, ss = [], []
        for lab in labels:
            pool = population[strata == lab]
            ds.append(rng.choice(pool, n_per_stratum, replace=True))
            ss += [lab] * n_per_stratum
        r = paired_cluster_bootstrap(np.concatenate(ds), np.array(ss), replicates, seed=int(rng.integers(1 << 31)))
        hits += r.lo <= truth <= r.hi
        widths.append(r.hi - r.lo)
    return {"coverage": hits / sims, "sims": sims, "replicates": replicates, "n_per_stratum": n_per_stratum,
            "mean_width": float(np.mean(widths)), "truth": truth}


def design_simulation(deltas, strata, n_grid=(200, 400, 600, 800, 1000, 1200, 1500, 2000), effect: float = 0.05,
                      sims: int = 2000, variance_inflation: float = 1.25, seed: int = 11, alpha: float = 0.05) -> dict:
    """Monte Carlo design study from DEVELOPMENT per-world deltas.

    Scenarios (worlds resampled within strata, equal allocation):
      observed  : the development distribution as is;
      null      : each stratum recentred to mean 0;
      effect    : each stratum recentred so the stratified mean equals ``effect``;
      effect_conservative : as 'effect' with deviations inflated by ``variance_inflation``.
    For each total N reports the median and 90th-percentile 95% half-width (normal
    interval with the stratified SE, validated against the bootstrap by
    ``bootstrap_coverage``), power P(lower bound > 0) and false-positive rate under null.
    """
    d = np.asarray(deltas, float)
    s = np.asarray(strata)
    labels = np.unique(s)
    K = len(labels)
    rng = np.random.default_rng(seed)
    z = 1.959963984540054
    pools = {lab: d[s == lab] for lab in labels}
    obs_mean = stratified_mean(d, s)

    def scenario_pool(name):
        out = {}
        for lab, p in pools.items():
            c = p - p.mean()
            if name == "observed":
                out[lab] = p
            elif name == "null":
                out[lab] = c
            elif name == "effect":
                out[lab] = c + effect
            elif name == "effect_conservative":
                out[lab] = c * variance_inflation + effect
        return out

    res = {"assumptions": {"strata": [str(x) for x in labels], "dev_worlds": int(len(d)),
                           "dev_stratified_mean": obs_mean, "dev_sd_per_stratum": {str(k): float(v.std(ddof=1))
                                                                                    for k, v in pools.items()},
                           "effect": effect, "variance_inflation": variance_inflation, "sims": sims,
                           "allocation": "equal per stratum", "interval": "normal with stratified SE",
                           "seed": seed}, "grid": []}
    for N in n_grid:
        m = max(2, N // K)
        row = {"N_total": m * K, "n_per_stratum": m}
        for name in ("observed", "null", "effect", "effect_conservative"):
            pool = scenario_pool(name)
            est = np.empty(sims)
            se = np.empty(sims)
            for i in range(sims):
                means, var = [], 0.0
                for lab in labels:
                    x = rng.choice(pool[lab], m, replace=True)
                    means.append(x.mean())
                    var += x.var(ddof=1) / m
                est[i] = np.mean(means)
                se[i] = math.sqrt(var) / K
            hw = z * se
            row[name] = {"median_half_width": float(np.median(hw)), "p90_half_width": float(np.quantile(hw, 0.9)),
                         "p_lower_gt_0": float(np.mean(est - hw > 0)), "p_upper_lt_0": float(np.mean(est + hw < 0)),
                         "mean_estimate": float(est.mean())}
        res["grid"].append(row)
    return res


def normal_approx_n(sigma: float, delta: float = 0.05, alpha: float = 0.05, power: float = 0.8) -> int:
    """The planning formula from the protocol (not the final power analysis)."""
    from statistics import NormalDist
    za = NormalDist().inv_cdf(1 - alpha / 2)
    zb = NormalDist().inv_cdf(power)
    return math.ceil((za + zb) ** 2 * sigma ** 2 / delta ** 2)


def holm(pvalues: dict[str, float]) -> dict[str, float]:
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(items)
    out, running = {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out
