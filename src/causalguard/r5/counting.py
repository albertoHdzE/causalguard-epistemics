"""Track C: generic distinct-mechanism counting comparators, independent of arm D's derivation.

Three pieces, none of which imports s4.mechspace:

1. ``VECounter`` (backend 'GEN-VE'): explicit-domain variable elimination.  Each node's domain is enumerated as
   its CANONICAL encodings (F, t): F the essential support (|F| <= k, ascending), t a local table on which every
   input of F is essential.  A function has exactly one essential support, so (F, t) <-> distinct mechanism is a
   bijection (no Moebius correction, no closed-form schema count: every candidate table is checked against the
   evidence).  Queries: h = 1 multiplies per-node counts; h = 2 eliminates every non-target node into a
   per-value factor a_j(b) = #{f_j : f_j(s0) = b} and sums the target's encodings over the assignments of s1 on
   F u {t} (the rest of s1 factorizes).  Exact Python integers.  Cost per node O(C(n,k) * #tables(k) * B) -- the
   explicit domain is the price of being generic.
2. ``canonical_cnf``: a CNF whose models are in bijection with distinct mechanisms (one-hot essential-support
   selector, table variables forced to 0 when unselected, full-equivalence essentiality auxiliaries), with the
   projection set declared ('c p show') for a projected model counter.  ``projected_count_bruteforce`` enumerates
   projected models with a SAT solver and blocking clauses (tiny cases only) to validate the projection semantics
   and to exhibit the multiplicity trap of the verdict-oriented encoding.
3. ``ganak_count``: adapter for the external projected counter ganak (pinned release v2.9.0, mac-arm64).  Its
   download/execution was NOT authorized in this session (see reports/R5_COUNTING_AND_COST.md); the adapter
   reports 'unavailable' unless a binary is supplied via CAUSALGUARD_GANAK.
"""
from __future__ import annotations

import functools
import itertools
import math
import os
import time

import numpy as np

from ..schema import Evidence, Query, SemanticsError
from ..versionspace import point_query_parts

GEN_VE_VERSION = "r5-gen-ve-v1"


@functools.lru_cache(maxsize=None)
def essential_tables(d: int) -> np.ndarray:
    """All local tables on d ordered inputs where every input is essential (independent enumeration)."""
    out = []
    for t in range(1 << (1 << d)):
        ok = True
        for i in range(d):
            if all(((t >> y) & 1) == ((t >> (y ^ (1 << i))) & 1) for y in range(1 << d)):
                ok = False
                break
        if ok:
            out.append(t)
    return np.array(out, dtype=np.int64)


def _constraints(evidence: Evidence) -> tuple[list[list[tuple[int, int]]], bool]:
    """Per node: list of (effective input state, required value); independently written (one-step only)."""
    n = evidence.n
    cons: list[dict[int, int]] = [{} for _ in range(n)]
    ok = True
    for o in evidence.observations:
        if o.horizon != 1:
            raise SemanticsError("GEN-VE supports one-step observations only")
        m, v = o.intervention.masks
        x = (o.state & ~m) | v if o.intervention.kind != "none" else o.state
        for j, val in o.observed:
            if o.intervention.kind == "persistent_clamp" and (m >> j) & 1:
                if ((v >> j) & 1) != val:
                    ok = False
                continue
            if cons[j].get(x, val) != val:
                ok = False
            cons[j][x] = val
    return [sorted(c.items()) for c in cons], ok


class _NodeDomain:
    """Consistent canonical encodings of one node, grouped by support."""

    def __init__(self, n: int, k: int, cons: list[tuple[int, int]]):
        self.n, self.k = n, k
        xs = np.array([x for x, _ in cons], dtype=np.uint64)        # n <= 64 state bits (R5-04: was int64)
        vs = np.array([v for _, v in cons], dtype=np.int64)
        self.groups = []                          # (supports array (m, d), tables array T_d, consistent mask (m, |T_d|))
        self.count = 0
        for d in range(min(k, n) + 1):
            T = essential_tables(d)
            F = np.array(list(itertools.combinations(range(n), d)), dtype=np.int64).reshape(math.comb(n, d), d)
            if len(xs):
                Y = np.zeros((len(F), len(xs)), dtype=np.int64)
                for t in range(d):
                    Y |= (((xs[None, :] >> F[:, t:t + 1].astype(np.uint64)) & np.uint64(1)).astype(np.int64)) << t
                mask = np.zeros(len(F), dtype=np.int64)
                val = np.zeros(len(F), dtype=np.int64)
                conflict = np.zeros(len(F), dtype=bool)
                for b in range(len(xs)):
                    bit = np.left_shift(1, Y[:, b])
                    seen = (mask & bit) != 0
                    prev = (val & bit) != 0
                    conflict |= seen & (prev != bool(vs[b]))
                    mask |= bit
                    val |= bit * int(vs[b])
                ok = ((T[None, :] & mask[:, None]) == val[:, None]) & ~conflict[:, None]
            else:
                ok = np.ones((len(F), len(T)), dtype=bool)
            self.groups.append((F, T, ok))
            self.count += int(ok.sum())

    def out_counts(self, s: int) -> tuple[int, int]:
        """#encodings with output 0 / 1 at full state s."""
        c = [0, 0]
        for F, T, ok in self.groups:
            d = F.shape[1]
            y = np.zeros(len(F), dtype=np.int64)
            su = np.uint64(s)
            for t in range(d):
                y |= (((su >> F[:, t].astype(np.uint64)) & np.uint64(1)).astype(np.int64)) << t
            bit = (T[None, :] >> y[:, None]) & 1
            c1 = int((ok & (bit == 1)).sum())
            c[1] += c1
            c[0] += int(ok.sum()) - c1
        return c[0], c[1]


class VECounter:
    """Backend GEN-VE.  Built from public (n, k, evidence) only."""

    def __init__(self, evidence: Evidence, k: int):
        t0 = time.perf_counter()
        self.n, self.k = evidence.n, k
        cons, self.possible = _constraints(evidence)
        self.nodes = [_NodeDomain(self.n, k, c) for c in cons]
        self.counts = [nd.count for nd in self.nodes]
        self.empty = (not self.possible) or any(c == 0 for c in self.counts)
        self.build_s = time.perf_counter() - t0

    def size(self) -> int:
        return 0 if self.empty else math.prod(self.counts)

    def count(self, q: Query) -> tuple[int, int]:
        if self.empty:
            raise SemanticsError("empty version space")
        if q.target.op != "lit" or q.horizon not in (1, 2):
            raise SemanticsError("GEN-VE: literal targets, h in {1, 2}")
        n = self.n
        x0 = point_query_parts(q, n)
        m, v = q.intervention.masks
        s0 = (x0 & ~m) | v if q.intervention.kind != "none" else x0
        clamp = {j: (v >> j) & 1 for j in range(n) if q.intervention.kind == "persistent_clamp" and (m >> j) & 1}
        t, c = q.target.node, q.target.value
        den = self.size()
        if t in clamp:
            return (den if clamp[t] == c else 0), den
        if q.horizon == 1:
            return math.prod(self.counts[j] for j in range(n) if j != t) * self.nodes[t].out_counts(s0)[c], den
        # h = 2: eliminate every non-target node into w_j(b) = #{f_j : s1_j = b}
        w = {}
        for j in range(n):
            if j == t:
                continue
            if j in clamp:
                w[j] = (self.counts[j] * (clamp[j] == 0), self.counts[j] * (clamp[j] == 1))
            else:
                w[j] = self.nodes[j].out_counts(s0)
        tot = {j: w[j][0] + w[j][1] for j in w}
        num = 0
        for F, T, ok in self.nodes[t].groups:
            for fi in range(len(F)):
                okr = ok[fi]
                if not okr.any():
                    continue
                Fs = [int(x) for x in F[fi]]
                Tok = T[okr]
                y0 = sum(((s0 >> i) & 1) << p for p, i in enumerate(Fs))
                a_of = (Tok >> y0) & 1                                   # s1_t = f_t(s0) per table
                W = sorted(set(Fs) | {t})
                rest = math.prod(tot[j] for j in range(n) if j != t and j not in W)
                if rest == 0:
                    continue
                sub = 0
                for assign in itertools.product((0, 1), repeat=len(W)):
                    s1 = dict(zip(W, assign))
                    wt = 1
                    for i in W:
                        if i != t:
                            wt *= w[i][s1[i]]
                    if wt == 0:
                        continue
                    z = sum(s1[i] << p for p, i in enumerate(Fs))
                    sel = (a_of == s1[t]) & (((Tok >> z) & 1) == c)
                    sub += wt * int(sel.sum())
                num += rest * sub
        return num, den


# --------------------------------------------------------------------------- canonical CNF (projected semantics)

class CNF:
    def __init__(self):
        self.nv = 0
        self.clauses: list[list[int]] = []

    def var(self) -> int:
        self.nv += 1
        return self.nv

    def add(self, c):
        self.clauses.append(list(c))

    def xor_def(self, a: int, b: int) -> int:
        """e <-> (a xor b), full equivalence."""
        e = self.var()
        for c in ([-e, a, b], [-e, -a, -b], [e, -a, b], [e, a, -b]):
            self.add(c)
        return e

    def or_def(self, lits: list[int]) -> int:
        o = self.var()
        self.add([-o] + lits)
        for l in lits:
            self.add([o, -l])
        return o


def canonical_cnf(evidence: Evidence, k: int) -> tuple[CNF, list[int], dict]:
    """CNF over the canonical (essential support, table) encoding of every node; returns (cnf, projection vars,
    layout).  Every model restricted to the projection set is one distinct mechanism and vice versa; all other
    variables are functionally determined (so projected count = plain count here, tested)."""
    n = evidence.n
    cons, possible = _constraints(evidence)
    cnf = CNF()
    show: list[int] = []
    layout = {"nodes": []}
    if not possible:
        cnf.add([])
    for j in range(n):
        sels = []
        node = []
        for d in range(min(k, n) + 1):
            for F in itertools.combinations(range(n), d):
                s = cnf.var()
                L = [cnf.var() for _ in range(1 << d)]
                show += [s] + L
                sels.append(s)
                node.append((F, s, L))
                for y in range(1 << d):                         # unselected -> zero table (no free multiplicity)
                    cnf.add([s, -L[y]])
                for i in range(d):                              # every input of F essential when selected
                    diffs = [cnf.xor_def(L[y], L[y ^ (1 << i)]) for y in range(1 << d) if not (y >> i) & 1]
                    cnf.add([-s] + diffs)
                for x, val in cons[j]:                          # evidence on the selected table
                    y = sum(((x >> i) & 1) << p for p, i in enumerate(F))
                    cnf.add([-s, L[y] if val else -L[y]])
        cnf.add(sels)                                           # exactly one selector (pairwise)
        for a in range(len(sels)):
            for b in range(a + 1, len(sels)):
                cnf.add([-sels[a], -sels[b]])
        layout["nodes"].append(node)
    return cnf, show, layout


def projected_count_bruteforce(clauses: list[list[int]], show: list[int], limit: int = 200_000) -> int:
    """Count distinct projections of models onto ``show`` by blocking-clause enumeration (tiny cases)."""
    from pysat.solvers import Solver
    cnt = 0
    with Solver(name="cadical153", bootstrap_with=clauses) as sv:
        while sv.solve():
            m = set(sv.get_model())
            cnt += 1
            if cnt > limit:
                raise RuntimeError("projected enumeration limit")
            sv.add_clause([-v if v in m else v for v in show])
    return cnt


def to_mcc(cnf: CNF, show: list[int]) -> str:
    """Model-counting-competition projected CNF text."""
    lines = [f"p cnf {cnf.nv} {len(cnf.clauses)}", "c t pmc", "c p show " + " ".join(map(str, show)) + " 0"]
    lines += [" ".join(map(str, c)) + " 0" for c in cnf.clauses]
    return "\n".join(lines) + "\n"


def ganak_binary() -> str | None:
    p = os.environ.get("CAUSALGUARD_GANAK")
    return p if p and os.path.exists(p) else None


def ganak_count(cnf: CNF, show: list[int], timeout_s: float = 300.0) -> dict:
    """Projected count by the external ganak binary, or status 'unavailable' (never a substitute value)."""
    import subprocess
    import tempfile
    b = ganak_binary()
    if b is None:
        return {"status": "unavailable", "reason": "ganak binary not authorized/installed in this session"}
    with tempfile.NamedTemporaryFile("w", suffix=".cnf", delete=False) as fh:
        fh.write(to_mcc(cnf, show))
        path = fh.name
    t0 = time.perf_counter()
    try:
        r = subprocess.run([b, "--mode", "0", path], capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "wall_s": time.perf_counter() - t0}
    finally:
        os.unlink(path)
    for line in r.stdout.splitlines():
        if line.startswith("c s exact arb int"):
            return {"status": "exact", "count": int(line.split()[-1]), "wall_s": time.perf_counter() - t0}
    return {"status": "error", "stdout_tail": r.stdout[-400:], "wall_s": time.perf_counter() - t0}
