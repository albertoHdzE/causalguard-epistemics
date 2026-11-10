"""Confirmatory guard on the REAL project state: nothing can run (no freeze record exists).  The full lifecycle
with a dummy fixture record is tests/test_freeze_lifecycle.py."""
import json
from pathlib import Path

import pytest

from causalguard.freeze import CONFIRM_NAMESPACE, FIXTURE_NAMESPACE, Refused, confirmatory_salt, preflight

ROOT = Path(__file__).resolve().parents[1]


def test_salt_depends_on_freeze_commit_and_namespace_only():
    assert confirmatory_salt("a" * 40, CONFIRM_NAMESPACE) != confirmatory_salt("b" * 40, CONFIRM_NAMESPACE)
    assert confirmatory_salt("a" * 40, CONFIRM_NAMESPACE) == confirmatory_salt("a" * 40, CONFIRM_NAMESPACE)
    assert confirmatory_salt("a" * 40, CONFIRM_NAMESPACE) != confirmatory_salt("a" * 40, FIXTURE_NAMESPACE)


def test_no_freeze_record_in_repository():
    assert not (ROOT / "docs" / "FREEZE_RECORD.json").exists()


def test_project_preflight_refuses(tmp_path):
    import subprocess
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    with pytest.raises(Refused):
        preflight(ROOT, "S2", head, ROOT / "docs" / "FREEZE_RECORD.json")


def test_cli_run_refuses_confirmatory_mode(tmp_path):
    from causalguard.__main__ import main
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"study": "S2", "mode": "confirmatory"}))
    with pytest.raises(SystemExit):
        main(["run", "--config", str(cfg)])


def test_confirmatory_config_declares_s3_not_ready_and_no_authorization():
    cfg = json.loads((ROOT / "configs" / "confirmatory.json").read_text())
    assert cfg.get("confirmatory_authorized") is False
    assert cfg["readiness_proposal"]["S3"] == "not_ready"
