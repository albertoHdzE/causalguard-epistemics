"""R7 surface reference rule (declared and fitted before any model output; train split only, no model).

The question it answers: can a simple reader of the public text recover a claim's status without reasoning about
mechanisms?  If so the benchmark is broken (protocol section 7, gate 'not readable from the surface').

Features of a claim, all computed from the PUBLIC task:
  h          horizon (1, 2, 3)
  kind       initial_edit | persistent_clamp
  dist       Hamming distance from the claim's effective start state to the nearest observed effective start
             state, bucketed 1 / 2 / >= 3
  copy       the target node's observed next value in the nearest observed row(s) (ties: all rows at that
             distance with the target observed), compared with the asserted value: agree / disagree / mixed or
             unobserved   ("copy the outcome of the most similar observed experiment")
  column     the target node's observed next values over ALL evidence rows: constant and equal to the asserted
             value / constant and different / not constant

Rule: a lookup table over the 162 feature cells fitted on the train split.  The status predicted in a cell is the
argmax of count(status) / base_rate(status) (class-reweighted, so the table maximises balanced accuracy rather
than copying the majority); the probability is the mean p* of train claims in the cell.  Empty cells fall back to
the marginal (reweighted) status and the marginal mean p*.  The fitted table is committed before any model output.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict

from ..schema import Evidence, Query

STATUSES = ("entailed", "refuted", "underdetermined")
RULE_VERSION = "r7-surface-table-v1"


def _eff(x: int, iv) -> int:
    m, v = iv.masks
    return (x & ~m) | v if iv.kind != "none" else x


def features(pub: dict) -> dict[str, tuple]:
    from ..versionspace import point_query_parts
    n = pub["n"]
    ev = Evidence.from_json(pub["evidence"])
    rows = [(_eff(o.state, o.intervention), dict(o.observed)) for o in ev.observations]
    out = {}
    for c in pub["claims"]:
        q = Query.from_json(c["query"])
        s0 = _eff(point_query_parts(q, n), q.intervention)
        t, val = q.target.node, q.target.value
        obs = [(bin(s0 ^ s).count("1"), o[t]) for s, o in rows if t in o]
        if obs:
            d = min(x for x, _ in obs)
            near = {v for x, v in obs if x == d}
            copy = ("agree" if near == {val} else "disagree") if len(near) == 1 else "mixed"
            col = {v for _, v in obs}
            column = ("const_agree" if col == {val} else "const_disagree") if len(col) == 1 else "varies"
        else:
            d, copy, column = 99, "mixed", "varies"
        out[c["cid"]] = (q.horizon, q.intervention.kind, min(d, 3), copy, column)
    return out


def fit(items: list[tuple[dict, dict]]) -> dict:
    """items: (public task, reference {cid: {status, p_star}}).  Returns the serialisable rule table."""
    cells: dict = defaultdict(lambda: {"n": Counter(), "p": []})
    base = Counter()
    allp = []
    for pub, ref in items:
        for cid, f in features(pub).items():
            r = ref[cid]
            cells[f]["n"][r["status"]] += 1
            cells[f]["p"].append(r["p_star"])
            base[r["status"]] += 1
            allp.append(r["p_star"])
    tot = sum(base.values())
    rate = {s: base[s] / tot for s in STATUSES}

    def pick(cnt: Counter) -> str:
        return max(STATUSES, key=lambda s: (cnt[s] / rate[s] if rate[s] else 0.0, -STATUSES.index(s)))
    table = {json.dumps(list(f)): {"status": pick(v["n"]), "p": sum(v["p"]) / len(v["p"]),
                                   "n": sum(v["n"].values())} for f, v in sorted(cells.items())}
    rule = {"version": RULE_VERSION, "train_claims": tot, "base_rates": rate, "table": table,
            "fallback": {"status": pick(base), "p": sum(allp) / len(allp)}}
    rule["sha256"] = hashlib.sha256(json.dumps({k: v for k, v in rule.items() if k != "sha256"},
                                               sort_keys=True).encode()).hexdigest()
    return rule


def predict(rule: dict, pub: dict) -> dict[str, dict]:
    out = {}
    for cid, f in features(pub).items():
        cell = rule["table"].get(json.dumps(list(f)), rule["fallback"])
        out[cid] = {"verdict": cell["status"], "probability": cell["p"]}
    return out
