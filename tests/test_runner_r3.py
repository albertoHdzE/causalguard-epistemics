"""Iteration-3 runner repairs (review R2-01..R2-04): exclusive ownership, no-clobber attempts, parent-death
cleanup, storage-derived status and strict identity validation.  Temporary FIXTURE storage only."""
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
from causalguard.runner import Ledger, Run, RunBusy, RunCorruption, RunRefused, config_hash, load_run, make_plan, publish_new_json, read_jsonl

ROOT = Path(__file__).resolve().parents[1]


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def _wait_dead(pids, bound=5.0) -> bool:
    t_end = time.time() + bound
    while time.time() < t_end:
        if not any(_alive(p) for p in pids):
            return True
        time.sleep(0.05)
    return not any(_alive(p) for p in pids)


def _driver(tmp_path: Path, body: str) -> Path:
    script = tmp_path / "drive.py"
    script.write_text(textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {str(ROOT / 'src')!r})
        from causalguard.runner import Run, RunBusy, make_plan
        from causalguard import testing_fixtures as fx
        ROOT = {str(tmp_path)!r}
        if __name__ == "__main__":
    """) + textwrap.indent(textwrap.dedent(body), "    "))
    return script


def _attempt_files(run_dir: Path) -> list[Path]:
    return sorted((run_dir / "attempts").rglob("*.json"))


# ------------------------------------------------------------------------------------------------ R2-01

def test_concurrent_resume_is_refused_and_attempt_bytes_survive(tmp_path):
    """Process A owns and executes; process B resumes while A is mid-item and must be refused without touching
    anything; exactly one successful attempt exists afterwards and its bytes are unchanged by a later resume."""
    plan = make_plan("same", "FIXTURE", {}, [("item", {"value": 1, "sleep": 2})])
    Run("same", plan, runs_root=tmp_path).close()
    script = _driver(tmp_path, """
        plan = make_plan("same", "FIXTURE", {}, [("item", {"value": 1, "sleep": 2})])
        try:
            end = Run("same", plan, runs_root=ROOT, resume=True).execute(fx.echo, workers=1, timeout_s=30)
        except RunBusy as e:
            print("BUSY", e)
            sys.exit(4)
        sys.exit(0 if end["status"] == "complete" else 3)
    """)
    a = subprocess.Popen([sys.executable, str(script)])
    ev = tmp_path / "same" / "events.jsonl"
    t0 = time.time()
    while time.time() - t0 < 30 and not any(e.get("event") == "attempt_start" for e in read_jsonl(ev)):
        time.sleep(0.02)
    b = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=60)
    assert b.returncode == 4 and "BUSY" in b.stdout
    assert a.wait(60) == 0
    files = _attempt_files(tmp_path / "same")
    assert len(files) == 1
    original = files[0].read_bytes()
    ends = [e for e in read_jsonl(ev) if e["event"] == "attempt_end"]
    assert len(ends) == 1 and ends[0]["status"] == "ok"
    # a later (sequential) resume is a no-op and leaves the bytes intact
    end = Run("same", plan, runs_root=tmp_path, resume=True).execute(fx.echo, workers=1, timeout_s=30)
    assert end["status"] == "complete" and end["invocation"]["attempted"] == 0
    assert _attempt_files(tmp_path / "same") == files and files[0].read_bytes() == original


def test_second_opener_refused_and_live_temporary_not_quarantined(tmp_path):
    plan = make_plan("r", "FIXTURE", {}, [("a", {"value": 1})])
    owner = Run("r", plan, runs_root=tmp_path)
    live_tmp = tmp_path / "r" / "attempts" / "deadbeef" / "001.json.tmp99999"
    live_tmp.parent.mkdir(parents=True)
    live_tmp.write_bytes(b"in-flight")
    before = (tmp_path / "r" / "events.jsonl").read_bytes()
    with pytest.raises(RunBusy):
        Run("r", plan, runs_root=tmp_path, resume=True)
    assert live_tmp.read_bytes() == b"in-flight"
    assert (tmp_path / "r" / "events.jsonl").read_bytes() == before
    with pytest.raises(RunBusy):          # a NEW open of an owned id is refused before inspecting the directory
        Run("r", plan, runs_root=tmp_path)
    owner.close()
    live_tmp.unlink()
    live_tmp.parent.rmdir()
    Run("r", plan, runs_root=tmp_path, resume=True).close()   # released ownership can be taken again


def test_publication_never_replaces_an_existing_attempt(tmp_path):
    f = tmp_path / "attempts" / "k" / "001.json"
    publish_new_json(f, {"x": 1})
    original = f.read_bytes()
    with pytest.raises(RunCorruption, match="refusing to overwrite"):
        publish_new_json(f, {"x": 2})
    assert f.read_bytes() == original and not list(f.parent.glob("*.tmp*"))


def test_shared_registry_concurrent_writers_do_not_corrupt(tmp_path):
    reg = tmp_path / "registry.jsonl"
    script = tmp_path / "w.py"
    script.write_text(textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {str(ROOT / 'src')!r})
        from causalguard.runner import Ledger
        led = Ledger({str(reg)!r}, shared=True)
        for i in range(300):
            led.recover_and_append({{"writer": sys.argv[1], "i": i, "pad": "x" * 2000}})
    """))
    procs = [subprocess.Popen([sys.executable, str(script), str(k)]) for k in range(4)]
    assert all(p.wait(120) == 0 for p in procs)
    recs = read_jsonl(reg)
    assert len(recs) == 1200 and {(r["writer"], r["i"]) for r in recs} == {(str(k), i) for k in range(4) for i in range(300)}


# ------------------------------------------------------------------------------------------------ R2-02

def test_hard_supervisor_group_kill_cleans_worker_group_and_resume_does_not_overlap(tmp_path):
    """SIGKILL the supervisor's whole process group while a noncooperating worker (and its child) runs.  The
    lifeline watchdog must kill the worker group within the declared bound; an IMMEDIATE resume must wait for
    the old group to vanish (workers lock) before it proceeds, and then nothing old is alive."""
    pidfile = tmp_path / "pids"
    script = _driver(tmp_path, f"""
        plan = make_plan("kill", "FIXTURE", {{}}, [("item", {{"pidfile": {str(pidfile)!r}}})])
        Run("kill", plan, runs_root=ROOT).execute(fx.hung_with_child, workers=1, timeout_s=120)
    """)
    parent = subprocess.Popen([sys.executable, str(script)], start_new_session=True,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wpid = cpid = None
    try:
        t0 = time.time()
        while not pidfile.exists() and time.time() - t0 < 30:
            time.sleep(0.02)
        time.sleep(0.2)
        wpid, cpid = map(int, pidfile.read_text().split())
        os.killpg(parent.pid, signal.SIGKILL)
        parent.wait()
        plan = make_plan("kill", "FIXTURE", {}, [("item", {"pidfile": str(pidfile)})])
        t_kill = time.time()
        resumed = Run("kill", plan, runs_root=tmp_path, resume=True)      # immediately after the kill
        assert not _alive(wpid) or _wait_dead([wpid], 0.5)
        assert _wait_dead([wpid, cpid], 5.0), "worker group survived supervisor death"
        assert time.time() - t_kill < 10
        resumed.close()
        lr = load_run(tmp_path / "kill")
        assert lr["missing"] == ["item"] and lr["execution_status"]["status"] == "incomplete"
    finally:
        for pid in (wpid, cpid):
            if pid and _alive(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


def test_normal_end_leaves_no_watchdog_or_worker(tmp_path):
    p = make_plan("r", "FIXTURE", {}, [(f"i{k}", {"value": k}) for k in range(3)])
    end = Run("r", p, runs_root=tmp_path).execute(fx.echo, workers=2, timeout_s=30)
    pids = {r["pid"] for r in load_run(tmp_path / "r")["results"].values()}
    assert end["status"] == "complete" and _wait_dead(pids, 5.0)


# ------------------------------------------------------------------------------------------------ R2-03

def test_failure_then_noop_resume_stays_complete_with_failures(tmp_path):
    p = make_plan("f", "FIXTURE", {}, [("ok", {"value": 1}), ("bad", {"value": 1, "fail": True})])
    first = Run("f", p, runs_root=tmp_path).execute(fx.echo, workers=1, timeout_s=30)
    second = Run("f", p, runs_root=tmp_path, resume=True).execute(fx.echo, workers=1, timeout_s=30)
    for end in (first, second):
        assert end["status"] == "complete_with_failures" and end["failed"] == 1 and end["ok"] == 1
    assert second["invocation"] == {"attempted": 0, "ok": 0, "failed": 0}
    assert load_run(tmp_path / "f")["execution_status"]["status"] == "complete_with_failures"
    with pytest.raises(RunRefused, match="development-only"):
        Run("f", p, runs_root=tmp_path, resume=True).execute(fx.echo, retry_failed=True, mode="confirmatory")
    third = Run("f", p, runs_root=tmp_path, resume=True).execute(fx.echo, workers=1, timeout_s=30, retry_failed=True)
    assert third["status"] == "complete_with_failures"       # the fixture fails deterministically again
    atts = json.loads(sorted((tmp_path / "f" / "attempts").rglob("002.json"))[0].read_text())
    assert atts["supersedes"] == [1] and atts["status"] == "error"


# ------------------------------------------------------------------------------------------------ R2-04

def _rewrite(path: Path, **changes) -> None:
    rec = json.loads(path.read_text())
    rec.update(changes)
    path.write_text(json.dumps(rec))


def test_altered_stored_plan_with_old_digest_is_refused(tmp_path):
    p = make_plan("id", "FIXTURE", {}, [("item", {"value": 1})])
    Run("id", p, runs_root=tmp_path).execute(fx.echo, workers=1, timeout_s=30)
    pp = tmp_path / "id" / "plan.json"
    saved = json.loads(pp.read_text())
    saved["items"][0]["payload"]["value"] = 999          # digest string left unchanged
    pp.write_text(json.dumps(saved))
    with pytest.raises(RunCorruption, match="digest"):
        Run("id", p, runs_root=tmp_path, resume=True)
    with pytest.raises(RunCorruption):
        load_run(tmp_path / "id")
    # a fully re-digested but different stored plan is a different plan: refused as such
    saved["items"][0]["payload_sha256"] = config_hash(saved["items"][0]["payload"])
    saved["plan_sha256"] = config_hash({k: v for k, v in saved.items() if k != "plan_sha256"})
    pp.write_text(json.dumps(saved))
    with pytest.raises(RunRefused, match="plan differs"):
        Run("id", p, runs_root=tmp_path, resume=True)


@pytest.mark.parametrize("field,value", [("run_id", "OTHER_RUN"), ("plan_sha256", "0" * 64),
                                         ("source_tree_sha256", "f" * 64), ("payload_sha256", "a" * 64),
                                         ("status", "maybe"), ("supersedes", []), ("unexpected", 1)])
@pytest.mark.parametrize("which", ["superseded_failure", "latest"])
def test_wrong_identity_on_any_attempt_is_corruption_before_mutation(tmp_path, field, value, which):
    p = make_plan("w", "FIXTURE", {}, [("bad", {"value": 1, "fail": True})])
    Run("w", p, runs_root=tmp_path).execute(fx.echo, workers=1, timeout_s=30)
    Run("w", p, runs_root=tmp_path, resume=True).execute(fx.echo, workers=1, timeout_s=30, retry_failed=True)
    f1, f2 = sorted((tmp_path / "w" / "attempts").rglob("*.json"))
    target = f1 if which == "superseded_failure" else f2
    if field == "supersedes" and which == "superseded_failure":
        value = [7]
    _rewrite(target, **{field: value})
    with pytest.raises(RunCorruption):
        load_run(tmp_path / "w")
    # resume must refuse BEFORE recovery mutates storage: a torn ledger tail and a stray temporary survive
    ev = tmp_path / "w" / "events.jsonl"
    with open(ev, "ab") as fh:
        fh.write(b'{"torn')
    stray = f2.parent / "003.json.tmp1"
    stray.write_bytes(b"x")
    before = ev.read_bytes()
    with pytest.raises(RunCorruption):
        Run("w", p, runs_root=tmp_path, resume=True)
    assert ev.read_bytes() == before and stray.exists() and not (tmp_path / "w" / "quarantine").exists()


def test_ledger_shared_lock_file_is_outside_ledger(tmp_path):
    led = Ledger(tmp_path / "access_ledger.jsonl", shared=True)
    led.append({"a": 1})
    assert read_jsonl(tmp_path / "access_ledger.jsonl") == [{"a": 1}]


def test_worker_started_after_supervisor_death_never_runs_work(tmp_path):
    """Startup race: the lifeline's write end is already closed when a worker starts (its supervisor died between
    spawning and setup).  The worker's group must die promptly, release the workers lock and run no payload."""
    import multiprocessing as mp

    from causalguard.runner import FileLock, _worker_main
    ctx = mp.get_context("spawn")
    conn, child = ctx.Pipe()
    life_r, life_w = ctx.Pipe(duplex=False)
    lock = tmp_path / "w.lock"
    proc = ctx.Process(target=_worker_main, args=(child, fx.echo, life_r, str(lock)), daemon=True)
    proc.start()
    child.close()
    life_r.close()
    life_w.close()                                   # "supervisor death" before the worker finished its setup
    conn.send({"value": 1, "sleep": 30})             # work that must never complete
    proc.join(10)
    assert not proc.is_alive()
    with pytest.raises(EOFError):                    # the pipe is closed and no result was ever produced
        conn.recv()
    assert FileLock(lock).acquire(exclusive=True, timeout=5.0)


def test_same_object_can_execute_twice_and_reacquires_as_resume(tmp_path):
    p = make_plan("t", "FIXTURE", {}, [("a", {"value": 1}), ("b", {"value": 2})])
    run = Run("t", p, runs_root=tmp_path)
    first = run.execute(fx.echo, workers=1, timeout_s=30, stop_after=1)
    second = run.execute(fx.echo, workers=1, timeout_s=30)
    assert first["status"] == "incomplete" and second["status"] == "complete" and second["invocation"]["attempted"] == 1
    assert [e["event"] for e in read_jsonl(tmp_path / "t" / "events.jsonl")].count("resume") == 1
    assert not [d for d in tmp_path.iterdir() if ".creating-" in d.name]


def test_published_attempt_without_ledger_end_is_reconciled_on_resume(tmp_path):
    p = make_plan("g", "FIXTURE", {}, [("a", {"value": 1}), ("b", {"value": 2})])
    Run("g", p, runs_root=tmp_path).execute(fx.echo, workers=1, timeout_s=30)
    ev = tmp_path / "g" / "events.jsonl"
    lines = [x for x in ev.read_text().splitlines(keepends=True)
             if not ('"attempt_end"' in x and '"item_id": "b"' in x)]          # the kill landed after publication
    ev.write_text("".join(lines))
    Run("g", p, runs_root=tmp_path, resume=True).close()
    ends = [e for e in read_jsonl(ev) if e["event"] == "attempt_end"]
    assert sorted(e["item_id"] for e in ends) == ["a", "b"]
    assert [e.get("reconciled") for e in ends if e["item_id"] == "b"] == [True]
    Run("g", p, runs_root=tmp_path, resume=True).close()                       # idempotent
    assert len([e for e in read_jsonl(ev) if e["event"] == "attempt_end"]) == 2
