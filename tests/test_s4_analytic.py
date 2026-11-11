"""Formal-paper analytic calculus: independent checks of conventions, gate one-sets, ordering transport,
deconvolution, canonical reconstruction and support locality (c vs mu)."""
import itertools
import random

import pytest

from causalguard import reference
from causalguard.codec import _gate_table
from causalguard.s4.analytic import (
    Gate,
    analytic_predictor,
    band,
    coord,
    dec,
    gate_to_rule,
    gate_value,
    gates_to_network,
    offset_family,
    one_set,
    phi,
    support_local_query,
    universe,
    vector,
    weight_class,
)


def all_gates(n):
    out = [Gate("CONST0", ()), Gate("CONST1", ())]
    for r in range(1, n + 1):
        out += [Gate("COPY", (r,), (r,)), Gate("NOT", (r,), (r,))]
    for d in (2, 3):
        for I in itertools.combinations(range(1, n + 1), d):
            out += [Gate(f, I) for f in ("AND", "OR", "NAND", "NOR", "XOR", "XNOR", "MAJORITY_STRICT")]
            out += [Gate("KOFN", I, (k,)) for k in range(1, d + 1)] + [Gate("EXACTK", I, (k,)) for k in range(d + 1)]
            out += [Gate("CANALIZING", I, (I[0], cv, o, Gate("XOR", I[1:]))) for cv in (0, 1) for o in (0, 1)]
        for a, b in itertools.permutations(range(1, n + 1), 2):
            out += [Gate("IMPLIES", (a, b), (a, b)), Gate("NIMPLIES", (a, b), (a, b))]
    return out


def test_orderings_and_involution():
    n = 4
    assert vector(1, n, "LSB") == (0, 0, 0, 0) and vector(2, n, "LSB") == (1, 0, 0, 0)
    assert vector(2, n, "MSB") == (0, 0, 0, 1)
    for j in universe(n):
        assert phi(phi(j, n), n) == j
        assert vector(phi(j, n), n, "MSB") == vector(j, n, "LSB")     # e_MSB(phi(j)) = e_LSB(j)
    assert band(1, 1, 3) == frozenset({2, 4, 6, 8})                    # periodic bit band, LSB


@pytest.mark.parametrize("n", [3, 4])
def test_one_sets_match_direct_semantics_and_transport(n):
    for g in all_gates(n):
        J = one_set(g, n, "LSB")
        assert J == frozenset(j for j in universe(n) if gate_value(g, vector(j, n, "LSB")) == 1), g
        Jm = one_set(g, n, "MSB")
        assert Jm == frozenset(phi(j, n) for j in J), g                # Theorem: J^MSB = phi(J^LSB)


def test_gate_tables_match_independent_codec_tables():
    n = 4
    for g, cf, p in [("AND", "AND", 0), ("OR", "OR", 0), ("XOR", "XOR", 0), ("XNOR", "XNOR", 0), ("NOR", "NOR", 0)]:
        for I in itertools.combinations(range(1, n + 1), 3):
            assert gate_to_rule(Gate(g, I), n).table == _gate_table(cf, 3, p)
    for k in (1, 2, 3):
        assert gate_to_rule(Gate("KOFN", (1, 2, 3), (k,)), n).table == _gate_table("KOFN", 3, k)
    assert gate_to_rule(Gate("MAJORITY_STRICT", (1, 2, 3)), n).table == _gate_table("MAJORITY", 3)
    # IMPLIES(a=1st, b=2nd) == codec param 0
    assert gate_to_rule(Gate("IMPLIES", (1, 2), (1, 2)), n).table == _gate_table("IMPLIES", 2, 0)


def test_strict_majority_is_floor_plus_one_not_ceil():
    n, I = 4, (1, 2, 3, 4)
    strict = one_set(Gate("MAJORITY_STRICT", I), n)
    ceil_version = one_set(Gate("KOFN", I, (2,)), n)        # the manuscript's k = ceil(d/2) at d = 4
    tie_states = weight_class(I, 2, n)
    assert strict == one_set(Gate("KOFN", I, (3,)), n)
    assert ceil_version - strict == tie_states and len(tie_states) == 6
    for d in (3, 5):                                         # odd arity: the two coincide
        J = tuple(range(1, d + 1))
        assert one_set(Gate("MAJORITY_STRICT", J), d) == one_set(Gate("KOFN", J, ((d + 1) // 2,)), d)


def test_deconvolution_recovers_query_set():
    n = 5
    gates = [Gate("AND", (1, 2)), Gate("XOR", (2, 3)), Gate("NOT", (4,), (4,)), Gate("CONST0", ()),
             Gate("OR", (1, 3))]
    J = one_set(gates[0], n) & (frozenset(universe(n)) - one_set(gates[1], n))
    C = {1, 2, 3}
    F = tuple(i for i in range(1, n + 1) if i not in C)
    L0 = frozenset(j for j in J if all(coord(j, k, n) == 0 for k in F))
    assert dec(L0, offset_family(F, n)) == J


def test_support_locality_counts_c_and_mu_separately():
    n = 6
    gates = [Gate("AND", (1, 2)), Gate("XOR", (2, 3))] + [Gate("CONST0", ())] * 4
    r = support_local_query(gates, {1: 1, 2: 0}, n)
    assert (r.c, r.d, r.mu, r.enumerated, r.reduction_vs_independent, r.reduction_vs_global) == (3, 4, 1, 8, 2, 8)
    brute = sum(1 for j in universe(n) if gate_value(gates[0], vector(j, n)) == 1 and gate_value(gates[1], vector(j, n)) == 0)
    assert r.count == brute == 1 * 8          # one support assignment (1,1,1) x 2^(n-c) free fillings
    # disjoint supports: mu = 0, no reduction relative to independent enumeration
    g2 = [Gate("AND", (1, 2)), Gate("OR", (3, 4))] + [Gate("CONST0", ())] * 4
    r2 = support_local_query(g2, {1: 1, 2: 1}, n)
    assert r2.mu == 0 and r2.enumerated == 16 and r2.reduction_vs_independent == 1


def test_support_locality_resource_refusal():
    n = 30
    gates = [Gate("XOR", tuple(range(1, 26)))] + [Gate("CONST0", ())] * 29
    with pytest.raises(ResourceWarning):
        support_local_query(gates, {1: 1}, n, max_support=22)


@pytest.mark.parametrize("seed", range(5))
def test_canonical_exact_reconstruction_against_reference(seed):
    rng = random.Random(seed)
    n = 5
    pool = all_gates(n)
    gates = [rng.choice(pool) for _ in range(n)]
    Y = analytic_predictor(gates, n)
    net = gates_to_network(gates, n)
    for j in universe(n):
        x = j - 1
        assert Y[j - 1] == tuple(reference.step_bits(net, reference.to_bits(x, n)))
