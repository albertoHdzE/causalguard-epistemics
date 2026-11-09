"""Hand-derived semantic fixtures (data/fixtures/semantic_fixtures.json).

Each expected answer is explained in the fixture file independently of the code;
both the independent reference and every production backend must reproduce it."""
import pytest

from causalguard import query, reference
from causalguard.bdd_ref import BDDModel
from causalguard.index_repr import from_network
from causalguard.schema import Evidence, HypothesisClass, Network, Observation, Query
from causalguard.versionspace import build_version_space, verdict, verdict_from_enumeration


def _model_cases(fx):
    return [(c["id"], c) for c in fx["model_fixtures"]]


def test_fixture_counts(fixtures):
    assert len(fixtures["model_fixtures"]) == 9
    assert len(fixtures["evidence_fixtures"]) == 5


@pytest.mark.parametrize("backend", ["reference", "index_enum", "index_cube", "index_sat", "literal", "bdd"])
def test_model_fixtures(fixtures, backend):
    checked = 0
    for c in fixtures["model_fixtures"]:
        net = Network.from_json(c["network"])
        q = Query.from_json(c["query"])
        rep = from_network(net)
        if backend == "reference":
            r = reference.evaluate(net, q)
        elif backend == "index_enum":
            r = query.index_enum(rep, net, q)
        elif backend == "index_cube":
            r = query.index_cube(rep, net, q)
        elif backend == "index_sat":
            r = query.index_sat(rep, net, q, check_proof=True)
        elif backend == "literal":
            r = query.literal_query(query.literal_successors(net), net, q)
        else:
            with BDDModel(net) as m:
                r = m.answer(q)
        assert r.answer.value == c["expected"], (c["id"], backend, r.answer)
        checked += 1
    assert checked == 9


def test_sequential_update_differs(fixtures):
    c = next(c for c in fixtures["model_fixtures"] if c["id"] == "F09_sync_vs_sequential")
    net = Network.from_json(c["network"])
    assert reference.step_bits(net, [1, 0]) == [0, 1]
    assert reference.step_bits_sequential(net, [1, 0]) == [0, 0]


def test_evidence_fixtures(fixtures):
    for c in fixtures["evidence_fixtures"]:
        ev = Evidence(c["n"], tuple(Observation.from_json(o) for o in c["observations"]))
        q = Query.from_json(c["query"])
        vs = build_version_space(ev, HypothesisClass(c["n"], c["k"]))
        v = verdict(vs, q, check_proof=True)
        assert v.verdict.value == c["expected"], c["id"]
        assert v.candidate_set_complete
        assert verdict_from_enumeration(vs, q).value == c["expected"]
        bf, _ = reference.version_space_verdict(reference.all_bounded_networks(c["n"], c["k"]), ev, q) \
            if c["n"] <= 2 or (c["n"] == 3 and c["k"] == 1) else (v.verdict, None)
        assert bf == v.verdict


def test_underdetermined_has_two_replayed_witnesses(fixtures):
    c = fixtures["evidence_fixtures"][0]
    ev = Evidence(c["n"], tuple(Observation.from_json(o) for o in c["observations"]))
    q = Query.from_json(c["query"])
    v = verdict(build_version_space(ev, HypothesisClass(c["n"], c["k"])), q)
    assert v.verdict.value == "underdetermined"
    plus, minus = (Network.from_json(w) for w in v.certificate.witness_models)
    assert reference.consistent(plus, ev) and reference.consistent(minus, ev)
    assert reference.evaluate(plus, q).answer.value == "true"
    assert reference.evaluate(minus, q).answer.value == "false"
