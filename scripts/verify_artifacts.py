#!/usr/bin/env python3
"""Verify checksums in artifacts/manifest.json.  Report files must match; raw run files are
checked when present locally (download and extract the release asset first).  Exit 1 on mismatch,
2 if nothing could be checked."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


man = json.loads((ROOT / "artifacts" / "manifest.json").read_text())
ok = bad = missing = 0
for group in ("reports", "raw_runs"):
    for e in man[group]:
        p = ROOT / e["path"]
        if not p.exists():
            missing += 1
            continue
        if sha(p) == e["sha256"]:
            ok += 1
        else:
            bad += 1
            print("MISMATCH", e["path"])
print(f"checked {ok + bad}: ok {ok}, mismatched {bad}, absent {missing}")
sys.exit(1 if bad else (2 if ok == 0 else 0))
