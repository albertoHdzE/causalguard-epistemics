"""Track M: wrong assumptions, false assurances and recovery.

1. ``and_counterexample()``: the hand-checkable n = 2 case.  Declared H = indegree <= 1.  Evidence: one-step
   outcomes (0,0) from (0,0), (1,0), (0,1).  In H both node functions must be constant 0, so node 0 after one
   step from the unseen state (1,1) is VERIFIED 0.  The hidden simulator has x0' = x0 AND x1, x1' = 0: it matches
   every observation and returns 1.  Under indegree <= 2 the target is underdetermined.  Model-relative proof is
   not world correctness; no solver is wrong.

2. ``m_world(payload)``: one base world of a stress panel (n = 6, declared k = 2):
     realizable           hidden mechanism in H(6, 2)
     evidence_inconsistent hidden has 1-2 nodes with 3 essential inputs and V_H(D) is EMPTY
     evidence_consistent  same generator, V_H(D) NONEMPTY
   Panel membership uses only (i) the generator's construction label (outside H by construction) and (ii) the
   PUBLIC emptiness of V_H(D); acceptance is a fixed seeded search with a maximum number of draws and a log.
   Policies (none sees the hidden mechanism, its class label or panel):
     current          the S4 gate under the declared class: release a definite verdict iff it is verified
     expanded         fixed enlarged class H(6, 3) always
     robust_union     union of the declared plausible classes {H(6,2), H(6,2) with ONE node allowed indegree 3}
                      = the one-exception class; verified only if every consistent class member agrees
                      (certificate: trusted exact computation; the common SAT cross-check covers uniform classes)
     challenge        public falsification tests: before release buy up to 4 one-node measurements (menu of 16,
                      target-equivalent purchases excluded) where H(6,2) is definite but H(6,3) is not; if the
                      declared class is contradicted (V empty) switch to H(6,3) (logged class change)
     abstain          never releases (extreme baseline)
   Scored by the evaluator AFTER every policy decision is fixed: false verified outcomes (a released definite
   verdict whose action postcondition fails in the hidden simulator), correct releases, unnecessary blocks,
   false uncertainty, inconsistency detection, measurements, costs and class-change logs.
"""
from __future__ import annotations

import hashlib
import json
import random
import time

from .. import reference
from ..generators import world_seed
from ..s4.mechspace import MechanismSpace
from ..schema import Evidence, Intervention, Network, Observation, Pred, Query, Rule
from ..versionspace import point_query_parts
from .contracts import assumption_check
from .data import role_rule

N_M, K_DECL, K_BIG = 6, 2, 3
PANELS = ("realizable", "evidence_inconsistent", "evidence_consistent")
MAX_DRAWS = 4000
BUDGETS_M = (6, 10)          # evidence size drawn per world from this list (design stream)
MENU = 16
CHALLENGES = 4
POLICIES = ("current", "expanded", "robust_union", "challenge", "abstain")
SPEC = {"version": "r5-m-v1", "n": N_M, "declared_k": K_DECL, "expanded_k": K_BIG, "panels": list(PANELS),
        "max_draws_per_panel": MAX_DRAWS, "budgets": list(BUDGETS_M), "queries": 8, "menu": MENU,
        "challenges": CHALLENGES, "policies": list(POLICIES),
        "robust_union": "H(n,2) u {one node indegree 3}", "outside_nodes": [1, 2]}


# --------------------------------------------------------------------------- exact counterexample

def and_counterexample() -> dict:
    n = 2
    obs = tuple(Observation(x, Intervention("none"), 1, ((0, 0), (1, 0))) for x in (0b00, 0b01, 0b10))
    ev = Evidence(n, obs)
    hidden = Network(n, (Rule((0, 1), 0b1000), Rule((), 0)))
    q = Query.point(0b11, n, Intervention("none"), 1, Pred.lit(0, 1))
    out = {"evidence_matches_hidden": reference.consistent(hidden, ev)}
    for k in (1, 2):
        ms = MechanismSpace(ev, k)
        cc = ms.claim_counts(q)
        out[f"k{k}"] = {"per_node_counts": ms.counts(), "num": cc.num, "den": cc.den,
                        "verdict": "refuted" if cc.num == 0 else "entailed" if cc.num == cc.den else "underdetermined"}
    out["hidden_target_value"] = (reference.run(hidden, 0b11, Intervention("none"), 1)[-1] >> 0) & 1
    return out


# --------------------------------------------------------------------------- generators

def _rule(rng, ins):
    d = len(ins)
    while True:
        t = rng.getrandbits(1 << d)
        r = role_rule(list(ins), t, N_M).canonical()
        if r.arity == d:
            return r


def gen_mech(rng: random.Random, outside: bool) -> tuple[Network, list[int]]:
    rules = []
    bad = rng.sample(range(N_M), rng.choice([1, 2])) if outside else []
    for j in range(N_M):
        d = 3 if j in bad else rng.choice([1, 2, 2])
        rules.append(_rule(rng, rng.sample(range(N_M), d)))
    return Network(N_M, tuple(rules)), bad


def _eff(x, iv):
    m, v = iv.masks
    return (x & ~m) | v if iv.kind != "none" else x


def gen_design(rng: random.Random, B: int):
    states = rng.sample(range(1 << N_M), B)
    specs = [(x, Intervention("none")) if i % 3 != 2 else
             (x, Intervention("persistent_clamp", ((rng.randrange(N_M), rng.randint(0, 1)),)))
             for i, x in enumerate(states)]
    seen = {_eff(x, iv) for x, iv in specs} | set(states)
    queries, keys = [], set()
    while len(queries) < 8:
        h = 1 if len(queries) < 4 else 2
        x = rng.randrange(1 << N_M)
        kind = rng.choice(["none", "initial_edit"])
        iv = Intervention("none") if kind == "none" else Intervention("initial_edit", ((rng.randrange(N_M), rng.randint(0, 1)),))
        t = rng.randrange(N_M)
        if _eff(x, iv) in seen or x in seen:
            continue
        key = (_eff(x, iv), h, t)
        if key in keys:
            continue
        keys.add(key)
        queries.append(Query.point(x, N_M, iv, h, Pred.lit(t, 1)))
    # measurement menu: one-node one-step observations at fresh states; target-equivalent purchases (the
    # effective start state of an h = 1 query with its target node) are excluded
    forbidden = {(_eff(point_query_parts(q, N_M), q.intervention), q.target.node) for q in queries if q.horizon == 1}
    menu = []
    while len(menu) < MENU:
        x, node = rng.randrange(1 << N_M), rng.randrange(N_M)
        if (x, node) in forbidden or (x, node) in menu:
            continue
        menu.append((x, node))
    return specs, queries, menu


def evidence_of(net, specs):
    obs = []
    for x, iv in specs:
        y = reference.run(net, x, iv, 1)[-1]
        cl = {j for j, _ in iv.assign} if iv.kind == "persistent_clamp" else set()
        obs.append(Observation(x, iv, 1, tuple((j, (y >> j) & 1) for j in range(N_M) if j not in cl)))
    return Evidence(N_M, tuple(obs))


def panel_members(panel: str, count: int, salt: str = "r5-M-v1") -> tuple[list[dict], dict]:
    """Seeded bounded construction with an acceptance log.  Public criterion for the misspecified panels: whether
    V_H(D) is empty under the DECLARED class (computable from public evidence)."""
    acc, log = [], {"draws": 0, "accepted": 0, "rejected_other_panel": 0}
    i = 0
    while len(acc) < count and log["draws"] < MAX_DRAWS:
        seed = world_seed(salt, "R5M", i, panel)
        i += 1
        log["draws"] += 1
        rng = random.Random(seed)
        net, bad = gen_mech(rng, outside=panel != "realizable")
        drng = random.Random(seed ^ 0x5EED)
        B = drng.choice(BUDGETS_M)
        specs, queries, menu = gen_design(drng, B)
        ev = evidence_of(net, specs)
        empty = MechanismSpace(ev, K_DECL).empty
        want_empty = panel == "evidence_inconsistent"
        if panel != "realizable" and empty != want_empty:
            log["rejected_other_panel"] += 1
            continue
        acc.append({"panel": panel, "seed": seed, "index": len(acc)})
        log["accepted"] += 1
    log["acceptance_rate"] = log["accepted"] / max(1, log["draws"])
    log["complete"] = len(acc) == count
    return acc, log


# --------------------------------------------------------------------------- policies (public information only)

def _verdict(ms: MechanismSpace, q: Query) -> tuple[str, int | None, int | None]:
    if ms.empty:
        return "inconsistent", None, None
    cc = ms.claim_counts(q)
    return ("refuted" if cc.num == 0 else "entailed" if cc.num == cc.den else "underdetermined"), cc.num, cc.den


def _gate(ev: Evidence, k: int, q: Query, crosscheck: bool = True) -> dict:
    """The S4 gate (workspace D + common checker) asked to verify the backend's own definite verdict."""
    from ..s4.checking import check, commit, validate_proposal
    from ..s4.workspace import make_workspace
    pub = {"n": ev.n, "k": k, "node_labels": [f"x{i}" for i in range(ev.n)], "evidence": ev.to_json(),
           "claims": [{"cid": "c0", "query": q.to_json()}]}
    ws = make_workspace("D", pub)
    r = ws.check(pub["claims"][0])
    v = r["verdict"]
    if v not in ("entailed", "refuted"):
        return {"released": False, "verdict": v, "certificate": None}
    p = validate_proposal({"cid": "c0", "asserted": v}, {"c0": pub["claims"][0]})
    d = check(p, ws, crosscheck=crosscheck)
    if d.proposal_check_status != "verified":
        return {"released": False, "verdict": v, "certificate": d.proposal_check_status}
    commit(p, d, ws)
    side = [x for k_, x in d.certificate.items() if k_.startswith("side")]
    return {"released": True, "verdict": v, "certificate": "sat_solver_assertion+witness_replay" if side else
            "witness_replay"}


def _union_verdict(ev: Evidence, q: Query) -> tuple[str, list]:
    """Verdict over H(n,2) u {exactly one node with indegree <= 3}: every member space must agree."""
    spaces = [MechanismSpace(ev, K_DECL)] + [
        MechanismSpace(ev, K_DECL, node_k=[K_BIG if j == i else K_DECL for j in range(N_M)]) for i in range(N_M)]
    vs = [_verdict(s, q)[0] for s in spaces]
    live = [v for v in vs if v != "inconsistent"]
    if not live:
        return "inconsistent", vs
    if all(v == "entailed" for v in live):
        return "entailed", vs
    if all(v == "refuted" for v in live):
        return "refuted", vs
    return "underdetermined", vs


def _challenge(ev: Evidence, menu, observe):
    """Buy up to CHALLENGES falsification tests where H(n,2) is definite and H(n,3) is uncertain about the
    measurement outcome, ranked by the H(n,3) uniform probability of contradicting H(n,2).  ``observe`` is the
    evaluator's measurement oracle (outcomes only after purchase)."""
    bought, log = [], []
    k = K_DECL
    avail = list(range(len(menu)))
    for _ in range(CHALLENGES):
        ms2, ms3 = MechanismSpace(ev, K_DECL), MechanismSpace(ev, K_BIG)
        if ms2.empty:
            break
        best = None
        for i in avail:
            x, node = menu[i]
            mq = Query.point(x, N_M, Intervention("none"), 1, Pred.lit(node, 1))
            v2, _, _ = _verdict(ms2, mq)
            if v2 not in ("entailed", "refuted"):
                continue
            c3 = ms3.claim_counts(mq)
            p_contra = (c3.den - c3.num) / c3.den if v2 == "entailed" else c3.num / c3.den
            if p_contra > 0 and (best is None or p_contra > best[0]):
                best = (p_contra, i)
        if best is None:
            break
        i = best[1]
        avail.remove(i)
        x, node = menu[i]
        val = observe(x, node)
        bought.append({"menu_index": i, "node": node, "value": val})
        ev = Evidence(ev.n, tuple(ev.observations) + (Observation(x, Intervention("none"), 1, ((node, val),)),))
        if MechanismSpace(ev, K_DECL).empty:
            k = K_BIG
            log.append({"class_change": "H(n,2) -> H(n,3)", "reason": "declared class contradicted by purchased "
                        "public measurement", "after_purchases": len(bought)})
            break
    return ev, k, bought, log


def m_world(p: dict) -> dict:
    seed = p["seed"]
    rng = random.Random(seed)
    net, bad = gen_mech(rng, outside=p["panel"] != "realizable")
    drng = random.Random(seed ^ 0x5EED)
    B = drng.choice(BUDGETS_M)
    specs, queries, menu = gen_design(drng, B)
    ev = evidence_of(net, specs)
    pub_hash = hashlib.sha256(json.dumps(ev.to_json(), sort_keys=True).encode()).hexdigest()
    observe_log = []

    def observe(x, node):                                     # evaluator oracle (purchases logged)
        val = (reference.run(net, x, Intervention("none"), 1)[-1] >> node) & 1
        observe_log.append([x, node, val])
        return val
    decisions = {pol: [] for pol in POLICIES}
    costs = {pol: 0.0 for pol in POLICIES}
    checks = []
    t0 = time.perf_counter()
    ev_c, k_c, bought, clog = _challenge(ev, menu, observe)          # once per world (tests the class)
    costs["challenge"] += time.perf_counter() - t0
    for q in queries:
        t0 = time.perf_counter()
        g = _gate(ev, K_DECL, q)
        costs["current"] += time.perf_counter() - t0
        decisions["current"].append({"released": g["released"], "verdict": g["verdict"], "cert": g["certificate"]})
        t0 = time.perf_counter()
        g3 = _gate(ev, K_BIG, q)
        costs["expanded"] += time.perf_counter() - t0
        decisions["expanded"].append({"released": g3["released"], "verdict": g3["verdict"], "cert": g3["certificate"]})
        t0 = time.perf_counter()
        uv, member = _union_verdict(ev, q)
        costs["robust_union"] += time.perf_counter() - t0
        decisions["robust_union"].append({"released": uv in ("entailed", "refuted"), "verdict": uv,
                                          "cert": "trusted_exact_computation" if uv in ("entailed", "refuted") else None})
        checks.append(assumption_check(
            declared_class="H(6,2)", alternative_classes=["H(6,2)+1", "H(6,3)"],
            evidence_consistent=not MechanismSpace(ev, K_DECL).empty,
            verdict_per_class={"H(6,2)": g["verdict"], "H(6,2)+1": uv, "H(6,3)": g3["verdict"]},
            aggregate_guarantee=("verified_all_classes" if g["verdict"] == uv == g3["verdict"] and g["released"]
                                 else "inconsistent" if g["verdict"] == "inconsistent" and g3["verdict"] == "inconsistent"
                                 else "abstain" if g["released"] else "underdetermined"),
            certificate_level="sat_solver_assertion+witness_replay" if g["released"] else "none",
            abstention_reason=None if g["released"] and g["verdict"] == g3["verdict"] else "class-dependent verdict"))
        t0 = time.perf_counter()
        gc = _gate(ev_c, k_c, q)
        costs["challenge"] += time.perf_counter() - t0
        decisions["challenge"].append({"released": gc["released"], "verdict": gc["verdict"], "cert": gc["certificate"],
                                       "class": f"H(6,{k_c})"})
        decisions["abstain"].append({"released": False, "verdict": "abstain", "cert": None})
    decisions["challenge_world"] = {"purchases": bought, "class_changes": clog, "final_class": f"H(6,{k_c})"}
    digest = hashlib.sha256(json.dumps(decisions, sort_keys=True).encode()).hexdigest()
    # ---- evaluator scoring (after decisions are fixed)
    truth = [int((reference.run(net, point_query_parts(q, N_M), q.intervention, q.horizon)[-1] >> q.target.node) & 1)
             for q in queries]
    v3 = [_verdict(MechanismSpace(ev, K_BIG), q)[0] for q in queries]     # status within a class containing truth
    score = {}
    for pol in POLICIES:
        s = {"released": 0, "false_verified": 0, "correct_release": 0, "unnecessary_block": 0,
             "false_uncertainty": 0, "measurements": 0, "class_changes": 0}
        for qi, d in enumerate(decisions[pol]):  # noqa: B007 (qi used below)
            rel = d["released"]
            if rel:
                s["released"] += 1
                claim_true = truth[qi] == 1                       # literal 'node = 1'
                ok = claim_true if d["verdict"] == "entailed" else not claim_true
                s["correct_release" if ok else "false_verified"] += 1
            else:
                cur = decisions["current"][qi]
                if cur["released"]:
                    claim_true = truth[qi] == 1
                    if (cur["verdict"] == "entailed") == claim_true:
                        s["unnecessary_block"] += 1
                if v3[qi] in ("entailed", "refuted"):
                    s["false_uncertainty"] += 1
        if pol == "challenge":
            s["measurements"] = len(bought)
            s["class_changes"] = len(clog)
        s["cost_s"] = costs[pol]
        score[pol] = s
    return {"panel": p["panel"], "index": p["index"], "seed": seed, "budget": B, "public_evidence_sha256": pub_hash,
            "declared_consistent": not MechanismSpace(ev, K_DECL).empty, "decisions": decisions,
            "decisions_sha256": digest, "assumption_checks": checks, "purchases_log": observe_log,
            "outside_nodes": len(bad), "truth": truth, "status_in_H3": v3, "score": score}
