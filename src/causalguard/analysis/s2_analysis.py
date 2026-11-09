"""Offline S2 analysis: reads raw run records only (never calls a model or regenerates data).

Primary endpoint (registered in configs/confirmatory.json and docs/PROTOCOL.md):
  population realizable, regime uniform_states, budget 16, the 16 hidden INTERVENTION
  queries per world; Delta_w = acc(min index-code model) - E[acc(uniform compatible model)];
  equal-weight stratified mean over families; stratified paired cluster bootstrap over worlds
  (5000 replicates, fixed seed).  Missing outputs (empty V(D)) score 0 (primary); complete-case
  is reported as sensitivity.
Everything else is exploratory/secondary.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from ..runner import ROOT, read_jsonl
from ..stats import design_simulation, paired_cluster_bootstrap, stratified_mean

CODECS = ("index", "circuit", "bdd", "dnf")
PRIMARY = {"population": "realizable", "regime": "uniform_states", "budget": "16", "kind": "intervention",
           "method_a": "index", "method_b": "uniform"}


def load(run_ids: list[str]) -> list[dict]:
    recs = []
    for rid in run_ids:
        recs += read_jsonl(ROOT / "runs" / rid / "records.jsonl")
    return recs


def _query_scores(rows: list[dict], kind: str) -> dict:
    """Per-world scores over the query grid of one (regime, budget).  Denominator = all queries
    of that kind (missing predictions count as incorrect)."""
    qs = [q for q in rows if q["kind"] == kind]
    N = len(qs)
    out = {"n_queries": N}
    for cd in CODECS:
        out[cd] = sum(1 for q in qs if q["pred"][cd] is not None and q["pred"][cd] == q["truth"]) / N
        out[cd + "_missing"] = sum(1 for q in qs if q["pred"][cd] is None)
    if "mdl_two_part_index" in qs[0]["pred"]:
        out["mdl_two_part_index"] = sum(1 for q in qs if q["pred"]["mdl_two_part_index"] == q["truth"]) / N
    out["uniform"] = sum((q["p_uniform"] if q["truth"] else 1 - q["p_uniform"]) for q in qs
                         if q["p_uniform"] is not None) / N
    out["uniform_missing"] = sum(1 for q in qs if q["p_uniform"] is None)
    out["uniform_mc_se_mean"] = float(np.mean([q["uniform_se"] or 0.0 for q in qs]))
    out["uniform_mc_fraction"] = sum(1 for q in qs if q.get("uniform_method") == "monte_carlo") / N
    out["majority"] = sum(1 for q in qs if q["majority"] == q["truth"]) / N
    out["oracle"] = 1.0
    if "verdict" in qs[0]:
        ans = [q for q in qs if q["verdict"] in ("entailed", "refuted")]
        correct = [q for q in ans if (q["verdict"] == "entailed") == bool(q["truth"])]
        out["consensus_coverage"] = len(ans) / N
        out["consensus_correct"] = len(correct) / N
        out["consensus_wrong_hidden"] = (len(ans) - len(correct)) / N
        out["consensus_cond_acc"] = (len(correct) / len(ans)) if ans else None
        out["inconsistent"] = sum(1 for q in qs if q["verdict"] == "inconsistent_evidence_or_class") / N
        # selected-model predictions on queries the consensus leaves underdetermined
        und = [q for q in qs if q["verdict"] == "underdetermined"]
        out["n_underdetermined"] = len(und)
        if und:
            out["index_acc_on_underdetermined"] = sum(1 for q in und if q["pred"]["index"] == q["truth"]) / len(und)
            out["uniform_acc_on_underdetermined"] = sum((q["p_uniform"] if q["truth"] else 1 - q["p_uniform"])
                                                        for q in und) / len(und)
    return out


def per_world_table(recs: list[dict]) -> list[dict]:
    rows = []
    for r in recs:
        w = r["world"]
        base = {"world_id": w["world_id"], "item_id": r["item_id"], "run_id": r["run_id"], "family": w["family"],
                "population": w["population"], "realizable": w["realizable"]}
        for regime, byb in r["regimes"].items():
            for B, res in byb.items():
                for kind in ("intervention", "state"):
                    s = _query_scores(res["queries"], kind)
                    rows.append({**base, "regime": regime, "budget": int(B), "kind": kind, "empty_vs": res["empty"],
                                 "log10_vs": res["log10_vs"], **s})
        for rate, nz in r.get("noise", {}).items():
            for B, res in nz["budgets"].items():
                s = _query_scores(res["queries"], "intervention")
                rows.append({**base, "regime": f"uniform_states+noise{rate}", "budget": int(B), "kind": "intervention",
                             "empty_vs": res["empty"], "log10_vs": res["log10_vs"], **s})
    return rows


def _select(rows, **kw):
    return [r for r in rows if all(r.get(k) == v for k, v in kw.items())]


def contrast(rows, a, b, reps=5000, seed=20261109, complete_case=False):
    sel = rows
    if complete_case:
        sel = [r for r in rows if not r["empty_vs"]]
    if not sel:
        return None
    d = np.array([r[a] - r[b] for r in sel])
    s = np.array([r["family"] for r in sel])
    br = paired_cluster_bootstrap(d, s, replicates=reps, seed=seed)
    return {"a": a, "b": b, "estimate": br.estimate, "ci95": [br.lo, br.hi], "se": br.se, "n_worlds": br.n_worlds,
            "n_strata": br.n_strata, "replicates": reps, "seed": seed,
            "mean_a": stratified_mean(np.array([r[a] for r in sel]), s),
            "mean_b": stratified_mean(np.array([r[b] for r in sel]), s),
            "sd_delta": float(d.std(ddof=1)) if len(d) > 1 else None,
            "per_family": {f: {"mean_delta": float(d[s == f].mean()), "n": int((s == f).sum())} for f in np.unique(s)}}


def analyze(run_ids: list[str], out_dir: Path, reps_primary: int = 5000, reps_secondary: int = 2000,
            sizing: bool = True) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    recs = load(run_ids)
    if not recs:
        raise SystemExit("no records")
    rows = per_world_table(recs)
    # world-count audit (independent units) per population
    worlds = defaultdict(set)
    for r in rows:
        worlds[r["population"]].add(r["world_id"])
    result = {"run_ids": run_ids, "n_records": len(recs),
              "independent_worlds": {k: len(v) for k, v in worlds.items()},
              "primary_definition": PRIMARY}
    # ---------------- primary
    prim_rows = _select(rows, population="realizable", regime="uniform_states", budget=16, kind="intervention")
    # restrict to the main realizable corpus (exclude the noise-stress worlds, which only ran uniform_states)
    noise_ids = {r["world_id"] for r in rows if "noise" in r["regime"]}
    prim_rows = [r for r in prim_rows if r["world_id"] not in noise_ids]
    result["primary"] = contrast(prim_rows, "index", "uniform", reps_primary)
    result["primary_complete_case"] = contrast(prim_rows, "index", "uniform", reps_primary, complete_case=True)
    # ---------------- secondary / exploratory curves
    curves = []
    for pop in ("realizable", "misspecified", "shift"):
        for regime in ("uniform_states", "observational", "clamp_interventions", "active"):
            for B in (2, 4, 8, 16, 32, 64):
                for kind in ("intervention", "state"):
                    sel = [r for r in _select(rows, population=pop, regime=regime, budget=B, kind=kind)
                           if r["world_id"] not in noise_ids]
                    if not sel:
                        continue
                    s = np.array([r["family"] for r in sel])
                    entry = {"population": pop, "regime": regime, "budget": B, "kind": kind, "n_worlds": len(sel),
                             "empty_vs_rate": float(np.mean([r["empty_vs"] for r in sel])),
                             "mean_log10_vs": float(np.mean([r["log10_vs"] for r in sel if r["log10_vs"] != float("-inf")]
                                                            or [float("nan")]))}
                    for m in CODECS + ("uniform", "majority", "consensus_coverage", "consensus_correct",
                                       "consensus_wrong_hidden"):
                        vals = np.array([r[m] for r in sel if r.get(m) is not None], dtype=float)
                        entry[m] = stratified_mean(vals, s[[r.get(m) is not None for r in sel]]) if len(vals) else None
                    curves.append(entry)
    result["curves"] = curves
    sec = {}
    for B in (4, 8, 16, 32):
        base = [r for r in _select(rows, population="realizable", regime="uniform_states", budget=B, kind="intervention")
                if r["world_id"] not in noise_ids]
        for cd in CODECS:
            sec[f"uniform_states|B{B}|{cd}-uniform"] = contrast(base, cd, "uniform", reps_secondary)
        sec[f"uniform_states|B{B}|index-circuit"] = contrast(base, "index", "circuit", reps_secondary)
        sec[f"uniform_states|B{B}|index-majority"] = contrast(base, "index", "majority", reps_secondary)
    for regime in ("observational", "clamp_interventions", "active"):
        base = _select(rows, population="realizable", regime=regime, budget=16, kind="intervention")
        sec[f"{regime}|B16|index-uniform"] = contrast(base, "index", "uniform", reps_secondary)
    st = [r for r in _select(rows, population="realizable", regime="uniform_states", budget=16, kind="state")
          if r["world_id"] not in noise_ids]
    sec["uniform_states|B16|STATE-holdout|index-uniform"] = contrast(st, "index", "uniform", reps_secondary)
    # active vs random designed measurements at equal budgets (index accuracy and consensus coverage)
    for B in (4, 8, 16):
        a = {r["world_id"]: r for r in _select(rows, population="realizable", regime="active", budget=B, kind="intervention")}
        u = {r["world_id"]: r for r in _select(rows, population="realizable", regime="uniform_states", budget=B,
                                               kind="intervention")}
        ids = sorted(set(a) & set(u))
        if ids:
            for m in ("index", "consensus_coverage"):
                d = np.array([a[i][m] - u[i][m] for i in ids])
                s = np.array([a[i]["family"] for i in ids])
                br = paired_cluster_bootstrap(d, s, replicates=reps_secondary)
                sec[f"active-minus-random|B{B}|{m}"] = {"estimate": br.estimate, "ci95": [br.lo, br.hi], "n_worlds": len(ids)}
    for pop in ("misspecified", "shift"):
        base = _select(rows, population=pop, regime="uniform_states", budget=16, kind="intervention")
        if base:
            sec[f"{pop}|uniform_states|B16|index-uniform(missing=0)"] = contrast(base, "index", "uniform", reps_secondary)
            sec[f"{pop}|uniform_states|B16|index-uniform(complete-case)"] = contrast(base, "index", "uniform",
                                                                                   reps_secondary, complete_case=True)
    result["secondary_exploratory"] = sec
    # ---------------- noise stress (separate MDL experiment)
    noise = []
    for rate in ("0.01", "0.05", "0.1"):
        for B in (16, 32, 64):
            sel = _select(rows, regime=f"uniform_states+noise{rate}", budget=B)
            if not sel:
                continue
            s = np.array([r["family"] for r in sel])
            noise.append({"rate": float(rate), "budget": B, "n_worlds": len(sel),
                          "exact_vs_empty_rate": float(np.mean([r["empty_vs"] for r in sel])),
                          "index_exact_acc(missing=0)": stratified_mean(np.array([r["index"] for r in sel]), s),
                          "mdl_two_part_index_acc": stratified_mean(np.array([r["mdl_two_part_index"] for r in sel]), s),
                          "uniform_acc(missing=0)": stratified_mean(np.array([r["uniform"] for r in sel]), s)})
    result["noise_stress"] = noise
    # ---------------- true-rank audit (B16 uniform_states, realizable)
    audit = defaultdict(list)
    for r in recs:
        if r["world"]["population"] != "realizable" or r["world"]["world_id"] in noise_ids:
            continue
        a = r["regimes"].get("uniform_states", {}).get("16", {}).get("true_rank_audit")
        if not a:
            continue
        for cd, nodes in a.items():
            for nd in nodes:
                if nd.get("compatible"):
                    audit[(r["world"]["family"], cd)].append((nd["frac_shorter"], nd["frac_tied"],
                                                              nd["true_bits"] == nd["min_bits"]))
    result["true_rank_audit_B16"] = {f"{f}|{cd}": {"nodes": len(v), "mean_frac_compatible_strictly_shorter":
                                                   float(np.mean([x[0] for x in v])),
                                                   "frac_true_rule_is_minimum": float(np.mean([x[2] for x in v]))}
                                     for (f, cd), v in sorted(audit.items())}
    # ---------------- timing / cost
    secs = [r["seconds"] for r in recs]
    result["compute"] = {"world_seconds_median": float(np.median(secs)), "world_seconds_max": float(np.max(secs)),
                         "world_seconds_total": float(np.sum(secs)),
                         "peak_rss_bytes_max": int(max(r.get("worker_peak_rss_bytes", 0) for r in recs))}
    irr = defaultdict(int)
    for r in recs:
        for x in r["world"]["irregularities"] + r["instance_irregularities"]:
            irr[x.split(":")[0] if "degenerate" not in x else "degenerate_rule"] += 1
    result["generator_irregularities"] = dict(irr)
    # ---------------- design sizing from DEVELOPMENT primary deltas only
    if sizing and prim_rows:
        d = np.array([r["index"] - r["uniform"] for r in prim_rows])
        s = np.array([r["family"] for r in prim_rows])
        result["design_simulation"] = design_simulation(d, s, sims=2000)
    # ---------------- write
    with (out_dir / "s2_per_world.csv").open("w", newline="") as fh:
        keys = sorted({k for r in rows for k in r})
        wr = csv.DictWriter(fh, keys)
        wr.writeheader()
        for r in rows:
            wr.writerow(r)
    (out_dir / "s2_summary.json").write_text(json.dumps(result, indent=1, sort_keys=True, default=float))
    result["digest"] = hashlib.sha256((out_dir / "s2_summary.json").read_bytes()).hexdigest()
    try:
        _figures(result, out_dir)
    except Exception as e:  # figures are optional; numbers are in the JSON
        result["figure_error"] = repr(e)
    return {"primary": result["primary"], "independent_worlds": result["independent_worlds"],
            "summary": str(out_dir / "s2_summary.json"), "digest": result["digest"]}


def _figures(result: dict, out_dir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cv = [c for c in result["curves"] if c["kind"] == "intervention"]
    fig, axes = plt.subplots(1, 4, figsize=(17, 4), sharey=True)
    colors = {"index": "#1f77b4", "circuit": "#ff7f0e", "bdd": "#2ca02c", "dnf": "#9467bd", "uniform": "#7f7f7f",
              "majority": "#bcbd22"}
    for ax, regime in zip(axes, ("uniform_states", "observational", "clamp_interventions", "active")):
        sel = sorted([c for c in cv if c["population"] == "realizable" and c["regime"] == regime], key=lambda c: c["budget"])
        if not sel:
            continue
        xs = [c["budget"] for c in sel]
        for m, col in colors.items():
            ax.plot(xs, [c[m] for c in sel], marker="o", ms=3, label=m, color=col)
        ax.plot(xs, [c["consensus_coverage"] for c in sel], ls="--", color="k", label="consensus coverage")
        ax.set_xscale("log", base=2)
        ax.set_title(f"{regime} (n={sel[0]['n_worlds']} worlds)", fontsize=9)
        ax.set_xlabel("evidence budget (measurements)")
    axes[0].set_ylabel("hidden intervention accuracy")
    axes[-1].legend(fontsize=7, loc="lower right")
    fig.suptitle("S2 DEVELOPMENT (not confirmatory): realizable worlds, equal-weight family strata", fontsize=10)
    fig.tight_layout()
    fig.savefig(out_dir / "s2_accuracy_vs_budget.png", dpi=130)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, pop in zip(axes, ("realizable", "misspecified")):
        sel = sorted([c for c in cv if c["population"] == pop and c["regime"] == "uniform_states"], key=lambda c: c["budget"])
        if not sel:
            continue
        ax.plot([c["consensus_coverage"] for c in sel], [c["consensus_wrong_hidden"] for c in sel], marker="o")
        for c in sel:
            ax.annotate(str(c["budget"]), (c["consensus_coverage"], c["consensus_wrong_hidden"]), fontsize=7)
        ax.set_xlabel("consensus answer coverage (fraction of queries certified)")
        ax.set_ylabel("certified but wrong about hidden world (fraction of all queries)")
        ax.set_title(f"{pop} worlds (DEVELOPMENT)", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_dir / "s2_consensus_risk_coverage.png", dpi=130)
    plt.close(fig)
