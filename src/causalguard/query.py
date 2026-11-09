"""Production query engines over the index-family representation.

Backends (each result records ``backend`` and its verification level):

index_enum   exhaustive enumeration of admissible states, stepping with the
             index families (NetworkIndex.step).  Small n.  Level: exhaustive.
index_cube   pure index-family cube algebra: iterated exact preimages of the
             target set through the families (and their complements) for h
             steps, intersected with the domain.  Exact when it finishes;
             complements can blow up -> unknown_resource under a cube budget.
index_sat    HYBRID: index families are translated (Tseitin) to CNF, unrolled
             h steps and decided by a SAT solver.  Representation = index,
             query backend = SAT.  SAT witnesses are replayed by the
             independent reference; UNSAT may be backed by a RUP proof checked
             by causalguard.proofcheck.
literal      literal repertoire: full successor table for all 2**n states,
             built from direct rules (n <= 20).  Exhaustive.

No backend may report a truth value it did not establish: budgets yield
ModelAnswer.UNKNOWN_RESOURCE, never FALSE.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from . import reference
from .index_repr import NetworkIndex
from .schema import (
    Certificate,
    ModelAnswer,
    ModelResult,
    Network,
    Pred,
    Query,
    VerificationLevel,
    content_hash,
)
from .semantics import Cube, apply_assign, cube_and, eval_pred, pred_to_cubes, trajectory


def _cert(net_hash, q: Query, level, **kw) -> Certificate:
    return Certificate("model", level, net_hash, None, q.digest(), **kw)


def _finish_witness(net: Network, q: Query, state: int, backend: str, net_hash: str, extra=None) -> ModelResult:
    """Replay a candidate witness with the independent reference; never trust it blindly."""
    tr = reference.run(net, state, q.intervention, q.horizon)
    ok_dom = reference.holds(q.domain, reference.to_bits(state, net.n))
    hit = reference.holds(q.target, reference.to_bits(tr[-1], net.n))
    good = ok_dom and (hit if q.quantifier == "exists" else not hit)
    if not good:
        raise AssertionError(f"{backend}: witness failed independent replay (engine defect)")
    ans = ModelAnswer.TRUE if q.quantifier == "exists" else ModelAnswer.FALSE
    return ModelResult(ans, _cert(net_hash, q, VerificationLevel.WITNESS_REPLAYED, witness_state=state,
                                  witness_trace=tuple(tr), detail=extra or {}), backend)


# --------------------------------------------------------------------------- index_enum

def index_enum(rep: NetworkIndex, net: Network, q: Query, max_n: int = 22) -> ModelResult:
    n = rep.n
    q.check_against(n)
    h = content_hash(net.canonical().to_json())
    if n > max_n:
        return ModelResult(ModelAnswer.UNKNOWN_RESOURCE, _cert(h, q, VerificationLevel.NONE,
                           detail={"reason": "n too large for enumeration"}), "index_enum")
    admissible = 0
    for x in range(1 << n):
        if not eval_pred(q.domain, x):
            continue
        admissible += 1
        tr = trajectory(rep.step, x, q.intervention, q.horizon)
        ok = eval_pred(q.target, tr[-1])
        if (q.quantifier == "exists") == ok:
            return _finish_witness(net, q, x, "index_enum", h)
    if admissible == 0:
        return ModelResult(ModelAnswer.INVALID_DOMAIN, _cert(h, q, VerificationLevel.EXHAUSTIVE, domain_size=0),
                           "index_enum")
    ans = ModelAnswer.FALSE if q.quantifier == "exists" else ModelAnswer.TRUE
    return ModelResult(ans, _cert(h, q, VerificationLevel.EXHAUSTIVE, domain_size=admissible), "index_enum")


# --------------------------------------------------------------------------- index_cube

class CubeBudget(ResourceWarning):
    pass


def _absorb(cubes: list[Cube]) -> list[Cube]:
    cubes = sorted(set(cubes), key=lambda c: bin(c[0]).count("1"))
    out: list[Cube] = []
    for m, v in cubes:
        if any((m & om) == om and (v & om) == ov for om, ov in out):
            continue
        out.append((m, v))
    return out


def _intersect(a: list[Cube], b: list[Cube], budget: int) -> list[Cube]:
    out = []
    for c in a:
        for d in b:
            e = cube_and(c, d)
            if e is not None:
                out.append(e)
                if len(out) > budget:
                    raise CubeBudget("cube intersection budget exceeded")
    return _absorb(out)


def _complement(cubes: list[Cube], n: int, budget: int) -> list[Cube]:
    res: list[Cube] = [(0, 0)]
    for m, v in cubes:
        comp_c = []
        prefM = prefV = 0
        mm = m
        while mm:
            low = mm & -mm
            comp_c.append((prefM | low, prefV | ((v & low) ^ low)))
            prefM |= low
            prefV |= v & low
            mm ^= low
        res = _intersect(res, comp_c, budget)
        if not res:
            return []
    return res


@dataclass
class _CubeNet:
    rep: NetworkIndex
    budget: int

    def __post_init__(self):
        self._on: dict[int, list[Cube]] = {}
        self._off: dict[int, list[Cube]] = {}

    def value_set(self, j: int, val: int) -> list[Cube]:
        nd = self.rep.nodes[j]
        covered = [(f.fixed, f.anchor) for f in nd.families]
        if val == nd.polarity:
            return covered
        if j not in self._off:
            self._off[j] = _complement(covered, self.rep.n, self.budget)
        return self._off[j]


def _pre_assign(cubes: list[Cube], assign_mask: int, assign_val: int) -> list[Cube]:
    out = []
    for m, v in cubes:
        if (v ^ assign_val) & m & assign_mask:
            continue
        out.append((m & ~assign_mask, v & ~assign_mask))
    return _absorb(out)


def _preimage(cn: _CubeNet, cubes: list[Cube], clamp_mask: int, clamp_val: int) -> list[Cube]:
    res: list[Cube] = []
    for m, v in cubes:
        cond: list[Cube] = [(0, 0)]
        mm = m
        dead = False
        while mm:
            low = mm & -mm
            j = low.bit_length() - 1
            want = (v >> j) & 1
            mm ^= low
            if clamp_mask & low:
                if ((clamp_val >> j) & 1) != want:
                    dead = True
                    break
                continue
            cond = _intersect(cond, cn.value_set(j, want), cn.budget)
            if not cond:
                dead = True
                break
        if not dead:
            res.extend(cond)
            if len(res) > cn.budget:
                raise CubeBudget("preimage budget exceeded")
    return _absorb(res)


def index_cube(rep: NetworkIndex, net: Network, q: Query, budget: int = 20000) -> ModelResult:
    n = rep.n
    q.check_against(n)
    h = content_hash(net.canonical().to_json())
    try:
        dom = pred_to_cubes(q.domain, budget)
        if not dom:
            return ModelResult(ModelAnswer.INVALID_DOMAIN, _cert(h, q, VerificationLevel.NONE,
                               detail={"method": "symbolic_complete"}), "index_cube")
        tgt = q.target if q.quantifier == "exists" else Pred.not_(q.target)
        cur = pred_to_cubes(tgt, budget)
        am, av = q.intervention.masks
        clamp = q.intervention.kind == "persistent_clamp"
        cn = _CubeNet(rep, budget)
        for _ in range(q.horizon):
            if clamp:
                cur = _pre_assign(cur, am, av)  # post-update clamp: fixed bits checked here
                cur = _preimage(cn, cur, 0, 0)
            else:
                cur = _preimage(cn, cur, 0, 0)
            if not cur:
                break
        if q.intervention.kind != "none":
            cur = _pre_assign(cur, am, av)
        hit = _intersect(dom, cur, budget)
    except (CubeBudget, ResourceWarning) as e:
        return ModelResult(ModelAnswer.UNKNOWN_RESOURCE, _cert(h, q, VerificationLevel.NONE,
                           detail={"reason": str(e)}), "index_cube")
    if hit:
        m, v = hit[0]
        return _finish_witness(net, q, v, "index_cube", h, {"final_cubes": len(hit)})
    ans = ModelAnswer.FALSE if q.quantifier == "exists" else ModelAnswer.TRUE
    return ModelResult(ans, _cert(h, q, VerificationLevel.SOLVER_ONLY,
                                  detail={"method": "symbolic_complete_cube_algebra"}), "index_cube")


# --------------------------------------------------------------------------- index_sat (hybrid)

class _CNF:
    def __init__(self):
        self.nv = 0
        self.clauses: list[list[int]] = []

    def var(self) -> int:
        self.nv += 1
        return self.nv

    def add(self, c):
        self.clauses.append(list(c))

    def and_gate(self, lits: list[int]) -> int:
        if not lits:
            return self.const(True)
        if len(lits) == 1:
            return lits[0]
        g = self.var()
        for l in lits:
            self.add([-g, l])
        self.add([g] + [-l for l in lits])
        return g

    def or_gate(self, lits: list[int]) -> int:
        if not lits:
            return self.const(False)
        if len(lits) == 1:
            return lits[0]
        g = self.var()
        for l in lits:
            self.add([g, -l])
        self.add([-g] + list(lits))
        return g

    _true = None

    def const(self, val: bool) -> int:
        if self._true is None:
            self._true = self.var()
            self.add([self._true])
        return self._true if val else -self._true


def _tseitin_pred(cnf: _CNF, p: Pred, xs: list[int]) -> int:
    if p.op == "lit":
        return xs[p.node] if p.value == 1 else -xs[p.node]
    if p.op == "true":
        return cnf.const(True)
    if p.op == "false":
        return cnf.const(False)
    if p.op == "not":
        return -_tseitin_pred(cnf, p.args[0], xs)
    sub = [_tseitin_pred(cnf, a, xs) for a in p.args]
    return cnf.and_gate(sub) if p.op == "and" else cnf.or_gate(sub)


def build_index_cnf(rep: NetworkIndex, q: Query, negate_target: bool) -> tuple[_CNF, list[int], int, int]:
    """CNF over the unrolled index-family dynamics.  Returns (cnf, s_vars, dom_lit, tgt_lit)."""
    n = rep.n
    cnf = _CNF()
    s = [cnf.var() for _ in range(n)]
    am, av = q.intervention.masks
    x = []
    for i in range(n):
        if (am >> i) & 1:
            x.append(cnf.const(bool((av >> i) & 1)))
        else:
            x.append(s[i])
    clamp = q.intervention.kind == "persistent_clamp"
    for _ in range(q.horizon):
        nxt = []
        for j, nd in enumerate(rep.nodes):
            if clamp and (am >> j) & 1:
                nxt.append(cnf.const(bool((av >> j) & 1)))
                continue
            fam_lits = []
            for f in nd.families:
                lits = []
                mm = f.fixed
                while mm:
                    low = mm & -mm
                    i = low.bit_length() - 1
                    lits.append(x[i] if (f.anchor >> i) & 1 else -x[i])
                    mm ^= low
                fam_lits.append(cnf.and_gate(lits))
            u = cnf.or_gate(fam_lits)
            nxt.append(u if nd.polarity == 1 else -u)
        x = nxt
    dom = _tseitin_pred(cnf, q.domain, s)
    tgt = _tseitin_pred(cnf, q.target, x)
    return cnf, s, dom, (-tgt if negate_target else tgt)


def index_sat(rep: NetworkIndex, net: Network, q: Query, solver: str = "cadical153",
              check_proof: bool = False, proof_budget: int = 2_000_000) -> ModelResult:
    from pysat.solvers import Solver

    n = rep.n
    q.check_against(n)
    h = content_hash(net.canonical().to_json())
    cnf, s, dom, tgt = build_index_cnf(rep, q, negate_target=(q.quantifier == "forall"))
    with Solver(name=solver, bootstrap_with=cnf.clauses + [[dom]]) as sv:
        if not sv.solve():
            return ModelResult(ModelAnswer.INVALID_DOMAIN, _cert(h, q, VerificationLevel.SOLVER_ONLY,
                               detail={"solver": solver}), "index_sat")
    clauses = cnf.clauses + [[dom], [tgt]]
    use = "glucose4" if check_proof else solver
    with Solver(name=use, bootstrap_with=clauses, with_proof=check_proof) as sv:
        sat = sv.solve()
        model = sv.get_model() if sat else None
        proof = sv.get_proof() if (check_proof and not sat) else None
    if sat:
        mset = set(l for l in model if l > 0)
        state = sum(1 << i for i in range(n) if s[i] in mset)
        return _finish_witness(net, q, state, "index_sat", h, {"solver": use, "vars": cnf.nv,
                                                               "clauses": len(clauses)})
    ans = ModelAnswer.FALSE if q.quantifier == "exists" else ModelAnswer.TRUE
    level = VerificationLevel.SOLVER_ONLY
    detail = {"solver": use, "vars": cnf.nv, "clauses": len(clauses)}
    if proof is not None:
        from .proofcheck import check_rup_refutation
        ok, info = check_rup_refutation(clauses, proof, budget=proof_budget)
        detail["proof"] = info
        if ok:
            level = VerificationLevel.CHECKED_PROOF
    return ModelResult(ans, _cert(h, q, level, detail=detail), "index_sat")


# --------------------------------------------------------------------------- literal repertoire

def literal_successors(net: Network):
    """Full successor table (numpy, length 2**n) from DIRECT rules; n <= 20."""
    import numpy as np
    n = net.n
    if n > 20:
        raise ResourceWarning("literal repertoire refused for n > 20")
    xs = np.arange(1 << n, dtype=np.int64)
    succ = np.zeros(1 << n, dtype=np.int64)
    for j, r in enumerate(net.rules):
        y = np.zeros(1 << n, dtype=np.int64)
        for t, i in enumerate(r.inputs):
            y |= ((xs >> i) & 1) << t
        tab = np.array([(r.table >> k) & 1 for k in range(1 << r.arity)], dtype=np.int64)
        succ |= tab[y] << j
    return succ


def _eval_pred_vec(p: Pred, xs):
    import numpy as np
    if p.op == "lit":
        return ((xs >> p.node) & 1) == p.value
    if p.op == "true":
        return np.ones(len(xs), bool)
    if p.op == "false":
        return np.zeros(len(xs), bool)
    if p.op == "not":
        return ~_eval_pred_vec(p.args[0], xs)
    parts = [_eval_pred_vec(a, xs) for a in p.args]
    out = parts[0]
    for z in parts[1:]:
        out = (out & z) if p.op == "and" else (out | z)
    return out


def literal_query(succ, net: Network, q: Query) -> ModelResult:
    import numpy as np
    n = net.n
    h = content_hash(net.canonical().to_json())
    xs = np.arange(1 << n, dtype=np.int64)
    dom = _eval_pred_vec(q.domain, xs)
    if not dom.any():
        return ModelResult(ModelAnswer.INVALID_DOMAIN, _cert(h, q, VerificationLevel.EXHAUSTIVE, domain_size=0),
                           "literal")
    am, av = q.intervention.masks
    st = xs[dom]
    if q.intervention.kind != "none":
        st = (st & ~am) | av
    for _ in range(q.horizon):
        st = succ[st]
        if q.intervention.kind == "persistent_clamp":
            st = (st & ~am) | av
    ok = _eval_pred_vec(q.target, st)
    starts = xs[dom]
    if q.quantifier == "exists" and ok.any():
        return _finish_witness(net, q, int(starts[np.argmax(ok)]), "literal", h)
    if q.quantifier == "forall" and not ok.all():
        return _finish_witness(net, q, int(starts[np.argmin(ok)]), "literal", h)
    ans = ModelAnswer.FALSE if q.quantifier == "exists" else ModelAnswer.TRUE
    return ModelResult(ans, _cert(h, q, VerificationLevel.EXHAUSTIVE, domain_size=int(dom.sum())), "literal")


def timed(fn, *a, **kw):
    t0 = time.perf_counter()
    r = fn(*a, **kw)
    return r, time.perf_counter() - t0


__all__ = ["index_enum", "index_cube", "index_sat", "literal_successors", "literal_query",
           "build_index_cnf", "timed", "apply_assign"]
