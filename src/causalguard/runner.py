"""Resumable, append-only experiment runner.

Owner of: run directories, RUNS.jsonl registry, config hashing, resume rules
and failure records.

Rules
-----
* A run directory ``runs/<run_id>/`` holds ``config.json`` (frozen at start),
  ``records.jsonl`` (append-only, one JSON object per completed item) and
  ``failures.jsonl`` (exceptions/timeouts, also append-only).
* Resume re-opens the same run_id, refuses if the config hash differs (mixed
  configurations), and skips items whose ``item_id`` already has a record or a
  terminal failure.  Nothing is overwritten.
* Each item is executed in a worker process with a wall-clock cap; a timeout or
  crash becomes a failure record, never a silently dropped item.
* RUNS.jsonl (repository root) gets one 'start' and one 'end' line per
  invocation with config/commit/environment hashes.  No secrets are stored.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import multiprocessing as mp
import os
import platform
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Callable, Iterable

from .schema import canonical_json

ROOT = Path(__file__).resolve().parents[2]


def now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def config_hash(cfg: dict) -> str:
    return hashlib.sha256(canonical_json(cfg).encode()).hexdigest()


def git_state(root: Path = ROOT) -> dict:
    try:
        commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True,
                                         stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
                                             text=True, stderr=subprocess.DEVNULL).strip())
    except Exception:
        commit, dirty = None, None
    return {"commit": commit, "dirty": dirty}


def environment_info() -> dict:
    import numpy
    info = {"python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine(),
            "numpy": numpy.__version__, "cpu_count": os.cpu_count()}
    for mod in ("pysat", "dd"):
        try:
            m = __import__(mod)
            info[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            info[mod] = None
    info["env_hash"] = hashlib.sha256(canonical_json(info).encode()).hexdigest()[:16]
    return info


def _registry_append(entry: dict, registry: Path) -> None:
    with registry.open("a") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


class Run:
    def __init__(self, run_id: str, config: dict, runs_root: Path | None = None, registry: Path | None = None):
        self.run_id = run_id
        self.config = config
        self.chash = config_hash(config)
        self.dir = (runs_root or ROOT / "runs") / run_id
        self.registry = registry or ROOT / "RUNS.jsonl"
        self.dir.mkdir(parents=True, exist_ok=True)
        cfg_path = self.dir / "config.json"
        if cfg_path.exists():
            old = json.loads(cfg_path.read_text())
            if old.get("config_hash") != self.chash:
                raise RuntimeError(f"run {run_id}: config hash mismatch on resume (mixed configurations refused)")
        else:
            cfg_path.write_text(json.dumps({"run_id": run_id, "config": config, "config_hash": self.chash,
                                            "created": now(), "git": git_state(), "environment": environment_info()},
                                           indent=1, sort_keys=True))
        self.records = self.dir / "records.jsonl"
        self.failures = self.dir / "failures.jsonl"

    def done_ids(self) -> set[str]:
        ids = set()
        for p in (self.records, self.failures):
            if p.exists():
                for line in p.open():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ids.add(json.loads(line)["item_id"])
                    except Exception:
                        continue  # a torn final line from a crash is ignored, never rewritten
        return ids

    def append(self, path: Path, obj: dict) -> None:
        with path.open("a") as fh:
            fh.write(json.dumps(obj, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def execute(self, items: Iterable[tuple[str, dict]], fn: Callable[[dict], dict], workers: int = 1,
                timeout_s: float = 600.0, quiet: bool = True, mode: str = "development",
                maxtasks: int = 50) -> dict:
        items = list(items)
        done = self.done_ids()
        todo = [(i, p) for i, p in items if i not in done]
        start = {"event": "start", "run_id": self.run_id, "mode": mode, "time": now(), "config_hash": self.chash,
                 "git": git_state(), "env_hash": environment_info()["env_hash"], "items_total": len(items),
                 "items_todo": len(todo), "artifact_dir": str(self.dir.relative_to(ROOT)) if self.dir.is_relative_to(ROOT) else str(self.dir)}
        _registry_append(start, self.registry)
        t0 = time.time()
        ok = fail = 0
        ctx = mp.get_context("spawn")
        with ctx.Pool(processes=max(1, workers), maxtasksperchild=maxtasks) as pool:
            pending = {}
            for item_id, payload in todo:
                pending[item_id] = pool.apply_async(_call, (fn, payload, timeout_s))
            for item_id, res in pending.items():
                try:
                    status, out, secs = res.get(timeout=timeout_s * 4 + 60)
                except mp.TimeoutError:
                    status, out, secs = "timeout", {"error": f"worker unresponsive beyond {timeout_s * 4 + 60}s"}, timeout_s
                if status == "ok":
                    out = {"item_id": item_id, "run_id": self.run_id, "seconds": secs, **out}
                    self.append(self.records, out)
                    ok += 1
                else:
                    self.append(self.failures, {"item_id": item_id, "run_id": self.run_id, "status": status,
                                                "seconds": secs, **out})
                    fail += 1
                if not quiet:
                    print(f"[{self.run_id}] {item_id} {status} {secs:.1f}s", flush=True)
        end = {"event": "end", "run_id": self.run_id, "time": now(), "status": "complete" if not fail else "complete_with_failures",
               "ok": ok, "failed": fail, "skipped_already_done": len(items) - len(todo), "wall_s": round(time.time() - t0, 1)}
        _registry_append(end, self.registry)
        return end


class ItemTimeout(Exception):
    pass


def _alarm(signum, frame):
    raise ItemTimeout()


def _call(fn, payload, timeout_s=None):
    """Run one item inside a worker; a per-item wall-clock cap is enforced with
    SIGALRM (POSIX), so a timeout is attributed to the item that caused it."""
    import resource
    import signal
    t0 = time.time()
    if timeout_s:
        signal.signal(signal.SIGALRM, _alarm)
        signal.setitimer(signal.ITIMER_REAL, timeout_s)
    try:
        out = fn(payload)
        status = "ok"
    except ItemTimeout:
        out, status = {"error": f"wall-clock cap {timeout_s}s"}, "timeout"
    except MemoryError:
        out, status = {"error": "MemoryError"}, "oom"
    except Exception as e:  # recorded as a failure, never dropped
        out, status = {"error": repr(e), "traceback": traceback.format_exc()[-4000:]}, "error"
    finally:
        if timeout_s:
            signal.setitimer(signal.ITIMER_REAL, 0)
    if isinstance(out, dict):
        out.setdefault("worker_peak_rss_bytes", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                       * (1 if sys.platform == "darwin" else 1024))
    return status, out, time.time() - t0


def read_jsonl(path: Path) -> list[dict]:
    out = []
    if not path.exists():
        return out
    for line in path.open():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out
