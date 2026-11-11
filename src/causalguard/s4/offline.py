"""S4 offline programs (no model calls).  Each function is a runner item (payload dict -> JSON-able dict).

map_world      fixed offline family/cost map: reference verdicts at nested evidence prefixes, fixed-request
               replay of the same claims through B/C/D (agreement + cost), codec-induced averaging and
               shortest-model forecasts on underdetermined claims (the 'less evidence' secondary), evaluator-side
               description lengths of the hidden mechanism (family map only; never shown to an agent)
stress_item    larger symbolic stress cases: which backend finishes at which n (resource refusals recorded)
known_item     known-mechanism checking panel (formal paper, public rules): support-local exact checks with
               c, d, mu reported separately; exact enumeration cross-check where n is small, labelled random
               corroboration otherwise
active_world   S4-B prototype: start from claims underdetermined by D, buy 0/1/2/4 one-node measurements from a
               fixed menu (target experiment and its duplicates excluded), random vs exact-EIG policy, the EIG
               policy crossed with B/C/D; every purchased observation is logged
"""
from __future__ import annotations

import random
import time

from .. import reference
from ..schema import Evidence, Intervention, Network, Observation, Query, Rule
from .evaluator import Evaluator
from .tasks import S4_K, make_design, make_evidence, make_s4_world, public_task
from .workspace import Limits, make_workspace

MAP_PREFIXES = (8, 12, 16, 24)


def _hidden_lengths(net: Network, k: int) -> dict:
    from ..codec import encode_network
    from .hcode import describe
    out = {}
    for cd in ("index", "gate", "circuit", "lut", "dnf", "bdd"):
        try:
            out[cd] = encode_network(net, cd).total_bits
        except Exception as e:  # recorded, not hidden
            out[cd] = f"error:{type(e).__name__}"
    for v in ("full", "flat", "no_order", "no_analytic"):
        b, mode, _ = describe(net, k, v)
        out[f"cgh_{v}"] = b
        out[f"cgh_{v}_mode"] = mode
    return out


def map_world(p: dict) -> dict:
    from .prior import CODES, Averager
    world = make_s4_world(p["salt"], p["index"], p["family"])
    design = make_design(p["salt"], p["index"], p["family"], budget=max(p.get("prefixes", MAP_PREFIXES)))
    full = make_evidence(world, design)
    out = {"world_id": world.world_id, "family": world.family, "design_seed": design.design_seed,
           "hidden_description_bits": _hidden_lengths(world.net, world.max_indegree), "prefixes": {}}
    for B in p.get("prefixes", MAP_PREFIXES):
        ev = Evidence(full.n, full.observations[:B], full.regime)
        pub = public_task(world, design, ev)
        cell = {"replay": {}, "claims": []}
        res = {}
        for arm in p.get("backends", ("B", "C", "D")):
            t0 = time.perf_counter()
            ws = make_workspace(arm, pub, Limits())
            rs = [ws.check(c) for c in pub["claims"]]
            res[arm] = rs
            cell["replay"][arm] = {"wall_s": time.perf_counter() - t0, "build_s": ws.cost["build_s"],
                                   "verdicts": [r["verdict"] for r in rs],
                                   "meters": [r.get("certificate", {}).get("meter") for r in rs]}
        t0 = time.perf_counter()
        av = Averager(ev, world.max_indegree)
        cell["averager_build_s"] = time.perf_counter() - t0
        cell["struct_status"] = av.struct_status
        cell["log10_V"] = av.vs.log10_size()
        arms = list(res)
        for i, c in enumerate(design.claims):
            q = c.query
            vs = [res[a][i]["verdict"] for a in arms]
            row = {"cid": c.cid, "h": q.horizon, "iv": q.intervention.kind, "verdicts": dict(zip(arms, vs)),
                   "agree": len(set(vs)) == 1, "truth_holds": int(reference.holds(
                       q.target, reference.to_bits(reference.run(world.net, _x0(q, full.n), q.intervention,
                                                                 q.horizon)[-1], full.n)))}
            ref = res[arms[0]][i]
            row["counts"] = ref["counts"]
            if row["agree"] and vs[0] == "underdetermined":
                row["prob"] = {cd: av.probability(cd, q) for cd in CODES}
                row["shortest"] = {cd: av.shortest_prediction(cd, q) for cd in ("index", "cgh_flat", "cgh_prior")}
            cell["claims"].append(row)
        out["prefixes"][str(B)] = cell
    return out


def _x0(q: Query, n: int) -> int:
    from ..versionspace import point_query_parts
    return point_query_parts(q, n)


# --------------------------------------------------------------------------- stress

def stress_item(p: dict) -> dict:
    """Random bounded network at size n; one-step uniform evidence; h <= 2 claims; one backend per item."""
    rng = random.Random(p["seed"])
    n, k, B = p["n"], p.get("k", S4_K), p["budget"]
    rules = []
    for _ in range(n):
        d = rng.randint(1, k)
        rules.append(Rule(tuple(sorted(rng.sample(range(n), d))), rng.getrandbits(1 << d)).canonical())
    net = Network(n, tuple(rules))
    obs = []
    for _ in range(B):
        x = rng.randrange(1 << n)
        y = reference.run(net, x, Intervention("none"), 1)[-1]
        obs.append(Observation(x, Intervention("none"), 1, tuple((j, (y >> j) & 1) for j in range(n))))
    ev = Evidence(n, tuple(obs))
    claims = []
    for i in range(p.get("claims", 4)):
        iv = Intervention("initial_edit", ((rng.randrange(n), rng.randint(0, 1)),))
        q = Query.point(rng.randrange(1 << n), n, iv, rng.choice(p.get("horizons", [1, 2])),
                        __import__("causalguard.schema", fromlist=["Pred"]).Pred.lit(rng.randrange(n), 1))
        claims.append({"cid": f"c{i}", "query": q.to_json()})
    pub = {"n": n, "k": k, "node_labels": [f"x{i}" for i in range(n)], "evidence": ev.to_json(), "claims": claims}
    t0 = time.perf_counter()
    ws = make_workspace(p["backend"], pub, Limits(explicit_max_n=p.get("explicit_max_n", 10)))
    build = time.perf_counter() - t0
    rs = [ws.check(c) for c in claims]
    return {"n": n, "backend": p["backend"], "budget": B, "build_s": build,
            "wall_s": time.perf_counter() - t0, "verdicts": [r["verdict"] for r in rs],
            "counts": [r["counts"] for r in rs], "reasons": [r.get("reason") for r in rs],
            "per_claim_s": [r["wall_s"] for r in rs]}


# --------------------------------------------------------------------------- known-mechanism panel

def known_item(p: dict) -> dict:
    from .analytic import Gate, gate_value, support_local_query, vector
    rng = random.Random(p["seed"])
    n = p["n"]
    fams = ["XOR", "XNOR", "AND", "OR", "KOFN", "EXACTK", "MAJORITY_STRICT", "IMPLIES", "CANALIZING"]
    gates = []
    for _ in range(n):
        f = rng.choice(fams)
        d = rng.choice([2, 3, 4]) if f not in ("IMPLIES",) else 2
        # overlapping supports: draw inputs from a window so neighbouring nodes share coordinates
        lo = rng.randrange(n)
        I = tuple(sorted({(lo + o) % n + 1 for o in rng.sample(range(6), d)}))
        d = len(I)
        if f == "KOFN":
            g = Gate("KOFN", I, (rng.randint(1, d),))
        elif f == "EXACTK":
            g = Gate("EXACTK", I, (rng.randint(0, d),))
        elif f == "IMPLIES":
            g = Gate("IMPLIES", I[:2], tuple(I[:2]))
        elif f == "CANALIZING":
            g = Gate("CANALIZING", I, (I[0], rng.randint(0, 1), rng.randint(0, 1), Gate("XOR", I[1:])))
        else:
            g = Gate(f, I)
        gates.append(g)
    rows = []
    for _ in range(p.get("queries", 6)):
        Q = rng.sample(range(1, n + 1), rng.choice([2, 3, 4]))
        query = {i: rng.randint(0, 1) for i in Q}
        t0 = time.perf_counter()
        r = support_local_query(gates, query, n)
        dt = time.perf_counter() - t0
        row = {"queried": {str(k): v for k, v in query.items()}, "count": str(r.count), "c": r.c, "d": r.d,
               "mu": r.mu, "enumerated": r.enumerated, "reduction_vs_independent": r.reduction_vs_independent,
               "log2_reduction_vs_global": n - r.c, "wall_s": dt,
               "families": sorted({gates[i - 1].family for i in Q})}
        if n <= 14:      # exact global cross-check by enumeration of all 2^n rows (independent semantics)
            brute = sum(1 for j in range(1, (1 << n) + 1)
                        if all(gate_value(gates[i - 1], vector(j, n)) == v for i, v in query.items()))
            row["global_enumeration_count"] = str(brute)
            row["exact_match"] = brute == r.count
        else:            # corroboration only (NOT a proof): witness replay + random rows vs support-local membership
            ok = True
            if r.witness_index is not None:
                ok &= all(gate_value(gates[i - 1], vector(r.witness_index, n)) == v for i, v in query.items())
            row["witness_replayed"] = ok
            row["verification"] = "corroboration_only"
        rows.append(row)
    return {"n": n, "seed": p["seed"], "gates": [g.family for g in gates], "queries": rows}


# --------------------------------------------------------------------------- S4-B active investigation

def _menu(rng: random.Random, n: int, size: int, exclude: set) -> list[dict]:
    menu = []
    while len(menu) < size:
        x = rng.randrange(1 << n)
        kind = rng.choice(["none", "persistent_clamp"])
        if kind == "none":
            iv = Intervention("none")
        else:
            iv = Intervention("persistent_clamp", ((rng.randrange(n), rng.randint(0, 1)),))
        clamped = {j for j, _ in iv.assign} if iv.kind == "persistent_clamp" else set()
        node = rng.choice([j for j in range(n) if j not in clamped])
        m, v = iv.masks
        eff = (x & ~m) | v if iv.kind != "none" else x
        if (eff, node) in exclude or any(e[0] == eff for e in exclude):
            continue
        menu.append({"state": x, "intervention": iv.to_json(), "node": node})
    return menu


def active_world(p: dict) -> dict:
    ev = Evaluator(p["salt"], p["index"], p["family"], budget=p.get("budget", 12))
    pub = ev.public()
    refs = ev.reference(crosscheck_sat=False)
    n = pub["n"]
    targets = [(c, r) for c, r in zip(pub["claims"], refs) if r.verdict == "underdetermined"][:p.get("targets", 2)]
    out = {"world_id": ev.world.world_id, "family": p["family"], "n_initially_underdetermined":
           sum(r.verdict == "underdetermined" for r in refs), "targets": []}
    for c, r in targets:
        q = Query.from_json(c["query"])
        s0 = _x0(q, n)
        m, v = q.intervention.masks
        eff = (s0 & ~m) | v
        rng = random.Random(f"{p['salt']}|S4B-menu|{p['index']}|{c['cid']}")
        menu = _menu(rng, n, p.get("menu", 12), {(eff, q.target.node)})
        trow = {"cid": c["cid"], "truth_holds": r.truth_holds, "menu": menu, "policies": {}}
        for policy, arm in [("random", "D"), ("eig", "B"), ("eig", "C"), ("eig", "D")]:
            ws = make_workspace(arm, pub)
            prng = random.Random(f"{p['salt']}|S4B-random|{p['index']}|{c['cid']}")
            bought, curve, t0 = [], {}, time.perf_counter()
            avail = list(range(len(menu)))
            for step in range(max(p.get("budgets", [0, 1, 2, 4])) + 1):
                if step in p.get("budgets", [0, 1, 2, 4]):
                    res = ws.check(c)
                    num, den = (int(res["counts"]["num"]), int(res["counts"]["den"])) if res["counts"] else (None, None)
                    curve[str(step)] = {"verdict": res["verdict"], "p": None if num is None else num / den,
                                        "forecast_correct": None if num is None or 2 * num == den else
                                        int((2 * num > den) == bool(r.truth_holds))}
                if step == max(p.get("budgets", [0, 1, 2, 4])) or not avail:
                    break
                if policy == "random":
                    pick = prng.choice(avail)
                else:
                    vals = ws.measurement_values(c, [menu[i] for i in avail])
                    pick = avail[max(range(len(avail)), key=lambda t: ((vals[t]["eig_bits"] or 0), -t))]
                avail.remove(pick)
                it = menu[pick]
                iv = Intervention.from_json(it["intervention"])
                val = ev.observe(it["state"], iv, it["node"])
                bought.append({"menu_index": pick, "observed": val})
                ws = ws.update([Observation(it["state"], iv, 1, ((it["node"], val),))])
            trow["policies"][f"{policy}|{arm}"] = {"purchases": bought, "curve": curve,
                                                  "wall_s": time.perf_counter() - t0}
        out["targets"].append(trow)
    return out


# --------------------------------------------------------------------------- misspecification / action diagnostic

def misspec_world(p: dict) -> dict:
    """Separately scored diagnostic: the hidden mechanism is OUTSIDE the declared class (``n_out`` nodes get a
    4-input rule while H declares k = 3).  Verified conclusions are executed as simulated actions on the hidden
    system; postcondition violations show that a proof is relative to its assumptions.  Also reports how often
    the evidence itself exposes the misspecification (empty V(D) -> inconsistent assumptions)."""
    import random as _r

    from .checking import check, validate_proposal
    from .evaluator import Evaluator
    ev = Evaluator(p["salt"], p["index"], p["family"])
    rng = _r.Random(f"{p['salt']}|misspec|{p['index']}|{p['family']}")
    rules = list(ev.world.net.rules)
    n = ev.world.net.n
    for j in rng.sample(range(n), p.get("n_out", 1)):
        ins = tuple(sorted(rng.sample(range(n), 4)))
        while True:
            t = rng.getrandbits(16)
            if Rule(ins, t).canonical().arity == 4:
                break
        rules[j] = Rule(ins, t)
    ev.world.net = Network(n, tuple(rules))                   # hidden mechanism replaced (evaluator side only)
    ev.evidence = make_evidence(ev.world, ev.design)
    ev._pub = public_task(ev.world, ev.design, ev.evidence)
    pub = ev.public()
    ws = make_workspace("D", pub)
    cby = {c["cid"]: c for c in pub["claims"]}
    rows = []
    for c in pub["claims"]:
        r = ws.check(c)
        row = {"cid": c["cid"], "verdict": r["verdict"]}
        if r["verdict"] in ("entailed", "refuted"):
            d = check(validate_proposal({"cid": c["cid"], "asserted": r["verdict"]}, cby), ws)
            held = ev.execute_action(Query.from_json(c["query"]))["postcondition_held"]
            row.update(status=d.proposal_check_status,
                       postcondition_violated=(held != (r["verdict"] == "entailed")))
        rows.append(row)
    return {"family": p["family"], "index": p["index"], "inconsistent": ws._empty(), "claims": rows}
