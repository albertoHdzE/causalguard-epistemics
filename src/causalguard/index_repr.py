"""Index-family (schema) representation of Boolean network repertoires.

COMPATIBLE IMPLEMENTATION of the CausalBool index-set method (UPSTREAM.md):
the upstream monorepo has no top-level license, so its code is not vendored.
Parity with the pinned upstream owners (``index-deconvolution/src/deconvolution.py:
minimal_dnf`` and ``causalbool.repertoire``) is checked by
tests/test_upstream_parity.py when a pinned checkout is supplied.

Object
------
A node's on-set (or, with polarity 0, its off-set) over the n-bit state space
is a union of schema families.  A family is fixed by a mask F of constrained
coordinates and the anchor a (the decimal value of the fixed 1-bits).  Its
don't-care positions are J = [n] \\ F, which INCLUDES don't-care positions on
connected inputs (Rule 110), not merely disconnected coordinates.  The family
represents the indices a + Omega, Omega = { sum_{j in S} 2**j : S subset J }.

J is stored symbolically (as the complement of F); offsets are never
materialized unless explicitly requested under a size guard, and every
materialization is recorded in MATERIALIZATION_LOG.  Families in a union may
overlap; exact counts use overlap-aware Shannon splitting, never the sum of
family sizes.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Iterator

from .schema import Network, Rule, SemanticsError

REPRESENTATION_ID = "causalguard.index_repr/schema-families-v1"

MATERIALIZATION_LOG: list[dict] = []


class MaterializationRefused(ResourceWarning):
    pass


@dataclass(frozen=True, order=True)
class Family:
    """Schema family over n coordinates: {x : x & fixed == anchor}."""
    fixed: int
    anchor: int

    def __post_init__(self):
        if self.anchor & ~self.fixed:
            raise SemanticsError("anchor has bits outside the fixed mask")

    def contains(self, x: int) -> bool:
        return (x & self.fixed) == self.anchor

    def dont_care_mask(self, n: int) -> int:
        return ((1 << n) - 1) & ~self.fixed

    def size(self, n: int) -> int:
        return 1 << (n - bin(self.fixed).count("1"))

    def intersect(self, other: "Family") -> "Family | None":
        if (self.anchor ^ other.anchor) & self.fixed & other.fixed:
            return None
        return Family(self.fixed | other.fixed, self.anchor | other.anchor)

    def offsets(self, n: int, limit: int = 1 << 16) -> Iterator[int]:
        """Lazily enumerate Omega (guarded)."""
        J = [j for j in range(n) if not (self.fixed >> j) & 1]
        if len(J) >= 63 or (1 << len(J)) > limit:
            raise MaterializationRefused(f"|Omega|=2**{len(J)} exceeds limit {limit}")
        MATERIALIZATION_LOG.append({"what": "offsets", "n": n, "count": 1 << len(J)})
        for z in range(1 << len(J)):
            off = 0
            for t, j in enumerate(J):
                if (z >> t) & 1:
                    off |= 1 << j
            yield off

    def schema_string(self, positions: tuple[int, ...]) -> str:
        """Schema over the given coordinates, character t = coordinate positions[t]
        (LSB-first string order), '*' for don't-care."""
        out = []
        for p in positions:
            if (self.fixed >> p) & 1:
                out.append(str((self.anchor >> p) & 1))
            else:
                out.append("*")
        return "".join(out)


# --------------------------------------------------------------------------- Quine-McCluskey (local)

def prime_implicants(minterms: list[int], k: int) -> list[tuple[int, int]]:
    """All prime implicants of the set of local minterms over k variables,
    as (fixed mask, value) pairs.  Compatible with upstream minimal_dnf's
    merge step (same merge rule; tested for parity)."""
    full = (1 << k) - 1
    terms = {(full, y) for y in minterms}
    primes: set[tuple[int, int]] = set()
    while terms:
        merged = set()
        used = set()
        by_mask: dict[int, list[int]] = {}
        for m, v in terms:
            by_mask.setdefault(m, []).append(v)
        for m, vals in by_mask.items():
            vs = set(vals)
            for v in vals:
                for b in range(k):
                    bit = 1 << b
                    if (m & bit) and not (v & bit) and (v | bit) in vs:
                        merged.add((m & ~bit, v))
                        used.add((m, v))
                        used.add((m, v | bit))
        primes |= terms - used
        terms = merged
    return sorted(primes)


def _covers(p: tuple[int, int], y: int) -> bool:
    return (y & p[0]) == p[1]


def minimum_cover(minterms: list[int], primes: list[tuple[int, int]], node_budget: int = 200000
                  ) -> tuple[list[tuple[int, int]], bool]:
    """Exact minimum cover by (count, total literals); branch and bound.

    Returns (cover, exact).  If the search budget is exhausted the best cover
    found is returned with exact=False (recorded by the caller)."""
    if not minterms:
        return [], True
    cov = {p: frozenset(y for y in minterms if _covers(p, y)) for p in primes}
    lits = {p: bin(p[0]).count("1") for p in primes}

    def cost(sel):
        return (len(sel), sum(lits[p] for p in sel))

    # greedy upper bound
    unc = set(minterms)
    greedy = []
    while unc:
        best = max(primes, key=lambda p: (len(cov[p] & unc), -lits[p], p))
        greedy.append(best)
        unc -= cov[best]
    best_sel = list(greedy)
    best_cost = cost(best_sel)
    nodes = 0
    exhausted = False

    def rec(unc: frozenset, sel: list):
        nonlocal best_sel, best_cost, nodes, exhausted
        nodes += 1
        if nodes > node_budget:
            exhausted = True
            return
        if not unc:
            c = cost(sel)
            if c < best_cost:
                best_cost, best_sel = c, list(sel)
            return
        if len(sel) + 1 > best_cost[0]:
            return
        # lower bound: ceil(|unc| / max cover size)
        mx = max(len(cov[p] & unc) for p in primes)
        if len(sel) + math.ceil(len(unc) / mx) > best_cost[0]:
            return
        # branch on the uncovered minterm with fewest options
        y = min(unc, key=lambda t: sum(1 for p in primes if t in cov[p]))
        opts = sorted((p for p in primes if y in cov[p]), key=lambda p: (-len(cov[p] & unc), lits[p], p))
        for p in opts:
            sel.append(p)
            rec(unc - cov[p], sel)
            sel.pop()
            if exhausted:
                return

    rec(frozenset(minterms), [])
    return sorted(best_sel), not exhausted


# --------------------------------------------------------------------------- node representation

@dataclass(frozen=True)
class NodeIndex:
    """Node function: output = polarity if x in union(families) else 1 - polarity."""
    n: int
    polarity: int
    families: tuple[Family, ...]
    connected: tuple[int, ...]           # declared connected inputs (metadata)
    exact_cover: bool = True             # whether the cover search was exhaustive
    construction: str = "local_table"

    def output(self, x: int) -> int:
        for f in self.families:
            if (x & f.fixed) == f.anchor:
                return self.polarity
        return 1 - self.polarity

    def covered_count(self, budget: int = 1 << 20) -> int:
        return union_count(list(self.families), self.n, budget)

    def onset_count(self, budget: int = 1 << 20) -> int:
        c = self.covered_count(budget)
        return c if self.polarity == 1 else (1 << self.n) - c

    def materialize_onset(self, limit: int = 1 << 20) -> list[int]:
        if self.n > 30 or (1 << self.n) > limit:
            raise MaterializationRefused(f"repertoire 2**{self.n} exceeds limit {limit}")
        MATERIALIZATION_LOG.append({"what": "onset", "n": self.n, "count": 1 << self.n})
        return [x for x in range(1 << self.n) if self.output(x) == 1]

    def to_rule(self) -> Rule:
        """Local rule over declared connected inputs (exhaustive over 2**k)."""
        ins = self.connected
        table = 0
        for y in range(1 << len(ins)):
            x = 0
            for t, i in enumerate(ins):
                if (y >> t) & 1:
                    x |= 1 << i
            table |= self.output(x) << y
        return Rule(ins, table)


def union_count(fams: list[Family], n: int, budget: int = 1 << 20) -> int:
    """Exact |union of families| by Shannon splitting (overlap aware).

    Raises ResourceWarning if more than ``budget`` recursion nodes are needed."""
    counter = [0]

    def rec(fs: list[Family], free: int) -> int:
        # free = mask of coordinates not yet split on
        counter[0] += 1
        if counter[0] > budget:
            raise ResourceWarning("union_count budget exceeded")
        if not fs:
            return 0
        nfree = bin(free).count("1")
        for f in fs:
            if f.fixed & free == 0:
                return 1 << nfree
        if len(fs) == 1:
            return 1 << (nfree - bin(fs[0].fixed & free).count("1"))
        # split on the coordinate fixed by most families
        best, bestc = -1, -1
        m = free
        while m:
            low = m & -m
            c = sum(1 for f in fs if f.fixed & low)
            if c > bestc:
                best, bestc = low, c
            m ^= low
        tot = 0
        for val in (0, best):
            sub = []
            for f in fs:
                if f.fixed & best and (f.anchor & best) != val:
                    continue
                sub.append(Family(f.fixed & ~best, f.anchor & ~best))
            tot += rec(sub, free & ~best)
        return tot

    return rec(list(fams), (1 << n) - 1)


def _lift(local: tuple[int, int], inputs: tuple[int, ...]) -> Family:
    m, v = local
    F = A = 0
    for t, i in enumerate(inputs):
        if (m >> t) & 1:
            F |= 1 << i
            if (v >> t) & 1:
                A |= 1 << i
    return Family(F, A)


def from_rule(rule: Rule, n: int, polarity: str | int = "auto", cover_budget: int = 20000) -> NodeIndex:
    """Index representation of a local rule, lifted to the n-bit space.

    polarity='auto' chooses the polarity with fewer families (then fewer
    literals; ties -> on-set).  Every schema's don't-cares are kept, whether
    they fall on connected or disconnected coordinates."""
    k = rule.arity
    if rule.inputs and rule.inputs[-1] >= n:
        raise SemanticsError("rule reads a node outside n")
    on = [y for y in range(1 << k) if (rule.table >> y) & 1]
    off = [y for y in range(1 << k) if not (rule.table >> y) & 1]
    options = []
    for pol, mts in ((1, on), (0, off)):
        if polarity != "auto" and pol != int(polarity):
            continue
        cover, exact = minimum_cover(mts, prime_implicants(mts, k), cover_budget)
        lits = sum(bin(m).count("1") for m, _ in cover)
        options.append(((len(cover), lits, -pol), pol, cover, exact))
    options.sort(key=lambda t: t[0])
    _, pol, cover, exact = options[0]
    fams = tuple(sorted(_lift(c, rule.inputs) for c in cover))
    return NodeIndex(n, pol, fams, rule.inputs, exact, "local_table")


# --------------------------------------------------------------------------- closed-form gate families

GATE_FAMILIES = ("AND", "OR", "NAND", "NOR", "XOR", "XNOR", "KOFN", "CANALIZING", "COPY", "NOT",
                 "CONST0", "CONST1")


def from_gate(gate: str, inputs: tuple[int, ...], n: int, params: dict | None = None,
              max_families: int = 1 << 16) -> NodeIndex:
    """Closed-form index families for named gate families (no truth table).

    Allows in-degrees far beyond truth-table construction.  Formulae (cf.
    upstream method paper, Prop. 'Gate-Family One-Sets'):
      AND: one family fixing all inputs to 1.  OR: one band per input
      (overlapping).  NAND/NOR: complements via polarity.  XOR/XNOR: one fully
      fixed family per odd/even minterm (2**(k-1); refused above max_families).
      KOFN(t): C(k,t) families of t inputs fixed to 1 (overlapping).
      CANALIZING: nested canalizing list [(input, canalizing value, output)...]
      plus default; disjoint families.
    """
    params = params or {}
    ins = tuple(inputs)
    if list(ins) != sorted(set(ins)) or (ins and ins[-1] >= n):
        raise SemanticsError("gate inputs must be ascending, distinct, < n")
    k = len(ins)

    def band(i, v):
        return Family(1 << i, v << i)

    g = gate.upper()
    if g == "CONST0":
        return NodeIndex(n, 1, (), ins, True, "closed_form:CONST0")
    if g == "CONST1":
        return NodeIndex(n, 1, (Family(0, 0),), ins, True, "closed_form:CONST1")
    if g in ("COPY", "NOT"):
        if k != 1:
            raise SemanticsError(f"{g} needs one input")
        return NodeIndex(n, 1, (band(ins[0], 1 if g == "COPY" else 0),), ins, True, f"closed_form:{g}")
    if g in ("AND", "NAND"):
        F = sum(1 << i for i in ins)
        return NodeIndex(n, 1 if g == "AND" else 0, (Family(F, F),), ins, True, f"closed_form:{g}")
    if g in ("OR", "NOR"):
        if g == "NOR":
            F = sum(1 << i for i in ins)
            return NodeIndex(n, 1, (Family(F, 0),), ins, True, "closed_form:NOR")
        return NodeIndex(n, 1, tuple(sorted(band(i, 1) for i in ins)), ins, True, "closed_form:OR")
    if g in ("XOR", "XNOR"):
        if (1 << max(k - 1, 0)) > max_families:
            raise MaterializationRefused(f"parity of in-degree {k} needs 2**{k-1} families")
        want = 1 if g == "XOR" else 0
        F = sum(1 << i for i in ins)
        fams = []
        for y in range(1 << k):
            if bin(y).count("1") % 2 == want:
                fams.append(_lift(((1 << k) - 1, y), ins))
        return NodeIndex(n, 1, tuple(sorted(fams)), ins, True, f"closed_form:{g}")
    if g == "KOFN":
        t = int(params["t"])
        if math.comb(k, t) > max_families:
            raise MaterializationRefused("KOFN family count exceeds budget")
        fams = [Family(sum(1 << i for i in c), sum(1 << i for i in c)) for c in itertools.combinations(ins, t)]
        if t == 0:
            fams = [Family(0, 0)]
        return NodeIndex(n, 1, tuple(sorted(fams)), ins, True, "closed_form:KOFN")
    if g == "CANALIZING":
        levels = params["levels"]          # [(input, canalizing value, output), ...]
        default = int(params["default"])
        fams = []
        prefF = prefA = 0
        for (i, c, o) in levels:
            if i not in ins:
                raise SemanticsError("canalizing input not in inputs")
            if o == 1:
                fams.append(Family(prefF | (1 << i), prefA | (c << i)))
            prefF |= 1 << i
            prefA |= (1 - c) << i
        if default == 1:
            fams.append(Family(prefF, prefA))
        return NodeIndex(n, 1, tuple(sorted(fams)), ins, True, "closed_form:CANALIZING")
    raise SemanticsError(f"unknown gate family {gate!r}")


# --------------------------------------------------------------------------- network

@dataclass(frozen=True)
class NetworkIndex:
    n: int
    nodes: tuple[NodeIndex, ...]

    def step(self, x: int) -> int:
        y = 0
        for j, node in enumerate(self.nodes):
            pol = node.polarity
            hit = False
            for f in node.families:
                if (x & f.fixed) == f.anchor:
                    hit = True
                    break
            if (pol if hit else 1 - pol):
                y |= 1 << j
        return y

    def family_count(self) -> int:
        return sum(len(nd.families) for nd in self.nodes)

    def to_network(self) -> Network:
        return Network(self.n, tuple(nd.to_rule() for nd in self.nodes))


def from_network(net: Network, polarity: str | int = "auto") -> NetworkIndex:
    return NetworkIndex(net.n, tuple(from_rule(r, net.n, polarity) for r in net.rules))
