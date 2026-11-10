#!/usr/bin/env python3
"""Build a versioned artifact manifest.

  scripts/build_manifest.py r2 --runs RUN_ID ... --historical-runs RUN_ID ... --asset dist/<name>.tar.gz

r2 format (artifacts/manifest_r2.json): one entry per file with {path, bytes, sha256, required, group}.
* group raw_run_v2  : files of the iteration-2 development runs (in the new release asset)   required
* group raw_run_v1  : files of the iteration-1 runs (in the v0.1.0-dev release asset; used by duplicate
                      audits and the byte-level v1 reproduction)                                 required
* group report / config / fitted : committed files under reports/, configs/                     required
* group release_asset : the tarballs themselves (downloads; may be absent locally)               optional
The historical artifacts/manifest.json (v0.1.0-dev) is never rewritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


MANIFEST_EXCLUDED = {"reports/REVIEW_READY_R2.md"}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def entry(p: Path, group: str, required: bool = True) -> dict:
    return {"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p), "required": required,
            "group": group}


def run_files(rid: str) -> list[Path]:
    d = ROOT / "runs" / rid
    if not d.is_dir():
        raise SystemExit(f"run directory missing: {d}")
    return sorted(p for p in d.rglob("*") if p.is_file())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("version", choices=["r2"])
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--historical-runs", nargs="*", default=[])
    ap.add_argument("--asset", required=True)
    ap.add_argument("--historical-asset", default="causalguard-dev-runs-v0.1.0-dev.tar.gz")
    a = ap.parse_args()
    files = []
    new_raw = [f for rid in a.runs for f in run_files(rid)]
    reg = ROOT / "runs" / "registry.jsonl"
    if reg.exists():
        new_raw.append(reg)
    files += [entry(f, "raw_run_v2") for f in new_raw]
    files += [entry(f, "raw_run_v1") for rid in a.historical_runs for f in run_files(rid)]
    # The handoff records the release identity (commit, tag, asset digest), which exists only after this
    # manifest and the asset are built; a document cannot checksum itself, so it is excluded and named.
    files += [entry(f, "report") for f in sorted((ROOT / "reports").rglob("*"))
              if f.is_file() and f.relative_to(ROOT).as_posix() not in MANIFEST_EXCLUDED]
    files += [entry(f, "config") for f in sorted((ROOT / "configs").rglob("*.json"))]
    asset = ROOT / a.asset
    asset.parent.mkdir(exist_ok=True)
    with tarfile.open(asset, "w:gz") as tf:
        for f in new_raw:
            tf.add(f, arcname=str(f.relative_to(ROOT)))
    assets = [{"path": str(asset.relative_to(ROOT)), "bytes": asset.stat().st_size, "sha256": sha(asset),
               "required": False, "group": "release_asset",
               "contents": f"iteration-2 development runs: {', '.join(a.runs)} + runs/registry.jsonl"}]
    old = json.loads((ROOT / "artifacts" / "manifest.json").read_text())
    assets.append({"path": f"dist/{a.historical_asset}", "bytes": old["release_asset"]["bytes"],
                   "sha256": old["release_asset"]["sha256"], "required": False, "group": "release_asset",
                   "contents": "iteration-1 development runs (release v0.1.0-dev)"})
    man = {"manifest_version": "r2", "files": files + assets, "excluded": sorted(MANIFEST_EXCLUDED),
           "historical_manifest": {"path": "artifacts/manifest.json",
                                   "sha256": sha(ROOT / "artifacts" / "manifest.json")},
           "historical_registry": {"path": "RUNS.jsonl", "sha256": sha(ROOT / "RUNS.jsonl")}}
    (ROOT / "artifacts" / "manifest_r2.json").write_text(json.dumps(man, indent=1))
    groups = {}
    for f in man["files"]:
        groups[f["group"]] = groups.get(f["group"], 0) + 1
    print(json.dumps({"files": len(man["files"]), "by_group": groups, "asset_bytes": asset.stat().st_size}))


if __name__ == "__main__":
    main()
