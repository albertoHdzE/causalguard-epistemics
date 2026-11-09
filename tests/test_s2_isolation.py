"""Selectors see only public evidence: swapping the hidden world (keeping the same evidence)
must leave every prediction unchanged while the hidden answers change."""
import numpy as np

from causalguard import reference
from causalguard.experiments.s2 import evaluate_budget
from causalguard.generators import World
from causalguard.schema import Evidence, Intervention, Network, Observation, Pred, Query, Rule


def test_predictions_independent_of_hidden_world():
    a = Network(3, (Rule((0, 1), 0b1000), Rule((1,), 2), Rule((2,), 1)))
    b = Network(3, (Rule((0, 1), 0b1110), Rule((1,), 2), Rule((2,), 1)))   # AND vs OR on x0'
    obs = []
    for s in (0b000, 0b011, 0b111):      # states where AND and OR agree
        fa = reference.run(a, s, Intervention(), 1)[-1]
        assert fa == reference.run(b, s, Intervention(), 1)[-1]
        obs.append(Observation(s, Intervention(), 1, tuple((i, (fa >> i) & 1) for i in range(3))))
    ev = Evidence(3, tuple(obs))
    qs = [("intervention", Query.point(0b001, 3, Intervention("initial_edit", ((2, 1),)), 1, Pred.lit(0, 1)))]
    wa = World("wa", "S2", "t", "realizable", 1, a, 2)
    wb = World("wb", "S2", "t", "realizable", 1, b, 2)
    ra = evaluate_budget(wa, ev, qs, np.random.default_rng(0))
    rb = evaluate_budget(wb, ev, qs, np.random.default_rng(0))
    for x, y in zip(ra["queries"], rb["queries"]):
        assert x["pred"] == y["pred"] and x["p_uniform"] == y["p_uniform"] and x["verdict"] == y["verdict"]
    assert ra["queries"][0]["truth"] != rb["queries"][0]["truth"]
    assert ra["queries"][0]["verdict"] == "underdetermined"
