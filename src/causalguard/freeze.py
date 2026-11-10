"""Freeze lifecycle for confirmatory execution (repairs R03, R08; P2).  PREPARED, NOT AUTHORIZED.

Owner of: the typed freeze-record schema, preflight readiness checks, required-artifact verification,
confirmatory salts, confirmatory item plans with duplicate audits, and the access ledger.

Process rules (no-peeking is a PROCESS rule, not a cryptographic property):
* A confirmatory salt derived from a public commit is a REPRODUCIBILITY identifier.  It is not secret and
  does not seal anything; integrity comes from executing only at the reviewed freeze commit and recording
  every access in the ledger.
* The freeze record binds the reviewed source-tree digest, config, endpoint specs and development manifest.
  It does not contain its own commit hash (that would be self-referential): the containing commit is supplied
  with --freeze-commit and verified to be HEAD of a clean checkout.
* Runtime records live OUTSIDE the repository (``--runtime-root``), so the frozen checkout stays clean while
  several studies are started, interrupted and resumed at one freeze commit.
* All checks run BEFORE any run directory is created.  A failed check creates nothing except an access-ledger
  line (when the runtime root already exists).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from .runner import Ledger, Run, RunRefused, make_plan, now, source_tree_digest

RECORD_SCHEMA = "causalguard-freeze-record-v2"
FIXTURE_NAMESPACE = "FIXTURE-NONCONFIRMATORY"
CONFIRM_NAMESPACE = "confirm"
RECORD_FIELDS = {
    "schema": str, "decision": str, "confirmatory_authorized": bool, "fixture": bool,
    "reviewed_source_tree_sha256": str, "config_sha256": str, "endpoint_sha256": dict,
    "development_manifest_sha256": str, "approved_studies": list, "approved_models": dict, "readiness": dict,
    "salt_namespace": str, "reviewer": str, "review_id": str}
STUDIES = ("S1", "S2", "S3")


class Refused(SystemExit):
    pass


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(root: Path, *a: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *a], text=True, stderr=subprocess.DEVNULL).strip()


def validate_record(rec: dict) -> None:
    """Typed schema check; any deviation refuses (a review 'revise' decision has a different schema)."""
    if not isinstance(rec, dict) or rec.get("schema") != RECORD_SCHEMA:
        raise Refused(f"REFUSED: freeze record schema is not {RECORD_SCHEMA}")
    for k, t in RECORD_FIELDS.items():
        if k not in rec:
            raise Refused(f"REFUSED: freeze record lacks {k}")
        if type(rec[k]) is not t:
            raise Refused(f"REFUSED: freeze record field {k} must be {t.__name__}")
    extra = set(rec) - set(RECORD_FIELDS)
    if extra:
        raise Refused(f"REFUSED: unknown freeze record fields {sorted(extra)}")
    if rec["decision"] != "approve_confirmation" or rec["confirmatory_authorized"] is not True:
        raise Refused("REFUSED: the record does not approve confirmation")
    if rec["fixture"] != (rec["salt_namespace"] == FIXTURE_NAMESPACE):
        raise Refused("REFUSED: fixture flag and salt namespace disagree")
    for s in rec["approved_studies"]:
        if s not in STUDIES or rec["readiness"].get(s) != "ready":
            raise Refused(f"REFUSED: study {s} approved without typed readiness 'ready'")


def confirmatory_salt(freeze_commit: str, namespace: str) -> str:
    return f"{namespace}-" + hashlib.sha256(f"{freeze_commit}|causalguard-confirmatory-v2".encode()).hexdigest()[:16]


def verify_manifest(root: Path, manifest_path: Path) -> dict:
    """Every REQUIRED file must exist and match; optional release assets may be absent (reported)."""
    man = json.loads(manifest_path.read_text())
    out = {"required_ok": 0, "required_bad": [], "required_missing": [], "optional_ok": 0, "optional_missing": [],
           "optional_bad": []}
    for e in man["files"]:
        p = root / e["path"]
        kind = "required" if e.get("required", True) else "optional"
        if not p.exists():
            out[f"{kind}_missing"].append(e["path"])
        elif sha256_file(p) != e["sha256"]:
            out[f"{kind}_bad"].append(e["path"])
        else:
            out[f"{kind}_ok"] += 1
    return out


def preflight(root: Path, study: str, freeze_commit: str, record_path: Path, model: str | None = None) -> dict:
    root = Path(root)
    if _git(root, "status", "--porcelain"):
        raise Refused("REFUSED: working tree not clean")
    head = _git(root, "rev-parse", "HEAD")
    if head != freeze_commit:
        raise Refused(f"REFUSED: HEAD {head} != freeze commit {freeze_commit}")
    if not record_path.exists():
        raise Refused(f"REFUSED: {record_path} absent (the design has not been frozen by review)")
    try:
        _git(root, "ls-files", "--error-unmatch", str(record_path.resolve().relative_to(root.resolve())))
    except (subprocess.CalledProcessError, ValueError):
        raise Refused("REFUSED: freeze record is not a committed file of the frozen checkout") from None
    rec = json.loads(record_path.read_text())
    validate_record(rec)
    if study not in rec["approved_studies"]:
        raise Refused(f"REFUSED: study {study} is not approved by the freeze record")
    if study == "S3" and (model is None or model not in rec["approved_models"].get("S3", [])):
        raise Refused(f"REFUSED: model {model!r} not approved for S3")
    if source_tree_digest(root / "src" / "causalguard") != rec["reviewed_source_tree_sha256"]:
        raise Refused("REFUSED: source tree differs from the reviewed source")
    cfg_path = root / "configs" / "confirmatory.json"
    if sha256_file(cfg_path) != rec["config_sha256"]:
        raise Refused("REFUSED: configs/confirmatory.json differs from the frozen hash")
    cfg = json.loads(cfg_path.read_text())
    scfg = cfg.get(study)
    if not isinstance(scfg, dict):
        raise Refused(f"REFUSED: no {study} block in the confirmatory config")
    ep = scfg.get("endpoint")
    if ep:
        if sha256_file(root / ep) != rec["endpoint_sha256"].get(study):
            raise Refused(f"REFUSED: endpoint spec {ep} differs from the frozen hash")
    elif study in rec["endpoint_sha256"]:
        raise Refused("REFUSED: frozen endpoint declared but the config names none")
    man_path = root / cfg["development_manifest"]
    if sha256_file(man_path) != rec["development_manifest_sha256"]:
        raise Refused("REFUSED: development manifest differs from the frozen hash")
    mv = verify_manifest(root, man_path)
    if mv["required_bad"] or mv["required_missing"]:
        raise Refused(f"REFUSED: required development artifacts missing/mismatched: "
                      f"{(mv['required_missing'] + mv['required_bad'])[:5]}")
    if cfg.get("salt_namespace") != rec["salt_namespace"]:
        raise Refused("REFUSED: config salt namespace differs from the record")
    return {"head": head, "record": rec, "config": cfg, "study_config": scfg, "manifest_check": mv}


# --------------------------------------------------------------------------- plans + duplicate audits

def dev_forms(root: Path, corpora: list[str]) -> set[str]:
    """Canonical (isomorphism) forms of every development world in the listed corpora (v1 or v2 layout)."""
    from .dedup import canonical_form
    from .runner import load_run
    from .schema import Network
    forms = set()
    for c in corpora:
        lr = load_run(root / c)
        for out in lr["results"].values():
            forms.add(canonical_form(Network.from_json(out["world"]["network"])))
    if not forms:
        raise Refused("REFUSED: development corpora are empty; the cross-split duplicate audit cannot run")
    return forms


def plan_s2(s2: dict, salt: str, forms: set[str]) -> tuple[list, dict]:
    """Structured populations: worlds isomorphic to a development world are EXCLUDED and replaced by the next
    index (deterministic replenishment).  Null (uniform_H) worlds are IID and never excluded: overlaps are
    audited only.  Within-confirmatory isomorphic duplicates are retained (IID generator) and reported."""
    from .dedup import canonical_form
    from .generators import make_s2_world
    items, audit = [], {"excluded_dev_isomorphic": [], "null_dev_overlap": [], "within_split_duplicates": 0,
                        "rule": s2.get("dedup_rule")}
    seen = {}
    for pop in s2["populations"]:
        label = pop.get("label", pop["population"])
        for fam in pop["families"]:
            i = pop.get("start", 0)
            got = 0
            while got < pop["worlds_per_family"]:
                w = make_s2_world(salt, i, fam, pop["population"], s2["n"], s2["kmax"])
                f = canonical_form(w.net)
                if f in forms:
                    if fam == "uniform_H":
                        audit["null_dev_overlap"].append(w.world_id)
                    else:
                        audit["excluded_dev_isomorphic"].append({"index": i, "family": fam, "label": label})
                        i += 1
                        continue
                if f in seen:
                    audit["within_split_duplicates"] += 1
                seen.setdefault(f, w.world_id)
                payload = {"salt": salt, "index": i, "family": fam, "population": pop["population"], "label": label,
                           "design_version": s2["design_version"], "n": s2["n"], "kmax": s2["kmax"],
                           "budgets": s2["budgets"], "regimes": pop.get("regimes", s2["regimes"]),
                           "noise_rates": pop.get("noise_rates", []),
                           "noise_budgets": pop.get("noise_budgets", [16, 32, 64]),
                           "verdicts": pop.get("verdicts", True)}
                items.append((f"{label}|{fam}|{i}", payload))
                got += 1
                i += 1
    return items, audit


def plan_s1(s1: dict, salt: str) -> list:
    items = []
    for cell in s1["cells"]:
        for i in range(cell.get("start", 0), cell.get("start", 0) + cell["seeds"]):
            for backend in s1["backends"]:
                items.append((f"{cell['family']}|n{cell['n']}|{i}|{backend}",
                              {"salt": salt, "index": i, "family": cell["family"], "n": cell["n"], "backend": backend,
                               "query_timeout_s": s1["query_timeout_s"], "limits": s1["limits"]}))
    return items


def _strata(p: dict) -> dict:
    return {k: p[k] for k in ("family", "population", "label", "n", "backend", "index") if k in p}


def execute(root: Path, study: str, freeze_commit: str, runtime_root: Path, resume: bool = False,
            record_path: Path | None = None, model: str | None = None, workers: int | None = None,
            quiet: bool = True) -> dict:
    root = Path(root)
    runtime_root = Path(runtime_root).resolve()
    if runtime_root.is_relative_to(root.resolve()):
        raise Refused("REFUSED: runtime root must be outside the frozen repository")
    record_path = record_path or root / "docs" / "FREEZE_RECORD.json"
    ledger = Ledger(runtime_root / "access_ledger.jsonl") if runtime_root.exists() else None
    entry = {"time": now(), "study": study, "freeze_commit": freeze_commit, "resume": resume, "model": model}
    try:
        pf = preflight(root, study, freeze_commit, record_path, model)
    except SystemExit as e:
        if ledger:
            ledger.recover()
            ledger.append({**entry, "event": "refused", "reason": str(e)})
        raise
    rec, cfg, scfg = pf["record"], pf["config"], pf["study_config"]
    import tempfile
    if rec["fixture"] and not runtime_root.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise Refused("REFUSED: fixture freeze records may only run in temporary fixture storage")
    salt = confirmatory_salt(freeze_commit, rec["salt_namespace"])
    run_id = f"{rec['salt_namespace']}-{study}-{freeze_commit[:12]}" + (f"-{model}" if model else "")
    extra = {"freeze": {"freeze_commit": freeze_commit, "record_sha256": sha256_file(record_path),
                        "salt": salt, "salt_note": "public reproducibility identifier, not a secret seal",
                        "manifest_check": pf["manifest_check"]}}
    if study == "S2":
        items, audit = plan_s2(scfg, salt, dev_forms(root, cfg["development_corpora"]["S2"]))
        extra["duplicate_audit"] = audit
        from .experiments.s2 import run_world_v2 as fn
    elif study == "S1":
        items = plan_s1(scfg, salt)
        from .experiments.s1 import run_item as fn
    else:
        raise Refused("REFUSED: S3 confirmatory execution is not implemented in this iteration")
    if scfg.get("endpoint"):
        ep = root / scfg["endpoint"]
        extra["endpoint"] = {"path": scfg["endpoint"], "sha256": sha256_file(ep), "spec": json.loads(ep.read_text())}
    plan = make_plan(run_id, study, {"confirmatory_config_sha256": rec["config_sha256"], "study_config": scfg},
                     items, strata_fn=_strata, source_digest=rec["reviewed_source_tree_sha256"], extra=extra)
    runtime_root.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(runtime_root / "access_ledger.jsonl")
    ledger.recover()
    try:
        run = Run(run_id, plan, runs_root=runtime_root, resume=resume, registry=runtime_root / "registry.jsonl")
    except RunRefused as e:
        ledger.append({**entry, "event": "refused", "reason": str(e)})
        raise Refused(f"REFUSED: {e}") from None
    ledger.append({**entry, "event": "resumed" if resume else "started", "run_id": run_id,
                   "plan_sha256": plan["plan_sha256"]})
    end = run.execute(fn, workers=workers or scfg.get("workers", 8), timeout_s=scfg.get("item_timeout_s", 900),
                      quiet=quiet, mode="confirmatory" if not rec["fixture"] else "fixture",
                      maxtasks=scfg.get("maxtasks", 50))
    ledger.append({**entry, "event": "end", "run_id": run_id, "status": end["status"]})
    return {"run_id": run_id, "end": end, "run_dir": str(run.dir)}
