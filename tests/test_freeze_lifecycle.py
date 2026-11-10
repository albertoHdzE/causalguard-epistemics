"""End-to-end freeze lifecycle with a DUMMY fixture record in a temporary git repository (P2 acceptance).

S2 start -> SIGKILL interrupt -> resume -> S1 start, all at ONE fixture freeze commit with the checkout clean
throughout; refusals for unapproved study, unintended rerun, changed config, corrupt run storage, missing
required development artifact, changed endpoint and a revise-type review record.  The fixture salt namespace is
FIXTURE-NONCONFIRMATORY and all runtime storage is temporary.  No production freeze record is created.
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from causalguard.freeze import FIXTURE_NAMESPACE, RECORD_SCHEMA, Refused, sha256_file, validate_record
from causalguard.runner import Run, load_run, make_plan, source_tree_digest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def git(repo, *a):
    return subprocess.check_output(["git", "-C", str(repo), *a], text=True, stderr=subprocess.DEVNULL).strip()


def build_fixture(tmp: Path, bad_endpoint: bool = False) -> tuple[Path, str]:
    repo = tmp / "repo"
    shutil.copytree(ROOT / "src", repo / "src", ignore=shutil.ignore_patterns("__pycache__"))
    (repo / "scripts").mkdir()
    shutil.copy(ROOT / "scripts" / "run_confirmatory.py", repo / "scripts")
    (repo / "configs" / "endpoints").mkdir(parents=True)
    shutil.copy(ROOT / "configs/endpoints/S2-primary-v2.json", repo / "configs/endpoints")
    (repo / ".gitignore").write_text("devruns/\n__pycache__/\n")
    # tiny development corpus (ignored raw files, verified by hash like the real runs/)
    sys.path.insert(0, str(repo / "src"))
    from causalguard.experiments.s2 import run_world_v2  # noqa: F401  (same code as the fixture copy)
    dev_items = [(f"realizable|conjunctive|{i}", {"salt": "FIXTURE-dev", "index": i, "family": "conjunctive",
                                                 "population": "realizable", "label": "realizable",
                                                 "design_version": "s2-design-v2", "budgets": [16],
                                                 "regimes": ["uniform_states"]}) for i in range(3)]
    dev = Run("S2-fixture-dev", make_plan("S2-fixture-dev", "S2", {"fixture": True}, dev_items),
              runs_root=repo / "devruns")
    dev.execute(run_world_v2_ref(), workers=1, timeout_s=120)
    files = sorted(p for p in (repo / "devruns").rglob("*") if p.is_file())
    man = {"files": [{"path": str(p.relative_to(repo)), "sha256": sha256_file(p), "required": True} for p in files]
           + [{"path": "release/optional_asset.tar.gz", "sha256": "0" * 64, "required": False}]}
    (repo / "artifacts").mkdir()
    (repo / "artifacts/manifest_fixture.json").write_text(json.dumps(man))
    cfg = {"salt_namespace": FIXTURE_NAMESPACE, "development_manifest": "artifacts/manifest_fixture.json",
           "development_corpora": {"S2": ["devruns/S2-fixture-dev"]},
           "S2": {"design_version": "s2-design-v2", "n": 7, "kmax": 3, "budgets": [2, 4, 8, 16, 32, 64],
                  "regimes": ["uniform_states", "observational"], "endpoint": "configs/endpoints/S2-primary-v2.json",
                  "dedup_rule": "structured: exclude dev-isomorphic, replenish next index; null: IID, audit only",
                  "populations": [{"population": "realizable", "families": ["conjunctive", "parity"], "start": 0,
                                   "worlds_per_family": 10},
                                  {"population": "null", "families": ["uniform_H"], "start": 0,
                                   "worlds_per_family": 4}], "workers": 1, "item_timeout_s": 120},
           "S1": {"cells": [{"family": "sparse_conj", "n": 4, "seeds": 1}], "backends": ["reference", "index_sat"],
                  "query_timeout_s": 20, "limits": {}, "workers": 2, "item_timeout_s": 300}}
    (repo / "configs/confirmatory.json").write_text(json.dumps(cfg, indent=1))
    rec = {"schema": RECORD_SCHEMA, "decision": "approve_confirmation", "confirmatory_authorized": True,
           "fixture": True, "reviewed_source_tree_sha256": source_tree_digest(repo / "src" / "causalguard"),
           "config_sha256": sha256_file(repo / "configs/confirmatory.json"),
           "endpoint_sha256": {"S2": "f" * 64 if bad_endpoint else
                               sha256_file(repo / "configs/endpoints/S2-primary-v2.json")},
           "development_manifest_sha256": sha256_file(repo / "artifacts/manifest_fixture.json"),
           "approved_studies": ["S2", "S1"], "approved_models": {}, "readiness": {"S2": "ready", "S1": "ready",
                                                                                 "S3": "not_ready"},
           "salt_namespace": FIXTURE_NAMESPACE, "reviewer": "FIXTURE", "review_id": "FIXTURE"}
    (repo / "docs").mkdir()
    (repo / "docs/FREEZE_RECORD.json").write_text(json.dumps(rec, indent=1))
    git(tmp, "init", "-q", str(repo))
    git(repo, "add", ".")
    git(repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
    return repo, git(repo, "rev-parse", "HEAD")


def run_world_v2_ref():
    from causalguard.experiments.s2 import run_world_v2
    return run_world_v2


def cli(repo, *args, check=False, **kw):
    return subprocess.run([PY, str(repo / "scripts/run_confirmatory.py"), *args], capture_output=True, text=True,
                          check=check, **kw)


def test_lifecycle_single_freeze_commit(tmp_path):
    repo, commit = build_fixture(tmp_path)
    rt = tmp_path / "runtime"
    base = ["--freeze-commit", commit, "--runtime-root", str(rt)]
    # ---- S2 start, interrupted by SIGKILL of the whole process group
    proc = subprocess.Popen([PY, str(repo / "scripts/run_confirmatory.py"), "--study", "S2", *base],
                            start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while time.time() - t0 < 120:
        runs = list(rt.glob("*-S2-*/attempts/*/001.json")) if rt.exists() else []
        if len(runs) >= 3:
            break
        time.sleep(0.05)
    os.killpg(proc.pid, signal.SIGKILL)
    proc.wait()
    run_dir = next(rt.glob("*-S2-*"))
    part = load_run(run_dir)
    assert 3 <= len(part["results"]) < 24 and part["missing"]
    assert git(repo, "status", "--porcelain") == ""
    # ---- unintended rerun without --resume is refused
    r = cli(repo, "--study", "S2", *base)
    assert r.returncode != 0 and "resume" in (r.stderr + r.stdout)
    # ---- resume completes under the same plan and salt
    r = cli(repo, "--study", "S2", *base, "--resume")
    assert r.returncode == 0, r.stderr[-2000:]
    full = load_run(run_dir)
    assert len(full["results"]) == 24 and not full["missing"] and not full["failures"]
    plan = full["plan"]
    assert plan["freeze"]["salt"].startswith(FIXTURE_NAMESPACE) and plan["source_tree_sha256"] == source_tree_digest(
        repo / "src" / "causalguard")
    assert "excluded_dev_isomorphic" in plan["duplicate_audit"]
    # ---- a second approved study at the SAME freeze commit
    r = cli(repo, "--study", "S1", *base)
    assert r.returncode == 0, r.stderr[-2000:]
    assert git(repo, "status", "--porcelain") == "" and git(repo, "rev-parse", "HEAD") == commit
    # ---- unapproved study
    r = cli(repo, "--study", "S3", "--model", "x", *base)
    assert r.returncode != 0 and "not approved" in r.stderr
    # ---- corrupt run storage is refused on resume (interior ledger line)
    ev = run_dir / "events.jsonl"
    lines = ev.read_bytes().split(b"\n")
    lines[1] = b'{"broken'
    ev.write_bytes(b"\n".join(lines))
    r = cli(repo, "--study", "S2", *base, "--resume")
    assert r.returncode != 0 and "RunCorruption" in r.stderr
    # ---- missing REQUIRED development artifact (ignored raw file deleted)
    victim = next((repo / "devruns").rglob("001.json"))
    victim.unlink()
    r = cli(repo, "--study", "S1", *base, "--resume")
    assert r.returncode != 0 and "required development artifacts" in r.stderr
    # ---- changed config: dirty tree refused; committed change refused by the freeze commit check
    cfgp = repo / "configs/confirmatory.json"
    cfgp.write_text(cfgp.read_text().replace('"workers": 2', '"workers": 3'))
    r = cli(repo, "--study", "S1", *base)
    assert r.returncode != 0 and "not clean" in r.stderr
    git(repo, "-c", "user.name=F", "-c", "user.email=f@example.invalid", "commit", "-qam", "change")
    r = cli(repo, "--study", "S1", *base)
    assert r.returncode != 0 and "!= freeze commit" in r.stderr
    led = [json.loads(x) for x in (rt / "access_ledger.jsonl").read_text().splitlines()]
    assert [e["event"] for e in led].count("refused") >= 5 and "started" in [e["event"] for e in led]


def test_changed_endpoint_refused(tmp_path):
    repo, commit = build_fixture(tmp_path, bad_endpoint=True)
    r = cli(repo, "--study", "S2", "--freeze-commit", commit, "--runtime-root", str(tmp_path / "rt"))
    assert r.returncode != 0 and "endpoint spec" in r.stderr
    assert not (tmp_path / "rt").exists()          # nothing created before readiness passes


def test_revise_decision_and_project_state_cannot_authorize():
    review = json.loads((ROOT / "reports/review_r1/DECISION.json").read_text())
    with pytest.raises(Refused):
        validate_record(review)
    assert not (ROOT / "docs/FREEZE_RECORD.json").exists()
    good = {"schema": RECORD_SCHEMA, "decision": "revise_before_confirmation", "confirmatory_authorized": False,
            "fixture": False, "reviewed_source_tree_sha256": "", "config_sha256": "", "endpoint_sha256": {},
            "development_manifest_sha256": "", "approved_studies": [], "approved_models": {}, "readiness": {},
            "salt_namespace": "confirm", "reviewer": "x", "review_id": "x"}
    with pytest.raises(Refused):
        validate_record(good)
    with pytest.raises(Refused):   # typed: a string "true" is not authorization
        validate_record({**good, "decision": "approve_confirmation", "confirmatory_authorized": "true"})
