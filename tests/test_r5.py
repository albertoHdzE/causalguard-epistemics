"""R5 tests: independent correctness, projection semantics, contracts, leakage, accounting, counterexample."""
from __future__ import annotations

import itertools
import json
import math
import random

import pytest

from causalguard import reference
from causalguard.schema import Evidence, HypothesisClass, Intervention, Network, Observation, Pred, Query, Rule


def _rnet(rng, n, k):
    return Network(n, tuple(Rule(tuple(sorted(rng.sample(range(n), d))), rng.getrandbits(1 << d)).canonical()
                            for d in [rng.randint(0, k) for _ in range(n)]))


def _ev(rng, net, B, clamp=True):
    obs = []
    for i, x in enumerate(rng.sample(range(1 << net.n), B)):
        iv = Intervention("persistent_clamp", ((rng.randrange(net.n), rng.randint(0, 1)),)) if clamp and i % 3 == 2 \
            else Intervention("none")
        y = reference.run(net, x, iv, 1)[-1]
        cl = {j for j, _ in iv.assign} if iv.kind == "persistent_clamp" else set()
        obs.append(Observation(x, iv, 1, tuple((j, (y >> j) & 1) for j in range(net.n) if j not in cl)))
    return Evidence(net.n, tuple(obs))


# --------------------------------------------------------------------------- Track M exact counterexample

def test_and_counterexample_model_relative_proof_is_not_world_truth():
    from causalguard.r5.misspec import and_counterexample
    r = and_counterexample()
    assert r["evidence_matches_hidden"]
    assert r["k1"]["per_node_counts"] == [1, 1] and r["k1"]["verdict"] == "refuted"     # verified node0 = 0
    assert r["hidden_target_value"] == 1                                                  # simulator says 1
    assert r["k2"]["verdict"] == "underdetermined"


def test_mixed_node_bounds_match_explicit_union_space():
    from causalguard.s4.mechspace import MechanismSpace
    rng = random.Random(3)
    net = _rnet(rng, 4, 2)
    ev = _ev(rng, net, 5)
    ms = MechanismSpace(ev, 2, node_k=[3, 2, 2, 2])
    a, b = MechanismSpace(ev, 3), MechanismSpace(ev, 2)
    assert ms.counts() == [a.counts()[0]] + b.counts()[1:]


# --------------------------------------------------------------------------- Track C counting

def test_gen_ve_matches_d_and_explicit_engine():
    from causalguard.r5.counting import VECounter
    from causalguard.s4.mechspace import MechanismSpace
    from causalguard.versionspace import build_version_space, exact_query_counts
    rng = random.Random(11)
    for _ in range(12):
        n = rng.choice([4, 6])
        k = rng.choice([2, 3])
        net = _rnet(rng, n, k)
        ev = _ev(rng, net, rng.choice([3, 6, 9]))
        ve, ms = VECounter(ev, k), MechanismSpace(ev, k)
        vs = build_version_space(ev, HypothesisClass(n, k))
        assert ve.counts == ms.counts() == [len(c) for c in vs.compatible]
        for _ in range(3):
            kind = rng.choice(["none", "initial_edit", "persistent_clamp"])
            iv = Intervention("none") if kind == "none" else Intervention(kind, ((rng.randrange(n), rng.randint(0, 1)),))
            q = Query.point(rng.randrange(1 << n), n, iv, rng.choice([1, 2]), Pred.lit(rng.randrange(n), rng.randint(0, 1)))
            c = ms.claim_counts(q)
            assert ve.count(q) == (c.num, c.den) == exact_query_counts(vs, q)


def test_gen_ve_against_truth_table_oracle():
    """Independent of every engine: all functions on 3 inputs as full 8-row truth tables."""
    from causalguard.r5.counting import VECounter
    k = 2
    funcs = [f for f in range(256) if sum(1 for i in range(3) if any(((f >> y) & 1) != ((f >> (y ^ (1 << i))) & 1)
                                                                       for y in range(8))) <= k]
    assert len(funcs) == 38
    rng = random.Random(4)
    net = _rnet(rng, 3, 2)
    ev = _ev(rng, net, 3, clamp=False)
    cons = [dict() for _ in range(3)]
    for o in ev.observations:
        for j, v in o.observed:
            cons[j][o.state] = v
    per = [[f for f in funcs if all(((f >> x) & 1) == v for x, v in cons[j].items())] for j in range(3)]
    ve = VECounter(ev, k)
    assert ve.counts == [len(p) for p in per]
    q = Query.point(5, 3, Intervention("none"), 2, Pred.lit(1, 1))
    num = 0
    for fs in itertools.product(*per):
        s1 = sum(((fs[j] >> 5) & 1) << j for j in range(3))
        num += (sum(((fs[j] >> s1) & 1) << j for j in range(3)) >> 1) & 1
    assert ve.count(q) == (num, math.prod(len(p) for p in per))


def test_impossible_evidence_is_empty_not_zero_probability():
    from causalguard.r5.counting import VECounter
    from causalguard.schema import SemanticsError
    obs = (Observation(0, Intervention("none"), 1, ((0, 0),)), Observation(0, Intervention("none"), 1, ((0, 1),)))
    ve = VECounter(Evidence(2, obs), 1)
    assert ve.empty and ve.size() == 0
    with pytest.raises(SemanticsError):
        ve.count(Query.point(1, 2, Intervention("none"), 1, Pred.lit(0, 1)))


def test_projected_cnf_counts_distinct_mechanisms_and_trap():
    from causalguard.r5.counting import VECounter, canonical_cnf, projected_count_bruteforce
    rng = random.Random(2)
    net = _rnet(rng, 3, 2)
    for ev in (Evidence(3, ()), _ev(rng, net, 2, clamp=False)):
        cnf, show, _ = canonical_cnf(ev, 2)
        distinct = VECounter(ev, 2).size()
        assert projected_count_bruteforce(cnf.clauses, show) == distinct
        assert projected_count_bruteforce(cnf.clauses, list(range(1, cnf.nv + 1))) == distinct
    # trap: the verdict-oriented ladder encoding (exact-k selector + free tables) does NOT count mechanisms
    from causalguard.versionspace import _Enc, build_version_space
    ev1 = Evidence(2, ())
    vs = build_version_space(ev1, HypothesisClass(2, 1))
    enc = _Enc(vs, "ladder")
    node0 = [v for S in enc.sel[0] for v in [enc.sel[0][S]] + enc.L[0][S]]
    clauses0 = [c for c in enc.cnf.clauses if all(abs(x) in set(node0) for x in c)]
    enc_count = projected_count_bruteforce(clauses0, node0)
    distinct = VECounter(Evidence(2, ()), 1).counts[0]                 # 2 constants + 2 x (COPY, NOT) = 6
    assert distinct == 6 and enc_count != distinct


def test_count_result_contract():
    from causalguard.r5.contracts import ContractError, CountResult
    ok = CountResult("D", "v", "distinct_canonical_mechanisms", "none", "e", "q", "exact", 1, 2, True)
    assert ok.to_json()["num"] == "1"
    for bad in (dict(semantics="sat_assignments"), dict(num=True), dict(num=3), dict(status="timeout")):
        kw = dict(backend="D", backend_version="v", semantics="distinct_canonical_mechanisms", projection="none",
                  evidence_hash="e", query_hash="q", status="exact", num=1, den=2, exact=True)
        kw.update(bad)
        with pytest.raises(ContractError):
            CountResult(**kw).validate()


# --------------------------------------------------------------------------- Track G

def test_gsr_matches_program_enumeration():
    from causalguard.r5.priors import GSR, gsr_bruteforce
    rng = random.Random(3)
    net = Network(3, (Rule((1,), 0b10), Rule((0,), 0b01), Rule((), 1)))
    ev = _ev(rng, net, 2, clamp=False)
    g = GSR(ev, 1)
    for h in (1, 2):
        for iv in (Intervention("none"), Intervention("persistent_clamp", ((2, 0),))):
            q = Query.point(rng.randrange(8), 3, iv, h, Pred.lit(rng.choice([0, 1]), 1))
            for a in (0.25, 0.75):
                assert abs(g.probability(q, a)["p"] - float(gsr_bruteforce(ev, 1, q, a))) < 1e-10


def test_xdc_matches_enumeration_and_reduces_to_base_code():
    """R6: the exchangeable dictionary code is summed exactly (vs explicit enumeration of every seating, type and
    instantiation), and theta = inf is exactly the flat base code (so XDC - base isolates sharing)."""
    from fractions import Fraction

    from causalguard.r5.priors import XDC, xdc_bruteforce
    from causalguard.s4.prior import Averager
    rng = random.Random(5)
    net = Network(3, (Rule((1,), 0b10), Rule((0,), 0b01), Rule((), 1)))
    ev = _ev(rng, net, 2, clamp=False)
    checked = 0
    for base in ("gate", "cgh_flat"):
        x = XDC(ev, 1, base=base, thetas=(0.5, 3.0, float("inf")))
        av = Averager(ev, 1, codes=(base,))
        for h in (1, 2):
            for iv in (Intervention("none"), Intervention("persistent_clamp", ((2, 0),)),
                       Intervention("initial_edit", ((1, 1),))):
                q = Query.point(rng.randrange(8), 3, iv, h, Pred.lit(rng.choice([0, 1]), 1))
                pr = x.probabilities(q)
                for th, name in ((Fraction(1, 2), "xdc_t0.5"), (Fraction(3), "xdc_t3")):
                    assert abs(pr[name] - float(xdc_bruteforce(ev, 1, q, th, base))) < 1e-10
                    checked += 1
                assert abs(pr["xdc_tinf"] - float(av.probability_exact(base, q))) < 1e-10
                assert abs(sum(pr["theta_posterior"].values()) - 1) < 1e-12
    assert checked == 24
    # sharing must matter: on evidence where two nodes are seen to copy each other the finite-theta forecast differs
    assert any(abs(pr["xdc_t0.5"] - pr["xdc_tinf"]) > 1e-6 for pr in [x.probabilities(
        Query.point(s, 3, Intervention("none"), 1, Pred.lit(t, 1))) for s in range(8) for t in range(3)])


def test_outcome_is_node_value_and_literal_convention():
    from causalguard.r5 import data as D
    from causalguard.r5.forecast import _node_prob
    net = Network(2, (Rule((), 0), Rule((), 1)))
    q1 = Query.point(0, 2, Intervention("none"), 1, Pred.lit(1, 1))
    q0 = Query.point(0, 2, Intervention("none"), 1, Pred.lit(1, 0))
    assert D.outcome(net, q1) == 1 and D.outcome(net, q0) == 1          # node value, not literal truth
    assert _node_prob(0.3, q1) == 0.3
    with pytest.raises(ValueError):
        _node_prob(0.3, q0)


def test_public_payload_has_no_hidden_fields_and_predictions_depend_only_on_it():
    from causalguard.r5 import data as D
    from causalguard.r5.forecast import predict_public
    from causalguard.s4.tasks import audit_public_payload
    inst = D.make_instance("calibration", "uniform_H", 0)
    des = D.make_design("t", inst.mechanism_id)
    ev = D.make_evidence(inst.net, des, 8)
    pub = D.public_payload(inst.mechanism_id, ev, des)
    blob = json.dumps(pub)
    assert audit_public_payload(pub) == []
    assert inst.mechanism_id not in blob and inst.stratum not in blob
    pub["queries"] = pub["queries"][:2]
    a = predict_public(json.dumps(pub, sort_keys=True))
    b = predict_public(json.dumps(pub, sort_keys=True))
    strip = lambda o: [{k: {n: (v["p"], v["status"]) for n, v in q["predictions"].items()} for k in ("x",)}  # noqa
                       for q in o["queries"]]
    assert strip(a) == strip(b)


def test_design_queries_are_novel_and_distinct():
    from causalguard.r5 import data as D
    des = D.make_design("t", "k")
    seen = {x for x, _ in des.obs_specs}
    keys = set()
    for _, q in des.queries:
        from causalguard.versionspace import point_query_parts
        x0 = point_query_parts(q, D.N)
        assert x0 not in seen and q.target.value == 1
        keys.add((x0, json.dumps(q.intervention.to_json()), q.horizon, q.target.node))
    assert len(keys) == D.N_QUERIES and sum(q.horizon == 1 for _, q in des.queries) == 4


def test_split_has_no_shared_groups_or_duplicates():
    from causalguard.r5 import data as D
    a = D.split_audit(D.population("calibration"), D.population("evaluation"))
    assert a["shared_groups"] == 0 and a["exact_duplicates_cross_split"] == 0 and a["isomorphic_cross_split"] == 0
    assert a["evaluation_groups"] == 280                       # 40 rewired controls share their source's group


def test_world_brier_bounds_missing_predictions():
    from causalguard.analysis.r5_analysis import _world_brier
    rows = [{"query_id": "q0", "predictions": {"x": {"p": 1.0}}}, {"query_id": "q1", "predictions": {"x": {"p": None}}}]
    pt, lo, hi = _world_brier(rows, {"q0": 1, "q1": 0}, "x")
    assert math.isnan(pt) and lo == 0.0 and hi == 0.5


def test_external_parser_deep_nesting_and_rejects_bad_syntax():
    from causalguard.r5.external import ParseError, evaluate, parse_expr
    e = parse_expr("(" * 3000 + "a" + ")" * 3000 + " & !b")
    assert evaluate(e, {"a": 1, "b": 0}) == 1 and evaluate(e, {"a": 1, "b": 1}) == 0
    for bad in ("a &", "(a | b", "a b", "!"):
        with pytest.raises(ParseError):
            parse_expr(bad)


# --------------------------------------------------------------------------- accounting / contracts

def test_call_budget_phase_cap_and_interrupted_reservation(tmp_path):
    from causalguard.llm.harness import CallBudget
    from causalguard.llm.providers import CapExceeded
    led = tmp_path / "ledger.jsonl"
    b = CallBudget(None, 5, led, "w", phase="A-calibration", phase_cap=2)
    b.before_attempt()
    b.before_attempt()                                     # reserved before dispatch: counts even if interrupted
    with pytest.raises(CapExceeded) as ei:
        b.before_attempt()
    assert ei.value.scope == "phase_cap_reached"
    other = CallBudget(None, 5, led, "w", phase="A-evaluation", phase_cap=10)
    for _ in range(3):
        other.before_attempt()
    with pytest.raises(CapExceeded) as ei:
        other.before_attempt()
    assert ei.value.scope == "global_cap_reached"
    from causalguard.r5.contracts import call_usage
    assert call_usage(led) == {"total": 5, "by_phase": {"A-calibration": 2, "A-evaluation": 3}}


def test_assumption_check_rejects_hidden_fields():
    from causalguard.r5.contracts import ContractError, assumption_check
    kw = dict(declared_class="H", alternative_classes=[], evidence_consistent=True, verdict_per_class={},
              aggregate_guarantee="abstain", certificate_level="none", abstention_reason=None)
    assumption_check(**kw)
    with pytest.raises(ContractError):
        assumption_check(**{**kw, "verdict_per_class": {"misspecified": True}})


def test_prediction_contract_states():
    from causalguard.r5.contracts import ContractError, Prediction
    Prediction("q", "g", "s", "u", "u", "refused_resource", None, reason="cap").validate()
    with pytest.raises(ContractError):
        Prediction("q", "g", "s", "u", "u", "refused_resource", 0.5, reason="cap").validate()
    with pytest.raises(ContractError):
        Prediction("q", "g", "s", "u", "u", "exact", 0.5).validate()


# --------------------------------------------------------------------------- Track A

def test_menu_excludes_target_equivalent_and_parse_rejects_invalid_actions():
    from causalguard.r5 import investigation as I
    from causalguard.versionspace import point_query_parts
    w = I.world("calibration", "uniform_H", 0)
    q = Query.from_json(w["pub"]["claims"][0]["query"])
    s0 = I._eff(point_query_parts(q, 8), q.intervention)
    if q.horizon == 1:
        assert not any(I._eff(m["state"], Intervention.from_json(m["intervention"])) == s0 and m["node"] == q.target.node
                       for m in w["pub"]["menu"])
    assert "net" not in json.dumps(w["pub"]) and len(w["pub"]["menu"]) == 16
    assert I.parse_reply('{"verdict": "refuted", "measure": 99}', [0, 1], True) == (None, "invalid_measure")
    assert I.parse_reply('{"verdict": "maybe", "measure": 0}', [0, 1], True) == (None, "bad_verdict")
    ok, _ = I.parse_reply('x {"verdict": "underdetermined", "p_target": 0.4, "measure": 1} y', [0, 1], True)
    assert ok == {"verdict": "underdetermined", "p_target": 0.4, "measure": 1}


def test_ai_episode_respects_eight_attempt_cap():
    from causalguard.llm.harness import CallBudget
    from causalguard.llm.providers import MockProvider
    from causalguard.r5 import investigation as I
    w = I.world("calibration", "uniform_H", 0)
    e = I.ai_episode(w, "D", MockProvider(script=lambda m, t, s: "no json here"), CallBudget(8, None))
    assert e["n_attempts"] <= 8 and e["status"] in ("call_cap",) or e["status"].startswith("cap:")
    assert len(e["invalid"]) == e["n_attempts"]


def test_stop_action_is_valid_and_carries_verdict():
    from causalguard.llm.harness import CallBudget
    from causalguard.llm.providers import MockProvider
    from causalguard.r5 import investigation as I
    assert I.parse_reply('{"verdict": "entailed", "p_target": 1, "measure": null}', [0], True)[0]["measure"] is None
    w = I.world("calibration", "uniform_H", 0)
    e = I.ai_episode(w, "D", MockProvider(script=lambda m, t, s: '{"verdict": "underdetermined", "measure": null}'),
                     CallBudget(8, None))
    assert e["status"] == "stopped" and e["n_attempts"] == 1 and set(e["per_turn"]) == {"0", "1", "2", "3", "4"}


def test_gen_ve_handles_64_bit_states():
    from causalguard.r5.counting import VECounter
    from causalguard.s4.mechspace import MechanismSpace
    rng = random.Random(64)
    n = 64
    net = Network(n, tuple(Rule(tuple(sorted(rng.sample(range(n), 2))), rng.getrandbits(4)).canonical() for _ in range(n)))
    obs = []
    for x in [rng.getrandbits(64) | (1 << 63) for _ in range(3)]:
        y = reference.run(net, x, Intervention("none"), 1)[-1]
        obs.append(Observation(x, Intervention("none"), 1, tuple((j, (y >> j) & 1) for j in range(n))))
    ev = Evidence(n, tuple(obs))
    q = Query.point((1 << 63) | 5, n, Intervention("none"), 1, Pred.lit(63, 1))
    ve, ms = VECounter(ev, 2), MechanismSpace(ev, 2)
    c = ms.claim_counts(q)
    assert ve.counts == ms.counts() and ve.count(q) == (c.num, c.den)
