"""S1 — compression and exact query scaling.  One item = (world, backend).

Backends: reference (direct-rule exhaustive), literal (full successor table), index_enum,
index_cube, index_sat (hybrid: index families -> CNF -> SAT), bdd_ref (independent BDD
from direct rules), codecs (bit lengths of every codec on the same target object).
Each item runs in its own worker process (runner maxtasks=1) so peak RSS is per item.
Per-query wall-clock caps produce 'timeout' rows; they are never dropped or zeroed.
Cells outside a backend's declared feasibility limit are recorded 'excluded_by_design'.
"""
from __future__ import annotations

import signal
import time

from .. import query, reference
from ..codec import ALL_NODE_CODECS, decode_network, decoder_identity, encode_network, generic_bits
from ..generators import make_s1_world, s1_queries
from ..index_repr import MATERIALIZATION_LOG, from_network
from ..schema import ModelAnswer

DEFAULT_LIMITS = {"reference_max_n": 10, "literal_max_n": 16, "index_enum_max_n": 12, "full_codec_max_n": 16,
                  "cube_budget": 20000, "bdd_node_budget": 2_000_000, "proof_check_max_n": 256}


class QueryTimeout(Exception):
    pass


def _alarm(signum, frame):
    raise QueryTimeout()


def _with_timeout(fn, secs):
    signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, secs)
    t0 = time.perf_counter()
    try:
        out = fn()
        return out, time.perf_counter() - t0, None
    except QueryTimeout:
        return None, secs, "timeout"
    except MemoryError:
        return None, time.perf_counter() - t0, "oom"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def run_item(p: dict) -> dict:
    lim = {**DEFAULT_LIMITS, **p.get("limits", {})}
    world = make_s1_world(p["salt"], p["index"], p["family"], p["n"])
    net = world.net
    n = net.n
    backend = p["backend"]
    qs, tags = s1_queries(world)
    qto = p.get("query_timeout_s", 20)
    out = {"world_id": world.world_id, "family": world.family, "n": n, "backend": backend,
           "query_tags": tags, "limits": lim}
    MATERIALIZATION_LOG.clear()

    if backend == "codecs":
        rep, t_build, err = _with_timeout(lambda: from_network(net), p.get("construct_timeout_s", 600))
        out["t_index_construct"] = t_build
        if err:
            out["status"] = err
            return out
        out["index_family_count"] = rep.family_count()
        out["index_cover_exact"] = all(nd.exact_cover for nd in rep.nodes)
        bits = {}
        for cd in ALL_NODE_CODECS:
            if cd == "full" and n > lim["full_codec_max_n"]:
                bits[cd] = {"status": "excluded_by_design"}
                continue
            t0 = time.perf_counter()
            a = encode_network(net, cd, list(rep.nodes) if cd in ("index", "dnf") else None)
            t_enc = time.perf_counter() - t0
            t1 = time.perf_counter()
            back = decode_network(a.data)
            t_dec = time.perf_counter() - t1
            ok = back.canonical() == net.canonical()
            bits[cd] = {"status": "ok" if ok else "ROUNDTRIP_FAILURE", "archive_bits": a.total_bits,
                        "payload_bits": a.payload_bits, "header_bits": a.header_bits, "framing_bits": a.framing_bits,
                        "t_encode": t_enc, "t_decode": t_dec}
        for m in ("lzma", "gzip", "raw"):
            bits[f"generic_{m}"] = {"status": "ok", "archive_bits": generic_bits(net, m)}
        out["bits"] = bits
        out["decoder"] = decoder_identity()
        out["status"] = "ok"
        return out

    feasible = {"reference": n <= lim["reference_max_n"], "literal": n <= lim["literal_max_n"],
                "index_enum": n <= lim["index_enum_max_n"]}.get(backend, True)
    if not feasible:
        out["status"] = "excluded_by_design"
        return out

    # ---- representation construction (charged separately from queries)
    t0 = time.perf_counter()
    state = {}
    if backend in ("index_enum", "index_cube", "index_sat"):
        rep, t_c, err = _with_timeout(lambda: from_network(net), p.get("construct_timeout_s", 600))
        if err:
            out.update(status=f"construct_{err}", t_construct=t_c)
            return out
        state["rep"] = rep
        out["representation_backend"] = "index_families"
        out["query_backend"] = {"index_enum": "enumeration", "index_cube": "index_cube_algebra",
                                "index_sat": "sat_hybrid"}[backend]
    elif backend == "literal":
        succ, t_c, err = _with_timeout(lambda: query.literal_successors(net), p.get("construct_timeout_s", 600))
        if err:
            out.update(status=f"construct_{err}", t_construct=t_c)
            return out
        state["succ"] = succ
        out["representation_backend"] = "literal_repertoire"
        out["representation_bytes"] = int(succ.nbytes)
    elif backend == "bdd_ref":
        from ..bdd_ref import BDDModel
        m, t_c, err = _with_timeout(lambda: BDDModel(net, lim["bdd_node_budget"]), p.get("construct_timeout_s", 600))
        if err:
            out.update(status=f"construct_{err}", t_construct=t_c)
            return out
        state["bdd"] = m
        out["representation_backend"] = "bdd_from_direct_rules"
        out["bdd_nodes_after_build"] = m.size()
    elif backend == "reference":
        out["representation_backend"] = "direct_rules"
    out["t_construct"] = time.perf_counter() - t0

    rows = []
    for qi, q in enumerate(qs):
        if backend == "reference":
            fn = lambda q=q: reference.evaluate(net, q)  # noqa: E731
        elif backend == "literal":
            fn = lambda q=q: query.literal_query(state["succ"], net, q)  # noqa: E731
        elif backend == "index_enum":
            fn = lambda q=q: query.index_enum(state["rep"], net, q)  # noqa: E731
        elif backend == "index_cube":
            fn = lambda q=q: query.index_cube(state["rep"], net, q, budget=lim["cube_budget"])  # noqa: E731
        elif backend == "index_sat":
            fn = lambda q=q: query.index_sat(state["rep"], net, q, check_proof=n <= lim["proof_check_max_n"])  # noqa: E731
        elif backend == "bdd_ref":
            fn = lambda q=q: state["bdd"].answer(q)  # noqa: E731
        else:
            raise ValueError(backend)
        res, secs, err = _with_timeout(fn, qto)
        row = {"q": qi, "tag": tags[qi], "seconds": secs}
        if err:
            row.update(answer=err, level="none")
            if "bdd" in state:
                # an asynchronous interrupt can leave the dd manager inconsistent: never reuse it
                state["bdd"].close()
                from ..bdd_ref import BDDModel
                state["bdd"] = BDDModel(net, lim["bdd_node_budget"])
                row["manager_rebuilt_after_interrupt"] = True
        else:
            row.update(answer=res.answer.value, level=res.certificate.level.value)
            if res.certificate.witness_state is not None:
                # every witness is replayed by the independent reference here as well
                st = res.certificate.witness_state
                tr = reference.run(net, st, q.intervention, q.horizon)
                row["witness_replay_ok"] = reference.replay_witness(net, q, st, tr) and (
                    res.answer in (ModelAnswer.TRUE, ModelAnswer.FALSE))
            if "proof" in res.certificate.detail:
                row["proof"] = {k: v for k, v in res.certificate.detail["proof"].items() if k != "failed_lemma"}
            if backend == "index_sat":
                row["cnf_vars"] = res.certificate.detail.get("vars")
                row["cnf_clauses"] = res.certificate.detail.get("clauses")
        rows.append(row)
    if "bdd" in state:
        out["bdd_nodes_final"] = state["bdd"].size()
        state["bdd"].close()
    out["queries"] = rows
    out["materializations"] = list(MATERIALIZATION_LOG)
    out["status"] = "ok"
    return out
