"""Arm D's support-schema version space vs (i) the explicit candidate-class engine (versionspace) and (ii) brute
force over every network of a tiny class.  Exact integer agreement is required."""
import itertools
import random

import pytest

from causalguard import reference
from causalguard.s4.mechspace import MechanismSpace, ResourceLimit, UnsupportedClaim
from causalguard.schema import Evidence, HypothesisClass, Intervention, Observation, Pred, Query
from causalguard.versionspace import build_version_space, exact_query_counts, predict


def rand_net(rng, n, k):
    from causalguard.schema import Network, Rule
    rules = []
    for _ in range(n):
        d = rng.randint(0, k)
        ins = tuple(sorted(rng.sample(range(n), d)))
        rules.append(Rule(ins, rng.getrandbits(1 << d)))
    return Network(n, tuple(rules))


def rand_iv(rng, n):
    kind = rng.choice(["none", "initial_edit", "persistent_clamp"])
    if kind == "none":
        return Intervention("none")
    nodes = rng.sample(range(n), rng.randint(1, 2))
    return Intervention(kind, tuple((i, rng.randint(0, 1)) for i in nodes))


def rand_evidence(rng, net, B, with_iv=True, partial=False):
    n = net.n
    obs = []
    for _ in range(B):
        x = rng.randrange(1 << n)
        iv = rand_iv(rng, n) if with_iv and rng.random() < 0.3 else Intervention("none")
        clamped = {i for i, _ in iv.assign} if iv.kind == "persistent_clamp" else set()
        if len(clamped) == n:
            iv, clamped = Intervention("none"), set()
        y = reference.run(net, x, iv, 1)[-1]
        free = [j for j in range(n) if j not in clamped]
        nodes = rng.sample(free, rng.randint(1, len(free))) if partial else free
        obs.append(Observation(x, iv, 1, tuple((j, (y >> j) & 1) for j in nodes)))
    return Evidence(n, tuple(obs))


@pytest.mark.parametrize("seed", range(40))
def test_counts_equal_explicit_engine(seed):
    rng = random.Random(seed)
    n = rng.choice([3, 4, 5])
    k = rng.choice([1, 2, 3])
    net = rand_net(rng, n, k)
    ev = rand_evidence(rng, net, rng.choice([2, 4, 8]), partial=seed % 3 == 0)
    vs = build_version_space(ev, HypothesisClass(n, k))
    ms = MechanismSpace(ev, k)
    assert ms.counts() == vs.counts()
    for _ in range(6):
        q = Query.point(rng.randrange(1 << n), n, rand_iv(rng, n), rng.choice([1, 2, 3]),
                        Pred.lit(rng.randrange(n), rng.randint(0, 1)))
        cc = ms.claim_counts(q)
        assert (cc.num, cc.den) == exact_query_counts(vs, q), (seed, q)
        for want in (1, 0):
            w = ms.witness(q, want)
            has = (cc.num > 0) if want else (cc.num < cc.den)
            assert (w is not None) == has
            if w is not None:
                assert reference.consistent(w, ev)                         # independent replay
                assert bool(predict(w, q)) == bool(want)


def test_every_two_node_network_brute_force():
    """Every 2-node network with k=2 (all 16^2 networks), every one-step evidence prefix of a fixed schedule."""
    n, k = 2, 2
    nets = list(reference.all_bounded_networks(n, k))
    assert len(nets) == 256
    rng = random.Random(7)
    for truth in nets[::5]:
        ev = rand_evidence(rng, truth, rng.choice([1, 2, 3]), with_iv=True)
        compat = [m for m in nets if reference.consistent(m, ev)]
        ms = MechanismSpace(ev, k)
        assert ms.size() == len(compat)
        for x, h, t, c in itertools.product(range(4), (1, 2, 3), range(2), (0, 1)):
            for iv in (Intervention("none"), Intervention("persistent_clamp", ((1 - t, 1),)),
                       Intervention("initial_edit", ((t, 1),))):
                q = Query.point(x, n, iv, h, Pred.lit(t, c))
                num = sum(1 for m in compat if predict(m, q))
                cc = ms.claim_counts(q)
                assert (cc.num, cc.den) == (num, len(compat))


def test_inconsistent_evidence_is_empty_and_unsupported_claims_refuse():
    n = 3
    o1 = Observation(0, Intervention("none"), 1, ((0, 1),))
    o2 = Observation(0, Intervention("none"), 1, ((0, 0),))
    ms = MechanismSpace(Evidence(n, (o1, o2)), 2)
    assert ms.empty and ms.size() == 0
    clamp_bad = Observation(0, Intervention("persistent_clamp", ((1, 1),)), 1, ((1, 0),))
    assert MechanismSpace(Evidence(n, (clamp_bad,)), 2).empty
    with pytest.raises(UnsupportedClaim):
        MechanismSpace(Evidence(n, (Observation(0, Intervention("none"), 2, ((0, 1),)),)), 2)
    ms2 = MechanismSpace(Evidence(n, (o1,)), 2)
    with pytest.raises(UnsupportedClaim):
        ms2.claim_counts(Query.point(0, n, Intervention("none"), 1, Pred.and_(Pred.lit(0, 1), Pred.lit(1, 1))))
    with pytest.raises(UnsupportedClaim):
        ms2.claim_counts(Query.point(0, n, Intervention("none"), 4, Pred.lit(0, 1)))


def test_h3_enumeration_cap_is_a_resource_refusal():
    n, k = 6, 2
    ms = MechanismSpace(Evidence(n, (Observation(0, Intervention("none"), 1, ((0, 1),)),)), k, max_enum=8)
    with pytest.raises(ResourceLimit):
        ms.claim_counts(Query.point(5, n, Intervention("none"), 3, Pred.lit(0, 1)))


def test_no_op_intervention_and_duplicate_observations():
    rng = random.Random(3)
    n, k = 4, 2
    net = rand_net(rng, n, k)
    ev = rand_evidence(rng, net, 5, with_iv=False)
    dup = Evidence(n, ev.observations + ev.observations)
    assert MechanismSpace(dup, k).counts() == MechanismSpace(ev, k).counts()
    ms = MechanismSpace(ev, k)
    x = 0b0101
    # initial_edit that sets a node to the value it already has is a no-op on the claim
    same = Intervention("initial_edit", ((0, x & 1),))
    for h in (1, 2, 3):
        a = ms.claim_counts(Query.point(x, n, Intervention("none"), h, Pred.lit(2, 1)))
        b = ms.claim_counts(Query.point(x, n, same, h, Pred.lit(2, 1)))
        assert (a.num, a.den) == (b.num, b.den)


def test_scales_without_materialization():
    """n=20, k=3: the candidate-class engine would need 2^20-column tables per candidate; D does not."""
    rng = random.Random(11)
    n, k = 20, 3
    net = rand_net(rng, n, k)
    ev = rand_evidence(rng, net, 16, with_iv=False)
    ms = MechanismSpace(ev, k)
    assert ms.size() > 0
    for h in (1, 2):
        cc = ms.claim_counts(Query.point(rng.randrange(1 << n), n, Intervention("none"), h, Pred.lit(3, 1)))
        assert 0 <= cc.num <= cc.den == ms.size()
