"""S2 — induction from incomplete evidence (primary study), one world per item.

Information flow (audited by tests/test_s2_isolation.py):
  public evidence --> version space --> {selectors, uniform, consensus} --> predictions
  hidden world --> hidden answers --> SCORING ONLY (after predictions are fixed)
Selectors receive a VersionSpace built from public observations; they never
receive the world, its network, hidden queries' answers or the full repertoire.
"""
from __future__ import annotations

import random
import time

import numpy as np

from ..generators import REGIMES, World, make_s2_instance, make_s2_world
from ..schema import Evidence, HypothesisClass, Intervention, Observation, Query
from ..versionspace import (
    Unsupported,
    build_version_space,
    candidate_class,
    choose_disagreement_state,
    network_from_choice,
    predict,
    select_mdl_noisy,
    select_min_code,
    true_rank_audit,
    uniform_prob_true,
    verdict,
    verdict_fast,
)

SELECTORS = ("index", "circuit", "bdd", "dnf")
BUDGETS = (2, 4, 8, 16, 32, 64)


def _majority_baseline(evidence: Evidence, node: int) -> int:
    """Surface baseline: most frequent observed value of the target node (ties -> 0)."""
    vals = [v for o in evidence.observations for i, v in o.observed if i == node]
    return int(sum(vals) * 2 > len(vals)) if vals else 0


def evaluate_budget(world: World, evidence: Evidence, queries: list[tuple[str, Query]], rng: np.random.Generator,
                    with_verdicts: bool = True, mc_samples: int = 4096) -> dict:
    hc = HypothesisClass(world.net.n, world.max_indegree)
    t0 = time.perf_counter()
    vs = build_version_space(evidence, hc)
    t_vs = time.perf_counter() - t0
    # ---- learner side: public evidence only -------------------------------------------
    t1 = time.perf_counter()
    choices = {cd: select_min_code(vs, cd) for cd in SELECTORS}
    t_sel = time.perf_counter() - t1
    nets = {cd: (network_from_choice(vs.cls, c) if c is not None else None) for cd, c in choices.items()}
    rows = []
    t_ver = 0.0
    for kind, q in queries:
        b = q.target.args[0].node if q.target.op != "lit" else q.target.node
        row = {"kind": kind, "h": q.horizon, "iv": q.intervention.kind, "target_node": b,
               "pred": {cd: (int(predict(nets[cd], q)) if nets[cd] is not None else None) for cd in SELECTORS},
               "majority": _majority_baseline(evidence, b)}
        if not vs.empty:
            p, meth, se = uniform_prob_true(vs, q, rng, mc_samples=mc_samples)
            row.update(p_uniform=p, uniform_method=meth, uniform_se=se)
            if with_verdicts:
                tv = time.perf_counter()
                row["verdict"] = (verdict_fast(vs, q) if q.horizon <= 1 else verdict(vs, q).verdict).value
                t_ver += time.perf_counter() - tv
        else:
            row.update(p_uniform=None, uniform_method=None, uniform_se=None,
                       verdict="inconsistent_evidence_or_class")
        rows.append(row)
    # ---- scoring side: hidden world (after all predictions are fixed) -------------------
    for (_kind, q), row in zip(queries, rows):
        row["truth"] = int(predict(world.net, q))
    return {"vs_counts": vs.counts(), "log10_vs": vs.log10_size(), "empty": vs.empty,
            "t_version_space": t_vs, "t_selection": t_sel, "t_verdicts": t_ver,
            "selected_bits": {cd: (int(sum(vs.cls.bits[cd][c] for c in choices[cd])) if choices[cd] else None)
                              for cd in SELECTORS},
            "queries": rows, "_vs": vs}


def active_evidence(world: World, holdout: list[int], budget: int, seed: int) -> tuple[list[Observation], dict]:
    """Disagreement-guided designed measurements (no intervention, full observation)."""
    from .. import reference
    hc = HypothesisClass(world.net.n, world.max_indegree)
    rng = np.random.default_rng(seed)
    obs: list[Observation] = []
    used: set[int] = set()
    t0 = time.perf_counter()
    scored = 0
    for _ in range(budget):
        vs = build_version_space(Evidence(world.net.n, tuple(obs)), hc)
        if vs.empty:
            break
        x = choose_disagreement_state(vs, used, rng, exclude=set(holdout))
        scored += (1 << world.net.n) - len(used)
        used.add(x)
        fin = reference.run(world.net, x, Intervention(), 1)[-1]   # the measurement itself (world answers)
        obs.append(Observation(x, Intervention(), 1, tuple((i, (fin >> i) & 1) for i in range(world.net.n))))
    return obs, {"policy_seconds": time.perf_counter() - t0, "states_scored": scored}


def flip_noise(obs: list[Observation], rate: float, seed: int) -> tuple[list[Observation], int]:
    rng = random.Random(seed)
    out = []
    flips = 0
    for o in obs:
        new = []
        for i, v in o.observed:
            if rng.random() < rate:
                v = 1 - v
                flips += 1
            new.append((i, v))
        out.append(Observation(o.state, o.intervention, o.horizon, tuple(new)))
    return out, flips


def run_world(p: dict) -> dict:
    """One S2 world: all regimes x budgets x methods.  Pure function of the payload."""
    world = make_s2_world(p["salt"], p["index"], p["family"], p["population"], p.get("n", 7), p.get("kmax", 3))
    inst = make_s2_instance(world)
    candidate_class(world.net.n, world.max_indegree)
    queries = [("state", q) for q in inst.state_queries] + [("intervention", q) for q in inst.intervention_queries]
    budgets = tuple(p.get("budgets", BUDGETS))
    regimes = list(p.get("regimes", list(REGIMES) + ["active"]))
    rng = np.random.default_rng(world.seed % (2**32))
    out = {"world": world.to_private_json(), "instance_irregularities": inst.irregularities,
           "holdout_states": inst.holdout_states, "n_queries": len(queries), "regimes": {}}
    for regime in regimes:
        if regime == "active":
            seq, cost = active_evidence(world, inst.holdout_states, max(budgets), world.seed % (2**32))
            out.setdefault("active_cost", cost)
        else:
            seq = inst.evidence[regime]
        res = {}
        for B in budgets:
            ev = Evidence(world.net.n, tuple(seq[:B]), regime)
            r = evaluate_budget(world, ev, queries, rng, with_verdicts=p.get("verdicts", True),
                                mc_samples=p.get("mc_samples", 4096))
            vs = r.pop("_vs")
            if B == 16 and not vs.empty and world.realizable():
                r["true_rank_audit"] = {cd: true_rank_audit(vs, world.net, cd) for cd in SELECTORS}
            r["n_observations"] = len(ev.observations)
            res[str(B)] = r
        out["regimes"][regime] = res
    # ---- noise stress (separately labelled MDL experiment), uniform_states regime only ---------
    for rate in p.get("noise_rates", ()):
        noisy, flips = flip_noise(inst.evidence["uniform_states"], rate, world.seed ^ int(rate * 1e6))
        nres = {}
        for B in p.get("noise_budgets", (16, 32, 64)):
            ev = Evidence(world.net.n, tuple(noisy[:B]), f"uniform_states+noise{rate}")
            r = evaluate_budget(world, ev, queries, rng, with_verdicts=False, mc_samples=p.get("mc_samples", 4096))
            r.pop("_vs")
            cls = candidate_class(world.net.n, world.max_indegree)
            ch, info = select_mdl_noisy(cls, ev, "index")
            mnet = network_from_choice(cls, ch)
            for (_kind, q), row in zip(queries, r["queries"]):
                row["pred"]["mdl_two_part_index"] = int(predict(mnet, q))
            r["mdl_residual_errors"] = info["residual_errors"]
            nres[str(B)] = r
        out.setdefault("noise", {})[str(rate)] = {"flips_total_64": flips, "budgets": nres}
    return out


__all__ = ["run_world", "SELECTORS", "BUDGETS", "Unsupported"]
