"""R3-02: a worker must never start a payload for an already-dead supervisor (synchronous startup refusal), while
work for a live supervisor proceeds and the watchdog still handles later death."""
import multiprocessing as mp
import time

import pytest

from causalguard import testing_fixtures as fx
from causalguard.runner import FileLock, Run, _lifeline_closed, _worker_main, load_run, make_plan


def _spawn(ctx, lock, close_lifeline_first: bool):
    conn, child = ctx.Pipe()
    life_r, life_w = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_worker_main, args=(child, fx.touch_marker, life_r, str(lock)), daemon=True)
    if close_lifeline_first:
        # the supervisor is already dead: its write end is closed before the worker even exists
        life_w.close()
    proc.start()
    child.close()
    life_r.close()
    return conn, life_w, proc


@pytest.mark.parametrize("rep", range(5))
def test_dead_supervisor_immediate_side_effect_never_happens(tmp_path, rep):
    """The reviewer's 5/5 reproduction: a queued payload with an IMMEDIATE side effect, lifeline already closed."""
    ctx = mp.get_context("spawn")
    marker = tmp_path / "marker"
    conn, life_w, proc = _spawn(ctx, tmp_path / "w.lock", close_lifeline_first=False)
    life_w.close()                                     # death between spawn and the worker's setup
    conn.send({"marker": str(marker)})
    proc.join(15)
    assert not proc.is_alive()
    time.sleep(0.2)
    assert not marker.exists(), "payload side effect executed for a dead supervisor"
    assert FileLock(tmp_path / "w.lock").acquire(exclusive=True, timeout=5.0)


def test_late_starting_old_worker_after_drain_runs_nothing_and_resume_completes(tmp_path):
    """Controlled late start: a new owner drains the workers lock and releases it; an OLD worker whose supervisor is
    dead then starts and obtains the shared lock.  It must run nothing; the new owner's run still completes."""
    ctx = mp.get_context("spawn")
    lock = tmp_path / "w.lock"
    fl = FileLock(lock)
    assert fl.acquire(exclusive=True, timeout=5.0)    # new owner drains ...
    fl.release()                                      # ... and releases before the old worker gets scheduled
    marker = tmp_path / "old-marker"
    conn, _w, proc = _spawn(ctx, lock, close_lifeline_first=True)
    conn.send({"marker": str(marker)})
    proc.join(15)
    assert not proc.is_alive() and not marker.exists()
    # the new owner's resume is unaffected and produces the only side effect
    p = make_plan("late", "FIXTURE", {}, [("a", {"marker": str(tmp_path / "new-marker")})])
    run = Run("late", p, runs_root=tmp_path / "runs")
    st = run.execute(fx.touch_marker, workers=1, timeout_s=30)
    assert st["status"] == "complete" and (tmp_path / "new-marker").exists()
    assert load_run(tmp_path / "runs" / "late")["results"]["a"]["marker"] == str(tmp_path / "new-marker")


def test_live_supervisor_worker_runs_immediately(tmp_path):
    """The guard does not refuse a live supervisor (no false positive)."""
    ctx = mp.get_context("spawn")
    marker = tmp_path / "m"
    conn, life_w, proc = _spawn(ctx, tmp_path / "w.lock", close_lifeline_first=False)
    conn.send({"marker": str(marker)})
    assert conn.poll(20)
    status, out, _dt, _rss = conn.recv()
    assert status == "ok" and marker.exists()
    conn.send(None)
    proc.join(10)
    life_w.close()


def test_watchdog_still_kills_on_death_during_payload(tmp_path):
    ctx = mp.get_context("spawn")
    marker = tmp_path / "m"
    conn, life_w, proc = _spawn(ctx, tmp_path / "w.lock", close_lifeline_first=False)
    conn.send({"marker": str(marker), "sleep": 60})
    deadline = time.time() + 20
    while not marker.exists() and time.time() < deadline:
        time.sleep(0.05)
    assert marker.exists()
    life_w.close()                                    # supervisor dies mid-payload
    proc.join(15)
    assert not proc.is_alive()
    assert not conn.poll(0.5) or pytest.raises(EOFError, conn.recv)


def test_lifeline_closed_primitive():
    r, w = mp.Pipe(duplex=False)
    assert _lifeline_closed(r.fileno()) is False
    w.close()
    assert _lifeline_closed(r.fileno()) is True
