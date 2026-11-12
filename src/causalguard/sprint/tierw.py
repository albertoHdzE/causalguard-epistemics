"""R7b Tier W (wiring given), pre-sprint: exact reference, derivations, the verifier and forged checks.

Class.  The public task lists, for every node j, its input nodes I_j (the essential inputs of the hidden rule,
|I_j| <= 3).  Each node's next value is a fixed but unknown function of I_j, which it may ignore in part.  A
mechanism is a filling of every node's truth table over I_j; a fitting mechanism agrees with every unclamped
observed coordinate.  Under the uniform prior over distinct mechanisms every unobserved table entry is an
independent fair bit, so:

  * a node's next value at a state is settled exactly when its input combination at that state appears in an
    evidence row where the node was not clamped (the ENTRY is observed); otherwise both values are possible;
  * |V_W(D)| = 2^F, F = number of unobserved entries over all nodes, and a claim's count num is an exact integer.

Two independent exact implementations, which must agree on (num, den) for every claim:

  1. ``lazy_counts`` (direct): evaluate the claim's target lazily along its trajectory, reading table entries
     from the evidence; when an unobserved entry is first needed, branch on its two values.  A leaf with a
     assumed entries carries 2^(F - a) mechanisms.
  2. ``vs_counts`` (existing engines): the explicit version-space engine of ``versionspace`` with each node's
     candidate set restricted to rules whose essential inputs are a subset of I_j (= every table on I_j), plus the
     SAT verdict on the same restricted space.

Cross-tier test: every Tier W mechanism is a Tier H (H(8, 3)) mechanism, so a claim settled on Tier H must be
settled the same way on Tier W for the same evidence (``cross_tier``).

Derivation (``derive``): the lookups the lazy evaluation performs, each with step, node, input values and either
the evidence row that shows the entry or the statement that no row does, and a two-way case split where an
unobserved entry is needed.  ``verify`` checks a derivation against the PUBLIC evidence and wiring only.  A forged
derivation (``forge``) is the derivation under an evidence table with ONE entry altered (a row cited for an input
combination it does not show; a wrong next value for a cited row; or 'no row shows this' where a row does),
chosen by hash among the alterations that change the status; it always fails ``verify``.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from fractions import Fraction

from ..schema import Evidence, Query

ENT, REF, UND = "entailed", "refuted", "underdetermined"
FORGERY_KINDS = ("phantom_row", "wrong_value", "hidden_row")
DERIVATION_CAP = 16          # rendered lines per claim; longer derivations make the claim ineligible to be named
TIERW_VERSION = "r7b-tierw-v1"


def _h(*parts) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


def _bits(x: int, n: int) -> str:
    return "".join(str((x >> i) & 1) for i in range(n))


def wiring_of(net) -> list[list[int]]:
    """Each node's listed inputs = the essential inputs of the hidden rule (ascending)."""
    return [sorted(r.canonical().inputs) for r in net.rules]


def status_of(num: int, den: int) -> str:
    return REF if num == 0 else ENT if num == den else UND


# --------------------------------------------------------------------------- the evidence table (public)

Key = tuple            # (node, ((input, value), ...))


@dataclass
class Table:
    """Observed table entries from the public evidence: key -> (value, first row number (1-based) showing it).
    ``rows_showing`` lists every row number showing a key (the verifier and the forgeries use it)."""
    n: int
    wiring: list[list[int]]
    entries: dict = field(default_factory=dict)
    rows_showing: dict = field(default_factory=dict)
    rows: list = field(default_factory=list)          # [(effective start state, {node: next value})]

    @classmethod
    def from_public(cls, pub: dict) -> "Table":
        n, W = pub["n"], [list(x) for x in pub["wiring"]]
        t = cls(n, W)
        for i, o in enumerate(Evidence.from_json(pub["evidence"]).observations, 1):
            m, v = o.intervention.masks
            s = (o.state & ~m) | v if o.intervention.kind != "none" else o.state
            obs = dict(o.observed)
            t.rows.append((s, obs))
            for j, val in obs.items():
                key = (j, tuple((a, (s >> a) & 1) for a in W[j]))
                if key in t.entries and t.entries[key][0] != val:
                    raise AssertionError(f"evidence contradicts the listed wiring at node {j}")
                t.entries.setdefault(key, (val, i))
                t.rows_showing.setdefault(key, []).append(i)
        return t

    def free_entries(self) -> int:
        return sum((1 << len(self.wiring[j])) for j in range(self.n)) - len(self.entries)


class _Need(Exception):
    def __init__(self, key):
        self.key = key


@dataclass
class Lookup:
    step: int
    node: int
    inputs: tuple            # ((input node, value at step-1), ...)
    source: str              # 'row' | 'none' (no row shows it: case split follows) | 'case' (assumed earlier)
    row: int | None
    value: int | None        # None for 'none'

    def to_json(self) -> dict:
        return {"step": self.step, "node": self.node, "inputs": [list(x) for x in self.inputs],
                "source": self.source, "row": self.row, "value": self.value}

    @staticmethod
    def from_json(d: dict) -> "Lookup":
        return Lookup(d["step"], d["node"], tuple(tuple(x) for x in d["inputs"]), d["source"], d["row"],
                      d["value"])


def _claim_parts(q: Query, n: int):
    from ..versionspace import point_query_parts
    x0 = point_query_parts(q, n)
    m, v = q.intervention.masks
    s0 = (x0 & ~m) | v if q.intervention.kind != "none" else x0
    clamp = dict(q.intervention.assign) if q.intervention.kind == "persistent_clamp" else {}
    return s0, clamp


def _evaluate(table: Table, q: Query, assume: dict, entries: dict | None = None):
    """Lazy evaluation of the claim target under the evidence table (or the altered ``entries``) and the assumed
    unobserved entries.  Returns (target value, lookups in evaluation order); raises _Need(key) at the first
    unobserved, unassumed entry (the lookups made so far are attached to the exception)."""
    ent = table.entries if entries is None else entries
    n = table.n
    s0, clamp = _claim_parts(q, n)
    memo: dict = {}
    looks: list[Lookup] = []

    def val(j: int, t: int) -> int:
        if t == 0:
            return (s0 >> j) & 1
        if j in clamp:
            return clamp[j]
        if (j, t) in memo:
            return memo[(j, t)]
        ins = tuple((a, val(a, t - 1)) for a in table.wiring[j])
        key = (j, ins)
        if key in ent:
            v, row = ent[key]
            looks.append(Lookup(t, j, ins, "row", row, v))
        elif key in assume:
            v = assume[key]
            looks.append(Lookup(t, j, ins, "case", None, v))
        else:
            looks.append(Lookup(t, j, ins, "none", None, None))
            e = _Need(key)
            e.looks = looks
            raise e
        memo[(j, t)] = v
        return v
    return val(q.target.node, q.horizon), looks


# --------------------------------------------------------------------------- implementation 1: direct

def lazy_counts(table: Table, q: Query, entries: dict | None = None) -> tuple[int, int]:
    """Exact (num, den) over every filling of the unobserved entries: depth-first over the entries the claim
    needs, each leaf weighted by 2^(F - assumed)."""
    F = table.free_entries() if entries is None else \
        sum(1 << len(w) for w in table.wiring) - len(entries)
    num = 0
    stack = [{}]
    while stack:
        a = stack.pop()
        try:
            v, _ = _evaluate(table, q, a, entries)
        except _Need as e:
            stack.append({**a, e.key: 1})
            stack.append({**a, e.key: 0})
            continue
        if v == q.target.value:
            num += 1 << (F - len(a))
    return num, 1 << F


# --------------------------------------------------------------------------- implementation 2: existing engines

def restricted_space(evidence: Evidence, wiring: list[list[int]], k: int = 3):
    """The explicit version space of H(n, k) with node j's candidates restricted to rules whose essential inputs
    are a subset of I_j: exactly the Tier W class."""
    import numpy as np

    from ..schema import HypothesisClass
    from ..versionspace import VersionSpace, build_version_space
    vs = build_version_space(evidence, HypothesisClass(evidence.n, k))
    comp = []
    for j, c in enumerate(vs.compatible):
        allowed = set(wiring[j])
        comp.append(np.array([i for i in c if set(vs.cls.rules[i].inputs) <= allowed], dtype=c.dtype))
    return VersionSpace(vs.cls, vs.evidence, comp)


def vs_counts(vs, q: Query, sat: bool = True, wiring: list | None = None) -> tuple[int, int, str | None]:
    """Explicit engine counts on the restricted space; SAT verdict on the Tier W encoding (``wiring``)."""
    from ..schema import Network
    from ..versionspace import exact_query_counts, verdict
    num, den = exact_query_counts(vs, q)
    if not sat:
        return num, den, None
    r = verdict(vs, q, wiring=wiring)
    for m in r.certificate.witness_models:          # SAT witnesses must lie in the Tier W class
        net = Network.from_json(m)
        if wiring is not None and any(not set(rl.inputs) <= set(wiring[j]) for j, rl in enumerate(net.rules)):
            raise AssertionError("Tier W SAT witness uses an unlisted input")
    return num, den, r.verdict.value


def reference_w(pub: dict, hidden_net=None, sat: bool = True) -> dict:
    """Tier W reference per claim; raises if the two implementations (or SAT) disagree on any claim."""
    table = Table.from_public(pub)
    ev = Evidence.from_json(pub["evidence"])
    vs = restricted_space(ev, table.wiring, pub["k"])
    out = {}
    for c in pub["claims"]:
        q = Query.from_json(c["query"])
        a = lazy_counts(table, q)
        num, den, sv = vs_counts(vs, q, sat, table.wiring)
        if a != (num, den):
            raise AssertionError(f"Tier W mismatch (lazy vs engine) on {c['cid']}: {a} vs {(num, den)}")
        st = status_of(num, den)
        if sat and sv != st:
            raise AssertionError(f"Tier W mismatch (engine vs SAT) on {c['cid']}")
        r = {"status": st, "num": str(num), "den": str(den), "p_star": num / den, "h": q.horizon,
             "iv": q.intervention.kind}
        if hidden_net is not None:
            from ..versionspace import predict
            r["truth"] = int(predict(hidden_net, q))
        out[c["cid"]] = r
    return out


def cross_tier(ref_h: dict, ref_w: dict) -> list[str]:
    """Claims settled on Tier H must be settled the same way on Tier W (same evidence).  Returns violations."""
    return [c for c, r in ref_h.items() if r["status"] != UND and ref_w[c]["status"] != r["status"]]


# --------------------------------------------------------------------------- derivations

def derive(table: Table, q: Query, entries: dict | None = None) -> dict:
    """The derivation tree: {"looks": [Lookup...], "cases": None | [tree_if_0, tree_if_1], "value": v | None}.
    Each case subtree continues AFTER the 'none' lookup that opens the split."""
    def go(assume: dict, skip: int) -> dict:
        try:
            v, looks = _evaluate(table, q, assume, entries)
            return {"looks": [x.to_json() for x in looks[skip:]], "cases": None, "value": v}
        except _Need as e:
            looks = e.looks
            return {"looks": [x.to_json() for x in looks[skip:]], "key": [e.key[0], [list(x) for x in e.key[1]]],
                    "cases": [go({**assume, e.key: b}, len(looks)) for b in (0, 1)], "value": None}
    return go({}, 0)


def leaves(tree: dict) -> list[int]:
    return [tree["value"]] if tree["cases"] is None else leaves(tree["cases"][0]) + leaves(tree["cases"][1])


def tree_status(tree: dict, target_value: int) -> str:
    hold = [v == target_value for v in leaves(tree)]
    return ENT if all(hold) else REF if not any(hold) else UND


def _ins(ins, L) -> str:
    return ", ".join(f"{L[a]}={b}" for a, b in ins) if ins else "no inputs"


def render(tree: dict, q: Query, pub: dict, cid: str, status: str) -> list[str]:
    """Rendered derivation lines for one claim (the P3 / P4 block).  Indentation marks case nesting."""
    L = pub["node_labels"]
    word = {ENT: "settled TRUE", REF: "settled FALSE", UND: "NOT SETTLED"}[status]
    tname = L[q.target.node]
    out = [f"{cid}: {word}."]

    def go(t: dict, ind: str) -> None:
        for x in t["looks"]:
            lk = Lookup.from_json(x)
            head = f"{ind}step {lk.step}: {L[lk.node]} reads {_ins(lk.inputs, L)}"
            if lk.source == "row":
                out.append(f"{head}; row #{lk.row:02d} shows {L[lk.node]} -> {lk.value}.")
            elif lk.source == "case":
                out.append(f"{head}; same inputs as assumed above, so {L[lk.node]} -> {lk.value}.")
            else:
                out.append(f"{head}; no evidence row shows these inputs, so {L[lk.node]} can be 0 or 1.")
        if t["cases"] is None:
            out.append(f"{ind}=> {tname} = {t['value']} after {q.horizon} step(s).")
            return
        j = t["key"][0]
        for b in (0, 1):
            out.append(f"{ind}if {L[j]} -> {b}:")
            go(t["cases"][b], ind + "  ")
    go(tree, "  ")
    return out


def derivation_lines(table: Table, q: Query, pub: dict, cid: str, entries: dict | None = None) -> tuple[list[str], dict, str]:
    tree = derive(table, q, entries)
    st = tree_status(tree, q.target.value)
    return render(tree, q, pub, cid, st), tree, st


# --------------------------------------------------------------------------- verifier (public evidence only)

def verify(pub: dict, cid: str, tree: dict, status: str, lines: list[str]) -> list[str]:
    """Check one claim's derivation against the public evidence and wiring.  Returns the list of problems
    (empty = the derivation is valid and proves ``status``)."""
    table = Table.from_public(pub)
    L = pub["node_labels"]
    c = {x["cid"]: x for x in pub["claims"]}[cid]
    q = Query.from_json(c["query"])
    s0, clamp = _claim_parts(q, table.n)
    probs: list[str] = []
    if render(tree, q, pub, cid, status) != lines:
        probs.append("rendered text does not match the derivation")

    def known(j: int, t: int, vals: dict):
        if t == 0:
            return (s0 >> j) & 1
        if j in clamp:
            return clamp[j]
        return vals.get((j, t))

    def walk(t: dict, vals: dict, assumed: dict) -> list[int] | None:
        vals, assumed = dict(vals), dict(assumed)
        for x in t["looks"]:
            lk = Lookup.from_json(x)
            if lk.node in clamp or lk.step < 1:
                probs.append(f"step {lk.step}: {L[lk.node]} is clamped or not an update")
                return None
            if [a for a, _ in lk.inputs] != table.wiring[lk.node]:
                probs.append(f"step {lk.step}: {L[lk.node]} inputs differ from its listed wiring")
                return None
            for a, b in lk.inputs:
                kv = known(a, lk.step - 1, vals)
                if kv is None or kv != b:
                    probs.append(f"step {lk.step}: input {L[a]}={b} is not the value at step {lk.step - 1}")
                    return None
            key = (lk.node, tuple(lk.inputs))
            if lk.source == "row":
                if not (1 <= lk.row <= len(table.rows)):
                    probs.append(f"row #{lk.row} does not exist")
                    return None
                s, obs = table.rows[lk.row - 1]
                if lk.node not in obs:
                    probs.append(f"row #{lk.row:02d} does not observe {L[lk.node]} (clamped)")
                    return None
                if any(((s >> a) & 1) != b for a, b in lk.inputs):
                    probs.append(f"row #{lk.row:02d} does not show inputs {_ins(lk.inputs, L)}")
                    return None
                if obs[lk.node] != lk.value:
                    probs.append(f"row #{lk.row:02d} shows {L[lk.node]} -> {obs[lk.node]}, not {lk.value}")
                    return None
                vals[(lk.node, lk.step)] = lk.value
            elif lk.source == "case":
                if assumed.get(key) != lk.value:
                    probs.append(f"step {lk.step}: {L[lk.node]} -> {lk.value} was not assumed")
                    return None
                vals[(lk.node, lk.step)] = lk.value
            elif lk.source == "none":
                if key in table.entries:
                    probs.append(f"step {lk.step}: 'no evidence row shows' {L[lk.node]} with {_ins(lk.inputs, L)}, "
                                 f"but row #{table.entries[key][1]:02d} does")
                    return None
                if x is not t["looks"][-1] or t["cases"] is None:
                    probs.append("an unobserved entry is not followed by a case split")
                    return None
                out = []
                for b in (0, 1):
                    r = walk(t["cases"][b], {**vals, (lk.node, lk.step): b}, {**assumed, key: b})
                    if r is None:
                        return None
                    out += r
                return out
            else:
                probs.append(f"unknown source {lk.source}")
                return None
        if t["cases"] is not None:
            probs.append("a case split without an unobserved entry")
            return None
        v = known(q.target.node, q.horizon, vals)
        if v is None or v != t["value"]:
            probs.append(f"the conclusion {L[q.target.node]} = {t['value']} is not established")
            return None
        return [v]
    res = walk(tree, {}, {})
    if res is not None:
        hold = [v == q.target.value for v in res]
        derived = ENT if all(hold) else REF if not any(hold) else UND
        if derived != status:
            probs.append(f"the stated status {status} does not follow (derivation gives {derived})")
    return probs


# --------------------------------------------------------------------------- forgeries

def _keys_in(tree: dict) -> list[tuple]:
    out = []
    for x in tree["looks"]:
        lk = Lookup.from_json(x)
        out.append(((lk.node, tuple(lk.inputs)), lk.source))
    for c in tree["cases"] or []:
        out += _keys_in(c)
    seen, res = set(), []
    for k, s in out:
        if (k, s) not in seen:
            seen.add((k, s))
            res.append((k, s))
    return res


def forgery_candidates(table: Table, q: Query, true_status: str) -> list[dict]:
    """Every single-entry alteration of the evidence table on the claim's path that changes the status.  Each
    candidate: kind, key, the altered entries and the forged status."""
    tree = derive(table, q)
    cands = []
    for key, src in _keys_in(tree):
        j = key[0]
        if src == "row":
            v, row = table.entries[key]
            alts = [("wrong_value", {**table.entries, key: (1 - v, row)}, None)]
            hid = dict(table.entries)
            del hid[key]
            alts.append(("hidden_row", hid, None))
        elif src == "none":
            rows = [i for i, (_, obs) in enumerate(table.rows, 1) if j in obs]
            if not rows:
                continue
            alts = []
            for b in (0, 1):
                r = min(rows, key=lambda i: _h("r7b-phantom-row", json.dumps(key), i))
                alts.append(("phantom_row", {**table.entries, key: (b, r)}, b))
        else:
            continue
        for kind, ent, b in alts:
            tr = derive(table, q, ent)
            st = tree_status(tr, q.target.value)
            if st != true_status:
                cands.append({"kind": kind, "key": key, "entries": ent, "status": st, "value": b})
    return cands


def forge(table: Table, q: Query, pub: dict, cid: str, true_status: str, salt: str) -> dict | None:
    """The forged check for one claim, by hash of (salt, task id, claim id): kind first (among kinds that can
    change the status), then the alteration.  None if no single alteration changes the status."""
    cands = forgery_candidates(table, q, true_status)
    if not cands:
        return None
    tid = pub["task_id"]
    kinds = sorted({c["kind"] for c in cands}, key=lambda k: _h(salt, "kind", tid, cid, k))
    pool = [c for c in cands if c["kind"] == kinds[0]]
    c = min(pool, key=lambda c: _h(salt, "alt", tid, cid, json.dumps(c["key"]), c["value"]))
    lines, tree, st = derivation_lines(table, q, pub, cid, c["entries"])
    return {"kind": c["kind"], "key": [c["key"][0], [list(x) for x in c["key"][1]]], "status": st,
            "lines": lines, "tree": tree, "n_candidates": len(cands), "kinds_available": sorted(kinds)}


def claim_package(pub: dict, cid: str, salt: str, table: Table | None = None) -> dict:
    """Everything Task P needs for one Tier W claim, from the PUBLIC task only: the valid derivation, its status,
    the forged derivation, and eligibility (both within the cap and a forgery exists)."""
    table = table or Table.from_public(pub)
    c = {x["cid"]: x for x in pub["claims"]}[cid]
    q = Query.from_json(c["query"])
    lines, tree, st = derivation_lines(table, q, pub, cid)
    f = forge(table, q, pub, cid, st, salt)
    eligible = len(lines) <= DERIVATION_CAP and f is not None and len(f["lines"]) <= DERIVATION_CAP
    return {"cid": cid, "status": st, "lines": lines, "tree": tree, "forged": f, "eligible": eligible,
            "n_lines": len(lines), "n_lines_forged": len(f["lines"]) if f else None,
            "p_star": float(Fraction(*lazy_counts(table, q)))}
