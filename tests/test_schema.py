import pytest

from causalguard.schema import (
    Evidence,
    Intervention,
    ModelAnswer,
    Network,
    Observation,
    Pred,
    Query,
    Rule,
    SemanticsError,
    Verdict,
    bits_of,
    state_from_bits,
)


def test_status_enums_refuse_bool():
    for v in list(ModelAnswer) + list(Verdict):
        with pytest.raises(TypeError):
            bool(v)


def test_state_roundtrip():
    for n in range(1, 7):
        for x in range(1 << n):
            assert state_from_bits(bits_of(x, n)) == x
    assert bits_of(1, 3) == (1, 0, 0)  # LSB-first: node 0 is bit 0


@pytest.mark.parametrize("bad", [
    lambda: Rule((1, 0), 0), lambda: Rule((0, 0), 0), lambda: Rule((0,), 4), lambda: Rule((-1,), 0),
    lambda: Network(2, (Rule((0,), 2),)), lambda: Network(2, (Rule((0,), 2), Rule((2,), 2))),
    lambda: Pred("xor"), lambda: Pred.lit(0, 2), lambda: Intervention("none", ((0, 1),)),
    lambda: Intervention("persistent_clamp", ()), lambda: Intervention("initial_edit", ((0, 1), (0, 0))),
    lambda: Query("most", Pred.true(), Intervention(), 1, Pred.true()), lambda: Query("exists", Pred.true(), Intervention(), -1, Pred.true()),
    lambda: Observation(0, Intervention(), 1, ((0, 2),)), lambda: Observation(0, Intervention(), 1, ()),
    lambda: Evidence(2, (Observation(4, Intervention(), 1, ((0, 1),)),)),
    lambda: Network(2, (Rule((0,), 2), Rule((1,), 2)), update="sequential"),
    lambda: Pred.from_json({"op": "exec", "code": "x"}),
])
def test_invalid_objects_rejected(bad):
    with pytest.raises(SemanticsError):
        bad()


def test_json_roundtrip():
    net = Network(3, (Rule((0, 2), 6, "XOR"), Rule((), 1), Rule((1,), 1)))
    assert Network.from_json(net.to_json()) == net
    q = Query("forall", Pred.or_(Pred.lit(0, 1), Pred.not_(Pred.lit(2, 0))), Intervention("persistent_clamp", ((1, 0),)), 4,
              Pred.and_(Pred.lit(1, 0), Pred.true()))
    assert Query.from_json(q.to_json()) == q
    ev = Evidence(3, (Observation(5, Intervention("initial_edit", ((0, 1),)), 1, ((2, 1), (0, 0))),), "x")
    assert Evidence.from_json(ev.to_json()) == ev
    assert ev.digest() == Evidence.from_json(ev.to_json()).digest()


def test_canonical_rule_drops_inessential():
    r = Rule((0, 1), 0b1010)  # depends only on input 0
    c = r.canonical()
    assert c.inputs == (0,) and c.table == 0b10
