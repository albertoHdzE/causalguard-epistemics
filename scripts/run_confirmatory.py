#!/usr/bin/env python3
"""Confirmatory runner CLI — PREPARED, NOT AUTHORIZED.  Logic and rules: src/causalguard/freeze.py.

No production freeze record exists; every invocation therefore refuses.  Dummy fixture records are used only
by tests/test_freeze_lifecycle.py inside temporary git repositories.

  scripts/run_confirmatory.py --study S2 --freeze-commit <sha> --runtime-root /external/path [--resume]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main(argv=None) -> int:
    from causalguard.freeze import execute
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--study", required=True, choices=["S1", "S2", "S3"])
    ap.add_argument("--freeze-commit", required=True)
    ap.add_argument("--runtime-root", required=True, help="external runtime storage (outside the repository)")
    ap.add_argument("--resume", action="store_true", help="continue the run of this study at this freeze commit")
    ap.add_argument("--model", default=None, help="S3 model identity (must be approved)")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--record", default=None, help="freeze record path (default docs/FREEZE_RECORD.json)")
    a = ap.parse_args(argv)
    res = execute(ROOT, a.study, a.freeze_commit, Path(a.runtime_root), resume=a.resume,
                  record_path=Path(a.record).resolve() if a.record else None, model=a.model, workers=a.workers)
    print(json.dumps(res, sort_keys=True))
    return 0 if res["end"]["status"] == "complete" else 3


if __name__ == "__main__":
    sys.exit(main())
