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
        recs = [r["results"][k] for k in sorted(r["results"])]
        out.append({"run_dir": str(d), "run_id": r["plan"]["run_id"], "model": r["plan"]["config"]["provider"]["model"],
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
              "answered_t1": sum(w["S"]["answered"] for w in ws), "claims": sum(w["S"]["claims"] for w in ws),
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
         "| model | run | planned | completed | parsed t1 / t2 | truncated worlds | valid answers t1 |",
         "|---|---|---|---|---|---|---|"]
    for m, v in res["models"].items():
        h = v["health"]
        L.append(f"| {m} | `{v['run_id']}` | {v['planned']} | {v['completed']} | {h['parsed_t1']} / {h['parsed_t2']} | "
                 f"{h['truncated_worlds']} | {h['answered_t1']}/{h['claims']} |")
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
    a = ap.parse_args(argv)
    analyze(a.run_dir, a.out, a.label, a.B)
    return 0


if __name__ == "__main__":
    sys.exit(main())
