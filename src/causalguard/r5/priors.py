"""Track G generic structured prior ('gsr': generic shared-rule program prior), and the predictor table.

GSR(alpha) is a mixture over GENERATIVE PROGRAMS, independently specified from CGH (no code lengths, no analytic
vocabulary, no cyclic offsets/templates/modules):

    U      every node uniform over its complete class H_j (full support on H)
    S_q    (q = 1, 2) a dictionary of q local tables, entries iid uniform over the catalogue
           Lambda = {(d, t): 0 <= d <= k, t in [0, 2^(2^d))}  (|Lambda| = 278 for k = 3);
           each node independently picks an entry uniformly (prob 1/q) and a support F uniformly among the C(n, d)
           ascending d-subsets; its mechanism is Rule(F, t) (local input i <-> i-th smallest node), canonicalized.
    P = alpha U + (1 - alpha)/2 S_1 + (1 - alpha)/2 S_2.

The prior on MECHANISMS is the push-forward of the program distribution: several programs can produce the same
canonical mechanism (degenerate tables, duplicate entries), and their masses add; a mechanism is never counted as
two models.  P(q | D) = P(D and q) / P(D) with all masses summed EXACTLY over programs, by the subset identity

    sum_{l1,l2} prod_j (phi_j(l1) + phi_j(l2)) = sum_{A subset [n]} G(A) G([n] - A),  G(A) = sum_l prod_{j in A} phi_j(l)

applied pointwise in the intermediate state s1 for h = 2 (nodes are independent given the dictionary, the entry
assignment and s1).  Arithmetic is float64 over nonnegative terms; every reported probability carries the declared
certified relative error bound GAMMA (status 'bounded'); tests compare against exact rational enumeration of every
program on small classes.  alpha is chosen on calibration from ALPHAS (each alpha is a separate candidate in the
champion selection, fixed tie order).
"""
from __future__ import annotations

import functools
import math
from fractions import Fraction

import numpy as np

from ..schema import Evidence, Query
from ..versionspace import candidate_class, exact_query_counts, point_query_parts

ALPHAS = {"gsr_a25": 0.25, "gsr_a50": 0.5, "gsr_a75": 0.75}
GAMMA = 1e-9                     # declared certified relative error of each mass (float64, nonnegative sums)
# champion candidates and their FIXED tie order (lower index wins ties); analytic-only CGH is the ablation, not a
# candidate (protocol G2)
CHAMPION_CANDIDATES = ("uniform", "circuit", "gate", "gsr_a50", "gsr_a25", "gsr_a75")
AVERAGER_CODES = ("uniform", "index", "circuit", "gate", "cgh_flat", "cgh_prior", "cgh_flat_noanalytic",
                  "cgh_prior_noanalytic")


@functools.lru_cache(maxsize=4)
def _catalogue(n: int, k: int):
    """Rows (lambda, F) with the class index of Rule(F, t).canonical(), grouped contiguously by lambda."""
    import itertools

    from ..schema import Rule
    cls = candidate_class(n, k)
    index = {(r.inputs, r.table): i for i, r in enumerate(cls.rules)}
    lam_d, lam_start, rows = [], [], []
    for d in range(k + 1):
        subs = list(itertools.combinations(range(n), d))
        for t in range(1 << (1 << d)):
            lam_start.append(len(rows))
            lam_d.append(d)
            for F in subs:
                r = Rule(F, t).canonical()
                rows.append(index[(r.inputs, r.table)])
    rows = np.array(rows, dtype=np.int64)
    lam_d = np.array(lam_d)
    inv_c = np.array([1.0 / math.comb(n, int(d)) for d in lam_d])
    T = cls.tables[rows]                                      # (R, 2^n) uint8
    return cls, rows, np.array(lam_start), lam_d, inv_c, T


def _subset_mass(phi: np.ndarray, q: int) -> float:
    """phi: (n, L, S) nonnegative.  q = 1: sum_s sum_l prod_j phi[j,l,s].  q = 2: (1/2^n) sum_s sum_A G(A,s)G(~A,s)
    with G(A, s) = sum_l prod_{j in A} phi[j, l, s].  (Uniform dictionary averaging is applied by the caller.)"""
    n, L, S = phi.shape
    if q == 1:
        return float(np.prod(phi, axis=0).sum())
    full = (1 << n) - 1
    G = np.empty((1 << n, S))
    # iterative DFS over subsets: prod[A] = prod[A - top] * phi[top]
    stack = [(0, np.ones((L, S)), 0)]
    while stack:
        A, prod, nxt = stack.pop()
        G[A] = prod.sum(axis=0)
        for j in range(nxt, n):
            stack.append((A | (1 << j), prod * phi[j], j + 1))
    return float((G * G[full ^ np.arange(1 << n)]).sum() / (1 << n))


class GSR:
    """Program masses for one evidence set; ``probability(q)`` for each alpha."""

    def __init__(self, evidence: Evidence, k: int, vs=None):
        from ..schema import HypothesisClass
        from ..versionspace import build_version_space
        self.n, self.k = evidence.n, k
        self.vs = vs if vs is not None else build_version_space(evidence, HypothesisClass(evidence.n, k))
        self.cls, self.rows, self.lam_start, self.lam_d, self.inv_c, self.T = _catalogue(self.n, k)
        if self.vs.empty:
            return
        H = self.cls.size
        self.cons = []
        for comp in self.vs.compatible:
            m = np.zeros(H, dtype=bool)
            m[comp] = True
            self.cons.append(m[self.rows])                     # (R,) row consistent with node j's evidence
        self.u = np.stack([self._agg(c.astype(float)) for c in self.cons])        # (n, L)
        self.U_den = math.prod(len(c) / H for c in self.vs.compatible)
        self.S_den = {1: self._mass_const(self.u, 1), 2: self._mass_const(self.u, 2)}

    def _agg(self, rowvals: np.ndarray) -> np.ndarray:
        """Sum row values per lambda and divide by C(n, d)."""
        return np.add.reduceat(rowvals, self.lam_start, axis=0) * (
            self.inv_c if rowvals.ndim == 1 else self.inv_c[:, None])

    def _mass_const(self, u: np.ndarray, q: int) -> float:
        L = u.shape[1]
        return _subset_mass(u[:, :, None], q) / (L ** q)

    def masses(self, q: Query) -> dict:
        n = self.n
        x0 = point_query_parts(q, n)
        m, v = q.intervention.masks
        s0 = (x0 & ~m) | v if q.intervention.kind != "none" else x0
        clamp = {j for j in range(n) if q.intervention.kind == "persistent_clamp" and (m >> j) & 1}
        t = q.target.node
        if q.target.op != "lit":
            raise ValueError("literal targets only")
        if q.horizon not in (1, 2) or t in clamp:
            raise ValueError("gsr: h in {1,2}, unclamped target")
        L = self.u.shape[1]
        out1_s0 = self.T[:, s0]                                 # each row's output at s0
        if q.horizon == 1:
            phi = self.u.copy()
            phi[t] = self._agg((self.cons[t] & (out1_s0 == 1)).astype(float))
            S = {qq: _subset_mass(phi[:, :, None], qq) / (L ** qq) for qq in (1, 2)}
        else:
            N = 1 << n
            bits = (np.arange(N)[:, None] >> np.arange(n)[None, :]) & 1          # (N, n)
            phi = np.empty((n, L, N))
            for j in range(n):
                if j == t:
                    match = (out1_s0[:, None] == bits[None, :, t])                # s1_t = f_t(s0)
                    val = self.cons[t][:, None] & match & (self.T == 1)           # f_t(s1) = 1
                    phi[j] = self._agg(val.astype(float))
                elif j in clamp:
                    phi[j] = self.u[j][:, None] * (bits[:, j] == ((v >> j) & 1))[None, :]
                else:
                    a = np.stack([self._agg((self.cons[j] & (out1_s0 == b)).astype(float)) for b in (0, 1)])
                    phi[j] = a[bits[:, j]].T                                      # (L, N)
            S = {qq: _subset_mass(phi, qq) / (L ** qq) for qq in (1, 2)}
        num_u, den_u = exact_query_counts(self.vs, q)
        return {"U": self.U_den * num_u / den_u, "S1": S[1], "S2": S[2]}

    def probability(self, q: Query, alpha: float, masses: dict | None = None) -> dict:
        if self.vs.empty:
            return {"status": "inconsistent_evidence", "p": None}
        ms = masses or self.masses(q)
        b = (1 - alpha) / 2
        num = alpha * ms["U"] + b * ms["S1"] + b * ms["S2"]
        den = alpha * self.U_den + b * self.S_den[1] + b * self.S_den[2]
        p = min(1.0, num / den)
        g = GAMMA
        return {"status": "bounded", "p": p, "lo": max(0.0, p * (1 - g) / (1 + g)), "hi": min(1.0, p * (1 + g) / (1 - g))}


# --------------------------------------------------------------------------- independent rational oracle (tests)

def gsr_bruteforce(evidence: Evidence, k: int, q: Query, alpha) -> Fraction:
    """Exact P(q | D) by explicit enumeration of EVERY program (tiny n only).  Independent of the subset identity:
    enumerates dictionaries, entry assignments and supports, executes each produced network."""
    import itertools

    from .. import reference
    from ..schema import Network, Rule
    n = evidence.n
    cls = candidate_class(n, k)
    lam = [(d, t) for d in range(k + 1) for t in range(1 << (1 << d))]
    subs = {d: list(itertools.combinations(range(n), d)) for d in range(k + 1)}

    def holds(net):
        x0 = point_query_parts(q, n)
        tr = reference.run(net, x0, q.intervention, q.horizon)
        return ((tr[-1] >> q.target.node) & 1) == q.target.value

    def consistent(net):
        return reference.consistent(net, evidence)
    alpha = Fraction(alpha)
    num = den = Fraction(0)
    # U
    H = cls.size
    for choice in itertools.product(range(H), repeat=n):
        net = Network(n, tuple(cls.rules[c] for c in choice))
        if consistent(net):
            w = alpha / Fraction(H) ** n
            den += w
            num += w * holds(net)
    b = (1 - alpha) / 2
    for qq in (1, 2):
        for dic in itertools.product(lam, repeat=qq):
            per_node = []
            for _j in range(n):
                opts = []
                for e in range(qq):
                    d, t = dic[e]
                    for F in subs[d]:
                        opts.append((Rule(F, t).canonical(), Fraction(1, qq * math.comb(n, d))))
                per_node.append(opts)
            for combo in itertools.product(*per_node):
                w = b / Fraction(len(lam)) ** qq
                for _, pw in combo:
                    w *= pw
                net = Network(n, tuple(r for r, _ in combo))
                if consistent(net):
                    den += w
                    num += w * holds(net)
    return num / den
