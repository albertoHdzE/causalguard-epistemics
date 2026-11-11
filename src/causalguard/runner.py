"""Resumable experiment runner with a persisted item plan, immutable attempt records,
exclusive run ownership, a supervising scheduler and strict logs.

Iteration 2 introduced plans, attempts and supervisor deadlines (R03-R06).  Iteration 3 repairs
R2-01..R2-04: exclusive ownership, no-clobber publication, parent-death cleanup, run-level status
derived from storage, and one strict validator for plans and every attempt.

Owner of: run directories, the item plan, attempt records, the run event ledger,
the registry, source/config identity, ownership locks, resume rules, per-item deadlines and
failure records.  Every analysis reads run outputs through ``load_run``.

Layout of a v2 run directory ``<runs_root>/<run_id>/``::

    plan.json            immutable plan: config, config hash, source identity, every planned item
                         (id, payload, payload hash, strata) and the plan digest
    attempts/<key>/NNN.json   ONE file per finished attempt.  Published no-clobber (tmp + fsync + hard
                         link): an existing attempt file is never replaced.  status ok | error | timeout |
                         oom | worker_died.  A later attempt names the attempts it supersedes; failed
                         attempts are never deleted.
    events.jsonl         append-only ledger: open, resume, start, attempt_start, attempt_end, kill,
                         quarantine, end.
    quarantine/          exact bytes of a torn ledger tail or a stray temporary file, with digests.

and, outside the run directory, ``<runs_root>/.locks/<run_id>.owner.lock`` / ``.workers.lock``.

Rules
-----
* Ownership.  Before the run directory is inspected, recovered or created, the opener takes an
  exclusive, non-blocking ``flock`` on the owner lock.  A second active opener is refused
  (``RunBusy``) deterministically and touches nothing.  ``flock`` ownership belongs to the open file
  description and is released by the kernel when the owner exits or dies, so a stale lock never
  blocks recovery and no PID is trusted as an identity.  Ownership is released at the end of
  ``execute`` (or by ``close``).
* Worker groups.  Every worker runs in its own session/process group, holds a SHARED lock on the
  workers lock for its whole life and starts a watchdog process inside its group.  The watchdog
  blocks on a lifeline pipe whose only write end belongs to the supervisor; when the supervisor
  exits or is killed (including SIGKILL of its whole group) the kernel closes that end and the
  watchdog SIGKILLs the worker's entire process group (worker, watchdog and every descendant that
  stayed in the group).  A new owner must then obtain the workers lock EXCLUSIVELY (bounded wait,
  ``WORKER_DRAIN_S``) before it may recover or schedule anything, so a resume never overlaps old
  computation.  Descendants that deliberately leave the group (``setsid``) are out of scope.
* A run is opened either NEW (directory must not exist; it is created by an atomic directory
  rename, plan included) or with ``resume=True`` (the stored plan is strictly re-validated --
  digests recomputed -- and must be canonically identical to the requested plan).  Every attempt,
  including superseded failures, is validated against the plan BEFORE any recovery mutates storage.
* Readers are strict.  A malformed attempt file, an attempt whose run/plan/source/payload identity,
  schema, status, numbering or supersession disagrees with the plan, an invalid interior ledger
  line or two conflicting successful attempts are corruption: ``RunCorruption`` is raised (fail
  closed).  Only a torn FINAL ledger line and stray ``*.tmp*`` attempt files (an interrupted
  publication) are permitted recoveries; their exact bytes are quarantined with a ledger event.
* Per-item deadlines are enforced by the PARENT: when an item exceeds its deadline the parent
  SIGKILLs the worker's process group, reaps it, records a ``timeout`` attempt and starts a fresh
  worker.  Code inside an item (e.g. S1 per-query caps) may use SIGALRM freely; it cannot cancel the
  outer deadline.  S1 per-query timeouts are scientific outcomes inside an ``ok`` item.
* An item is terminal when its latest attempt is ok, or failed and no retry was requested.
  ``retry_failed=True`` (explicit, logged, development only) re-runs failed items under their original
  identity.  Successful items are never re-run.
* Status.  ``run_status`` derives the run-level state from the LATEST attempt of every planned
  item as stored on disk: ``complete`` (all ok), ``complete_with_failures`` (every item terminal,
  some failed) or ``incomplete``.  The ``end`` event also records this invocation's own counts
  separately.  This is EXECUTION status; each study's scientific completeness policy lives in its
  analysis module.
* The registry (``<runs_root>/registry.jsonl``) lives with runtime storage, never in a tracked
  file, and is shared by runs: its recovery and appends are serialized by an exclusive lock.
"""
from __future__ import annotations

import datetime as _dt
import fcntl
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
STATUSES = ("ok",) + FAILED
ATTEMPT_REQUIRED = ("schema", "run_id", "item_id", "attempt", "payload_sha256", "plan_sha256", "source_tree_sha256",
                    "status", "seconds", "finished", "supersedes", "output")
ATTEMPT_OPTIONAL = ("worker_peak_rss_bytes", "killed_pid")
WORKER_DRAIN_S = 30.0      # bound for a previous owner's worker groups to disappear before a resume proceeds
LOCK_DIR = ".locks"


class RunCorruption(RuntimeError):
    """Run storage is inconsistent; analysis and execution must stop."""


class RunRefused(RuntimeError):
    """A run cannot be opened/resumed under the requested identity."""


class RunBusy(RunRefused):
    """Another live process owns this run (or its old workers are still alive); nothing was touched."""


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


def publish_new_json(path: Path, obj) -> None:
    """No-clobber publication of an immutable record: write ``<name>.tmp<pid>``, fsync, then hard-link it to
    its final name (``link`` fails if the name exists, so an existing record is NEVER replaced), unlink the
    temporary and fsync the directory.  An existing destination raises ``RunCorruption`` and its bytes are
    left untouched."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    data = json.dumps(obj, sort_keys=True, default=_json_default).encode()
    with open(tmp, "xb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    try:
        os.link(tmp, path)
    except FileExistsError:
        os.unlink(tmp)
        raise RunCorruption(f"{path}: refusing to overwrite an existing attempt record") from None
    os.unlink(tmp)
    _fsync_dir(path.parent)


class FileLock:
    """``flock`` on a lock file.  The lock belongs to this open file description: the kernel releases it when
    the holder closes it, exits or dies (no stale locks, no PID identity)."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.fd: int | None = None

    def acquire(self, exclusive: bool = True, blocking: bool = False, timeout: float | None = None) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT, 0o644)
        op = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        t_end = None if timeout is None else time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, op | (0 if blocking and timeout is None else fcntl.LOCK_NB))
                self.fd = fd
                return True
            except BlockingIOError:
                if t_end is None or time.monotonic() >= t_end:
                    os.close(fd)
                    return False
                time.sleep(0.05)

    def describe(self, info: dict) -> None:
        """Diagnostic owner description written into the lock file (not used as an identity)."""
        if self.fd is not None:
            os.ftruncate(self.fd, 0)
            os.pwrite(self.fd, (json.dumps(info, sort_keys=True) + "\n").encode(), 0)

    def release(self) -> None:
        if self.fd is not None:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
            finally:
                os.close(self.fd)
                self.fd = None

    @property
    def held(self) -> bool:
        return self.fd is not None


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

    def __init__(self, path: Path, quarantine_dir: Path | None = None, shared: bool = False):
        """``shared=True`` for ledgers written by several runs/processes (registry, access ledger): recovery
        and appends are then serialized by an exclusive lock on ``<name>.lock``."""
        self.path = Path(path)
        self.qdir = quarantine_dir or self.path.parent / "quarantine"
        self.shared = shared

    def _lock(self):
        lk = FileLock(self.path.with_name(self.path.name + ".lock"))
        if self.shared:
            lk.acquire(exclusive=True, blocking=True)
        return lk

    def recover(self) -> dict | None:
        lk = self._lock()
        try:
            return self._recover()
        finally:
            lk.release()

    def recover_and_append(self, obj: dict) -> dict | None:
        """Atomic (under the shared lock) recovery of a torn tail followed by one append."""
        lk = self._lock()
        try:
            rec = self._recover()
            self._append(obj)
            return rec
        finally:
            lk.release()

    def _recover(self) -> dict | None:
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
        self._append(ev)
        return ev

    def append(self, obj: dict) -> None:
        lk = self._lock()
        try:
            self._append(obj)
        finally:
            lk.release()

    def _append(self, obj: dict) -> None:
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


def _is_hex64(x) -> bool:
    return isinstance(x, str) and len(x) == 64 and all(c in "0123456789abcdef" for c in x)


def validate_plan(plan: dict, run_id: str | None = None, where: str = "plan") -> dict:
    """STRICT plan validator (resume and read time).  Recomputes the plan digest, the config hash and every
    payload hash; checks schema, run id, unique item ids/keys.  Returns {item_id: plan entry}."""
    if not isinstance(plan, dict) or plan.get("schema") != PLAN_SCHEMA:
        raise RunCorruption(f"{where}: not a {PLAN_SCHEMA} plan")
    body = {k: v for k, v in plan.items() if k != "plan_sha256"}
    if config_hash(body) != plan.get("plan_sha256"):
        raise RunCorruption(f"{where}: plan digest mismatch (stored plan altered)")
    if run_id is not None and plan.get("run_id") != run_id:
        raise RunCorruption(f"{where}: plan run_id {plan.get('run_id')!r} differs from {run_id!r}")
    if config_hash(plan.get("config")) != plan.get("config_hash"):
        raise RunCorruption(f"{where}: config hash mismatch")
    if not _is_hex64(plan.get("source_tree_sha256")):
        raise RunCorruption(f"{where}: malformed source_tree_sha256")
    items = {}
    for e in plan.get("items", []):
        iid = e.get("item_id")
        if not isinstance(iid, str) or iid in items:
            raise RunCorruption(f"{where}: missing or duplicate item id {iid!r}")
        if config_hash(e.get("payload")) != e.get("payload_sha256"):
            raise RunCorruption(f"{where}: payload hash mismatch for {iid}")
        items[iid] = e
    if len({item_key(i) for i in items}) != len(items):  # pragma: no cover - sha256 prefix collision
        raise RunCorruption(f"{where}: item key collision")
    return items


def validate_attempt(rec, plan: dict, planned: dict, fname: str, dirname: str) -> dict:
    """STRICT attempt validator: schema, exact key set, identities (run, plan, source, payload, item/directory),
    status, numbering and types.  Applied to EVERY attempt, superseded failures included."""
    where = f"attempts/{dirname}/{fname}"
    if not isinstance(rec, dict) or rec.get("schema") != ATTEMPT_SCHEMA:
        raise RunCorruption(f"{where}: not a {ATTEMPT_SCHEMA} record")
    keys = set(rec)
    if missing := [k for k in ATTEMPT_REQUIRED if k not in keys]:
        raise RunCorruption(f"{where}: missing fields {missing}")
    if extra := sorted(keys - set(ATTEMPT_REQUIRED) - set(ATTEMPT_OPTIONAL)):
        raise RunCorruption(f"{where}: unexpected fields {extra}")
    n = rec["attempt"]
    if not isinstance(n, int) or isinstance(n, bool) or n < 1 or fname != f"{n:03d}.json":
        raise RunCorruption(f"{where}: schema/attempt-number mismatch")
    iid = rec["item_id"]
    if not isinstance(iid, str) or item_key(iid) != dirname:
        raise RunCorruption(f"{where}: item id does not match its directory")
    if iid not in planned:
        raise RunCorruption(f"{where}: attempt for an unplanned item {iid}")
    for k in ("run_id", "plan_sha256", "source_tree_sha256"):
        if rec[k] != plan[k]:
            raise RunCorruption(f"{where}: {k} {str(rec[k])[:16]!r} differs from the plan")
    if rec["payload_sha256"] != planned[iid]["payload_sha256"]:
        raise RunCorruption(f"{where}: attempt payload hash differs from the plan")
    if rec["status"] not in STATUSES:
        raise RunCorruption(f"{where}: invalid status {rec['status']!r}")
    if not isinstance(rec["output"], dict):
        raise RunCorruption(f"{where}: output is not an object")
    if not isinstance(rec["seconds"], (int, float)) or isinstance(rec["seconds"], bool) or rec["seconds"] < 0:
        raise RunCorruption(f"{where}: invalid seconds")
    rss = rec.get("worker_peak_rss_bytes")
    if rss is not None and (not isinstance(rss, int) or isinstance(rss, bool) or rss < 0):
        raise RunCorruption(f"{where}: invalid worker_peak_rss_bytes")
    if rec["supersedes"] != list(range(1, n)):
        raise RunCorruption(f"{where}: supersedes {rec['supersedes']} must list every earlier attempt 1..{n - 1}")
    return rec


def run_status(plan_items, atts: dict[str, list[dict]]) -> dict:
    """Run-level EXECUTION status from the latest stored attempt of every planned item."""
    ids = [e["item_id"] if isinstance(e, dict) else e for e in plan_items]
    ok = sum(1 for i in ids if atts.get(i) and atts[i][-1]["status"] == "ok")
    failed = sum(1 for i in ids if atts.get(i) and atts[i][-1]["status"] in FAILED)
    missing = len(ids) - ok - failed
    return {"planned": len(ids), "ok": ok, "failed": failed, "missing": missing,
            "status": "complete" if ok == len(ids) else "incomplete" if missing else "complete_with_failures"}


PHASES = ("development", "fixture", "confirmatory")


def run_phase(plan: dict, events: list[dict]) -> str:
    """Reporting phase from validated provenance.  Confirmatory/fixture plans carry ``phase`` (written by
    freeze.execute together with the freeze block); a plan without a freeze block is development.  Every
    ``start`` event's ``mode`` must agree; any disagreement or unknown value is refused (ambiguous phase)."""
    declared = plan.get("phase")
    if declared is None:
        if "freeze" in plan:
            raise RunCorruption(f"{plan.get('run_id')}: freeze block without a declared phase (ambiguous)")
        declared = "development"
    if declared not in PHASES or (declared == "development") == ("freeze" in plan):
        raise RunCorruption(f"{plan.get('run_id')}: inconsistent phase {declared!r} for its freeze provenance")
    modes = {e.get("mode") for e in events if e.get("event") == "start"}
    if modes - {declared}:
        raise RunCorruption(f"{plan.get('run_id')}: executions ran in modes {sorted(map(str, modes))} but the plan "
                            f"declares phase {declared!r}")
    return declared


def _lock_paths(root: Path, run_id: str) -> tuple[Path, Path]:
    d = Path(root) / LOCK_DIR
    return d / f"{run_id}.owner.lock", d / f"{run_id}.workers.lock"


class Run:
    """A v2 run.  ``Run(run_id, plan, resume=...)``; see module docstring.  Construction acquires exclusive
    ownership (``RunBusy`` if another live process owns the run); ``execute`` releases it when it returns."""

    def __init__(self, run_id: str, plan: dict, runs_root: Path | None = None, resume: bool = False,
                 registry: Path | None = None):
        self.run_id = run_id
        self.root = Path(runs_root) if runs_root else default_runs_root()
        self.dir = self.root / run_id
        self.registry = Ledger(Path(registry) if registry else self.root / "registry.jsonl", shared=True)
        self.resume = resume
        if plan.get("run_id") != run_id:
            raise RunRefused("plan run_id mismatch")
        self._items = validate_plan(plan, run_id, where="requested plan")
        self.plan = plan
        owner_path, self._workers_lock = _lock_paths(self.root, run_id)
        self._owner = FileLock(owner_path)
        self._open()

    # ---- ownership
    def _open(self) -> None:
        if not self._owner.acquire(exclusive=True, blocking=False):
            raise RunBusy(f"run {self.run_id}: another live process owns this run; refused without touching it")
        try:
            drain = FileLock(self._workers_lock)
            if not drain.acquire(exclusive=True, timeout=WORKER_DRAIN_S):
                raise RunBusy(f"run {self.run_id}: worker processes of a previous owner are still alive after "
                              f"{WORKER_DRAIN_S}s; refused")
            drain.release()
            self._owner.describe({"pid": os.getpid(), "host": platform.node(), "since": now(),
                                  "note": "diagnostic only; ownership is the kernel flock"})
            self._open_owned()
        except BaseException:
            self._owner.release()
            raise

    def _open_owned(self) -> None:
        run_id, plan = self.run_id, self.plan
        plan_path = self.dir / "plan.json"
        if self.resume:
            if not plan_path.exists():
                raise RunRefused(f"run {run_id}: --resume given but no plan exists at {plan_path}")
            try:
                old = json.loads(plan_path.read_bytes())
            except Exception as e:
                raise RunCorruption(f"{plan_path}: unreadable stored plan ({e})") from None
            validate_plan(old, run_id, where=str(plan_path))       # recomputed digests, not the stored string
            if canonical_json(old) != canonical_json(plan):
                diffs = [k for k in ("config_hash", "source_tree_sha256", "study") if old.get(k) != plan.get(k)]
                if len(old.get("items", [])) != len(plan["items"]):
                    diffs.append("item count")
                raise RunRefused(f"run {run_id}: resume refused, plan differs ({diffs or 'items/payloads'})")
            # validate every stored attempt BEFORE any recovery mutates storage (temporaries are permitted)
            read_attempts(self.dir, plan, allow_tmp=True)
        else:
            if self.dir.exists():
                raise RunRefused(f"run {run_id}: directory exists; pass resume=True (--resume) to continue it")
            self.root.mkdir(parents=True, exist_ok=True)
            stage = self.root / f".{run_id}.creating-{os.getpid()}-{time.monotonic_ns()}"
            stage.mkdir()
            (stage / "attempts").mkdir()
            atomic_write_json(stage / "plan.json", plan)
            try:
                os.rename(stage, self.dir)       # atomic; refuses an existing non-empty directory
            except OSError:
                raise RunRefused(f"run {run_id}: directory appeared concurrently; refused") from None
            _fsync_dir(self.root)
        self.ledger = Ledger(self.dir / "events.jsonl")
        (self.dir / "attempts").mkdir(exist_ok=True)
        rec = self.ledger.recover()
        self._quarantine_stray_tmp()
        self.ledger.append({"event": "resume" if self.resume else "open", "time": now(), "run_id": run_id,
                            "plan_sha256": plan["plan_sha256"], "git": git_state(), "pid": os.getpid(),
                            "env_hash": environment_info()["env_hash"], "recovered": rec})

    def close(self) -> None:
        """Release ownership (idempotent)."""
        self._owner.release()

    def __del__(self):
        try:
            self._owner.release()
        except Exception:
            pass

    def _quarantine_stray_tmp(self) -> None:
        for p in sorted((self.dir / "attempts").rglob("*.tmp*")):
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
        return read_attempts(self.dir, self.plan)

    def terminal(self, retry_failed: bool = False) -> dict[str, dict]:
        out = {}
        for iid, atts in self.attempts().items():
            last = atts[-1]
            if last["status"] == "ok" or not retry_failed:
                out[iid] = last
        return out

    def status(self) -> dict:
        return run_status(self.plan["items"], self.attempts())

    # ---- execution
    def execute(self, fn: Callable[[dict], dict], workers: int = 1, timeout_s: float = 600.0, quiet: bool = True,
                retry_failed: bool = False, maxtasks: int = 50, mode: str = "development",
                stop_after: int | None = None) -> dict:
        if not self._owner.held:      # a Run object may execute again after a previous execute released it
            self._open()
        try:
            return self._execute(fn, workers, timeout_s, quiet, retry_failed, maxtasks, mode, stop_after)
        finally:
            self._owner.release()

    def _execute(self, fn, workers, timeout_s, quiet, retry_failed, maxtasks, mode, stop_after) -> dict:
        if retry_failed and mode != "development":
            raise RunRefused("retry_failed is a development-only facility (no confirmatory retry policy is frozen)")
        if mode != self.plan.get("phase", "development"):
            raise RunRefused(f"execution mode {mode!r} differs from the plan phase {self.plan.get('phase', 'development')!r}")
        atts = self.attempts()
        done = {i for i, a in atts.items() if a[-1]["status"] == "ok" or (a[-1]["status"] in FAILED and not retry_failed)}
        todo = [e for e in self.plan["items"] if e["item_id"] not in done]
        if stop_after is not None:
            todo = todo[:stop_after]
        start = {"event": "start", "run_id": self.run_id, "mode": mode, "time": now(),
                 "plan_sha256": self.plan["plan_sha256"], "config_hash": self.plan["config_hash"],
                 "source_tree_sha256": self.plan["source_tree_sha256"], "git": git_state(),
                 "items_total": len(self.plan["items"]), "items_todo": len(todo), "retry_failed": retry_failed,
                 "run_dir": str(self.dir), "pid": os.getpid()}
        self.registry.recover_and_append(start)
        self.ledger.append(start)
        t0 = time.time()
        counts = {"attempted": 0, "ok": 0, "failed": 0}

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
            publish_new_json(self.dir / "attempts" / item_key(e["item_id"]) / f"{n:03d}.json", rec)
            atts.setdefault(e["item_id"], []).append(rec)
            self.ledger.append({"event": "attempt_end", "time": now(), "item_id": e["item_id"], "attempt": n,
                                "status": status, "seconds": round(secs, 3)})
            counts["attempted"] += 1
            counts["ok" if status == "ok" else "failed"] += 1
            if not quiet:
                print(f"[{self.run_id}] {e['item_id']} {status} {secs:.1f}s", flush=True)

        def on_kill(e, why):
            self.ledger.append({"event": "kill", "time": now(), "item_id": e["item_id"], "reason": why})

        supervise(todo, fn, workers, timeout_s, on_start, on_end, on_kill, maxtasks, workers_lock=self._workers_lock)
        st = self.status()          # strict re-read of every latest attempt from storage
        end = {"event": "end", "run_id": self.run_id, "time": now(), "mode": mode,
               "status": st["status"], "planned": st["planned"], "ok": st["ok"], "failed": st["failed"],
               "missing": st["missing"], "items_without_terminal_attempt": st["missing"],
               "invocation": counts, "status_scope": "execution (latest stored attempt per planned item)",
               "wall_s": round(time.time() - t0, 1)}
        self.ledger.append(end)
        self.registry.append(end)
        return end


# --------------------------------------------------------------------------- reading runs (analysis side)

def read_attempts(run_dir: Path, plan: dict | None = None, allow_tmp: bool = False) -> dict[str, list[dict]]:
    """All attempt records of a v2 run, each strictly validated against the (validated) plan, ordered by
    attempt number.  ``plan=None`` reads and validates ``plan.json``.  ``allow_tmp`` skips (does not accept)
    temporary files; only the owning runner uses it, immediately before quarantining them."""
    run_dir = Path(run_dir)
    if plan is None:
        try:
            plan = json.loads((run_dir / "plan.json").read_bytes())
        except Exception as e:
            raise RunCorruption(f"{run_dir}: unreadable plan ({e})") from None
    planned = validate_plan(plan, None, where=str(run_dir / "plan.json"))
    out: dict[str, list[dict]] = {}
    adir = run_dir / "attempts"
    if not adir.exists():
        return out
    for d in sorted(adir.iterdir()):
        if not d.is_dir():
            raise RunCorruption(f"unexpected file {d}")
        for f in sorted(d.iterdir()):
            if ".tmp" in f.name:
                if allow_tmp:
                    continue
                raise RunCorruption(f"unquarantined temporary file {f} (open the run to quarantine it)")
            try:
                rec = json.loads(f.read_bytes())
            except Exception as e:
                raise RunCorruption(f"{f}: unreadable attempt record ({e})") from None
            rec = validate_attempt(rec, plan, planned, f.name, d.name)
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
     attempt_meta: {item_id: envelope fields of the latest attempt (no output)}, execution_status, phase,
     attempts_total, layout}.  v1 (legacy) directories are read strictly from records/failures.jsonl."""
    run_dir = Path(run_dir)
    if (run_dir / "plan.json").exists():
        try:
            plan = json.loads((run_dir / "plan.json").read_bytes())
        except Exception as e:
            raise RunCorruption(f"{run_dir}: unreadable plan ({e})") from None
        planned = validate_plan(plan, None, where=str(run_dir / "plan.json"))
        events = Ledger(run_dir / "events.jsonl").read()  # strict: torn tails must have been recovered by the runner
        atts = read_attempts(run_dir, plan)
        results, failures, missing, meta = {}, {}, [], {}
        for iid in planned:
            a = atts.get(iid)
            if not a:
                missing.append(iid)
                continue
            meta[iid] = {k: v for k, v in a[-1].items() if k != "output"}
            if a[-1]["status"] == "ok":
                results[iid] = a[-1]["output"]
            else:
                failures[iid] = a[-1]
        return {"layout": "v2", "plan": plan, "results": results, "failures": failures, "missing": missing,
                "attempt_meta": meta, "execution_status": run_status(list(planned), atts),
                "phase": run_phase(plan, events),
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

_WATCHDOG = (
    "import os, signal\n"
    "fd = int(os.environ['CAUSALGUARD_LIFELINE_FD'])\n"
    "while True:\n"
    "    try:\n"
    "        b = os.read(fd, 1)\n"
    "    except InterruptedError:\n"
    "        continue\n"
    "    except OSError:\n"
    "        b = b''\n"
    "    if not b:\n"
    "        break\n"
    "os.killpg(os.getpgid(0), signal.SIGKILL)\n"
)


def _worker_main(conn, fn, lifeline=None, workers_lock: str | None = None) -> None:
    os.setsid()  # own session/process group: the parent (and the watchdog) can kill everything this worker starts
    if workers_lock:
        # SHARED hold for the life of this group: a new owner cannot proceed until every old worker is gone
        FileLock(Path(workers_lock)).acquire(exclusive=False, blocking=True)
    if lifeline is not None:
        # The watchdog lives in THIS process group and blocks on the lifeline; the supervisor holds the only write
        # end.  Supervisor exit/death (even SIGKILL of its whole group) => EOF => SIGKILL of this whole group.
        fd = lifeline.fileno()
        subprocess.Popen([sys.executable, "-I", "-S", "-c", _WATCHDOG], pass_fds=(fd,),
                         env={"CAUSALGUARD_LIFELINE_FD": str(fd)}, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
    def __init__(self, ctx, fn, workers_lock: Path | None = None):
        self.conn, child = ctx.Pipe()
        life_r, self.lifeline = ctx.Pipe(duplex=False)      # supervisor keeps the only write end
        self.proc = ctx.Process(target=_worker_main, args=(child, fn, life_r, str(workers_lock) if workers_lock else None),
                                daemon=True)
        self.proc.start()
        child.close()
        life_r.close()
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
        self.lifeline.close()

    def stop(self) -> None:
        try:
            self.conn.send(None)
        except Exception:
            pass
        self.proc.join(5)
        if self.proc.is_alive():
            self.kill()
        else:
            try:  # reap anything the worker left in its group (watchdog, descendants)
                os.killpg(self.proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            self.lifeline.close()


def supervise(todo: list[dict], fn, workers: int, timeout_s: float, on_start, on_end, on_kill,
              maxtasks: int = 50, workers_lock: Path | None = None) -> None:
    """Run plan entries on persistent worker processes with parent-enforced deadlines.  Each worker group
    carries a parent-death watchdog and (when given) a shared hold on ``workers_lock``."""
    ctx = mp.get_context("spawn")
    queue = list(todo)
    pool: list[_Worker] = []
    try:
        while queue or any(w.item is not None for w in pool):
            # fill idle workers
            while queue and (len(pool) < max(1, workers) or any(w.item is None for w in pool)):
                w = next((w for w in pool if w.item is None), None)
                if w is None:
                    w = _Worker(ctx, fn, workers_lock)
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


__all__ = ["Run", "make_plan", "load_run", "read_jsonl", "read_attempts", "validate_plan", "validate_attempt",
           "run_status", "run_phase", "PHASES", "Ledger", "FileLock", "RunCorruption", "RunRefused", "RunBusy", "source_tree_digest",
           "config_hash", "supervise", "atomic_write_json", "publish_new_json", "default_runs_root", "ROOT"]
