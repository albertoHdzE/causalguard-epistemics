"""S3 — AI reasoning and transfer: one world per runner item, plus an offline scorer.

Information flow:
  public payload --> prompts --> model --> raw outputs --> parsed answers
  private record --> witness_feedback (D) / label_feedback (D_label) / solver_answer (E) only
  oracle (verdict, hidden_answer) --> stored under record['oracle'] --> score() / per_world_scores() only

Run / resume (see docs/S3_HARNESS.md):
  python -m causalguard.experiments.s3 --config configs/s3_pilot_qwen25_7b.json --run-id <id> --worlds 80 --quiet
The scorer never calls a model and refuses to mix mock/replay records with real ones.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from ..llm.harness import ARMS, CallBudget, WorldHarness
from ..llm.providers import BaseProvider, make_provider
from ..s3_tasks import VERDICT_LABELS, make_s3_items

NON_REAL = ("mock", "replay")
REVISION_ARMS = ("B", "D", "D_label")
TRANSFER_ARMS = ("T_A", "T_D")


def build_payload(cfg: dict, index: int, ledger: str | None = None) -> dict:
    t = cfg.get("task", {})
    return {"salt": cfg["salt"], "index": index, "n": t.get("n", 4), "k": t.get("k", 2),
            "items_per_world": t.get("items_per_world", 4), "provider": cfg["provider"],
            "harness": cfg.get("harness", {}), "caps": cfg.get("caps", {}), "ledger": ledger}


def run_world_with(provider: BaseProvider, p: dict) -> dict:
    d = make_s3_items(p["salt"], p["index"], n=p.get("n", 4), k=p.get("k", 2),
                      items_per_world=p.get("items_per_world", 4))
    public, private = d["public"], d["private"]
    try:
        md = provider.metadata() if p.get("fetch_metadata", True) else {"provider_kind": provider.kind}
    except Exception as e:  # metadata is never invented
        md = {"provider_kind": provider.kind, "error": repr(e)[:200]}
    caps = p.get("caps", {})
    budget = CallBudget(caps.get("calls_per_world"), caps.get("calls_total"), p.get("ledger"), public["world_id"])
    res = WorldHarness(provider, public, private, p.get("harness"), budget).run()
    oracle = {"items": [{"item_id": it["item_id"], "verdict": it["verdict"], "hidden_answer": it["hidden_answer"]}
                        for it in private["items"]], "budget": private["budget"],
              "version_space_counts": private["version_space_counts"]}
    return {"study": "S3", "world_id": public["world_id"], "world_index": p["index"], "salt": p["salt"],
            "provider_kind": provider.kind, "provider_metadata": md,
            "provider_config": {k: v for k, v in p["provider"].items() if k != "extra"},
            "harness_config": {**p.get("harness", {})}, "caps": caps,
            "items": [it["item_id"] for it in public["items"]], "n_observations": len(public["observations_text"]),
            **res, "oracle": oracle}


def run_world(p: dict) -> dict:
    """One S3 world.  Pure function of the payload (except for the provider and the cap ledger)."""
    return run_world_with(make_provider(p["provider"]), p)


# ---------------------------------------------------------------- offline scoring
def brier(probs: dict | None, y: str) -> float | None:
    if probs is None:
        return None
    return sum((probs[k] - (1.0 if k == y else 0.0)) ** 2 for k in VERDICT_LABELS)


def check_kinds(records: list[dict], allow_mock: bool = False) -> str:
    kinds = set()
    for r in records:
        k = r.get("provider_kind")
        if k is None:
            raise ValueError(f"record {r.get('world_id')} has no provider_kind")
        kinds.add(k)
        for c in r.get("calls", {}).values():
            if c.get("provider_kind") != k:
                raise ValueError(f"record {r.get('world_id')} mixes call provider kinds")
    if len(kinds) > 1:
        raise ValueError(f"refusing to score mixed provider kinds {sorted(kinds)}")
    if kinds & set(NON_REAL) and not allow_mock:
        raise ValueError(f"records are {sorted(kinds)}; pass allow_mock=True to score non-real outputs")
    return next(iter(kinds)) if kinds else "none"


def _final(r: dict, arm: str, i: int) -> dict:
    v = r.get("arms", {}).get(arm, {}).get(str(i))
    if v is None:
        return {"status": "not_run", "verdict": None, "verdict_valid": False, "probabilities": None,
                "probs_valid": False}
    return v["final"]


def _arm_items(r: dict, arm: str) -> list[int]:
    n = len(r["oracle"]["items"])
    if arm in TRANSFER_ARMS:
        return [int(r.get("harness_config", {}).get("transfer", {}).get("target_item", 1))]
    return list(range(n))


def _arms_of(r: dict) -> list[str]:
    return [a for a in ARMS if a in r.get("harness_config", {}).get("arms", ARMS)]


def _correct(f: dict, y: str) -> int:
    return int(bool(f["verdict_valid"]) and f["verdict"] == y)


def per_world_scores(records: list[dict], allow_mock: bool = False) -> list[dict]:
    """One row per world with per-arm sufficient statistics for a paired cluster bootstrap."""
    kind = check_kinds(records, allow_mock)
    rows = []
    for r in sorted(records, key=lambda x: x["world_id"]):
        ys = [it["verdict"] for it in r["oracle"]["items"]]
        row = {"world_id": r["world_id"], "world_index": r.get("world_index"), "provider_kind": kind,
               "world_status": r.get("world_status"), "arms": {}, "revisions": {}, "transfer": {}}
        for arm in _arms_of(r):
            st = {"n_items": 0, "correct": 0, "by_class": {c: [0, 0] for c in VERDICT_LABELS},
                  "brier_valid_sum": 0.0, "n_probs_valid": 0, "brier_worst_sum": 0.0, "status_counts": Counter(),
                  "item_correct": {}}
            for i in _arm_items(r, arm):
                f, y = _final(r, arm, i), ys[i]
                c = _correct(f, y)
                b = brier(f["probabilities"] if f["probs_valid"] else None, y)
                st["n_items"] += 1
                st["correct"] += c
                st["by_class"][y][0] += 1
                st["by_class"][y][1] += c
                st["status_counts"][f["status"]] += 1
                st["item_correct"][str(i)] = c
                if b is not None:
                    st["brier_valid_sum"] += b
                    st["n_probs_valid"] += 1
                st["brier_worst_sum"] += 2.0 if b is None else b
            n = st["n_items"]
            st["accuracy"] = st["correct"] / n if n else None
            st["brier_valid_mean"] = st["brier_valid_sum"] / st["n_probs_valid"] if st["n_probs_valid"] else None
            st["brier_worst_mean"] = st["brier_worst_sum"] / n if n else None
            st["validity_coverage"] = st["n_probs_valid"] / n if n else None
            st["status_counts"] = dict(st["status_counts"])
            row["arms"][arm] = st
        if "A" in row["arms"]:
            a_corr = row["arms"]["A"]["item_correct"]
            for arm in REVISION_ARMS:
                if arm in row["arms"]:
                    cnt = Counter()
                    for i, ca in a_corr.items():
                        cr = row["arms"][arm]["item_correct"][i]
                        cnt[{(1, 1): "correct_to_correct", (1, 0): "correct_to_wrong", (0, 1): "wrong_to_correct",
                             (0, 0): "wrong_to_wrong"}[(ca, cr)]] += 1
                    row["revisions"][f"{arm}_vs_A"] = {k: cnt.get(k, 0) for k in
                                                       ("correct_to_correct", "correct_to_wrong", "wrong_to_correct",
                                                        "wrong_to_wrong")}
            for arm in TRANSFER_ARMS:
                if arm in row["arms"]:
                    tgt = str(_arm_items(r, arm)[0])
                    row["transfer"][arm] = {"target_item": int(tgt), "correct": row["arms"][arm]["item_correct"][tgt],
                                            "A_target_correct": a_corr[tgt]}
        rows.append(row)
    return rows


def score(records: list[dict], allow_mock: bool = False) -> dict:
    """Pooled per-arm metrics (no resampling; the lead's paired cluster bootstrap consumes per_world_scores)."""
    rows = per_world_scores(records, allow_mock)
    out = {"provider_kind": rows[0]["provider_kind"] if rows else None, "n_worlds": len(rows),
           "world_status_counts": dict(Counter(r["world_status"] for r in rows)), "arms": {}, "revisions": {},
           "transfer": {}, "cost": {}}
    arms = sorted({a for r in rows for a in r["arms"]}, key=ARMS.index)
    for arm in arms:
        sts = [r["arms"][arm] for r in rows if arm in r["arms"]]
        n = sum(s["n_items"] for s in sts)
        nv = sum(s["n_probs_valid"] for s in sts)
        by = {c: [sum(s["by_class"][c][0] for s in sts), sum(s["by_class"][c][1] for s in sts)] for c in VERDICT_LABELS}
        recalls = {c: by[c][1] / by[c][0] for c in VERDICT_LABELS if by[c][0]}
        sc = Counter()
        for s in sts:
            sc.update(s["status_counts"])
        out["arms"][arm] = {
            "n_items": n, "accuracy": sum(s["correct"] for s in sts) / n if n else None,
            "balanced_accuracy": sum(recalls.values()) / len(recalls) if recalls else None,
            "per_class_recall": recalls, "class_counts": {c: by[c][0] for c in VERDICT_LABELS},
            "brier_valid_only": sum(s["brier_valid_sum"] for s in sts) / nv if nv else None,
            "validity_coverage": nv / n if n else None,
            "brier_worst_case": sum(s["brier_worst_sum"] for s in sts) / n if n else None,
            "status_counts": dict(sc)}
    for key in sorted({k for r in rows for k in r["revisions"]}):
        tot = Counter()
        for r in rows:
            tot.update(r["revisions"].get(key, {}))
        out["revisions"][key] = dict(tot)
    for arm in TRANSFER_ARMS:
        tr = [r["transfer"][arm] for r in rows if arm in r["transfer"]]
        if tr:
            out["transfer"][f"{arm}_vs_A_target"] = {
                "n_worlds": len(tr), f"{arm}_accuracy": sum(t["correct"] for t in tr) / len(tr),
                "A_target_accuracy": sum(t["A_target_correct"] for t in tr) / len(tr),
                "worse_than_A": sum(t["A_target_correct"] > t["correct"] for t in tr),
                "better_than_A": sum(t["A_target_correct"] < t["correct"] for t in tr)}
    phys = sum(r.get("cost", {}).get("physical", {}).get("attempts", 0) for r in records)
    logical = Counter()
    for r in records:
        for arm, c in r.get("cost", {}).get("logical_standalone_by_arm", {}).items():
            logical[arm] += c["attempts"]
    out["cost"] = {"physical_attempts": phys, "logical_standalone_attempts_by_arm": dict(logical),
                   "attempts_saved_by_sharing": sum(logical.values()) - phys}
    return out


def run_world_v2(p: dict) -> dict:
    """One S3 v2 world (task version s3-tasks-v2).  The record SAVES the actual task objects (public payload
    and private oracle/task record) so analysis never reconstructs assumed defaults."""
    from ..llm.harness import WorldHarnessV2
    from ..s3_tasks import make_s3_items_v2
    provider = make_provider(p["provider"])
    d = make_s3_items_v2(p["salt"], p["index"], n=p.get("n", 4), k=p.get("k", 2))
    public, private = d["public"], d["private"]
    try:
        md = provider.metadata() if p.get("fetch_metadata", True) else {"provider_kind": provider.kind}
    except Exception as e:  # metadata is never invented
        md = {"provider_kind": provider.kind, "error": repr(e)[:200]}
    caps = p.get("caps", {})
    budget = CallBudget(caps.get("calls_per_world"), caps.get("calls_total"), p.get("ledger"), public["world_id"])
    res = WorldHarnessV2(provider, public, private, p.get("harness"), budget).run()
    return {"study": "S3", "task_version": public["task_version"], "world_id": public["world_id"],
            "world_index": p["index"], "salt": p["salt"], "panel": p.get("panel"),
            "provider_kind": provider.kind, "provider_metadata": md,
            "provider_config": {k: v for k, v in p["provider"].items() if k != "extra"},
            "harness_config": {**p.get("harness", {})}, "caps": caps, **res,
            "task_public": public, "task_private": private}


def plan_s3(cfg: dict, run_id: str, ledger: str) -> dict:
    from ..runner import make_plan
    idx = list(range(cfg["world_index_start"], cfg["world_index_stop"]))
    items = [(f"s3v2|{cfg['salt']}|{cfg['provider']['model']}|w{i}",
              {**build_payload(cfg, i, ledger), "panel": cfg.get("panel")}) for i in idx]
    return make_plan(run_id, "S3", cfg, items, strata_fn=lambda p: {"world_index": p["index"], "panel": p["panel"]})


# ---------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    from ..runner import Run, default_runs_root, load_run
    ap = argparse.ArgumentParser(description="S3 v2 LLM harness run (resumable, runner v2)")
    ap.add_argument("--config", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--runs-root", default=None)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    cfg = json.loads(Path(a.config).read_text())
    if cfg.get("mode") != "development":
        raise SystemExit("this entry point runs development S3 only")
    if cfg.get("task_version") != "s3-tasks-v2":
        raise SystemExit("S3 v1 pilots are historical; reproduce them from tag v0.1.0-dev")
    root = Path(a.runs_root) if a.runs_root else default_runs_root()
    ledger = str(root / a.run_id / "call_ledger.jsonl")
    run = Run(a.run_id, plan_s3(cfg, a.run_id, ledger), runs_root=root, resume=a.resume)
    rcfg = cfg.get("runner", {})
    end = run.execute(run_world_v2, workers=int(rcfg.get("workers", 1)), timeout_s=float(rcfg.get("world_timeout_s", 3600)),
                      quiet=a.quiet, retry_failed=a.retry_failed, mode="development")
    lr = load_run(run.dir)
    print(json.dumps({"run": end, "results": len(lr["results"]), "failures": len(lr["failures"]),
                      "missing": len(lr["missing"])}, sort_keys=True))
    return 0 if end["status"] == "complete" else 3


if __name__ == "__main__":
    sys.exit(main())
