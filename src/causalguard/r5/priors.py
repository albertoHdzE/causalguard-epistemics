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

    def _phi(self, q: Query) -> np.ndarray:
        """phi[j, l, s]: mass of node j's rules of catalogue entry l that fit the evidence and the query path
        through intermediate state s (h = 2), or the query outcome (h = 1, S = 1).  Shared by GSR and XDC."""
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
        out1_s0 = self.T[:, s0]                                 # each row's output at s0
        if q.horizon == 1:
            phi = self.u.copy()
            phi[t] = self._agg((self.cons[t] & (out1_s0 == 1)).astype(float))
            return phi[:, :, None]
        N = 1 << n
        L = self.u.shape[1]
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
        return phi

    def masses(self, q: Query) -> dict:
        phi = self._phi(q)
        L = self.u.shape[1]
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


# --------------------------------------------------------------------------- XDC (R6): exchangeable dictionary code

XDC_THETAS = (0.5, 2.0, 8.0, math.inf)          # fixed grid, equal prior weight (no tuning); inf = no sharing


def rule_type(r) -> tuple:
    """Order-free rule type: (arity, smallest table over all permutations of the local inputs)."""
    import itertools
    d = r.arity
    best = None
    for perm in itertools.permutations(range(d)):
        t = 0
        for z in range(1 << d):
            z2 = 0
            for i in range(d):
                z2 |= ((z >> i) & 1) << perm[i]
            t |= ((r.table >> z2) & 1) << z
        best = t if best is None or t < best else best
    return (d, best if best is not None else r.table)


def _partition_mass(G: np.ndarray, n: int, theta: float) -> np.ndarray:
    """sum over set partitions pi of [n] of CRP_theta(pi) prod_{b in pi} G[b]   (G: (2^n, S); returns (S,)).
    CRP_theta(pi) = theta^|pi| prod_b (|b|-1)! / (theta)_n.  theta = inf: singletons only (independent nodes)."""
    if math.isinf(theta):
        out = np.ones(G.shape[1])
        for j in range(n):
            out = out * G[1 << j]
        return out
    fact = [math.factorial(i) for i in range(n + 1)]
    F = np.zeros_like(G)
    F[0] = 1.0
    for A in range(1, 1 << n):
        low = A & -A
        rest = A ^ low
        acc = np.zeros(G.shape[1])
        sub = rest
        while True:                                            # blocks b = low | sub, sub subset of rest
            b = low | sub
            acc += theta * fact[bin(b).count("1") - 1] * G[b] * F[A ^ b]
            if sub == 0:
                break
            sub = (sub - 1) & rest
        F[A] = acc
    rising = math.prod(theta + i for i in range(n))
    return F[(1 << n) - 1] / rising


class XDC(GSR):
    """Exchangeable dictionary code over a flat base code (R6; the shared-dictionary idea of the original
    method made exactly summable).

    Generative description: nodes are seated by a Chinese-restaurant process with concentration theta; every
    table (dictionary entry) draws ONE order-free rule type lambda from G0; every node then instantiates its
    entry's type as a concrete rule r (support + pin order) with probability w(r) / W(lambda), where
    w(r) = 2^-bits_base(r), W(lambda) = sum of w over the type, G0(lambda) = W(lambda) / sum W.
    Equivalently an adaptive two-part code: a node either pays for a new type under the base code or refers to
    a type already used, at a cost that shrinks with its use count.  Properties:
      * full support on H and one mass per distinct mechanism (masses of coinciding programs add);
      * theta = inf is EXACTLY the base code's nodewise prior (tested), so XDC - base isolates sharing;
      * exchangeable: no node order, cyclic offset or module size is assumed.
    P(q | D) is summed exactly over all set partitions by a subset recursion (pointwise in the intermediate
    state for h = 2); float64 over nonnegative terms, declared relative error GAMMA.  The reported predictor
    'xdc' is the equal-weight Bayes mixture over XDC_THETAS (no parameter is fitted)."""

    def __init__(self, evidence: Evidence, k: int, base: str = "gate", vs=None, thetas=XDC_THETAS):
        from ..s4.prior import node_bits_table
        from ..schema import HypothesisClass
        from ..versionspace import build_version_space
        self.n, self.k, self.base, self.thetas = evidence.n, k, base, tuple(thetas)
        self.vs = vs if vs is not None else build_version_space(evidence, HypothesisClass(evidence.n, k))
        cls = self.cls = self.vs.cls
        self.T = cls.tables
        key = (cls.n, cls.k, base)
        if key not in _XDC_CACHE:
            bits = node_bits_table(cls, base, cls.n, cls.k).astype(float)
            w = np.exp2(-(bits - bits.min()))
            types = [rule_type(r) for r in cls.rules]
            names = sorted(set(types))
            tid = np.array([names.index(t) for t in types])
            order = np.argsort(tid, kind="stable")
            starts = np.searchsorted(tid[order], np.arange(len(names)))
            W = np.add.reduceat(w[order], starts)
            _XDC_CACHE[key] = (w, order, starts, W, W / W.sum(), names)
        self.w, self.order, self.starts, self.W, self.G0, self.type_names = _XDC_CACHE[key]
        if self.vs.empty:
            return
        H = cls.size
        self.cons = []
        for comp in self.vs.compatible:
            m = np.zeros(H, dtype=bool)
            m[comp] = True
            self.cons.append(m)
        self.u = np.stack([self._agg(c.astype(float)) for c in self.cons])        # (n, L)
        self.den = self._theta_masses(self.u[:, :, None])

    def _agg(self, rowvals: np.ndarray) -> np.ndarray:
        """Type-conditional mass: sum_r w(r) val(r) / W(type)."""
        wv = rowvals * (self.w if rowvals.ndim == 1 else self.w[:, None])
        return np.add.reduceat(wv[self.order], self.starts, axis=0) / (
            self.W if rowvals.ndim == 1 else self.W[:, None])

    def _theta_masses(self, phi: np.ndarray) -> dict:
        return theta_masses(phi, self.G0, self.thetas)

    def probabilities(self, q: Query) -> dict:
        """{'xdc': mixture, 'xdc_t<theta>': each theta} -> P(q | D); None values if the evidence is inconsistent."""
        names = {th: "xdc_t" + ("inf" if math.isinf(th) else f"{th:g}") for th in self.thetas}
        if self.vs.empty:
            return dict.fromkeys(["xdc", *names.values()])
        num = self._theta_masses(self._phi(q))
        out = {names[th]: min(1.0, num[th] / self.den[th]) for th in self.thetas}
        out["xdc"] = min(1.0, sum(num.values()) / sum(self.den.values()))
        out["theta_posterior"] = {names[th]: self.den[th] / sum(self.den.values()) for th in self.thetas}
        return out


_XDC_CACHE: dict = {}


def theta_masses(phi: np.ndarray, G0: np.ndarray, thetas) -> dict:
    """{theta: sum_s sum_pi CRP_theta(pi) prod_b G[b, s]} with G[b, s] = sum_l G0[l] prod_{j in b} phi[j, l, s].
    The one owner of the XDC sum (dense XDC, XDC-EB and the sparse large-n path all call it).  theta = inf with
    G0 = p is the nodewise-independent type-mixture prior used by XDC-EB."""
    n, L, S = phi.shape
    if all(math.isinf(th) for th in thetas):                  # singletons only: no subset table needed
        out = np.ones(S)
        for j in range(n):
            out = out * (G0[:, None] * phi[j]).sum(axis=0)
        return {th: float(out.sum()) for th in thetas}
    G = np.empty((1 << n, S))
    stack = [(0, np.broadcast_to(G0[:, None], (L, S)), 0)]
    while stack:
        A, prod, nxt = stack.pop()
        G[A] = prod.sum(axis=0)
        for j in range(nxt, n):
            stack.append((A | (1 << j), prod * phi[j], j + 1))
    return {th: float(_partition_mass(G, n, th).sum()) for th in thetas}


# --------------------------------------------------------------------------- XDC-EB (R6 Track S)

EB_TOL = 1e-9                    # certified Frank-Wolfe gap (nats) required of every fit


def fit_type_weights(u: np.ndarray, G0: np.ndarray, a: float, tol: float = EB_TOL, max_iter: int = 200000) -> dict:
    """Empirical-Bayes type weights for XDC-EB: maximise the concave objective
        F(p) = sum_j log(sum_l p_l u[j, l]) + sum_l a G0_l log p_l      over the simplex,
    i.e. the marginal likelihood of 'node rules are iid draws from the type mixture p' plus a Dirichlet(1 + a G0)
    log-prior pulling p toward the base code (a = 0: maximum likelihood; a -> inf: the base code).  Solved by EM
    (monotone).  Certificate: with g = grad F(p), concavity gives F(p*) - F(p) <= max_l g_l - p.g = max_l g_l - (n + a)
    (the Frank-Wolfe duality gap); the fit is returned only with that gap and the iteration count.  Rows of u that
    are identically equal across types carry no information and are kept (they add a constant)."""
    u = np.asarray(u, dtype=float)
    if u.ndim != 2 or u.shape[0] == 0:
        raise ValueError("fit_type_weights: need at least one node row")
    if (u.sum(axis=1) <= 0).any():
        raise ValueError("fit_type_weights: a node has no evidence-compatible rule")
    n = u.shape[0]
    c = a * np.asarray(G0, dtype=float)
    p = np.asarray(G0, dtype=float).copy()
    it, gap = 0, math.inf
    for it in range(1, max_iter + 1):  # noqa: B007  (it is reported)
        r = u.T @ (1.0 / (u @ p))                               # sum_j u_jl / (p . u_j)
        with np.errstate(divide="ignore", invalid="ignore"):
            g = r + np.where(c > 0, c / p, 0.0)
        gap = float(np.max(g) - (n + a))
        if gap <= tol:
            break
        p = (p * r + c) / (n + a)
        p = p / p.sum()
    F = float(np.log(u @ p).sum() + (c[c > 0] * np.log(p[c > 0])).sum())
    return {"p": p, "gap": gap, "iterations": it, "objective": F, "certified": gap <= tol}


class XDCEB(XDC):
    """XDC-EB over a flat base code (R6 Track S): node rules independent given type weights p, p fitted on the
    PUBLIC evidence by ``fit_type_weights`` (pseudo-count ``a`` toward the base code's type masses G0).  Given p it
    is a flat code with rule weights p_type(r) w(r) / W(type(r)), summed exactly (h = 1, 2) by ``theta_masses``
    at theta = inf.  ``loo``: forecasts for target t use a fit without node t's evidence row.  This is an
    approximation to XDC (a plug-in for its theta mixture), not the same prior."""

    def __init__(self, evidence: Evidence, k: int, base: str = "gate", vs=None, a: float = 4.0, loo: bool = False):
        super().__init__(evidence, k, base=base, vs=vs, thetas=(math.inf,))
        self.a, self.loo = float(a), bool(loo)
        if self.vs.empty:
            return
        self.fit = fit_type_weights(self.u, self.G0, self.a)
        self._loo: dict = {}

    def fit_for(self, t: int) -> dict:
        if not self.loo:
            return self.fit
        if t not in self._loo:
            keep = [j for j in range(self.n) if j != t]
            self._loo[t] = fit_type_weights(self.u[keep], self.G0, self.a)
        return self._loo[t]

    def probabilities(self, q: Query) -> dict:
        if self.vs.empty:
            return {"xdc_eb": None}
        f = self.fit_for(q.target.node)
        num = theta_masses(self._phi(q), f["p"], (math.inf,))[math.inf]
        den = theta_masses(self.u[:, :, None], f["p"], (math.inf,))[math.inf]
        return {"xdc_eb": min(1.0, num / den), "fit_gap": f["gap"], "fit_iterations": f["iterations"]}


def xdc_bruteforce(evidence: Evidence, k: int, q: Query, theta, base: str = "gate") -> Fraction:
    """Exact P(q | D) under XDC(theta) by explicit enumeration of every seating, every type draw and every
    instantiation (tiny n only); independent of the subset recursion and of the type aggregation."""
    import itertools

    from .. import reference
    from ..s4.prior import node_bits_table
    from ..schema import Network
    n = evidence.n
    cls = candidate_class(n, k)
    bits = node_bits_table(cls, base, n, k)
    mb = int(bits.max())
    w = [Fraction(2) ** (mb - int(b)) for b in bits]
    types = [rule_type(r) for r in cls.rules]
    names = sorted(set(types))
    members = {t: [i for i, x in enumerate(types) if x == t] for t in names}
    Wt = {t: sum(w[i] for i in members[t]) for t in names}
    Wsum = sum(Wt.values())
    theta = Fraction(theta)

    def partitions(items):
        if not items:
            yield []
            return
        first, rest = items[0], items[1:]
        for p in partitions(rest):
            for i in range(len(p)):
                yield p[:i] + [[first] + p[i]] + p[i + 1:]
            yield [[first]] + p
    x0 = point_query_parts(q, n)
    num = den = Fraction(0)
    rising = math.prod(theta + i for i in range(n))
    for part in partitions(list(range(n))):
        crp = theta ** len(part) * math.prod(math.factorial(len(b) - 1) for b in part) / rising
        for tys in itertools.product(names, repeat=len(part)):
            pt = crp * math.prod(Wt[t] / Wsum for t in tys)
            per_node = [None] * n
            for b, t in zip(part, tys):
                for j in b:
                    per_node[j] = [(i, w[i] / Wt[t]) for i in members[t]]
            for combo in itertools.product(*per_node):
                net = Network(n, tuple(cls.rules[i] for i, _ in combo))
                if not reference.consistent(net, evidence):
                    continue
                m = pt * math.prod(pw for _, pw in combo)
                den += m
                if ((reference.run(net, x0, q.intervention, q.horizon)[-1] >> q.target.node) & 1) == q.target.value:
                    num += m
    return num / den


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
