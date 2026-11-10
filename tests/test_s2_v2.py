"""S2 v2: exogenous design (R02), exact posterior and verdicts (R01, R07), Bayes inequality under uniform H."""
import itertools
import random
from dataclasses import replace
from fractions import Fraction

import numpy as np

from causalguard.experiments.s2 import run_world_v2
from causalguard.generators import (_full_obs, make_s2_design, make_s2_instance_v2, make_s2_world, query_novelty,
                                    s2_design_seed)
from causalguard.schema import Evidence, HypothesisClass, Intervention, Network, Observation, Pred, Query, Rule
from causalguard.versionspace import (boolean_support, build_version_space, candidate_class, exact_posterior,
                                      exact_query_counts, mc_posterior, network_from_choice, predict,
                                      select_min_code, uniform_prob_true, verdict, verdict_fast)


def _design_for(w):
    return make_s2_design(s2_design_seed("t", 0, w.family, w.population, 7, 3), 7)


def test_review_mechanism_swap_leaves_design_identical():
    """repro_s2.py, second check, inverted: same design seed, hidden zero vs identity network."""
    w = make_s2_world("t", 0, "parity")
    zero = replace(w, net=Network(7, tuple(Rule((), 0) for _ in range(7))))
    ident = replace(w, net=Network(7, tuple(Rule((j,), 2) for j in range(7))))
    d = _design_for(w)
    a, b = make_s2_instance_v2(zero, d), make_s2_instance_v2(ident, d)
    assert [o.state for o in a.evidence["uniform_states"]] == [o.state for o in b.evidence["uniform_states"]]
    assert d.to_json() == _design_for(w).to_json()           # pure function of the design seed
    assert not set(d.holdout_states) & set(d.uniform_inputs)  # holdouts reserved ex ante
    # streams are distinct and recorded
    assert d.design_seed != w.seed


def test_review_tautology_is_entailed_exactly():
    ev = Evidence(3, (Observation(0, Intervention(), 1, ((0, 1), (1, 1), (2, 0))),
                      Observation(1, Intervention(), 1, ((0, 1), (1, 0), (2, 0)))))
    vs = build_version_space(ev, HypothesisClass(3, 2))
    q = Query.point(3, 3, Intervention(), 1, Pred.or_(Pred.lit(0, 0), Pred.lit(0, 1), Pred.lit(1, 1), Pred.lit(2, 1)))
    assert verdict_fast(vs, q).value == verdict(vs, q).verdict.value == "entailed"
    assert boolean_support(vs, q) == {True}
    post = exact_posterior(vs, q)
    assert post["num"] == post["den"] and post["verdict"] == "entailed"
    # the v1 float path is kept only as a probability; it is NOT exactly 1.0 here (that was the bug)
    assert uniform_prob_true(vs, q, np.random.default_rng(0))[0] != 1.0


def _vs(n, k, net, xs, ivs=None):
    obs = [_full_obs(net, x, (ivs or {}).get(x, Intervention()), True) for x in xs]
    return build_version_space(Evidence(n, tuple(obs)), HypothesisClass(n, k))


def test_contradiction_correlated_literals_clamp_edit_horizon0_and_rare_counterexample():
    n, k = 3, 2
    w = make_s2_world("t", 5, "random_lookup", n=n, kmax=k)
    vs = _vs(n, k, w.net, [0, 5])
    x = 6
    for tgt, want in ((Pred.and_(Pred.lit(1, 0), Pred.lit(1, 1)), "refuted"),          # contradiction
                      (Pred.or_(Pred.lit(2, 1), Pred.lit(2, 0), Pred.lit(2, 1)), "entailed")):  # repeated literals
        q = Query.point(x, n, Intervention(), 1, tgt)
        assert verdict_fast(vs, q).value == verdict(vs, q).verdict.value == want
    for iv in (Intervention("initial_edit", ((0, 1),)), Intervention("persistent_clamp", ((1, 0),))):
        for h in (0, 1, 2, 3):
            q = Query.point(x, n, iv, h, Pred.lit(1, 0))
            assert verdict_fast(vs, q).value == verdict(vs, q).verdict.value
    # a genuinely possible low-probability counterexample: all nodes constant 1, 20 observations, claim
    # "x0 or x1 or x2 or x3 is 1" at an unobserved input.  Few compatible models make every disjunct false.
    net = Network(7, tuple(Rule((), 1) for _ in range(7)))
    xs = random.Random(0).sample(range(128), 20)
    vs = _vs(7, 3, net, xs)
    claim = Pred.or_(*[Pred.lit(j, 1) for j in range(4)])
    cands = [Query.point(s, 7, Intervention(), 1, claim) for s in range(128) if s not in xs]
    q, num, den = min(((c, *exact_query_counts(vs, c)) for c in cands), key=lambda t: (t[1] == t[2], (t[2] - t[1]) / t[2]))
    assert 0 < den - num and (den - num) * 1000 < den        # 0 < P(false) < 0.001
    assert verdict_fast(vs, q).value == verdict(vs, q).verdict.value == "underdetermined"
    assert boolean_support(vs, q) == {True, False}


def test_exact_counts_match_enumeration_small_classes():
    rng = random.Random(3)
    checked = 0
    for trial in range(80):
        n, k = rng.choice([(3, 1), (3, 2), (4, 1)])
        w = make_s2_world("t", trial, "random_lookup", n=n, kmax=k)
        vs = _vs(n, k, w.net, rng.sample(range(1 << n), rng.randint(1, 3)))
        if vs.product_size() > 20000:
            continue
        for _ in range(3):
            kind = rng.choice(["none", "initial_edit", "persistent_clamp"])
            iv = Intervention() if kind == "none" else Intervention(kind, ((rng.randrange(n), rng.randint(0, 1)),))
            q = Query.point(rng.randrange(1 << n), n, iv, rng.choice([1, 2, 3]),
                            Pred.or_(Pred.lit(rng.randrange(n), 1), Pred.lit(rng.randrange(n), 0)))
            vals = [predict(network_from_choice(vs.cls, list(c)), q)
                    for c in itertools.product(*[c.tolist() for c in vs.compatible])]
            assert exact_query_counts(vs, q) == (sum(vals), len(vals))
            checked += 1
    assert checked > 100


def test_mc_majority_is_labelled_and_converges():
    w = make_s2_world("t", 1, "canalizing")
    d = _design_for(w)
    inst = make_s2_instance_v2(w, d)
    vs = build_version_space(Evidence(7, tuple(inst.evidence["uniform_states"][:4])), HypothesisClass(7, 3))
    q = d.intervention_queries[5]
    ex = exact_posterior(vs, q)
    mc = mc_posterior(vs, q, 65536, np.random.default_rng(0))
    assert mc["method"] == "monte_carlo" and abs(mc["p"] - ex["p"]) < 6 * max(mc["se"], 1e-3)


def test_novelty_categories():
    w = make_s2_world("t", 2, "conjunctive")
    obs = [_full_obs(w.net, 9, Intervention(), False)]
    q_obs = Query.point(9, 7, Intervention("initial_edit", ((0, (9 >> 0) & 1),)), 1, Pred.lit(3, 1))
    nv = query_novelty(q_obs, obs, w.net)
    assert nv["category"] == "h1_observed_transition" and nv["syntactic_key_novel"]
    q_new = Query.point(100, 7, Intervention(), 2, Pred.lit(3, 1))
    assert query_novelty(q_new, obs, w.net)["category"] == "multistep_unobserved"


def test_run_world_v2_exact_verdicts_agree_with_sat():
    r = run_world_v2({"salt": "t", "index": 4, "family": "modular", "population": "realizable",
                      "design_version": "s2-design-v2", "budgets": [4, 16], "regimes": ["uniform_states"]})
    b16 = r["regimes"]["uniform_states"]["16"]
    assert b16["sat_crosscheck"] and b16["sat_mismatches"] == 0
    assert all(q["verdict"] == q["verdict_sat"] for q in b16["queries"])


def test_bayes_majority_dominates_on_average_under_uniform_H_exhaustive():
    """Exhaustive small-H average (n=3, k=1, all 512 networks) with a FIXED exogenous design: under the uniform
    prior the compatible-set majority (half-credit ties) has the highest average accuracy; random-compatible
    sampling is lower; the index selector cannot exceed majority on average, yet beats it on some worlds."""
    n, k = 3, 1
    cls = candidate_class(n, k)
    d = make_s2_design(12345, n=n, n_state_queries=2, n_int_queries=6, budget=6)
    totals = {"maj": Fraction(0), "rand": Fraction(0), "index": Fraction(0)}
    index_wins = 0
    nets = list(itertools.product(range(cls.size), repeat=n))
    for B in (1, 2, 3):
        for choice in nets:
            net = network_from_choice(cls, list(choice))
            ev = Evidence(n, tuple(_full_obs(net, x, Intervention(), False) for x in d.uniform_inputs[:B]))
            vs = build_version_space(ev, HypothesisClass(n, k))
            inet = network_from_choice(cls, select_min_code(vs, "index"))
            wm = wi = Fraction(0)
            for q in d.intervention_queries:
                t = predict(net, q)
                num, den = exact_query_counts(vs, q)
                p = Fraction(num, den)
                maj = Fraction(1, 2) if 2 * num == den else Fraction(int((2 * num > den) == t))
                wm += maj
                wi += int(predict(inet, q) == t)
                totals["maj"] += maj
                totals["rand"] += p if t else 1 - p
                totals["index"] += int(predict(inet, q) == t)
            index_wins += wi > wm
    assert totals["maj"] >= totals["index"] and totals["maj"] >= totals["rand"]
    assert totals["maj"] > totals["rand"]
    assert index_wins > 0
