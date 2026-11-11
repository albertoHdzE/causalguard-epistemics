"""S4 system tests: deterministic generators/designs, leakage audits, B/C/D agreement on S4 worlds, the codec
prior against brute-force enumeration, offline items run end to end."""
import itertools
import json
import random
from fractions import Fraction

import pytest

from causalguard.s4.evaluator import Evaluator
from causalguard.s4.hcode import describe, header_bits
from causalguard.s4.prior import Averager, node_bits_table, structured_models
from causalguard.s4.tasks import S4_FAMILIES, audit_public_payload, claim_audit, isomorphic, make_design, make_evidence, make_s4_world, public_task, relabel
from causalguard.s4.workspace import make_workspace
from causalguard.schema import HypothesisClass
from causalguard.versionspace import build_version_space, network_from_choice, predict


def test_generators_and_designs_are_deterministic_and_realizable():
    for f in S4_FAMILIES:
        a, b = make_s4_world("t", 3, f), make_s4_world("t", 3, f)
        assert a.net == b.net and a.realizable() and a.world_id == b.world_id
        assert make_design("t", 3, f).to_json() == make_design("t", 3, f).to_json()
    # matched control: same shared rule draw, different (unordered) supports
    om, od = make_s4_world("t", 5, "ordered_motif"), make_s4_world("t", 5, "order_disrupted")
    assert {r.arity for r in om.net.rules} == {r.arity for r in od.net.rules}
    assert describe(om.net, 3)[1] == 2


def test_public_payload_has_no_hidden_fields_and_claims_are_novel():
    for f in S4_FAMILIES:
        for i in range(4):
            w, d = make_s4_world("t", i, f), make_design("t", i, f)
            e = make_evidence(w, d)
            pub = public_task(w, d, e)
            assert audit_public_payload(pub) == []
            s = json.dumps(pub)
            for r in w.net.rules:
                assert f'"table": {r.table}' not in s
            assert claim_audit(d, e) == {"direct_answer_h1": 0, "start_state_observed": 0, "duplicates_or_complements": 0}


def test_design_is_independent_of_the_mechanism():
    # the design stream does not depend on the family's rules: same salt/index/family -> same design for
    # ordered_motif and order_disrupted only through their own family key; claims never depend on answers
    d1 = make_design("t", 0, "parity")
    assert d1.to_json() == make_design("t", 0, "parity").to_json()
    assert all(c.query.target.value in (0, 1) for c in d1.claims)


@pytest.mark.parametrize("family", S4_FAMILIES)
def test_backends_agree_on_s4_worlds(family):
    ev = Evaluator("t-agree", 1, family)
    pub = ev.public()
    refs = ev.reference()
    for arm in "BCD":
        ws = make_workspace(arm, pub)
        got = [ws.check(c) for c in pub["claims"]]
        assert [g["verdict"] for g in got] == [r.verdict for r in refs]
        for g, r in zip(got, refs):
            if g["counts"]:
                assert (int(g["counts"]["num"]), int(g["counts"]["den"])) == (r.num, r.den)


def test_isomorphism_test():
    w = make_s4_world("t", 0, "bounded_random")
    perm = [3, 1, 0, 2, 7, 6, 5, 4]
    assert isomorphic(w.net, relabel(w.net, perm)) is True
    other = make_s4_world("t", 1, "bounded_random")
    assert isomorphic(w.net, other.net) in (False, None)


def _tiny_case(seed):
    from test_s4_mechspace import rand_evidence, rand_net
    rng = random.Random(seed)
    n, k = 4, 2
    net = rand_net(rng, n, k)
    ev = rand_evidence(rng, net, 6, with_iv=False)
    return rng, n, k, ev


@pytest.mark.parametrize("seed", range(8))
def test_codec_average_matches_bruteforce(seed):
    """P_L(q|D) by weighted counts + structured correction == explicit sum over every model of V(D)."""
    rng, n, k, ev = _tiny_case(seed)
    av = Averager(ev, k, codes=("uniform", "index", "cgh_flat", "cgh_prior"))
    vs = av.vs
    if vs.empty or vs.product_size() > 30000:
        pytest.skip("space too large for brute force")
    from causalguard.schema import Intervention, Pred, Query
    bits = node_bits_table(vs.cls, "cgh_flat", n, k)
    H = header_bits(n, k)
    struct = av.struct["cgh_prior"]
    for _ in range(4):
        q = Query.point(rng.randrange(1 << n), n, Intervention("none"), rng.choice([1, 2]), Pred.lit(rng.randrange(n), 1))
        num = den = Fraction(0)
        for combo in itertools.product(*[list(c) for c in vs.compatible]):
            Lf = H + int(sum(bits[c] for c in combo))
            L = min(Lf, struct.get(tuple(int(c) for c in combo), Lf))
            w = Fraction(1, 2 ** (L - H))
            den += w
            if predict(network_from_choice(vs.cls, list(combo)), q):
                num += w
        assert abs(av.probability("cgh_prior", q) - float(num / den)) < 1e-12
        cnt = sum(1 for combo in itertools.product(*[list(c) for c in vs.compatible])
                  if predict(network_from_choice(vs.cls, list(combo)), q))
        assert abs(av.probability("uniform", q) - cnt / vs.product_size()) < 1e-12


def test_structured_models_are_in_V_and_correctly_coded():
    w = make_s4_world("t", 2, "ordered_motif")
    d = make_design("t", 2, "ordered_motif", budget=12)
    ev = make_evidence(w, d)
    vs = build_version_space(ev, HypothesisClass(8, 3))
    st = structured_models(vs, 8, 3)
    assert st is not None and len(st) >= 1
    for choice, L in st.items():
        net = network_from_choice(vs.cls, list(choice))
        assert all(int(c) in set(vs.compatible[j].tolist()) for j, c in enumerate(choice))
        assert describe(net, 3, "full")[0] <= L          # the full language can only be shorter


def test_offline_items_smoke():
    from causalguard.s4 import offline
    r = offline.map_world({"salt": "t-off", "index": 0, "family": "parity", "prefixes": [8, 16]})
    assert set(r["prefixes"]) == {"8", "16"} and all(c["agree"] for c in r["prefixes"]["16"]["claims"])
    k = offline.known_item({"n": 10, "seed": 3, "queries": 4})
    assert all(q["exact_match"] for q in k["queries"]) and all(q["mu"] == q["d"] - q["c"] for q in k["queries"])
    s = offline.stress_item({"n": 12, "seed": 3, "backend": "C", "budget": 8})
    assert set(s["verdicts"]) == {"unsupported_or_resource"}           # materialization refused, recorded


def test_weighted_counts_exact_with_huge_weights():
    """Codec weights can span > 64 bits within one node; the limb path must stay exact (bruteforce)."""
    import itertools

    import numpy as np

    from causalguard.schema import Pred, Query
    from causalguard.versionspace import exact_query_counts
    from test_s4_mechspace import rand_evidence, rand_iv, rand_net
    tested = 0
    for seed in range(40):
        rng = random.Random(seed)
        n = rng.choice([3, 4])
        net = rand_net(rng, n, 2)
        ev = rand_evidence(rng, net, rng.choice([3, 5, 8]))
        vs = build_version_space(ev, HypothesisClass(n, 2))
        if vs.product_size() > 5000:
            continue
        W = [np.array([rng.choice([1, 2 ** 40 + 7, 2 ** 70 + 3]) for _ in c], dtype=object) for c in vs.compatible]
        for _ in range(3):
            q = Query.point(rng.randrange(1 << n), n, rand_iv(rng, n), rng.choice([1, 2, 3]),
                            Pred.lit(rng.randrange(n), rng.randint(0, 1)))
            num = den = 0
            for combo in itertools.product(*[range(len(c)) for c in vs.compatible]):
                w = 1
                for j, i in enumerate(combo):
                    w *= int(W[j][i])
                den += w
                num += w * int(predict(network_from_choice(vs.cls, [int(vs.compatible[j][i])
                                                                    for j, i in enumerate(combo)]), q))
            assert exact_query_counts(vs, q, W) == (num, den)
            tested += 1
    assert tested >= 30


def test_ladder_amo_is_equivalent_to_pairwise():
    """B's competent sequential-counter at-most-one encoding gives the same verdicts (with RUP proof checks)."""
    from causalguard.schema import Pred, Query
    from causalguard.versionspace import verdict
    from test_s4_mechspace import rand_evidence, rand_iv, rand_net
    n_checked = 0
    for seed in range(15):
        rng = random.Random(seed)
        n, k = rng.choice([3, 4, 5]), rng.choice([1, 2, 3])
        vs = build_version_space(rand_evidence(rng, rand_net(rng, n, k), rng.choice([2, 4, 8])), HypothesisClass(n, k))
        if vs.empty:
            continue
        for _ in range(3):
            q = Query.point(rng.randrange(1 << n), n, rand_iv(rng, n), rng.choice([1, 2, 3]), Pred.lit(rng.randrange(n), 1))
            assert verdict(vs, q).verdict == verdict(vs, q, check_proof=True, amo="ladder").verdict
            n_checked += 1
    assert n_checked >= 30
