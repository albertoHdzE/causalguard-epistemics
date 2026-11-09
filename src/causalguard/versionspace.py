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

    def __init__(self, vs: VersionSpace):
        from .query import _CNF
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
                for a in range(len(svals)):            # at most one (pairwise; <= C(n,k) options)
                    for b in range(a + 1, len(svals)):
                        self.cnf.add([-svals[a], -svals[b]])

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


def verdict(vs: VersionSpace, q: Query, check_proof: bool = False, solver: str = "cadical153"
            ) -> VerdictResult:
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
    enc = _Enc(vs)
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


def verdict_fast(vs: VersionSpace, q: Query) -> Verdict:
    """Exact verdict shortcut for h <= 1 (factorized); otherwise defers to SAT ``verdict``."""
    if vs.empty:
        return Verdict.INCONSISTENT
    if q.horizon <= 1:
        p, _, _ = uniform_prob_true(vs, q, np.random.default_rng(0))
        if p == 1.0:
            return Verdict.ENTAILED
        if p == 0.0:
            return Verdict.REFUTED
        return Verdict.UNDERDETERMINED
    return verdict(vs, q).verdict


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
           "choose_disagreement_state", "disagreement_score", "Unsupported", "content_hash", "Pred"]
