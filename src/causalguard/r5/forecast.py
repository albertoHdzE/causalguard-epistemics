"""Track G runner item: predictions from the PUBLIC payload only, then evaluator-side outcomes.

``g_world(payload)`` (runner item; no model calls):
  1. the evaluator builds the hidden mechanism (synthetic instance or pinned external model) and the design;
  2. for each nested budget 8/16/24 it serializes the public payload and calls ``predict_public(json)``, a pure
     function of public data (evidence, class, queries); the leakage audit runs on every payload;
  3. the SHA-256 of all predictions is recorded BEFORE any outcome is computed;
  4. outcomes (hidden target-node values) and logical status are attached for scoring.
Predictors: the S4 Averager codes (uniform, index, circuit, gate, cgh_flat = analytic-only CGH, cgh_prior = full
CGH prior FLAT+TEMPLATE+MODULE without patches/DICT, and the *_noanalytic ablations), GSR(alpha) generic structured
priors, and the single shortest cgh_prior / index model (secondary).  Probabilities are P(node = 1).
"""
from __future__ import annotations

import hashlib
import json
import time

from ..s4.tasks import audit_public_payload
from ..schema import Evidence, Query
from . import data as D
from .contracts import Prediction
from .priors import ALPHAS, AVERAGER_CODES, GSR

SHORTEST = ("cgh_prior", "index")


def _node_prob(code_p, q: Query):
    """Literal -> node convention: a literal 'node = 0' would need 1 - P; R5 queries carry value 1 (asserted)."""
    if q.target.value != 1:
        raise ValueError("R5 queries carry literal value 1; P(literal) == P(node = 1)")
    return code_p


def predict_public(pub_json: str, snapshot: str = "") -> dict:
    """All predictor probabilities for every query of one public payload (JSON text)."""
    from ..s4.prior import Averager
    pub = json.loads(pub_json)
    bad = audit_public_payload(pub)
    if bad:
        raise AssertionError(f"public payload leak: {bad}")
    ev = Evidence.from_json(pub["evidence"])
    k = pub["k"]
    t0 = time.perf_counter()
    av = Averager(ev, k, codes=AVERAGER_CODES)
    t_av = time.perf_counter() - t0
    out = {"evidence_hash": pub["evidence_hash"], "struct_status": av.struct_status, "queries": [],
           "cost_s": {"averager_build": t_av}}
    if av.vs.empty:
        out["inconsistent"] = True
        for qd in pub["queries"]:
            out["queries"].append({"query_id": qd["query_id"], "predictions": {
                c: Prediction(qd["query_id"], "", snapshot, c, c, "inconsistent_evidence", None,
                              reason="empty V(D)").to_json() for c in list(AVERAGER_CODES) + list(ALPHAS)}})
        return out
    t0 = time.perf_counter()
    gsr = GSR(ev, k, vs=av.vs)
    out["cost_s"]["gsr_build"] = time.perf_counter() - t0
    from ..versionspace import exact_query_counts
    for qd in pub["queries"]:
        q = Query.from_json(qd["query"])
        qid = qd["query_id"]
        num_u, den_u = exact_query_counts(av.vs, q)
        row = {"query_id": qid, "h": q.horizon, "uniform_counts": [str(num_u), str(den_u)],
               "logical": "determined" if num_u in (0, den_u) else "underdetermined", "predictions": {}}
        for c in AVERAGER_CODES:
            t0 = time.perf_counter()
            f = av.probability_exact(c, q)
            dt = time.perf_counter() - t0
            if f is None:
                pr = Prediction(qid, "", snapshot, c, c, "refused_resource", None,
                                reason=f"struct enumeration {av.struct_status.get(c)}", cost_s=dt)
            else:
                pr = Prediction(qid, "", snapshot, c, c, "exact", _node_prob(float(f), q), num=str(f.numerator),
                                den=str(f.denominator), cost_s=dt)
            row["predictions"][c] = pr.to_json()
        t0 = time.perf_counter()
        ms = gsr.masses(q)
        dt = time.perf_counter() - t0
        for name, a in ALPHAS.items():
            r = gsr.probability(q, a, ms)
            row["predictions"][name] = Prediction(qid, "", snapshot, name, f"gsr-v1(alpha={a})", "bounded",
                                                  _node_prob(r["p"], q), lo=r["lo"], hi=r["hi"],
                                                  cost_s=dt).to_json()
        for c in SHORTEST:
            sp = av.shortest_prediction(c, q)
            row["predictions"][f"shortest_{c}"] = (
                Prediction(qid, "", snapshot, f"shortest_{c}", c, "exact", float(sp), num=str(sp), den="1").to_json()
                if sp is not None else
                Prediction(qid, "", snapshot, f"shortest_{c}", c, "refused_resource", None,
                           reason="struct enumeration refused").to_json())
        out["queries"].append(row)
    return out


def _instance(p: dict):
    if p.get("external_key"):
        from .external import load_instance
        net = load_instance(p["external_key"])
        return net, {"panel": p["panel"], "external_key": p["external_key"], "source_group_id": p["group"],
                     "mechanism_id": "x-" + hashlib.sha256(p["external_key"].encode()).hexdigest()[:16],
                     "split": "external", "transformation_id": p["transformation"]}
    inst = D.make_instance(p["split"], p["stratum"], p["index"])
    return inst.net, inst.identity()


def g_world(p: dict) -> dict:
    net, ident = _instance(p)
    key = ident["mechanism_id"]
    design = D.make_design(p["design_salt"], key, net.n)
    snapshot = p.get("run_snapshot", "")
    preds = {}
    for B in p.get("budgets", D.BUDGETS):
        ev = D.make_evidence(net, design, B)
        pub = D.public_payload(key, ev, design, net.n, D.K)
        preds[str(B)] = predict_public(json.dumps(pub, sort_keys=True), snapshot)
        preds[str(B)]["evidence_id"] = pub["evidence_hash"][:16]
        preds[str(B)]["public_task_id"] = pub["task_id"]
    digest = hashlib.sha256(json.dumps(preds, sort_keys=True).encode()).hexdigest()
    # ---- evaluator side: hidden outcomes (after the prediction digest is fixed)
    outcomes = {qid: D.outcome(net, q) for qid, q in design.queries}
    return {"identity": ident, "design_seed": design.design_seed, "design_redraws": design.redraws,
            "n": net.n, "predictions_sha256": digest, "predictions": preds, "outcomes": outcomes}
