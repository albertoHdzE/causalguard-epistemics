"""Codec-induced model averaging (offline SECONDARY; never used by the commit gate).

    w_L(M | D) = 2^-L(M) / sum_{M' in V(D)} 2^-L(M'),      P_L(q | D) = sum_{M in V(D)} w_L(M | D) [M satisfies q]

H = the declared complete class, V(D) its evidence-compatible subset, L a FIXED, fully specified prefix code with
ONE canonical description per distinct mechanism.  This is a testable preference over models, not a measured
universal algorithmic probability and not a frequency.  An empty V(D) is an inconsistency diagnostic, never a
posterior.  Codes compared (all serialized and counted bit for bit):

  uniform      L = const (exact uniform model averaging; the S2 majority comparator)
  index        sprint flat index code per node (codec 'index')          -- arm C's language
  circuit      sprint minimum-formula code per node (codec 'circuit')    -- a generic symbolic description
  gate         sprint flat gate-catalogue code per node (codec 'gate')
  cgh_flat     CGH-1 FLAT mode (formal-paper analytic vocabulary, no hierarchy)
  cgh_prior    CGH-1 'prior' language: FLAT u ordered TEMPLATE u MODULE (modes 0, 2, 3, no patches); the
               shared-DICTIONARY mode is excluded from the prior because the exact sum over V(D) is infeasible
               with it (it couples every node); it remains in the description-length map.

Nodewise-additive codes are summed exactly with weighted integer counts (versionspace.exact_query_counts with
weights).  cgh_prior = cgh_flat plus an exact correction over the enumerated structured models in V(D):
    sum_M 2^-L(M)[q] = sum_M 2^-Lflat(M)[q] + sum_{M in S n V} (2^-Lstruct(M) - 2^-Lflat(M))^+ [q],
with L(M) = min(Lflat, Lstruct) (one canonical description).  If the structured enumeration exceeds its cap the
cgh_prior value is a RESOURCE REFUSAL for that world (reported), never a truncated sum.
"""
from __future__ import annotations

import itertools
import math
from fractions import Fraction

import numpy as np

from ..schema import Evidence, HypothesisClass, Query
from ..versionspace import build_version_space, exact_query_counts, network_from_choice, predict
from .hcode import _gamma_len, _local_bits, flat_node_bits, header_bits, offset_rule

CODES = ("uniform", "index", "circuit", "gate", "cgh_flat", "cgh_prior", "cgh_flat_noanalytic",
         "cgh_prior_noanalytic")
# attribution ablations: *_noanalytic use the same CGH-1 modes with every rule written as a LUT (variant 3)
STRUCT_CAP = 50_000


def node_bits_table(cls, code: str, n: int, k: int) -> np.ndarray:
    if code in ("index", "circuit", "gate"):
        return cls.bits[code]
    if code in ("cgh_flat", "cgh_prior"):
        return _cgh_bits(cls, n, k, "flat")
    if code in ("cgh_flat_noanalytic", "cgh_prior_noanalytic"):
        return _cgh_bits(cls, n, k, "no_analytic")
    raise ValueError(code)


_CGH_CACHE: dict = {}


def _cgh_bits(cls, n, k, variant):
    key = (n, k, variant)
    if key not in _CGH_CACHE:
        _CGH_CACHE[key] = np.array([flat_node_bits(r, n, k, variant) for r in cls.rules], dtype=np.int64)
    return _CGH_CACHE[key]


def _weights(vs, bits):
    """Integer per-node weights 2^(max_b - b) over each compatible set, plus the per-node exponent offsets."""
    W, off = [], []
    for comp in vs.compatible:
        b = bits[comp]
        mb = int(b.max())
        W.append((np.int64(1) << (mb - b)).astype(np.int64))
        off.append(mb)
    return W, off


def structured_models(vs, n: int, k: int, cap: int = STRUCT_CAP, analytic: bool = True) -> dict[tuple, int] | None:
    """All TEMPLATE and MODULE (no patch) models inside V(D), deduplicated, with their minimal structured code
    length (bits including header).  None if the enumeration exceeds ``cap`` (resource refusal)."""
    cls = vs.cls
    index = {(r.inputs, r.table): i for i, r in enumerate(cls.rules)}
    comp = [set(int(c) for c in cj) for cj in vs.compatible]
    H = header_bits(n, k)
    out: dict[tuple, int] = {}

    def lsb(d, t):
        return _local_bits(d, t, k, analytic) + _wf(math.comb(n, d))
    # ordered templates: one local rule on one cyclic offset pattern at every node
    for d in range(k + 1):
        for offs in itertools.combinations(range(n), d):
            for t in range(1 << (1 << d)):
                choice = []
                for i in range(n):
                    r = offset_rule(i, offs, t, n)
                    ci = index[(r.inputs, r.table)]
                    if ci not in comp[i]:
                        break
                    choice.append(ci)
                else:
                    L = H + lsb(d, t) + _gamma_len(1)
                    key = tuple(choice)
                    out[key] = min(out.get(key, L), L)
    # modules: m | n, 1 < m < n; per-position signatures consistent with every block, then their product
    for m in range(2, n):
        if n % m:
            continue
        per_pos = []
        for p in range(m):
            opts = []
            for d in range(k + 1):
                for offs in itertools.combinations(range(n), d):
                    for t in range(1 << (1 << d)):
                        ch = []
                        for b in range(n // m):
                            r = offset_rule(b * m, offs, t, n)
                            ci = index[(r.inputs, r.table)]
                            if ci not in comp[b * m + p]:
                                break
                            ch.append(ci)
                        else:
                            opts.append((tuple(ch), lsb(d, t)))
            # keep one (shortest) description per distinct per-position choice
            best: dict[tuple, int] = {}
            for ch, L in opts:
                best[ch] = min(best.get(ch, L), L)
            per_pos.append(list(best.items()))
        size = math.prod(len(x) for x in per_pos)
        if size > cap:
            return None
        for combo in itertools.product(*per_pos):
            choice = [0] * n
            L = H + _gamma_len(m) + _gamma_len(1) + sum(Lp for _, Lp in combo)
            for p, (ch, _) in enumerate(combo):
                for b, ci in enumerate(ch):
                    choice[b * m + p] = ci
            key = tuple(choice)
            out[key] = min(out.get(key, L), L)
        if len(out) > cap:
            return None
    return out


def _wf(c):
    from ..codec import width_for
    return width_for(c)


class Averager:
    """All codec-induced averages and shortest-model predictions for one (evidence, claims) pair."""

    def __init__(self, evidence: Evidence, k: int, codes=CODES, struct_cap: int = STRUCT_CAP):
        self.n, self.k = evidence.n, k
        self.vs = build_version_space(evidence, HypothesisClass(evidence.n, k))
        self.codes = codes
        self.struct: dict = {}
        self.struct_status: dict = {}
        if self.vs.empty:
            return
        for code, an in (("cgh_prior", True), ("cgh_prior_noanalytic", False)):
            if code in codes:
                self.struct[code] = structured_models(self.vs, self.n, k, struct_cap, analytic=an)
                self.struct_status[code] = ("resource_refused" if self.struct[code] is None
                                            else f"{len(self.struct[code])} models")
        self._w = {}
        for c in codes:
            if c == "uniform":
                continue
            self._w[c] = _weights(self.vs, node_bits_table(self.vs.cls, c, self.n, k))

    def _flat_fraction(self, code, q) -> tuple[Fraction, Fraction]:
        if code == "uniform":
            num, den = exact_query_counts(self.vs, q)
            return Fraction(num), Fraction(den)
        W, off = self._w[code]
        num, den = exact_query_counts(self.vs, q, W)
        scale = Fraction(1, 2 ** sum(off))
        return num * scale, den * scale                       # = sum 2^-sum(b_j) (header constant omitted)

    def probability(self, code: str, q: Query) -> float | None:
        if self.vs.empty:
            return None
        base = code.replace("prior", "flat")
        num, den = self._flat_fraction(base, q)
        if code in self.struct:
            if self.struct[code] is None:
                return None
            H = header_bits(self.n, self.k)
            bits = node_bits_table(self.vs.cls, base, self.n, self.k)
            for choice, Ls in self.struct[code].items():
                Lf = H + int(sum(bits[c] for c in choice))
                if Ls < Lf:
                    delta = Fraction(1, 2 ** (Ls - H)) - Fraction(1, 2 ** (Lf - H))
                    den += delta
                    if predict(network_from_choice(self.vs.cls, list(choice)), q):
                        num += delta
        return float(num / den)

    def shortest_prediction(self, code: str, q: Query) -> int | None:
        """Prediction of the single shortest compatible model under ``code`` (ties: fixed world-independent rank)."""
        if self.vs.empty:
            return None
        from ..versionspace import select_min_code
        base = code.replace("prior", "flat")
        if base in ("index", "circuit", "gate"):
            choice = select_min_code(self.vs, base)
        else:
            bits = node_bits_table(self.vs.cls, base, self.n, self.k)
            choice = []
            for comp in self.vs.compatible:
                b = bits[comp]
                cand = comp[b == b.min()]
                choice.append(int(cand[np.argmin(self.vs.cls.tiebreak[cand])]))
        if code in self.struct:
            if self.struct[code] is None:
                return None
            if self.struct[code]:
                H = header_bits(self.n, self.k)
                bits = node_bits_table(self.vs.cls, base, self.n, self.k)
                Lf = H + int(sum(bits[c] for c in choice))
                best = min(self.struct[code].items(), key=lambda kv: (kv[1], kv[0]))
                if best[1] < Lf:
                    choice = list(best[0])
        return int(predict(network_from_choice(self.vs.cls, choice), q))
