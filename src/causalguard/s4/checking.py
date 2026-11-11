"""Check before release: propose -> check -> (counterexample | revise) -> commit.

A PROPOSAL is a structured statement by the AI about one claim:
    {"cid", "claim": <claim json>, "asserted": "entailed" | "refuted" | "underdetermined" | "forecast",
     "forecast": 0 | 1 | None, "action": None | {"execute": true}}
"entailed" asserts that the target literal holds in EVERY compatible mechanism, "refuted" that it fails in every
one, "underdetermined" that compatible mechanisms disagree, "forecast" a non-certified prediction of the target
value.

check() returns two SEPARATE fields:
    proposal_check_status   verified | refuted | underdetermined | inconsistent_assumptions | unsupported_or_resource
    epistemic_verdict       the claim's own status over V(D): entailed | refuted | underdetermined | inconsistent | ...
A counterexample to "q is certain" refutes that ASSERTION; it does not make the target "refuted" (the target can
remain underdetermined).  A forecast is never 'verified' because of a high probability: it is verified only
when the forecast value is certain (all compatible mechanisms agree), otherwise its status is 'underdetermined'
(displayable as a forecast, no verification badge).  An empty V(D) never approves anything (no vacuous truth).

Certificates (equal for every arm, produced by the COMMON checker, not by the AI or its self-critique):
    verified definite claims  -> exact count of the opposite side = 0 under the backend, cross-checked by the
                                 complete SAT encoding (UNSAT of the opposite side; RUP-checked when enabled), and
                                 one replayed witness of the asserted side
    verified underdetermined  -> two independently replayed opposing witnesses
    refuted assertions        -> a replayed counterexample (definite assertions) or the UNSAT certificate of the
                                 missing side (an 'underdetermined' assertion about a determined claim)
Every decision is bound to: claim digest, asserted status, forecast, hypothesis class, evidence hash, update
semantics, ordering, horizon, backend identity.  commit() re-derives the binding from the CURRENT proposal and
workspace; any change (claim, evidence, model class, ordering, horizon, assertion) makes the decision stale.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass, field

from .. import reference
from ..schema import Pred, Query, content_hash
from .workspace import Workspace

PROPOSAL_KINDS = ("entailed", "refuted", "underdetermined", "forecast")
CHECK_STATUSES = ("verified", "refuted", "underdetermined", "inconsistent_assumptions", "unsupported_or_resource")


class InvalidProposal(ValueError):
    pass


def validate_proposal(p: dict, claims_by_id: dict) -> dict:
    if not isinstance(p, dict):
        raise InvalidProposal("proposal must be an object")
    if p.get("asserted") not in PROPOSAL_KINDS:
        raise InvalidProposal(f"asserted must be one of {PROPOSAL_KINDS}")
    cid = p.get("cid")
    if cid not in claims_by_id:
        raise InvalidProposal(f"unknown claim id {cid!r}")
    claim = p.get("claim", claims_by_id[cid])
    if json.dumps(claim, sort_keys=True) != json.dumps(claims_by_id[cid], sort_keys=True):
        raise InvalidProposal("proposal claim text differs from the scheduled claim (changed claim)")
    f = p.get("forecast")
    if f not in (0, 1, None) or isinstance(f, bool):
        raise InvalidProposal("forecast must be 0, 1 or null")
    if p["asserted"] == "forecast" and f is None:
        raise InvalidProposal("a forecast proposal needs a forecast value")
    return {"cid": cid, "claim": claim, "asserted": p["asserted"], "forecast": f, "action": p.get("action")}


def binding(p: dict, ws: Workspace) -> str:
    q = Query.from_json(p["claim"]["query"])
    return content_hash({"claim": q.digest(), "asserted": p["asserted"], "forecast": p["forecast"],
                         "horizon": q.horizon, "action": p.get("action"), "assumptions": ws.identity()})


_SEAL_KEY = secrets.token_bytes(32)          # held by the checker process only; never sent to an agent


def _seal(d: dict) -> str:
    body = json.dumps({k: v for k, v in d.items() if k != "seal"}, sort_keys=True, default=str).encode()
    return hmac.new(_SEAL_KEY, body, hashlib.sha256).hexdigest()


@dataclass
class Decision:
    cid: str
    proposal_check_status: str
    epistemic_verdict: str
    binding: str
    certificate: dict
    counterexample: dict | None
    feedback: str
    seal: str = field(default="")

    def __post_init__(self):
        if not self.seal:
            self.seal = _seal(self.to_json())

    def to_json(self) -> dict:
        return dict(self.__dict__)

    def authentic(self) -> bool:
        return hmac.compare_digest(self.seal, _seal(self.to_json()))


def _sat_crosscheck(ws: Workspace, q: Query, side_holds: bool) -> str:
    """Common independent checker: is there a compatible model with target == side?  Uses the complete SAT
    encoding (independent of the backend's representation).  Returns 'sat' | 'unsat' | 'unsat_rup_checked'."""
    from ..versionspace import verdict
    from .workspace import _sat_only_space
    vs = _sat_only_space(ws.evidence, ws.hclass)
    vr = verdict(vs, q if side_holds else Query(q.quantifier, q.domain, q.intervention, q.horizon,
                                                Pred.lit(q.target.node, 1 - q.target.value)),
                 check_proof=ws.limits.proof_check)
    v = vr.verdict.value
    if v in ("entailed", "underdetermined"):
        return "sat"
    return "unsat_rup_checked" if vr.certificate.level.value == "checked_proof" else "unsat"


def check(p: dict, ws: Workspace, crosscheck: bool = True) -> Decision:
    q = Query.from_json(p["claim"]["query"])
    res = ws.check(p["claim"])
    ev = res["verdict"]
    b = binding(p, ws)
    labels = ws.labels
    if ev == "inconsistent":
        return Decision(p["cid"], "inconsistent_assumptions", "inconsistent", b, {"counts": None}, None,
                        "No mechanism in the declared class agrees with the evidence; nothing can be approved.")
    if ev == "unsupported_or_resource":
        return Decision(p["cid"], "unsupported_or_resource", ev, b, {"reason": res.get("reason")}, None,
                        "The check did not finish or the claim is outside the supported semantics. This is not a "
                        "proof and not evidence of underdetermination.")
    wn = ws.witness_networks()
    cert = {"backend": ws.arm, "counts": res.get("counts"), "backend_certificate": res.get("certificate")}
    asserted = p["asserted"]
    exists = {1: 1 in wn, 0: 0 in wn}
    if crosscheck:
        for side in (1, 0):
            if not exists[side]:
                x = _sat_crosscheck(ws, q, bool(side))
                if x == "sat":
                    raise AssertionError("backend and SAT cross-check disagree")
                cert[f"side{side}_impossible"] = x
    for net in wn.values():
        if not reference.consistent(net, ws.evidence):
            raise AssertionError("witness inconsistent with evidence")
    def cx(side):
        net = wn[side]
        tr = reference.run(net, _x0(q, ws.n), q.intervention, q.horizon)
        return {"side": side, "mechanism": res["witnesses"].get(str(side)), "trajectory": [f"{s:0{ws.n}b}"[::-1] for s in tr],
                "replayed": True}
    tgt = f"{labels[q.target.node]}={q.target.value} after {q.horizon} step(s)"
    if asserted in ("entailed", "refuted"):
        want = 1 if asserted == "entailed" else 0
        if not exists[1 - want]:
            return Decision(p["cid"], "verified", ev, b, {**cert, "witness_replayed": want in wn}, None,
                            f"Verified under the declared class and evidence: '{tgt}' is {asserted}.")
        return Decision(p["cid"], "refuted", ev, b, cert, cx(1 - want),
                        f"Your assertion '{tgt}' is {asserted} is refuted by a compatible mechanism (counterexample "
                        f"attached). The claim's own status is {ev}.")
    if asserted == "underdetermined":
        if exists[0] and exists[1]:
            return Decision(p["cid"], "verified", ev, b, {**cert, "witnesses_replayed": 2}, None,
                            f"Verified: compatible mechanisms disagree on '{tgt}' (two replayed witnesses).")
        return Decision(p["cid"], "refuted", ev, b, cert, None,
                        f"Not underdetermined: every compatible mechanism agrees; '{tgt}' is {ev}.")
    f = p["forecast"]                                      # forecast: target value predicted
    agrees = 1 if f == q.target.value else 0              # forecast side relative to the literal
    if not exists[1 - agrees]:
        return Decision(p["cid"], "verified", ev, b, cert, None, "The forecast value is certain (verified).")
    if not exists[agrees]:
        return Decision(p["cid"], "refuted", ev, b, cert, cx(1 - agrees),
                        "The forecast value is impossible under the declared class and evidence.")
    return Decision(p["cid"], "underdetermined", ev, b, cert, None,
                    "Forecast only: compatible mechanisms disagree. It can be shown as a forecast, never verified.")


def _x0(q: Query, n: int) -> int:
    from ..versionspace import point_query_parts
    return point_query_parts(q, n)


def counterexample(p: dict, ws: Workspace) -> dict | None:
    return check(p, ws).counterexample


def revise(old: dict, decision: Decision, new: dict, claims_by_id: dict) -> dict:
    """A revision is a NEW proposal for the same scheduled claim; it needs a fresh check (old decisions never
    transfer)."""
    newp = validate_proposal(new, claims_by_id)
    if newp["cid"] != old["cid"]:
        raise InvalidProposal("a revision must address the same claim")
    return newp


class CommitRefused(Exception):
    pass


def commit(p: dict, decision: Decision, ws: Workspace, require_proof: bool = True) -> dict:
    """Simulated release/execution gate.  Allowed only for a 'verified' decision whose binding equals the binding
    re-derived from the CURRENT proposal and workspace.  Forecasts are never released as verified."""
    if not require_proof:
        return {"released": True, "verified": decision.proposal_check_status == "verified"}
    if not isinstance(decision, Decision) or not decision.authentic():
        raise CommitRefused("not an authentic checker decision (edited, forged or text)")
    if decision.proposal_check_status != "verified":
        raise CommitRefused(f"not verified ({decision.proposal_check_status})")
    if p["asserted"] == "forecast" and decision.epistemic_verdict == "underdetermined":
        raise CommitRefused("forecast without certainty")
    if binding(p, ws) != decision.binding:
        raise CommitRefused("stale decision: the claim, assertion, assumptions or evidence changed")
    return {"released": True, "verified": True, "binding": decision.binding}


def proof_text_is_not_a_certificate(text: str) -> bool:
    """Fluent or proof-looking text is never accepted as a certificate: only Decision objects produced by
    check() authorize a commit.  (Kept as an explicit, tested rule.)"""
    return False
