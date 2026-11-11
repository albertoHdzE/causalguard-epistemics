"""Track C runner item: matched requests across backends, censored cost curves, workspace vs full checked release.

Instance (n, base index): k = 3; base 0-3 'matched' = an ordered cyclic template (the CGH-matched structure),
base 4-7 'rewired' = the degree-preserving rewiring of matched base (i - 4) (pair = one cluster).  Evidence: 16
one-step full-state observations (uniform distinct states).  Queries: 16 (h in {1, 2}, initial_edit on one node,
literal value 1, start state never observed); the first 4 are the scheduled queries, reuse is measured at 1/4/16.

Each item = (instance, backend, repetition).  Two phases run in a CHILD process with a hard wall limit (300 s
each); per-query completion times stream back, so budgets 1/10/60/300 s are read from one execution (censored at
the limit; the child and its descendants are killed at the limit).  Peak RSS of each phase is the child's maxrss.
  workspace   build + 16 queries: counts (D, GEN-VE, B where n <= 10) or SAT verdict (B)
  release     the 4 scheduled queries through s4.checking.check (common SAT cross-check of every impossible side,
              witness replay) + commit; proof_check on (RUP) -- actual certificate levels are recorded per query.
              Backends with a release path: D, B.  GEN-VE has no workspace adapter (no witnesses): workspace only.
"""
from __future__ import annotations

import multiprocessing as mp
import random
import resource
import time

from .. import reference
from ..s4.hcode import offset_rule
from ..schema import Evidence, Intervention, Network, Observation, Pred, Query
from .data import _nondeg, rewire

K = 3
B_OBS = 16
N_Q = 16
SCHEDULED = 4
LIMIT_S = 300.0
CHECKPOINTS = (1, 10, 60, 300)
SIZES = (8, 16, 32, 48, 64)
BACKENDS = ("D", "GEN-VE", "B")
REPEAT_SUBSET = [(8, 0), (8, 4), (32, 0), (32, 4)]     # (n, base) timed 3x (preregistered)


def instance(n: int, base: int, salt: str = "r5-C-v1") -> tuple[Network, Evidence, list[Query], dict]:
    rng = random.Random(f"{salt}|{n}|{base % 4}")
    d = 3
    offs = tuple(sorted(rng.sample(range(n), d)))
    t = _nondeg(rng, d, 0.0)
    net = Network(n, tuple(offset_rule(i, offs, t, n) for i in range(n)))
    kind = "matched"
    if base >= 4:
        net = rewire(net, random.Random(f"{salt}|rewire|{n}|{base}"))
        kind = "rewired"
    drng = random.Random(f"{salt}|design|{n}|{base}")
    states = set()
    while len(states) < B_OBS:
        states.add(drng.randrange(1 << n))
    obs = []
    for x in sorted(states):
        y = reference.run(net, x, Intervention("none"), 1)[-1]
        obs.append(Observation(x, Intervention("none"), 1, tuple((j, (y >> j) & 1) for j in range(n))))
    ev = Evidence(n, tuple(obs))
    qs = []
    while len(qs) < N_Q:
        x = drng.randrange(1 << n)
        node = drng.randrange(n)
        iv = Intervention("initial_edit", ((node, drng.randint(0, 1)),))
        m, v = iv.masks
        if x in states or ((x & ~m) | v) in states:
            continue
        qs.append(Query.point(x, n, iv, drng.choice([1, 2]), Pred.lit(drng.randrange(n), 1)))
    return net, ev, qs, {"n": n, "base": base, "kind": kind, "cluster": f"n{n}-pair{base % 4}"}


def _pub(ev: Evidence, qs, n):
    return {"n": n, "k": K, "node_labels": [f"x{i}" for i in range(n)], "evidence": ev.to_json(),
            "claims": [{"cid": f"c{i}", "query": q.to_json()} for i, q in enumerate(qs)]}


def _workspace_phase(conn, n, base, backend):
    try:
        _, ev, qs, _ = instance(n, base)
        t0 = time.perf_counter()
        if backend == "GEN-VE":
            from .counting import VECounter
            ws = VECounter(ev, K)
            conn.send(("build", time.perf_counter() - t0, None))
            for i, q in enumerate(qs):
                num, den = ws.count(q)
                conn.send(("q", time.perf_counter() - t0, {"i": i, "num": str(num), "den": str(den)}))
        else:
            from ..s4.workspace import Limits, make_workspace
            pub = _pub(ev, qs, n)
            ws = make_workspace(backend, pub, Limits(explicit_max_n=10))
            conn.send(("build", time.perf_counter() - t0, None))
            for i, c in enumerate(pub["claims"]):
                r = ws.check(c)
                conn.send(("q", time.perf_counter() - t0, {"i": i, "verdict": r["verdict"],
                                                          "num": (r["counts"] or {}).get("num"),
                                                          "den": (r["counts"] or {}).get("den"),
                                                          "cert": (r.get("certificate") or {}).get("level")}))
        conn.send(("done", time.perf_counter() - t0, None))
    except Exception as e:  # recorded, never hidden
        conn.send(("error", 0.0, f"{type(e).__name__}: {e}"[:300]))
    conn.send(("rss", 0.0, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))


def _release_phase(conn, n, base, backend):
    try:
        from ..s4.checking import check, commit, validate_proposal
        from ..s4.workspace import Limits, make_workspace
        _, ev, qs, _ = instance(n, base)
        pub = _pub(ev, qs[:SCHEDULED], n)
        t0 = time.perf_counter()
        ws = make_workspace(backend, pub, Limits(explicit_max_n=10, proof_check=True))
        conn.send(("build", time.perf_counter() - t0, None))
        cby = {c["cid"]: c for c in pub["claims"]}
        for i, c in enumerate(pub["claims"]):
            r = ws.check(c)
            v = r["verdict"]
            asserted = v if v in ("entailed", "refuted", "underdetermined") else None
            info = {"i": i, "verdict": v}
            if asserted:
                d = check(validate_proposal({"cid": c["cid"], "asserted": asserted}, cby), ws)
                info["status"] = d.proposal_check_status
                info["side_checks"] = {k: x for k, x in d.certificate.items() if k.startswith("side")}
                if d.proposal_check_status == "verified" and asserted != "underdetermined":
                    commit(validate_proposal({"cid": c["cid"], "asserted": asserted}, cby), d, ws)
                    info["committed"] = True
            conn.send(("q", time.perf_counter() - t0, info))
        conn.send(("done", time.perf_counter() - t0, None))
    except Exception as e:
        conn.send(("error", 0.0, f"{type(e).__name__}: {e}"[:300]))
    conn.send(("rss", 0.0, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))


def _run_phase(target, n, base, backend, limit=LIMIT_S) -> dict:
    ctx = mp.get_context("spawn")
    a, b = ctx.Pipe(duplex=False)
    p = ctx.Process(target=target, args=(b, n, base, backend), daemon=True)
    t0 = time.perf_counter()
    p.start()
    b.close()
    events = []
    status = "timeout"
    rss = None
    while True:
        left = limit + 5.0 - (time.perf_counter() - t0)       # +5 s spawn/import allowance
        if left <= 0 or not a.poll(left):
            break
        try:
            kind, t, info = a.recv()
        except EOFError:
            status = "crashed"
            break
        if kind == "rss":
            rss = info
            status = status if status != "timeout" else "done"
            break
        if kind == "error":
            status = "error"
            events.append({"t": t, "error": info})
            continue
        if kind == "done":
            status = "done"
        events.append({"kind": kind, "t": t, **({"info": info} if info is not None else {})})
    if p.is_alive():
        p.kill()                                               # the child has no descendants of its own
    p.join(5)
    qtimes = [e["t"] for e in events if e.get("kind") == "q"]
    build = next((e["t"] for e in events if e.get("kind") == "build"), None)
    ok_time = [e["t"] for e in events if e.get("kind") == "done"]
    if status == "done" and qtimes and qtimes[-1] > limit:
        status = "over_limit"
    return {"status": status, "build_s": build, "query_done_s": qtimes, "done_s": ok_time[0] if ok_time else None,
            "events": [e for e in events if e.get("kind") in ("q", None) or "error" in e],
            "peak_rss_bytes": rss, "checkpoints": {str(c): sum(1 for x in qtimes if x <= c) for c in CHECKPOINTS}}


def c_item(p: dict) -> dict:
    n, base, backend = p["n"], p["base"], p["backend"]
    _, ev, qs, meta = instance(n, base)
    out = {**meta, "backend": backend, "rep": p.get("rep", 0), "evidence_hash": ev.digest(),
           "query_hashes": [q.digest() for q in qs]}
    out["workspace"] = _run_phase(_workspace_phase, n, base, backend, p.get("limit_s", LIMIT_S))
    qd = out["workspace"]["query_done_s"]
    out["reuse_s"] = {str(m): (qd[m - 1] if len(qd) >= m else None) for m in (1, 4, 16)}
    if backend in ("D", "B"):
        out["release"] = _run_phase(_release_phase, n, base, backend, p.get("limit_s", LIMIT_S))
    return out
