import random

from causalguard import query, reference
from causalguard.bdd_ref import BDDModel
from causalguard.index_repr import from_network
from causalguard.proofcheck import check_rup_refutation
from causalguard.schema import (
    INTERVENTION_KINDS,
    QUANTIFIERS,
    Intervention,
    ModelAnswer,
    Network,
    Pred,
    Query,
    Rule,
)


def rpred(rng, n, depth=2):
    r = rng.random()
    if depth == 0 or r < 0.4:
        return Pred.lit(rng.randrange(n), rng.randint(0, 1))
    if r < 0.55:
        return Pred.not_(rpred(rng, n, depth - 1))
    return Pred(rng.choice(["and", "or"]), args=tuple(rpred(rng, n, depth - 1) for _ in range(rng.randint(1, 3))))


def random_case(rng, nmax=7):
    n = rng.randint(1, nmax)
    rules = []
    for _ in range(n):
        k = rng.randint(0, min(n, 3))
        rules.append(Rule(tuple(sorted(rng.sample(range(n), k))), rng.getrandbits(1 << k)))
    net = Network(n, tuple(rules))
    kind = rng.choice(INTERVENTION_KINDS)
    iv = Intervention() if kind == "none" else Intervention(kind, tuple((i, rng.randint(0, 1)) for i in rng.sample(range(n), rng.randint(1, min(2, n)))))
    q = Query(rng.choice(QUANTIFIERS), rpred(rng, n) if rng.random() < 0.85 else Pred.false(), iv,
              rng.choice([0, 1, 2, 4]), rpred(rng, n))
    return net, q


def test_all_backends_agree_with_reference():
    rng = random.Random(7)
    agree = 0
    for _ in range(300):
        net, q = random_case(rng)
        ref = reference.evaluate(net, q).answer
        rep = from_network(net)
        with BDDModel(net) as bm:
            results = [query.index_enum(rep, net, q), query.index_cube(rep, net, q),
                       query.index_sat(rep, net, q, check_proof=True),
                       query.literal_query(query.literal_successors(net), net, q), bm.answer(q)]
        for r in results:
            assert r.answer == ref, (r.backend, r.answer, ref)
            agree += 1
    assert agree == 1500


def test_witnesses_replay_and_corruptions_detected():
    rng = random.Random(8)
    seen = 0
    for _ in range(200):
        net, q = random_case(rng)
        r = query.index_sat(from_network(net), net, q)
        if r.certificate.witness_state is None:
            continue
        st, tr = r.certificate.witness_state, list(r.certificate.witness_trace)
        assert reference.replay_witness(net, q, st, tr)
        seen += 1
        # corrupted trace
        bad = list(tr)
        bad[-1] ^= 1
        assert not reference.replay_witness(net, q, st, bad)
        # quantifier swap: an exists-witness reaches the target, so it is not a forall counterexample
        swapped = Query("forall" if q.quantifier == "exists" else "exists", q.domain, q.intervention, q.horizon, q.target)
        assert not reference.replay_witness(net, swapped, st, tr)
    assert seen > 50


def test_bit_order_flip_detected():
    # a network whose answer changes if LSB/MSB order is flipped
    net = Network(2, (Rule((), 1), Rule((), 0)))           # x0 -> 1, x1 -> 0
    q = Query("forall", Pred.true(), Intervention(), 1, Pred.and_(Pred.lit(0, 1), Pred.lit(1, 0)))
    assert reference.evaluate(net, q).answer is ModelAnswer.TRUE
    flipped = Network(2, (Rule((), 0), Rule((), 1)))
    assert reference.evaluate(flipped, q).answer is ModelAnswer.FALSE
    assert query.literal_successors(net)[0] == 1           # state 0 -> state 1 (bit 0 set)


def test_resource_unknown_is_not_false():
    rng = random.Random(9)
    for _ in range(50):
        net, q = random_case(rng)
        r = query.index_cube(from_network(net), net, q, budget=1)
        if r.answer is ModelAnswer.UNKNOWN_RESOURCE:
            assert r.certificate.level.value == "none"
            return
    raise AssertionError("budget=1 never produced unknown_resource")


def test_rup_checker_rejects_bogus_proof():
    clauses = [[1, 2], [-1, 2], [1, -2], [-1, -2]]
    ok, _ = check_rup_refutation(clauses, ["2 0", "0"])
    assert ok
    ok, _ = check_rup_refutation([[1, 2], [-1, 2]], ["-2 0", "0"])   # satisfiable formula: lemma -2 not RUP
    assert not ok
