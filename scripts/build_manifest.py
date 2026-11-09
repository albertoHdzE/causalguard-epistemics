#!/usr/bin/env python3
"""Build artifacts/manifest.json: SHA-256 of every raw run file and of every committed report artifact,
plus the release archive that carries the raw records (runs/ is not in git)."""
import hashlib
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    run_ids = sys.argv[1:]
    entries = []
    for rid in run_ids:
        for f in sorted((ROOT / "runs" / rid).glob("*")):
            if f.is_file():
                entries.append({"path": str(f.relative_to(ROOT)), "bytes": f.stat().st_size, "sha256": sha(f)})
    reports = [{"path": str(f.relative_to(ROOT)), "bytes": f.stat().st_size, "sha256": sha(f)}
               for f in sorted((ROOT / "reports").rglob("*")) if f.is_file()]
    archive = ROOT / "dist" / "causalguard-dev-runs-v0.1.0-dev.tar.gz"
    archive.parent.mkdir(exist_ok=True)
    with tarfile.open(archive, "w:gz") as tf:
        for e in entries:
            tf.add(ROOT / e["path"], arcname=e["path"])
    man = {"raw_runs": entries, "reports": reports,
           "release_asset": {"name": archive.name, "bytes": archive.stat().st_size, "sha256": sha(archive),
                             "contents": "runs/<run_id>/* for the listed development runs (no confirmatory data)"},
           "registry": {"path": "RUNS.jsonl", "sha256": sha(ROOT / "RUNS.jsonl")}}
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts" / "manifest.json").write_text(json.dumps(man, indent=1))
    print(f"{len(entries)} raw files, {len(reports)} report files, archive {archive.stat().st_size} bytes")


if __name__ == "__main__":
    main()
