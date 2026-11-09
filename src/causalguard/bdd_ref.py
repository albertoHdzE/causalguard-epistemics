"""Independent exact BDD reference backend (dd.autoref), built from DIRECT rules.

DELIBERATE INDEPENDENCE: builds node functions from the local truth tables of
the Network (not from index families) and must not import index_repr, query,
codec or semantics (tests/test_structure.py).  Used (a) as the independent
exact solver that validates UNSAT/universal answers of the index backends and
(b) as the BDD comparator in S1.  Fixed variable order x0 < x1 < ... (declared
budget: a single order); node budget -> unknown_resource.
"""
from __future__ import annotations

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

BACKEND_ID = "bdd_ref"


class BDDBudget(ResourceWarning):
    pass


class BDDModel:
    def __init__(self, net: Network, node_budget: int = 2_000_000):
        from dd import autoref
        self.net = net
        self.budget = node_budget
        self.bdd = autoref.BDD()
        self.vars = [f"x{i}" for i in range(net.n)]
        self.bdd.declare(*self.vars)
        self.fns = [self._rule_bdd(r) for r in net.rules]

    def _check(self):
        if len(self.bdd) > self.budget:
            raise BDDBudget(f"BDD exceeded {self.budget} nodes")

    def _rule_bdd(self, rule):
        b = self.bdd
        k = len(rule.inputs)
        if k > 20:
            raise BDDBudget("local table too large for BDD construction")

        def rec(t: int, table: int):
            # Shannon expansion on input t (local bit t is input rule.inputs[t])
            size = 1 << (k - t)
            full = (1 << size) - 1
            if table == 0:
                return b.false
            if table == full:
                return b.true
            half = size >> 1
            lo = hi = 0
            for y in range(half):
                lo |= ((table >> (2 * y)) & 1) << y
                hi |= ((table >> (2 * y + 1)) & 1) << y
            v = b.var(self.vars[rule.inputs[t]])
            return b.ite(v, rec(t + 1, hi), rec(t + 1, lo))

        return rec(0, rule.table)

    def pred(self, p: Pred):
        b = self.bdd
        if p.op == "lit":
            v = b.var(self.vars[p.node])
            return v if p.value == 1 else ~v
        if p.op == "true":
            return b.true
        if p.op == "false":
            return b.false
        if p.op == "not":
            return ~self.pred(p.args[0])
        parts = [self.pred(a) for a in p.args]
        out = parts[0]
        for z in parts[1:]:
            out = (out & z) if p.op == "and" else (out | z)
        return out

    def answer(self, q: Query) -> ModelResult:
        n = self.net.n
        q.check_against(n)
        h = content_hash(self.net.canonical().to_json())
        cert = lambda lvl, **kw: Certificate("model", lvl, h, None, q.digest(), **kw)  # noqa: E731
        b = self.bdd
        try:
            dom = self.pred(q.domain)
            if dom == b.false:
                return ModelResult(ModelAnswer.INVALID_DOMAIN, cert(VerificationLevel.INDEPENDENT_EXACT,
                                   domain_size=0), BACKEND_ID)
            assign = dict(q.intervention.assign)
            clamp = q.intervention.kind == "persistent_clamp"
            T = self.pred(q.target)
            for _ in range(q.horizon):
                if clamp:
                    T = b.let({self.vars[i]: (b.true if v else b.false) for i, v in assign.items()}, T)
                T = b.let({self.vars[j]: self.fns[j] for j in range(n)}, T)
                self._check()
            if q.intervention.kind != "none":
                T = b.let({self.vars[i]: (b.true if v else b.false) for i, v in assign.items()}, T)
            bad = dom & (T if q.quantifier == "exists" else ~T)
            self._check()
        except BDDBudget as e:
            return ModelResult(ModelAnswer.UNKNOWN_RESOURCE, cert(VerificationLevel.NONE, detail={"reason": str(e)}),
                               BACKEND_ID)
        if bad == b.false:
            ans = ModelAnswer.FALSE if q.quantifier == "exists" else ModelAnswer.TRUE
            return ModelResult(ans, cert(VerificationLevel.INDEPENDENT_EXACT,
                                         detail={"bdd_nodes": len(b)}), BACKEND_ID)
        pick = b.pick(bad, care_vars=self.vars)
        del bad, T, dom
        state = sum(1 << i for i in range(n) if pick.get(self.vars[i], False))
        ans = ModelAnswer.TRUE if q.quantifier == "exists" else ModelAnswer.FALSE
        # The witness is replayed by the caller with causalguard.reference.
        return ModelResult(ans, cert(VerificationLevel.SOLVER_ONLY, witness_state=state,
                                     detail={"bdd_nodes": len(b), "witness_unreplayed": True}), BACKEND_ID)

    def size(self) -> int:
        return len(self.bdd)

    def close(self) -> None:
        """Drop all function references before the manager (dd asserts otherwise)."""
        import gc
        self.fns = []
        gc.collect()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False
