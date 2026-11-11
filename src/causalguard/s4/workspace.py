"""One semantic API over three symbolic backends (S4 arms B, C, D).

Every backend receives the same PUBLIC task (s4/tasks.public_task), supports the same operations and returns the
same response schema:

  status()                      consistency, exact distinct-mechanism count per node (or resource refusal)
  check(claim)                  epistemic verdict of the claim over ALL of V(D): entailed / refuted /
                                underdetermined / inconsistent / unsupported_or_resource, exact counts, opposing
                                witnesses (explicit networks, independently replayed), cost
  witness(claim, holds)         an explicit compatible mechanism with the claim true (holds=1) or false (0)
  measurement_values(claim, menu)  exact expected information about the claim per permitted measurement
  update(observations)          new workspace with added public observations

Backends differ ONLY in representation/algorithm, never in information:
  B generic   complete CNF encoding of H restricted by D + SAT (versionspace.verdict, the existing generic
              solver owner) for verdicts/witnesses; counts by explicit enumeration over the materialized candidate
              class (versionspace.exact_query_counts).  Renders witnesses as explicit truth tables.
  C flat      the sprint's flat index workspace: materialized candidate class, per-node compatible sets as unions
              of flat schema families (index_repr), counts by the same explicit engine; renders flat schemas.
  D index     support-schema mechanism space (s4.mechspace; no materialization) with analytic index-set
              vocabulary and CGH-1 descriptions (s4.hcode); renders named analytic rules.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass

from .. import reference
from ..schema import Evidence, HypothesisClass, Network, Observation, Query, SemanticsError, content_hash
from .mechspace import MechanismSpace, ResourceLimit, UnsupportedClaim

ARMS = ("B", "C", "D")
EXPLICIT_MAX_N = 10           # materialized candidate class (2^n-column tables) refused above this


@dataclass(frozen=True)
class Limits:
    max_enum: int = 1 << 14
    explicit_max_n: int = EXPLICIT_MAX_N
    proof_check: bool = False


def verdict_of(num: int, den: int) -> str:
    return "refuted" if num == 0 else "entailed" if num == den else "underdetermined"


def _labels(pub: dict) -> list[str]:
    return pub["node_labels"]


def render_table(net: Network, labels: list[str]) -> list[str]:
    out = []
    for j, r in enumerate(net.rules):
        ins = ",".join(labels[i] for i in r.inputs) or "-"
        bits = "".join(str(r.local_value(y)) for y in range(1 << r.arity))
        out.append(f"{labels[j]} := table[{ins}] = {bits}")
    return out


def render_flat(net: Network, labels: list[str]) -> list[str]:
    from ..index_repr import from_rule
    out = []
    for j, r in enumerate(net.rules):
        node = from_rule(r, net.n)
        pos = r.inputs
        fams = " | ".join(f.schema_string(pos) for f in node.families) or "(none)"
        ins = ",".join(labels[i] for i in pos) or "-"
        out.append(f"{labels[j]} = {node.polarity} iff ({ins}) matches {fams}")
    return out


def render_analytic(net: Network, labels: list[str], k: int) -> list[str]:
    from .hcode import describe, local_catalogue
    out = []
    for j, r in enumerate(net.rules):
        names = dict((t, nm) for nm, t in local_catalogue(r.arity))
        nm = names.get(r.table, "LUT" + "".join(str(r.local_value(y)) for y in range(1 << r.arity)))
        out.append(f"{labels[j]} = {nm}({','.join(labels[i] for i in r.inputs)})")
    b, mode, plan = describe(net, k, "full")
    out.append(f"[CGH-1 description: {b} bits, mode {['flat', 'shared-dictionary', 'ordered-template', 'module'][mode]}]")
    return out


class Workspace:
    arm = "?"

    def __init__(self, pub: dict, limits: Limits | None = None, evidence: Evidence | None = None):
        self.pub = pub
        self.limits = limits or Limits()
        self.n, self.k = pub["n"], pub["k"]
        self.evidence = evidence if evidence is not None else Evidence.from_json(pub["evidence"])
        self.labels = _labels(pub)
        self.hclass = HypothesisClass(self.n, self.k)
        self.cost = {"wall_s": 0.0, "ops": 0}
        t0 = time.perf_counter()
        self._build()
        self.cost["build_s"] = time.perf_counter() - t0

    # identity of the assumptions every result is bound to
    def identity(self) -> dict:
        return {"hypothesis_class": self.hclass.to_json(), "evidence_hash": self.evidence.digest(),
                "update": "synchronous", "ordering": "declared physical order; LSB-first local tables",
                "evidence_semantics": "one-step observations", "backend": self.arm,
                "backend_version": "s4-workspace-v1"}

    def identity_hash(self) -> str:
        return content_hash(self.identity())

    def update(self, obs: list[Observation]) -> "Workspace":
        ev = Evidence(self.n, tuple(self.evidence.observations) + tuple(obs), self.evidence.regime)
        return type(self)(self.pub, self.limits, ev)

    # ---- API
    def check(self, claim: dict) -> dict:
        q = Query.from_json(claim["query"])
        t0 = time.perf_counter()
        out = {"cid": claim.get("cid"), "backend": self.arm, "identity": self.identity_hash(),
               "claim_digest": q.digest()}
        try:
            if self._empty():
                out.update(verdict="inconsistent", counts=None, witnesses={})
            else:
                num, den, wit, extra = self._check(q)
                out.update(verdict=verdict_of(num, den) if num is not None else extra.pop("verdict"),
                           counts=None if num is None else {"num": str(num), "den": str(den)},
                           witnesses={str(h): w for h, w in wit.items()}, **extra)
                for h, net in self._last_witness_nets.items():      # independent replay of every witness
                    if not reference.consistent(net, self.evidence) or \
                            bool(_predict(net, q)) != bool(h):
                        raise AssertionError(f"{self.arm} witness failed independent replay")
        except (ResourceLimit, MemoryError) as e:
            out.update(verdict="unsupported_or_resource", counts=None, witnesses={}, reason=str(e)[:300])
        except (UnsupportedClaim, SemanticsError) as e:
            out.update(verdict="unsupported_or_resource", counts=None, witnesses={}, reason=str(e)[:300])
        dt = time.perf_counter() - t0
        self.cost["wall_s"] += dt
        self.cost["ops"] += 1
        out["wall_s"] = dt
        return out

    def witness_networks(self) -> dict[int, Network]:
        return dict(self._last_witness_nets)

    def measurement_values(self, claim: dict, menu: list[dict]) -> list[dict]:
        """Exact expected information gain (bits) about the claim's target for each one-node measurement."""
        q = Query.from_json(claim["query"])
        base = self._counts(q)
        res = []
        for item in menu:
            from ..schema import Intervention
            iv = Intervention.from_json(item["intervention"])
            per = {}
            for b in (0, 1):
                ws = self.update([Observation(int(item["state"]), iv, 1, ((int(item["node"]), b),))])
                if ws._empty():
                    per[b] = (0, 0)
                    continue
                per[b] = ws._counts(q)
            V = sum(per[b][1] for b in (0, 1))
            eig = None
            if V and base is not None:
                H0 = _h(base[0] / base[1])
                eig = H0 - sum(per[b][1] / V * (_h(per[b][0] / per[b][1]) if per[b][1] else 0) for b in (0, 1))
            res.append({"item": item, "outcome_sizes": {str(b): str(per[b][1]) for b in (0, 1)},
                        "eig_bits": eig})
        return res

    # ---- backend hooks
    def _build(self): raise NotImplementedError
    def _empty(self) -> bool: raise NotImplementedError
    def _counts(self, q: Query): raise NotImplementedError
    def _check(self, q: Query): raise NotImplementedError
    def status(self) -> dict: raise NotImplementedError


def _h(p: float) -> float:
    return 0.0 if p in (0.0, 1.0) else -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


def _predict(net: Network, q: Query) -> bool:
    from ..versionspace import predict
    return predict(net, q)


class ExplicitBase(Workspace):
    """Shared by B and C: the materialized candidate class (generic explicit enumeration)."""

    def _build(self):
        from ..versionspace import build_version_space
        if self.n > self.limits.explicit_max_n:
            self.vs = None
            return
        self.vs = build_version_space(self.evidence, self.hclass)

    def _empty(self):
        if self.vs is None:
            if self.arm != "B":
                raise ResourceLimit(f"explicit candidate class refused at n={self.n}")
            return not _sat_feasible(self.evidence, self.hclass)
        return self.vs.empty

    def _counts(self, q):
        from ..versionspace import exact_query_counts
        if self.vs is None:
            raise ResourceLimit(f"explicit candidate class refused at n={self.n} > {self.limits.explicit_max_n}")
        return exact_query_counts(self.vs, q)

    def status(self) -> dict:
        if self.vs is None:
            return {"backend": self.arm, "consistent": None, "per_node_compatible": None,
                    "note": "materialization refused (resource limit)"}
        return {"backend": self.arm, "consistent": not self.vs.empty,
                "per_node_compatible": {self.labels[j]: c for j, c in enumerate(self.vs.counts())},
                "total_compatible_mechanisms": str(self.vs.product_size()) if not self.vs.empty else "0"}


class GenericWorkspace(ExplicitBase):
    """Arm B: SAT verdicts/witnesses over the complete CNF encoding; explicit counts when feasible."""
    arm = "B"

    def _check(self, q):
        from ..versionspace import verdict
        self._last_witness_nets = {}
        vs = self.vs if self.vs is not None else _sat_only_space(self.evidence, self.hclass)
        vr = verdict(vs, q, check_proof=self.limits.proof_check)
        wm = vr.certificate.witness_models
        nets = [Network.from_json(m) for m in wm]
        v = vr.verdict.value
        if v == "underdetermined":
            self._last_witness_nets = {1: nets[0], 0: nets[1]}
        elif v == "entailed":
            self._last_witness_nets = {1: nets[0]}
        elif v == "refuted":
            self._last_witness_nets = {0: nets[0]}
        wit = {h: render_table(n, self.labels) for h, n in self._last_witness_nets.items()}
        extra = {"certificate": {"level": vr.certificate.level.value, "solver": vr.certificate.detail.get("solver"),
                                 "cnf_vars": vr.certificate.detail.get("vars"),
                                 "cnf_clauses": vr.certificate.detail.get("clauses")}}
        try:
            num, den = self._counts(q)
            if verdict_of(num, den) != v:
                raise AssertionError("B: SAT verdict disagrees with explicit counts")
        except ResourceLimit as e:
            num = den = None
            extra["verdict"] = v
            extra["counts_note"] = str(e)
        return num, den, wit, extra


def _sat_feasible(evidence, hclass) -> bool:
    """Consistency of (H, D) decided by B's own CNF encoding (no candidate class, no arm-D code)."""
    import numpy as np
    from pysat.solvers import Solver

    from ..versionspace import CandidateClass, VersionSpace, _Enc
    shell = VersionSpace(CandidateClass(hclass.n, hclass.max_indegree, [], np.zeros((0, 0), dtype=np.uint8), {},
                                        np.zeros(0, dtype=np.int64)), evidence, [np.zeros(1, dtype=np.int64)] * hclass.n)
    enc = _Enc(shell)
    if not enc.feasible:
        return False
    with Solver(name="cadical153", bootstrap_with=enc.cnf.clauses) as sv:
        return bool(sv.solve())


def _sat_only_space(evidence, hclass):
    """VersionSpace shell for the SAT path when the candidate class is not materialized (n large).  The SAT
    verdict needs only evidence, n, k and emptiness; per-node counts are NOT available on this path (the
    sentinel arrays carry no count and B reports counts as a resource refusal)."""
    import numpy as np

    from ..versionspace import CandidateClass, VersionSpace
    cls = CandidateClass(hclass.n, hclass.max_indegree, [], np.zeros((0, 0), dtype=np.uint8), {},
                         np.zeros(0, dtype=np.int64))
    size = 1 if _sat_feasible(evidence, hclass) else 0
    return VersionSpace(cls, evidence, [np.zeros(size, dtype=np.int64)] * hclass.n)


class FlatIndexWorkspace(ExplicitBase):
    """Arm C: explicit candidate enumeration labelled by flat index schema families."""
    arm = "C"

    def _check(self, q):
        num, den = self._counts(q)
        self._last_witness_nets = {}
        for h in (1, 0):
            net = self._explicit_witness(q, h)
            if net is not None:
                self._last_witness_nets[h] = net
        wit = {h: render_flat(n, self.labels) for h, n in self._last_witness_nets.items()}
        return num, den, wit, {"certificate": {"level": "exhaustive_explicit_count"}}

    def _explicit_witness(self, q, h):
        """Shortest-flat-index compatible model satisfying the side, by constrained explicit search: add the
        side as a requirement on the explicit sets via the exact engine (prefix fixing per node)."""
        import numpy as np

        from ..schema import Pred
        from ..versionspace import VersionSpace, exact_query_counts, network_from_choice
        tq = Query(q.quantifier, q.domain, q.intervention, q.horizon,
                   q.target if h else Pred.lit(q.target.node, 1 - q.target.value))
        comp = [c.copy() for c in self.vs.compatible]
        num, _ = exact_query_counts(VersionSpace(self.vs.cls, self.evidence, comp), tq)
        if num == 0:
            return None
        bits = self.vs.cls.bits["index"]
        for j in range(self.n):                       # fix nodes one by one, cheapest flat code first
            order = comp[j][np.argsort(bits[comp[j]], kind="stable")]
            for c in order:
                trial = comp[:j] + [np.array([c])] + comp[j + 1:]
                if exact_query_counts(VersionSpace(self.vs.cls, self.evidence, trial), tq)[0] > 0:
                    comp = trial
                    break
        return network_from_choice(self.vs.cls, [int(c[0]) for c in comp])


class IndexSetWorkspace(Workspace):
    """Arm D: support-schema mechanism space + analytic vocabulary + CGH-1 descriptions."""
    arm = "D"

    def _build(self):
        self.ms = MechanismSpace(self.evidence, self.k, self.limits.max_enum)

    def _empty(self):
        return self.ms.empty

    def _counts(self, q):
        cc = self.ms.claim_counts(q)
        return cc.num, cc.den

    def _check(self, q):
        cc = self.ms.claim_counts(q)
        self._last_witness_nets = {}
        for h in (1, 0):
            if (h and cc.num > 0) or (not h and cc.num < cc.den):
                self._last_witness_nets[h] = self.ms.witness(q, h)
        wit = {h: render_analytic(n, self.labels, self.k) for h, n in self._last_witness_nets.items()}
        return cc.num, cc.den, wit, {"certificate": {"level": "exhaustive_symbolic_count", "path": cc.path,
                                                     "meter": cc.meter}}

    def status(self) -> dict:
        return {"backend": "D", "consistent": not self.ms.empty,
                "per_node_compatible": {self.labels[j]: c for j, c in enumerate(self.ms.counts())},
                "total_compatible_mechanisms": str(self.ms.size()),
                "analytic_summary": [{**s, "node": self.labels[s["node"]]} for s in self.ms.analytic_summary()]}


BACKENDS = {"B": GenericWorkspace, "C": FlatIndexWorkspace, "D": IndexSetWorkspace}


def make_workspace(arm: str, pub: dict, limits: Limits | None = None) -> Workspace:
    return BACKENDS[arm](pub, limits)
