"""Resumable experiment runner with a persisted item plan, atomic attempt records,
a supervising scheduler and strict logs (iteration 2; repairs R03, R04, R05, R06).

Owner of: run directories, the item plan, attempt records, the run event ledger,
the registry, source/config identity, resume rules, per-item deadlines and
failure records.  Every analysis reads run outputs through ``load_run``.

Layout of a v2 run directory ``<runs_root>/<run_id>/``::

    plan.json            immutable plan: config, config hash, source identity, every planned item
                         (id, payload, payload hash, strata) and the plan digest
    attempts/<key>/NNN.json   ONE file per finished attempt, written atomically (tmp + fsync + rename).
                         status ok | error | timeout | oom | worker_died.  A later attempt names the
                         attempts it supersedes; failed attempts are never deleted.
    events.jsonl         append-only ledger: open, resume, attempt_start, attempt_end, kill, quarantine.
    quarantine/          exact bytes of a torn ledger tail or a stray temporary file, with digests.

Rules
-----
* A run is opened either NEW (directory must not exist) or with ``resume=True`` (plan must exist
  and be byte-identical in its digest: same items, payloads, config and source identity).  Anything
  else is refused before any item executes.
* Readers are strict.  A malformed attempt file, an invalid interior ledger line or two
  conflicting successful attempts are corruption: ``RunCorruption`` is raised (fail closed).  Only
  a torn FINAL ledger line can be recovered: its exact bytes are quarantined (offset, length,
  sha256) and a ``quarantine`` event is appended; then the ledger is truncated at that offset.
* Per-item deadlines are enforced by the PARENT: each worker runs in its own process group;
  when an item exceeds its deadline the parent SIGKILLs the whole group, reaps it, records a
  ``timeout`` attempt and starts a fresh worker.  Code inside an item (e.g. S1 per-query caps)
  may use SIGALRM freely; it cannot cancel the outer deadline.
* An item is terminal when it has an ok attempt, or a failed attempt and no retry was requested.
  ``retry_failed=True`` (explicit, logged) re-runs failed items under their original identity.
* The registry (``<runs_root>/registry.jsonl``) lives with runtime storage, never in a tracked
  file, so a frozen checkout stays clean while studies execute.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import multiprocessing as mp
import os
import platform
import signal
import subprocess
import sys
import time
import traceback
from multiprocessing.connection import wait as mp_wait
from pathlib import Path
from typing import Callable

from .schema import canonical_json

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).resolve().parent
PLAN_SCHEMA = "causalguard-plan-v2"
ATTEMPT_SCHEMA = "causalguard-attempt-v2"
FAILED = ("error", "timeout", "oom", "worker_died")


class RunCorruption(RuntimeError):
    """Run storage is inconsistent; analysis and execution must stop."""


class RunRefused(RuntimeError):
    """A run cannot be opened/resumed under the requested identity."""


def now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def config_hash(cfg: dict) -> str:
    return sha256_bytes(canonical_json(cfg).encode())


def default_runs_root() -> Path:
    return Path(os.environ.get("CAUSALGUARD_RUNS", str(ROOT / "runs")))


def git_state(root: Path = ROOT) -> dict:
    try:
        commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True,
                                         stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
                                             text=True, stderr=subprocess.DEVNULL).strip())
    except Exception:
        commit, dirty = None, None
    return {"commit": commit, "dirty": dirty}


def source_tree_digest(src: Path = SRC) -> str:
    """sha256 over (relative path, content) of every .py file of the package: the executable identity
    of a run, independent of git (a snapshot worktree and the main tree agree iff the code agrees)."""
    h = hashlib.sha256()
    for p in sorted(src.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        h.update(str(p.relative_to(src)).encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


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
    info["env_hash"] = sha256_bytes(canonical_json(info).encode())[:16]
    return info


# --------------------------------------------------------------------------- atomic files / strict jsonl

def _fsync_dir(d: Path) -> None:
    fd = os.open(str(d), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    data = json.dumps(obj, sort_keys=True, default=_json_default).encode()
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def _json_default(o):
    import numpy as np
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    raise TypeError(type(o))


def read_jsonl(path: Path) -> list[dict]:
    """STRICT reader: every non-empty line must be a JSON object, the file must end with a newline.
    Any defect raises RunCorruption (it is never silently skipped)."""
    path = Path(path)
    if not path.exists():
        return []
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        off = data.rfind(b"\n") + 1
        raise RunCorruption(f"{path}: torn final line at offset {off} (recover via Ledger.recover)")
    out = []
    for no, line in enumerate(data.split(b"\n"), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise RunCorruption(f"{path}:{no}: invalid JSON line ({e})") from None
        if not isinstance(obj, dict):
            raise RunCorruption(f"{path}:{no}: not a JSON object")
        out.append(obj)
    return out


class Ledger:
    """Append-only JSONL with boundary-safe recovery of a torn final line."""

    def __init__(self, path: Path, quarantine_dir: Path | None = None):
        self.path = Path(path)
        self.qdir = quarantine_dir or self.path.parent / "quarantine"

    def recover(self) -> dict | None:
        """If the file ends in a torn fragment, move the exact bytes to quarantine, truncate at the
        last newline and record a quarantine event.  Interior defects are NOT recoverable."""
        if not self.path.exists():
            return None
        data = self.path.read_bytes()
        if not data or data.endswith(b"\n"):
            read_jsonl(self.path)  # validate interior strictly
            return None
        off = data.rfind(b"\n") + 1
        frag = data[off:]
        head = data[:off]
        tmp = self.path.with_name(self.path.name + ".head")
        tmp.write_bytes(head)
        read_jsonl(tmp)  # interior must be valid before we truncate
        tmp.unlink()
        self.qdir.mkdir(parents=True, exist_ok=True)
        digest = sha256_bytes(frag)
        qpath = self.qdir / f"{self.path.name}.offset{off}.{digest[:16]}.bin"
        qpath.write_bytes(frag)
        with open(self.path, "r+b") as fh:
            fh.truncate(off)
            fh.flush()
            os.fsync(fh.fileno())
        ev = {"event": "quarantine", "time": now(), "file": self.path.name, "offset": off, "length": len(frag),
              "sha256": digest, "quarantine_path": qpath.name}
        self.append(ev)
        return ev

    def append(self, obj: dict) -> None:
        line = (json.dumps(obj, sort_keys=True, default=_json_default) + "\n").encode()
        with open(self.path, "ab") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())

    def read(self) -> list[dict]:
        return read_jsonl(self.path)


# --------------------------------------------------------------------------- plan

def item_key(item_id: str) -> str:
    return sha256_bytes(item_id.encode())[:20]


def make_plan(run_id: str, study: str, config: dict, items: list[tuple[str, dict]], strata_fn=None,
              source_digest: str | None = None, extra: dict | None = None) -> dict:
    ids = [i for i, _ in items]
    if len(set(ids)) != len(ids):
        dup = sorted({i for i in ids if ids.count(i) > 1})[:5]
        raise RunRefused(f"duplicate item ids in plan: {dup}")
    keys = [item_key(i) for i in ids]
    if len(set(keys)) != len(keys):  # pragma: no cover - sha256 prefix collision
        raise RunRefused("item key collision")
    plan_items = []
    for iid, payload in items:
        e = {"item_id": iid, "payload": payload, "payload_sha256": config_hash(payload)}
        if strata_fn:
            e["strata"] = strata_fn(payload)
        plan_items.append(e)
    body = {"schema": PLAN_SCHEMA, "run_id": run_id, "study": study, "config": config,
            "config_hash": config_hash(config), "source_tree_sha256": source_digest or source_tree_digest(),
            "items": plan_items, **(extra or {})}
    body["plan_sha256"] = config_hash(body)
    return body


class Run:
    """A v2 run.  ``Run(run_id, plan, resume=...)``; see module docstring."""

    def __init__(self, run_id: str, plan: dict, runs_root: Path | None = None, resume: bool = False,
                 registry: Path | None = None):
        self.run_id = run_id
        self.root = Path(runs_root) if runs_root else default_runs_root()
        self.dir = self.root / run_id
        self.registry = Ledger(Path(registry) if registry else self.root / "registry.jsonl")
        if plan.get("run_id") != run_id:
            raise RunRefused("plan run_id mismatch")
        self.plan = plan
        plan_path = self.dir / "plan.json"
        if resume:
            if not plan_path.exists():
                raise RunRefused(f"run {run_id}: --resume given but no plan exists at {plan_path}")
            old = json.loads(plan_path.read_text())
            if old.get("plan_sha256") != plan.get("plan_sha256"):
                diffs = [k for k in ("config_hash", "source_tree_sha256", "study") if old.get(k) != plan.get(k)]
                if len(old.get("items", [])) != len(plan["items"]):
                    diffs.append("item count")
                raise RunRefused(f"run {run_id}: resume refused, plan differs ({diffs or 'items/payloads'})")
        else:
            if self.dir.exists():
                raise RunRefused(f"run {run_id}: directory exists; pass resume=True (--resume) to continue it")
            self.dir.mkdir(parents=True)
            atomic_write_json(plan_path, plan)
        self.ledger = Ledger(self.dir / "events.jsonl")
        (self.dir / "attempts").mkdir(exist_ok=True)
        rec = self.ledger.recover()
        self._quarantine_stray_tmp()
        self.ledger.append({"event": "resume" if resume else "open", "time": now(), "run_id": run_id,
                            "plan_sha256": plan["plan_sha256"], "git": git_state(), "pid": os.getpid(),
                            "env_hash": environment_info()["env_hash"], "recovered": rec})
        self._items = {e["item_id"]: e for e in plan["items"]}

    def _quarantine_stray_tmp(self) -> None:
        for p in (self.dir / "attempts").rglob("*.tmp*"):
            data = p.read_bytes()
            q = self.dir / "quarantine"
            q.mkdir(exist_ok=True)
            digest = sha256_bytes(data)
            dest = q / f"{p.parent.name}.{p.name}.{digest[:16]}.bin"
            os.replace(p, dest)
            self.ledger.append({"event": "quarantine", "time": now(), "file": str(p.relative_to(self.dir)),
                                "length": len(data), "sha256": digest, "quarantine_path": dest.name})

    # ---- state
    def attempts(self) -> dict[str, list[dict]]:
        return read_attempts(self.dir, self._items)

    def terminal(self, retry_failed: bool = False) -> dict[str, dict]:
        out = {}
        for iid, atts in self.attempts().items():
            last = atts[-1]
            if last["status"] == "ok" or not retry_failed:
                out[iid] = last
        return out

    # ---- execution
    def execute(self, fn: Callable[[dict], dict], workers: int = 1, timeout_s: float = 600.0, quiet: bool = True,
                retry_failed: bool = False, maxtasks: int = 50, mode: str = "development",
                stop_after: int | None = None) -> dict:
        atts = self.attempts()
        done = {i for i, a in atts.items() if a[-1]["status"] == "ok" or (a[-1]["status"] in FAILED and not retry_failed)}
        todo = [e for e in self.plan["items"] if e["item_id"] not in done]
        if stop_after is not None:
            todo = todo[:stop_after]
        start = {"event": "start", "run_id": self.run_id, "mode": mode, "time": now(),
                 "plan_sha256": self.plan["plan_sha256"], "config_hash": self.plan["config_hash"],
                 "source_tree_sha256": self.plan["source_tree_sha256"], "git": git_state(),
                 "items_total": len(self.plan["items"]), "items_todo": len(todo), "retry_failed": retry_failed,
                 "run_dir": str(self.dir)}
        self.registry.recover()
        self.registry.append(start)
        self.ledger.append(start)
        t0 = time.time()
        counts = {"ok": 0, "failed": 0}

        def on_start(e):
            self.ledger.append({"event": "attempt_start", "time": now(), "item_id": e["item_id"]})

        def on_end(e, status, out, secs, extra):
            prior = atts.get(e["item_id"], [])
            n = len(prior) + 1
            rec = {"schema": ATTEMPT_SCHEMA, "run_id": self.run_id, "item_id": e["item_id"], "attempt": n,
                   "payload_sha256": e["payload_sha256"], "plan_sha256": self.plan["plan_sha256"],
                   "source_tree_sha256": self.plan["source_tree_sha256"], "status": status, "seconds": secs,
                   "finished": now(), "supersedes": [a["attempt"] for a in prior if a["status"] in FAILED],
                   **extra, "output": out}
            atomic_write_json(self.dir / "attempts" / item_key(e["item_id"]) / f"{n:03d}.json", rec)
            atts.setdefault(e["item_id"], []).append(rec)
            self.ledger.append({"event": "attempt_end", "time": now(), "item_id": e["item_id"], "attempt": n,
                                "status": status, "seconds": round(secs, 3)})
            counts["ok" if status == "ok" else "failed"] += 1
            if not quiet:
                print(f"[{self.run_id}] {e['item_id']} {status} {secs:.1f}s", flush=True)

        def on_kill(e, why):
            self.ledger.append({"event": "kill", "time": now(), "item_id": e["item_id"], "reason": why})

        supervise(todo, fn, workers, timeout_s, on_start, on_end, on_kill, maxtasks)
        terminal = {i for i, a in atts.items() if a}   # attempts recorded in this process + read at start (O(items))
        remaining = [e for e in self.plan["items"] if e["item_id"] not in terminal]
        end = {"event": "end", "run_id": self.run_id, "time": now(), "ok": counts["ok"], "failed": counts["failed"],
               "items_without_terminal_attempt": len(remaining),
               "status": ("complete" if not remaining and not counts["failed"] else
                          "complete_with_failures" if not remaining else "incomplete"),
               "wall_s": round(time.time() - t0, 1)}
        self.ledger.append(end)
        self.registry.append(end)
        return end


# --------------------------------------------------------------------------- reading runs (analysis side)

def read_attempts(run_dir: Path, planned: dict | None = None) -> dict[str, list[dict]]:
    """All attempt records of a v2 run, strictly validated, ordered by attempt number."""
    out: dict[str, list[dict]] = {}
    adir = Path(run_dir) / "attempts"
    if not adir.exists():
        return out
    for d in sorted(adir.iterdir()):
        if not d.is_dir():
            raise RunCorruption(f"unexpected file {d}")
        for f in sorted(d.iterdir()):
            if ".tmp" in f.name:
                raise RunCorruption(f"unquarantined temporary file {f} (open the run to quarantine it)")
            try:
                rec = json.loads(f.read_bytes())
            except Exception as e:
                raise RunCorruption(f"{f}: unreadable attempt record ({e})") from None
            if rec.get("schema") != ATTEMPT_SCHEMA or f.name != f"{rec.get('attempt', 0):03d}.json":
                raise RunCorruption(f"{f}: schema/attempt-number mismatch")
            if item_key(rec["item_id"]) != d.name:
                raise RunCorruption(f"{f}: item id does not match its directory")
            if planned is not None and rec["item_id"] not in planned:
                raise RunCorruption(f"{f}: attempt for an unplanned item {rec['item_id']}")
            out.setdefault(rec["item_id"], []).append(rec)
    for iid, atts in out.items():
        nums = [a["attempt"] for a in atts]
        if nums != list(range(1, len(atts) + 1)):
            raise RunCorruption(f"{iid}: attempt numbers {nums} are not contiguous")
        if sum(a["status"] == "ok" for a in atts) > 1:
            raise RunCorruption(f"{iid}: more than one successful attempt (conflicting results)")
        if any(a["status"] == "ok" for a in atts[:-1]):
            raise RunCorruption(f"{iid}: an attempt follows a successful attempt")
    return out


def load_run(run_dir: Path) -> dict:
    """Reconcile a run directory to its plan.  Returns
    {plan, results: {item_id: output}, failures: {item_id: last failed attempt}, missing: [item_id],
     attempts_total, layout}.  v1 (legacy) directories are read strictly from records/failures.jsonl."""
    run_dir = Path(run_dir)
    if (run_dir / "plan.json").exists():
        plan = json.loads((run_dir / "plan.json").read_text())
        body = {k: v for k, v in plan.items() if k != "plan_sha256"}
        if config_hash(body) != plan.get("plan_sha256"):
            raise RunCorruption(f"{run_dir}: plan digest mismatch")
        ev = Ledger(run_dir / "events.jsonl")
        if (run_dir / "events.jsonl").exists():
            ev.read()  # strict: torn tails must have been recovered by the runner
        planned = {e["item_id"]: e for e in plan["items"]}
        atts = read_attempts(run_dir, planned)
        results, failures, missing = {}, {}, []
        for iid, e in planned.items():
            a = atts.get(iid)
            if not a:
                missing.append(iid)
                continue
            if a[-1]["payload_sha256"] != e["payload_sha256"]:
                raise RunCorruption(f"{iid}: attempt payload hash differs from the plan")
            if a[-1]["status"] == "ok":
                results[iid] = a[-1]["output"]
            else:
                failures[iid] = a[-1]
        return {"layout": "v2", "plan": plan, "results": results, "failures": failures, "missing": missing,
                "attempts_total": sum(len(a) for a in atts.values()),
                "superseded_failures": sum(1 for a in atts.values() for x in a[:-1])}
    recs = read_jsonl(run_dir / "records.jsonl")
    fails = read_jsonl(run_dir / "failures.jsonl")
    ids = [r["item_id"] for r in recs]
    if len(set(ids)) != len(ids):
        raise RunCorruption(f"{run_dir}: duplicate item ids in legacy records")
    return {"layout": "v1_legacy", "plan": None, "results": {r["item_id"]: r for r in recs},
            "failures": {f["item_id"]: f for f in fails}, "missing": None, "attempts_total": len(recs) + len(fails)}


# --------------------------------------------------------------------------- supervisor

def _worker_main(conn, fn) -> None:
    os.setsid()  # own process group: the parent can kill everything this worker starts
    import resource
    while True:
        try:
            msg = conn.recv()
        except EOFError:
            return
        if msg is None:
            return
        payload = msg
        t0 = time.time()
        try:
            out = fn(payload)
            status = "ok"
        except MemoryError:
            out, status = {"error": "MemoryError"}, "oom"
        except Exception as e:  # recorded as a failure, never dropped
            out, status = {"error": repr(e)[:2000], "traceback": traceback.format_exc()[-4000:]}, "error"
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)
        try:
            conn.send((status, out, time.time() - t0, rss))
        except Exception as e:  # unpicklable output
            conn.send(("error", {"error": f"result not transferable: {e!r}"[:2000]}, time.time() - t0, rss))


class _Worker:
    def __init__(self, ctx, fn):
        self.conn, child = ctx.Pipe()
        self.proc = ctx.Process(target=_worker_main, args=(child, fn), daemon=True)
        self.proc.start()
        child.close()
        self.item = None
        self.deadline = None
        self.t0 = None
        self.done = 0

    def kill(self) -> None:
        try:
            os.killpg(self.proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            self.proc.kill()
        except Exception:
            pass
        self.proc.join(10)
        self.conn.close()

    def stop(self) -> None:
        try:
            self.conn.send(None)
        except Exception:
            pass
        self.proc.join(5)
        if self.proc.is_alive():
            self.kill()
        else:
            try:  # reap anything the worker left in its group
                os.killpg(self.proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass


def supervise(todo: list[dict], fn, workers: int, timeout_s: float, on_start, on_end, on_kill,
              maxtasks: int = 50) -> None:
    """Run plan entries on persistent worker processes with parent-enforced deadlines."""
    ctx = mp.get_context("spawn")
    queue = list(todo)
    pool: list[_Worker] = []
    try:
        while queue or any(w.item is not None for w in pool):
            # fill idle workers
            while queue and (len(pool) < max(1, workers) or any(w.item is None for w in pool)):
                w = next((w for w in pool if w.item is None), None)
                if w is None:
                    w = _Worker(ctx, fn)
                    pool.append(w)
                e = queue.pop(0)
                w.item, w.t0, w.deadline = e, time.time(), time.time() + timeout_s
                on_start(e)
                w.conn.send(e["payload"])
            busy = [w for w in pool if w.item is not None]
            if not busy:
                continue
            nearest = min(w.deadline for w in busy)
            ready = mp_wait([w.conn for w in busy] + [w.proc.sentinel for w in busy],
                            timeout=max(0.01, min(1.0, nearest - time.time())))
            for w in list(busy):
                e = w.item
                if w.conn in ready or w.conn.poll():
                    try:
                        status, out, secs, rss = w.conn.recv()
                    except (EOFError, OSError):
                        status, out, secs, rss = "worker_died", {"error": "worker exited without a result",
                                                                 "exitcode": w.proc.exitcode}, time.time() - w.t0, None
                        w.kill()
                        pool.remove(w)
                        on_end(e, status, out, secs, {"worker_peak_rss_bytes": rss})
                        continue
                    on_end(e, status, out, secs, {"worker_peak_rss_bytes": rss})
                    w.item = None
                    w.done += 1
                    if w.done >= maxtasks:
                        w.stop()
                        pool.remove(w)
                elif not w.proc.is_alive():
                    secs = time.time() - w.t0
                    w.kill()
                    pool.remove(w)
                    on_end(e, "worker_died", {"error": "worker process died", "exitcode": w.proc.exitcode}, secs, {})
                elif time.time() >= w.deadline:
                    on_kill(e, f"deadline {timeout_s}s exceeded")
                    w.kill()
                    pool.remove(w)
                    on_end(e, "timeout", {"error": f"wall-clock cap {timeout_s}s (process group killed)"},
                           time.time() - w.t0, {"killed_pid": w.proc.pid})
    finally:
        for w in pool:
            if w.item is not None:
                w.kill()
            else:
                w.stop()


__all__ = ["Run", "make_plan", "load_run", "read_jsonl", "read_attempts", "Ledger", "RunCorruption", "RunRefused",
           "source_tree_digest", "config_hash", "supervise", "atomic_write_json", "default_runs_root", "ROOT"]
