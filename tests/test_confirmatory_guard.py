"""The sealed confirmatory runner must refuse unless every freeze condition holds."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_confirmatory", ROOT / "scripts" / "run_confirmatory.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)


def _setup(tmp_path, monkeypatch, dirty="", head="abc", record=True, cfg=b'{"S2": {}}', phrase="ok"):
    (tmp_path / "configs").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "configs" / "confirmatory.json").write_bytes(cfg)
    if record:
        (tmp_path / "docs" / "FREEZE_RECORD.json").write_text(json.dumps(
            {"config_sha256": hashlib.sha256(b'{"S2": {}}').hexdigest(), "authorization_phrase": "ok"}))
    monkeypatch.setattr(rc, "ROOT", tmp_path)
    monkeypatch.setattr(rc, "sh", lambda *a: dirty if a[0] == "status" else head)
    return SimpleNamespace(freeze_commit="abc", authorization=phrase)


@pytest.mark.parametrize("kw,msg", [
    ({"dirty": " M x"}, "not clean"), ({"head": "zzz"}, "!= freeze commit"), ({"record": False}, "FREEZE_RECORD"),
    ({"cfg": b'{"S2": {"n": 8}}'}, "differs"), ({"phrase": "bad"}, "authorization"),
])
def test_preflight_refusals(tmp_path, monkeypatch, kw, msg):
    args = _setup(tmp_path, monkeypatch, **kw)
    with pytest.raises(SystemExit) as e:
        rc.preflight(args)
    assert msg in str(e.value)


def test_preflight_passes_only_when_all_hold(tmp_path, monkeypatch):
    args = _setup(tmp_path, monkeypatch)
    assert rc.preflight(args)["head"] == "abc"


def test_salt_depends_on_freeze_commit_only():
    assert rc.confirmatory_salt("a" * 40) != rc.confirmatory_salt("b" * 40)
    assert rc.confirmatory_salt("a" * 40) == rc.confirmatory_salt("a" * 40)
    assert rc.confirmatory_salt("a" * 40) != "dev-v1"


def test_no_freeze_record_in_repository_yet():
    assert not (ROOT / "docs" / "FREEZE_RECORD.json").exists()


def test_cli_run_refuses_confirmatory_mode(tmp_path):
    from causalguard.__main__ import main
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"study": "S2", "mode": "confirmatory", "run_id": "x"}))
    with pytest.raises(SystemExit):
        main(["run", "--config", str(cfg)])


def test_confirmatory_s2_plan_unique_items_and_worlds():
    """Dry plan with a DUMMY salt (not the confirmatory salt): ids and world seeds must be unique."""
    cfg = json.loads((ROOT / "configs" / "confirmatory.json").read_text())
    items, excluded = rc.plan_s2_items(cfg["S2"], "dummy-not-confirmatory", None)
    ids = [i for i, _ in items]
    assert len(ids) == len(set(ids)) == 1000 + 250 + 250 + 250
    keys = {(p["population"], p["family"], p["index"]) for _, p in items}
    assert len(keys) == len(items)
