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
import math
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
    # Bayes predictor under a uniform prior on V(D): predict the majority answer of the compatible set
    # (p > 0.5 -> 1; exact tie -> 0, counted).  Post-hoc richest control (DECISIONS D21).
    out["vs_majority"] = sum(1 for q in qs if q["p_uniform"] is not None and int(q["p_uniform"] > 0.5) == q["truth"]) / N
    out["vs_majority_ties"] = sum(1 for q in qs if q["p_uniform"] == 0.5)
    out["truth_prevalence"] = sum(q["truth"] for q in qs) / N
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
    prim_rows = [r for r in prim_rows if r["world_id"] not in noise_ids and r["family"] != "uniform_H"]
    null_ids = {r["world_id"] for r in rows if r["family"] == "uniform_H"}
    noise_ids = noise_ids | null_ids   # keep the null population out of every main-corpus table
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
                    for m in CODECS + ("uniform", "vs_majority", "majority", "truth_prevalence", "consensus_coverage", "consensus_correct",
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
        base = [r for r in _select(rows, population="realizable", regime=regime, budget=16, kind="intervention")
                if r["world_id"] not in noise_ids]
        sec[f"{regime}|B16|index-uniform"] = contrast(base, "index", "uniform", reps_secondary)
    st = [r for r in _select(rows, population="realizable", regime="uniform_states", budget=16, kind="state")
          if r["world_id"] not in noise_ids]
    sec["uniform_states|B16|STATE-holdout|index-uniform"] = contrast(st, "index", "uniform", reps_secondary)
    # active vs random designed measurements at equal budgets (index accuracy and consensus coverage)
    for B in (4, 8, 16):
        a = {r["world_id"]: r for r in _select(rows, population="realizable", regime="active", budget=B, kind="intervention")
             if r["world_id"] not in noise_ids}
        u = {r["world_id"]: r for r in _select(rows, population="realizable", regime="uniform_states", budget=B,
                                               kind="intervention") if r["world_id"] not in noise_ids}
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
    for B in (8, 16, 32):
        base = [r for r in _select(rows, population="realizable", regime="uniform_states", budget=B, kind="intervention")
                if r["world_id"] not in noise_ids]
        for cd in ("index", "circuit"):
            sec[f"POSTHOC|uniform_states|B{B}|{cd}-vs_majority"] = contrast(base, cd, "vs_majority", reps_secondary)
        sec[f"POSTHOC|uniform_states|B{B}|vs_majority-uniform"] = contrast(base, "vs_majority", "uniform", reps_secondary)
    result["secondary_exploratory"] = sec
    # ---------------- NULL population: worlds drawn uniformly from H (no simplicity in the generator)
    null = {}
    for regime in ("uniform_states", "observational", "clamp_interventions", "active"):
        for B in (4, 8, 16, 32):
            nr = _select(rows, family="uniform_H", regime=regime, budget=B, kind="intervention")
            if not nr:
                continue
            for a, b in (("index", "uniform"), ("circuit", "uniform"), ("vs_majority", "uniform"),
                         ("index", "vs_majority"), ("circuit", "vs_majority")):
                null[f"{regime}|B{B}|{a}-{b}"] = contrast(nr, a, b, reps_secondary)
    result["null_uniform_H"] = null
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
        _per_world_figure(rows, noise_ids - {r["world_id"] for r in rows if r["family"] == "uniform_H"}, out_dir)
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


def _per_world_figure(rows, exclude_ids, out_dir: Path) -> None:
    """Every world rendered (budget 16, uniform designs, intervention queries); null worlds in red."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sel = [r for r in rows if r["regime"] == "uniform_states" and r["kind"] == "intervention" and r["budget"] == 16
           and r["population"] == "realizable" and r["world_id"] not in exclude_ids]
    fams = [f for f in ("conjunctive", "canalizing", "parity", "random_lookup", "modular", "uniform_H")
            if any(r["family"] == f for r in sel)]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5), sharey=True)
    rng = np.random.default_rng(0)
    for ax, (a, b) in zip(axes, (("index", "uniform"), ("index", "vs_majority"), ("circuit", "vs_majority"))):
        for k, f in enumerate(fams):
            d = np.array([r[a] - r[b] for r in sel if r["family"] == f])
            ax.scatter(k + rng.uniform(-0.25, 0.25, len(d)), d, s=6, alpha=0.5,
                       color="tab:red" if f == "uniform_H" else "tab:blue")
            ax.plot([k - 0.3, k + 0.3], [d.mean()] * 2, color="k", lw=2)
        ax.axhline(0, color="gray", lw=0.8)
        ax.set_xticks(range(len(fams)))
        ax.set_xticklabels([f.replace("_", "\n") for f in fams], fontsize=8)
        ax.set_title(f"per-world {a} - {b} (budget 16, 16 intervention queries)", fontsize=9)
    axes[0].set_ylabel("per-world accuracy difference")
    fig.suptitle("S2 DEVELOPMENT, every world shown (blue: structured families; red: NULL worlds drawn uniformly "
                 "from H). Bars = means.", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_dir / "s2_per_world_deltas.png", dpi=130)
    plt.close(fig)


# =========================================================================== iteration 2 analysis (S2-primary-v2)
#
# ``analyze`` above is the HISTORICAL v1 analysis (index - uniform primary, MC majority thresholded at 0.5);
# byte-for-byte reproduction of the v0.1.0-dev summaries is done from that tag (scripts/reproduce_v1.sh).
# ``analyze_v2`` differs in semantics, explicitly:
#  * the primary is bound to a machine-readable endpoint spec that must equal SUPPORTED_ENDPOINT_V2;
#  * runs are reconciled to their persisted plans; duplicate run arguments, duplicate items/worlds across runs,
#    plan/endpoint mismatches and unresolved failures are refused or reported, never dropped silently;
#  * compatible-set majority and random-compatible accuracy are EXACT (integer counts), ties score 0.5;
#  * one world-level paired contribution per endpoint (queries nested inside worlds).

SUPPORTED_ENDPOINT_V2_KEYS = {
    "endpoint_id": "S2-primary-v2", "study": "S2", "design_version": "s2-design-v2", "population": "realizable",
    "families": ["conjunctive", "canalizing", "parity", "random_lookup", "modular"], "family_weighting": "equal",
    "regime": "uniform_states", "budget": 16, "query_kind": "intervention", "queries_per_world": 16,
    "method_a": "index", "method_b": "vs_majority", "majority_tie_rule": "half_credit", "unit": "world",
    "bootstrap_replicates": 5000, "bootstrap_seed": 20261109}
V2_CODECS = ("index", "circuit", "bdd", "dnf")


class AnalysisRefused(SystemExit):
    pass


def check_endpoint(spec: dict) -> None:
    bad = {k: (spec.get(k), v) for k, v in SUPPORTED_ENDPOINT_V2_KEYS.items() if spec.get(k) != v}
    if bad:
        raise AnalysisRefused(f"endpoint spec differs from the supported executable definition: {bad}")


# --------------------------------------------------------------------------- endpoint completeness (iteration 3, R2-05)
#
# A nominal ``ok`` attempt is NOT a scientific outcome until its output reconciles with the planned world and the
# versioned design.  Each output is checked against the world and design REGENERATED from its plan payload:
#   * identity: world_id, family, population, design (byte-equal JSON), design_version, n_queries;
#   * grid: every planned regime x budget cell (and noise rate x noise budget cell) and no unplanned cell;
#   * rows: exactly 8 state + 16 intervention rows per cell, in design order.  Rows carrying ``qid`` (runs from
#     iteration 3 on) must equal the design query digest at their position (distinct by construction).  LEGACY rows
#     (no qid) are matched by fingerprint (kind, horizon, intervention kind, target node, truth recomputed on the
#     regenerated world).  Byte-identical rows for distinct queries are common in saved data, so a duplicated legacy
#     row with the same fingerprint as the row it replaced cannot be detected; this limitation is reported;
#   * values: exact counts (0 <= num <= den, den > 0), p = num/den, tie, majority and verdict derived from the counts,
#     predictions in {0, 1, None}, truth in {0, 1}; an empty version space has the declared empty-row semantics.
# Fatal defects (wrong identity, unplanned/extra rows, malformed values) refuse the analysis.  ABSENT outcomes (a
# missing cell or a short cell) make that cell missing: the world contributes nothing there and the endpoint is
# explicitly incomplete -- never silently averaged over fewer queries, worlds or families.

S2_CELL_SHAPE = {"s2-design-v2": {"state": 8, "intervention": 16}}
PRIMARY_CELL = ("uniform_states", "16")


class OutputDefect(AnalysisRefused):
    pass


def _expected_world_v2(payload: dict):
    from ..experiments.s2 import build_world_v2
    from ..versionspace import predict
    world, design, _inst = build_world_v2(payload)
    queries = [("state", q) for q in design.state_queries] + [("intervention", q) for q in design.intervention_queries]
    exp = [{"kind": k, "qid": q.digest(), "h": q.horizon, "iv": q.intervention.kind, "target_node": q.target.node,
            "truth": int(predict(world.net, q))} for k, q in queries]
    return world, design, exp


def _check_row_values(q: dict, empty: bool, where: str) -> None:
    for k in ("pred", "truth", "verdict", "kind"):
        if k not in q:
            raise OutputDefect(f"{where}: row lacks {k}")
    if q["truth"] not in (0, 1) or isinstance(q["truth"], bool):
        raise OutputDefect(f"{where}: truth {q['truth']!r} not in {{0,1}}")
    if not isinstance(q["pred"], dict) or any(v not in (0, 1, None) or isinstance(v, bool) for v in q["pred"].values()):
        raise OutputDefect(f"{where}: malformed predictions")
    if empty:
        if any(q.get(k) is not None for k in ("p", "num", "den", "vs_majority", "tie")) or \
                q["verdict"] != "inconsistent_evidence_or_class":
            raise OutputDefect(f"{where}: empty version space row carries posterior values")
        return
    try:
        num, den = int(q["num"]), int(q["den"])
    except (TypeError, ValueError, KeyError):
        raise OutputDefect(f"{where}: malformed exact counts {q.get('num')!r}/{q.get('den')!r}") from None
    if str(num) != q["num"] or str(den) != q["den"] or not (0 <= num <= den) or den <= 0:
        raise OutputDefect(f"{where}: invalid exact counts {q['num']}/{q['den']}")
    tie = 2 * num == den
    if q.get("tie") is not tie or q.get("vs_majority") != (None if tie else int(2 * num > den)):
        raise OutputDefect(f"{where}: tie/majority inconsistent with counts {num}/{den}")
    if q.get("p") != num / den:
        raise OutputDefect(f"{where}: p inconsistent with counts")
    if q["verdict"] != ("refuted" if num == 0 else "entailed" if num == den else "underdetermined"):
        raise OutputDefect(f"{where}: verdict inconsistent with counts")


def _match_rows(rows: list[dict], exp: list[dict], where: str) -> tuple[bool, bool]:
    """Returns (complete, legacy).  Raises on identity defects."""
    if len(rows) > len(exp):
        raise OutputDefect(f"{where}: {len(rows)} rows for {len(exp)} planned queries (extra or duplicated rows)")
    has_qid = [("qid" in r) for r in rows]
    if any(has_qid) and not all(has_qid):
        raise OutputDefect(f"{where}: mixed rows with and without query identities")
    legacy = not any(has_qid)
    if not legacy:
        pos = {e["qid"]: i for i, e in enumerate(exp)}
        seen = []
        for r in rows:
            if r["qid"] not in pos:
                raise OutputDefect(f"{where}: query identity {r['qid'][:12]} is not in this world's design")
            seen.append(pos[r["qid"]])
        if len(set(seen)) != len(seen):
            raise OutputDefect(f"{where}: duplicated query identity")
        if seen != sorted(seen):
            raise OutputDefect(f"{where}: rows out of design order")
        for r in rows:
            e = exp[pos[r["qid"]]]
            if any(r.get(k) != e[k] for k in ("kind", "h", "iv", "target_node", "truth")):
                raise OutputDefect(f"{where}: row fields disagree with its query identity")
        return len(rows) == len(exp), False
    # legacy: order-preserving fingerprint match (exact positional match when the cell is full)
    fp = ("kind", "h", "iv", "target_node", "truth")
    j = 0
    for r in rows:
        while j < len(exp) and any(r.get(k) != exp[j][k] for k in fp):
            if len(rows) == len(exp):
                raise OutputDefect(f"{where}: row {j} does not match the planned query at that position")
            j += 1
        if j == len(exp):
            raise OutputDefect(f"{where}: a row matches no remaining planned query (wrong identity or duplicate)")
        j += 1
    return len(rows) == len(exp), True


def validate_world_v2(item_id: str, payload: dict, out: dict) -> dict:
    """Reconcile one ok S2 output with its planned world and design.  Returns
    {cells: {(regime_or_noise, budget): "complete" | "missing" | "short"}, legacy_rows, primary_complete}."""
    w = f"{item_id}"
    dv = payload.get("design_version")
    if dv not in S2_CELL_SHAPE or out.get("design_version") != dv:
        raise OutputDefect(f"{w}: design version {out.get('design_version')!r} (planned {dv!r})")
    world, design, exp = _expected_world_v2(payload)
    ow = out.get("world", {})
    if ow.get("world_id") != world.world_id or ow.get("family") != payload["family"] or \
            ow.get("population") != payload["population"]:
        raise OutputDefect(f"{w}: world identity differs from the planned world")
    if out.get("design") != json.loads(json.dumps(design.to_json())):
        raise OutputDefect(f"{w}: design differs from the regenerated design")
    shape = S2_CELL_SHAPE[dv]
    if [e["kind"] for e in exp].count("state") != shape["state"] or out.get("n_queries") != len(exp):
        raise OutputDefect(f"{w}: query count differs from the design shape")
    planned = {(rg, str(B)) for rg in payload["regimes"] for B in payload["budgets"]}
    planned |= {(f"noise{rate}", str(B)) for rate in payload.get("noise_rates", []) for B in payload.get("noise_budgets", [])}
    present = {(rg, B): c for rg, byb in out.get("regimes", {}).items() for B, c in byb.items()}
    for rate, nz in out.get("noise", {}).items():
        present.update({(f"noise{rate}", B): c for B, c in nz.get("budgets", {}).items()})
    if extra := sorted(set(present) - planned):
        raise OutputDefect(f"{w}: unplanned cells {extra[:4]}")
    cells, legacy_any = {}, False
    for key in sorted(planned):
        c = present.get(key)
        if c is None:
            cells[key] = "missing"
            continue
        where = f"{w}[{key[0]}|B{key[1]}]"
        rows = c.get("queries", [])
        if not isinstance(c.get("empty"), bool):
            raise OutputDefect(f"{where}: malformed empty flag")
        for q in rows:
            _check_row_values(q, c["empty"], where)
        complete, legacy = _match_rows(rows, exp, where)
        legacy_any |= legacy
        cells[key] = "complete" if complete else "short"
    return {"cells": cells, "legacy_rows": legacy_any, "primary_complete": cells.get(PRIMARY_CELL) == "complete"}


def _drop_incomplete_cells(out: dict, cells: dict) -> dict:
    """Copy of an output without its missing/short cells (they contribute no scores anywhere)."""
    bad = {k for k, v in cells.items() if v != "complete"}
    if not bad:
        return out
    o = dict(out)
    o["regimes"] = {rg: {B: c for B, c in byb.items() if (rg, B) not in bad} for rg, byb in out["regimes"].items()}
    if "noise" in out:
        o["noise"] = {rate: {**nz, "budgets": {B: c for B, c in nz["budgets"].items() if (f"noise{rate}", B) not in bad}}
                      for rate, nz in out["noise"].items()}
    return o


def load_v2(run_dirs: list[Path]) -> tuple[list[dict], dict]:
    """Strictly load v2 S2 runs; validate every ok output against its planned world/design; return
    (records with item ids, accounting).  Records keep only complete cells."""
    from ..runner import load_run
    if len({str(Path(d).resolve()) for d in run_dirs}) != len(run_dirs):
        raise AnalysisRefused("duplicate run arguments")
    recs, acct, seen_items, seen_worlds = [], {"runs": {}, "items": {}, "phases": set()}, set(), {}
    for d in run_dirs:
        lr = load_run(Path(d))
        if lr["layout"] != "v2":
            raise AnalysisRefused(f"{d}: v1 layout; use the historical analysis")
        plan = lr["plan"]
        acct["phases"].add(lr["phase"])
        planned = {e["item_id"]: e for e in plan["items"]}
        fails = {k: {"status": v["status"], "error": str(v["output"].get("error"))[:200], **planned[k]["strata"]}
                 for k, v in lr["failures"].items()}
        missing = [{"item_id": k, **planned[k]["strata"]} for k in lr["missing"]]
        incomplete_out = {}
        legacy = 0
        for iid, e in planned.items():
            if iid in seen_items:
                raise AnalysisRefused(f"item {iid} appears in more than one run (ambiguous rerun combination)")
            seen_items.add(iid)
            st = "failed" if iid in lr["failures"] else "missing" if iid not in lr["results"] else None
            info = {"status": st, "strata": e["strata"], "run_id": plan["run_id"]}
            if st is None:
                out = lr["results"][iid]
                v = validate_world_v2(iid, e["payload"], out)
                legacy += v["legacy_rows"]
                bad = {f"{a}|B{b}": c for (a, b), c in v["cells"].items() if c != "complete"}
                info.update(status="ok_complete_grid" if not bad else "ok_incomplete_grid",
                            primary_cell_complete=v["primary_complete"], incomplete_cells=bad)
                if bad:
                    incomplete_out[iid] = bad
                wid = out["world"]["world_id"]
                if wid in seen_worlds:
                    raise AnalysisRefused(f"world {wid} appears twice ({seen_worlds[wid]}, {iid})")
                seen_worlds[wid] = iid
                recs.append({"item_id": iid, "run_id": plan["run_id"], "strata": e["strata"],
                             **_drop_incomplete_cells(out, v["cells"])})
            acct["items"][iid] = info
        acct["runs"][plan["run_id"]] = {"plan_sha256": plan["plan_sha256"], "planned": len(planned),
                                        "ok": len(lr["results"]), "failed": len(fails), "missing": len(missing),
                                        "ok_with_incomplete_grid": len(incomplete_out),
                                        "ok_outputs_with_legacy_rows(no qid)": legacy,
                                        "execution_status": lr["execution_status"]["status"], "phase": lr["phase"],
                                        "attempts_total": lr["attempts_total"],
                                        "superseded_failed_attempts": lr["superseded_failures"],
                                        "failures": fails, "missing_items": missing,
                                        "incomplete_outputs": incomplete_out,
                                        "source_tree_sha256": plan["source_tree_sha256"],
                                        "endpoint": plan.get("endpoint", {}).get("sha256")}
        acct.setdefault("plans", {})[plan["run_id"]] = plan
    return recs, acct


def completeness_v2(items: dict, spec: dict) -> dict:
    """Planned / complete / failed / missing accounting, separately for the structured primary, the required
    uniform-H null (B16 intervention cell) and the whole planned study grid."""
    def block(sel, cell_key):
        ids = [i for i, x in items.items() if sel(x)]
        st = {"planned": len(ids), "complete": 0, "failed": 0, "missing_attempt": 0, "ok_but_endpoint_cell_absent": 0}
        by_fam: dict = {}
        for i in ids:
            x = items[i]
            f = x["strata"].get("family")
            bf = by_fam.setdefault(f, {"planned": 0, "complete": 0})
            bf["planned"] += 1
            if x["status"] == "failed":
                st["failed"] += 1
            elif x["status"] == "missing":
                st["missing_attempt"] += 1
            elif x.get(cell_key):
                st["complete"] += 1
                bf["complete"] += 1
            else:
                st["ok_but_endpoint_cell_absent"] += 1
        st["by_family"] = by_fam
        st["status"] = ("not_planned" if not ids else "complete" if st["complete"] == len(ids) else "incomplete")
        return st
    prim = block(lambda x: x["strata"].get("label") == "realizable" and x["strata"].get("family") in spec["families"],
                 "primary_cell_complete")
    missing_fams = [f for f in spec["families"] if f not in prim["by_family"]]
    if missing_fams:
        prim["status"] = "incomplete"
        prim["families_not_planned"] = missing_fams
    null = block(lambda x: x["strata"].get("label") == spec["required_null"]["population"]
                 and x["strata"].get("family") == spec["required_null"]["family"], "primary_cell_complete")
    allst = {"planned_items": len(items),
             "ok_complete_grid": sum(x["status"] == "ok_complete_grid" for x in items.values()),
             "ok_incomplete_grid": sum(x["status"] == "ok_incomplete_grid" for x in items.values()),
             "failed": sum(x["status"] == "failed" for x in items.values()),
             "missing_attempt": sum(x["status"] == "missing" for x in items.values())}
    allst["status"] = ("complete" if allst["ok_complete_grid"] == len(items) and prim["status"] == "complete"
                       and null["status"] == "complete" else "incomplete")
    return {"structured_primary": prim, "required_null": null, "overall_study": allst,
            "rule": ("an ok attempt counts toward an endpoint only if its planned cell reconciles exactly with the "
                     "regenerated world and design; absent cells/queries are missing outcomes, never averaged away. "
                     "A structured estimate can be reported while the null is unfinished, but the study is then "
                     "incomplete.")}


def _acc(q: dict, method: str) -> float:
    if method == "vs_majority":
        if q["vs_majority"] is None and not q.get("tie"):
            return 0.0
        return 0.5 if q["tie"] else float(q["vs_majority"] == q["truth"])
    if method == "uniform":
        return 0.0 if q["p"] is None else (q["p"] if q["truth"] else 1 - q["p"])
    if method == "observed_majority":
        return float(q["observed_majority"] == q["truth"])
    v = q["pred"].get(method)
    return 0.0 if v is None else float(v == q["truth"])


V2_METHODS = V2_CODECS + ("vs_majority", "uniform", "observed_majority")


def world_scores(qs: list[dict], methods=V2_METHODS) -> dict:
    out = {"n_queries": len(qs)}
    if not qs:
        return out
    for m in methods:
        if m in qs[0]["pred"] or m in ("vs_majority", "uniform", "observed_majority"):
            out[m] = float(np.mean([_acc(q, m) for q in qs]))
    out["ties"] = sum(1 for q in qs if q.get("tie"))
    out["truth_prevalence"] = float(np.mean([q["truth"] for q in qs]))
    ans = [q for q in qs if q["verdict"] in ("entailed", "refuted")]
    out["consensus_coverage"] = len(ans) / len(qs)
    out["consensus_wrong_hidden"] = sum((q["verdict"] == "entailed") != bool(q["truth"]) for q in ans) / len(qs)
    und = [q for q in qs if q["verdict"] == "underdetermined"]
    out["n_underdetermined"] = len(und)
    return out


def per_world_table_v2(recs: list[dict]) -> list[dict]:
    rows = []
    for r in recs:
        w = r["world"]
        base = {"world_id": w["world_id"], "item_id": r["item_id"], "run_id": r["run_id"], "family": w["family"],
                "population": w["population"], "label": r["strata"].get("label", w["population"]),
                "realizable": w["realizable"]}
        for regime, byb in r["regimes"].items():
            for B, res in byb.items():
                for kind in ("intervention", "state"):
                    qs = [q for q in res["queries"] if q["kind"] == kind]
                    rows.append({**base, "regime": regime, "budget": int(B), "kind": kind, "subset": "all",
                                 "empty_vs": res["empty"], "log10_vs": res["log10_vs"], **world_scores(qs)})
                    if kind == "intervention" and B == "16":
                        for sub, sel in (("h1", lambda q: q["h"] == 1), ("h>1", lambda q: q["h"] > 1)):
                            rows.append({**base, "regime": regime, "budget": 16, "kind": kind, "subset": sub,
                                         "empty_vs": res["empty"], **world_scores([q for q in qs if sel(q)])})
                        for cat in ("h1_observed_transition", "h1_novel_input", "multistep_interpolation",
                                    "multistep_unobserved"):
                            sq = [q for q in qs if q["novelty"]["category"] == cat]
                            if sq:
                                rows.append({**base, "regime": regime, "budget": 16, "kind": kind,
                                             "subset": f"novelty:{cat}", "empty_vs": res["empty"], **world_scores(sq)})
        for rate, nz in r.get("noise", {}).items():
            for B, res in nz["budgets"].items():
                qs = [q for q in res["queries"] if q["kind"] == "intervention"]
                sc = world_scores(qs, V2_METHODS + tuple(f"mdl_two_part_{c}" for c in V2_CODECS))
                rows.append({**base, "regime": f"uniform_states+noise{rate}", "budget": int(B), "kind": "intervention",
                             "subset": "all", "empty_vs": res["empty"], **sc})
    return rows


def _contrast(rows, a, b, reps, seed=20261109):
    sel = [r for r in rows if a in r and b in r]
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
            "per_family": {str(f): {"mean_delta": float(d[s == f].mean()), "n": int((s == f).sum())}
                           for f in np.unique(s)}}


def _sel(rows, **kw):
    return [r for r in rows if all(r.get(k) == v for k, v in kw.items())]


def mc_diagnostic_summary(run_dir: Path) -> dict:
    """Summarise the predeclared MC-majority convergence diagnostic against the exact posterior."""
    from ..runner import load_run
    lr = load_run(Path(run_dir))
    res = list(lr["results"].values())
    budgets = lr["plan"]["config"]["mc_budgets"]
    out = {"run_id": lr["plan"]["run_id"], "worlds": len(res), "failed": len(lr["failures"]),
           "missing": len(lr["missing"]), "by_population": {}}
    for pop in ("realizable", "null"):
        ws = [r for r in res if r["population"] == pop and not r["empty"]]
        if not ws:
            continue
        exact_tie = sum(q["tie_exact"] for w in ws for q in w["queries"])
        nq = sum(len(w["queries"]) for w in ws)
        entry = {"worlds": len(ws), "queries": nq, "exact_ties": exact_tie, "budgets": {}}
        fam = np.array([w["family"] for w in ws])

        def wacc(q, maj, tie):
            return 0.5 if tie else float(maj == q["truth"])
        exact_delta = np.array([np.mean([q["index_pred"] == q["truth"] for q in w["queries"]])
                                - np.mean([wacc(q, q["maj_exact"], q["tie_exact"]) for q in w["queries"]]) for w in ws])
        exact_mean = stratified_mean(exact_delta, fam)
        for M in budgets:
            reps = len(ws[0]["queries"][0]["mc"][str(M)])
            perr, flips, flips_tie, mc_ties, near = [], 0, 0, 0, 0
            sens = []
            for r in range(reps):
                dm = []
                for w in ws:
                    accs = []
                    for q in w["queries"]:
                        m = q["mc"][str(M)][r]
                        perr.append(abs(m["p"] - q["p_exact"]))
                        mc_ties += m["tie"]
                        se = math.sqrt(max(q["p_exact"] * (1 - q["p_exact"]), 1e-300) / M)
                        near += abs(q["p_exact"] - 0.5) < 2 * se
                        if (m["majority"] if not m["tie"] else "tie") != (q["maj_exact"] if not q["tie_exact"] else "tie"):
                            flips += 1
                            if q["tie_exact"]:
                                flips_tie += 1
                        accs.append(wacc(q, m["majority"], m["tie"]))
                    dm.append(np.mean([q["index_pred"] == q["truth"] for q in w["queries"]]) - np.mean(accs))
                sens.append(stratified_mean(np.array(dm), fam) - exact_mean)
            tot = nq * reps
            entry["budgets"][str(M)] = {"reps": reps, "mean_abs_prob_error": float(np.mean(perr)),
                                        "max_abs_prob_error": float(np.max(perr)),
                                        "near_tie_fraction(|p-1/2|<2SE_M)": near / tot,
                                        "decision_flip_fraction": flips / tot, "mc_tie_fraction": mc_ties / tot,
                                        "flips_at_exact_ties": flips_tie, "flips_at_non_ties": flips - flips_tie,
                                        "decision_flip_fraction_non_ties": (flips - flips_tie)
                                        / max(1, tot - exact_tie * reps),
                                        "world_contrast_sensitivity_per_rep": [float(x) for x in sens],
                                        "max_abs_contrast_sensitivity": float(np.max(np.abs(sens)))}
        entry["exact_index_minus_majority"] = exact_mean
        out["by_population"][pop] = entry
    out["policy"] = ("primary comparator uses the EXACT integer-count posterior; MC is not used. The diagnostic "
                     "quantifies what a finite-sample MC majority (as in v1) would have changed.")
    return out


def analyze_v2(run_dirs: list[Path], out_dir: Path, endpoint_path: Path, mc_run: Path | None = None,
               reps_primary: int = 5000, reps_secondary: int = 2000, development_sizing: bool | None = None,
               analysis_version: str = "s2-analysis-v3") -> dict:
    """``development_sizing``: prospective sizing from development deltas.  Default: only for development-phase
    runs; explicitly requesting it for fixture/confirmatory runs is refused (no re-sizing from final outcomes)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ep_bytes = Path(endpoint_path).read_bytes()
    spec = json.loads(ep_bytes)
    check_endpoint(spec)
    ep_sha = hashlib.sha256(ep_bytes).hexdigest()
    recs, acct = load_v2([Path(d) for d in run_dirs])
    for rid, a in acct["runs"].items():
        if a["endpoint"] not in (None, ep_sha):
            raise AnalysisRefused(f"run {rid} was planned under a different endpoint spec ({a['endpoint']})")
    phases = acct.pop("phases")
    if len(phases) != 1:
        raise AnalysisRefused(f"runs of different phases cannot be analysed together: {sorted(phases)}")
    phase = phases.pop()
    if development_sizing is None:
        development_sizing = phase == "development"
    elif development_sizing and phase != "development":
        raise AnalysisRefused("prospective sizing is a development-only action; refused for a "
                              f"{phase} analysis (no re-sizing from final outcomes)")
    acct.pop("plans")
    items = acct.pop("items")
    rows = per_world_table_v2(recs)
    result = {"analysis_version": analysis_version, "phase": phase,
              "endpoint": {"path": str(endpoint_path), "sha256": ep_sha, "spec": spec},
              "runs": acct["runs"], "semantics_changed_from_v1": [
                  "primary contrast index - vs_majority (v1: index - uniform)",
                  "exact integer-count posterior (v1: Monte Carlo for large multistep version spaces)",
                  "majority ties score 0.5 (v1: tie -> predict 0)",
                  "exogenous design s2-design-v2 (v1: holdouts and query redraws depended on hidden trajectories)",
                  "strict plan reconciliation and failure accounting (v1: concatenated records, failures ignored)"],
              "changes_in_v3": [
                  "every ok output reconciled with its regenerated world and design before scoring (R2-05)",
                  "absent cells/queries are missing outcomes; structured primary, required null and overall study "
                  "completeness reported separately",
                  "phase (development/fixture/confirmatory) derived from validated run provenance",
                  "prospective sizing only for development-phase analyses"]}
    comp = completeness_v2(items, spec)
    result["completeness"] = comp
    # ---------------- terminal accounting for the primary population
    pc = comp["structured_primary"]
    prim_ids = [i for i, x in items.items() if x["strata"].get("label") == "realizable"
                and x["strata"].get("family") in spec["families"]]
    unresolved = [i for i in prim_ids if not items[i].get("primary_cell_complete")]
    result["primary_terminal_accounting"] = {"planned_worlds": pc["planned"], "ok_worlds": pc["complete"],
                                             "unresolved_worlds": unresolved,
                                             "complete": pc["status"] == "complete"}
    base = dict(regime="uniform_states", budget=16, kind="intervention", subset="all")
    prim = [r for r in _sel(rows, label="realizable", **base) if r["family"] in spec["families"]]
    fam_done = {f: sum(1 for r in prim if r["family"] == f) for f in spec["families"]}
    absent_fams = [f for f in spec["families"] if fam_done[f] == 0]
    if prim and not absent_fams:
        result["primary"] = _contrast(prim, "index", "vs_majority", reps_primary)
    else:
        result["primary"] = {"a": "index", "b": "vs_majority", "estimate": None, "ci95": None,
                             "n_worlds": len(prim), "families_without_completed_worlds": absent_fams,
                             "note": "not estimable under equal family weighting; no family is dropped or reweighted"}
    if pc["status"] != "complete":
        result["primary"]["status"] = f"INCOMPLETE ({phase}): planned-N claim not issued"
        n_f = {f: pc["by_family"].get(f, {}).get("planned", 0) for f in spec["families"]}
        if all(n_f.values()):
            bounds = {}
            for name, fill in (("worst", -1.0), ("best", 1.0)):
                vals = []
                for f in spec["families"]:
                    d = [r["index"] - r["vs_majority"] for r in prim if r["family"] == f]
                    vals.append((sum(d) + fill * (n_f[f] - len(d))) / n_f[f])
                bounds[name] = float(np.mean(vals))
            result["primary"]["missing_outcome_bounds"] = bounds
            result["primary"]["missing_outcome_bounds_rule"] = ("each missing world scored -1 (worst) or +1 (best) "
                                                                "within its family; equal family weights")
        else:
            result["primary"]["missing_outcome_bounds"] = None
    else:
        result["primary"]["status"] = f"complete ({phase})" + ("; not confirmatory" if phase != "confirmatory" else "")
    result["required_null_status"] = comp["required_null"]["status"]
    result["overall_study_status"] = comp["overall_study"]["status"]
    result["primary_complete_case"] = _contrast([r for r in prim if not r["empty_vs"]], "index", "vs_majority",
                                                reps_primary)
    # ---------------- historical and named secondaries (structured realizable)
    sec = {"HISTORICAL_v1_primary|index-uniform": _contrast(prim, "index", "uniform", reps_secondary),
           "circuit-vs_majority": _contrast(prim, "circuit", "vs_majority", reps_secondary),
           "index-circuit": _contrast(prim, "index", "circuit", reps_secondary),
           "vs_majority-uniform": _contrast(prim, "vs_majority", "uniform", reps_secondary),
           "bdd-vs_majority": _contrast(prim, "bdd", "vs_majority", reps_secondary),
           "dnf-vs_majority": _contrast(prim, "dnf", "vs_majority", reps_secondary)}
    for sub in ("h1", "h>1", "novelty:h1_observed_transition", "novelty:h1_novel_input",
                "novelty:multistep_interpolation", "novelty:multistep_unobserved"):
        rr = [r for r in _sel(rows, label="realizable", regime="uniform_states", budget=16, kind="intervention",
                              subset=sub) if r["family"] in spec["families"]]
        sec[f"subset[{sub}]|index-vs_majority"] = _contrast(rr, "index", "vs_majority", reps_secondary)
        sec[f"subset[{sub}]|circuit-vs_majority"] = _contrast(rr, "circuit", "vs_majority", reps_secondary)
        sec[f"subset[{sub}]|n_queries_total"] = int(sum(r["n_queries"] for r in rr))
    for B in (4, 8, 32):
        rr = [r for r in _sel(rows, label="realizable", regime="uniform_states", budget=B, kind="intervention",
                              subset="all") if r["family"] in spec["families"]]
        sec[f"B{B}|index-vs_majority"] = _contrast(rr, "index", "vs_majority", reps_secondary)
    for regime in ("observational", "clamp_interventions", "active"):
        rr = [r for r in _sel(rows, label="realizable", regime=regime, budget=16, kind="intervention", subset="all")
              if r["family"] in spec["families"]]
        sec[f"{regime}|B16|index-vs_majority"] = _contrast(rr, "index", "vs_majority", reps_secondary)
    st = [r for r in _sel(rows, label="realizable", regime="uniform_states", budget=16, kind="state", subset="all")
          if r["family"] in spec["families"]]
    sec["STATE-holdout|B16|index-vs_majority"] = _contrast(st, "index", "vs_majority", reps_secondary)
    result["secondary_exploratory"] = sec
    # ---------------- mandatory uniform-H null
    null = {}
    for B in (4, 8, 16, 32):
        nr = _sel(rows, label="null", regime="uniform_states", budget=B, kind="intervention", subset="all")
        for a, b in (("index", "vs_majority"), ("index", "uniform"), ("circuit", "vs_majority"),
                     ("vs_majority", "uniform"), ("index", "circuit")):
            null[f"B{B}|{a}-{b}"] = _contrast(nr, a, b, reps_secondary)
    for sub in ("h1", "h>1"):
        nr = _sel(rows, label="null", regime="uniform_states", budget=16, kind="intervention", subset=sub)
        null[f"B16|subset[{sub}]|index-vs_majority"] = _contrast(nr, "index", "vs_majority", reps_secondary)
    result["null_uniform_H"] = null
    # structured - null (EXPLORATORY interaction; world-level, independent samples)
    nrows = _sel(rows, label="null", **base)
    if prim and nrows:
        ds = np.array([r["index"] - r["vs_majority"] for r in prim])
        sfam = np.array([r["family"] for r in prim])
        dn = np.array([r["index"] - r["vs_majority"] for r in nrows])
        rng = np.random.default_rng(20261110)
        boots = []
        idx = {f: np.nonzero(sfam == f)[0] for f in np.unique(sfam)}
        for _ in range(reps_secondary):
            sm = np.mean([ds[ix[rng.integers(0, len(ix), len(ix))]].mean() for ix in idx.values()])
            nm = dn[rng.integers(0, len(dn), len(dn))].mean()
            boots.append(sm - nm)
        est = stratified_mean(ds, sfam) - dn.mean()
        result["EXPLORATORY_structured_minus_null|index-vs_majority"] = {
            "estimate": float(est), "ci95": [float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))],
            "replicates": reps_secondary}
    # ---------------- stress populations (descriptive)
    stress = {}
    for lab in ("misspecified", "shift"):
        rr = _sel(rows, label=lab, **base)
        if rr:
            stress[f"{lab}|index-vs_majority(missing=0)"] = _contrast(rr, "index", "vs_majority", reps_secondary)
            stress[f"{lab}|empty_vs_rate"] = float(np.mean([r["empty_vs"] for r in rr]))
    noise = []
    for rate in ("0.01", "0.05", "0.1"):
        for B in (16, 32, 64):
            rr = _sel(rows, regime=f"uniform_states+noise{rate}", budget=B)
            if not rr:
                continue
            s = np.array([r["family"] for r in rr])
            e = {"rate": float(rate), "budget": B, "n_worlds": len(rr),
                 "exact_vs_empty_rate": float(np.mean([r["empty_vs"] for r in rr]))}
            for m in tuple(f"mdl_two_part_{c}" for c in V2_CODECS) + ("index", "vs_majority"):
                e[m] = stratified_mean(np.array([r[m] for r in rr]), s)
            noise.append(e)
    stress["noise_two_part_mdl_all_codes"] = noise
    stress["note"] = ("descriptive; noisy two-part MDL is computed for every selection code under the identical "
                      "residual code and budget, so index-specific robustness is assessed against matched codes")
    result["stress_descriptive"] = stress
    # ---------------- curves (stratified means) for figures
    curves = []
    for lab in ("realizable", "null", "misspecified", "shift"):
        for regime in ("uniform_states", "observational", "clamp_interventions", "active"):
            for B in (2, 4, 8, 16, 32, 64):
                rr = [r for r in _sel(rows, label=lab, regime=regime, budget=B, kind="intervention", subset="all")]
                if not rr:
                    continue
                s = np.array([r["family"] for r in rr])
                c = {"label": lab, "regime": regime, "budget": B, "n_worlds": len(rr)}
                for m in V2_METHODS + ("consensus_coverage", "consensus_wrong_hidden", "truth_prevalence"):
                    c[m] = stratified_mean(np.array([r[m] for r in rr]), s)
                curves.append(c)
    result["curves"] = curves
    # ---------------- exactness bookkeeping
    sat_q = sum(len([q for q in r["regimes"]["uniform_states"]["16"]["queries"]])
                for r in recs if r["regimes"].get("uniform_states", {}).get("16", {}).get("sat_crosscheck"))
    sat_mm = sum(r["regimes"]["uniform_states"]["16"]["sat_mismatches"] for r in recs
                 if r["regimes"].get("uniform_states", {}).get("16", {}).get("sat_crosscheck"))
    result["exact_verdict_vs_sat_B16"] = {"queries": sat_q, "mismatches": sat_mm}
    result["ties"] = {"primary_queries": int(sum(r["n_queries"] for r in prim)),
                      "primary_exact_ties": int(sum(r["ties"] for r in prim)),
                      "null_exact_ties": int(sum(r["ties"] for r in nrows))}
    # ---------------- overlap audit of the null against structured development worlds (reported; no exclusion)
    from ..dedup import canonical_form
    from ..schema import Network
    sforms = {canonical_form(Network.from_json(r["world"]["network"])) for r in recs
              if r["strata"].get("label") != "null"}
    nforms = [canonical_form(Network.from_json(r["world"]["network"])) for r in recs if r["strata"].get("label") == "null"]
    result["null_overlap_audit"] = {"null_worlds": len(nforms),
                                    "isomorphic_to_a_structured_dev_world": sum(f in sforms for f in nforms),
                                    "within_null_isomorphic_duplicates": len(nforms) - len(set(nforms)),
                                    "rule": "IID null draws retained; overlap audited and reported only"}
    if mc_run:
        result["mc_diagnostic"] = mc_diagnostic_summary(Path(mc_run))
    # ---------------- sizing for the revised endpoint (development deltas only)
    if not development_sizing:
        result["design_simulation_note"] = f"prospective sizing not run ({phase} analysis; development-only action)"
    if development_sizing and prim:
        d = np.array([r["index"] - r["vs_majority"] for r in prim])
        s = np.array([r["family"] for r in prim])
        result["design_simulation_revised_primary"] = design_simulation(d, s, sims=2000, effect=0.05)
    if development_sizing and nrows:
        d = np.array([r["index"] - r["vs_majority"] for r in nrows])
        result["design_simulation_null_index_minus_majority"] = design_simulation(
            d, np.array(["null"] * len(d)), sims=2000, effect=0.05,
            n_grid=(200, 400, 600, 800, 1000, 1200, 1500, 2000))
    # ---------------- write
    with (out_dir / "s2_v2_per_world.csv").open("w", newline="") as fh:
        keys = sorted({k for r in rows for k in r})
        wr = csv.DictWriter(fh, keys)
        wr.writeheader()
        for r in rows:
            wr.writerow(r)
    (out_dir / "s2_v2_summary.json").write_text(json.dumps(result, indent=1, sort_keys=True, default=float))
    digest = hashlib.sha256((out_dir / "s2_v2_summary.json").read_bytes()).hexdigest()
    try:
        _figures_v2(rows, result, out_dir, spec)
    except Exception as e:  # figures optional; numbers are in the JSON
        result["figure_error"] = repr(e)
    return {"primary": result["primary"], "accounting": result["primary_terminal_accounting"],
            "completeness": comp, "phase": phase,
            "summary": str(out_dir / "s2_v2_summary.json"), "digest": digest}


def _figures_v2(rows, result, out_dir: Path, spec: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5), sharey=True)
    rng = np.random.default_rng(0)
    groups = [(f, "realizable") for f in spec["families"]] + [("uniform_H", "null")]
    for ax, (a, b) in zip(axes, (("index", "vs_majority"), ("index", "uniform"), ("circuit", "vs_majority"))):
        for k, (f, lab) in enumerate(groups):
            d = np.array([r[a] - r[b] for r in _sel(rows, label=lab, regime="uniform_states", budget=16,
                                                     kind="intervention", subset="all") if r["family"] == f])
            if not len(d):
                continue
            ax.scatter(k + rng.uniform(-0.25, 0.25, len(d)), d, s=6, alpha=0.5,
                       color="tab:red" if lab == "null" else "tab:blue")
            ax.plot([k - 0.3, k + 0.3], [d.mean()] * 2, color="k", lw=2)
        ax.axhline(0, color="gray", lw=0.8)
        ax.set_xticks(range(len(groups)))
        ax.set_xticklabels([g[0].replace("_", "\n") for g in groups], fontsize=8)
        ax.set_title(f"per-world {a} - {b} (B16, 16 intervention queries)", fontsize=9)
    axes[0].set_ylabel("per-world accuracy difference")
    fig.suptitle(f"S2 {result['phase'].upper()} (exogenous design, exact majority). Blue: structured; red: "
                 "uniform-H null. Bars = means. Every world shown.", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_dir / "s2_v2_per_world_deltas.png", dpi=130)
    plt.close(fig)
    cv = [c for c in result["curves"] if c["regime"] == "uniform_states"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, lab in zip(axes, ("realizable", "null")):
        sel = sorted([c for c in cv if c["label"] == lab], key=lambda c: c["budget"])
        if not sel:
            continue
        xs = [c["budget"] for c in sel]
        for m, col in (("index", "#1f77b4"), ("circuit", "#ff7f0e"), ("vs_majority", "#d62728"),
                       ("uniform", "#7f7f7f"), ("observed_majority", "#bcbd22")):
            ax.plot(xs, [c[m] for c in sel], marker="o", ms=3, label=m, color=col)
        ax.set_xscale("log", base=2)
        ax.set_title(f"{lab}: uniform designed measurements (n={sel[0]['n_worlds']})", fontsize=9)
        ax.set_xlabel("evidence budget")
    axes[0].set_ylabel("hidden intervention accuracy")
    if axes[0].get_legend_handles_labels()[0]:
        axes[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out_dir / "s2_v2_accuracy_vs_budget.png", dpi=130)
    plt.close(fig)


def historical_exact_majority_v1(run_ids: list[str], reps: int = 2000) -> dict:
    """Re-score the iteration-1 S2 runs (v1 design, v1 records) with the EXACT compatible-set posterior at the
    v1 primary cell (uniform_states, B16, intervention queries), regenerating the public evidence with the
    historical v1 generator.  Quantifies what the v1 Monte Carlo majority changed.  The v1 design itself
    (mechanism-dependent holdouts/redraws, R02) is NOT repaired by this re-scoring."""
    from ..generators import make_s2_instance, make_s2_world
    from ..schema import Evidence, HypothesisClass
    from ..versionspace import build_version_space, exact_posterior
    rows, mismatch_truth, prob_err, mc_q, flips = [], 0, [], 0, 0
    for rid in run_ids:
        for r in read_jsonl(ROOT / "runs" / rid / "records.jsonl"):
            w = r["world"]
            if w["population"] != "realizable" or w["world_id"] in ():
                continue
            if "noise" in r:
                continue
            world = make_s2_world("dev-v1", int(r["item_id"].split("|")[-1]), w["family"], w["population"], 7, 3)
            assert world.world_id == w["world_id"]
            inst = make_s2_instance(world)
            ev = Evidence(7, tuple(inst.evidence["uniform_states"][:16]), "uniform_states")
            vs = build_version_space(ev, HypothesisClass(7, 3))
            qrows = [q for q in r["regimes"]["uniform_states"]["16"]["queries"] if q["kind"] == "intervention"]
            acc = {"index": [], "mc_v1": [], "exact_half": [], "exact_tie0": []}
            for q, rec in zip(inst.intervention_queries, qrows):
                ex = exact_posterior(vs, q)
                t = rec["truth"]
                mismatch_truth += int(predict_truth(world, q) != t)
                prob_err.append(abs(ex["p"] - rec["p_uniform"]))
                mc_q += rec.get("uniform_method") == "monte_carlo"
                mcmaj = int(rec["p_uniform"] > 0.5)
                exm = ex["majority"]
                flips += int((mcmaj if rec["p_uniform"] != 0.5 else "tie") != (exm if not ex["tie"] else "tie"))
                acc["index"].append(int(rec["pred"]["index"] == t))
                acc["mc_v1"].append(int(mcmaj == t))
                acc["exact_half"].append(0.5 if ex["tie"] else int(exm == t))
                acc["exact_tie0"].append(int((0 if ex["tie"] else exm) == t))
            rows.append({"family": w["family"], **{k: float(np.mean(v)) for k, v in acc.items()},
                         "ties": sum(1 for q in inst.intervention_queries if exact_posterior(vs, q)["tie"])})
    fam = np.array([r["family"] for r in rows])
    out = {"worlds": len(rows), "truth_mismatches": mismatch_truth, "queries": len(prob_err),
           "queries_mc_in_v1": mc_q, "mean_abs_prob_error_v1_mc": float(np.mean(prob_err)),
           "max_abs_prob_error_v1_mc": float(np.max(prob_err)), "majority_decision_flips": flips,
           "exact_ties": int(sum(r["ties"] for r in rows))}
    for comp in ("mc_v1", "exact_half", "exact_tie0"):
        d = np.array([r["index"] - r[comp] for r in rows])
        br = paired_cluster_bootstrap(d, fam, replicates=reps, seed=20261109)
        out[f"index-{comp}"] = {"estimate": br.estimate, "ci95": [br.lo, br.hi], "n_worlds": br.n_worlds}
    return out


def predict_truth(world, q) -> int:
    from ..versionspace import predict
    return int(predict(world.net, q))
