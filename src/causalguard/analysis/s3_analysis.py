"""Offline S3 analysis (secondary study; development pilot = exploratory).

Primary S3 contrast (protocol): D vs B on final-verdict balanced accuracy, world-clustered
bootstrap (balanced accuracy pooled over the resampled worlds' items).  Secondary: C - B,
D_label - B, D - A, transfer T_D vs A(target item), T_A vs A(target item).  Mock/replay
records are refused by the scorer.  Reads raw records only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from ..experiments.s3 import per_world_scores, score
from ..runner import ROOT, read_jsonl
from ..s3_tasks import VERDICT_LABELS
from ..stats import balanced_accuracy_from_counts, cluster_bootstrap


def _counts(rows, arm):
    out = np.zeros((len(rows), len(VERDICT_LABELS), 2))
    ok = np.zeros(len(rows), bool)
    for w, r in enumerate(rows):
        st = r["arms"].get(arm)
        if st is None:
            continue
        ok[w] = True
        for k, c in enumerate(VERDICT_LABELS):
            out[w, k] = st["by_class"][c]
    return out, ok


def contrast_balanced(rows, a, b, reps=5000, seed=20261109):
    ca, oka = _counts(rows, a)
    cb, okb = _counts(rows, b)
    keep = oka & okb
    ca, cb = ca[keep], cb[keep]
    if not len(ca):
        return None
    stat = lambda idx: balanced_accuracy_from_counts(ca[idx].sum(0)) - balanced_accuracy_from_counts(cb[idx].sum(0))  # noqa: E731
    r = cluster_bootstrap(stat, len(ca), reps, seed)
    r.update(a=a, b=b, metric="balanced_accuracy", mean_a=balanced_accuracy_from_counts(ca.sum(0)),
             mean_b=balanced_accuracy_from_counts(cb.sum(0)))
    return r


def contrast_accuracy(rows, a, b, reps=5000, seed=20261109):
    pairs = [(r["arms"][a]["correct"] / r["arms"][a]["n_items"], r["arms"][b]["correct"] / r["arms"][b]["n_items"])
             for r in rows if a in r["arms"] and b in r["arms"] and r["arms"][a]["n_items"] and r["arms"][b]["n_items"]]
    if not pairs:
        return None
    d = np.array([x - y for x, y in pairs])
    r = cluster_bootstrap(lambda idx: float(d[idx].mean()), len(d), reps, seed)
    r.update(a=a, b=b, metric="per-world accuracy (paired)")
    return r


def contrast_transfer(rows, arm, reps=5000, seed=20261109):
    pairs = [(r["transfer"][arm]["correct"], r["transfer"][arm]["A_target_correct"]) for r in rows
             if arm in r.get("transfer", {})]
    if not pairs:
        return None
    d = np.array([x - y for x, y in pairs], dtype=float)
    r = cluster_bootstrap(lambda idx: float(d[idx].mean()), len(d), reps, seed)
    r.update(a=arm, b="A(target item)", metric="target-item accuracy (paired)")
    return r


def shortcut_baselines(salt: str, indices: list[int]) -> dict:
    """Trivial/surface baselines on the same S3 items (no model): always the most common verdict, and a
    surface rule (observation budget, horizon, intervention kind) -> most common verdict, fit on even world
    indices and evaluated on odd ones.  Detects label shortcuts in the task construction."""
    from collections import Counter, defaultdict

    from ..s3_tasks import make_s3_items
    items = []
    for i in indices:
        d = make_s3_items(salt, i)
        for it in d["private"]["items"]:
            q = it["query"]
            items.append((i, (d["private"]["budget"], q["horizon"], q["intervention"]["kind"]), it["verdict"]))
    train = [x for x in items if x[0] % 2 == 0]
    test = [x for x in items if x[0] % 2 == 1]
    maj = Counter(v for _, _, v in train).most_common(1)[0][0]
    table = defaultdict(Counter)
    for _, f, v in train:
        table[f][v] += 1
    rule = {f: c.most_common(1)[0][0] for f, c in table.items()}

    def score(pred):
        by = {c: [0, 0] for c in VERDICT_LABELS}
        for (_, _f, v), p in zip(test, pred):
            by[v][0] += 1
            by[v][1] += int(p == v)
        rec = [by[c][1] / by[c][0] for c in VERDICT_LABELS if by[c][0]]
        return {"accuracy": sum(b[1] for b in by.values()) / len(test), "balanced_accuracy": sum(rec) / len(rec)}
    return {"n_test_items": len(test), "majority_verdict": maj, "majority": score([maj] * len(test)),
            "surface_rule": score([rule.get(f, maj) for _, f, _ in test])}


def analyze(run_ids: list[str], out_dir: Path, reps: int = 5000) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {}
    for rid in run_ids:
        recs = read_jsonl(ROOT / "runs" / rid / "records.jsonl")
        fails = read_jsonl(ROOT / "runs" / rid / "failures.jsonl")
        if not recs:
            result[rid] = {"status": "no records"}
            continue
        rows = per_world_scores(recs)          # refuses mock/replay mixing
        sc = score(recs)
        res = {"n_worlds": len(rows), "runner_failures": len(fails), "provider_kind": sc["provider_kind"],
               "provider_metadata": recs[0].get("provider_metadata"), "pooled": sc,
               "primary_D_minus_B_balanced_accuracy": contrast_balanced(rows, "D", "B", reps),
               "secondary": {
                   "C-B_balanced": contrast_balanced(rows, "C", "B", reps),
                   "D_label-B_balanced": contrast_balanced(rows, "D_label", "B", reps),
                   "D-A_balanced": contrast_balanced(rows, "D", "A", reps),
                   "B-A_balanced": contrast_balanced(rows, "B", "A", reps),
                   "E-A_balanced": contrast_balanced(rows, "E", "A", reps),
                   "D-B_accuracy": contrast_accuracy(rows, "D", "B", reps),
                   "T_D-A_target": contrast_transfer(rows, "T_D", reps),
                   "T_A-A_target": contrast_transfer(rows, "T_A", reps)}}
        # natural verdict distribution of the items actually asked
        res["verdict_distribution"] = {c: int(sum(r["arms"]["A"]["by_class"][c][0] for r in rows if "A" in r["arms"]))
                                       for c in VERDICT_LABELS}
        # verdict/probability coherence per call kind (a model may use the probability channel as
        # P(claim true/false) instead of confidence over the three statuses; Brier is then not calibration)
        from collections import Counter
        coh = {}
        for r in recs:
            calls = r["calls"].values() if isinstance(r["calls"], dict) else r["calls"]
            for c in calls:
                kind = c["call_id"].split("/")[-1].split("#")[0]
                p = c.get("parsed") or {}
                if p.get("probs_valid") and p.get("verdict_valid"):
                    coh.setdefault(kind, Counter())["mismatch" if "verdict_prob_mismatch" in p.get("flags", []) else "coherent"] += 1
        res["verdict_probability_coherence_by_call"] = {k: {**dict(v), "mismatch_rate": v["mismatch"] / sum(v.values())}
                                                       for k, v in sorted(coh.items())}
        res["shortcut_baselines"] = shortcut_baselines(recs[0]["salt"], sorted(r["world_index"] for r in recs))
        result[rid] = res
    (out_dir / "s3_summary.json").write_text(json.dumps(result, indent=1, sort_keys=True, default=str))
    digest = hashlib.sha256((out_dir / "s3_summary.json").read_bytes()).hexdigest()
    return {"digest": digest, "runs": {k: {kk: v.get(kk) for kk in ("n_worlds", "primary_D_minus_B_balanced_accuracy")}
                                       for k, v in result.items() if isinstance(v, dict)}}
