"""Figure 4 (Appendix E.1, D128): its numbers come from the repository's objects, and its dynamics from the
production owner, cross-checked here against the independent reference semantics (reference.step_bits)."""
from causalguard.reference import step_bits
from causalguard.schema import Network, Rule
from causalguard.sprint.figures import background_data


def test_figure4_dynamics_match_independent_reference():
    B = background_data()
    r = B["rule110"]
    assert r["table"] == 110 and r["rule_bits"] == 8 and len(r["rows"]) == r["steps"] + 1
    w = r["cells"]
    net = Network(w, (Rule((), 0),) + tuple(Rule((i - 1, i, i + 1), 110) for i in range(1, w - 1)) + (Rule((), 0),))
    rows = [[int(c) for c in reversed(s)] for s in r["rows"]]       # string MSB first -> node order
    assert sum(rows[0]) == 1 and rows[0][1] == 1
    checked = 0
    for t in range(len(rows) - 1):
        assert step_bits(net, rows[t]) == rows[t + 1]
        checked += 1
    assert checked == r["steps"]
    W = B["world"]
    wn = Network(W["n"], tuple(Rule.from_json(x) for x in W["rules"]))
    assert len(W["successor"]) == W["states"] == 1 << W["n"]
    for s in range(W["states"]):
        bits = [(s >> j) & 1 for j in range(W["n"])]
        assert sum(b << j for j, b in enumerate(step_bits(wn, bits))) == W["successor"][s]
    assert W["table_bits"] == sum(1 << len(x["inputs"]) for x in W["rules"]) == 32
    assert W["behaviour_bits"] == W["n"] * W["states"]
