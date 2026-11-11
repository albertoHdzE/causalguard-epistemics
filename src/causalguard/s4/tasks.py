"""S4 world families, exogenous evidence/claim designs, public payloads and leakage audits.

Population.  Eight strata, n = 8 nodes, declared class H = bounded indegree k = 3 (every world is realizable).
Public node order is the declared physical order of the system (part of the public model description, like
the cell order of a ring); node LABELS shown to the AI are opaque per world.  Families:

  sparse_conj      AND/OR/NAND/NOR on 1-3 random inputs per node
  canalizing       nested canalizing rule on 2-3 random inputs (generators.canalizing_rule)
  repeated_modules two blocks of 4 nodes share one module (4 rules, supports relative to the block start)
  ordered_motif    one shared local rule applied to the same cyclic offset pattern at every node (ring motif)
  parity           XOR/XNOR on 2-3 random inputs
  bounded_random   random lookup table on 3 random inputs
  order_disrupted  MATCHED to ordered_motif (same shared rule draw, same arity); each node's support is an
                   independent random subset (sharing without ordered position structure; class preserved)
  uniform_H        null: each node drawn uniformly from the complete class (generator has no simplicity bias)

Design.  A design RNG on a separate stream (salt|S4-design|index) fixes, BEFORE the mechanism is evaluated:
the evidence budget B in {12, 16, 24} (B - B//4 uniform one-step full-state observations + B//4 one-step
persistent-clamp observations of the unclamped nodes), and eight claims: effective start state never observed,
intervention initial_edit or persistent_clamp on 1-2 nodes, horizon in {1, 2, 3}, target node and asserted
value.  Claim values are drawn independently of hidden answers.  Redraws only enforce novelty with respect to
the PUBLIC evidence and semantic distinctness (no duplicates or complements); they are counted.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
from dataclasses import dataclass, field

from ..generators import World, canalizing_rule, gate_rule, opaque_id, random_rule, world_seed
from ..schema import Evidence, Intervention, Network, Observation, Pred, Query, Rule, content_hash
from .hcode import local_catalogue, offset_rule

S4_FAMILIES = ("sparse_conj", "canalizing", "repeated_modules", "ordered_motif", "parity", "bounded_random",
               "order_disrupted", "uniform_H")
S4_N, S4_K = 8, 3
BUDGETS = (12, 16, 24)
N_CLAIMS = 8
DESIGN_VERSION = "s4-design-v1"


def _nondegenerate_table(rng: random.Random, d: int, analytic_only: bool = False) -> int:
    if analytic_only:
        return rng.choice([t for _, t in local_catalogue(d)])
    while True:
        t = rng.getrandbits(1 << d)
        if Rule(tuple(range(d)), t).canonical().arity == d:
            return t


def _motif_draw(salt: str, index: int) -> tuple[int, tuple[int, ...], int]:
    """Shared rule draw used by BOTH ordered_motif and its matched order_disrupted world."""
    rng = random.Random(world_seed(salt, "S4-motif", index))
    d = rng.choice([2, 3, 3])
    offs = tuple(sorted(rng.sample(range(S4_N), d)))
    return d, offs, _nondegenerate_table(rng, d)


def make_s4_world(salt: str, index: int, family: str, n: int = S4_N, k: int = S4_K) -> World:
    if family not in S4_FAMILIES:
        raise ValueError(family)
    seed = world_seed(salt, "S4", index, f"{family}|{n}|{k}")
    rng = random.Random(seed)
    rules: list[Rule] = []
    if family == "sparse_conj":
        for _ in range(n):
            d = rng.choice([1, 2, 2, 3])
            ins = rng.sample(range(n), d)
            rules.append(gate_rule(rng.choice(["AND", "OR", "NAND", "NOR"]), ins) if d > 1 else
                         Rule((ins[0],), rng.choice([0b10, 0b01])))
    elif family == "canalizing":
        rules = [canalizing_rule(rng, rng.sample(range(n), rng.choice([2, 3]))) for _ in range(n)]
    elif family == "parity":
        rules = [gate_rule(rng.choice(["XOR", "XNOR"]), rng.sample(range(n), rng.choice([2, 3]))) for _ in range(n)]
    elif family == "bounded_random":
        rules = [random_rule(rng, rng.sample(range(n), 3)) for _ in range(n)]
    elif family == "repeated_modules":
        m = 4
        module = []
        for p in range(m):
            d = rng.choice([2, 3])
            local = sorted(set([p] + rng.sample([q for q in range(m) if q != p], d - 1)))   # inside the block
            if rng.random() < 0.5:                                                          # one input outside
                local[-1] = rng.choice(range(m, n))
                local = sorted(set(local))
            module.append((tuple(local), _nondegenerate_table(rng, len(local), analytic_only=rng.random() < .5)))
        for b in range(n // m):
            for p in range(m):
                offs, t = module[p]
                rules.append(offset_rule(b * m, offs, t, n))
    elif family in ("ordered_motif", "order_disrupted"):
        d, offs, t = _motif_draw(salt, index)
        if family == "ordered_motif":
            rules = [offset_rule(i, offs, t, n) for i in range(n)]
        else:
            rules = [Rule(tuple(sorted(rng.sample(range(n), d))), t).canonical() for _ in range(n)]
    elif family == "uniform_H":
        from ..versionspace import candidate_class
        cls = candidate_class(n, k)
        rules = [cls.rules[rng.randrange(cls.size)] for _ in range(n)]
    rules = [r.canonical() for r in rules]
    w = World(opaque_id("s4w", seed), "S4", family, "realizable", seed, Network(n, tuple(rules)), k)
    assert w.realizable()
    return w


# --------------------------------------------------------------------------- exogenous design

@dataclass(frozen=True)
class Claim:
    cid: str
    query: Query

    def to_json(self) -> dict:
        return {"cid": self.cid, "query": self.query.to_json()}


@dataclass
class Design:
    design_seed: int
    budget: int
    obs_specs: list[tuple[int, Intervention]]       # (state, intervention) of each one-step observation
    claims: list[Claim]
    redraws: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return {"design_version": DESIGN_VERSION, "design_seed": self.design_seed, "budget": self.budget,
                "obs_specs": [[x, iv.to_json()] for x, iv in self.obs_specs],
                "claims": [c.to_json() for c in self.claims], "redraws": self.redraws}


def s4_design_seed(salt: str, index: int, family: str) -> int:
    return world_seed(salt, "S4-design", index, family)


def _eff(x: int, iv: Intervention) -> int:
    m, v = iv.masks
    return (x & ~m) | v if iv.kind != "none" else x


def make_design(salt: str, index: int, family: str, n: int = S4_N, budget: int | None = None) -> Design:
    rng = random.Random(s4_design_seed(salt, index, family))
    B = budget if budget is not None else rng.choice(BUDGETS)
    nclamp = B // 4
    states = rng.sample(range(1 << n), B)
    specs = []
    for i, x in enumerate(states):
        if i < B - nclamp:
            specs.append((x, Intervention("none")))
        else:
            nodes = rng.sample(range(n), rng.choice([1, 2]))
            specs.append((x, Intervention("persistent_clamp", tuple((j, rng.randint(0, 1)) for j in nodes))))
    observed_inputs = {_eff(x, iv) for x, iv in specs}
    claims: list[Claim] = []
    seen = set()
    redraw = {"novelty": 0, "duplicate_or_complement": 0}
    while len(claims) < N_CLAIMS:
        x = rng.randrange(1 << n)
        kind = rng.choice(["initial_edit", "persistent_clamp"])
        nodes = rng.sample(range(n), rng.choice([1, 2]))
        iv = Intervention(kind, tuple((j, rng.randint(0, 1)) for j in nodes))
        h = rng.choice([1, 2, 3])
        clamped = {j for j, _ in iv.assign} if kind == "persistent_clamp" else set()
        t = rng.choice([j for j in range(n) if j not in clamped])
        c = rng.randint(0, 1)
        if _eff(x, iv) in observed_inputs or x in observed_inputs:
            redraw["novelty"] += 1
            continue
        key = (_eff(x, iv), kind, iv.assign if kind == "persistent_clamp" else (), h, t)
        if key in seen:
            redraw["duplicate_or_complement"] += 1
            continue
        seen.add(key)
        q = Query.point(x, n, iv, h, Pred.lit(t, c))
        claims.append(Claim(f"c{len(claims)}", q))
    return Design(s4_design_seed(salt, index, family), B, specs, claims, redraw)


def make_evidence(world: World, design: Design) -> Evidence:
    from .. import reference
    n = world.net.n
    obs = []
    for x, iv in design.obs_specs:
        y = reference.run(world.net, x, iv, 1)[-1]
        clamped = {j for j, _ in iv.assign} if iv.kind == "persistent_clamp" else set()
        obs.append(Observation(x, iv, 1, tuple((j, (y >> j) & 1) for j in range(n) if j not in clamped)))
    return Evidence(n, tuple(obs), "s4_uniform+clamp")


# --------------------------------------------------------------------------- public payload (what any agent sees)

def node_labels(world_id: str, n: int) -> list[str]:
    """Opaque per-world labels in the declared physical order."""
    h = hashlib.sha256(world_id.encode()).hexdigest()
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    base = [letters[int(h[2 * i:2 * i + 2], 16) % len(letters)] for i in range(n)]
    return [f"{b}{i}" for i, b in enumerate(base)]


def public_task(world: World, design: Design, evidence: Evidence) -> dict:
    """Serialized PUBLIC payload.  Contains no rule, table, family label, seed or answer."""
    n = world.net.n
    return {"schema": "s4-public-task-v1", "task_id": content_hash({"w": world.world_id, "d": design.design_seed}),
            "n": n, "k": world.max_indegree, "node_labels": node_labels(world.world_id, n),
            "hypothesis_class": {"kind": "bounded_indegree", "n": n, "max_indegree": world.max_indegree},
            "update": "synchronous", "ordering": "declared physical order; local tables LSB-first",
            "evidence": evidence.to_json(), "evidence_hash": evidence.digest(),
            "claims": [c.to_json() for c in design.claims]}


FORBIDDEN_PUBLIC_KEYS = ("rules", "table", "network", "family", "seed", "truth", "answer", "verdict", "world_id")


def audit_public_payload(pub: dict) -> list[str]:
    """Leakage audit: forbidden keys anywhere in the payload (recursively)."""
    bad = []

    def walk(x, path):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in FORBIDDEN_PUBLIC_KEYS:
                    bad.append(f"{path}/{k}")
                walk(v, f"{path}/{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{path}[{i}]")
    walk(pub, "")
    return bad


def claim_audit(design: Design, evidence: Evidence) -> dict:
    """Semantic novelty / direct-answer audit of claims against the PUBLIC evidence."""
    seen: dict[int, set[int]] = {}
    for o in evidence.observations:
        seen.setdefault(_eff(o.state, o.intervention), set()).update(j for j, _ in o.observed)
    out = {"direct_answer_h1": 0, "start_state_observed": 0, "duplicates_or_complements": 0}
    keys = set()
    for c in design.claims:
        q = c.query
        from ..versionspace import point_query_parts
        x0 = point_query_parts(q, evidence.n)
        s0 = _eff(x0, q.intervention)
        if q.horizon == 1 and q.target.node in seen.get(s0, set()):
            out["direct_answer_h1"] += 1
        if s0 in seen or x0 in seen:
            out["start_state_observed"] += 1
        key = (s0, q.intervention.kind, q.intervention.assign, q.horizon, q.target.node)
        if key in keys:
            out["duplicates_or_complements"] += 1
        keys.add(key)
    return out


# --------------------------------------------------------------------------- world equivalence (dedup)

def _invariant(net: Network) -> tuple:
    outdeg = [0] * net.n
    for r in net.rules:
        for i in r.inputs:
            outdeg[i] += 1
    sig = []
    for j, r in enumerate(net.rules):
        # rule up to input permutation: sorted multiset of tables under all input permutations -> min
        best = min(_permuted_table(r.table, r.arity, p) for p in itertools.permutations(range(r.arity)))
        sig.append((r.arity, outdeg[j], best, int(j in r.inputs)))
    return tuple(sorted(sig))


def _permuted_table(t: int, d: int, p: tuple[int, ...]) -> int:
    out = 0
    for y in range(1 << d):
        z = sum(((y >> s) & 1) << p[s] for s in range(d))
        out |= ((t >> z) & 1) << y
    return out


def relabel(net: Network, perm: list[int]) -> Network:
    """Network with node i renamed perm[i]."""
    n = net.n
    rules = [None] * n
    for j, r in enumerate(net.rules):
        ins = [perm[i] for i in r.inputs]
        order = sorted(range(len(ins)), key=lambda s: ins[s])
        new_ins = tuple(ins[s] for s in order)
        t = 0
        for y in range(1 << r.arity):
            z = sum(((y >> pos) & 1) << order[pos] for pos in range(r.arity))
            t |= r.local_value(z) << y
        rules[perm[j]] = Rule(new_ins, t)
    return Network(n, tuple(rules))


def isomorphic(a: Network, b: Network, max_perms: int = 50_000) -> bool | None:
    """Exact isomorphism test under node relabeling (invariant pruning, then search); None if over budget."""
    if a.n != b.n or _invariant(a) != _invariant(b):
        return False
    target = json.dumps(b.canonical().to_json(), sort_keys=True)
    for c, perm in enumerate(itertools.permutations(range(a.n))):
        if c >= max_perms:
            return None
        if json.dumps(relabel(a, list(perm)).canonical().to_json(), sort_keys=True) == target:
            return True
    return False
