"""Runner v2: plan binding, strict logs, torn-tail recovery, supervisor deadlines, real interruption."""
import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from causalguard import testing_fixtures as fx
from causalguard.runner import (Ledger, Run, RunCorruption, RunRefused, load_run, make_plan, read_attempts,
                                read_jsonl)

ROOT = Path(__file__).resolve().parents[1]


def _plan(run_id, n=3, **kw):
    items = [(f"it{i}", {"value": i, **kw}) for i in range(n)]
    return make_plan(run_id, "FIXTURE", {"fixture": True}, items)


def test_duplicate_ids_rejected():
    with pytest.raises(RunRefused):
        make_plan("r", "FIXTURE", {}, [("a", {}), ("a", {"x": 1})])


def test_new_vs_resume_rules(tmp_path):
    p = _plan("r1")
    Run("r1", p, runs_root=tmp_path)
    with pytest.raises(RunRefused):
        Run("r1", p, runs_root=tmp_path)                      # exists, no resume
    with pytest.raises(RunRefused):
        Run("r2", _plan("r2"), runs_root=tmp_path, resume=True)  # resume without plan
    changed = _plan("r1", n=4)
    with pytest.raises(RunRefused):
        Run("r1", changed, runs_root=tmp_path, resume=True)   # changed plan
    Run("r1", p, runs_root=tmp_path, resume=True)


def test_execute_and_reconcile(tmp_path):
    p = make_plan("r", "FIXTURE", {}, [("a", {"value": 1}), ("b", {"value": 2, "fail": True})])
    run = Run("r", p, runs_root=tmp_path)
    end = run.execute(fx.echo, workers=2, timeout_s=30)
    assert end["ok"] == 1 and end["failed"] == 1 and end["status"] == "complete_with_failures"
    lr = load_run(run.dir)
    assert set(lr["results"]) == {"a"} and set(lr["failures"]) == {"b"} and lr["missing"] == []
    # explicit retry keeps the failed attempt and records supersession
    run2 = Run("r", p, runs_root=tmp_path, resume=True)
    run2.execute(fx.echo, workers=1, timeout_s=30, retry_failed=True)
    atts = read_attempts(run.dir)
    assert [a["attempt"] for a in atts["b"]] == [1, 2] and atts["b"][1]["supersedes"] == [1]


def test_strict_reader_interior_corruption(tmp_path):
    f = tmp_path / "x.jsonl"
    f.write_bytes(b'{"a":1}\n{"bad\n{"c":3}\n')
    with pytest.raises(RunCorruption):
        read_jsonl(f)
    with pytest.raises(RunCorruption):
        Ledger(f).recover()   # interior defects are not recoverable


def test_torn_tail_quarantined_then_append_is_boundary_safe(tmp_path):
    f = tmp_path / "events.jsonl"
    f.write_bytes(b'{"a":1}\n{"item_id":"torn')
    with pytest.raises(RunCorruption):
        read_jsonl(f)
    led = Ledger(f)
    ev = led.recover()
    assert ev["offset"] == 8 and ev["length"] == len(b'{"item_id":"torn')
    q = tmp_path / "quarantine" / ev["quarantine_path"]
    assert q.read_bytes() == b'{"item_id":"torn'
    led.append({"item_id": "valid-next"})
    recs = read_jsonl(f)
    assert recs[0] == {"a": 1} and recs[-1] == {"item_id": "valid-next"} and recs[1]["event"] == "quarantine"


def test_corrupt_attempt_file_fails_closed(tmp_path):
    p = _plan("r")
    run = Run("r", p, runs_root=tmp_path)
    run.execute(fx.echo, workers=1, timeout_s=30)
    f = next((run.dir / "attempts").rglob("001.json"))
    f.write_bytes(f.read_bytes()[:-5])
    with pytest.raises(RunCorruption):
        load_run(run.dir)


def test_nested_timer_cannot_cancel_outer_deadline(tmp_path):
    """Review R06 diagnostic: nested SIGALRM use inside an item must not erase the item cap."""
    p = make_plan("r", "FIXTURE", {}, [("hang", {"hang": 5})])
    run = Run("r", p, runs_root=tmp_path)
    t0 = time.time()
    end = run.execute(fx.nested_timer_then_hang, workers=1, timeout_s=0.5)
    assert end["failed"] == 1 and time.time() - t0 < 4
    assert load_run(run.dir)["failures"]["hang"]["status"] == "timeout"


def test_hung_noncooperating_worker_and_child_are_reaped(tmp_path):
    pidfile = tmp_path / "pids"
    p = make_plan("r", "FIXTURE", {}, [("h", {"pidfile": str(pidfile)})])
    run = Run("r", p, runs_root=tmp_path)
    end = run.execute(fx.hung_with_child, workers=1, timeout_s=1.5)
    assert end["failed"] == 1
    wpid, cpid = map(int, pidfile.read_text().split())
    time.sleep(0.3)
    for pid in (wpid, cpid):
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)


def test_worker_crash_recorded(tmp_path):
    p = make_plan("r", "FIXTURE", {}, [("c", {}), ("d", {})])
    run = Run("r", p, runs_root=tmp_path)
    end = run.execute(fx.crash, workers=1, timeout_s=10)
    assert end["failed"] == 2
    assert {f["status"] for f in load_run(run.dir)["failures"].values()} == {"worker_died"}


def test_real_interruption_and_resume(tmp_path):
    """SIGKILL the whole runner process group mid-run, then resume: every item ends with exactly one
    terminal attempt, no completed item is re-run, nothing is lost."""
    script = tmp_path / "drive.py"
    script.write_text(textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {str(ROOT / 'src')!r})
        from causalguard.runner import Run, make_plan
        from causalguard import testing_fixtures as fx
        if __name__ == "__main__":
            items = [(f"it{{i}}", {{"value": i, "sleep": 0.4}}) for i in range(12)]
            plan = make_plan("r", "FIXTURE", {{}}, items)
            Run("r", plan, runs_root={str(tmp_path)!r}, resume=sys.argv[1] == "resume").execute(
                fx.echo, workers=2, timeout_s=30)
    """))
    proc = subprocess.Popen([sys.executable, str(script), "new"], start_new_session=True)
    adir = tmp_path / "r" / "attempts"
    t0 = time.time()
    while time.time() - t0 < 60:
        if adir.exists() and len(list(adir.rglob("*.json"))) >= 3:
            break
        time.sleep(0.05)
    os.killpg(proc.pid, signal.SIGKILL)
    proc.wait()
    first = load_run(tmp_path / "r")
    assert 3 <= len(first["results"]) < 12 and first["missing"]
    done_before = {k: v["pid"] for k, v in first["results"].items()}
    subprocess.run([sys.executable, str(script), "resume"], check=True, timeout=120)
    lr = load_run(tmp_path / "r")
    assert len(lr["results"]) == 12 and not lr["missing"] and not lr["failures"]
    assert all(lr["results"][k]["pid"] == pid for k, pid in done_before.items())
    ev = read_jsonl(tmp_path / "r" / "events.jsonl")
    assert [e["event"] for e in ev].count("resume") == 1
    starts = [e["item_id"] for e in ev if e["event"] == "attempt_start"]
    ends = [e["item_id"] for e in ev if e["event"] == "attempt_end"]
    assert sorted(set(starts)) == sorted(set(ends)) and len(ends) == 12  # interrupted starts were re-run
    assert json.loads((tmp_path / "r" / "plan.json").read_text())["plan_sha256"] == lr["plan"]["plan_sha256"]
