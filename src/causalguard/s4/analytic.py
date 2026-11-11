"""Analytic index-set calculus (port of the formal method paper; independent implementation).

Source (pinned in docs/S4_METHOD_COVERAGE.md): CausalBool papers/method/manuscript_formal/method_paper.tex,
sha256 04ea352c..., "Causal Index-Set Calculus for Boolean Networks and Deterministic Reconstruction".
No upstream code is copied; definitions are re-derived from the manuscript text and cross-checked against the
sprint repository's independent gate tables (codec._gate_table) and the reference evaluator.

Conventions (checked in tests/test_s4_analytic.py):
* Index universe U = {1, ..., 2^n} (1-based, as in the paper).  LSB-first: v(j) = Reverse(IntegerDigits(j-1, 2, n)),
  i.e. coordinate i (1-based) of state j is bit (i-1) of (j-1).  MSB-first: v(j) = IntegerDigits(j-1, 2, n), i.e.
  coordinate i is bit (n-i) of (j-1).  The bit-reversal involution phi maps an LSB index to the MSB index of the
  same vector (Theorem "Ordering-Transform Invariance": J^MSB = phi(J^LSB)).
* Internally the sprint repository's states are 0-based ints with node i (0-based) = bit i; this equals the paper's
  LSB-first ordering with j = state + 1 and coordinate i+1.
* Strict majority on d inputs is weight >= floor(d/2)+1.  The paper's sentence "k = ceil(|I|/2)" includes ties
  when d is even (e.g. d=4: ceil = 2 accepts weight 2); the strict four-input example needs k = 3.  Both are
  available here under distinct names (MAJORITY_STRICT, KOFN with k = ceil(d/2)) and are never conflated.
* Support locality (Proposition "Support Locality", Corollary "Exact Reduction From Shared Inputs"): an exact
  query over queried nodes Q enumerates at most 2^c assignments, c = |C_q|, C_q = union of N_i.  With
  d = sum |N_i| and mu = d - c, 2^mu is the REDUCTION FACTOR relative to independently enumerating 2^d local
  assignments; it is NOT the remaining count.  The paper's discussion shorthand "from 2^{d_q} to 2^{mu_q}" is
  therefore not used; ``support_local_query`` reports c, d, mu and the actual enumerated count separately.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

from ..schema import Network, Rule, SemanticsError

ORDERINGS = ("LSB", "MSB")


# --------------------------------------------------------------------------- repertoire and orderings

def coord(j: int, i: int, n: int, ordering: str = "LSB") -> int:
    """v_i(j): value of 1-based coordinate i in the 1-based repertoire index j."""
    if not (1 <= j <= 1 << n and 1 <= i <= n):
        raise SemanticsError("index/coordinate out of range")
    if ordering == "LSB":
        return ((j - 1) >> (i - 1)) & 1
    if ordering == "MSB":
        return ((j - 1) >> (n - i)) & 1
    raise SemanticsError(f"unknown ordering {ordering!r}")


def vector(j: int, n: int, ordering: str = "LSB") -> tuple[int, ...]:
    return tuple(coord(j, i, n, ordering) for i in range(1, n + 1))


def phi(j: int, n: int) -> int:
    """Bit-reversal involution on U (1-based)."""
    x = j - 1
    r = 0
    for b in range(n):
        r |= ((x >> b) & 1) << (n - 1 - b)
    return r + 1


def universe(n: int) -> range:
    return range(1, (1 << n) + 1)


# --------------------------------------------------------------------------- index-set families

def band(i: int, a: int, n: int, ordering: str = "LSB") -> frozenset[int]:
    """B_i^a = {j in U : v_i(j) = a}."""
    return frozenset(j for j in universe(n) if coord(j, i, n, ordering) == a)


def parity_class(I: tuple[int, ...], r: int, n: int, ordering: str = "LSB") -> frozenset[int]:
    return frozenset(j for j in universe(n) if sum(coord(j, i, n, ordering) for i in I) % 2 == r)


def weight_class(I: tuple[int, ...], r: int, n: int, ordering: str = "LSB") -> frozenset[int]:
    return frozenset(j for j in universe(n) if sum(coord(j, i, n, ordering) for i in I) == r)


def bit_weight(i: int, n: int, ordering: str = "LSB") -> int:
    return 1 << (i - 1) if ordering == "LSB" else 1 << (n - i)


def dec(L, S) -> frozenset[int]:
    """Deconvolution operator Dec(L, S) = {l + s}."""
    return frozenset(a + b for a in L for b in S)


def offset_family(F: tuple[int, ...], n: int, ordering: str = "LSB") -> frozenset[int]:
    """Omega(F): all offsets sum_{t in F} eta_t w(t)."""
    out = set()
    for eta in itertools.product((0, 1), repeat=len(F)):
        out.add(sum(e * bit_weight(t, n, ordering) for e, t in zip(eta, F)))
    return frozenset(out)


# --------------------------------------------------------------------------- gate one-sets (Proposition 1)

GATE_FAMILIES = ("CONST0", "CONST1", "COPY", "NOT", "AND", "OR", "NAND", "NOR", "XOR", "XNOR", "IMPLIES", "NIMPLIES",
                 "KOFN", "EXACTK", "MAJORITY_STRICT", "CANALIZING")
# TABLE: an explicit local table over ordered inputs.  NOT a paper family: used only as a canalizing fallback so
# that nested canalizing rules can be built recursively (CGH-1 catalogue construction).
AUX_FAMILIES = ("TABLE",)


@dataclass(frozen=True)
class Gate:
    """A local analytic rule over an ordered connected-input set (1-based coordinates).

    params: IMPLIES/NIMPLIES -> (a, b) ordered pair of inputs; KOFN/EXACTK -> (k,); NOT/COPY -> (r,);
    CANALIZING -> (trigger_input, trigger_value, trigger_output, fallback Gate)."""
    family: str
    inputs: tuple[int, ...]
    params: tuple = ()


def one_set(g: Gate, n: int, ordering: str = "LSB") -> frozenset[int]:
    """J_k for gate g by the paper's set formulas (bands / parity / weight classes / canalizing union)."""
    U = frozenset(universe(n))
    I = g.inputs
    f = g.family
    if f == "CONST0":
        return frozenset()
    if f == "CONST1":
        return U
    if f in ("COPY", "NOT"):
        (r,) = g.params or I
        return band(r, 1 if f == "COPY" else 0, n, ordering)
    if f == "AND":
        return frozenset.intersection(*[band(i, 1, n, ordering) for i in I])
    if f == "OR":
        return frozenset.union(*[band(i, 1, n, ordering) for i in I])
    if f == "NAND":
        return U - one_set(Gate("AND", I), n, ordering)
    if f == "NOR":
        return frozenset.intersection(*[band(i, 0, n, ordering) for i in I])
    if f == "XOR":
        return parity_class(I, 1, n, ordering)
    if f == "XNOR":
        return parity_class(I, 0, n, ordering)
    if f == "IMPLIES":
        a, b = g.params
        return band(a, 0, n, ordering) | (band(a, 1, n, ordering) & band(b, 1, n, ordering))
    if f == "NIMPLIES":
        a, b = g.params
        return band(a, 1, n, ordering) & band(b, 0, n, ordering)
    if f == "KOFN":
        (k,) = g.params
        return frozenset().union(*[weight_class(I, r, n, ordering) for r in range(k, len(I) + 1)])
    if f == "EXACTK":
        (k,) = g.params
        return weight_class(I, k, n, ordering)
    if f == "MAJORITY_STRICT":
        return one_set(Gate("KOFN", I, (len(I) // 2 + 1,)), n, ordering)
    if f == "TABLE":
        return frozenset(j for j in universe(n) if gate_value(g, vector(j, n, ordering)) == 1)
    if f == "CANALIZING":
        r, cv, o, fb = g.params
        C = band(r, cv, n, ordering)
        Jh = one_set(fb, n, ordering)
        return C | ((U - C) & Jh) if o == 1 else (U - C) & Jh
    raise SemanticsError(f"unknown gate family {f!r}")


def gate_value(g: Gate, bits: tuple[int, ...]) -> int:
    """Direct gate semantics on a full 1-based vector (independent of one_set; used to cross-check)."""
    v = [bits[i - 1] for i in g.inputs]
    s = sum(v)
    f = g.family
    if f == "CONST0":
        return 0
    if f == "CONST1":
        return 1
    if f in ("COPY", "NOT"):
        (r,) = g.params or g.inputs
        return bits[r - 1] if f == "COPY" else 1 - bits[r - 1]
    if f == "AND":
        return int(s == len(v))
    if f == "OR":
        return int(s > 0)
    if f == "NAND":
        return int(s != len(v))
    if f == "NOR":
        return int(s == 0)
    if f == "XOR":
        return s % 2
    if f == "XNOR":
        return 1 - s % 2
    if f == "IMPLIES":
        a, b = g.params
        return int((not bits[a - 1]) or bits[b - 1])
    if f == "NIMPLIES":
        a, b = g.params
        return int(bits[a - 1] and not bits[b - 1])
    if f == "KOFN":
        return int(s >= g.params[0])
    if f == "EXACTK":
        return int(s == g.params[0])
    if f == "MAJORITY_STRICT":
        return int(2 * s > len(v))
    if f == "CANALIZING":
        r, cv, o, fb = g.params
        return o if bits[r - 1] == cv else gate_value(fb, bits)
    if f == "TABLE":
        y = sum(bits[i - 1] << t for t, i in enumerate(g.inputs))
        return (g.params[0] >> y) & 1
    raise SemanticsError(f"unknown gate family {f!r}")


def gate_to_rule(g: Gate, n: int) -> Rule:
    """Sprint-repository Rule (0-based ascending inputs, LSB local table) of a gate, built from one_set."""
    J = one_set(g, n, "LSB")
    support = sorted(_gate_support(g))
    ins = tuple(i - 1 for i in support)
    table = 0
    for y in range(1 << len(ins)):
        x = sum(((y >> t) & 1) << i for t, i in enumerate(ins))     # any state with this local pattern
        if (x + 1) in J:
            table |= 1 << y
    return Rule(ins, table)


def _gate_support(g: Gate) -> set[int]:
    s = set(g.inputs)
    if g.family in ("COPY", "NOT") and g.params:
        s |= {g.params[0]}
    if g.family in ("IMPLIES", "NIMPLIES"):
        s |= set(g.params)
    if g.family == "CANALIZING":
        s |= {g.params[0]} | _gate_support(g.params[3])
    return s


def network_one_sets(gates: list[Gate], n: int, ordering: str = "LSB") -> list[frozenset[int]]:
    return [one_set(g, n, ordering) for g in gates]


def analytic_predictor(gates: list[Gate], n: int, ordering: str = "LSB") -> list[tuple[int, ...]]:
    """Y[j-1] = output vector at repertoire index j (Theorem "Canonical Exact Reconstruction")."""
    J = network_one_sets(gates, n, ordering)
    return [tuple(int(j in Ji) for Ji in J) for j in universe(n)]


def gates_to_network(gates: list[Gate], n: int) -> Network:
    return Network(n, tuple(gate_to_rule(g, n) for g in gates))


# --------------------------------------------------------------------------- support-local query evaluation

@dataclass(frozen=True)
class SupportLocalResult:
    count: int                 # |J_q| over U (exact)
    c: int                     # |C_q|, distinct support coordinates
    d: int                     # sum of queried arities
    mu: int                    # d - c (overlap multiplicity)
    enumerated: int            # support-level assignments actually evaluated (= 2^c)
    reduction_vs_independent: int    # 2^mu (relative to 2^d independent local enumeration)
    reduction_vs_global: int         # 2^(n-c) (relative to materializing 2^n rows)
    witness_index: int | None  # one 1-based LSB index in J_q, if any


def support_local_query(gates: list[Gate], query: dict[int, int], n: int, max_support: int = 22
                        ) -> SupportLocalResult:
    """Exact mixed query J_q = cap_{i in Q+} J_i cap cap_{i in Q-} (U minus J_i) for a KNOWN mechanism, evaluated
    on the support union only (Proposition "Overlap-Supported Query Factorisation").  ``query`` maps 1-based node
    -> required output.  Never materializes U; refuses if c exceeds ``max_support`` (resource limit)."""
    Q = sorted(query)
    sup = sorted(set().union(*[_gate_support(gates[i - 1]) for i in Q])) if Q else []
    c = len(sup)
    d = sum(len(_gate_support(gates[i - 1])) for i in Q)
    if c > max_support:
        raise ResourceWarning(f"support union {c} exceeds the declared bound {max_support}")
    sat = 0
    wit = None
    for assign in itertools.product((0, 1), repeat=c):
        bits = [0] * n
        for i, a in zip(sup, assign):
            bits[i - 1] = a
        if all(gate_value(gates[i - 1], tuple(bits)) == query[i] for i in Q):
            sat += 1
            if wit is None:
                wit = 1 + sum(b << (i - 1) for i, b in enumerate(bits, start=1))
    return SupportLocalResult(sat << (n - c), c, d, d - c, 1 << c, 1 << (d - c), 1 << (n - c), wit)
