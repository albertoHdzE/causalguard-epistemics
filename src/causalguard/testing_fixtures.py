"""Disposable fixture items for runner/lifecycle tests.  NOT scientific items.

They live in the package (not in tests/) because spawned worker processes must import them.
"""
from __future__ import annotations

import os
import signal
import subprocess
import time


def echo(p: dict) -> dict:
    if p.get("sleep"):
        time.sleep(p["sleep"])
    if p.get("fail"):
        raise ValueError("fixture failure")
    return {"value": p.get("value"), "pid": os.getpid()}


def nested_timer_then_hang(p: dict) -> dict:
    """A nested SIGALRM-timed operation (as in S1 per-query caps) followed by a long computation."""
    from .experiments.s1 import _with_timeout
    _with_timeout(lambda: None, 0.01)
    time.sleep(p.get("hang", 5))
    return {"inner": "completed"}


def hung_with_child(p: dict) -> dict:
    """Noncooperating worker: ignores SIGTERM/SIGALRM, starts a child process, then spins."""
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGALRM, signal.SIG_IGN)
    child = subprocess.Popen(["sleep", "300"])
    with open(p["pidfile"], "w") as fh:
        fh.write(f"{os.getpid()} {child.pid}\n")
    x = 0
    while True:  # busy loop (no cooperative interruption points beyond the interpreter)
        x += 1


def crash(p: dict) -> dict:
    os._exit(7)
