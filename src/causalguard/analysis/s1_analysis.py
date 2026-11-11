"""Offline S1 analysis (engineering / formal-correctness study; not causal identification).

Reads raw records only.  Correctness: every truth-valued answer is compared with the
exhaustive reference where it ran (n <= 10) and with every other truth-valued backend
answer for the same (world, query).  Timeouts / unknown_resource are kept in completion
curves and never replaced by a time or a truth value.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from ..runner import ROOT, read_jsonl

TRUTH = ("true", "false")
S1_QUERIES_PER_WORLD = 24


class S1OutputDefect(SystemExit):
    pass


def validate_s1_output(item_id: str, payload: dict, out: dict, world_ids: dict) -> dict:
    """Reconcile one ok S1 item output with its plan (iteration 3, R2-05 analogue).  Identity defects and
    duplicated/unplanned query rows refuse; ABSENT query rows are counted as missing outcomes (never dropped
    from denominators).  Returns {"missing_queries": int, "missing_codecs": [..]}."""
    from ..codec import ALL_NODE_CODECS
    w = item_id
    for k in ("family", "n", "backend"):
        if out.get(k) != payload[k]:
            raise S1OutputDefect(f"{w}: output {k}={out.get(k)!r} differs from the plan ({payload[k]!r})")
    key = (payload["family"], payload["n"], payload["index"])
    if world_ids.setdefault(key, out.get("world_id")) != out.get("world_id"):
        raise S1OutputDefect(f"{w}: world_id differs from the same planned world under another backend")
    tags = out.get("query_tags")
    if not isinstance(tags, list) or len(tags) != S1_QUERIES_PER_WORLD:
        raise S1OutputDefect(f"{w}: query grid has {len(tags) if isinstance(tags, list) else tags!r} tags, "
                             f"expected {S1_QUERIES_PER_WORLD}")
    res = {"missing_queries": 0, "missing_codecs": []}
    if out.get("status") == "ok" and payload["backend"] != "codecs":
        qs = out.get("queries")
        if not isinstance(qs, list):
            raise S1OutputDefect(f"{w}: ok item without a query list")
        ids = [q.get("q") for q in qs]
        if len(set(ids)) != len(ids) or any(not isinstance(i, int) or not 0 <= i < len(tags) for i in ids):
            raise S1OutputDefect(f"{w}: duplicated or unplanned query ids")
        if any(q.get("tag") != tags[q["q"]] for q in qs):
            raise S1OutputDefect(f"{w}: query tag differs from the planned grid")
        res["missing_queries"] = len(tags) - len(ids)
    if out.get("status") == "ok" and payload["backend"] == "codecs":
        bits = out.get("bits", {})
        res["missing_codecs"] = [c for c in ALL_NODE_CODECS if c not in bits]
    return res


def analyze(run_ids: list[str], out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # later runs override earlier ones for the same (world, backend): reruns replace, never merge
    by_item: dict = {}
    fails, failures_by_run, source = [], {}, Counter()
    for rid in run_ids:
        for r in read_jsonl(ROOT / "runs" / rid / "records.jsonl"):
            by_item[(r["world_id"], r["backend"])] = r
        fl = read_jsonl(ROOT / "runs" / rid / "failures.jsonl")
        failures_by_run[rid] = [{"item_id": f["item_id"], "status": f.get("status"), "error": str(f.get("error"))[:300]}
                                for f in fl]
        fails += fl
    recs = list(by_item.values())
    for r in recs:
        source[f"{r['backend']}<-{r['run_id']}"] += 1
    if not recs:
        raise SystemExit("no records")
    res: dict = {"run_ids": run_ids, "n_records": len(recs), "record_sources": dict(source),
                 "failures_by_run": failures_by_run}
    return _core(recs, res, out_dir, "s1_summary.json", planned=None)


def analyze_v2(run_dirs: list[Path], out_dir: Path) -> dict:
    """Iteration-2 S1 analysis: runs reconciled to their plans.  Failed and never-returned items stay in the
    completion denominators (24 queries each, as 'item_failure:<status>' / 'item_missing'); archive sums and
    payload sums are reported separately; the decoder charge is the complete dependency bundle."""
    from ..runner import load_run
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if len({str(Path(d).resolve()) for d in run_dirs}) != len(run_dirs):
        raise SystemExit("duplicate run arguments")
    recs, planned, acct = [], [], {}
    seen = set()
    world_ids: dict = {}
    phases = set()
    missing_q = Counter()
    missing_codecs = Counter()
    for d in run_dirs:
        lr = load_run(Path(d))
        if lr["layout"] != "v2":
            raise SystemExit(f"{d}: legacy layout; use analyze")
        plan = lr["plan"]
        phases.add(lr["phase"])
        rid = plan["run_id"]
        acct[rid] = {"planned": len(plan["items"]), "ok": len(lr["results"]), "failed": len(lr["failures"]),
                     "missing": len(lr["missing"]), "attempts_total": lr["attempts_total"],
                     "failures": {k: {"status": v["status"], "error": str(v["output"].get("error"))[:300]}
                                  for k, v in lr["failures"].items()},
                     "plan_sha256": plan["plan_sha256"], "source_tree_sha256": plan["source_tree_sha256"]}
        for e in plan["items"]:
            key = (e["payload"]["family"], e["payload"]["n"], e["payload"]["index"], e["payload"]["backend"])
            if key in seen:
                raise SystemExit(f"item {key} planned in more than one run (ambiguous combination)")
            seen.add(key)
            st = e["strata"]
            if e["item_id"] in lr["results"]:
                out = lr["results"][e["item_id"]]
                v = validate_s1_output(e["item_id"], e["payload"], out, world_ids)
                if v["missing_queries"]:
                    missing_q[f"{st['backend']}|n{st['n']}"] += v["missing_queries"]
                for c in v["missing_codecs"]:
                    missing_codecs[f"{c}|{st['family']}|n{st['n']}"] += 1
                rss = lr["attempt_meta"][e["item_id"]].get("worker_peak_rss_bytes")
                recs.append({"item_id": e["item_id"], "run_id": rid, **out, "_worker_peak_rss_bytes": rss,
                             "_missing_queries": v["missing_queries"]})
            else:
                f = lr["failures"].get(e["item_id"])
                planned.append({"backend": st["backend"], "n": st["n"], "family": st["family"],
                                "status": f"item_failure:{f['status']}" if f else "item_missing"})
    if len(phases) != 1:
        raise SystemExit(f"runs of different phases cannot be analysed together: {sorted(phases)}")
    phase = phases.pop()
    res = {"analysis_version": "s1-analysis-v3", "phase": phase, "run_dirs": [str(d) for d in run_dirs],
           "runs": acct, "n_records": len(recs), "semantics_changed_from_v1": [
               "failed/missing planned items counted in completion denominators",
               "amortized totals: archive_sum (sum of archive bits) and payload_sum reported separately",
               "decoder charge = gzip-9 of the complete local dependency bundle (codec+index_repr+schema)"],
           "changes_in_v3": [
               "peak RSS read from the validated attempt envelope (R2-06); missing measurements are null, never 0",
               "every ok item reconciled with its planned family/n/backend, shared world id and 24-query grid; "
               "absent query rows counted as 'query_missing' in completion denominators",
               "phase derived from validated run provenance"],
           "query_grid_reconciliation": {"queries_per_world": S1_QUERIES_PER_WORLD,
                                         "ok_items_missing_query_rows": dict(missing_q),
                                         "codec_items_missing_codecs": dict(missing_codecs),
                                         "status": "complete" if not missing_q and not missing_codecs and not planned
                                         else "incomplete"}}
    return _core(recs, res, out_dir, "s1_v2_summary.json", planned=planned)


def _core(recs: list[dict], res: dict, out_dir: Path, summary_name: str, planned: list[dict] | None) -> dict:
    worlds = {(r["family"], r["n"], r["world_id"]) for r in recs}
    res["independent_worlds"] = len(worlds)
    res["worlds_by_cell"] = {f"{f}|n{n}": c for (f, n), c in sorted(Counter((f, n) for f, n, _ in worlds).items())}

    # ------------- correctness
    answers = defaultdict(dict)   # (world, q) -> backend -> answer
    levels = Counter()
    replay_fail = 0
    excluded_post_interrupt = [0]
    proof_checked = proof_failed = 0
    tags = {}
    for r in recs:
        if r.get("status") != "ok" or "queries" not in r:
            continue
        interrupted = False
        for q in r["queries"]:
            if (r["backend"] == "bdd_ref" and interrupted and not any(x.get("manager_rebuilt_after_interrupt")
                                                                      for x in r["queries"])):
                # legacy records (before the rebuild fix): BDD answers after an in-item timeout may come
                # from a corrupted dd manager; excluded from correctness comparisons and counted
                excluded_post_interrupt[0] += 1
                continue
            if r["backend"] == "bdd_ref" and q["answer"] == "timeout":
                interrupted = True
            answers[(r["world_id"], q["q"])][r["backend"]] = q["answer"]
            tags[(r["world_id"], q["q"])] = (q["tag"], r["family"], r["n"])
            levels[(r["backend"], q["level"])] += 1
            if q.get("witness_replay_ok") is False:
                replay_fail += 1
            if "proof" in q:
                if q["level"] == "checked_proof":
                    proof_checked += 1
                else:
                    proof_failed += 1
    mismatch_ref = Counter()
    compared_ref = Counter()
    disagreements = []
    for key, by in answers.items():
        vals = {b: a for b, a in by.items() if a in TRUTH}
        if "reference" in vals:
            for b, a in vals.items():
                if b == "reference":
                    continue
                compared_ref[b] += 1
                if a != vals["reference"]:
                    mismatch_ref[b] += 1
                    disagreements.append({"world_q": key, "answers": by})
        elif len(set(vals.values())) > 1:
            disagreements.append({"world_q": key, "answers": by})
    res["correctness"] = {
        "compared_with_exhaustive_reference": dict(compared_ref), "mismatches_vs_reference": dict(mismatch_ref),
        "cross_backend_disagreements_total": len(disagreements), "disagreement_examples": disagreements[:10],
        "witness_replay_failures": replay_fail,
        "bdd_answers_excluded_post_interrupt_legacy": excluded_post_interrupt[0], "unsat_proofs_checked_ok": proof_checked,
        "unsat_proofs_not_certified": proof_failed}
    # UNSAT-type answers at n > 10: how were they validated?
    unsat_val = Counter()
    for key, by in answers.items():
        tag, fam, n = tags[key]
        if n <= 10:
            continue
        sat_ans = by.get("index_sat")
        if sat_ans not in TRUTH:
            continue
        # index_sat answer is "unsat-type" if no witness exists (exists-false / forall-true)
        is_forall = tag.startswith("forall") or "forall" in tag
        unsat_type = (sat_ans == "true") if is_forall else (sat_ans == "false")
        if not unsat_type:
            continue
        others = {b: a for b, a in by.items() if b != "index_sat" and a in TRUTH}
        unsat_val["total"] += 1
        if others:
            unsat_val["independently_confirmed_by_" + "+".join(sorted(others))] += 1
            if any(a != sat_ans for a in others.values()):
                unsat_val["CONTRADICTED"] += 1
        else:
            unsat_val["no_independent_exact_method_completed"] += 1
    res["large_n_unsat_type_validation"] = dict(unsat_val)
    res["certificate_levels"] = {f"{b}|{lv}": c for (b, lv), c in sorted(levels.items())}

    # ------------- balance of outcomes by construction tag (from the most authoritative available answer)
    bal = defaultdict(Counter)
    for key, by in answers.items():
        tag = tags[key][0]
        a = by.get("reference") or next((by[b] for b in ("index_sat", "bdd_ref", "literal") if by.get(b) in TRUTH), None)
        bal[tag.rsplit("_h", 1)[0]][a if a in TRUTH else "unresolved"] += 1
    res["outcome_balance_by_construction"] = {k: dict(v) for k, v in sorted(bal.items())}

    # ------------- completion & latency per backend x n (all families pooled, then by family)
    comp = {}
    lat = {}
    for r in recs:
        b, n = r["backend"], r["n"]
        if b == "codecs":
            continue
        key = f"{b}|n{n}"
        c = comp.setdefault(key, Counter())
        if r.get("status") == "excluded_by_design":
            c["excluded_by_design"] += 24
            continue
        if r.get("status") != "ok":
            c[r.get("status", "item_failure")] += 24
            continue
        for q in r["queries"]:
            st = "completed" if q["answer"] in TRUTH or q["answer"] == "invalid_domain" else q["answer"]
            c[st] += 1
            if st == "completed":
                lat.setdefault(key, []).append(q["seconds"])
        if r.get("_missing_queries"):
            c["query_missing"] += r["_missing_queries"]
    for e in planned or []:
        if e["backend"] != "codecs":
            comp.setdefault(f"{e['backend']}|n{e['n']}", Counter())[e["status"]] += 24
    res["completion"] = {k: dict(v) for k, v in sorted(comp.items(), key=lambda kv: (kv[0].split("|")[0], int(kv[0].split("|n")[1])))}
    res["latency_completed_queries"] = {k: {"n": len(v), "median_s": float(np.median(v)), "p90_s": float(np.quantile(v, 0.9)),
                                            "max_s": float(np.max(v))} for k, v in sorted(lat.items())}
    cons = defaultdict(list)
    rss = defaultdict(list)
    for r in recs:
        if r.get("status") == "ok" and "t_construct" in r:
            cons[f"{r['backend']}|n{r['n']}"].append(r["t_construct"])
        if r.get("status") == "ok":
            if planned is None:   # legacy v1 records carry the field themselves (field kept for byte reproduction)
                rss[f"{r['backend']}|n{r['n']}"].append(r.get("worker_peak_rss_bytes", 0))
            else:                 # v2+: validated attempt envelope; None = not measured (never a zero)
                rss[f"{r['backend']}|n{r['n']}"].append(r.get("_worker_peak_rss_bytes"))
    res["construction_seconds_median"] = {k: float(np.median(v)) for k, v in sorted(cons.items())}
    if planned is None:
        res["peak_rss_mib_median"] = {k: float(np.median(v)) / 2**20 for k, v in sorted(rss.items())}
    else:
        res["peak_rss_mib_median"] = {k: (float(np.median([x for x in v if x is not None])) / 2**20
                                          if any(x is not None for x in v) else None) for k, v in sorted(rss.items())}
        res["peak_rss_coverage"] = {k: {"measured": sum(x is not None for x in v), "ok_items": len(v)}
                                    for k, v in sorted(rss.items())}
        res["peak_rss_note"] = ("median over ok items of the worker's ru_maxrss (bytes on macOS; KiB x 1024 on Linux), "
                                "reported in MiB = 2^20 bytes; one fresh worker per item (maxtasks=1), so the value "
                                "includes the interpreter and imported-module baseline; null = no measurement")

    # ------------- bits (identical target object per world)
    bits = defaultdict(lambda: defaultdict(list))
    payload = defaultdict(lambda: defaultdict(list))
    bundle = None
    rt_fail = 0
    exact_cover = Counter()
    decoder = None
    for r in recs:
        if r["backend"] != "codecs" or r.get("status") != "ok":
            continue
        decoder = r.get("decoder")
        bundle = r.get("decoder_bundle", bundle)
        exact_cover[r["index_cover_exact"]] += 1
        for cd, v in r["bits"].items():
            if v.get("status") == "ROUNDTRIP_FAILURE":
                rt_fail += 1
            if v.get("status") == "ok":
                bits[(r["family"], r["n"])][cd].append(v["archive_bits"])
                if "payload_bits" in v:
                    payload[(r["family"], r["n"])][cd].append(v["payload_bits"])
    res["codec_roundtrip_failures"] = rt_fail
    res["index_cover_exact_worlds"] = {str(k): v for k, v in exact_cover.items()}
    res["decoder"] = decoder
    table = {}
    for (fam, n), d in sorted(bits.items()):
        row = {cd: float(np.median(v)) for cd, v in d.items()}
        row["worlds"] = len(d["index"])
        best = min((cd for cd in row if cd not in ("worlds",) and not cd.startswith("generic_raw")), key=lambda c: row[c])
        row["best_codec"] = best
        row["index_rank_among_codecs"] = 1 + sum(1 for cd in row if cd not in ("worlds", "best_codec", "generic_raw")
                                                 and isinstance(row[cd], float) and row[cd] < row["index"])
        table[f"{fam}|n{n}"] = row
    res["median_archive_bits"] = table
    if decoder and planned is None:   # legacy v1 accounting (field name kept for byte-level reproduction)
        dec_bits = decoder["gzip_bytes"] * 8
        am = {}
        for (fam, n), d in sorted(bits.items()):
            am[f"{fam}|n{n}"] = {cd: {"payload_sum": int(np.sum(v)), "decoder_bits": dec_bits,
                                      "amortized_total": int(dec_bits + np.sum(v)), "objects": len(v)}
                                 for cd, v in d.items() if not cd.startswith("generic")}
        res["amortized_totals_note"] = ("decoder charged once per cell = gzip-9 size of codec.py (all codecs share one "
                                        "decoder module, so the charge is identical across codecs)")
        res["amortized_totals"] = am
    elif planned is not None:
        dec = bundle or {}
        dec_bits = dec.get("gzip_bytes", 0) * 8
        am = {}
        for (fam, n), d in sorted(bits.items()):
            am[f"{fam}|n{n}"] = {cd: {"archive_sum_bits": int(np.sum(v)),
                                      "payload_sum_bits": (int(np.sum(payload[(fam, n)][cd]))
                                                           if payload[(fam, n)].get(cd) else None),
                                      "decoder_bundle_bits": dec_bits,
                                      "amortized_total_bits(archive_sum+decoder_bundle)": int(dec_bits + np.sum(v)),
                                      "objects": len(v)}
                                 for cd, v in d.items() if not cd.startswith("generic")}
        res["decoder_bundle"] = dec
        res["amortized_totals_note"] = (
            "archive_sum = sum of complete archives (header+framing+payload); payload_sum is NOT added to it. The "
            "decoder charge is the gzip-9 size of the complete local dependency bundle under CPython 3.12 stdlib, "
            "identical for every codec. These are encoder-specific code lengths, not Kolmogorov complexity.")
        res["amortized_totals"] = am
    (out_dir / summary_name).write_text(json.dumps(res, indent=1, sort_keys=True, default=str))
    digest = hashlib.sha256((out_dir / summary_name).read_bytes()).hexdigest()
    try:
        _figures(res, out_dir)
    except Exception as e:
        res["figure_error"] = repr(e)
    return {"digest": digest, "independent_worlds": res["independent_worlds"], "correctness": res["correctness"],
            "summary": str(out_dir / summary_name)}


def _figures(res: dict, out_dir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fams = ("sparse_conj", "canalizing", "parity", "modular", "bounded_random", "dense_random")
    codecs = ("index", "dnf", "gate", "circuit", "bdd", "lut", "generic_lzma")
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    for ax, fam in zip(axes.flat, fams):
        rows = sorted(((int(k.split("|n")[1]), v) for k, v in res["median_archive_bits"].items() if k.startswith(fam + "|")))
        for cd in codecs:
            xs = [n for n, v in rows if cd in v]
            ys = [v[cd] for n, v in rows if cd in v]
            if xs:
                ax.plot(xs, ys, marker="o", ms=3, label=cd)
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_title(fam, fontsize=9)
        ax.set_xlabel("n (nodes)")
        ax.set_ylabel("median archive bits")
    axes.flat[0].legend(fontsize=7)
    phase = res.get("phase", "development").upper()
    fig.suptitle(f"S1 {phase}: archive bits of the same network object under each codec", fontsize=10)
    fig.tight_layout()
    fig.savefig(out_dir / "s1_bits_vs_n.png", dpi=130)
    plt.close(fig)
    fig, ax = plt.subplots(1, 1, figsize=(8, 5))
    backends = ("reference", "literal", "index_enum", "index_cube", "index_sat", "bdd_ref")
    for b in backends:
        pts = []
        for k, c in res["completion"].items():
            bb, n = k.split("|n")
            if bb != b:
                continue
            tot = sum(v for s, v in c.items() if s != "excluded_by_design")
            if tot:
                pts.append((int(n), c.get("completed", 0) / tot))
        pts.sort()
        if pts:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", label=b)
    ax.set_xscale("log", base=2)
    ax.set_xlabel("n (nodes)")
    ax.set_ylabel("fraction of queries completed within the 20 s cap (excl. design exclusions)")
    ax.legend(fontsize=8)
    ax.set_title(f"S1 {phase}: capped completion by backend (timeouts/unknown kept in denominator)", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_dir / "s1_completion.png", dpi=130)
    plt.close(fig)
