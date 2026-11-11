"""Incomplete-evidence inference over a complete bounded-indegree hypothesis class.

Owner of: candidate classes, compatibility filtering, version spaces V(D),
evidence-relative verdicts (complete symbolic quantification), model
selection by code length, uniform-compatible-model prediction and
disagreement-guided measurement.

Scope and honesty rules (docs/SEMANTICS.md §5):
* H = all networks on n nodes whose node functions each have <= k essential
  inputs.  Per-node candidates are enumerated COMPLETELY (candidate_set_complete
  = True, candidate_count = product of per-node counts).
* Evidence supported here: one-step observations (horizon 1, interventions none /
  initial_edit / persistent_clamp).  V(D) then factorizes exactly into a product
  of per-node compatible sets.  Other evidence -> Verdict.UNSUPPORTED.
* Verdicts quantify over ALL of V(D) by a complete SAT encoding of H (each node
  picks a k-subset of inputs and a free local table -- exactly the functions
  with <= k essential inputs).  Disagreement witnesses (M+, M-) are replayed by
  the independent reference.  Entailment/refutation is UNSAT of the opposite
  side (optionally RUP-proof-checked).
* "Prediction of the selected (shortest) model" is a PREDICTION, never a
  certificate: it is returned by ``predict`` and never as a Verdict.
* Selection functions receive only the version space (built from public
  evidence).  They never see hidden networks or hidden answers.
"""
from __future__ import annotations

import functools
import hashlib
import itertools
import math
from dataclasses import dataclass

import numpy as np

from . import reference
from .codec import node_bits
from .schema import (
    Certificate,
    Evidence,
    HypothesisClass,
    Network,
    Pred,
    Query,
    Rule,
    SemanticsError,
    Verdict,
    VerdictResult,
    VerificationLevel,
    content_hash,
)

SELECTION_CODECS = ("index", "circuit", "bdd", "dnf", "gate", "lut")
TIEBREAK_SEED = "causalguard-tiebreak-v1"


# --------------------------------------------------------------------------- candidate class

@dataclass
class CandidateClass:
    n: int
    k: int
    rules: list[Rule]
    tables: np.ndarray            # (C, 2**n) uint8: full truth table over the n-bit state
    bits: dict[str, np.ndarray]   # codec -> (C,) int code lengths (actual bits)
    tiebreak: np.ndarray          # (C,) fixed pseudo-random rank, independent of any world

    @property
    def size(self) -> int:
        return len(self.rules)


def _all_canonical_rules(n: int, k: int) -> list[Rule]:
    seen = set()
    out = []
    for size in range(k + 1):
        for ins in itertools.combinations(range(n), size):
            for table in range(1 << (1 << size)):
                r = Rule(ins, table).canonical()
                key = (r.inputs, r.table)
                if key not in seen:
                    seen.add(key)
                    out.append(r)
    return out


def expected_class_size(n: int, k: int) -> int:
    """Number of functions of n variables with exactly <= k essential variables."""
    exact = [2]  # number of functions on m vars depending on all m
    for m in range(1, k + 1):
        tot = 1 << (1 << m)
        exact.append(tot - sum(math.comb(m, i) * exact[i] for i in range(m)))
    return sum(math.comb(n, m) * exact[m] for m in range(k + 1))


@functools.lru_cache(maxsize=8)
def candidate_class(n: int, k: int) -> CandidateClass:
    rules = _all_canonical_rules(n, k)
    N = 1 << n
    tables = np.zeros((len(rules), N), dtype=np.uint8)
    xs = np.arange(N)
    for c, r in enumerate(rules):
        y = np.zeros(N, dtype=np.int64)
        for t, i in enumerate(r.inputs):
            y |= ((xs >> i) & 1) << t
        tab = np.array([(r.table >> z) & 1 for z in range(1 << r.arity)], dtype=np.uint8)
        tables[c] = tab[y]
    bits = {cd: np.array([node_bits(cd, r, n) for r in rules], dtype=np.int64) for cd in SELECTION_CODECS}
    tb = np.array([int.from_bytes(hashlib.sha256(f"{TIEBREAK_SEED}|{r.inputs}|{r.table}".encode()).digest()[:8],
                                  "big") for r in rules], dtype=np.uint64)
    tiebreak = np.argsort(np.argsort(tb, kind="stable"), kind="stable")
    return CandidateClass(n, k, rules, tables, bits, tiebreak)


# --------------------------------------------------------------------------- version space

class Unsupported(SemanticsError):
    pass


@dataclass
class VersionSpace:
    cls: CandidateClass
    evidence: Evidence
    compatible: list[np.ndarray]   # per node: indices of compatible candidates

    @property
    def n(self) -> int:
        return self.cls.n

    @property
    def empty(self) -> bool:
        return any(len(c) == 0 for c in self.compatible)

    def counts(self) -> list[int]:
        return [len(c) for c in self.compatible]

    def log10_size(self) -> float:
        if self.empty:
            return float("-inf")
        return float(sum(math.log10(len(c)) for c in self.compatible))

    def product_size(self) -> int:
        return math.prod(len(c) for c in self.compatible)

    def hypothesis_class(self) -> HypothesisClass:
        return HypothesisClass(self.cls.n, self.cls.k)


def node_constraints(evidence: Evidence) -> tuple[list[list[tuple[int, int]]], bool]:
    """Per node list of (input state fed to F, required output); plus a flag that is
    False if some observation is impossible for every model (e.g. a clamped node
    observed at a value different from its clamp)."""
    n = evidence.n
    cons: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    possible = True
    for o in evidence.observations:
        if o.horizon != 1:
            raise Unsupported("version space supports one-step observations only")
        m, v = o.intervention.masks
        x = (o.state & ~m) | v if o.intervention.kind != "none" else o.state
        for j, val in o.observed:
            if o.intervention.kind == "persistent_clamp" and (m >> j) & 1:
                if ((v >> j) & 1) != val:
                    possible = False
                continue
            cons[j].append((x, val))
    return cons, possible


def build_version_space(evidence: Evidence, hclass: HypothesisClass) -> VersionSpace:
    if evidence.n != hclass.n:
        raise SemanticsError("evidence/class size mismatch")
    cls = candidate_class(hclass.n, hclass.max_indegree)
    cons, possible = node_constraints(evidence)
    comp = []
    for j in range(evidence.n):
        mask = np.ones(cls.size, dtype=bool)
        if not possible:
            mask[:] = False
        for x, val in cons[j]:
            mask &= cls.tables[:, x] == val
        comp.append(np.nonzero(mask)[0])
    return VersionSpace(cls, evidence, comp)


# --------------------------------------------------------------------------- fast simulation

def network_from_choice(cls: CandidateClass, choice: list[int]) -> Network:
    return Network(cls.n, tuple(cls.rules[c] for c in choice))


def _final_state(tables: np.ndarray, x0: int, q: Query) -> int:
    """tables: (n, N) for one model."""
    m, v = q.intervention.masks
    s = (x0 & ~m) | v if q.intervention.kind != "none" else x0
    n = tables.shape[0]
    w = (1 << np.arange(n))
    for _ in range(q.horizon):
        s = int((tables[:, s].astype(np.int64) * w).sum())
        if q.intervention.kind == "persistent_clamp":
            s = (s & ~m) | v
    return s


def point_query_parts(q: Query, n: int) -> int:
    """Initial state of a point query (domain must be a full cube)."""
    from .semantics import pred_to_cubes
    cubes = pred_to_cubes(q.domain)
    if len(cubes) != 1 or cubes[0][0] != (1 << n) - 1 or q.quantifier != "exists":
        raise Unsupported("S2 inference supports point queries (single full initial state)")
    return cubes[0][1]


def predict(net: Network, q: Query) -> bool:
    """Answer of q under ONE selected model (a prediction, not a certificate)."""
    x0 = point_query_parts(q, net.n)
    tr = reference.run(net, x0, q.intervention, q.horizon)
    return reference.holds(q.target, reference.to_bits(tr[-1], net.n))


# --------------------------------------------------------------------------- selection

def select_min_code(vs: VersionSpace, codec: str) -> list[int] | None:
    """Per-node minimum code length (code is additive over nodes, V(D) is a product),
    ties broken by the fixed world-independent tie-break rank."""
    if vs.empty:
        return None
    bits = vs.cls.bits[codec]
    out = []
    for comp in vs.compatible:
        b = bits[comp]
        best = b.min()
        cand = comp[b == best]
        out.append(int(cand[np.argmin(vs.cls.tiebreak[cand])]))
    return out


def select_mdl_noisy(cls: CandidateClass, evidence: Evidence, codec: str = "index") -> tuple[list[int], dict]:
    """Two-part code L(M) + L(D|M) with an explicit per-node residual code.

    L(D|M) per node = gamma(e+1) + e * ceil(log2 N_j) bits, where e mismatches out
    of N_j observations of node j (positions of flipped observations, values implied).
    The code exactly reconstructs the observed bits given the observation inputs."""
    cons, _ = node_constraints(evidence)
    bits = cls.bits[codec]
    choice = []
    resid = []
    for j in range(cls.n):
        if not cons[j]:
            errs = np.zeros(cls.size, dtype=np.int64)
            Nj = 0
        else:
            xs = np.array([x for x, _ in cons[j]])
            vals = np.array([v for _, v in cons[j]], dtype=np.uint8)
            errs = (cls.tables[:, xs] != vals[None, :]).sum(axis=1)
            Nj = len(cons[j])
        posw = (Nj - 1).bit_length() if Nj > 1 else 0
        gam = 2 * np.floor(np.log2(errs + 1)).astype(np.int64) + 1
        total = bits + gam + errs * posw
        best = total.min()
        cand = np.nonzero(total == best)[0]
        c = int(cand[np.argmin(cls.tiebreak[cand])])
        choice.append(c)
        resid.append(int(errs[c]))
    return choice, {"residual_errors": resid}


def true_rank_audit(vs: VersionSpace, truth: Network, codec: str) -> list[dict]:
    """Where the generating rule sits in the code-length distribution of V_j
    (evaluation only; never used by selection)."""
    out = []
    lookup = {(r.inputs, r.table): c for c, r in enumerate(vs.cls.rules)}
    bits = vs.cls.bits[codec]
    for j, r in enumerate(truth.rules):
        cr = r.canonical()
        c = lookup.get((cr.inputs, cr.table))
        comp = vs.compatible[j]
        if c is None or c not in set(comp.tolist()):
            out.append({"node": j, "in_class": c is not None, "compatible": False})
            continue
        b = bits[comp]
        out.append({"node": j, "in_class": True, "compatible": True, "true_bits": int(bits[c]),
                    "min_bits": int(b.min()), "frac_shorter": float((b < bits[c]).mean()),
                    "frac_tied": float((b == bits[c]).mean()), "n_compatible": int(len(comp))})
    return out


# --------------------------------------------------------------------------- uniform compatible-model prediction

def uniform_prob_true(vs: VersionSpace, q: Query, rng: np.random.Generator, exact_limit: int = 200_000,
                      mc_samples: int = 4096) -> tuple[float, str, float]:
    """P_{M ~ Uniform(V(D))}[q(M) = true].  Returns (p, method, standard_error).

    Exact for h <= 1 (outputs factorize over nodes) or when |V(D)| <= exact_limit;
    otherwise Monte Carlo with independent per-node uniform draws (exactly uniform
    over the product), with its binomial standard error."""
    if vs.empty:
        raise SemanticsError("empty version space")
    n = vs.n
    x0 = point_query_parts(q, n)
    m, v = q.intervention.masks
    s0 = (x0 & ~m) | v if q.intervention.kind != "none" else x0
    clamp = q.intervention.kind == "persistent_clamp"
    T = vs.cls.tables
    if q.horizon == 0:
        return float(reference.holds(q.target, reference.to_bits(s0, n))), "exact", 0.0
    if q.horizon == 1:
        p1 = np.array([T[vs.compatible[j], s0].mean() for j in range(n)])
        if clamp:
            for j in range(n):
                if (m >> j) & 1:
                    p1[j] = (v >> j) & 1
        nodes = sorted(q.target.nodes())
        p = 0.0
        for combo in itertools.product((0, 1), repeat=len(nodes)):
            w = 1.0
            x = 0
            for nd, b in zip(nodes, combo):
                w *= p1[nd] if b else (1 - p1[nd])
                x |= b << nd
            if w and reference.holds(q.target, reference.to_bits(x, n)):
                p += w
        return float(p), "exact_factorized", 0.0
    size = vs.product_size()
    if size <= exact_limit:
        choices = np.array(list(itertools.product(*[c.tolist() for c in vs.compatible])), dtype=np.int64)
        method = "exact_enumeration"
    else:
        choices = np.stack([rng.choice(c, size=mc_samples) for c in vs.compatible], axis=1)
        method = "monte_carlo"
    K = choices.shape[0]
    tabs = T[choices, :]  # (K, n, N)
    s = np.full(K, s0, dtype=np.int64)
    w = (1 << np.arange(n)).astype(np.int64)
    for _ in range(q.horizon):
        bitsnext = tabs[np.arange(K)[:, None], np.arange(n)[None, :], s[:, None]].astype(np.int64)
        s = (bitsnext * w[None, :]).sum(axis=1)
        if clamp:
            s = (s & ~m) | v
    from .semantics import eval_pred
    vals = np.array([eval_pred(q.target, int(z)) for z in s], dtype=float) if K <= 4096 else None
    if vals is None:
        uniq, inv = np.unique(s, return_inverse=True)
        uv = np.array([eval_pred(q.target, int(z)) for z in uniq], dtype=float)
        vals = uv[inv]
    p = float(vals.mean())
    se = 0.0 if method.startswith("exact") else float(math.sqrt(max(p * (1 - p), 1e-12) / K))
    return p, method, se


# --------------------------------------------------------------------------- complete symbolic verdicts

class _Enc:
    """Complete CNF encoding of H restricted by evidence, plus a point-query trajectory."""

    def __init__(self, vs: VersionSpace, amo: str = "pairwise"):
        """``amo``: at-most-one encoding of the per-node support selector.  'pairwise' (historical default,
        O(C(n,k)^2) clauses per node) or 'ladder' (iteration 4: Sinz sequential counter, O(C(n,k)) clauses and
        auxiliary variables; equisatisfiable, same selector semantics)."""
        from .query import _CNF
        if amo not in ("pairwise", "ladder"):
            raise ValueError(f"unknown at-most-one encoding {amo!r}")
        self.vs = vs
        self.cnf = _CNF()
        n, k = vs.n, vs.cls.k
        self.k = min(k, n)
        self.subsets = list(itertools.combinations(range(n), self.k))
        cons, possible = node_constraints(vs.evidence)
        self.sel: list[dict] = []
        self.L: list[dict] = []
        self.feasible = possible
        for j in range(n):
            sels = {}
            Ls = {}
            for S in self.subsets:
                req: dict[int, int] = {}
                ok = True
                for x, val in cons[j]:
                    y = sum(((x >> i) & 1) << t for t, i in enumerate(S))
                    if req.get(y, val) != val:
                        ok = False
                        break
                    req[y] = val
                if not ok:
                    continue
                sv = self.cnf.var()
                sels[S] = sv
                lv = [self.cnf.var() for _ in range(1 << self.k)]
                Ls[S] = lv
                for y, val in req.items():
                    self.cnf.add([-sv, lv[y] if val else -lv[y]])
            if not sels:
                self.feasible = False
            self.sel.append(sels)
            self.L.append(Ls)
            if sels:
                self.cnf.add(list(sels.values()))       # at least one subset
                svals = list(sels.values())
                if amo == "pairwise":
                    for a in range(len(svals)):        # at most one (pairwise; <= C(n,k) options)
                        for b in range(a + 1, len(svals)):
                            self.cnf.add([-svals[a], -svals[b]])
                else:                                   # sequential counter: r_i <=> some x_1..x_i is true
                    r_prev = None
                    for i, x in enumerate(svals):
                        if i == len(svals) - 1:
                            if r_prev is not None:
                                self.cnf.add([-x, -r_prev])
                            break
                        r = self.cnf.var()
                        self.cnf.add([-x, r])
                        if r_prev is not None:
                            self.cnf.add([-r_prev, r])
                            self.cnf.add([-x, -r_prev])
                        r_prev = r

    def out_lit(self, j: int, state_lits: list[int]) -> int:
        """Literal for node j's output given symbolic state bits."""
        cnf = self.cnf
        terms = []
        for S, sv in self.sel[j].items():
            lv = self.L[j][S]
            for y in range(1 << self.k):
                lits = [sv, lv[y]]
                for t, i in enumerate(S):
                    lits.append(state_lits[i] if (y >> t) & 1 else -state_lits[i])
                terms.append(cnf.and_gate(lits))
        return cnf.or_gate(terms)

    def query_lit(self, q: Query) -> int:
        from .query import _tseitin_pred
        n = self.vs.n
        x0 = point_query_parts(q, n)
        m, v = q.intervention.masks
        s0 = (x0 & ~m) | v if q.intervention.kind != "none" else x0
        cnf = self.cnf
        state = [cnf.const(bool((s0 >> i) & 1)) for i in range(n)]
        clamp = q.intervention.kind == "persistent_clamp"
        for _ in range(q.horizon):
            nxt = []
            for j in range(n):
                if clamp and (m >> j) & 1:
                    nxt.append(cnf.const(bool((v >> j) & 1)))
                else:
                    nxt.append(self.out_lit(j, state))
            state = nxt
        return _tseitin_pred(cnf, q.target, state)

    def model_network(self, model: list[int]) -> Network:
        mset = set(l for l in model if l > 0)
        rules = []
        for j in range(self.vs.n):
            chosen = [S for S, sv in self.sel[j].items() if sv in mset]
            S = chosen[0]
            lv = self.L[j][S]
            table = sum(1 << y for y in range(1 << self.k) if lv[y] in mset)
            rules.append(Rule(S, table).canonical())
        return Network(self.vs.n, tuple(rules))


def verdict(vs: VersionSpace, q: Query, check_proof: bool = False, solver: str = "cadical153",
            amo: str = "pairwise") -> VerdictResult:
    """Evidence-relative verdict for a point query over ALL of V(D)."""
    from pysat.solvers import Solver

    hc = vs.hypothesis_class()
    scope = f"version_space:bounded_indegree(n={hc.n},k={hc.max_indegree})"
    ev_h = vs.evidence.digest()
    count = vs.product_size() if not vs.empty else 0
    if vs.empty:
        return VerdictResult(Verdict.INCONSISTENT, Certificate(scope, VerificationLevel.EXHAUSTIVE, None, ev_h,
                                                               q.digest()), True, 0)
    try:
        point_query_parts(q, vs.n)
    except Unsupported:
        return VerdictResult(Verdict.UNSUPPORTED, Certificate(scope, VerificationLevel.NONE, None, ev_h,
                                                              q.digest()), True, count)
    enc = _Enc(vs, amo)
    if not enc.feasible:  # pragma: no cover - enumerated V(D) nonempty implies feasible
        raise AssertionError("SAT encoding infeasible while enumerated version space is nonempty")
    ql = enc.query_lit(q)
    witnesses = {}
    detail = {"solver": solver, "vars": enc.cnf.nv, "clauses": len(enc.cnf.clauses)}
    unsat_level = {}
    for want in (True, False):
        lit = ql if want else -ql
        use = "glucose4" if check_proof else solver
        with Solver(name=use, bootstrap_with=enc.cnf.clauses + [[lit]], with_proof=check_proof) as sv:
            if sv.solve():
                net = enc.model_network(sv.get_model())
                # independent replay: compatible with ALL evidence and gives the claimed answer
                if not reference.consistent(net, vs.evidence) or predict(net, q) != want:
                    raise AssertionError("version-space witness failed independent replay")
                witnesses[want] = net
            elif check_proof:
                from .proofcheck import check_rup_refutation
                ok, info = check_rup_refutation(enc.cnf.clauses + [[lit]], sv.get_proof())
                unsat_level[want] = VerificationLevel.CHECKED_PROOF if ok else VerificationLevel.SOLVER_ONLY
                detail[f"proof_{want}"] = info
            else:
                unsat_level[want] = VerificationLevel.SOLVER_ONLY
    if True in witnesses and False in witnesses:
        cert = Certificate(scope, VerificationLevel.WITNESS_REPLAYED, None, ev_h, q.digest(),
                           witness_models=(witnesses[True].to_json(), witnesses[False].to_json()), detail=detail)
        return VerdictResult(Verdict.UNDERDETERMINED, cert, True, count)
    if True in witnesses:
        cert = Certificate(scope, unsat_level[False], None, ev_h, q.digest(),
                           witness_models=(witnesses[True].to_json(),), detail=detail)
        return VerdictResult(Verdict.ENTAILED, cert, True, count)
    if False in witnesses:
        cert = Certificate(scope, unsat_level[True], None, ev_h, q.digest(),
                           witness_models=(witnesses[False].to_json(),), detail=detail)
        return VerdictResult(Verdict.REFUTED, cert, True, count)
    raise AssertionError("nonempty version space but neither side satisfiable")


def verdict_from_enumeration(vs: VersionSpace, q: Query, limit: int = 200_000) -> Verdict | None:
    """Independent cross-check by explicit enumeration of V(D) (small only)."""
    if vs.empty:
        return Verdict.INCONSISTENT
    if vs.product_size() > limit:
        return None
    vals = set()
    for choice in itertools.product(*[c.tolist() for c in vs.compatible]):
        vals.add(predict(network_from_choice(vs.cls, list(choice)), q))
        if len(vals) == 2:
            return Verdict.UNDERDETERMINED
    return Verdict.ENTAILED if vals == {True} else Verdict.REFUTED


# --------------------------------------------------------------------------- measurement policies

def disagreement_score(vs: VersionSpace, x: int) -> float:
    """Expected split of each node's compatible set at input state x (symbolic, public)."""
    s = 0.0
    for comp in vs.compatible:
        if len(comp) == 0:
            continue
        p = vs.cls.tables[comp, x].mean()
        s += min(p, 1 - p)
    return float(s)


def choose_disagreement_state(vs: VersionSpace, used: set[int], rng: np.random.Generator,
                              exclude: set[int] = frozenset()) -> int:
    N = 1 << vs.n
    best = -1.0
    cands = []
    for x in range(N):
        if x in used or x in exclude:
            continue
        sc = disagreement_score(vs, x)
        if sc > best + 1e-12:
            best, cands = sc, [x]
        elif abs(sc - best) <= 1e-12:
            cands.append(x)
    return int(rng.choice(cands))


__all__ = ["CandidateClass", "candidate_class", "expected_class_size", "VersionSpace", "build_version_space",
           "select_min_code", "select_mdl_noisy", "uniform_prob_true", "verdict", "verdict_fast",
           "verdict_from_enumeration", "predict", "true_rank_audit", "network_from_choice",
           "choose_disagreement_state", "disagreement_score", "Unsupported", "content_hash", "Pred",
           "exact_query_counts", "exact_posterior", "boolean_support", "mc_posterior", "MAJORITY_TIE_RULE"]


# --------------------------------------------------------------------------- exact posterior counts (iteration 2)
#
# Owner of the EXACT uniform-compatible posterior for point queries (repairs R01, R07).
# Under M ~ Uniform(V(D)) with V(D) a product of per-node compatible sets, node rules are independent.  The
# trajectory s0 -> s1 -> ... -> s_h is deterministic given the rules, so
#     #{M in V(D): q(M) true} = sum over intermediate states (s1..s_{h-1}) of prod_j C_j(...)
# where C_j counts node-j candidates whose outputs at s0..s_{h-1} reproduce node j's bits of s1..s_h.
# For h <= 3 this is a sum over at most 2^(2n) intermediate pairs and is computed with INTEGER arithmetic
# (Python ints; counts from 0/1 matrix products are exact).  The result (num, den) is exact: verdicts are
# num == 0 / num == den, majority ties are 2*num == den.  No floating tolerance is involved anywhere.

EXACT_MAX_HORIZON = 3


def _bits_matrix(n: int) -> np.ndarray:
    xs = np.arange(1 << n)
    return ((xs[:, None] >> np.arange(n)[None, :]) & 1).astype(np.int64)  # (N, n)


_LIMB = 26


def _limbs(w) -> list[np.ndarray]:
    """Exact decomposition of nonnegative Python-int weights into 26-bit int64 limbs (w = sum_l limb_l 2^(26 l))."""
    w = [int(x) for x in w]
    top = max((x.bit_length() for x in w), default=0)
    return [np.array([(x >> (_LIMB * l)) & ((1 << _LIMB) - 1) for x in w], dtype=np.int64)
            for l in range(max(1, -(-top // _LIMB)))]


def _wcolsum(A01: np.ndarray, w) -> np.ndarray:
    """Exact weighted column sums sum_m w_m A[m, s] as an object array (int64 products per limb are exact)."""
    out = np.zeros(A01.shape[1], dtype=object)
    for l, lw in enumerate(_limbs(w)):
        out = out + ((A01.astype(np.int64) * lw[:, None]).sum(axis=0).astype(object) << (_LIMB * l))
    return out


def _wgram(A01: np.ndarray, w, N: int) -> np.ndarray:
    """Exact A^T diag(w) A as an object array."""
    G = np.zeros((N, N), dtype=object)
    if len(A01) == 0:
        return G
    for l, lw in enumerate(_limbs(w)):
        G = G + ((A01.T @ (A01 * lw[:, None])).astype(object) << (_LIMB * l))
    return G


def exact_query_counts(vs: VersionSpace, q: Query, weights: list[np.ndarray] | None = None) -> tuple[int, int]:
    """Exact (number of models in V(D) for which q holds, |V(D)|) for a point query with h <= 3.

    ``weights`` (iteration 4, codec-induced averaging): optional per-node nonnegative INTEGER weights aligned with
    ``vs.compatible``; the result is then (sum of model weights where q holds, total weight) with the weight of a
    model = product of its node weights.  ``None`` is the unweighted count (every weight 1; unchanged path)."""
    if vs.empty:
        raise SemanticsError("empty version space")
    if weights is not None:
        if len(weights) != vs.n or any(len(w) != len(c) for w, c in zip(weights, vs.compatible)):
            raise SemanticsError("weights must align with the compatible sets")
        if any(int(np.asarray(w).min(initial=0)) < 0 for w in weights):
            raise SemanticsError("weights must be nonnegative")
    n = vs.n
    N = 1 << n
    x0 = point_query_parts(q, n)
    m, v = q.intervention.masks
    s0 = (x0 & ~m) | v if q.intervention.kind != "none" else x0
    clamp = q.intervention.kind == "persistent_clamp"
    clamped = [bool(clamp and (m >> j) & 1) for j in range(n)]
    cval = [(v >> j) & 1 for j in range(n)]
    W = [np.ones(len(c), dtype=np.int64) for c in vs.compatible] if weights is None else \
        [np.array([int(x) for x in w], dtype=object) for w in weights]
    sizes = [int(len(c)) for c in vs.compatible] if weights is None else [int(sum(w)) for w in W]
    den = math.prod(sizes)
    h = q.horizon
    tnodes = sorted(q.target.nodes())
    combos = []
    for combo in itertools.product((0, 1), repeat=len(tnodes)):
        x = sum(b << nd for nd, b in zip(tnodes, combo))
        if reference.holds(q.target, reference.to_bits(x, n)):
            combos.append(combo)
    if h == 0:
        return (den if reference.holds(q.target, reference.to_bits(s0, n)) else 0), den
    if h > EXACT_MAX_HORIZON:
        raise Unsupported(f"exact posterior counts implemented for h <= {EXACT_MAX_HORIZON}")
    T = vs.cls.tables
    bits = _bits_matrix(n)                               # bits[s, j]
    A = [T[vs.compatible[j]] for j in range(n)]          # (|V_j|, N) uint8
    if h == 1:
        num = 0
        for combo in combos:
            w = 1
            for j in range(n):
                if j in tnodes:
                    c = combo[tnodes.index(j)]
                    w *= (sizes[j] if c == cval[j] else 0) if clamped[j] else (
                        int((A[j][:, s0] == c).sum()) if weights is None else int(sum(W[j][A[j][:, s0] == c])))
                else:
                    w *= sizes[j]
            num += w
        return num, den
    # per node and per a = output at s0: subsets, their sizes and column sums (#{A[m, s] = 1})
    split = []
    for j in range(n):
        a0 = A[j][:, s0]
        parts = {}
        for a in (0, 1):
            Aa = A[j][a0 == a].astype(np.float64)
            if weights is None:
                parts[a] = (Aa, int(Aa.shape[0]), Aa.sum(axis=0).astype(np.int64))
            else:
                wa = W[j][a0 == a]
                parts[a] = (Aa, int(sum(wa)), _wcolsum(A[j][a0 == a], wa), wa)
        split.append(parts)

    def obj(x):
        if isinstance(x, np.ndarray) and x.dtype == object:
            return x
        return np.asarray(x, dtype=np.int64).astype(object)

    def sc(x):      # a (possibly > int64) weighted scalar; plain int on the unweighted path
        return x if weights is None else np.array(x, dtype=object)
    fdt = np.int64 if weights is None else object

    if h == 2:
        # grid over s1 (N,)
        s1 = np.arange(N)
        cnt = {}   # cnt[j][c] -> (N,) counts of node j consistent with s1_j and final bit c
        valid = np.ones(N, dtype=bool)
        for j in range(n):
            if clamped[j]:
                valid &= bits[:, j] == cval[j]
                cnt[j] = {c: np.full(N, sizes[j] if c == cval[j] else 0, dtype=fdt) for c in (0, 1)}
                continue
            a = bits[:, j]
            n_a = np.where(a == 1, sc(split[j][1][1]), sc(split[j][0][1]))
            col = np.where(a == 1, split[j][1][2][s1], split[j][0][2][s1])
            cnt[j] = {1: col, 0: n_a - col}
        base = np.ones(N, dtype=object)
        for j in range(n):
            if j not in tnodes:
                base = base * obj(cnt[j][0] + cnt[j][1])
        tot = np.zeros(N, dtype=object)
        for combo in combos:
            w = base.copy()
            for nd, c in zip(tnodes, combo):
                w = w * obj(cnt[nd][c])
            tot = tot + w
        num = int(sum(tot[valid]))
        return num, den
    # h == 3: grid over (s1, s2), shape (N, N)
    valid = np.ones((N, N), dtype=bool)
    base = np.ones((N, N), dtype=object)
    tcnt = {}
    for j in range(n):
        if clamped[j]:
            valid &= (bits[:, j] == cval[j])[:, None] & (bits[:, j] == cval[j])[None, :]
            tcnt[j] = {c: np.full((N, N), sizes[j] if c == cval[j] else 0, dtype=fdt) for c in (0, 1)}
            if j not in tnodes:
                base = base * sizes[j]
            continue
        a = bits[:, j][:, None]           # bit j of s1 (selects the subset at s0)
        e = bits[:, j][None, :]           # bit j of s2 (= required output at s1)
        n_a = np.where(a == 1, sc(split[j][1][1]), sc(split[j][0][1]))
        col1 = np.where(a == 1, split[j][1][2][:, None], split[j][0][2][:, None])   # #{A[m,s1]=1} as (N,1)
        Ne = np.where(e == 1, col1, n_a - col1)                                     # (N, N)
        if j not in tnodes:
            base = base * obj(Ne)
            continue
        # target node: joint counts at (s1, s2) need G_a = A_a^T A_a
        K = {}
        for aa in (0, 1):
            Aa, na, col = split[j][aa][:3]
            if weights is None:
                G = (Aa.T @ Aa).round().astype(np.int64) if na else np.zeros((N, N), dtype=np.int64)
            else:
                G = _wgram(Aa.astype(np.int64), split[j][aa][3], N)
            ci, cj = col[:, None], col[None, :]
            K[aa] = {(1, 1): G, (1, 0): ci - G, (0, 1): cj - G, (0, 0): na - ci - cj + G}
        tc = {}
        for c in (0, 1):
            k1 = np.where(e == 1, K[1][(1, c)], K[1][(0, c)])
            k0 = np.where(e == 1, K[0][(1, c)], K[0][(0, c)])
            tc[c] = np.where(a == 1, k1, k0)
        tcnt[j] = tc
    tot = np.zeros((N, N), dtype=object)
    for combo in combos:
        w = base.copy()
        for nd, c in zip(tnodes, combo):
            w = w * obj(tcnt[nd][c])
        tot = tot + w
    num = int(sum(tot[valid]))
    return num, den


MAJORITY_TIE_RULE = "half_credit"   # an exact tie scores 0.5 (expected accuracy of any tie-break; polarity-free)


def posterior_from_counts(num: int, den: int) -> dict:
    """The ONE derivation of probability, exact majority, tie and verdict from exact integer counts (also used by
    the analysis-side validator to check saved records)."""
    tie = 2 * num == den
    return {"num": num, "den": den, "p": num / den if den else None, "method": "exact_counts",
            "majority": None if tie else int(2 * num > den), "tie": tie,
            "verdict": (Verdict.REFUTED if num == 0 else Verdict.ENTAILED if num == den else Verdict.UNDERDETERMINED).value}


def exact_posterior(vs: VersionSpace, q: Query) -> dict:
    """Exact uniform-compatible posterior summary of q: probability, exact majority decision and tie flag."""
    num, den = exact_query_counts(vs, q)
    return posterior_from_counts(num, den)


def boolean_support(vs: VersionSpace, q: Query) -> set[bool]:
    """Exact set of possible answers of a ONE-STEP point query over V(D): per-node output supports (sets of
    attainable bits; clamped nodes fixed) combined by evaluating the predicate on every supported
    combination.  Pure Boolean evaluation; no probabilities."""
    n = vs.n
    if q.horizon != 1:
        raise Unsupported("boolean_support handles one-step queries")
    x0 = point_query_parts(q, n)
    m, v = q.intervention.masks
    s0 = (x0 & ~m) | v if q.intervention.kind != "none" else x0
    clamp = q.intervention.kind == "persistent_clamp"
    tnodes = sorted(q.target.nodes())
    supp = []
    for j in tnodes:
        if clamp and (m >> j) & 1:
            supp.append(((v >> j) & 1,))
        else:
            supp.append(tuple(sorted({int(b) for b in vs.cls.tables[vs.compatible[j], s0]})))
    out = set()
    for combo in itertools.product(*supp):
        x = sum(b << nd for nd, b in zip(tnodes, combo))
        out.add(bool(reference.holds(q.target, reference.to_bits(x, n))))
    return out


def verdict_fast(vs: VersionSpace, q: Query) -> Verdict:
    """Exact verdict without SAT: Boolean support for h == 1, exact integer counts for 1 < h <= 3,
    otherwise the complete SAT ``verdict``.  (The v1 version compared a floating probability with 1.0/0.0.)"""
    if vs.empty:
        return Verdict.INCONSISTENT
    if q.horizon == 0:
        return verdict(vs, q).verdict
    if q.horizon == 1:
        s = boolean_support(vs, q)
        return Verdict.UNDERDETERMINED if len(s) == 2 else (Verdict.ENTAILED if True in s else Verdict.REFUTED)
    if q.horizon <= EXACT_MAX_HORIZON:
        num, den = exact_query_counts(vs, q)
        return Verdict.REFUTED if num == 0 else Verdict.ENTAILED if num == den else Verdict.UNDERDETERMINED
    return verdict(vs, q).verdict


def mc_posterior(vs: VersionSpace, q: Query, samples: int, rng: np.random.Generator) -> dict:
    """FINITE-SAMPLE MONTE CARLO majority algorithm (diagnostic only; never called exact): `samples`
    independent per-node uniform draws from V(D)."""
    choices = np.stack([rng.choice(c, size=samples) for c in vs.compatible], axis=1)
    n = vs.n
    x0 = point_query_parts(q, n)
    m, v = q.intervention.masks
    s0 = (x0 & ~m) | v if q.intervention.kind != "none" else x0
    clamp = q.intervention.kind == "persistent_clamp"
    T = vs.cls.tables
    s = np.full(samples, s0, dtype=np.int64)
    w = (1 << np.arange(n)).astype(np.int64)
    for _ in range(q.horizon):
        nb = T[choices, s[:, None]].astype(np.int64)          # (K, n): node j's table at state s
        s = (nb * w[None, :]).sum(axis=1)
        if clamp:
            s = (s & ~m) | v
    from .semantics import eval_pred
    uniq, inv = np.unique(s, return_inverse=True)
    vals = np.array([eval_pred(q.target, int(z)) for z in uniq], dtype=np.int64)[inv]
    k = int(vals.sum())
    p = k / samples
    return {"p": p, "k": k, "samples": samples, "se": math.sqrt(max(p * (1 - p), 0.0) / samples),
            "majority": None if 2 * k == samples else int(2 * k > samples), "tie": 2 * k == samples,
            "method": "monte_carlo"}
