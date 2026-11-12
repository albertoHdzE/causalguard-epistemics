"""Track G populations: eight structural strata (synthetic), nested evidence designs, novel query schedules,
identity fields and split audits.  Specification ``G_POPULATION_SPEC`` below is hashed into the design lock.

All mechanisms lie in H(n = 8, k = 3) (bounded indegree, synchronous update).  The strata are OUR synthetic
generators, written before any R5 evaluation score was computed; they are not externally chosen.  They are
deliberately different from the R4 map families: R4's exact cyclic templates and equal repeated modules (which the
CGH prior encodes exactly) do not occur; the closest strata carry structural exceptions or unequal modules.

  S1 template_exceptions   a cyclic offset template at every node, then 1-2 nodes receive a structural exception
                           (different local rule on the same offsets, or one input rewired)
  S2 imperfect_modules     unequal block partition (3+3+2, module of size 3 does not divide n) OR two 4-blocks
                           where one block copy differs at one position
  S3 shared_motifs         two shared local tables; each node uses one with a RANDOM support and a random role
                           order (sharing without cyclic physical order)
  S4 feedforward_hetero    random topological order; inputs only from earlier nodes; roots are constants or
                           self-memory; heterogeneous gates (AND/OR/NAND/NOR/XOR/threshold/canalizing/LUT)
  S5 feedback_canalizing   every node has >= 1 input from a node at the same or later rank (cycles); nested
                           canalizing rules with heterogeneous canalizing values and fallbacks
  S6 mixed_parity_thresh   per node parity (XOR/XNOR), threshold k-of-d, majority, exact-k or random LUT
  S7 rewired_control       degree-preserving rewiring (double-edge swaps) of an S1/S2/S3 mechanism of the SAME
                           split; each node keeps its local table and indegree; clustered with its source
  S8 uniform_H             null: every node uniform over the complete class

Identity: every instance carries source_group_id, mechanism_id, split, transformation_id; evidence/query ids are
added by the design.  S7 shares the source_group_id of its source mechanism (paired control).
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass

from ..generators import canalizing_rule, gate_rule, opaque_id, world_seed
from ..s4.hcode import local_catalogue, offset_rule
from ..schema import Evidence, Intervention, Network, Observation, Pred, Query, Rule, content_hash

N, K = 8, 3
STRATA = ("template_exceptions", "imperfect_modules", "shared_motifs", "feedforward_hetero",
          "feedback_canalizing", "mixed_parity_thresh", "rewired_control", "uniform_H")
SPLITS = {"calibration": {"salt": "r5-G-cal-v1", "per_stratum": 8},
          "evaluation": {"salt": "r5-G-eval-v1", "per_stratum": 40},
          # R6: fresh mechanisms from the SAME locked generators (G_POPULATION_SPEC unchanged), never scored in R5
          "evaluation_r6": {"salt": "r6-G-eval-v1", "per_stratum": 40},
          # R7 sprint benchmark (pre-sprint): fresh mechanisms from the SAME locked generators; never model-facing
          # before R7.  'sprint_train' is used only to fit the surface reference rule (no model ever sees it).
          "sprint_train": {"salt": "r7-sprint-train-v1", "per_stratum": 40},
          "sprint_smoke": {"salt": "r7-sprint-smoke-v1", "per_stratum": 1},
          "sprint_pilot": {"salt": "r7-sprint-pilot-v1", "per_stratum": 3},
          "sprint_main": {"salt": "r7-sprint-main-v1", "per_stratum": 26},
          # R7 pilot revision 1 (D76): fresh pilot worlds after the wording change
          "sprint_pilot2": {"salt": "r7-sprint-pilot2-v1", "per_stratum": 4},
          "sprint_pilot3": {"salt": "r7-sprint-pilot3-v1", "per_stratum": 4}}       # revision 2 (D78)
BUDGETS = (8, 16, 24)
PRIMARY_BUDGET = 16
N_QUERIES = 8
DESIGN_VERSION = "r5-g-design-v1"
G_POPULATION_SPEC = {
    "version": "r5-g-population-v1", "n": N, "k": K, "strata": list(STRATA),
    "S1": {"template_arity": [2, 3, 3], "table": "nondegenerate; analytic catalogue w.p. 0.5", "exceptions": [1, 2],
           "exception_kind": ["new_local_rule_same_offsets", "rewire_one_input"]},
    "S2": {"variants": ["3+3+2 (module size 3, remainder block of 2 random rules)",
                        "4+4 with one position of the second copy replaced"], "external_input_prob": 0.5},
    "S3": {"motifs": 2, "arity": [2, 3], "assignment": "4 nodes per motif, random", "support": "random",
           "role_order": "random permutation per node"},
    "S4": {"indegree": [1, 2, 3], "roots": "const0/const1/self-memory",
           "gates": ["AND", "OR", "NAND", "NOR", "XOR", "KOFN", "CANALIZING", "LUT"]},
    "S5": {"indegree": [2, 3], "feedback": ">=1 input of rank >= own rank",
           "rule": "nested canalizing (random order/values) w.p. 0.6, canalizing-then-XOR/AND fallback otherwise"},
    "S6": {"choices": ["XOR", "XNOR", "KOFN", "MAJORITY", "EXACTK", "LUT"], "arity": [2, 3]},
    "S7": {"source": "stratum (i mod 3) of S1/S2/S3, same index i, same split", "swaps": "2 x edges attempts"},
    "S8": {"node_rule": "uniform over candidate_class(8, 3)"},
    "evidence": {"budgets": list(BUDGETS), "nested": True, "clamp_positions": "i % 4 == 3",
                 "clamp_nodes": [1, 2], "states": "distinct uniform"},
    "queries": {"count": N_QUERIES, "h1": 4, "h2": 4, "literal": "target node = 1",
                "interventions": ["none", "initial_edit", "persistent_clamp"],
                "novelty": "start and effective start state not among ANY of the 24 evidence inputs",
                "exclusions": "duplicate (s0, intervention, h, target); clamped target"},
}


def spec_hash() -> str:
    return hashlib.sha256(json.dumps(G_POPULATION_SPEC, sort_keys=True).encode()).hexdigest()


# --------------------------------------------------------------------------- helpers

def role_rule(roles: list[int], table: int, n: int = N) -> Rule:
    """Rule whose local input t is node roles[t] (any order; the owner offset_rule with base 0)."""
    return offset_rule(0, tuple(roles), table, n)


def _nondeg(rng: random.Random, d: int, analytic_p: float = 0.5) -> int:
    if d == 0:
        return rng.randint(0, 1)
    if rng.random() < analytic_p:
        cands = [t for _, t in local_catalogue(d) if Rule(tuple(range(d)), t).canonical().arity == d]
        return rng.choice(cands)
    while True:
        t = rng.getrandbits(1 << d)
        if Rule(tuple(range(d)), t).canonical().arity == d:
            return t


def _kofn(d: int, kk: int) -> int:
    return sum(1 << y for y in range(1 << d) if bin(y).count("1") >= kk)


def _exactk(d: int, kk: int) -> int:
    return sum(1 << y for y in range(1 << d) if bin(y).count("1") == kk)


def _hetero_gate(rng: random.Random, ins: list[int], choices: tuple[str, ...]) -> Rule:
    d = len(ins)
    g = rng.choice(choices)
    if d == 1:
        return Rule((ins[0],), rng.choice([0b10, 0b01]))
    if g in ("AND", "OR", "NAND", "NOR", "XOR", "XNOR"):
        return gate_rule(g, ins)
    if g == "KOFN":
        return role_rule(ins, _kofn(d, rng.randint(1, d)))
    if g == "MAJORITY":
        return role_rule(ins, _kofn(d, d // 2 + 1))
    if g == "EXACTK":
        return role_rule(ins, _exactk(d, rng.randint(0, d)))
    if g == "CANALIZING":
        return canalizing_rule(rng, ins)
    return role_rule(ins, _nondeg(rng, d, 0.0))


def _rules_to_roles(net: Network) -> list[tuple[list[int], int]]:
    return [(list(r.inputs), r.table) for r in net.rules]


# --------------------------------------------------------------------------- strata

def _template(rng):
    d = rng.choice([2, 3, 3])
    offs = sorted(rng.sample(range(N), d))
    return d, offs, _nondeg(rng, d)


def gen_template_exceptions(rng):
    d, offs, t = _template(rng)
    rules = [offset_rule(i, tuple(offs), t, N) for i in range(N)]
    info = {"template": {"offsets": offs, "table": t}, "exceptions": []}
    for j in rng.sample(range(N), rng.choice([1, 2])):
        if rng.random() < 0.5:
            while True:
                t2 = _nondeg(rng, d)
                if t2 != t:
                    break
            rules[j] = offset_rule(j, tuple(offs), t2, N)
            info["exceptions"].append({"node": j, "kind": "new_local_rule"})
        else:
            roles = [(j + o) % N for o in offs]
            pos = rng.randrange(d)
            alt = [x for x in range(N) if x not in roles]
            roles[pos] = rng.choice(alt)
            rules[j] = role_rule(roles, t)
            info["exceptions"].append({"node": j, "kind": "rewire_one_input"})
    return rules, info


def _module(rng, m):
    mod = []
    for p in range(m):
        d = rng.choice([2, 3]) if m > 2 else rng.choice([1, 2])
        local = sorted(set([p] + rng.sample([q for q in range(m) if q != p], min(d, m) - 1)))
        if rng.random() < 0.5:                                    # one input outside the block (relative offset)
            local[-1] = rng.choice(range(m, N))
            local = sorted(set(local))
        mod.append((tuple(local), _nondeg(rng, len(local))))
    return mod


def gen_imperfect_modules(rng):
    if rng.random() < 0.5:
        mod = _module(rng, 3)
        rules = []
        for b in range(2):
            for p in range(3):
                offs, t = mod[p]
                rules.append(offset_rule(3 * b, offs, t, N))
        for _j in (6, 7):                                         # remainder block: random rules
            d = rng.choice([2, 3])
            rules.append(role_rule(rng.sample(range(N), d), _nondeg(rng, d)))
        return rules, {"variant": "3+3+2"}
    mod = _module(rng, 4)
    rules = [offset_rule(4 * b, mod[p][0], mod[p][1], N) for b in range(2) for p in range(4)]
    p = rng.randrange(4)
    offs, t = mod[p]
    while True:
        t2 = _nondeg(rng, len(offs))
        if t2 != t:
            break
    rules[4 + p] = offset_rule(4, offs, t2, N)
    return rules, {"variant": "4+4-imperfect", "position": p}


def gen_shared_motifs(rng):
    motifs = [(d, _nondeg(rng, d)) for d in (rng.choice([2, 3]), rng.choice([2, 3]))]
    assign = [0] * 4 + [1] * 4
    rng.shuffle(assign)
    rules = []
    for j in range(N):
        d, t = motifs[assign[j]]
        roles = rng.sample(range(N), d)                           # random support AND random role order
        rules.append(role_rule(roles, t))
    return rules, {"assign": assign}


def gen_feedforward(rng):
    order = list(range(N))
    rng.shuffle(order)
    rules = [None] * N
    gates = ("AND", "OR", "NAND", "NOR", "XOR", "KOFN", "CANALIZING", "LUT")
    for r, j in enumerate(order):
        if r == 0:
            c = rng.choice(["const0", "const1", "self"])
            rules[j] = Rule((), 0) if c == "const0" else Rule((), 1) if c == "const1" else Rule((j,), 0b10)
            continue
        d = min(rng.choice([1, 2, 3]), r)
        rules[j] = _hetero_gate(rng, rng.sample(order[:r], d), gates)
    return rules, {"order": order}


def gen_feedback_canalizing(rng):
    order = list(range(N))
    rng.shuffle(order)
    rank = {j: r for r, j in enumerate(order)}
    rules = []
    for j in range(N):
        d = rng.choice([2, 3])
        back = [x for x in range(N) if rank[x] >= rank[j]]
        ins = {rng.choice(back)}
        while len(ins) < d:
            ins.add(rng.randrange(N))
        ins = list(ins)
        if rng.random() < 0.6:
            rules.append(canalizing_rule(rng, ins))
        else:                                                      # canalizing on one input, XOR/AND fallback
            rng.shuffle(ins)
            c, o = rng.randint(0, 1), rng.randint(0, 1)
            fb = rng.choice(["XOR", "AND"])
            rest = ins[1:]

            def f(v, c=c, o=o, fb=fb):
                if v[0] == c:
                    return o
                tail = v[1:]
                return (sum(tail) % 2) if fb == "XOR" else int(all(tail))
            t = sum(1 << y for y in range(1 << d) if f([(y >> s) & 1 for s in range(d)]))
            rules.append(role_rule([ins[0]] + rest, t))
    return rules, {"order": order}


def gen_mixed(rng):
    rules = []
    for _ in range(N):
        d = rng.choice([2, 3])
        rules.append(_hetero_gate(rng, rng.sample(range(N), d), ("XOR", "XNOR", "KOFN", "MAJORITY", "EXACTK", "LUT")))
    return rules, {}


def gen_uniform(rng):
    from ..versionspace import candidate_class
    cls = candidate_class(N, K)
    return [cls.rules[rng.randrange(cls.size)] for _ in range(N)], {}


def rewire(net: Network, rng: random.Random) -> Network:
    """Degree-preserving rewiring: double-edge swaps on (input -> node) edges; each node keeps its local table in
    role order (inputs replaced in place) and its indegree; outdegrees are preserved by every swap."""
    roles = [list(r.inputs) for r in net.rules]
    tables = [r.table for r in net.rules]
    edges = [(j, p) for j in range(net.n) for p in range(len(roles[j]))]
    for _ in range(2 * max(1, len(edges))):
        if len(edges) < 2:
            break
        (a, pa), (b, pb) = rng.sample(edges, 2)
        if a == b:
            continue
        ua, ub = roles[a][pa], roles[b][pb]
        if ua == ub or ub in roles[a] or ua in roles[b]:
            continue
        roles[a][pa], roles[b][pb] = ub, ua
    return Network(net.n, tuple(role_rule(roles[j], tables[j], net.n).canonical() for j in range(net.n)))


GENERATORS = {"template_exceptions": gen_template_exceptions, "imperfect_modules": gen_imperfect_modules,
              "shared_motifs": gen_shared_motifs, "feedforward_hetero": gen_feedforward,
              "feedback_canalizing": gen_feedback_canalizing, "mixed_parity_thresh": gen_mixed,
              "uniform_H": gen_uniform}


@dataclass
class Instance:
    split: str
    stratum: str
    index: int
    mechanism_id: str
    source_group_id: str
    transformation_id: str
    net: Network
    info: dict

    def identity(self) -> dict:
        return {"split": self.split, "stratum": self.stratum, "index": self.index, "mechanism_id": self.mechanism_id,
                "source_group_id": self.source_group_id, "transformation_id": self.transformation_id}


def make_instance(split: str, stratum: str, index: int) -> Instance:
    salt = SPLITS[split]["salt"]
    if stratum == "rewired_control":
        src = make_instance(split, STRATA[index % 3], index)
        rng = random.Random(world_seed(salt, "R5G-rewire", index, src.mechanism_id))
        net = rewire(src.net, rng)
        mid = opaque_id("r5m", world_seed(salt, "R5G-mech", index, stratum))
        return Instance(split, stratum, index, mid, src.source_group_id, f"rewire:{src.mechanism_id}", net,
                        {"source": src.identity()})
    seed = world_seed(salt, "R5G", index, stratum)
    rules, info = GENERATORS[stratum](random.Random(seed))
    net = Network(N, tuple(r.canonical() for r in rules))
    if not all(r.arity <= K for r in net.rules):
        raise AssertionError("generator left the declared class")
    mid = opaque_id("r5m", world_seed(salt, "R5G-mech", index, stratum))
    return Instance(split, stratum, index, mid, "sg-" + mid[4:], "identity", net, info)


def population(split: str) -> list[Instance]:
    return [make_instance(split, s, i) for s in STRATA for i in range(SPLITS[split]["per_stratum"])]


# --------------------------------------------------------------------------- evidence + queries

@dataclass
class GDesign:
    design_seed: int
    obs_specs: list[tuple[int, Intervention]]
    queries: list[tuple[str, Query]]
    redraws: dict

    def to_json(self) -> dict:
        return {"design_version": DESIGN_VERSION, "design_seed": self.design_seed,
                "obs_specs": [[x, iv.to_json()] for x, iv in self.obs_specs],
                "queries": [[qid, q.to_json()] for qid, q in self.queries], "redraws": self.redraws}


def _eff(x: int, iv: Intervention) -> int:
    m, v = iv.masks
    return (x & ~m) | v if iv.kind != "none" else x


def make_design(salt: str, key: str, n: int = N, max_budget: int | None = None,
                horizons: tuple | None = None) -> GDesign:
    """Evidence (24 nested one-step observations) and 8 queries.  Drawn from a design stream that never touches
    the mechanism; redraws only enforce novelty against the PUBLIC evidence inputs and distinctness.
    R6 Track S: ``max_budget`` (largest nested budget) and ``horizons`` (one per query, e.g. all 1); the defaults
    reproduce the R5 design exactly."""
    seed = world_seed(salt, "R5G-design", 0, key)
    rng = random.Random(seed)
    B = max(BUDGETS) if max_budget is None else max_budget
    states = rng.sample(range(1 << n), B)
    specs = []
    for i, x in enumerate(states):
        if i % 4 == 3:
            nodes = rng.sample(range(n), rng.choice([1, 2]))
            specs.append((x, Intervention("persistent_clamp", tuple((j, rng.randint(0, 1)) for j in nodes))))
        else:
            specs.append((x, Intervention("none")))
    seen_inputs = {_eff(x, iv) for x, iv in specs} | set(states)
    queries: list[tuple[str, Query]] = []
    keys = set()
    redraw = {"novelty": 0, "duplicate": 0}
    hs = [1] * (N_QUERIES // 2) + [2] * (N_QUERIES // 2) if horizons is None else list(horizons)
    while len(queries) < len(hs):
        h = hs[len(queries)]
        x = rng.randrange(1 << n)
        kind = rng.choice(["none", "initial_edit", "persistent_clamp"])
        if kind == "none":
            iv = Intervention("none")
        else:
            nodes = rng.sample(range(n), rng.choice([1, 2]))
            iv = Intervention(kind, tuple((j, rng.randint(0, 1)) for j in nodes))
        clamped = {j for j, _ in iv.assign} if kind == "persistent_clamp" else set()
        t = rng.choice([j for j in range(n) if j not in clamped])
        if _eff(x, iv) in seen_inputs or x in seen_inputs:
            redraw["novelty"] += 1
            continue
        k = (_eff(x, iv), kind, iv.assign if kind == "persistent_clamp" else (), h, t)
        if k in keys:
            redraw["duplicate"] += 1
            continue
        keys.add(k)
        q = Query.point(x, n, iv, h, Pred.lit(t, 1))
        queries.append((f"q{len(queries)}", q))
    return GDesign(seed, specs, queries, redraw)


def make_evidence(net: Network, design: GDesign, budget: int) -> Evidence:
    from .. import reference
    obs = []
    for x, iv in design.obs_specs[:budget]:
        y = reference.run(net, x, iv, 1)[-1]
        clamped = {j for j, _ in iv.assign} if iv.kind == "persistent_clamp" else set()
        obs.append(Observation(x, iv, 1, tuple((j, (y >> j) & 1) for j in range(net.n) if j not in clamped)))
    return Evidence(net.n, tuple(obs), "r5_uniform+clamp")


def outcome(net: Network, q: Query) -> int:
    """Hidden target-node value (the scored 0/1 outcome).  Queries carry literal value 1, so the literal holds iff
    the node is 1; this function returns the NODE VALUE independently of the literal (tested)."""
    from .. import reference
    from ..versionspace import point_query_parts
    tr = reference.run(net, point_query_parts(q, net.n), q.intervention, q.horizon)
    return (tr[-1] >> q.target.node) & 1


def public_payload(inst_key: str, ev: Evidence, design: GDesign, n: int = N, k: int = K) -> dict:
    """What a predictor receives: class, semantics, evidence and query ids/queries.  No mechanism, stratum, seed,
    source or outcome."""
    return {"schema": "r5-g-public-v1", "task_id": content_hash({"key": inst_key, "d": design.design_seed}),
            "n": n, "k": k, "hypothesis_class": {"kind": "bounded_indegree", "n": n, "max_indegree": k},
            "update": "synchronous", "evidence": ev.to_json(), "evidence_hash": ev.digest(),
            "queries": [{"query_id": qid, "query": q.to_json()} for qid, q in design.queries]}


# --------------------------------------------------------------------------- split audits

def split_audit(cal: list[Instance], ev: list[Instance]) -> dict:
    """Mechanism/source-group separation between calibration and evaluation, exact duplicates and isomorphic
    duplicates (bounded exact test).  Any isomorphic cross-split pair is reported (and must be zero)."""
    from ..s4.tasks import _invariant, isomorphic
    canon = lambda net: json.dumps(net.canonical().to_json(), sort_keys=True)  # noqa: E731
    cg = {i.source_group_id for i in cal}
    eg = {i.source_group_id for i in ev}
    out = {"calibration_instances": len(cal), "evaluation_instances": len(ev),
           "calibration_groups": len(cg), "evaluation_groups": len(eg), "shared_groups": len(cg & eg),
           "exact_duplicates_within_eval": 0, "exact_duplicates_cross_split": 0, "isomorphic_cross_split": 0,
           "isomorphic_undecided": 0}
    ce = {canon(i.net) for i in cal}
    seen = set()
    for i in ev:
        c = canon(i.net)
        out["exact_duplicates_within_eval"] += c in seen
        seen.add(c)
        out["exact_duplicates_cross_split"] += c in ce
    inv_cal: dict = {}
    for i in cal:
        inv_cal.setdefault(_invariant(i.net), []).append(i)
    for i in ev:
        for j in inv_cal.get(_invariant(i.net), []):
            r = isomorphic(i.net, j.net, max_perms=50_000)
            if r is None:
                out["isomorphic_undecided"] += 1
            elif r:
                out["isomorphic_cross_split"] += 1
    return out
