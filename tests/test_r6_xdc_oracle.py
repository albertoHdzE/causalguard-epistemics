"""R6 Track X: independent oracle for the exchangeable dictionary code (XDC).

Written by the implementation agent (not the author of XDC).  It deliberately shares NO code with
``r5/priors.py`` (XDC, GSR, xdc_bruteforce, rule_type, _partition_mass), with ``versionspace`` (candidate class,
version space, simulation) or with ``reference``.  Its only imports from the package are the data types used to
build inputs (Evidence, Observation, Query, Intervention, Pred, Rule) and the BASE code's per-rule bit lengths
(``codec.node_bits`` for 'gate', ``s4.hcode.flat_node_bits`` for 'cgh_flat'), which are inputs of XDC, not part of
the sharing step under audit.

Derivation used here (docs/R6_XDC_DERIVATION.md §3): the prior mass of ONE mechanism m = (r_1..r_n) in closed form,
summing over seatings analytically instead of enumerating them.  With tau_j the order-free type of r_j,
G0(lam) = W(lam)/sum W and s_c the number of nodes of type lam_c,

    P_theta(m) = prod_j w(r_j)/W(tau_j) * prod_c (theta*G0(lam_c))^(s_c rising) / theta^(n rising)

(the Dirichlet-process / Polya-urn marginal: sum over partitions of an s-set of x^{#blocks} prod (|b|-1)! equals the
rising factorial x^(s)).  theta = inf gives prod_j w(r_j)/sum W.  The oracle enumerates every mechanism whose
nodes fit the evidence (own simulator), adds this mass, and conditions.
"""
from __future__ import annotations

import itertools
import math
import random
from functools import lru_cache

import pytest

from causalguard.schema import Evidence, Intervention, Observation, Pred, Query, Rule

INF = math.inf
THETAS = (0.5, 2.0, 8.0, INF)


# --------------------------------------------------------------------------- own rule space and semantics

def _local(ins, s):
    y = 0
    for t, i in enumerate(ins):
        y |= ((s >> i) & 1) << t
    return y


def _essential(ins, table):
    d = len(ins)
    for t in range(d):
        if all(((table >> y) & 1) == ((table >> (y | (1 << t))) & 1) for y in range(1 << d) if not y & (1 << t)):
            return False
    return True


def _orbit(d, table):
    """All tables obtained by permuting the d local inputs (the order-free type is this frozenset)."""
    out = set()
    for perm in itertools.permutations(range(d)):
        t2 = 0
        for y in range(1 << d):
            y2 = 0
            for i in range(d):
                if (y >> i) & 1:
                    y2 |= 1 << perm[i]
            if (table >> y2) & 1:
                t2 |= 1 << y
        out.add(t2)
    return (d, frozenset(out))


def _base_bits(base, ins, table, n, k):
    if base == "gate":
        from causalguard.codec import node_bits
        return node_bits("gate", Rule(ins, table), n)
    if base == "cgh_flat":
        from causalguard.s4.hcode import flat_node_bits
        return flat_node_bits(Rule(ins, table), n, k, "flat")
    raise ValueError(base)


@lru_cache(maxsize=None)
def rule_space(n, k, base):
    """[(ins, table, type, weight)] for every function with <= k essential inputs (one entry per function)."""
    rules = []
    for d in range(k + 1):
        for ins in itertools.combinations(range(n), d):
            for table in range(1 << (1 << d)):
                if _essential(ins, table):
                    rules.append((ins, table, _orbit(d, table), _base_bits(base, ins, table, n, k)))
    mb = min(b for *_, b in rules)
    rules = [(ins, tab, ty, 2.0 ** (mb - b)) for ins, tab, ty, b in rules]
    W = {}
    for _, _, ty, w in rules:
        W[ty] = W.get(ty, 0.0) + w
    return rules, W


def _out(rule, s):
    ins, table = rule[0], rule[1]
    return (table >> _local(ins, s)) & 1


def _start(iv, x):
    if iv.kind == "none":
        return x
    m = v = 0
    for i, b in iv.assign:
        m |= 1 << i
        v |= b << i
    return (x & ~m) | v


def _step(mech, iv, s):
    y = 0
    for j, r in enumerate(mech):
        y |= _out(r, s) << j
    if iv.kind == "persistent_clamp":
        y = _start(iv, y)
    return y


def _fits(rule, j, evidence):
    for o in evidence.observations:
        s = _start(o.intervention, o.state)
        clamped = {i for i, _ in o.intervention.assign} if o.intervention.kind == "persistent_clamp" else set()
        for node, val in o.observed:
            if node == j and node not in clamped and _out(rule, s) != val:
                return False
    return True


def _rising(x, s):
    return math.prod(x + i for i in range(s))


def mechanism_mass(mech, n, W, theta):
    Wsum = sum(W.values())
    p = math.prod(r[3] / W[r[2]] for r in mech)
    if math.isinf(theta):
        return p * math.prod(W[r[2]] / Wsum for r in mech)
    counts = {}
    for r in mech:
        counts[r[2]] = counts.get(r[2], 0) + 1
    return p * math.prod(_rising(theta * W[ty] / Wsum, s) for ty, s in counts.items()) / _rising(theta, n)


def oracle(evidence, k, q, base, thetas=THETAS):
    """{theta: P_theta(q | D)} and the equal-weight mixture, by explicit enumeration of mechanisms."""
    n = evidence.n
    rules, W = rule_space(n, k, base)
    per_node = [[r for r in rules if _fits(r, j, evidence)] for j in range(n)]
    x0 = q.domain_state
    iv, h, t, val = q.intervention, q.horizon, q.target.node, q.target.value
    num = dict.fromkeys(thetas, 0.0)
    den = dict.fromkeys(thetas, 0.0)
    for mech in itertools.product(*per_node):
        s = _start(iv, x0)
        for _ in range(h):
            s = _step(mech, iv, s)
        hit = ((s >> t) & 1) == val
        for th in thetas:
            m = mechanism_mass(mech, n, W, th)
            den[th] += m
            if hit:
                num[th] += m
    out = {th: num[th] / den[th] for th in thetas}
    out["mix"] = sum(num.values()) / sum(den.values())
    return out


def prior_total(n, k, base, theta):
    rules, W = rule_space(n, k, base)
    return math.fsum(mechanism_mass(m, n, W, theta) for m in itertools.product(rules, repeat=n))


# --------------------------------------------------------------------------- random cases (own generator)

IV_KINDS = ("none", "persistent_clamp", "initial_edit")


def _rand_iv(rng, n, kind, avoid=None):
    if kind == "none":
        return Intervention("none")
    nodes = [j for j in range(n) if j != avoid]
    a = rng.sample(nodes, rng.randint(1, min(2, len(nodes))))
    return Intervention(kind, tuple((j, rng.randint(0, 1)) for j in a))


def _point_state(q, n):
    lits = {}

    def walk(p):
        if p.op == "lit":
            lits[p.node] = p.value
        for a in getattr(p, "args", ()) or ():
            walk(a)
    walk(q.domain)
    assert set(lits) == set(range(n))
    return sum(v << i for i, v in lits.items())


# Query is a frozen dataclass in some versions; attach the start state through a light wrapper instead.
class _Q:
    def __init__(self, q, n):
        self.q, self.domain_state = q, _point_state(q, n)
        self.intervention, self.horizon, self.target = q.intervention, q.horizon, q.target


def make_case(rng, n, k, base, i):
    rules, _ = rule_space(n, k, base)
    if rng.random() < 0.5:
        hidden = [rng.choice(rules) for _ in range(n)]
    else:
        ty = rng.choice(rules)[2]
        same = [r for r in rules if r[2] == ty]
        hidden = [rng.choice(same) if rng.random() < 0.75 else rng.choice(rules) for _ in range(n)]
    B = rng.randint(1, 3) if n == 3 else rng.randint(3, 6)
    obs = []
    for b in range(B):
        kind = IV_KINDS[(i + b) % 3] if rng.random() < 0.6 else "none"
        iv = _rand_iv(rng, n, kind)
        x = rng.randrange(1 << n)
        y = _step(hidden, iv, _start(iv, x))
        cl = {j for j, _ in iv.assign} if iv.kind == "persistent_clamp" else set()
        free = [j for j in range(n) if j not in cl]
        seen = [j for j in free if rng.random() < 0.8] or free
        obs.append(Observation(x, iv, 1, tuple((j, (y >> j) & 1) for j in seen)))
    ev = Evidence(n, tuple(obs))
    t = rng.randrange(n)
    q = Query.point(rng.randrange(1 << n), n, _rand_iv(rng, n, IV_KINDS[i % 3], avoid=t), 1 + (i // 3) % 2,
                    Pred.lit(t, rng.randint(0, 1)))
    return ev, q


GRID = [(3, 1), (3, 2), (4, 1), (4, 2)]


def audit_cases(n_cases=216, seed=20261112, bases=("gate", "cgh_flat")):
    """Compare XDC with the oracle on n_cases random (evidence, query) cases; return the summary."""
    from causalguard.r5.priors import XDC
    rng = random.Random(seed)
    worst, rows = 0.0, []
    for i in range(n_cases):
        n, k = GRID[i % len(GRID)]
        base = bases[(i // len(GRID)) % len(bases)]
        ev, q = make_case(rng, n, k, base, i)
        x = XDC(ev, k, base=base)
        if x.vs.empty:
            continue
        pr = x.probabilities(q)                      # P(target node = 1); forecast._node_prob converts for value 0
        if q.target.value == 0:
            pr = {kk: (1.0 - v if isinstance(v, float) else v) for kk, v in pr.items() if kk != "theta_posterior"}
        orc = oracle(ev, k, _Q(q, n), base)
        diffs = {("xdc" if th == "mix" else x_name(th)): abs(pr["xdc" if th == "mix" else x_name(th)] - orc[th])
                 for th in orc}
        d = max(diffs.values())
        worst = max(worst, d)
        rows.append({"n": n, "k": k, "base": base, "h": q.horizon, "iv": q.intervention.kind, "max_abs_diff": d,
                     "sharing_effect": abs(orc[0.5] - orc[INF])})
    return {"cases": len(rows), "max_abs_diff": worst, "rows": rows}


def x_name(th):
    return "xdc_t" + ("inf" if math.isinf(th) else f"{th:g}")


# --------------------------------------------------------------------------- tests

def test_oracle_prior_normalises():
    for base in ("gate", "cgh_flat"):
        for th in THETAS:
            assert abs(prior_total(3, 1, base, th) - 1.0) < 1e-12


def test_xdc_matches_independent_oracle():
    s = audit_cases()
    assert s["cases"] >= 200
    cover = {(r["n"], r["k"], r["h"], r["iv"]) for r in s["rows"]}
    assert {(n, k) for n, k, *_ in cover} == set(GRID)
    assert {iv for *_, iv in cover} == set(IV_KINDS) and {h for _, _, h, _ in cover} == {1, 2}
    assert sum(r["sharing_effect"] > 1e-4 for r in s["rows"]) >= 50      # the cases exercise sharing
    assert s["max_abs_diff"] < 1e-9, s["max_abs_diff"]


def test_planted_defect_is_caught(monkeypatch):
    """Negative control: drop the (|b|-1)! factor in a copy of the subset recursion; the oracle must fail."""
    import numpy as np

    from causalguard.r5 import priors as P

    def broken(G, n, theta):
        if math.isinf(theta):
            return np.prod([G[1 << j] for j in range(n)], axis=0)
        F = np.zeros_like(G)
        F[0] = 1.0
        for A in range(1, 1 << n):
            low = A & -A
            rest = A ^ low
            acc = np.zeros(G.shape[1])
            sub = rest
            while True:
                b = low | sub
                acc += theta * G[b] * F[A ^ b]                   # (|b|-1)! dropped
                if sub == 0:
                    break
                sub = (sub - 1) & rest
            F[A] = acc
        return F[(1 << n) - 1] / math.prod(theta + i for i in range(n))
    monkeypatch.setattr(P, "_partition_mass", broken)
    s = audit_cases(n_cases=24, seed=7)
    assert s["max_abs_diff"] > 1e-4


def _relabel_state(s, perm):
    return sum(((s >> j) & 1) << perm[j] for j in range(len(perm)))


def _relabel_iv(iv, perm):
    return iv if iv.kind == "none" else Intervention(iv.kind, tuple((perm[j], b) for j, b in iv.assign))


@pytest.mark.parametrize("base", ["gate", "cgh_flat"])
def test_relabelling_nodes_leaves_forecasts_unchanged(base):
    """Exchangeability of the full predictor (sharing step AND base code) under node relabelling, 60 cases."""
    from causalguard.r5.priors import XDC
    rng = random.Random(11)
    done = 0
    for i in range(60):
        n, k = GRID[i % 4]
        ev, q = make_case(rng, n, k, base, i)
        perm = list(range(n))
        rng.shuffle(perm)
        ev2 = Evidence(n, tuple(Observation(_relabel_state(o.state, perm), _relabel_iv(o.intervention, perm), 1,
                                            tuple((perm[j], v) for j, v in o.observed)) for o in ev.observations))
        x0 = _point_state(q, n)
        q2 = Query.point(_relabel_state(x0, perm), n, _relabel_iv(q.intervention, perm), q.horizon,
                         Pred.lit(perm[q.target.node], q.target.value))
        a, b = XDC(ev, k, base=base), XDC(ev2, k, base=base)
        if a.vs.empty:
            continue
        pa, pb = a.probabilities(q), b.probabilities(q2)
        for key in ("xdc", "xdc_t0.5", "xdc_t2", "xdc_t8", "xdc_tinf"):
            assert abs(pa[key] - pb[key]) < 1e-9, (base, i, key, pa[key], pb[key])
        done += 1
    assert done >= 50


if __name__ == "__main__":
    import json
    import sys
    s = audit_cases(int(sys.argv[1]) if len(sys.argv) > 1 else 216)
    by = {}
    for r in s["rows"]:
        kk = f"n{r['n']}k{r['k']}"
        by.setdefault(kk, [0, 0.0])
        by[kk][0] += 1
        by[kk][1] = max(by[kk][1], r["max_abs_diff"])
    print(json.dumps({"cases": s["cases"], "max_abs_diff": s["max_abs_diff"], "by_class": by,
                      "by_horizon_iv": sorted({(r["h"], r["iv"]) for r in s["rows"]}),
                      "cases_with_sharing_effect_gt_1e-4": sum(r["sharing_effect"] > 1e-4 for r in s["rows"])},
                     indent=1))
