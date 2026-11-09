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
        result[rid] = res
    (out_dir / "s3_summary.json").write_text(json.dumps(result, indent=1, sort_keys=True, default=str))
    digest = hashlib.sha256((out_dir / "s3_summary.json").read_bytes()).hexdigest()
    return {"digest": digest, "runs": {k: {kk: v.get(kk) for kk in ("n_worlds", "primary_D_minus_B_balanced_accuracy")}
                                       for k, v in result.items() if isinstance(v, dict)}}
