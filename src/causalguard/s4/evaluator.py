"""S4 reference evaluator: the ONLY holder of hidden mechanisms (capability separation).

Agents and workspaces receive ``public_task`` payloads (serialized JSON) and never this object.  The evaluator:
  * builds worlds/designs/evidence from (salt, index, family);
  * computes reference epistemic verdicts with the explicit exact engine and requires agreement of the
    independent D engine and the complete SAT encoding (any mismatch is a gate failure, never averaged);
  * reveals hidden target values only for scoring, after answers are fixed;
  * executes simulated actions on the hidden mechanism (postcondition checks).
"""
from __future__ import annotations

from dataclasses import dataclass

from .. import reference
from ..schema import HypothesisClass, Query
from ..versionspace import build_version_space, exact_query_counts, predict, verdict
from .mechspace import MechanismSpace
from .tasks import Design, make_design, make_evidence, make_s4_world, public_task
from .workspace import verdict_of


@dataclass
class ReferenceClaim:
    cid: str
    verdict: str
    num: int
    den: int
    truth_holds: int          # 1 if the claim's literal holds in the hidden mechanism
    h: int
    kind: str


class Evaluator:
    def __init__(self, salt: str, index: int, family: str, budget: int | None = None):
        self.salt, self.index, self.family = salt, index, family
        self.world = make_s4_world(salt, index, family)
        self.design: Design = make_design(salt, index, family, budget=budget)
        self.evidence = make_evidence(self.world, self.design)
        self._pub = public_task(self.world, self.design, self.evidence)

    @classmethod
    def from_world(cls, world, design: Design) -> "Evaluator":
        """An evaluator over a prebuilt world and design (R7 sprint: R5 G mechanisms and published fragments with
        the S4 evidence/claim design).  Same reference, truth and audit code as the (salt, index, family) path."""
        self = cls.__new__(cls)
        self.salt, self.index, self.family = None, None, world.family
        self.world, self.design = world, design
        self.evidence = make_evidence(world, design)
        self._pub = public_task(world, design, self.evidence)
        return self

    def public(self) -> dict:
        import json
        return json.loads(json.dumps(self._pub))          # a serialized copy: no shared objects

    def reference(self, crosscheck_sat: bool = True) -> list[ReferenceClaim]:
        n, k = self.world.net.n, self.world.max_indegree
        vs = build_version_space(self.evidence, HypothesisClass(n, k))
        ms = MechanismSpace(self.evidence, k)
        out = []
        for c in self.design.claims:
            q = c.query
            num, den = exact_query_counts(vs, q)
            cc = ms.claim_counts(q)
            if (cc.num, cc.den) != (num, den):
                raise AssertionError(f"reference mismatch (explicit vs D) on {c.cid}")
            v = verdict_of(num, den)
            if crosscheck_sat and verdict(vs, q).verdict.value != v:
                raise AssertionError(f"reference mismatch (explicit vs SAT) on {c.cid}")
            out.append(ReferenceClaim(c.cid, v, num, den, int(predict(self.world.net, q)), q.horizon,
                                      q.intervention.kind))
        return out

    def truth_holds(self, q: Query) -> int:
        return int(predict(self.world.net, q))

    def execute_action(self, q: Query) -> dict:
        """Run the intervention on the hidden mechanism; report whether the postcondition (target literal) held."""
        from ..versionspace import point_query_parts
        tr = reference.run(self.world.net, point_query_parts(q, self.world.net.n), q.intervention, q.horizon)
        return {"postcondition_held": bool(reference.holds(q.target, reference.to_bits(tr[-1], self.world.net.n)))}

    def observe(self, state: int, iv, node: int) -> int:
        """S4-B: the result of a purchased one-step measurement (logged by the caller)."""
        y = reference.run(self.world.net, state, iv, 1)[-1]
        return (y >> node) & 1
