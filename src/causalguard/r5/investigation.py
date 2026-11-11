"""Track A: sequential investigation episodes (bounded pilot).

World: an instance of the locked G strata (n = 8, k = 3) on separate A salts; public evidence = 8 one-step
observations; target = the first scheduled query (G design rules) that is UNDERDETERMINED by the public evidence
(evaluator-applied population restriction, logged).  Menu: 16 one-node one-step measurements (fresh start state,
no intervention or a persistent clamp of one other node); target-equivalent purchases (the target's effective
start state with the target node, h = 1) are excluded.  Budgets 0/1/2/4 are prefixes of ONE trajectory.

Readout (identical numbers in both backend arms; the AI pilot uses the uniform-H exact posterior in both):
  target status (exact counts -> entailed / refuted / underdetermined), P(target node = 1),
  per available menu item: P(outcome = 1) and exact expected information gain (bits) about the target.
Representation view differs by arm: D shows named analytic candidate rules per node (s4 analytic summary); the
generic arm (B) shows per-node counts and one explicit witness truth table.  Outcomes come only from the evaluator
after a purchase.

Policies: random, eig (target-directed exact EIG), disagreement (max outcome entropy, not target-directed),
oracle_lookahead (PRIVILEGED: sees hidden outcomes; reference only), and the AI (one local model) choosing
measurements through the JSON action API.  'Resolved at b' = a checked definite verdict after b purchases: for
deterministic policies the exact verdict; for the AI its stated verdict at that turn, verified by the common gate.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
import time

from .. import reference
from ..generators import world_seed
from ..s4.workspace import make_workspace
from ..schema import Evidence, Intervention, Observation, Query
from ..versionspace import point_query_parts
from . import data as D
from .contracts import investigation_step

A_SPLITS = {"calibration": "r5-A-cal-v1", "evaluation": "r5-A-eval-v1"}
A_BUDGET_OBS = 8
MENU = 16
BUDGETS = (0, 1, 2, 4)
MAX_PURCHASES = 4
MAX_CALLS = 8
DET_POLICIES = ("random", "eig", "disagreement")
REFERENCE_POLICIES = ("oracle_lookahead",)
PROMPT_VERSION = "r5-a-prompt-v2"  # v2: measure null = stop (calibration defect R5-02)


# --------------------------------------------------------------------------- worlds

def _eff(x, iv):
    m, v = iv.masks
    return (x & ~m) | v if iv.kind != "none" else x


def world(split: str, stratum: str, index: int) -> dict | None:
    """Hidden world + public episode, or None if no scheduled query is initially underdetermined (logged by the
    population builder)."""
    salt = A_SPLITS[split]
    inst = _a_instance(salt, stratum, index)
    design = D.make_design(salt, inst["mechanism_id"])
    ev = D.make_evidence(inst["net"], design, A_BUDGET_OBS)
    from ..s4.mechspace import MechanismSpace
    ms = MechanismSpace(ev, D.K)
    target = None
    for qid, q in design.queries:
        cc = ms.claim_counts(q)
        if 0 < cc.num < cc.den:
            target = (qid, q)
            break
    if target is None:
        return None
    rng = random.Random(world_seed(salt, "R5A-menu", index, stratum))
    menu = make_menu(rng, target[1], {o.state for o in ev.observations})
    labels = _labels(inst["mechanism_id"])
    pub = {"schema": "r5-a-public-v1", "task_id": hashlib.sha256(inst["mechanism_id"].encode()).hexdigest()[:16],
           "n": D.N, "k": D.K, "node_labels": labels, "evidence": ev.to_json(),
           "claims": [{"cid": "target", "query": q.to_json()}], "menu": menu}
    return {"pub": pub, "net": inst["net"], "identity": {"split": split, "stratum": stratum, "index": index,
                                                         "mechanism_id": inst["mechanism_id"], "target_qid": target[0]}}


MENU_SPEC = {"target_near": 4, "other_near": 4, "random": 8, "near": "Hamming distance 1-2 from the query's "
             "effective start state", "interventions": "none for near items; none or one-node clamp for random",
             "excluded": "target-equivalent (query effective start state with the target node, h = 1); duplicates; "
             "evidence start states"}


def make_menu(rng: random.Random, q: Query, used: set[int]) -> list[dict]:
    """PUBLIC, query-dependent menu (never uses the hidden mechanism or outcomes)."""
    s0 = _eff(point_query_parts(q, D.N), q.intervention)
    t = q.target.node
    forbidden = {(s0, t)} if q.horizon == 1 else set()
    clamp = q.intervention.assign if q.intervention.kind == "persistent_clamp" else ()
    menu: list[dict] = []

    def add(x, iv, node):
        key = (x, node, json.dumps(iv.to_json(), sort_keys=True))
        if x in used or (_eff(x, iv), node) in forbidden or any(
                (m["state"], m["node"], json.dumps(m["intervention"], sort_keys=True)) == key for m in menu):
            return False
        menu.append({"state": x, "intervention": iv.to_json(), "node": node})
        return True

    def near():
        d = rng.choice([1, 1, 2])
        x = s0
        for i in rng.sample(range(D.N), d):
            x ^= 1 << i
        for j, b in clamp:                      # keep the query's clamped nodes at their clamp values
            x = (x & ~(1 << j)) | (b << j)
        return x
    none = Intervention("none")
    while len(menu) < MENU_SPEC["target_near"]:
        add(near(), none, t)
    while len(menu) < MENU_SPEC["target_near"] + MENU_SPEC["other_near"]:
        add(near(), none, rng.choice([j for j in range(D.N) if j != t]))
    while len(menu) < MENU:
        x = rng.randrange(1 << D.N)
        if rng.random() < 0.5:
            iv, cl = none, set()
        else:
            c = rng.randrange(D.N)
            iv, cl = Intervention("persistent_clamp", ((c, rng.randint(0, 1)),)), {c}
        add(x, iv, rng.choice([j for j in range(D.N) if j not in cl]))
    order = list(range(MENU))
    rng.shuffle(order)                           # presentation order carries no information about item type
    return [menu[i] for i in order]


def _a_instance(salt, stratum, index):
    """A-specific instances: the locked G generators on a separate salt (rewired controls rewire the A instance
    of stratum index%3)."""
    import random as _r

    from ..generators import opaque_id
    if stratum == "rewired_control":
        src = _a_instance(salt, D.STRATA[index % 3], index)
        net = D.rewire(src["net"], _r.Random(world_seed(salt, "R5A-rewire", index, src["mechanism_id"])))
    else:
        rules, _ = D.GENERATORS[stratum](_r.Random(world_seed(salt, "R5A", index, stratum)))
        from ..schema import Network
        net = Network(D.N, tuple(r.canonical() for r in rules))
    return {"net": net, "mechanism_id": opaque_id("r5a", world_seed(salt, "R5A-mech", index, stratum))}


def _labels(mid: str) -> list[str]:
    from ..s4.tasks import node_labels
    return node_labels(mid, D.N)


def population(split: str, per_stratum: int, max_index: int = 400) -> tuple[list[dict], dict]:
    keys, log = [], {}
    for s in D.STRATA:
        got, tried = 0, 0
        i = 0
        while got < per_stratum and i < max_index:
            w = world(split, s, i)
            tried += 1
            if w is not None:
                keys.append({"split": split, "stratum": s, "index": i})
                got += 1
            i += 1
        log[s] = {"tried": tried, "accepted": got, "complete": got == per_stratum}
    return keys, log


# --------------------------------------------------------------------------- readout (public, exact)

def readout(ws, menu: list[dict], avail: list[int]) -> dict:
    claim = ws.pub["claims"][0]
    r = ws.check(claim)
    num, den = (int(r["counts"]["num"]), int(r["counts"]["den"])) if r["counts"] else (None, None)
    vals = ws.measurement_values(claim, [menu[i] for i in avail]) if avail else []
    items = []
    for i, v in zip(avail, vals):
        sz = {int(b): int(c) for b, c in v["outcome_sizes"].items()}
        tot = sz[0] + sz[1]
        items.append({"index": i, "p_outcome_1": sz[1] / tot if tot else None,
                      "eig_bits": None if v["eig_bits"] is None else round(v["eig_bits"], 6)})
    return {"status": r["verdict"], "p_target_1": None if num is None else num / den, "num": num, "den": den,
            "items": items}


def state_hash(ev: Evidence) -> str:
    return hashlib.sha256(json.dumps(ev.to_json(), sort_keys=True).encode()).hexdigest()[:16]


def _observe(net, item) -> int:
    iv = Intervention.from_json(item["intervention"])
    y = reference.run(net, item["state"], iv, 1)[-1]
    return (y >> item["node"]) & 1


def _purchase(ws, item, val):
    return ws.update([Observation(item["state"], Intervention.from_json(item["intervention"]), 1,
                                  ((item["node"], val),))])


def _h(p):
    return 0.0 if p in (0.0, 1.0) else -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


def choose(policy: str, ro: dict, avail: list[int], rng: random.Random, net=None, ws=None, menu=None) -> int:
    if policy == "random":
        return rng.choice(avail)
    if policy == "eig":
        return max(ro["items"], key=lambda it: ((it["eig_bits"] or 0.0), -it["index"]))["index"]
    if policy == "disagreement":
        return max(ro["items"], key=lambda it: (_h(it["p_outcome_1"] or 0.0), -it["index"]))["index"]
    if policy == "oracle_lookahead":          # PRIVILEGED: uses hidden outcomes (reference only)
        best = None
        for it in ro["items"]:
            i = it["index"]
            ws2 = _purchase(ws, menu[i], _observe(net, menu[i]))
            r2 = readout(ws2, menu, [])
            p = r2["p_target_1"]
            score = (r2["status"] in ("entailed", "refuted"), -abs(p - (1 if _truth(net, ws) else 0)) if p is not None else -1)
            if best is None or score > best[0]:
                best = (score, i)
        return best[1]
    raise ValueError(policy)


def _truth(net, ws) -> int:
    q = Query.from_json(ws.pub["claims"][0]["query"])
    tr = reference.run(net, point_query_parts(q, D.N), q.intervention, q.horizon)
    return (tr[-1] >> q.target.node) & 1


def det_episode(w: dict, policy: str, backend: str) -> dict:
    """Deterministic policy on one backend; outcomes come from the evaluator (``w['net']``) after purchase."""
    pub, net = w["pub"], w["net"]
    menu = pub["menu"]
    ws = make_workspace(backend, pub)
    rng = random.Random(f"r5A-random|{pub['task_id']}")
    avail = list(range(len(menu)))
    steps, curve = [], {}
    t0 = time.perf_counter()
    for step in range(MAX_PURCHASES + 1):
        ro = readout(ws, menu, avail if step < MAX_PURCHASES else [])
        if step in BUDGETS:
            curve[str(step)] = {"verdict": ro["status"], "p_target_1": ro["p_target_1"]}
        if step == MAX_PURCHASES:
            break
        pick = choose(policy, ro, avail, rng, net=net, ws=ws, menu=menu)
        val = _observe(net, menu[pick])
        prior_h = state_hash(ws.evidence)
        avail.remove(pick)
        ws = _purchase(ws, menu[pick], val)
        steps.append(investigation_step(step=step, prior_state_hash=prior_h, proposed=pick, accepted=True,
                                        menu_hash=hashlib.sha256(json.dumps(menu).encode()).hexdigest()[:16],
                                        purchased={"menu_index": pick, "node": menu[pick]["node"], "value": val},
                                        measurement_cost=1, updated_state_hash=state_hash(ws.evidence),
                                        model_calls=0, tool_calls=1))
    return {"policy": policy, "backend": backend, "steps": steps, "curve": curve,
            "wall_s": time.perf_counter() - t0}


# --------------------------------------------------------------------------- AI episodes

SYSTEM = ("You are a careful scientific investigator of a hidden deterministic system. You decide which "
          "measurements to buy to settle a question, using an exact symbolic tool whose numbers you can trust.")


def _bits(x, n):
    return "".join(str((x >> i) & 1) for i in range(n))


def render(pub: dict, ws, ro: dict, arm: str, avail: list[int], left: int, bought: list) -> str:
    from ..s4.pilot import render_claim, render_task
    n, L = pub["n"], pub["node_labels"]
    base = render_task({**pub, "claims": []}).rsplit("Claims:", 1)[0]
    lines = [base.rstrip(), "", "Question (target): " + render_claim(pub["claims"][0], pub).split(": ", 1)[1]]
    if bought:
        lines.append("Measurements bought so far:")
        for b in bought:
            it = pub["menu"][b["menu_index"]]
            lines.append(f"  item {b['menu_index']}: {_desc(it, L, n)} -> observed {L[it['node']]} = {b['value']}")
    lines += ["", "Exact tool readout over ALL mechanisms consistent with the evidence so far:",
              f"  target status: {ro['status']}; P(target node = 1) = {ro['p_target_1']:.4f} "
              f"({ro['num']} of {ro['den']} consistent mechanisms)"]
    lines.append("  " + _view(ws, arm))
    if left > 0 and avail:
        lines.append(f"Available measurements ({left} purchase(s) left). Each shows P(observed value = 1) and the "
                     "exact expected information gain (bits) about the target:")
        for it in ro["items"]:
            lines.append(f"  item {it['index']}: {_desc(pub['menu'][it['index']], L, n)}; P(=1) = "
                         f"{it['p_outcome_1']:.3f}; EIG = {it['eig_bits'] if it['eig_bits'] is not None else 'n/a'}")
    lines += ["", "Verdict meanings: entailed = target true in every consistent mechanism; refuted = false in every "
              "one; underdetermined = they disagree."]
    if left > 0 and avail:
        lines.append('Reply with ONLY one JSON object: {"verdict": "entailed|refuted|underdetermined", '
                     '"p_target": <probability the target node is 1>, "measure": <item number to buy next, or null to stop>}')
    else:
        lines.append('No purchases left. Reply with ONLY one JSON object: {"verdict": '
                     '"entailed|refuted|underdetermined", "p_target": <probability the target node is 1>}')
    return "\n".join(lines)


def _desc(it, L, n):
    iv = Intervention.from_json(it["intervention"])
    c = (" clamp " + ",".join(f"{L[j]}={b}" for j, b in iv.assign)) if iv.kind == "persistent_clamp" else ""
    return f"one step from {_bits(it['state'], n)}{c}, observe {L[it['node']]}"


def _view(ws, arm: str) -> str:
    st = ws.status()
    if arm == "D":
        parts = []
        for s in st.get("analytic_summary", []):
            ex = ", ".join(s["examples"][:2]) or "no named rule"
            parts.append(f"{s['node']}: {s['compatible_mechanisms']} candidates (e.g. {ex})")
        return "Mechanism view (named analytic rules): " + "; ".join(parts)
    pc = st.get("per_node_compatible") or {}
    return "Mechanism view (explicit candidate counts per node): " + ", ".join(f"{k}: {v}" for k, v in pc.items())


_JSON = re.compile(r"\{.*\}", re.S)


def parse_reply(text: str | None, avail: list[int], need_measure: bool) -> tuple[dict | None, str | None]:
    if not text:
        return None, "empty"
    m = _JSON.search(text)
    if not m:
        return None, "no_json"
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None, "bad_json"
    if not isinstance(obj, dict):
        return None, "not_object"
    v = obj.get("verdict")
    if v not in ("entailed", "refuted", "underdetermined"):
        return None, "bad_verdict"
    p = obj.get("p_target")
    p = float(p) if isinstance(p, (int, float)) and not isinstance(p, bool) and 0 <= p <= 1 else None
    out = {"verdict": v, "p_target": p}
    if need_measure:
        mi = obj.get("measure")
        if mi is None:
            out["measure"] = None                      # stop investigating (valid action; stopped prefix)
        elif not isinstance(mi, int) or isinstance(mi, bool) or mi not in avail:
            return None, "invalid_measure"
        else:
            out["measure"] = mi
    return out, None


def ai_episode(w: dict, arm: str, provider, budget, seed: int | None = 0) -> dict:
    """One AI investigation episode (<= MAX_CALLS physical attempts incl. retries; ``budget`` reserves ledger lines
    before dispatch).  The AI's stated verdict at turn b is its verdict at budget b."""
    from ..llm.harness import derive_seed
    from ..llm.providers import CapExceeded
    pub, net = w["pub"], w["net"]
    menu = pub["menu"]
    ws = make_workspace(arm, pub)
    avail = list(range(len(menu)))
    msgs = [{"role": "system", "content": SYSTEM}]
    calls, invalid, bought, steps, per_turn = [], [], [], [], {}
    status = "complete"
    turn = 0
    attempts_used = 0
    while turn <= MAX_PURCHASES:
        left = MAX_PURCHASES - turn
        ro = readout(ws, menu, avail if left > 0 else [])
        msgs.append({"role": "user", "content": render(pub, ws, ro, arm, avail, left, bought)})
        parsed = None
        while parsed is None:
            if attempts_used >= MAX_CALLS:
                status = "call_cap"
                break
            budget.current = f"{arm}|t{turn}|a{attempts_used}"
            try:
                res = provider.chat(msgs, 0.0, derive_seed(seed, pub["task_id"], f"{arm}|{turn}|{attempts_used}"),
                                    budget.before_attempt)
            except CapExceeded as e:
                status = f"cap:{e.scope}"
                break
            attempts_used += max(1, len(res.get("attempts", [])))
            calls.append({k: res.get(k) for k in ("ok", "raw_output", "failure", "request_hash", "attempts")})
            if not res["ok"]:
                invalid.append({"turn": turn, "reason": "call_failed"})
                continue
            parsed, why = parse_reply(res["raw_output"], avail, left > 0)
            msgs.append({"role": "assistant", "content": res["raw_output"] or ""})
            if parsed is None:
                invalid.append({"turn": turn, "reason": why})
                msgs.append({"role": "user", "content": f"Invalid reply ({why}). Reply with ONLY the JSON object "
                                                        "described above."})
        if parsed is None:
            break
        per_turn[str(turn)] = {"verdict": parsed["verdict"], "p_target": parsed["p_target"],
                               "readout_status": ro["status"], "readout_p": ro["p_target_1"]}
        if left == 0:
            break
        if parsed["measure"] is None:                  # stopped: the stated verdict holds for later budgets
            for b in range(turn + 1, MAX_PURCHASES + 1):
                per_turn[str(b)] = {**per_turn[str(turn)], "stopped_at": turn}
            status = "stopped"
            break
        pick = parsed["measure"]
        val = _observe(net, menu[pick])
        prior_h = state_hash(ws.evidence)
        avail.remove(pick)
        ws = _purchase(ws, menu[pick], val)
        eig_best = max(ro["items"], key=lambda it: ((it["eig_bits"] or 0.0), -it["index"]))["index"]
        bought.append({"menu_index": pick, "value": val, "eig_argmax": eig_best})
        steps.append(investigation_step(step=turn, prior_state_hash=prior_h, proposed=pick, accepted=True,
                                        menu_hash=hashlib.sha256(json.dumps(menu).encode()).hexdigest()[:16],
                                        purchased={"menu_index": pick, "node": menu[pick]["node"], "value": val},
                                        measurement_cost=1, updated_state_hash=state_hash(ws.evidence),
                                        model_calls=len(calls), tool_calls=1))
        turn += 1
    # gate checks of the AI's stated definite verdicts at each budget prefix (common checker)
    from ..s4.checking import check, validate_proposal
    resolved = {}
    ws_b = make_workspace(arm, pub)
    claim = pub["claims"][0]
    for b in range(MAX_PURCHASES + 1):
        if str(b) in per_turn and b in BUDGETS:
            v = per_turn[str(b)]["verdict"]
            if v in ("entailed", "refuted"):
                d = check(validate_proposal({"cid": "target", "asserted": v}, {"target": claim}), ws_b)
                resolved[str(b)] = {"asserted": v, "check": d.proposal_check_status}
            else:
                resolved[str(b)] = {"asserted": v, "check": None}
        if b < len(bought):
            it = menu[bought[b]["menu_index"]]
            ws_b = _purchase(ws_b, it, bought[b]["value"])
    lat = sum(a.get("latency_s") or 0 for c in calls for a in (c.get("attempts") or []))
    toks = sum((a.get("prompt_tokens") or 0) + (a.get("completion_tokens") or 0)
               for c in calls for a in (c.get("attempts") or []))
    return {"arm": arm, "status": status, "calls": calls, "n_attempts": attempts_used, "invalid": invalid,
            "per_turn": per_turn, "purchases": bought, "steps": steps, "gate": resolved,
            "server_latency_s": lat, "tokens": toks, "prompt_version": PROMPT_VERSION}


# --------------------------------------------------------------------------- runner items

def a_det_item(p: dict) -> dict:
    w = world(p["split"], p["stratum"], p["index"])
    if w is None:
        return {"identity": p, "excluded": "no initially underdetermined scheduled query"}
    out = {"identity": w["identity"], "truth": _truth(w["net"], make_workspace("D", w["pub"])), "episodes": []}
    for pol in DET_POLICIES + REFERENCE_POLICIES:
        for be in (("D", "B") if pol in DET_POLICIES else ("D",)):
            out["episodes"].append(det_episode(w, pol, be))
    return out


def a_ai_item(p: dict) -> dict:
    import os
    from pathlib import Path

    from ..llm.harness import CallBudget
    from ..llm.providers import make_provider
    w = world(p["split"], p["stratum"], p["index"])
    if w is None:
        return {"identity": p, "excluded": "no initially underdetermined scheduled query"}
    ledger = p["call_ledger"]
    if ledger.startswith("RUNS/"):
        ledger = str(Path(os.environ.get("CAUSALGUARD_RUNS", "runs")) / ledger[len("RUNS/"):])
    out = {"identity": w["identity"], "model": p["provider"]["model"], "episodes": {}}
    for arm in p.get("arms", ("D", "B")):
        budget = CallBudget(MAX_CALLS, p["global_cap"], ledger, world_id=f"{w['pub']['task_id']}|{arm}",
                            phase=p["phase"], phase_cap=p["phase_cap"])
        out["episodes"][arm] = ai_episode(w, arm, make_provider(p["provider"]), budget, seed=0)
    # evaluator side, after both episodes are fixed
    out["truth"] = _truth(w["net"], make_workspace("D", w["pub"]))
    return out
