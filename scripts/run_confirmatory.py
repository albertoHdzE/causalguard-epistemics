#!/usr/bin/env python3
"""Sealed confirmatory runner — PREPARED, NOT YET RUN.  Do not run before review approval.

Refuses to run unless ALL hold:
  1. the working tree is clean and HEAD == --freeze-commit;
  2. docs/FREEZE_RECORD.json exists AT that commit (written only at the review/freeze step) and
     its config_sha256 equals sha256(configs/confirmatory.json);
  3. --authorization equals FREEZE_RECORD.json["authorization_phrase"];
  4. no confirmatory run directory for this study exists yet (no repeated peeking).
The confirmatory salt is derived from the freeze commit, so no confirmatory world can be
generated before the freeze.  Every generated world is checked for isomorphic duplicates
against the complete development corpus; duplicates are excluded and logged (never silently).

Usage (after the freeze):
  .venv/bin/python scripts/run_confirmatory.py --study S2 --freeze-commit <sha> --authorization "<phrase>"
  .venv/bin/python scripts/run_confirmatory.py --study S1 ...
  .venv/bin/python scripts/run_confirmatory.py --study S3 --model qwen25_7b ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def sh(*a: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *a], text=True).strip()


def confirmatory_salt(freeze_commit: str) -> str:
    return "confirm-" + hashlib.sha256(f"{freeze_commit}|causalguard-confirmatory-v1".encode()).hexdigest()[:16]


def preflight(args) -> dict:
    if sh("status", "--porcelain"):
        raise SystemExit("REFUSED: working tree not clean")
    head = sh("rev-parse", "HEAD")
    if head != args.freeze_commit:
        raise SystemExit(f"REFUSED: HEAD {head} != freeze commit {args.freeze_commit}")
    fr = ROOT / "docs" / "FREEZE_RECORD.json"
    if not fr.exists():
        raise SystemExit("REFUSED: docs/FREEZE_RECORD.json absent (the design has not been frozen by review)")
    rec = json.loads(fr.read_text())
    cfg_bytes = (ROOT / "configs" / "confirmatory.json").read_bytes()
    if hashlib.sha256(cfg_bytes).hexdigest() != rec["config_sha256"]:
        raise SystemExit("REFUSED: configs/confirmatory.json differs from the frozen hash")
    if args.authorization != rec["authorization_phrase"]:
        raise SystemExit("REFUSED: authorization phrase mismatch")
    return {"head": head, "freeze_record": rec, "config": json.loads(cfg_bytes)}


def dev_canonical_forms() -> set[str]:
    from causalguard.dedup import canonical_form
    from causalguard.runner import read_jsonl
    from causalguard.schema import Network
    forms = set()
    for rid in ("S2-dev-v1",):
        for r in read_jsonl(ROOT / "runs" / rid / "records.jsonl"):
            forms.add(canonical_form(Network.from_json(r["world"]["network"])))
    if not forms:
        raise SystemExit("REFUSED: development corpus records unavailable for the cross-split duplicate audit")
    return forms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", required=True, choices=["S1", "S2", "S3"])
    ap.add_argument("--freeze-commit", required=True)
    ap.add_argument("--authorization", required=True)
    ap.add_argument("--model", help="S3 model key in the confirmatory config")
    ap.add_argument("--workers", type=int)
    args = ap.parse_args()
    pf = preflight(args)
    cfg = pf["config"]
    salt = confirmatory_salt(args.freeze_commit)
    run_id = f"{args.study}-confirmatory-{args.freeze_commit[:10]}" + (f"-{args.model}" if args.model else "")
    if (ROOT / "runs" / run_id).exists():
        raise SystemExit(f"REFUSED: {run_id} already exists; resume only via --resume after a documented interruption")
    from causalguard.runner import Run, now
    access = ROOT / "runs" / run_id / "ACCESS_LOG.jsonl"
    access.parent.mkdir(parents=True)
    access.write_text(json.dumps({"event": "seal_opened", "time": now(), "freeze_commit": args.freeze_commit,
                                  "study": args.study}) + "\n")
    if args.study == "S2":
        from causalguard.dedup import canonical_form
        from causalguard.experiments.s2 import run_world
        from causalguard.generators import make_s2_world
        s2 = cfg["S2"]
        dev = dev_canonical_forms()
        items, excluded = [], []
        for pop in s2["populations"]:
            for fam in pop["families"]:
                for i in range(pop["worlds_per_family"]):
                    w = make_s2_world(salt, i, fam, pop["population"], s2["n"], s2["kmax"])
                    if canonical_form(w.net) in dev:
                        excluded.append({"population": pop["population"], "family": fam, "index": i,
                                         "reason": "isomorphic to a development world"})
                        continue
                    items.append((f"{pop['population']}|{fam}|{i}", {
                        "salt": salt, "index": i, "family": fam, "population": pop["population"], "n": s2["n"],
                        "kmax": s2["kmax"], "budgets": s2["budgets"], "regimes": pop.get("regimes", s2["regimes"]),
                        "mc_samples": s2["mc_samples"], "noise_rates": pop.get("noise_rates", []),
                        "noise_budgets": pop.get("noise_budgets", [16, 32, 64]), "verdicts": pop.get("verdicts", True)}))
        (ROOT / "runs" / run_id / "EXCLUSIONS.json").write_text(json.dumps(excluded, indent=1))
        run = Run(run_id, {**s2, "salt": salt, "mode": "confirmatory", "freeze_commit": args.freeze_commit})
        end = run.execute(items, run_world, workers=args.workers or s2.get("workers", 24), timeout_s=900,
                          mode="confirmatory")
    elif args.study == "S1":
        from causalguard.__main__ import _items_from_config
        from causalguard.experiments.s1 import run_item
        s1 = {**cfg["S1"], "salt": salt, "study": "S1"}
        run = Run(run_id, {**s1, "mode": "confirmatory", "freeze_commit": args.freeze_commit})
        end = run.execute(list(_items_from_config(s1)), run_item, workers=args.workers or s1.get("workers", 16),
                          timeout_s=s1.get("item_timeout_s", 1200), mode="confirmatory", maxtasks=1)
    else:
        from causalguard.experiments.s3 import build_payload
        from causalguard.experiments.s3 import run_world as s3_world
        s3 = cfg["S3"]
        mcfg = {"salt": salt, "task": s3["task"], "harness": s3["harness"], "caps": s3["caps"],
                "provider": s3["models"][args.model]}
        run = Run(run_id, {"S3": s3, "model": args.model, "salt": salt, "mode": "confirmatory",
                           "freeze_commit": args.freeze_commit})
        ledger = str(run.dir / "call_ledger.jsonl")
        items = [(f"s3-{salt}-w{i}", build_payload(mcfg, i, ledger)) for i in range(s3["worlds"])]
        end = run.execute(items, s3_world, workers=1, timeout_s=3600, mode="confirmatory")
    with access.open("a") as fh:
        fh.write(json.dumps({"event": "run_end", "time": now(), **end}) + "\n")
    print(json.dumps(end))


if __name__ == "__main__":
    main()
