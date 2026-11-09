"""Deterministic world, evidence and query generators for S1/S2/S3.

Owner of: mechanism families, world seeds/IDs, evidence regimes, hidden query
grids and generator-irregularity records.

* Seeds derive from sha256(split_salt | study | index); IDs are opaque hashes
  of the seed and carry no label information.
* The development salt is public ("dev-v1").  The confirmatory salt is NOT
  chosen here: it is derived from the frozen commit at run time
  (configs/confirmatory.json) so it cannot be tuned on before the freeze.
* Irregularities (degenerate rules, misspecified nodes that turn out realizable,
  holdout shortfalls, query-key collisions) are RECORDED, never silently
  rerolled.  The only redraws are the declared semantic disjointness rules.
"""
from __future__ import annotations

import hashlib
import itertools
import random
from dataclasses import dataclass, field

from . import reference
from .schema import Intervention, Network, Observation, Pred, Query, Rule

DEV_SALT = "dev-v1"

S2_FAMILIES = ("conjunctive", "canalizing", "parity", "random_lookup", "modular")
S1_SMALL_FAMILIES = ("sparse_conj", "canalizing", "parity", "modular", "bounded_random", "dense_random")
S1_LARGE_FAMILIES = ("sparse_conj", "canalizing", "parity", "modular", "bounded_random")


def world_seed(salt: str, study: str, index: int, extra: str = "") -> int:
    h = hashlib.sha256(f"{salt}|{study}|{index}|{extra}".encode()).digest()
    return int.from_bytes(h[:8], "big")


def opaque_id(prefix: str, seed: int) -> str:
    return prefix + "-" + hashlib.sha256(f"id|{seed}".encode()).hexdigest()[:16]


# --------------------------------------------------------------------------- local gate tables

def _tbl(fn, k: int) -> int:
    return sum(1 << y for y in range(1 << k) if fn([(y >> t) & 1 for t in range(k)]))


GATES = {
    "AND": lambda v: all(v), "OR": lambda v: any(v), "NAND": lambda v: not all(v), "NOR": lambda v: not any(v),
    "XOR": lambda v: sum(v) % 2 == 1, "XNOR": lambda v: sum(v) % 2 == 0,
}


def gate_rule(gate: str, inputs: list[int]) -> Rule:
    ins = tuple(sorted(set(inputs)))
    return Rule(ins, _tbl(GATES[gate], len(ins)), label=gate)


def canalizing_rule(rng: random.Random, inputs: list[int]) -> Rule:
    ins = tuple(sorted(set(inputs)))
    order = list(range(len(ins)))
    rng.shuffle(order)
    cvals = [rng.randint(0, 1) for _ in order]
    outs = [rng.randint(0, 1) for _ in order]
    default = 1 - outs[-1]

    def f(v):
        for pos, c, o in zip(order, cvals, outs):
            if v[pos] == c:
                return o
        return default
    return Rule(ins, _tbl(f, len(ins)), label="CANALIZING")


def composed_rule(rng: random.Random, inputs: list[int], allow_not: bool = False) -> Rule:
    """g(h(a,b),c) over 3 inputs (or h(a,b) over 2)."""
    ins = tuple(sorted(set(inputs)))
    k = len(ins)
    perm = list(range(k))
    rng.shuffle(perm)
    g = rng.choice(["AND", "OR", "XOR"])
    h = rng.choice(["AND", "OR", "XOR"])
    nots = [rng.random() < 0.3 if allow_not else False for _ in range(k)]
    ops = {"AND": lambda a, b: a & b, "OR": lambda a, b: a | b, "XOR": lambda a, b: a ^ b}

    def f(v):
        w = [v[perm[i]] ^ int(nots[i]) for i in range(k)]
        if k == 1:
            return w[0]
        inner = ops[h](w[0], w[1])
        return inner if k == 2 else ops[g](inner, w[2])
    return Rule(ins, _tbl(f, k), label=f"COMPOSE({g},{h})")


def random_rule(rng: random.Random, inputs: list[int]) -> Rule:
    ins = tuple(sorted(set(inputs)))
    return Rule(ins, rng.getrandbits(1 << len(ins)), label="LUT")


# --------------------------------------------------------------------------- S2 / S3 worlds

@dataclass
class World:
    world_id: str
    study: str
    family: str
    population: str            # realizable | misspecified | shift
    seed: int
    net: Network
    max_indegree: int          # declared hypothesis class bound k
    irregularities: list[str] = field(default_factory=list)

    def realizable(self) -> bool:
        return all(len(r.canonical().inputs) <= self.max_indegree for r in self.net.rules)

    def to_private_json(self) -> dict:
        return {"world_id": self.world_id, "study": self.study, "family": self.family,
                "population": self.population, "seed": self.seed, "max_indegree": self.max_indegree,
                "network": self.net.to_json(), "irregularities": self.irregularities,
                "realizable": self.realizable()}


def _pick_inputs(rng: random.Random, n: int, d: int, pool: list[int] | None = None) -> list[int]:
    pool = list(range(n)) if pool is None else pool
    return rng.sample(pool, min(d, len(pool)))


def make_family_rule(rng: random.Random, family: str, n: int, j: int, kmax: int) -> Rule:
    d = rng.randint(2, kmax) if kmax >= 2 else 1
    if family == "conjunctive":
        return gate_rule(rng.choice(["AND", "OR", "NAND", "NOR"]), _pick_inputs(rng, n, d))
    if family == "canalizing":
        return canalizing_rule(rng, _pick_inputs(rng, n, d))
    if family == "parity":
        return gate_rule(rng.choice(["XOR", "XNOR"]), _pick_inputs(rng, n, d))
    if family == "random_lookup":
        return random_rule(rng, _pick_inputs(rng, n, kmax))
    if family == "modular":
        # modules of ~3 consecutive nodes; inputs mostly from the own module + one outside input
        size = 3
        mod = [i for i in range(n) if i // size == j // size]
        ins = _pick_inputs(rng, n, min(d - 1, len(mod)), mod)
        outside = [i for i in range(n) if i not in ins]
        if outside and len(ins) < d:
            ins.append(rng.choice(outside))
        return composed_rule(rng, ins)
    raise ValueError(family)


def make_s2_world(salt: str, index: int, family: str, population: str = "realizable", n: int = 7,
                  kmax: int = 3, study: str = "S2") -> World:
    seed = world_seed(salt, study, index, f"{family}|{population}|{n}|{kmax}")
    rng = random.Random(seed)
    irregular = []
    rules = []
    if population == "shift":
        # distribution shift: every node in-degree exactly kmax, composed gates with negations,
        # family mixed per node
        for _j in range(n):
            ins = _pick_inputs(rng, n, kmax)
            rules.append(composed_rule(rng, ins, allow_not=True))
    else:
        for j in range(n):
            rules.append(make_family_rule(rng, family, n, j, kmax))
    if population == "misspecified":
        for j in rng.sample(range(n), 2):
            ins = _pick_inputs(rng, n, kmax + 1)
            kind = rng.choice(["XOR", "THRESH", "LUT"])
            if kind == "XOR":
                rules[j] = gate_rule("XOR", ins)
            elif kind == "THRESH":
                t = rng.choice([2, 3])
                r = Rule(tuple(sorted(ins)), _tbl(lambda v, t=t: sum(v) >= t, len(ins)), label=f"THRESH{t}")
                rules[j] = r
            else:
                rules[j] = random_rule(rng, ins)
    for j, r in enumerate(rules):
        if len(r.canonical().inputs) < len(r.inputs):
            irregular.append(f"node{j}:degenerate_rule({len(r.inputs)}->{len(r.canonical().inputs)})")
    w = World(opaque_id("w", seed), study, family, population, seed, Network(n, tuple(rules)), kmax, irregular)
    if population == "misspecified" and w.realizable():
        w.irregularities.append("misspecified_world_is_actually_realizable")
    return w


# --------------------------------------------------------------------------- S2 evidence + hidden queries

REGIMES = ("uniform_states", "observational", "clamp_interventions")
MAX_BUDGET = 64


def _full_obs(net: Network, x: int, iv: Intervention, skip_clamped: bool) -> Observation:
    fin = reference.run(net, x, iv, 1)[-1]
    clamped = {i for i, _ in iv.assign} if (skip_clamped and iv.kind == "persistent_clamp") else set()
    return Observation(x, iv, 1, tuple((i, (fin >> i) & 1) for i in range(net.n) if i not in clamped))


def trajectory_evidence(net: Network, rng: random.Random, budget: int, clamp: bool, run_len: int = 8
                        ) -> list[Observation]:
    n = net.n
    obs: list[Observation] = []
    while len(obs) < budget:
        x = rng.randrange(1 << n)
        if clamp:
            i = rng.randrange(n)
            iv = Intervention("persistent_clamp", ((i, rng.randint(0, 1)),))
            x = (x & ~(1 << i)) | (iv.assign[0][1] << i)
        else:
            iv = Intervention()
        seen = set()
        for _ in range(run_len):
            if len(obs) >= budget or x in seen:
                break
            seen.add(x)
            o = _full_obs(net, x, iv, skip_clamped=True)
            obs.append(o)
            x = reference.run(net, x, iv, 1)[-1]
    return obs


@dataclass
class S2Instance:
    world: World
    evidence: dict[str, list[Observation]]       # regime -> max-budget sequence (nested prefixes)
    holdout_states: list[int]
    state_queries: list[Query]
    intervention_queries: list[Query]
    irregularities: list[str]


def make_s2_instance(world: World, n_state_queries: int = 8, n_int_queries: int = 16,
                     horizons: tuple[int, ...] = (1, 2, 3)) -> S2Instance:
    net = world.net
    n = net.n
    rng = random.Random(world.seed ^ 0x5EED)
    irr = []
    ev = {}
    ev["observational"] = trajectory_evidence(net, random.Random(rng.getrandbits(64)), MAX_BUDGET, clamp=False)
    ev["clamp_interventions"] = trajectory_evidence(net, random.Random(rng.getrandbits(64)), MAX_BUDGET, clamp=True)
    visited = {o.state for r in ev.values() for o in r}
    unvisited = [x for x in range(1 << n) if x not in visited]
    if len(unvisited) < n_state_queries:
        irr.append(f"holdout_shortfall:{len(unvisited)}<{n_state_queries}")
    holdout = sorted(rng.sample(unvisited, min(n_state_queries, len(unvisited))))
    pool = [x for x in range(1 << n) if x not in holdout]
    rng.shuffle(pool)
    if len(pool) < MAX_BUDGET:
        irr.append("uniform_pool_shortfall")
    ev["uniform_states"] = [_full_obs(net, x, Intervention(), False) for x in pool[:MAX_BUDGET]]
    keys = {o.key() for r in ev.values() for o in r}
    sq = [Query.point(x, n, Intervention(), 1, Pred.lit(rng.randrange(n), 1)) for x in holdout]
    iq: list[Query] = []
    collisions = 0
    kinds = ["initial_edit", "persistent_clamp"]
    while len(iq) < n_int_queries:
        idx = len(iq)
        kind = kinds[idx % 2]
        h = horizons[(idx // 2) % len(horizons)]
        a = rng.randrange(n)
        iv = Intervention(kind, ((a, rng.randint(0, 1)),))
        x = rng.randrange(1 << n)
        b = rng.choice([i for i in range(n) if not (kind == "persistent_clamp" and i == a)])
        key = (x, iv.kind, iv.assign, h)
        if key in keys:
            collisions += 1
            continue   # declared semantic disjointness rule, not a performance-based redraw
        keys.add(key)
        iq.append(Query.point(x, n, iv, h, Pred.lit(b, 1)))
    if collisions:
        irr.append(f"query_key_collisions_redrawn:{collisions}")
    return S2Instance(world, ev, holdout, sq, iq, irr)


# --------------------------------------------------------------------------- S3 tasks (small, LLM-facing)

def make_s3_world(salt: str, index: int, n: int = 4, kmax: int = 2) -> World:
    fam = S2_FAMILIES[index % len(S2_FAMILIES)]
    return make_s2_world(salt, index, fam, "realizable", n=n, kmax=kmax, study="S3")


# --------------------------------------------------------------------------- S1 worlds

def make_s1_world(salt: str, index: int, family: str, n: int) -> World:
    seed = world_seed(salt, "S1", index, f"{family}|{n}")
    rng = random.Random(seed)
    rules = []
    for j in range(n):
        if family == "sparse_conj":
            d = rng.randint(2, min(8, n))
            rules.append(gate_rule(rng.choice(["AND", "OR", "NAND", "NOR"]), _pick_inputs(rng, n, d)))
        elif family == "canalizing":
            d = rng.randint(2, min(6, n))
            rules.append(canalizing_rule(rng, _pick_inputs(rng, n, d)))
        elif family == "parity":
            d = rng.randint(2, min(6, n))
            rules.append(gate_rule(rng.choice(["XOR", "XNOR"]), _pick_inputs(rng, n, d)))
        elif family == "modular":
            size = 4
            mod = [i for i in range(n) if i // size == j // size]
            ins = _pick_inputs(rng, n, min(2, len(mod)), mod)
            outside = [i for i in range(n) if i not in ins]
            if outside:
                ins.append(rng.choice(outside))
            rules.append(composed_rule(rng, ins, allow_not=True))
        elif family == "bounded_random":
            rules.append(random_rule(rng, _pick_inputs(rng, n, min(4, n))))
        elif family == "dense_random":
            if n > 10:
                raise ValueError("dense_random excluded by design above n=10")
            rules.append(random_rule(rng, list(range(n))))
        else:
            raise ValueError(family)
    return World(opaque_id("s1", seed), "S1", family, "realizable", seed, Network(n, tuple(rules)), n)


def s1_queries(world: World, count: int = 24) -> tuple[list[Query], list[str]]:
    """Fixed query grid: membership, exists, forall, finite-horizon reachability h in {1,2,4,8},
    clamp interventions.  Half of exists/forall queries are planted by construction (guaranteed
    SAT / guaranteed counterexample); the other half are free and take their natural outcome.
    Returns (queries, construction tags)."""
    net = world.net
    n = net.n
    rng = random.Random(world.seed ^ 0xA11)
    qs: list[Query] = []
    tags: list[str] = []

    def dom_cube(m: int) -> dict[int, int]:
        return {i: rng.randint(0, 1) for i in rng.sample(range(n), min(m, n))}

    for _ in range(4):  # membership: node output at a single state
        x = rng.getrandbits(n)
        qs.append(Query.point(x, n, Intervention(), 1, Pred.lit(rng.randrange(n), 1)))
        tags.append("membership")
    for h in (1, 2, 4, 8):
        for planted in (True, False):
            cube = dom_cube(max(1, n // 2))
            dom = Pred.cube(cube)
            if planted:
                x = rng.getrandbits(n)
                for i, v in cube.items():
                    x = (x & ~(1 << i)) | (v << i)
                fin = reference.run(net, x, Intervention(), h)[-1]
                lits = {i: (fin >> i) & 1 for i in rng.sample(range(n), min(3, n))}
                qs.append(Query("exists", dom, Intervention(), h, Pred.cube(lits)))
                tags.append(f"exists_planted_h{h}")
                cube2 = dom_cube(max(1, n // 2))
                x2 = rng.getrandbits(n)
                for i, v in cube2.items():
                    x2 = (x2 & ~(1 << i)) | (v << i)
                fin2 = reference.run(net, x2, Intervention(), h)[-1]
                lits2 = {i: (fin2 >> i) & 1 for i in rng.sample(range(n), min(3, n))}
                qs.append(Query("forall", Pred.cube(cube2), Intervention(), h, Pred.not_(Pred.cube(lits2))))
                tags.append(f"forall_planted_counterexample_h{h}")
            else:
                lits = {i: rng.randint(0, 1) for i in rng.sample(range(n), min(3, n))}
                qs.append(Query("exists", dom, Intervention(), h, Pred.cube(lits)))
                tags.append(f"exists_free_h{h}")
                dom2 = Pred.cube(dom_cube(max(1, (3 * n) // 4)))
                tgt = Pred.or_(*[Pred.lit(i, rng.randint(0, 1)) for i in rng.sample(range(n), min(2, n))])
                qs.append(Query("forall", dom2, Intervention(), h, tgt))
                tags.append(f"forall_free_h{h}")
    while len(qs) < count:
        h = rng.choice([2, 4])
        a = rng.randrange(n)
        iv = Intervention("persistent_clamp", ((a, rng.randint(0, 1)),))
        lits = {i: rng.randint(0, 1) for i in rng.sample(range(n), min(2, n))}
        q_ = rng.choice(["exists", "forall"])
        dom = Pred.cube(dom_cube(max(1, n // 2)))
        tgt = Pred.cube(lits) if q_ == "exists" else Pred.or_(*[Pred.lit(i, v) for i, v in lits.items()])
        qs.append(Query(q_, dom, iv, h, tgt))
        tags.append(f"clamp_{q_}_h{h}")
    return qs, tags


__all__ = ["World", "make_s2_world", "make_s2_instance", "make_s3_world", "make_s1_world", "s1_queries",
           "S2_FAMILIES", "S1_SMALL_FAMILIES", "S1_LARGE_FAMILIES", "REGIMES", "DEV_SALT", "world_seed",
           "opaque_id", "itertools"]
