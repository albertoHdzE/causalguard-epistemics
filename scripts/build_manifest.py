#!/usr/bin/env python3
"""Build a versioned artifact manifest.

  scripts/build_manifest.py r2 --runs RUN_ID ... --historical-runs RUN_ID ... --asset dist/<name>.tar.gz
  scripts/build_manifest.py r3 --runs NEW_RUN ... --prior-runs R2_RUN ... --historical-runs V1_RUN ... \
                               --asset dist/causalguard-dev-runs-v0.3.0-dev.tar.gz

r3 format (artifacts/manifest_r3.json) = r2 format plus:
* group raw_run_v3   : files of the iteration-3 runs + the CURRENT runs/registry.jsonl (append-only; the
                       v0.2.0-dev copy is a byte prefix of it), in the new release asset          required
* group raw_run_v2   : iteration-2 runs, contained in the v0.2.0-dev asset                        required
* extraction order for COMPLETE verification: v0.1.0-dev, v0.2.0-dev, then v0.3.0-dev (the last carries the
  current registry).  manifest.json and manifest_r2.json are never rewritten.

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


MANIFEST_EXCLUDED = {"r2": {"reports/REVIEW_READY_R2.md"}, "r3": {"reports/REVIEW_READY_R3.md"},
                     "r4": {"reports/REVIEW_READY_R4.md"}}


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
    ap.add_argument("version", choices=["r2", "r3", "r4"])
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--prior-runs", nargs="*", default=[], help="r3: iteration-2 runs (v0.2.0-dev asset)")
    ap.add_argument("--historical-runs", nargs="*", default=[])
    ap.add_argument("--asset", required=True)
    ap.add_argument("--historical-asset", default="causalguard-dev-runs-v0.1.0-dev.tar.gz")
    a = ap.parse_args()
    files = []
    new_raw = [f for rid in a.runs for f in run_files(rid)]
    reg = ROOT / "runs" / "registry.jsonl"
    if reg.exists():
        new_raw.append(reg)
    ledger = ROOT / "runs" / "s4-calls" / "ledger.jsonl"
    if a.version == "r4" and ledger.exists():
        new_raw.append(ledger)                     # S4 model-call ledger (every physical attempt, incl. smokes)
    new_group = {"r2": "raw_run_v2", "r3": "raw_run_v3", "r4": "raw_run_v4"}[a.version]
    excluded = MANIFEST_EXCLUDED[a.version]
    files += [entry(f, new_group) for f in new_raw]
    files += [entry(f, "raw_run_v2") for rid in a.prior_runs for f in run_files(rid)]
    files += [entry(f, "raw_run_v1") for rid in a.historical_runs for f in run_files(rid)]
    # The handoff records the release identity (commit, tag, asset digest), which exists only after this
    # manifest and the asset are built; a document cannot checksum itself, so it is excluded and named.
    files += [entry(f, "report") for f in sorted((ROOT / "reports").rglob("*"))
              if f.is_file() and f.relative_to(ROOT).as_posix() not in excluded]
    files += [entry(f, "config") for f in sorted((ROOT / "configs").rglob("*.json"))]
    if a.version in ("r3", "r4"):
        files += [entry(f, "doc") for f in sorted((ROOT / "docs").rglob("*")) if f.is_file()]
    asset = ROOT / a.asset
    asset.parent.mkdir(exist_ok=True)
    with tarfile.open(asset, "w:gz") as tf:
        for f in new_raw:
            tf.add(f, arcname=str(f.relative_to(ROOT)))
    label = {"r2": "iteration-2", "r3": "iteration-3", "r4": "iteration-4"}[a.version] + " development runs"
    assets = [{"path": str(asset.relative_to(ROOT)), "bytes": asset.stat().st_size, "sha256": sha(asset),
               "required": False, "group": "release_asset",
               "contents": f"{label}: {', '.join(a.runs)} + runs/registry.jsonl"}]
    if a.version == "r3":
        r2 = json.loads((ROOT / "artifacts" / "manifest_r2.json").read_text())
        assets += [{**e, "contents": e["contents"] + " (release v0.2.0-dev)"} for e in r2["files"]
                   if e["group"] == "release_asset" and "v0.2.0-dev" in e["path"]]
    old = json.loads((ROOT / "artifacts" / "manifest.json").read_text())
    assets.append({"path": f"dist/{a.historical_asset}", "bytes": old["release_asset"]["bytes"],
                   "sha256": old["release_asset"]["sha256"], "required": False, "group": "release_asset",
                   "contents": "iteration-1 development runs (release v0.1.0-dev)"})
    man = {"manifest_version": a.version, "files": files + assets, "excluded": sorted(excluded),
           "historical_manifest": {"path": "artifacts/manifest.json",
                                   "sha256": sha(ROOT / "artifacts" / "manifest.json")},
           "historical_registry": {"path": "RUNS.jsonl", "sha256": sha(ROOT / "RUNS.jsonl")}}
    if a.version == "r4":
        man["previous_manifest"] = {"path": "artifacts/manifest_r3.json",
                                    "sha256": sha(ROOT / "artifacts" / "manifest_r3.json")}
        man["registry_note"] = ("iteration-1..3 raw runs are verified by manifest_r3.json from releases v0.1.0-dev.."
                                "v0.3.0-dev; this manifest adds the iteration-4 runs (asset v0.4.0-dev) and the S4 "
                                "call ledger. runs/registry.jsonl is append-only.")
    if a.version == "r3":
        man["previous_manifest"] = {"path": "artifacts/manifest_r2.json",
                                    "sha256": sha(ROOT / "artifacts" / "manifest_r2.json")}
        man["registry_note"] = ("runs/registry.jsonl is append-only; the copy in the v0.2.0-dev asset is a byte prefix "
                                "of this one. Extract v0.1.0-dev, v0.2.0-dev, then v0.3.0-dev.")
    (ROOT / "artifacts" / f"manifest_{a.version}.json").write_text(json.dumps(man, indent=1))
    groups = {}
    for f in man["files"]:
        groups[f["group"]] = groups.get(f["group"], 0) + 1
    print(json.dumps({"files": len(man["files"]), "by_group": groups, "asset_bytes": asset.stat().st_size}))


if __name__ == "__main__":
    main()
