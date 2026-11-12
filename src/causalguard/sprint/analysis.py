"""R7 sprint analysis: ONE command over a list of runs (adding the online models tomorrow = two more --run-dir).

  python -m causalguard sprint-analyze --run-dir runs/<a> --run-dir runs/<b> ... --out reports/sprint_local \
      [--label pilot] [--manifest artifacts/sprint_main_manifest.json]

Writes <out>/analysis.json, <out>/RESULTS.md and figures <out>/fig_*.png.  Deterministic: no timestamps, sorted
keys, fixed bootstrap seed, PNG metadata stripped; regenerating from the same raw runs is byte-identical.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from . import population as P
from . import scoring as S

S_FIELDS = ("overclaim", "underclaim", "wrong_settled", "accuracy", "prob_mae", "brier", "brier_pstar",
            "incoherent", "incoherent_tol05")
P_SCORES = [("capitulation_named", ("P0", "P1")), ("capitulation_all", ("P0", "P2")),
            ("forced_overclaim", ("P0", "P2")), ("repair_named", ("P0", "P3")),
            ("collateral", ("P0", "P1", "P3")), ("changed_any", ("P0", "P1", "P2", "P3")),
            ("overclaim_t2", ("P0", "P1", "P2", "P3"))]
WORDS = {"entailed": "true", "refuted": "false", "underdetermined": "not settled"}


def _r(x, nd=4):
    if isinstance(x, float):
        return round(x, nd)
    if isinstance(x, dict):
        return {k: _r(v, nd) for k, v in x.items()}
    if isinstance(x, list):
        return [_r(v, nd) for v in x]
    return x


def load(run_dirs: list[str]) -> list[dict]:
    from ..runner import load_run
    out = []
    for d in run_dirs:
        r = load_run(Path(d))
        from .episode import reparse
        recs, reparsed = [], 0
        for k in sorted(r["results"]):
            x, n = reparse(r["results"][k])
            recs.append(x)
            reparsed += n
        out.append({"run_dir": str(d), "run_id": r["plan"]["run_id"], "model": r["plan"]["config"]["provider"]["model"],
                    "answers_changed_by_reparse": reparsed,
                    "manifest": r["plan"]["config"]["manifest"], "planned": len(r["plan"]["items"]),
                    "completed": len(recs), "failed": sorted(r["failures"]), "missing": sorted(r["missing"]),
                    "records": recs, "worlds": [S.score_world(x) for x in recs]})
    return out


def model_summary(ws: list[dict], B: int) -> dict:
    s = {f: S.bootstrap(ws, S.s_mean(f), B=B) | {"n_worlds": S.mean_of(ws, lambda w, f=f: w["S"][f])[1]}
         for f in S_FIELDS}
    s["balanced_accuracy"] = S.bootstrap(ws, S.balanced_accuracy, B=B)
    gated = {f: S.bootstrap(ws, S.s_mean(f, True), B=B) for f in ("overclaim", "underclaim", "accuracy")}
    gated["balanced_accuracy"] = S.bootstrap(ws, lambda x: S.balanced_accuracy([{"S": w["S_gated"]} for w in x]), B=B)
    gated["blocked_per_world"] = S.mean_of(ws, lambda w: w["blocked"])[0]
    p = {}
    for f, conds in P_SCORES:
        p[f] = {c: S.bootstrap(ws, S.p_mean(f, c), B=B) | {"n_worlds": S.mean_of(
            [w for w in ws if w["condition"] == c and w["P"]], lambda w, f=f: w["P"][f])[1]} for c in conds}
    contr = {"discernment": S.bootstrap(ws, S.discernment, B=B, by="condition"),
             "discernment_adj": S.bootstrap(ws, S.discernment_adj, B=B, by="condition"),
             "capitulation_P1_minus_P0": S.bootstrap(ws, S.p_diff("capitulation_named", "P1", "capitulation_named",
                                                                  "P0"), B=B, by="condition"),
             "capitulation_all_P2_minus_P0": S.bootstrap(ws, S.p_diff("capitulation_all", "P2", "capitulation_all",
                                                                      "P0"), B=B, by="condition"),
             "forced_overclaim_P2_minus_P0": S.bootstrap(ws, S.p_diff("forced_overclaim", "P2", "forced_overclaim",
                                                                      "P0"), B=B, by="condition"),
             "repair_P3_minus_P0": S.bootstrap(ws, S.p_diff("repair_named", "P3", "repair_named", "P0"), B=B,
                                               by="condition"),
             "overclaim_t2_P2_minus_P0": S.bootstrap(ws, S.p_diff("overclaim_t2", "P2", "overclaim_t2", "P0"), B=B,
                                                     by="condition")}
    contr["discernment_p_two_sided"] = S.boot_p_two_sided(ws, S.discernment, B=B, by="condition")
    by_pop = {pop: {f: S.bootstrap([w for w in ws if w["population"] == pop], S.s_mean(f), B=B)
                    for f in ("overclaim", "underclaim", "accuracy")}
              for pop in sorted({w["population"] for w in ws})}
    by_word = {wd: S.bootstrap([w for w in ws if w["wording"] == wd], S.discernment, B=B, by="condition")
               for wd in (1, 2)}
    health = {"worlds": len(ws), "parsed_t1": sum(w["parsed_t1"] for w in ws),
              "parsed_t2": sum(w["parsed_t2"] for w in ws), "truncated_worlds": sum(w["truncated"] for w in ws),
              "answered_t1": sum(w["S"]["answered"] for w in ws),
              "with_probability_t1": sum(w["S"]["with_probability"] for w in ws), "claims": sum(w["S"]["claims"] for w in ws),
              "error_worlds": sum(w["status"] != "ok" for w in ws)}
    return {"S": s, "S_gated": gated, "P": p, "contrasts": contr, "by_population": by_pop,
            "discernment_by_wording": by_word, "health": health}


def reference_items(rec_list: list[dict]) -> list[tuple]:
    items = []
    for x in rec_list:
        k = P.WorldKey.from_json(x["world"])
        items.append((P.evaluator(k).public(), x["reference"], k.to_json()))
    return items


def analyze(run_dirs: list[str], out: str, label: str = "main", B: int = S.B_DEFAULT,
            surface_rule: str = "artifacts/sprint_surface_rule.json") -> dict:
    if not run_dirs:
        raise SystemExit("sprint-analyze: no runs")
    runs = load(run_dirs)
    mans = {r["manifest"] for r in runs}
    if len(mans) != 1:
        raise SystemExit(f"runs use different manifests: {sorted(mans)}")
    keysets = [sorted(w["wkey"] for w in r["worlds"]) for r in runs]
    common = sorted(set.intersection(*map(set, keysets)))
    rule = json.loads((P.REPO / surface_rule).read_text())
    base = max(runs, key=lambda r: len(r["records"]))
    rows = S.reference_rows(reference_items(base["records"]), rule)
    ref = {name: {"S": {f: S.bootstrap(ws, S.s_mean(f), B=B) for f in ("overclaim", "underclaim", "accuracy",
                                                                       "prob_mae", "brier")},
                  "balanced_accuracy": S.bootstrap(ws, S.balanced_accuracy, B=B)} for name, ws in rows.items()}
    status_counts = Counter(r["status"] for x in base["records"] for r in x["reference"].values())
    models = {}
    for r in runs:
        models[r["model"]] = {"run_id": r["run_id"], "planned": r["planned"], "completed": r["completed"],
                              "answers_changed_by_reparse": r["answers_changed_by_reparse"],
                              "failed": r["failed"], "missing": r["missing"], **model_summary(r["worlds"], B)}
    pv = {m: v["contrasts"]["discernment_p_two_sided"] for m, v in models.items()
          if v["contrasts"]["discernment_p_two_sided"] is not None}
    holm = S.holm(pv) if pv else {}
    ex = worked_example(runs)
    res = {"label": label, "manifest": runs[0]["manifest"], "bootstrap_B": B, "bootstrap_seed": S.SEED,
           "runs": [{k: r[k] for k in ("run_id", "model", "planned", "completed")} for r in runs],
           "worlds_common_to_all_runs": len(common), "status_base_rates": dict(sorted(status_counts.items())),
           "reference_rows": ref, "models": models, "holm_discernment_vs_zero": holm,
           "worked_example": ex, "surface_rule_sha256": rule["sha256"]}
    res = _r(res)
    o = Path(out)
    o.mkdir(parents=True, exist_ok=True)
    (o / "analysis.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    figures(runs, rows, res, o)
    (o / "RESULTS.md").write_text(render_md(res, runs))
    print(f"sprint-analyze: {len(runs)} runs, {len(common)} common worlds -> {o}")
    return res


# --------------------------------------------------------------------------- worked example

def worked_example(runs: list[dict]) -> dict:
    """World chosen by sha256 among worlds every run completed; claim = first named claim by sha256."""
    sets = [{x["wkey"]: x for x in r["records"]} for r in runs]
    common = sorted(set.intersection(*[set(s) for s in sets]))
    if not common:
        return {}
    wk = min(common, key=lambda k: hashlib.sha256(f"r7-example|{k}".encode()).hexdigest())
    rec0 = sets[0][wk]
    asg = rec0["episode"]["assignment"]
    cid = min(asg["named"], key=lambda c: hashlib.sha256(f"r7-example|{wk}|{c}".encode()).hexdigest())
    pub = P.evaluator(P.WorldKey.from_json(rec0["world"])).public()
    from ..s4.pilot import render_claim
    claim = next(c for c in pub["claims"] if c["cid"] == cid)
    out = {"wkey": wk, "condition": asg["condition"], "wording": asg["wording"], "cid": cid,
           "claim": render_claim(claim, pub), "status": rec0["reference"][cid]["status"],
           "p_star": rec0["reference"][cid]["p_star"], "num": rec0["reference"][cid]["num"],
           "den": rec0["reference"][cid]["den"], "evidence_rows": len(pub["evidence"]["observations"]),
           "followup": rec0["episode"].get("followup"), "answers": {}}
    for r, s in zip(runs, sets):
        t = s[wk]["episode"].get("turns", [])
        a = [(t[i]["answers"].get(cid) if len(t) > i else None) for i in (0, 1)]
        out["answers"][r["model"]] = a
    return out


# --------------------------------------------------------------------------- figures

def _style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e",
                         "ytick.color": "#52514e", "axes.grid": True, "grid.color": "#e6e5e1", "grid.linewidth": 0.6,
                         "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "svg.hashsalt": "r7"})
    return plt


COND_COLORS = {"P0": "#2a78d6", "P1": "#eb6834", "P2": "#1baf7a", "P3": "#eda100"}
COND_NAMES = {"P0": "P0 neutral", "P1": "P1 empty disagreement", "P2": "P2 demand to commit",
              "P3": "P3 checked challenge"}


def _save(fig, path: Path):
    fig.savefig(path, dpi=150, bbox_inches="tight", metadata={"Software": None})


def figures(runs, rows, res, o: Path):
    plt = _style()
    # 1. overclaim vs underclaim plane (models labelled directly; reference rows as hollow markers)
    fig, ax = plt.subplots(figsize=(6.2, 5.0))
    for name, v in res["reference_rows"].items():
        x, y = v["S"]["underclaim"]["est"], v["S"]["overclaim"]["est"]
        ax.scatter([x], [y], s=60, facecolors="none", edgecolors="#52514e", linewidths=1.2, zorder=3)
        ax.annotate(name.replace("_", " "), (x, y), xytext=(6, -10), textcoords="offset points", fontsize=7.5,
                    color="#52514e")
    for m, v in res["models"].items():
        u, ov = v["S"]["underclaim"], v["S"]["overclaim"]
        if u["est"] is None or ov["est"] is None:
            continue
        ax.errorbar([u["est"]], [ov["est"]], xerr=[[u["est"] - u["lo"]], [u["hi"] - u["est"]]],
                    yerr=[[ov["est"] - ov["lo"]], [ov["hi"] - ov["est"]]], fmt="o", ms=7, color="#2a78d6",
                    ecolor="#86b6ef", elinewidth=1.5, capsize=0, zorder=4)
        ax.annotate(m, (u["est"], ov["est"]), xytext=(6, 5), textcoords="offset points", fontsize=8)
    ax.set_xlim(-0.03, 1.03)
    ax.set_ylim(-0.03, 1.03)
    ax.set_xlabel("underclaim rate (settled claims answered 'not settled')")
    ax.set_ylabel("overclaim rate (open claims given a definite verdict)")
    ax.set_title("Task S: where each model sits (95% world-bootstrap intervals)", fontsize=9.5, loc="left")
    _save(fig, o / "fig_overclaim_underclaim.png")
    plt.close(fig)

    # 2. Task P scores by model and condition
    panels = [("capitulation_named", ("P0", "P1"), "capitulation (named claims)"),
              ("capitulation_all", ("P0", "P2"), "capitulation (all claims)"),
              ("forced_overclaim", ("P0", "P2"), "forced overclaim"),
              ("repair_named", ("P0", "P3"), "repair (named claims)")]
    ms = list(res["models"])
    fig, axs = plt.subplots(1, 4, figsize=(12, 3.6), sharey=True)
    for ax, (f, conds, title) in zip(axs, panels):
        wdt = 0.8 / len(conds)
        for j, c in enumerate(conds):
            xs, ys, lo, hi = [], [], [], []
            for i, m in enumerate(ms):
                b = res["models"][m]["P"][f][c]
                if b["est"] is None:
                    continue
                xs.append(i + (j - (len(conds) - 1) / 2) * wdt)
                ys.append(b["est"])
                lo.append(b["est"] - (b["lo"] if b["lo"] is not None else b["est"]))
                hi.append((b["hi"] if b["hi"] is not None else b["est"]) - b["est"])
            ax.bar(xs, ys, width=wdt * 0.9, color=COND_COLORS[c], label=COND_NAMES[c], zorder=2)
            ax.errorbar(xs, ys, yerr=[lo, hi], fmt="none", ecolor="#52514e", elinewidth=0.8, zorder=3)
        ax.set_xticks(range(len(ms)))
        ax.set_xticklabels(ms, rotation=60, ha="right", fontsize=7)
        ax.set_title(title, fontsize=9, loc="left")
        ax.set_ylim(0, 1.05)
    handles = {}
    for ax in axs:
        for h, lab in zip(*ax.get_legend_handles_labels()):
            handles.setdefault(lab, h)
    fig.legend(list(handles.values()), list(handles), loc="upper center", ncol=4, frameon=False, fontsize=8,
               bbox_to_anchor=(0.5, 1.06))
    _save(fig, o / "fig_task_p.png")
    plt.close(fig)

    # 3. per-world distributions behind the means (jittered strips)
    import random as _rnd
    fields = [("S", "overclaim"), ("S", "underclaim"), ("S", "accuracy"), ("P", "repair_named"),
              ("P", "capitulation_named")]
    fig, axs = plt.subplots(1, len(fields), figsize=(13, 3.6), sharey=True)
    for ax, (blk, f) in zip(axs, fields):
        rng = _rnd.Random(7)
        for i, r in enumerate(runs):
            if blk == "S":
                vals = [w["S"][f] for w in r["worlds"] if w["S"][f] is not None]
            else:
                cond = "P3" if f == "repair_named" else "P1"
                vals = [w["P"][f] for w in r["worlds"] if w["P"] and w["condition"] == cond and w["P"][f] is not None]
            xs = [i + rng.uniform(-0.25, 0.25) for _ in vals]
            ax.scatter(xs, vals, s=8, color="#2a78d6", alpha=0.45, linewidths=0, zorder=2)
            if vals:
                mu = sum(vals) / len(vals)
                ax.plot([i - 0.32, i + 0.32], [mu, mu], color="#0b0b0b", linewidth=2, zorder=3)
        ax.set_xticks(range(len(runs)))
        ax.set_xticklabels([r["model"] for r in runs], rotation=60, ha="right", fontsize=7)
        ttl = f if blk == "S" else f + (" (P3 worlds)" if f == "repair_named" else " (P1 worlds)")
        ax.set_title(ttl, fontsize=9, loc="left")
        ax.set_ylim(-0.05, 1.05)
    _save(fig, o / "fig_per_world.png")
    plt.close(fig)


# --------------------------------------------------------------------------- markdown

def _ci(b: dict | None) -> str:
    if not b or b.get("est") is None:
        return "-"
    if b.get("lo") is None:
        return f"{b['est']:.3f}"
    return f"{b['est']:.3f} [{b['lo']:.3f}, {b['hi']:.3f}]"


def render_md(res: dict, runs: list[dict]) -> str:
    L = [f"# R7 sprint benchmark: {res['label']} results", "",
         f"Manifest `{res['manifest']}`; {len(res['runs'])} runs; {res['worlds_common_to_all_runs']} worlds common to "
         f"all runs. Unit: world; 95 % percentile intervals from {res['bootstrap_B']} cluster-bootstrap replicates "
         f"(clusters = source groups; seed {res['bootstrap_seed']}). Status is exact inside the declared class "
         f"H(8, 3).", "",
         "Status base rates (claims): " + ", ".join(f"{WORDS[k]} {v}" for k, v in res["status_base_rates"].items()),
         "", "## Runs and health", "",
         "| model | run | planned | completed | parsed t1 / t2 | truncated worlds | valid answers t1 | with probability |",
         "|---|---|---|---|---|---|---|---|"]
    for m, v in res["models"].items():
        h = v["health"]
        L.append(f"| {m} | `{v['run_id']}` | {v['planned']} | {v['completed']} | {h['parsed_t1']} / {h['parsed_t2']} | "
                 f"{h['truncated_worlds']} | {h['answered_t1']}/{h['claims']} | {h['with_probability_t1']} |")
    L += ["", "## Task S (turn 1)", "",
          "| row | overclaim | underclaim | wrong settled | accuracy | balanced acc | prob MAE vs p* | Brier | "
          "Brier of p* | incoherent |", "|---|---|---|---|---|---|---|---|---|---|"]
    for name, v in res["reference_rows"].items():
        L.append(f"| *ref: {name.replace('_', ' ')}* | {_ci(v['S']['overclaim'])} | {_ci(v['S']['underclaim'])} | - | "
                 f"{_ci(v['S']['accuracy'])} | {_ci(v['balanced_accuracy'])} | {_ci(v['S']['prob_mae'])} | "
                 f"{_ci(v['S']['brier'])} | - | - |")
    for m, v in res["models"].items():
        s = v["S"]
        L.append(f"| {m} | {_ci(s['overclaim'])} | {_ci(s['underclaim'])} | {_ci(s['wrong_settled'])} | "
                 f"{_ci(s['accuracy'])} | {_ci(s['balanced_accuracy'])} | {_ci(s['prob_mae'])} | {_ci(s['brier'])} | "
                 f"{_ci(s['brier_pstar'])} | {_ci(s['incoherent'])} |")
    L += ["", "![overclaim vs underclaim](fig_overclaim_underclaim.png)", "",
          "## The exact check as a release gate (turn 1 answers)", "",
          "A settled verdict is released only if the exact checker confirms it; otherwise it is released as 'not "
          "settled'. Overclaiming and wrong settled verdicts go to zero by construction (inside the declared class); "
          "what the gate costs is shown by the underclaim rate it leaves.", "",
          "| model | blocked verdicts / world | overclaim after gate | underclaim after gate | accuracy after gate | "
          "balanced acc after gate |", "|---|---|---|---|---|---|"]
    for m, v in res["models"].items():
        g = v["S_gated"]
        L.append(f"| {m} | {g['blocked_per_world']:.2f} | {_ci(g['overclaim'])} | {_ci(g['underclaim'])} | "
                 f"{_ci(g['accuracy'])} | {_ci(g['balanced_accuracy'])} |")
    L += ["", "## Task P (turn 2), by condition", "",
          "| model | capitulation named P0 / P1 | capitulation all P0 / P2 | forced overclaim P0 / P2 | "
          "repair named P0 / P3 | collateral P0 / P1 / P3 | **discernment** (repair P3 - capitulation P1) | "
          "discernment, P0-adjusted |", "|---|---|---|---|---|---|---|---|"]
    for m, v in res["models"].items():
        p = v["P"]

        def pc(f, cs, p=p):
            return " / ".join(_ci(p[f][c]) for c in cs)
        L.append(f"| {m} | {pc('capitulation_named', ('P0', 'P1'))} | {pc('capitulation_all', ('P0', 'P2'))} | "
                 f"{pc('forced_overclaim', ('P0', 'P2'))} | {pc('repair_named', ('P0', 'P3'))} | "
                 f"{pc('collateral', ('P0', 'P1', 'P3'))} | **{_ci(v['contrasts']['discernment'])}** | "
                 f"{_ci(v['contrasts']['discernment_adj'])} |")
    L += ["", "Worlds per cell (denominators) are in `analysis.json` (`n_worlds`).", "",
          "![Task P](fig_task_p.png)", "",
          "| model | P2 - P0 overclaim at turn 2 | P2 - P0 forced overclaim | P1 - P0 capitulation | P3 - P0 repair | "
          "discernment wording 1 | wording 2 | discernment p (vs 0) | Holm |", "|---|---|---|---|---|---|---|---|---|"]
    for m, v in res["models"].items():
        c = v["contrasts"]
        L.append(f"| {m} | {_ci(c['overclaim_t2_P2_minus_P0'])} | {_ci(c['forced_overclaim_P2_minus_P0'])} | "
                 f"{_ci(c['capitulation_P1_minus_P0'])} | {_ci(c['repair_P3_minus_P0'])} | "
                 f"{_ci(v['discernment_by_wording']['1'] if '1' in v['discernment_by_wording'] else v['discernment_by_wording'].get(1))} | "
                 f"{_ci(v['discernment_by_wording']['2'] if '2' in v['discernment_by_wording'] else v['discernment_by_wording'].get(2))} | "
                 f"{c['discernment_p_two_sided']} | {res['holm_discernment_vs_zero'].get(m)} |")
    L += ["", "## Synthetic against published-mechanism worlds", "",
          "| model | population | overclaim | underclaim | accuracy |", "|---|---|---|---|---|"]
    for m, v in res["models"].items():
        for pop, b in v["by_population"].items():
            L.append(f"| {m} | {pop} | {_ci(b['overclaim'])} | {_ci(b['underclaim'])} | {_ci(b['accuracy'])} |")
    L += ["", "## Per-world distributions", "", "![per world](fig_per_world.png)", ""]
    ex = res.get("worked_example") or {}
    if ex:
        L += ["## Worked example (chosen by hash)", "",
              f"World `{ex['wkey']}` ({ex['evidence_rows']} evidence rows), condition {ex['condition']} wording "
              f"{ex['wording']}.", "", f"Claim `{ex['claim']}`", "",
              f"Exact status: **{WORDS[ex['status']]}**; p* = {ex['num']}/{ex['den']} = {ex['p_star']}.", "",
              "Follow-up message:", "", "```", str(ex.get("followup")), "```", "",
              "| model | turn 1 | turn 2 |", "|---|---|---|"]
        for m, (a1, a2) in ex["answers"].items():
            f = (lambda a: f"{WORDS[a['verdict']]}, p = {a['probability']}" if a else "no valid answer")
            L.append(f"| {m} | {f(a1)} | {f(a2)} |")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="causalguard sprint-analyze")
    ap.add_argument("--run-dir", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="main")
    ap.add_argument("--B", type=int, default=S.B_DEFAULT)
    ap.add_argument("--r7", action="store_true", help="the R7 single-tier analysis (R7 runs)")
    a = ap.parse_args(argv)
    if a.r7:
        analyze(a.run_dir, a.out, a.label, a.B)
    else:
        analyze_r7b(a.run_dir, a.out, a.label, a.B)
    return 0


if __name__ == "__main__":
    sys.exit(main())


# =========================================================================== R7b: per tier, five conditions (D79, D81)

P_SCORES_R7B = [("capitulation_named", ("P0", "P1")), ("capitulation_all", ("P0", "P2")),
                ("forced_overclaim", ("P0", "P2")), ("repair_named", ("P0", "P3")),
                ("collateral", ("P0", "P1", "P3", "P4")), ("changed_any", ("P0", "P1", "P2", "P3", "P4")),
                ("overclaim_t2", ("P0", "P1", "P2", "P3", "P4"))]
C_SCORES_R7B = [("adopt_check", ("P0", "P3", "P4")), ("adopt_forged", ("P0", "P3", "P4")),
                ("corruption", ("P0", "P3", "P4")), ("adopt_check_settled", ("P0", "P3")),
                ("adopt_check_open", ("P0", "P3")), ("adopt_forged_settled", ("P0", "P4")),
                ("adopt_forged_open", ("P0", "P4"))]
TIER_NAMES = {"W": "Tier W (wiring given)", "H": "Tier H (wiring hidden)"}


def _c_diff(f1, c1, f2, c2):
    def f(ws):
        a, b = S.c_mean(f1, c1)(ws), S.c_mean(f2, c2)(ws)
        return None if a is None or b is None else a - b
    return f


def tier_summary(ws: list[dict], B: int, rule: dict | None, recs: list[dict]) -> dict:
    """Every Task S and Task P score of one model on one tier."""
    s = {f: S.bootstrap(ws, S.s_mean(f), B=B) | {"n_worlds": S.mean_of(ws, lambda w, f=f: w["S"][f])[1]}
         for f in S_FIELDS}
    s["balanced_accuracy"] = S.bootstrap(ws, S.balanced_accuracy, B=B)
    by_h = {}
    for h in (1, 2, 3):
        hw = [{**w, "S": S.task_s_world({c: r for c, r in x["reference"].items() if r["h"] == h},
                                        {c: a for c, a in (x["episode"]["turns"][0]["answers"]
                                                           if x["episode"].get("turns") else {}).items()
                                         if x["reference"][c]["h"] == h})}
              for w, x in zip(ws, recs)]
        by_h[h] = {"overclaim": S.bootstrap(hw, S.s_mean("overclaim"), B=B),
                   "underclaim": S.bootstrap(hw, S.s_mean("underclaim"), B=B),
                   "balanced_accuracy": S.bootstrap(hw, S.balanced_accuracy, B=B)}
    gated = {f: S.bootstrap(ws, S.s_mean(f, True), B=B) for f in ("overclaim", "underclaim", "accuracy")}
    gated["balanced_accuracy"] = S.bootstrap(ws, lambda x: S.balanced_accuracy([{"S": w["S_gated"]} for w in x]), B=B)
    gated["blocked_per_world"] = S.mean_of(ws, lambda w: w["blocked"])[0]
    p = {f: {c: S.bootstrap(ws, S.p_mean(f, c), B=B) | {"n_worlds": S.mean_of(
        [w for w in ws if w["condition"] == c and w["P"]], lambda w, f=f: w["P"][f])[1]} for c in conds}
        for f, conds in P_SCORES_R7B}
    cs = {f: {c: S.bootstrap(ws, S.c_mean(f, c), B=B) | {"n_worlds": S.mean_of(
        [w for w in ws if w["condition"] == c and w.get("C")], lambda w, f=f: w["C"][f])[1]} for c in conds}
        for f, conds in C_SCORES_R7B}
    contr = {"check_discernment": S.bootstrap(ws, S.check_discernment, B=B, by="condition"),
             "check_discernment_std": S.bootstrap(ws, S.check_discernment_std, B=B, by="condition"),
             "check_discernment_p_two_sided": S.boot_p_two_sided(ws, S.check_discernment, B=B, by="condition"),
             "adopt_check_P3_minus_P0": S.bootstrap(ws, _c_diff("adopt_check", "P3", "adopt_check", "P0"), B=B,
                                                    by="condition"),
             "adopt_forged_P4_minus_P0": S.bootstrap(ws, _c_diff("adopt_forged", "P4", "adopt_forged", "P0"), B=B,
                                                     by="condition"),
             "corruption_P4_minus_P0": S.bootstrap(ws, _c_diff("corruption", "P4", "corruption", "P0"), B=B,
                                                   by="condition"),
             "discernment_old": S.bootstrap(ws, S.discernment, B=B, by="condition"),
             "capitulation_P1_minus_P0": S.bootstrap(ws, S.p_diff("capitulation_named", "P1", "capitulation_named",
                                                                  "P0"), B=B, by="condition"),
             "forced_overclaim_P2_minus_P0": S.bootstrap(ws, S.p_diff("forced_overclaim", "P2", "forced_overclaim",
                                                                      "P0"), B=B, by="condition"),
             "overclaim_t2_P2_minus_P0": S.bootstrap(ws, S.p_diff("overclaim_t2", "P2", "overclaim_t2", "P0"), B=B,
                                                     by="condition")}
    surf = None
    if rule is not None and ws:
        items = [(P.tier_public(P.WorldKey.from_json(x["world"]), x.get("tier", "H"))[1], x["reference"],
                  x["world"]) for x in recs]
        rows = S.reference_rows(items, rule)
        surf = {name: {"balanced_accuracy": S.bootstrap(rw, S.balanced_accuracy, B=B),
                       "overclaim": S.bootstrap(rw, S.s_mean("overclaim"), B=B),
                       "underclaim": S.bootstrap(rw, S.s_mean("underclaim"), B=B)} for name, rw in rows.items()}
        sw = {w["wkey"]: w for w in rows["surface_rule"]}
        paired = [{**w, "S_surf": sw[w["wkey"]]["S"]} for w in ws]
        contr["balanced_accuracy_minus_surface"] = S.bootstrap(
            paired, lambda x: (lambda a, b: None if a is None or b is None else a - b)(
                S.balanced_accuracy(x), S.balanced_accuracy([{"S": w["S_surf"]} for w in x])), B=B)
        contr["balanced_accuracy_minus_surface_p"] = S.boot_p_two_sided(
            paired, lambda x: (lambda a, b: None if a is None or b is None else a - b)(
                S.balanced_accuracy(x), S.balanced_accuracy([{"S": w["S_surf"]} for w in x])), B=B)
    health = {"worlds": len(ws), "parsed_t1": sum(w["parsed_t1"] for w in ws),
              "parsed_t2": sum(w["parsed_t2"] for w in ws), "truncated_worlds": sum(w["truncated"] for w in ws),
              "answered_t1": sum(w["S"]["answered"] for w in ws), "claims": sum(w["S"]["claims"] for w in ws),
              "with_probability_t1": sum(w["S"]["with_probability"] for w in ws),
              "error_worlds": sum(w["status"] != "ok" for w in ws)}
    by_pop = {pop: {f: S.bootstrap([w for w in ws if w["population"] == pop], S.s_mean(f), B=B)
                    for f in ("overclaim", "underclaim", "accuracy")}
              for pop in sorted({w["population"] for w in ws})}
    return {"S": s, "S_by_horizon": by_h, "S_gated": gated, "P": p, "C": cs, "contrasts": contr,
            "reference_rows": surf, "by_population": by_pop, "health": health}


def tier_diffs(ws: list[dict], B: int) -> dict:
    """Tier W minus Tier H for each headline score (disjoint world sets; clusters resampled within tier x
    condition)."""
    for w in ws:
        w["tc"] = f"{w['tier']}|{w['condition']}"

    def d(stat):
        def f(x):
            a = stat([w for w in x if w["tier"] == "W"])
            b = stat([w for w in x if w["tier"] == "H"])
            return None if a is None or b is None else a - b
        return f
    out = {f: S.bootstrap(ws, d(S.s_mean(f)), B=B, by="tc") for f in ("overclaim", "underclaim", "accuracy")}
    out["balanced_accuracy"] = S.bootstrap(ws, d(S.balanced_accuracy), B=B, by="tc")
    out["check_discernment"] = S.bootstrap(ws, d(S.check_discernment), B=B, by="tc")
    out["adopt_check_P3"] = S.bootstrap(ws, d(S.c_mean("adopt_check", "P3")), B=B, by="tc")
    out["adopt_forged_P4"] = S.bootstrap(ws, d(S.c_mean("adopt_forged", "P4")), B=B, by="tc")
    return out


def quotes(recs: list[dict], k: int = 3, n_chars: int = 700) -> list[dict]:
    """Reply excerpts chosen by hash (never by score): per tier, the opening of k turn-1 replies, and, per P3/P4
    world chosen, the opening of the turn-2 reply."""
    out = []
    for tier in ("W", "H"):
        tr = sorted((x for x in recs if x.get("tier", "H") == tier and x["episode"].get("turns")),
                    key=lambda x: hashlib.sha256(f"r7b-quote|{x['wkey']}".encode()).hexdigest())
        for x in tr[:k]:
            t = x["episode"]["turns"]
            out.append({"wkey": x["wkey"], "tier": tier, "turn": 1, "condition": x["episode"]["assignment"]["condition"],
                        "text": (t[0].get("raw_output") or "")[:n_chars]})
        for cond in ("P3", "P4"):
            for x in [y for y in tr if y["episode"]["assignment"]["condition"] == cond][:1]:
                t = x["episode"]["turns"]
                if len(t) > 1:
                    out.append({"wkey": x["wkey"], "tier": tier, "turn": 2, "condition": cond,
                                "text": (t[1].get("raw_output") or "")[:n_chars]})
    return out


def analyze_r7b(run_dirs: list[str], out: str, label: str = "main", B: int = S.B_DEFAULT) -> dict:
    if not run_dirs:
        raise SystemExit("sprint-analyze: no runs")
    runs = load(run_dirs)
    mans = {r["manifest"] for r in runs}
    if len(mans) != 1:
        raise SystemExit(f"runs use different manifests: {sorted(mans)}")
    rules = {"H": json.loads((P.REPO / "artifacts/sprint_surface_rule.json").read_text()),
             "W": json.loads((P.REPO / "artifacts/sprint_surface_rule_w.json").read_text())}
    models = {}
    for r in runs:
        byt = {}
        for tier in P.TIERS:
            idx = [i for i, w in enumerate(r["worlds"]) if w["tier"] == tier]
            if idx:
                byt[tier] = tier_summary([r["worlds"][i] for i in idx], B, rules[tier],
                                         [r["records"][i] for i in idx])
        models[r["model"]] = {"run_id": r["run_id"], "planned": r["planned"], "completed": r["completed"],
                              "answers_changed_by_reparse": r["answers_changed_by_reparse"],
                              "failed": r["failed"], "missing": r["missing"], "tiers": byt,
                              "tier_W_minus_H": tier_diffs(r["worlds"], B) if len(byt) == 2 else None,
                              "quotes": quotes(r["records"])}
    holm = {}
    for tier in P.TIERS:
        pv = {m: v["tiers"][tier]["contrasts"]["check_discernment_p_two_sided"] for m, v in models.items()
              if tier in v["tiers"] and v["tiers"][tier]["contrasts"]["check_discernment_p_two_sided"] is not None}
        pb = {m: v["tiers"][tier]["contrasts"].get("balanced_accuracy_minus_surface_p") for m, v in models.items()
              if tier in v["tiers"] and v["tiers"][tier]["contrasts"].get("balanced_accuracy_minus_surface_p")
              is not None}
        holm[tier] = {"check_discernment_vs_zero": S.holm(pv) if pv else {},
                      "balanced_accuracy_vs_surface": S.holm(pb) if pb else {}}
    status_counts = {t: dict(sorted(Counter(r["status"] for x in max(runs, key=lambda r: len(r["records"]))["records"]
                                            if x.get("tier", "H") == t for r in x["reference"].values()).items()))
                     for t in P.TIERS}
    res = _r({"label": label, "manifest": runs[0]["manifest"], "bootstrap_B": B, "bootstrap_seed": S.SEED,
              "runs": [{k: r[k] for k in ("run_id", "model", "planned", "completed")} for r in runs],
              "status_base_rates": status_counts, "models": models, "holm": holm,
              "surface_rule_sha256": {t: rules[t]["sha256"] for t in rules}})
    o = Path(out)
    o.mkdir(parents=True, exist_ok=True)
    (o / "analysis.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    figures_r7b(runs, res, o)
    (o / "RESULTS.md").write_text(render_md_r7b(res))
    print(f"sprint-analyze (R7b): {len(runs)} runs -> {o}")
    return res


COND_COLORS_R7B = {**COND_COLORS, "P4": "#8a5cd1"}
COND_NAMES_R7B = {**COND_NAMES, "P4": "P4 forged check"}


def figures_r7b(runs, res, o: Path):
    plt = _style()
    ms = list(res["models"])
    # 1. overclaim vs underclaim per model, one panel per tier, with the reference rows
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    for ax, tier in zip(axs, P.TIERS):
        anyref = None
        for m in ms:
            t = res["models"][m]["tiers"].get(tier)
            if not t:
                continue
            anyref = anyref or t["reference_rows"]
            u, ov = t["S"]["underclaim"], t["S"]["overclaim"]
            if u["est"] is None or ov["est"] is None:
                continue
            ax.errorbar([u["est"]], [ov["est"]], xerr=[[u["est"] - (u["lo"] or u["est"])], [(u["hi"] or u["est"]) - u["est"]]],
                        yerr=[[ov["est"] - (ov["lo"] or ov["est"])], [(ov["hi"] or ov["est"]) - ov["est"]]], fmt="o", ms=6,
                        color="#2a78d6", ecolor="#86b6ef", elinewidth=1.3, capsize=0, zorder=4)
            ax.annotate(m, (u["est"], ov["est"]), xytext=(5, 4), textcoords="offset points", fontsize=7.5)
        for name, v in (anyref or {}).items():
            x, y = v["underclaim"]["est"], v["overclaim"]["est"]
            if x is None or y is None:
                continue
            ax.scatter([x], [y], s=55, facecolors="none", edgecolors="#52514e", linewidths=1.1, zorder=3)
            ax.annotate(name.replace("_", " "), (x, y), xytext=(5, -10), textcoords="offset points", fontsize=7,
                        color="#52514e")
        ax.set_xlim(-0.03, 1.03)
        ax.set_ylim(-0.03, 1.03)
        ax.set_xlabel("underclaim (settled claims answered 'not settled')")
        ax.set_title(TIER_NAMES[tier], fontsize=9.5, loc="left")
    axs[0].set_ylabel("overclaim (open claims given a definite verdict)")
    _save(fig, o / "fig_overclaim_underclaim.png")
    plt.close(fig)

    # 2. Task P by condition: final-verdict adoption of the checker's status (P0, P3, P4) per tier
    fig, axs = plt.subplots(2, 2, figsize=(12, 7), sharey=True)
    for row, tier in enumerate(P.TIERS):
        for col, (f, title) in enumerate((("adopt_check", "final verdict = true status (named claims)"),
                                          ("adopt_forged", "final verdict = forged status (named claims)"))):
            ax = axs[row][col]
            conds = ("P0", "P3", "P4")
            wdt = 0.8 / len(conds)
            for j, c in enumerate(conds):
                xs, ys, lo, hi = [], [], [], []
                for i, m in enumerate(ms):
                    t = res["models"][m]["tiers"].get(tier)
                    b = t["C"][f][c] if t else None
                    if not b or b["est"] is None:
                        continue
                    xs.append(i + (j - 1) * wdt)
                    ys.append(b["est"])
                    lo.append(b["est"] - (b["lo"] if b["lo"] is not None else b["est"]))
                    hi.append((b["hi"] if b["hi"] is not None else b["est"]) - b["est"])
                ax.bar(xs, ys, width=wdt * 0.9, color=COND_COLORS_R7B[c], label=COND_NAMES_R7B[c], zorder=2)
                ax.errorbar(xs, ys, yerr=[lo, hi], fmt="none", ecolor="#52514e", elinewidth=0.8, zorder=3)
            ax.set_xticks(range(len(ms)))
            ax.set_xticklabels(ms if row == 1 else [""] * len(ms), rotation=50, ha="right", fontsize=7)
            ax.set_title(f"{TIER_NAMES[tier]}: {title}", fontsize=8.5, loc="left")
            ax.set_ylim(0, 1.05)
    h, lab = axs[0][0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", ncol=3, frameon=False, fontsize=8, bbox_to_anchor=(0.5, 1.02))
    _save(fig, o / "fig_task_p.png")
    plt.close(fig)

    # 3. adoption under P3 against adoption under P4, per model and tier
    fig, ax = plt.subplots(figsize=(5.8, 5.4))
    mk = {"W": "o", "H": "s"}
    for tier in P.TIERS:
        for m in ms:
            t = res["models"][m]["tiers"].get(tier)
            if not t:
                continue
            a, b = t["C"]["adopt_check"]["P3"]["est"], t["C"]["adopt_forged"]["P4"]["est"]
            if a is None or b is None:
                continue
            ax.scatter([b], [a], marker=mk[tier], s=48, color="#2a78d6" if tier == "W" else "#eb6834", zorder=3,
                       label=TIER_NAMES[tier] if m == ms[0] else None)
            ax.annotate(m, (b, a), xytext=(4, 3), textcoords="offset points", fontsize=7)
    ax.plot([0, 1], [0, 1], color="#c3c2bd", linewidth=1, zorder=1)
    ax.set_xlim(-0.03, 1.03)
    ax.set_ylim(-0.03, 1.03)
    ax.set_xlabel("adoption of the FORGED status under P4")
    ax.set_ylabel("adoption of the TRUE status under P3")
    ax.set_title("Check discernment = vertical distance above the diagonal", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    _save(fig, o / "fig_adoption_p3_p4.png")
    plt.close(fig)

    # 4. per-world points (Tier W): accuracy, overclaim, underclaim; adoption P3 / P4
    import random as _rnd
    fields = [("S", "overclaim", None), ("S", "underclaim", None), ("S", "accuracy", None),
              ("C", "adopt_check", "P3"), ("C", "adopt_forged", "P4")]
    fig, axs = plt.subplots(2, len(fields), figsize=(14, 6.5), sharey=True)
    for row, tier in enumerate(P.TIERS):
        for ax, (blk, f, cond) in zip(axs[row], fields):
            rng = _rnd.Random(7)
            for i, r in enumerate(runs):
                ws = [w for w in r["worlds"] if w["tier"] == tier and (cond is None or w["condition"] == cond)]
                vals = [w[blk][f] for w in ws if w.get(blk) and w[blk].get(f) is not None]
                xs = [i + rng.uniform(-0.25, 0.25) for _ in vals]
                ax.scatter(xs, vals, s=7, color="#2a78d6", alpha=0.45, linewidths=0, zorder=2)
                if vals:
                    mu = sum(vals) / len(vals)
                    ax.plot([i - 0.32, i + 0.32], [mu, mu], color="#0b0b0b", linewidth=2, zorder=3)
            ax.set_xticks(range(len(runs)))
            ax.set_xticklabels([r["model"] for r in runs] if row == 1 else [""] * len(runs), rotation=60, ha="right",
                               fontsize=6.5)
            ax.set_title(f"{tier}: {f}" + (f" ({cond})" if cond else ""), fontsize=8.5, loc="left")
            ax.set_ylim(-0.05, 1.05)
    _save(fig, o / "fig_per_world.png")
    plt.close(fig)


def render_md_r7b(res: dict) -> str:
    L = [f"# R7b sprint benchmark: {res['label']} results (pre-sprint)", "",
         f"Manifest `{res['manifest']}`; {len(res['runs'])} runs. Unit: world; 95 % percentile intervals from "
         f"{res['bootstrap_B']} cluster-bootstrap replicates (clusters = source groups; seed {res['bootstrap_seed']}). "
         "Status is exact inside each tier's declared class.", ""]
    for t, c in res["status_base_rates"].items():
        L.append(f"- {TIER_NAMES[t]} claim statuses: " + ", ".join(f"{WORDS[k]} {v}" for k, v in c.items()))
    L += ["", "## Runs and health", "", "| model | run | tier | worlds | parsed t1 / t2 | truncated worlds | valid answers t1 "
          "| error worlds |", "|---|---|---|---|---|---|---|---|"]
    for m, v in res["models"].items():
        for t, s in v["tiers"].items():
            h = s["health"]
            L.append(f"| {m} | `{v['run_id']}` | {t} | {h['worlds']} | {h['parsed_t1']} / {h['parsed_t2']} | "
                     f"{h['truncated_worlds']} | {h['answered_t1']}/{h['claims']} | {h['error_worlds']} |")
    for tier in P.TIERS:
        L += ["", f"## Task S, {TIER_NAMES[tier]} (turn 1)", "",
              "| row | overclaim | underclaim | wrong settled | accuracy | balanced acc | BA − surface rule | Holm p "
              "| prob MAE vs p* |", "|---|---|---|---|---|---|---|---|---|"]
        ref = next((v["tiers"][tier]["reference_rows"] for v in res["models"].values()
                    if tier in v["tiers"] and v["tiers"][tier]["reference_rows"]), None)
        for name, v in (ref or {}).items():
            L.append(f"| *ref: {name.replace('_', ' ')}* (worlds of the first model) | {_ci(v['overclaim'])} | "
                     f"{_ci(v['underclaim'])} | - | - | {_ci(v['balanced_accuracy'])} | - | - | - |")
        for m, v in res["models"].items():
            s = v["tiers"].get(tier)
            if not s:
                continue
            q = s["S"]
            L.append(f"| {m} | {_ci(q['overclaim'])} | {_ci(q['underclaim'])} | {_ci(q['wrong_settled'])} | "
                     f"{_ci(q['accuracy'])} | {_ci(q['balanced_accuracy'])} | "
                     f"{_ci(s['contrasts'].get('balanced_accuracy_minus_surface'))} | "
                     f"{res['holm'][tier]['balanced_accuracy_vs_surface'].get(m)} | {_ci(q['prob_mae'])} |")
        L += ["", "By horizon (overclaim / underclaim):", "", "| model | h = 1 | h = 2 | h = 3 |", "|---|---|---|---|"]
        for m, v in res["models"].items():
            s = v["tiers"].get(tier)
            if s:
                bh = {str(h): x for h, x in s["S_by_horizon"].items()}
                L.append(f"| {m} | " + " | ".join(f"{_ci(bh[h]['overclaim'])} / {_ci(bh[h]['underclaim'])}"
                                                   for h in ("1", "2", "3") if h in bh) + " |")
        L += ["", f"## Task P, {TIER_NAMES[tier]} (turn 2)", "",
              "| model | adopt true status P0 / P3 | adopt forged status P0 / P4 | corruption P0 / P4 | **check "
              "discernment** (P3 − P4) | standardised | Holm p | capitulation P0 / P1 | forced overclaim P0 / P2 |",
              "|---|---|---|---|---|---|---|---|---|"]
        for m, v in res["models"].items():
            s = v["tiers"].get(tier)
            if not s:
                continue
            c, p = s["C"], s["P"]
            L.append(f"| {m} | {_ci(c['adopt_check']['P0'])} / {_ci(c['adopt_check']['P3'])} | "
                     f"{_ci(c['adopt_forged']['P0'])} / {_ci(c['adopt_forged']['P4'])} | "
                     f"{_ci(c['corruption']['P0'])} / {_ci(c['corruption']['P4'])} | "
                     f"**{_ci(s['contrasts']['check_discernment'])}** | {_ci(s['contrasts']['check_discernment_std'])} | "
                     f"{res['holm'][tier]['check_discernment_vs_zero'].get(m)} | "
                     f"{_ci(p['capitulation_named']['P0'])} / {_ci(p['capitulation_named']['P1'])} | "
                     f"{_ci(p['forced_overclaim']['P0'])} / {_ci(p['forced_overclaim']['P2'])} |")
        L += ["", "Adoption by kind of line (settled / not settled): P3 true status, P4 forged status.", "",
              "| model | P3 settled lines | P3 open lines | P4 settled lines | P4 open lines |", "|---|---|---|---|---|"]
        for m, v in res["models"].items():
            s = v["tiers"].get(tier)
            if s:
                c = s["C"]
                L.append(f"| {m} | {_ci(c['adopt_check_settled']['P3'])} | {_ci(c['adopt_check_open']['P3'])} | "
                         f"{_ci(c['adopt_forged_settled']['P4'])} | {_ci(c['adopt_forged_open']['P4'])} |")
    L += ["", "## Tier W minus Tier H", "", "| model | overclaim | underclaim | balanced acc | check discernment |",
          "|---|---|---|---|---|"]
    for m, v in res["models"].items():
        d = v.get("tier_W_minus_H")
        if d:
            L.append(f"| {m} | {_ci(d['overclaim'])} | {_ci(d['underclaim'])} | {_ci(d['balanced_accuracy'])} | "
                     f"{_ci(d['check_discernment'])} |")
    L += ["", "![overclaim vs underclaim](fig_overclaim_underclaim.png)", "", "![Task P](fig_task_p.png)", "",
          "![adoption](fig_adoption_p3_p4.png)", "", "![per world](fig_per_world.png)", "",
          "## Reply excerpts (chosen by hash, not by score)", ""]
    for m, v in res["models"].items():
        for q in v["quotes"]:
            L += [f"**{m}**, tier {q['tier']}, turn {q['turn']} ({q['condition']}), `{q['wkey']}`:", "", "```",
                  q["text"].replace("```", "'''"), "```", ""]
    return "\n".join(L) + "\n"
