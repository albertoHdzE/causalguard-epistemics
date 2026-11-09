import itertools
import random

import pytest

from causalguard import reference
from causalguard.index_repr import (
    MATERIALIZATION_LOG,
    Family,
    MaterializationRefused,
    from_gate,
    from_network,
    from_rule,
    union_count,
)
from causalguard.schema import Network, Rule

RULE110_ON = {"110", "101", "011", "010", "001"}  # Wolfram (left,center,right) patterns with output 1


def rule110():
    # inputs (r, c, l) = nodes (0, 1, 2); local index y = r + 2c + 4l
    return Rule((0, 1, 2), sum(1 << y for y in range(8) if format(y, "03b") in RULE110_ON))


def test_rule110_schemata_on_connected_inputs():
    node = from_rule(rule110(), 3, polarity=1)
    strings = {f.schema_string((0, 1, 2)) for f in node.families}
    assert len(strings) == 3 and node.exact_cover
    for s in strings:   # every schema has a don't-care, and all three inputs are connected
        assert s.count("*") == 1
    assert set(rule110().essential_inputs()) == {0, 1, 2}
    # the upstream-cited cover {01*, 10*, *10} (LSB-first strings: char t = local input t) is a valid cover
    up = []
    for s in ("01*", "10*", "*10"):
        F = sum(1 << t for t, ch in enumerate(s) if ch != "*")
        A = sum(1 << t for t, ch in enumerate(s) if ch == "1")
        up.append(Family(F, A))
    for x in range(8):
        assert any(f.contains(x) for f in up) == bool((rule110().table >> x) & 1)
    # a method blind to connected-input don't-cares would need the 5 minterms
    assert len([y for y in range(8) if (rule110().table >> y) & 1]) == 5


def test_rule110_auto_polarity_offset_is_shorter():
    node = from_rule(rule110(), 3)
    assert node.polarity == 0 and len(node.families) == 2


@pytest.mark.parametrize("k", [2, 4, 6, 8, 10])
def test_or_vs_parity_scaling(k):
    ins = tuple(range(k))
    orr = from_gate("OR", ins, k)
    xor = from_gate("XOR", ins, k)
    assert len(orr.families) == k                      # overlapping bands
    assert len(xor.families) == 2 ** (k - 1)           # no merges possible
    assert orr.onset_count() == 2 ** k - 1             # overlap-aware: not k * 2**(k-1)
    assert sum(f.size(k) for f in orr.families) == k * 2 ** (k - 1)
    assert xor.onset_count() == 2 ** (k - 1)


def test_closed_forms_match_truth_tables():
    rng = random.Random(0)
    for _ in range(60):
        k = rng.randint(1, 6)
        n = k + rng.randint(0, 3)
        ins = tuple(sorted(rng.sample(range(n), k)))
        for g in ["AND", "OR", "NAND", "NOR", "XOR", "XNOR"] + (["COPY", "NOT"] if k == 1 else []):
            node = from_gate(g, ins, n)
            fn = {"AND": all, "OR": any, "NAND": lambda v: not all(v), "NOR": lambda v: not any(v),
                  "XOR": lambda v: sum(v) % 2 == 1, "XNOR": lambda v: sum(v) % 2 == 0,
                  "COPY": lambda v: v[0] == 1, "NOT": lambda v: v[0] == 0}[g]
            for x in range(1 << n):
                assert node.output(x) == int(bool(fn([(x >> i) & 1 for i in ins]))), (g, ins, x)
        t = rng.randint(0, k)
        kof = from_gate("KOFN", ins, n, {"t": t})
        for x in range(1 << n):
            assert kof.output(x) == int(sum((x >> i) & 1 for i in ins) >= t)


def test_canalizing_closed_form():
    levels = [(2, 1, 0), (0, 0, 1), (3, 1, 1)]
    node = from_gate("CANALIZING", (0, 2, 3), 5, {"levels": levels, "default": 0})
    for x in range(32):
        b = lambda i: (x >> i) & 1  # noqa: E731
        exp = 0 if b(2) == 1 else 1 if b(0) == 0 else 1 if b(3) == 1 else 0
        assert node.output(x) == exp
    assert union_count(list(node.families), 5) == sum(node.output(x) for x in range(32))


def test_union_count_overlap_exhaustive():
    rng = random.Random(1)
    for _ in range(200):
        n = rng.randint(1, 8)
        fams = []
        for _ in range(rng.randint(0, 6)):
            F = rng.getrandbits(n)
            fams.append(Family(F, rng.getrandbits(n) & F))
        truth = sum(1 for x in range(1 << n) if any(f.contains(x) for f in fams))
        assert union_count(fams, n) == truth


def test_from_rule_exact_on_random_rules():
    rng = random.Random(2)
    for _ in range(300):
        n = rng.randint(1, 7)
        k = rng.randint(0, min(n, 5))
        r = Rule(tuple(sorted(rng.sample(range(n), k))), rng.getrandbits(1 << k))
        for pol in ("auto", 0, 1):
            node = from_rule(r, n, pol)
            net = Network(n, tuple([r] + [Rule((), 0)] * (n - 1)))
            for x in range(1 << n):
                assert node.output(x) == reference.node_output(net, 0, reference.to_bits(x, n))


def test_network_step_matches_reference():
    rng = random.Random(3)
    for _ in range(100):
        n = rng.randint(1, 7)
        rules = []
        for _ in range(n):
            k = rng.randint(0, min(n, 3))
            rules.append(Rule(tuple(sorted(rng.sample(range(n), k))), rng.getrandbits(1 << k)))
        net = Network(n, tuple(rules))
        rep = from_network(net)
        for x in range(1 << n):
            assert rep.step(x) == reference.from_bits(reference.step_bits(net, reference.to_bits(x, n)))


def test_no_hidden_materialization_at_large_n():
    MATERIALIZATION_LOG.clear()
    node = from_gate("OR", tuple(range(0, 256, 16)), 256)
    assert node.output(1 << 32) == 1 and node.output(0) == 0
    assert node.onset_count() == 2 ** 256 - 2 ** 240
    assert MATERIALIZATION_LOG == []
    with pytest.raises(MaterializationRefused):
        list(node.families[0].offsets(256))
    with pytest.raises(MaterializationRefused):
        node.materialize_onset()
    with pytest.raises(MaterializationRefused):
        from_gate("XOR", tuple(range(40)), 64)


def test_family_intersection_semantics():
    for n in range(1, 5):
        fams = [Family(F, A) for F in range(1 << n) for A in range(1 << n) if A & ~F == 0]
        for a, b in itertools.product(fams, repeat=2):
            c = a.intersect(b)
            for x in range(1 << n):
                assert (a.contains(x) and b.contains(x)) == (c is not None and c.contains(x))
