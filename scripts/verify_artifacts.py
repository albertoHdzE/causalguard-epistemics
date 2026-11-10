#!/usr/bin/env python3
"""Verify an artifact manifest.  Prints the denominator for every class of file.

  scripts/verify_artifacts.py [artifacts/manifest_r2.json]

r2 manifests: REQUIRED files must all exist and match; OPTIONAL release assets may be absent (reported).
Exit 0 only if every required file was checked and matched; 1 on any mismatch; 2 if any required file is
absent (verification incomplete -- extract the release assets into the checkout first); 3 if nothing loaded.
The historical v0.1.0-dev manifest (artifacts/manifest.json) is verified with the same rules: its reports are
required, its raw files are required, its release asset optional.
"""
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


def entries(man: dict) -> list[dict]:
    if man.get("manifest_version") == "r2":
        return man["files"]
    out = [{**e, "required": True, "group": "report"} for e in man["reports"]]
    out += [{**e, "required": True, "group": "raw_run_v1"} for e in man["raw_runs"]]
    ra = man["release_asset"]
    out.append({"path": f"dist/{ra['name']}", "sha256": ra["sha256"], "required": False, "group": "release_asset"})
    return out


def main(argv) -> int:
    path = Path(argv[1]) if len(argv) > 1 else ROOT / "artifacts" / "manifest_r2.json"
    man = json.loads(path.read_text())
    es = entries(man)
    if not es:
        print("nothing to verify")
        return 3
    stats = {}
    bad, missing_req = [], []
    for e in es:
        p = ROOT / e["path"]
        s = stats.setdefault(e["group"], {"listed": 0, "ok": 0, "mismatch": 0, "absent": 0, "required": e["required"]})
        s["listed"] += 1
        if not p.exists():
            s["absent"] += 1
            if e["required"]:
                missing_req.append(e["path"])
        elif sha(p) == e["sha256"]:
            s["ok"] += 1
        else:
            s["mismatch"] += 1
            bad.append(e["path"])
    for g, s in sorted(stats.items()):
        print(f"{g:16s} {'required' if s['required'] else 'optional'}: listed {s['listed']}, ok {s['ok']}, "
              f"mismatch {s['mismatch']}, absent {s['absent']}")
    for b in bad[:20]:
        print("MISMATCH", b)
    for m in missing_req[:20]:
        print("REQUIRED ABSENT", m)
    if bad:
        return 1
    if missing_req:
        print(f"INCOMPLETE: {len(missing_req)} required files absent; verification is not complete")
        return 2
    print(f"COMPLETE: all {sum(s['ok'] for s in stats.values() if s['required'])} required files verified")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
