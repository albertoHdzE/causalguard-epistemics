"""R6 Track S: dictionary sharing at the scale of published models (h = 1 queries only).

What the compact representation makes feasible.  The dense path (``versionspace.candidate_class``) stores every
rule's full truth table over all 2^n states: at n = 24 that is 2^24 columns for ~4.4e5 rules, impossible.  Here a
node's compatible set is never listed.  Following the support-schema representation (``s4/mechspace.py``): node
j's observations project, on each support F (|F| <= k), to a local SCHEMA (fixed local addresses with values).
Rules are canonical (essential inputs), and every base code used here prices a rule by (arity, local table) only
(checked by ``base_weights``), so the per-node type masses need only

    N_j(d, t) = #{supports F, |F| = d : local table t is consistent with node j's schema on F}

which is a sum over DISTINCT schemas (signatures) weighted by how many supports share them.  The number of
distinct signatures is bounded by 3^(2^k) independently of n, so the cost is one projection pass over the C(n, k)
supports plus a (signatures x tables) consistency product; memory is O(C(n, k)), not O(2^n).  Query masses for a
target t at start state s0 add the local address of s0 on F to the signature.

Predictors (all from the same N_j counts):
  flat[base]      the nodewise base code (uniform, gate, circuit, index, cgh_flat)
  xdc_eb[base]    XDC-EB (``r5.priors.fit_type_weights``; certified fit), full-evidence or leave-target-out fit
  xdc[base]       exact XDC theta mixture (``r5.priors.theta_masses``), only for n <= XDC_EXACT_MAX_N
"""
from __future__ import annotations

import functools
import itertools
import math

import numpy as np

from ..r5.priors import XDC_THETAS, fit_type_weights, rule_type, theta_masses
from ..s4.mechspace import node_constraints_d
from ..schema import Evidence, Query, Rule

K = 3
BASES = ("uniform", "gate", "circuit", "index", "cgh_flat")
XDC_EXACT_MAX_N = 12


@functools.lru_cache(maxsize=64)
def base_weights(n: int, k: int, base: str):
    """Essential local tables per arity, their order-free type ids, base weights w(d, t) and type masses.

    Returns (tables[d] int array, type_id[d] int array, w[d] float array, type_names, W (per type), G0).
    W(lam) = sum_{(d,t) in lam} C(n, d) w(d, t) is the base code's mass of the type over all supports (each base
    code here is support-independent: asserted on a sample of supports for every table)."""
    from ..codec import node_bits
    from ..s4.hcode import flat_node_bits
    tabs, tys, bits = [], [], []
    for d in range(k + 1):
        T, Y, B = [], [], []
        for t in range(1 << (1 << d)):
            r = Rule(tuple(range(d)), t)
            if r.canonical() != r:
                continue
            T.append(t)
            Y.append(rule_type(r))
            B.append(_bits(base, r, n, k, node_bits, flat_node_bits))
        tabs.append(T)
        tys.append(Y)
        bits.append(B)
    names = sorted({y for Y in tys for y in Y})
    idx = {y: i for i, y in enumerate(names)}
    mb = min(b for B in bits for b in B)
    w = [np.exp2(-(np.array(B, dtype=float) - mb)) for B in bits]
    W = np.zeros(len(names))
    for d in range(k + 1):
        np.add.at(W, [idx[y] for y in tys[d]], math.comb(n, d) * w[d])
    _check_support_independence(n, k, base, tabs, bits, node_bits, flat_node_bits)
    return ([np.array(T, dtype=np.int64) for T in tabs], [np.array([idx[y] for y in Y]) for Y in tys], w,
            names, W, W / W.sum())


def _bits(base, r, n, k, node_bits, flat_node_bits):
    if base == "uniform":
        return 0
    if base == "cgh_flat":
        return flat_node_bits(r, n, k, "flat")
    return node_bits(base, r, n)


def _check_support_independence(n, k, base, tabs, bits, node_bits, flat_node_bits):
    if base == "uniform":
        return
    for d in range(1, k + 1):
        F = tuple(range(n - d, n))                              # a different support from range(d)
        for t, b in zip(tabs[d], bits[d]):
            if _bits(base, Rule(F, int(t)), n, k, node_bits, flat_node_bits) != b:
                raise ValueError(f"base code {base} is support-dependent at n={n}; the sparse path does not apply")


@functools.lru_cache(maxsize=16)
def _supports(n: int, d: int) -> np.ndarray:
    c = list(itertools.combinations(range(n), d))
    return np.array(c, dtype=np.int64).reshape(len(c), d)


@functools.lru_cache(maxsize=16)
def _consistency(d: int, tables: tuple) -> np.ndarray:
    """M[care, val, t] = table t agrees with val on the local addresses in care (all care/val pairs)."""
    A = 1 << (1 << d)
    T = np.array(tables, dtype=np.int64)
    care = np.arange(A)[:, None, None]
    val = np.arange(A)[None, :, None]
    return (((T[None, None, :] ^ val) & care) == 0)


def _bitmatrix(states: list[int], n: int) -> np.ndarray:
    return np.array([[(x >> i) & 1 for i in range(n)] for x in states], dtype=np.uint8).reshape(len(states), n)


class SparseMasses:
    """Per-node consistent-support counts N_j(d, t) for one evidence set (one-step observations)."""

    def __init__(self, evidence: Evidence, k: int = K):
        self.n, self.k = evidence.n, k
        cons, ok = node_constraints_d(evidence)
        self.consistent = all(ok)
        self.tables = base_weights(self.n, k, "uniform")[0]      # essential tables per arity (base-independent)
        self.N = []                                              # N[j][d]: (n_tables_d,) counts
        self.sig = []                                            # sig[j][d]: (care, val) per support, -1 = conflict
        self.meter = {"supports": sum(math.comb(self.n, d) for d in range(k + 1)), "distinct_signatures": 0}
        for j in range(self.n):
            xs = list(cons[j])
            vs = np.array([cons[j][x] for x in xs], dtype=np.int64)
            X = _bitmatrix(xs, self.n)
            Nj, Sj = [], []
            for d in range(k + 1):
                care, val = self._schema(X, vs, d)
                Sj.append((care, val))
                Nj.append(self._count(care, val, d, None))
            self.N.append(Nj)
            self.sig.append(Sj)

    def _schema(self, X: np.ndarray, vs: np.ndarray, d: int):
        S = _supports(self.n, d)
        if X.shape[0] == 0:
            z = np.zeros(S.shape[0], dtype=np.int64)
            return z, z.copy()
        Y = np.zeros((X.shape[0], S.shape[0]), dtype=np.int64)
        for i in range(d):
            Y |= X[:, S[:, i]].astype(np.int64) << i
        bit = np.left_shift(1, Y)
        one = np.bitwise_or.reduce(np.where(vs[:, None] == 1, bit, 0), axis=0)
        zero = np.bitwise_or.reduce(np.where(vs[:, None] == 0, bit, 0), axis=0)
        care = one | zero
        care = np.where((one & zero) != 0, -1, care)            # conflicting schema: no table fits on this support
        return care, one

    def _count(self, care, val, d, yq):
        """sum over supports of consistent[t] (and, if yq is given, table bit at yq == 1)."""
        T = self.tables[d]
        good = care >= 0
        A = 1 << (1 << d)
        if yq is None:
            key = care[good] * A + val[good]
            u, c = np.unique(key, return_counts=True)
            self.meter["distinct_signatures"] = max(self.meter["distinct_signatures"], int(u.size))
            M = _consistency(d, tuple(T.tolist()))[u // A, u % A]          # (nsig, ntab)
            return c.astype(float) @ M
        key = (care[good] * A + val[good]) * 8 + yq[good]
        u, c = np.unique(key, return_counts=True)
        s, y = u // 8, u % 8
        M = _consistency(d, tuple(T.tolist()))[s // A, s % A] & (((T[None, :] >> y[:, None]) & 1) == 1)
        return c.astype(float) @ M

    def query_counts(self, t: int, s0: int) -> list:
        """N^q_t(d, t'): consistent supports on which table t' outputs 1 at the local address of s0."""
        xb = _bitmatrix([s0], self.n)[0]
        out = []
        for d in range(self.k + 1):
            S = _supports(self.n, d)
            yq = np.zeros(S.shape[0], dtype=np.int64)
            for i in range(d):
                yq |= xb[S[:, i]].astype(np.int64) << i
            care, val = self.sig[t][d]
            out.append(self._count(care, val, d, yq))
        return out

    def type_masses(self, counts_by_d: list, base: str) -> np.ndarray:
        """u(lam) = sum_{(d,t) in lam} w(d,t) N(d,t) / W(lam)."""
        _, tid, w, names, W, _ = base_weights(self.n, self.k, base)
        u = np.zeros(len(names))
        for d in range(self.k + 1):
            np.add.at(u, tid[d], w[d] * counts_by_d[d])
        return u / W

    def u(self, base: str) -> np.ndarray:
        return np.stack([self.type_masses(self.N[j], base) for j in range(self.n)])


def _start_state(q: Query, n: int) -> tuple[int, int]:
    from ..versionspace import point_query_parts
    if q.horizon != 1 or q.target.op != "lit":
        raise ValueError("Track S: h = 1 literal point queries only")
    x0 = point_query_parts(q, n)
    m, v = q.intervention.masks
    s0 = (x0 & ~m) | v if q.intervention.kind != "none" else x0
    if q.intervention.kind == "persistent_clamp" and (m >> q.target.node) & 1:
        raise ValueError("clamped target")
    return q.target.node, s0


EB_A_GRID = (1.0, 4.0, 16.0)       # declared regulariser candidates (pseudo-nodes toward the base code)


def predict_sparse(evidence: Evidence, queries: list[tuple[str, Query]], bases=BASES, eb_bases=("gate", "cgh_flat",
                   "circuit", "index"), a_grid=EB_A_GRID, exact_bases=("gate", "cgh_flat"), k: int = K) -> dict:
    """All Track S predictions P(target node = 1 | D) for one evidence set (node value, whatever the literal's
    value; Track S queries carry literal value 1 as in R5).  Public inputs only."""
    import time
    t0 = time.perf_counter()
    sm = SparseMasses(evidence, k)
    out = {"n": evidence.n, "cost_s": {"sparse_counts": time.perf_counter() - t0}, "meter": dict(sm.meter),
           "queries": [], "fits": {}}
    if not sm.consistent or any(sum(float(x.sum()) for x in sm.N[j]) == 0 for j in range(sm.n)):
        out["status"] = "inconsistent_evidence"
        for qid, _ in queries:
            out["queries"].append({"query_id": qid, "predictions": {}})
        return out
    U = {b: sm.u(b) for b in set(bases) | set(eb_bases) | set(exact_bases)}
    G0 = {b: base_weights(sm.n, k, b)[5] for b in U}
    t0 = time.perf_counter()
    fits = {}
    for b in eb_bases:
        for a in a_grid:
            f = fit_type_weights(U[b], G0[b], a)
            fits[(b, a, None)] = f
            out["fits"][f"{b}|a{a:g}|full"] = {"gap": f["gap"], "iterations": f["iterations"],
                                               "certified": f["certified"]}
    out["cost_s"]["eb_fit_full"] = time.perf_counter() - t0
    exact_ok = sm.n <= XDC_EXACT_MAX_N
    den_x = {b: theta_masses(U[b][:, :, None], G0[b], XDC_THETAS) for b in exact_bases} if exact_ok else {}
    for qid, q in queries:
        t, s0 = _start_state(q, sm.n)
        Nq = sm.query_counts(t, s0)
        pr = {}
        for b in U:
            uq = sm.type_masses(Nq, b)
            if b in bases:
                pr[f"flat[{b}]"] = float(G0[b] @ uq / (G0[b] @ U[b][t]))
            if b in eb_bases:
                for a in a_grid:
                    pr[f"xdc_eb[{b}]|a{a:g}|full"] = float(fits[(b, a, None)]["p"] @ uq / (fits[(b, a, None)]["p"] @ U[b][t]))
                    key = (b, a, t)
                    if key not in fits:
                        keep = [j for j in range(sm.n) if j != t]
                        fits[key] = fit_type_weights(U[b][keep], G0[b], a)
                        out["fits"][f"{b}|a{a:g}|loo{t}"] = {"gap": fits[key]["gap"],
                                                             "iterations": fits[key]["iterations"],
                                                             "certified": fits[key]["certified"]}
                    p = fits[key]["p"]
                    pr[f"xdc_eb[{b}]|a{a:g}|loo"] = float(p @ uq / (p @ U[b][t]))
            if b in exact_bases and exact_ok:
                phi = U[b].copy()
                phi[t] = uq
                num = theta_masses(phi[:, :, None], G0[b], XDC_THETAS)
                pr[f"xdc[{b}]"] = min(1.0, sum(num.values()) / sum(den_x[b].values()))
        out["queries"].append({"query_id": qid, "predictions": {k2: min(1.0, max(0.0, v)) for k2, v in pr.items()}})
    out["cost_s"]["total"] = time.perf_counter() - t0 + out["cost_s"]["sparse_counts"]
    out["status"] = "ok"
    return out


# --------------------------------------------------------------------------- runner item (one world)

PROBE_BUDGETS = (4, 8, 16, 32, 64)
MAX_BUDGET = 64                    # the design stream is drawn once with this many observations (nested prefixes)


def s_world(p: dict) -> dict:
    """One Track S world: public payload -> predictions (digest fixed) -> evaluator-side outcomes and diagnostics."""
    import hashlib
    import json

    from ..r5 import data as D
    from ..r5.external import load_instance
    from ..s4.tasks import audit_public_payload
    net = load_instance(p["key"])
    n = net.n
    budgets = [int(b) for b in p.get("budgets", PROBE_BUDGETS)]
    design = D.make_design(p["design_salt"], p["key"], n, max_budget=int(p.get("max_budget", MAX_BUDGET)),
                           horizons=(1,) * D.N_QUERIES)
    preds = {}
    for B in budgets:
        ev = D.make_evidence(net, design, B)
        pub = D.public_payload(p["key"], ev, design, n, K)
        bad = audit_public_payload(pub)
        if bad:
            raise ValueError(f"public payload leaks {bad}")
        pev = Evidence.from_json(pub["evidence"])
        qs = [(qd["query_id"], Query.from_json(qd["query"])) for qd in pub["queries"]]
        out = predict_sparse(pev, qs)
        for row in out["queries"]:
            row["predictions"] = {k2: {"p": v} for k2, v in row["predictions"].items()}
        out["evidence_id"] = pub["evidence_hash"][:16]
        preds[str(B)] = out
    digest = hashlib.sha256(json.dumps(preds, sort_keys=True).encode()).hexdigest()
    # ---- evaluator side (after the digest)
    outcomes = {qid: D.outcome(net, q) for qid, q in design.queries}
    rules = [r.canonical() for r in net.rules]
    types = [rule_type(r) for r in rules]
    nonconst = [t for t, r in zip(types, rules) if r.arity > 0]
    ident = {"panel": p["panel"], "external_key": p["key"], "source_group_id": p["group"], "split": p["split"],
             "mechanism_id": "x-" + hashlib.sha256(p["key"].encode()).hexdigest()[:16], "n": n,
             "clamped_edge_fraction": p.get("clamped_edge_fraction"), "group_seen_in_n8": p.get("group_seen_in_n8"),
             "hidden_rule_reuse": n - len(set(types)), "constant_share": sum(r.arity == 0 for r in rules) / n,
             "reuse_nonconstant": len(nonconst) - len(set(nonconst)),
             "arity_hist": [sum(r.arity == d for r in rules) for d in range(K + 1)]}
    return {"identity": ident, "design_seed": design.design_seed, "design_redraws": design.redraws, "n": n,
            "predictions_sha256": digest, "predictions": preds, "outcomes": outcomes}
