"""Offline S4 analysis (reads saved run records only; never calls a model).

Units: the WORLD is the unit of independence.  Per-world values are means over that world's scheduled claims;
missing/invalid outcomes are failed scheduled outcomes (scored wrong), never dropped.  Strata (families) are
equally weighted; stratified paired cluster bootstrap over worlds (stats.paired_cluster_bootstrap).
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from ..stats import design_simulation, holm, paired_cluster_bootstrap, stratified_mean

VERDICTS = ("entailed", "refuted", "underdetermined")


def _load(run_dir):
    from ..runner import load_run
    lr = load_run(Path(run_dir))
    return lr


def _boot(vals_a, vals_b, strata, reps=10000, seed=20261111):
    d = np.asarray(vals_a, float) - np.asarray(vals_b, float)
    br = paired_cluster_bootstrap(d, np.asarray(strata), replicates=reps, seed=seed)
    return {"estimate": br.estimate, "ci95": [br.lo, br.hi], "n_worlds": br.n_worlds, "replicates": reps,
            "seed": seed}


# --------------------------------------------------------------------------- offline family / cost map

def _forecast_scores(p, truth):
    if p is None:
        return None
    acc = 0.5 if p == 0.5 else float((p > 0.5) == bool(truth))
    pc = min(max(p, 1e-12), 1 - 1e-12)
    return {"acc": acc, "brier": (p - truth) ** 2, "logloss": -(math.log2(pc) if truth else math.log2(1 - pc))}


def summarize_map(run_dir, reps=10000) -> dict:
    lr = _load(run_dir)
    res = lr["results"]
    out = {"run_id": lr["plan"]["run_id"], "planned": len(lr["plan"]["items"]), "ok": len(res),
           "failed": {k: str(v["output"].get("error"))[:160] for k, v in lr["failures"].items()},
           "missing": lr["missing"], "by_family": {}, "by_prefix": {}, "secondary": {}}
    fams = sorted({r["family"] for r in res.values()})
    prefixes = sorted({int(b) for r in res.values() for b in r["prefixes"]})
    # agreement, verdict mix, costs
    agree = Counter()
    for r in res.values():
        for cell in r["prefixes"].values():
            for c in cell["claims"]:
                agree[c["agree"]] += 1
    out["replay_agreement"] = {"claims": sum(agree.values()), "agree": agree[True], "disagree": agree[False]}
    for f in fams:
        rows = [r for r in res.values() if r["family"] == f]
        fam = {"worlds_ok": len(rows), "hidden_description_bits_median": {}, "prefix": {}}
        for cd in ("index", "gate", "circuit", "lut", "cgh_full", "cgh_flat", "cgh_no_order", "cgh_no_analytic"):
            vals = [r["hidden_description_bits"][cd] for r in rows if isinstance(r["hidden_description_bits"][cd], int)]
            fam["hidden_description_bits_median"][cd] = float(np.median(vals)) if vals else None
        fam["cgh_full_mode_counts"] = dict(Counter(r["hidden_description_bits"]["cgh_full_mode"] for r in rows))
        for B in prefixes:
            cells = [r["prefixes"][str(B)] for r in rows if str(B) in r["prefixes"]]
            vm = Counter(c["verdicts"][next(iter(c["verdicts"]))] for cell in cells for c in cell["claims"])
            cost = {a: float(np.median([cell["replay"][a]["wall_s"] for cell in cells])) for a in cells[0]["replay"]}
            fam["prefix"][str(B)] = {"verdict_mix": dict(vm), "median_log10_V": float(np.median([c["log10_V"] for c in cells])),
                                     "median_replay_wall_s": cost,
                                     "structured_models_median": float(np.median([
                                         int(c["struct_status"].get("cgh_prior", "0 models").split()[0])
                                         if "models" in c["struct_status"].get("cgh_prior", "") else -1 for c in cells]))}
        out["by_family"][f] = fam
    # secondary: codec-induced averaging on underdetermined claims, world level
    codes = None
    for B in prefixes:
        per_world = []
        for r in res.values():
            cell = r["prefixes"].get(str(B))
            if not cell:
                continue
            und = [c for c in cell["claims"] if c.get("prob")]
            if not und:
                continue
            codes = codes or list(und[0]["prob"])
            row = {"family": r["family"], "n_und": len(und)}
            for cd in codes:
                sc = [_forecast_scores(c["prob"][cd], c["truth_holds"]) for c in und]
                if any(s is None for s in sc):
                    row[cd] = None
                    continue
                row[cd] = {k: float(np.mean([s[k] for s in sc])) for k in ("acc", "brier", "logloss")}
            for cd, pred in (("shortest_index", "index"), ("shortest_cgh_flat", "cgh_flat"),
                             ("shortest_cgh_prior", "cgh_prior")):
                v = [c["shortest"][pred] for c in und]
                row[cd] = None if any(x is None for x in v) else {"acc": float(np.mean([int(x == c["truth_holds"])
                                                                                         for x, c in zip(v, und)]))}
            per_world.append(row)
        sec = {"worlds_with_underdetermined": len(per_world),
               "claims": int(sum(w["n_und"] for w in per_world)), "by_code": {}, "contrasts": {}, "by_family": {}}
        methods = codes + ["shortest_index", "shortest_cgh_flat", "shortest_cgh_prior"]
        for m in methods:
            ok = [w for w in per_world if w.get(m) is not None]
            if not ok:
                continue
            s = np.array([w["family"] for w in ok])
            sec["by_code"][m] = {k: stratified_mean(np.array([w[m][k] for w in ok]), s)
                                 for k in ok[0][m]}
            sec["by_code"][m]["worlds"] = len(ok)
        for a, b in (("cgh_prior", "uniform"), ("cgh_prior", "index"), ("cgh_prior", "cgh_flat"),
                     ("cgh_flat", "uniform"), ("cgh_flat", "cgh_flat_noanalytic"), ("cgh_prior", "cgh_prior_noanalytic"),
                     ("index", "uniform"), ("circuit", "uniform"), ("shortest_cgh_prior", "uniform"),
                     ("shortest_index", "uniform")):
            ok = [w for w in per_world if w.get(a) is not None and w.get(b) is not None]
            if len(ok) < 4:
                continue
            s = [w["family"] for w in ok]
            sec["contrasts"][f"{a}-{b}|acc"] = _boot([w[a]["acc"] for w in ok], [w[b]["acc"] for w in ok], s, reps)
            if "brier" in ok[0][a] and "brier" in ok[0][b]:
                sec["contrasts"][f"{a}-{b}|brier"] = _boot([w[a]["brier"] for w in ok], [w[b]["brier"] for w in ok], s,
                                                           reps)
        for f in fams:
            ok = [w for w in per_world if w["family"] == f]
            sec["by_family"][f] = {m: (float(np.mean([w[m]["acc"] for w in ok if w.get(m)])) if any(w.get(m) for w in ok)
                                       else None) for m in methods}
            sec["by_family"][f]["worlds"] = len(ok)
        out["secondary"][str(B)] = sec
    return out


# --------------------------------------------------------------------------- S4-B, known panel, stress

def summarize_active(run_dir) -> dict:
    lr = _load(run_dir)
    res = list(lr["results"].values())
    pol = defaultdict(lambda: defaultdict(list))
    agree_bcd, n_t = 0, 0
    for r in res:
        for t in r["targets"]:
            n_t += 1
            buys = {k: [b["menu_index"] for b in v["purchases"]] for k, v in t["policies"].items()}
            agree_bcd += int(buys.get("eig|B") == buys.get("eig|C") == buys.get("eig|D"))
            for k, v in t["policies"].items():
                for B, c in v["curve"].items():
                    pol[k][B].append({"resolved": int(c["verdict"] in ("entailed", "refuted")),
                                      "forecast_correct": c["forecast_correct"], "family": r["family"]})
    out = {"run_id": lr["plan"]["run_id"], "worlds": len(res), "targets": n_t,
           "eig_choices_identical_across_B_C_D": agree_bcd, "policies": {}}
    for k, byb in pol.items():
        out["policies"][k] = {B: {"resolved_fraction": float(np.mean([x["resolved"] for x in v])),
                                  "forecast_accuracy_nontie": (float(np.mean([x["forecast_correct"] for x in v
                                                                               if x["forecast_correct"] is not None]))
                                                               if any(x["forecast_correct"] is not None for x in v)
                                                               else None),
                                  "n": len(v)} for B, v in sorted(byb.items(), key=lambda kv: int(kv[0]))}
    return out


def summarize_known(run_dir) -> dict:
    lr = _load(run_dir)
    rows = [q | {"n": r["n"]} for r in lr["results"].values() for q in r["queries"]]
    exact = [q for q in rows if "exact_match" in q]
    return {"run_id": lr["plan"]["run_id"], "queries": len(rows), "exact_checked": len(exact),
            "exact_matches": sum(q["exact_match"] for q in exact),
            "corroboration_only": sum(1 for q in rows if q.get("verification") == "corroboration_only"),
            "witness_replayed_all": all(q.get("witness_replayed", True) for q in rows),
            "by_n": {n: {"median_c": float(np.median([q["c"] for q in rows if q["n"] == n])),
                         "median_d": float(np.median([q["d"] for q in rows if q["n"] == n])),
                         "median_mu": float(np.median([q["mu"] for q in rows if q["n"] == n])),
                         "max_enumerated": max(q["enumerated"] for q in rows if q["n"] == n),
                         "median_wall_s": float(np.median([q["wall_s"] for q in rows if q["n"] == n]))}
                     for n in sorted({q["n"] for q in rows})},
            "families_covered": sorted({f for q in rows for f in q["families"]})}


def summarize_stress(run_dir) -> dict:
    lr = _load(run_dir)
    plan = {e["item_id"]: e["payload"] for e in lr["plan"]["items"]}
    cells = defaultdict(lambda: {"items": 0, "finished_claims": 0, "claims": 0, "timeouts_or_errors": 0, "wall": []})
    by_seed = defaultdict(dict)
    for iid, p in plan.items():
        c = cells[(p["n"], p["backend"])]
        c["items"] += 1
        if iid in lr["results"]:
            r = lr["results"][iid]
            c["claims"] += len(r["verdicts"])
            c["finished_claims"] += sum(v != "unsupported_or_resource" for v in r["verdicts"])
            c["wall"].append(r["wall_s"])
            by_seed[(p["n"], p["seed"])][p["backend"]] = r["verdicts"]
        else:
            c["timeouts_or_errors"] += 1
            c["claims"] += p.get("claims", 4)
    agree = Counter()
    for vs in by_seed.values():
        if len(vs) > 1:
            for i in range(len(next(iter(vs.values())))):
                fin = {b: v[i] for b, v in vs.items() if v[i] != "unsupported_or_resource"}
                if len(fin) > 1:
                    agree[len(set(fin.values())) == 1] += 1
    return {"run_id": lr["plan"]["run_id"],
            "cells": {f"n{n}|{b}": {**{k: v for k, v in c.items() if k != "wall"},
                                    "median_item_wall_s": float(np.median(c["wall"])) if c["wall"] else None}
                      for (n, b), c in sorted(cells.items())},
            "cross_backend_agreement_where_both_finished": {"agree": agree[True], "disagree": agree[False]},
            "item_timeout_s": lr["plan"]["config"].get("item_timeout_s")}


# --------------------------------------------------------------------------- surface baselines (training only)

def fit_surface_baselines(out_path, salt="dev-s4-train-v1", per_family=20) -> dict:
    """Fitted on a TRAINING salt before any pilot call; persisted with its digest."""
    from ..s4.evaluator import Evaluator
    from ..s4.tasks import S4_FAMILIES
    cell = defaultdict(Counter)
    cellB = defaultdict(Counter)
    tot = Counter()
    for f in S4_FAMILIES:
        for i in range(per_family):
            ev = Evaluator(salt, i, f)
            for r in ev.reference(crosscheck_sat=False):
                cell[f"h{r.h}|{r.kind}"][r.verdict] += 1
                cellB[f"h{r.h}|{r.kind}|B{ev.design.budget}"][r.verdict] += 1
                tot[r.verdict] += 1
    art = {"schema": "s4-surface-baselines-v1", "training_salt": salt, "worlds": per_family * len(S4_FAMILIES),
           "rules": {"always_underdetermined": "underdetermined",
                     "cell_majority": {k: v.most_common(1)[0][0] for k, v in sorted(cell.items())},
                     "cell_budget_majority": {k: v.most_common(1)[0][0] for k, v in sorted(cellB.items())},
                     "forecast_observed_majority": "majority of the target node's observed next values (ties -> 0)"},
           "training_verdict_mix": dict(tot), "cell_counts": {k: dict(v) for k, v in sorted(cell.items())}}
    body = json.dumps(art, sort_keys=True, indent=1)
    art["sha256"] = hashlib.sha256(body.encode()).hexdigest()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(art, sort_keys=True, indent=1) + "\n")
    return art


def _baseline_answers(rec_pub_claims, ref, budget, bl, evidence):
    from ..schema import Evidence, Query
    ev = Evidence.from_json(evidence)
    out = {}
    for c in rec_pub_claims:
        q = Query.from_json(c["query"])
        vals = [v for o in ev.observations for j, v in o.observed if j == q.target.node]
        maj = int(2 * sum(vals) > len(vals))
        out[c["cid"]] = {"always_underdetermined": "underdetermined",
                         "cell_majority": bl["rules"]["cell_majority"].get(f"h{q.horizon}|{q.intervention.kind}",
                                                                          "underdetermined"),
                         "cell_budget_majority": bl["rules"]["cell_budget_majority"].get(
                             f"h{q.horizon}|{q.intervention.kind}|B{budget}", "underdetermined"),
                         "forecast_majority": maj, "target_value": q.target.value}
    return out


# --------------------------------------------------------------------------- pilot

def merged_commit_answers(ep, cids) -> dict | None:
    """Sensitivity re-scoring (D52): re-parse the committing turn's raw output and MERGE all its commit calls
    (first answer per claim wins).  Deterministic; no model call.  None if the episode never committed."""
    from ..s4.pilot import parse_answers, parse_json
    if ep.get("status") != "committed" or not ep.get("calls"):
        return None
    obj = parse_json(ep["calls"][-1]["raw_output"]) or {}
    tcs = obj.get("tool_calls")
    if not isinstance(tcs, list):
        tcs = [{"tool": "commit", "answers": obj.get("answers")}] if isinstance(obj.get("answers"), list) else []
    out: dict = {}
    for tc in tcs[:24]:
        if isinstance(tc, dict) and tc.get("tool") == "commit":
            for c, a in parse_answers(tc.get("answers"), cids).items():
                out.setdefault(c, a)
    return out


def _world_scores(ep, ref, final=None):
    """Per-world scores of one episode (8 scheduled claims; missing = wrong).  ``final`` overrides the recorded
    final answers (merged-commit sensitivity)."""
    fin = (ep.get("final", {}) or {}) if final is None else final
    cids = sorted(ref)
    acc = [int(fin.get(c, {}).get("verdict") == ref[c]["verdict"]) for c in cids]
    wrong_def = [int(c in fin and fin[c]["verdict"] in ("entailed", "refuted") and fin[c]["verdict"] != ref[c]["verdict"])
                 for c in cids]
    und = [c for c in cids if ref[c]["verdict"] == "underdetermined"]
    # forecast: predicted TARGET VALUE vs actual value of the target node
    fc = []
    for c in und:
        if c in fin:
            fc.append(int(fin[c]["forecast"] == _actual_value(ref[c])))
        else:
            fc.append(0)
    rel = ep.get("released_verified", {}) or {}
    # a released answer is the COMMITTED answer; under the recorded (v1-harness) final, released answers that were
    # overwritten are not in ``fin`` and are counted separately, never as wrong
    wrong_released = sum(1 for c, ok in rel.items() if ok and c in fin and fin[c]["verdict"] != ref[c]["verdict"])
    released_not_in_final = sum(1 for c, ok in rel.items() if ok and c not in fin)
    return {"acc": float(np.mean(acc)), "answered": len(fin), "wrong_definitive": int(sum(wrong_def)),
            "forecast_acc": float(np.mean(fc)) if fc else None, "n_und": len(und),
            "released_verified": int(sum(bool(v) for v in rel.values())), "wrong_released_verified": wrong_released,
            "released_not_in_recorded_final": released_not_in_final}


def _actual_value(r):
    """Actual target-node value: the claim literal value if the claim holds in the hidden mechanism, else its
    complement (the claim literal is target = value)."""
    return r["target_value"] if r["truth_holds"] else 1 - r["target_value"]


def _gates(recs):
    g = {}
    for arm in ("A", "B", "C", "D"):
        eps = [r["episodes"].get(arm) for r in recs if arm in r["episodes"]]
        calls = [c for e in eps for c in e.get("calls", [])]
        parsable = [e for e in eps if e.get("status") in ("answered", "committed")]
        answered = sum(len(e.get("final", {})) for e in eps)
        trunc = sum(1 for c in calls if c["attempts"] and c["attempts"][-1].get("finish_reason") == "length")
        g[arm] = {"episodes": len(eps), "calls": len(calls),
                  "parsable_verdict_rate": answered / max(1, 8 * len(eps)),
                  "episodes_completed": len(parsable), "truncated_calls": trunc,
                  "truncation_rate": trunc / max(1, len(calls)),
                  "statuses": dict(Counter(e.get("status") for e in eps))}
    return g


def analyze_pilot(run_dirs, baselines_path, out_dir, reps=10000) -> dict:
    bl = json.loads(Path(baselines_path).read_text())
    from ..s4.evaluator import Evaluator
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {"models": {}, "baselines_sha256": bl.get("sha256")}
    for d in run_dirs:
        lr = _load(d)
        recs = [lr["results"][e["item_id"]] for e in lr["plan"]["items"] if e["item_id"] in lr["results"]]
        model = lr["plan"]["config"]["provider"]["model"]
        planned = len(lr["plan"]["items"])
        m = {"run_id": lr["plan"]["run_id"], "planned_worlds": planned, "ok_worlds": len(recs),
             "failed_worlds": list(lr["failures"]), "missing_worlds": lr["missing"], "gates": _gates(recs)}
        # semantic mismatch gate: backend verdicts in tool results vs reference (via common batch replay)
        mism = 0
        for r in recs:
            for per in r.get("common_batch_replay", {}).values():
                for cid, x in per.items():
                    mism += x["claim_status"] != r["reference"][cid]["verdict"]
        m["gates"]["semantic_mismatches"] = mism
        rows = []
        for r in recs:
            ev = Evaluator(lr["plan"]["config"]["salt"], r["index"], r["family"])
            pub = ev.public()
            ref = {c: {**x, "target_value": next(cc for cc in pub["claims"] if cc["cid"] == c)["query"]["target"]["value"]}
                   for c, x in r["reference"].items()}
            row = {"family": r["family"], "index": r["index"]}
            for arm, ep in r["episodes"].items():
                row[arm] = _world_scores(ep, ref)
                if arm != "A":
                    mf = merged_commit_answers(ep, sorted(ref))
                    row[f"{arm}_merged"] = _world_scores(ep, ref, mf if mf is not None else ep.get("final", {}))
                    row[f"{arm}_merged"]["changed_by_merge"] = int(mf is not None and mf != ep.get("final", {}))
            # deterministic no-LLM controller: copy the exact tool verdict, forecast = exact majority (ties -> 0)
            from ..versionspace import posterior_from_counts
            ctl_final = {}
            for c, x in ref.items():
                post = posterior_from_counts(int(x["num"]), int(x["den"]))      # owner's majority/tie rule
                holds = post["majority"]                                         # None at an exact tie
                ctl_final[c] = {"verdict": x["verdict"],
                                "forecast": 0 if holds is None else (x["target_value"] if holds else 1 - x["target_value"])}
            row["controller"] = _world_scores({"final": ctl_final}, ref)
            bans = _baseline_answers(pub["claims"], ref, r["budget"], bl, pub["evidence"])
            for b in ("always_underdetermined", "cell_majority", "cell_budget_majority"):
                row[b] = {"acc": float(np.mean([int(bans[c][b] == ref[c]["verdict"]) for c in sorted(ref)]))}
            und = [c for c in ref if ref[c]["verdict"] == "underdetermined"]
            row["forecast_majority"] = {"forecast_acc": float(np.mean([int(bans[c]["forecast_majority"] == _actual_value(ref[c]))
                                                                       for c in und])) if und else None}
            # pre-release checking on the COMMON initial batch (arm A's proposals) replayed through B/C/D
            fa = r["episodes"].get("A", {}).get("final", {}) or {}
            row["prevention"] = {}
            for arm, per in r.get("common_batch_replay", {}).items():
                wrong = [c for c in fa if fa[c]["verdict"] != ref[c]["verdict"]]
                right = [c for c in fa if fa[c]["verdict"] == ref[c]["verdict"]]
                row["prevention"][arm] = {
                    "proposed": len(fa), "wrong_proposed": len(wrong),
                    "wrong_blocked": sum(per[c]["status"] != "verified" for c in wrong),
                    "wrong_verified": sum(per[c]["status"] == "verified" for c in wrong),
                    "correct_blocked": sum(per[c]["status"] != "verified" for c in right),
                    "correct_verified": sum(per[c]["status"] == "verified" for c in right),
                    "scheduled": len(ref)}
            rows.append(row)
        m["per_world"] = rows
        fams = np.array([r["family"] for r in rows])
        arms = [a for a in ("A", "B", "C", "D") if all(a in r for r in rows)]
        m["arm_means"] = {a: {"verdict_acc": stratified_mean(np.array([r[a]["acc"] for r in rows]), fams),
                              "wrong_definitive_per_world": float(np.mean([r[a]["wrong_definitive"] for r in rows])),
                              "forecast_acc_und": _sm([r[a]["forecast_acc"] for r in rows], fams),
                              "released_verified_per_world": float(np.mean([r[a]["released_verified"] for r in rows])),
                              "wrong_released_verified_total": int(sum(r[a]["wrong_released_verified"] for r in rows))}
                          for a in arms + ["controller"]}
        for b in ("always_underdetermined", "cell_majority", "cell_budget_majority"):
            m["arm_means"][b] = {"verdict_acc": stratified_mean(np.array([r[b]["acc"] for r in rows]), fams)}
        for a in ("B", "C", "D"):
            if all(f"{a}_merged" in r for r in rows):
                m["arm_means"][f"{a}_merged_commit_sensitivity"] = {
                    "verdict_acc": stratified_mean(np.array([r[f"{a}_merged"]["acc"] for r in rows]), fams),
                    "episodes_changed_by_merge": int(sum(r[f"{a}_merged"]["changed_by_merge"] for r in rows)),
                    "wrong_released_verified_total": int(sum(r[f"{a}_merged"]["wrong_released_verified"] for r in rows))}
        m["arm_means"]["released_not_in_recorded_final_total"] = {
            a: int(sum(r[a]["released_not_in_recorded_final"] for r in rows)) for a in ("B", "C", "D")}
        m["arm_means"]["forecast_majority"] = {"forecast_acc_und": _sm([r["forecast_majority"]["forecast_acc"] for r in rows], fams)}
        con = {}
        for a, b in (("D", "B"), ("D", "A"), ("D", "C"), ("B", "A"), ("C", "A")):
            if a in arms and b in arms:
                con[f"{a}-{b}"] = _boot([r[a]["acc"] for r in rows], [r[b]["acc"] for r in rows], fams, reps)
        for a, b in (("D", "B"), ("D", "C")):
            if all(f"{a}_merged" in r and f"{b}_merged" in r for r in rows):
                con[f"{a}-{b}|merged_commit_sensitivity"] = _boot([r[f"{a}_merged"]["acc"] for r in rows],
                                                                  [r[f"{b}_merged"]["acc"] for r in rows], fams, reps)
        m["contrasts_verdict_acc"] = con
        prev = defaultdict(Counter)
        for r in rows:
            for arm, x in r["prevention"].items():
                prev[arm].update(x)
        m["prevention_common_batch"] = {arm: {**dict(c), "wrong_blocked_fraction": c["wrong_blocked"] / max(1, c["wrong_proposed"]),
                                              "valid_release_coverage": c["correct_verified"] / max(1, c["scheduled"])}
                                        for arm, c in prev.items()}
        m["costs"] = _costs(recs)
        report["models"][model] = m
    # Holm across the two models' primary contrast (development pilot: descriptive; not a confirmatory test)
    pv = {}
    for model, m in report["models"].items():
        c = m["contrasts_verdict_acc"].get("D-B")
        if c:
            pv[model] = _boot_p(c)
    report["holm_D-B_descriptive"] = holm(pv) if pv else {}
    (out_dir / "s4_pilot_summary.json").write_text(json.dumps(report, indent=1, default=float) + "\n")
    return report


def _sm(vals, fams):
    ok = [(v, f) for v, f in zip(vals, fams) if v is not None]
    if not ok:
        return None
    return stratified_mean(np.array([v for v, _ in ok]), np.array([f for _, f in ok]))


def _boot_p(c):
    """Two-sided normal-approximation p from the bootstrap interval (descriptive only)."""
    from statistics import NormalDist
    lo, hi = c["ci95"]
    se = (hi - lo) / (2 * 1.959964) if hi > lo else 0.0
    if se == 0:
        return 1.0 if c["estimate"] == 0 else 0.0
    z = abs(c["estimate"]) / se
    return 2 * (1 - NormalDist().cdf(z))


def _costs(recs):
    out = {}
    for arm in ("A", "B", "C", "D"):
        eps = [r["episodes"][arm] for r in recs if arm in r["episodes"]]
        calls = [c for e in eps for c in e.get("calls", [])]
        pt = [c["attempts"][-1].get("prompt_tokens") or 0 for c in calls if c["attempts"]]
        ct = [c["attempts"][-1].get("completion_tokens") or 0 for c in calls if c["attempts"]]
        lat = [c["attempts"][-1].get("latency_s") or 0 for c in calls if c["attempts"]]
        tools = [t for e in eps for t in e.get("tool_log", []) if t.get("tool")]
        out[arm] = {"calls": len(calls), "calls_per_world": len(calls) / max(1, len(eps)),
                    "prompt_tokens": int(sum(pt)), "completion_tokens": int(sum(ct)),
                    "model_latency_s": float(sum(lat)), "tool_calls": len(tools),
                    "tool_wall_s": float(sum(t.get("wall_s", 0) for t in tools)),
                    "max_prompt_tokens": int(max(pt)) if pt else 0}
    return out


def sizing(pilot_report: dict, alpha_per_model=0.025, effect=0.05) -> dict:
    """Prospective main-study sizing from pilot per-world deltas (upper-variance scenario reported)."""
    out = {}
    for model, m in pilot_report["models"].items():
        rows = m["per_world"]
        fams = [r["family"] for r in rows]
        out[model] = {}
        for a, b in (("D", "B"), ("D", "A"), ("D", "C")):
            if not all(a in r and b in r for r in rows):
                continue
            d = np.array([r[a]["acc"] - r[b]["acc"] for r in rows])
            entry = {"pilot_sd_delta": float(d.std(ddof=1)), "pilot_mean_delta": float(d.mean()),
                     "nonzero_world_deltas": int((d != 0).sum())}
            if (d != 0).sum() >= 4:
                entry["simulation"] = design_simulation(d, np.array(fams), n_grid=(160, 320, 480, 640, 800),
                                                        effect=effect, sims=2000, variance_inflation=1.5,
                                                        alpha=alpha_per_model)
            else:
                entry["simulation"] = None
                entry["note"] = ("per-world deltas are (almost) all zero: an exact-tool tie; power for a 5-point "
                                 "accuracy difference is not estimable from this pilot and a tie is the expected "
                                 "outcome when both backends finish")
            # conservative normal formula with an UPPER variance (max of pilot SD and 0.25 for a 0/1-ish metric)
            sd_up = max(entry["pilot_sd_delta"] * 1.5, 0.10)
            from ..stats import normal_approx_n
            entry["normal_approx_N_upper_sd"] = {"sd_used": sd_up,
                                                 "N": normal_approx_n(sd_up, effect, alpha_per_model, 0.8)}
            out[model][f"{a}-{b}"] = entry
    return out


def summarize_misspec(run_dir) -> dict:
    lr = _load(run_dir)
    res = list(lr["results"].values())
    ver = [c for r in res for c in r["claims"] if c.get("status") == "verified"]
    return {"run_id": lr["plan"]["run_id"], "worlds": len(res),
            "worlds_evidence_inconsistent": sum(r["inconsistent"] for r in res),
            "claims": sum(len(r["claims"]) for r in res), "verified_definite": len(ver),
            "verified_but_postcondition_violated": sum(c["postcondition_violated"] for c in ver),
            "note": "hidden mechanism outside the declared class (one 4-input node, H declares k = 3); a verified "
                    "conclusion is proof under the declared assumptions only"}
