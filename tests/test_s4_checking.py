"""Check-before-release gate: separate proposal status vs epistemic verdict, binding/staleness, adversarial
fixtures (wrong quantifier, off-by-one state, stale proof, order mismatch, wrong horizon, correlation-based claim,
empty V, proof-looking text) and equal behaviour across B/C/D."""
import copy
import dataclasses

import pytest

from causalguard.s4.checking import CommitRefused, InvalidProposal, binding, check, commit, proof_text_is_not_a_certificate, revise, validate_proposal
from causalguard.s4.evaluator import Evaluator
from causalguard.s4.workspace import Limits, make_workspace
from causalguard.schema import Evidence, Intervention, Observation, Query


@pytest.fixture(scope="module")
def world():
    ev = Evaluator("t-s4-check", 3, "repeated_modules")
    assert {r.verdict for r in ev.reference()} == {"entailed", "refuted", "underdetermined"}
    return ev, ev.public(), {r.cid: r for r in ev.reference()}


def _claims(pub):
    return {c["cid"]: c for c in pub["claims"]}


def _first(refs, v):
    return next(r for r in refs.values() if r.verdict == v)


@pytest.mark.parametrize("arm", ["B", "C", "D"])
def test_status_semantics_by_case(world, arm):
    ev, pub, refs = world
    ws = make_workspace(arm, pub)
    cl = _claims(pub)
    for r in refs.values():
        for asserted in ("entailed", "refuted", "underdetermined"):
            p = validate_proposal({"cid": r.cid, "asserted": asserted, "forecast": None}, cl)
            d = check(p, ws)
            assert d.epistemic_verdict == r.verdict
            expect = "verified" if asserted == r.verdict else "refuted"
            assert d.proposal_check_status == expect, (arm, r, asserted)
            if expect == "refuted" and asserted != "underdetermined":
                assert d.counterexample and d.counterexample["replayed"]
        for f in (0, 1):
            d = check(validate_proposal({"cid": r.cid, "asserted": "forecast", "forecast": f}, cl), ws)
            if r.verdict == "underdetermined":
                assert d.proposal_check_status == "underdetermined"      # never a verification badge
            else:
                assert d.proposal_check_status in ("verified", "refuted")


def test_wrong_quantifier_counterexample_does_not_refute_target(world):
    ev, pub, refs = world
    r = _first(refs, "underdetermined")
    ws = make_workspace("D", pub)
    d = check(validate_proposal({"cid": r.cid, "asserted": "entailed"}, _claims(pub)), ws)
    assert d.proposal_check_status == "refuted" and d.epistemic_verdict == "underdetermined"


def test_commit_gate_and_staleness(world):
    ev, pub, refs = world
    cl = _claims(pub)
    r = _first(refs, "entailed") if any(x.verdict == "entailed" for x in refs.values()) else _first(refs, "refuted")
    ws = make_workspace("D", pub)
    p = validate_proposal({"cid": r.cid, "asserted": r.verdict}, cl)
    d = check(p, ws)
    assert commit(p, d, ws)["released"]
    # stale: new evidence changes the assumptions
    o = Observation(0, Intervention("none"), 1, ((0, ev.evaluator_value if hasattr(ev, "evaluator_value") else
                                                   ev.observe(0, Intervention("none"), 0)),))
    ws2 = ws.update([o])
    with pytest.raises(CommitRefused, match="stale"):
        commit(p, d, ws2)
    # order mismatch: a workspace whose declared ordering differs
    ws3 = make_workspace("D", pub)
    ws3.identity = lambda: {**ws.identity(), "ordering": "MSB-first local tables"}
    with pytest.raises(CommitRefused, match="stale"):
        commit(p, d, ws3)
    # changed assertion reuses an old decision
    p2 = dict(p, asserted="underdetermined")
    with pytest.raises(CommitRefused):
        commit(p2, d, ws)
    # refuted/underdetermined decisions are never released
    u = _first(refs, "underdetermined")
    pu = validate_proposal({"cid": u.cid, "asserted": "forecast", "forecast": 1}, cl)
    with pytest.raises(CommitRefused):
        commit(pu, check(pu, ws), ws)


def test_off_by_one_state_and_wrong_horizon_are_changed_claims(world):
    ev, pub, refs = world
    cl = _claims(pub)
    c = copy.deepcopy(cl["c0"])
    c["query"]["horizon"] += 1
    with pytest.raises(InvalidProposal, match="changed claim"):
        validate_proposal({"cid": "c0", "claim": c, "asserted": "entailed"}, cl)
    c = copy.deepcopy(cl["c0"])
    c["query"]["domain"] = Query.point(1, pub["n"], Intervention("none"), 1,
                                       Query.from_json(cl["c0"]["query"]).target).to_json()["domain"]
    with pytest.raises(InvalidProposal):
        validate_proposal({"cid": "c0", "claim": c, "asserted": "entailed"}, cl)
    with pytest.raises(InvalidProposal):
        validate_proposal({"cid": "c99", "asserted": "entailed"}, cl)
    with pytest.raises(InvalidProposal):
        validate_proposal({"cid": "c0", "asserted": "proved"}, cl)


def test_forged_decision_and_proof_text_are_rejected(world):
    ev, pub, refs = world
    cl = _claims(pub)
    ws = make_workspace("D", pub)
    u = _first(refs, "underdetermined")
    p = validate_proposal({"cid": u.cid, "asserted": "entailed"}, cl)
    d = check(p, ws)
    forged = dataclasses.replace(d, proposal_check_status="verified", seal=d.seal)   # edited status, old seal
    assert forged.binding == binding(p, ws) and not forged.authentic()
    with pytest.raises(CommitRefused, match="authentic"):
        commit(p, forged, ws)
    with pytest.raises(CommitRefused, match="authentic"):
        commit(p, {"proposal_check_status": "verified", "binding": binding(p, ws)}, ws)   # a dict, not a Decision
    with pytest.raises(CommitRefused, match="authentic"):
        commit(p, "Proof: by exhaustive reasoning every model agrees. QED", ws)       # proof-looking text
    assert proof_text_is_not_a_certificate("Proof: ... QED") is False
    # a genuine verified decision for ANOTHER claim, relabelled, is refused (seal and binding both fail)
    other = validate_proposal({"cid": u.cid, "asserted": "underdetermined"}, cl)
    with pytest.raises(CommitRefused):
        commit(p, dataclasses.replace(check(other, ws)), ws)


def test_empty_version_space_never_approves(world):
    ev, pub, refs = world
    pub2 = copy.deepcopy(pub)
    obs = pub2["evidence"]["observations"]
    o = copy.deepcopy(obs[0])
    o["observed"] = [[j, 1 - v] for j, v in o["observed"]]           # contradicts the first observation
    obs.append(o)
    pub2["evidence_hash"] = Evidence.from_json(pub2["evidence"]).digest()
    for arm in "BCD":
        ws = make_workspace(arm, pub2)
        p = validate_proposal({"cid": "c0", "asserted": "entailed"}, _claims(pub2))
        d = check(p, ws)
        assert d.proposal_check_status == "inconsistent_assumptions"
        with pytest.raises(CommitRefused):
            commit(p, d, ws)


def test_correlation_based_claim_is_checked_not_trusted(world):
    """A claim asserted from the target's observed majority (a noncausal surface rule) is accepted only if the
    mechanism space entails it."""
    ev, pub, refs = world
    cl = _claims(pub)
    ws = make_workspace("D", pub)
    obs = Evidence.from_json(pub["evidence"]).observations
    for r in refs.values():
        q = Query.from_json(cl[r.cid]["query"])
        vals = [v for o in obs for j, v in o.observed if j == q.target.node]
        maj = int(2 * sum(vals) > len(vals))
        asserted = "entailed" if maj == q.target.value else "refuted"
        d = check(validate_proposal({"cid": r.cid, "asserted": asserted}, cl), ws)
        assert (d.proposal_check_status == "verified") == (r.verdict == asserted)


def test_resource_refusal_is_not_a_proof(world):
    ev, pub, refs = world
    cl = _claims(pub)
    ws = make_workspace("D", pub, Limits(max_enum=1))
    h3 = [r for r in refs.values() if r.h == 3]
    if not h3:
        pytest.skip("no h=3 claim in this world")
    d = check(validate_proposal({"cid": h3[0].cid, "asserted": "entailed"}, cl), ws)
    assert d.proposal_check_status == "unsupported_or_resource"
    with pytest.raises(CommitRefused):
        commit(validate_proposal({"cid": h3[0].cid, "asserted": "entailed"}, cl), d, ws)


def test_revision_needs_fresh_check(world):
    ev, pub, refs = world
    cl = _claims(pub)
    ws = make_workspace("D", pub)
    u = _first(refs, "underdetermined")
    p = validate_proposal({"cid": u.cid, "asserted": "entailed"}, cl)
    d = check(p, ws)
    p2 = revise(p, d, {"cid": u.cid, "asserted": "underdetermined"}, cl)
    with pytest.raises(CommitRefused):
        commit(p2, d, ws)                                   # old decision does not transfer
    d2 = check(p2, ws)
    assert commit(p2, d2, ws)["released"]
