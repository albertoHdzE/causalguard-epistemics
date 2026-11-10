"""Offline S3 analysis (secondary study; development pilot = exploratory).

Primary S3 contrast (protocol): D vs B on final-verdict balanced accuracy, world-clustered
bootstrap (balanced accuracy pooled over the resampled worlds' items).  Secondary: C - B,
D_label - B, D - A, transfer T_D vs A(target item), T_A vs A(target item).  Mock/replay
records are refused by the scorer.  Reads raw records only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from ..experiments.s3 import per_world_scores, score
from ..runner import ROOT, read_jsonl
from ..s3_tasks import VERDICT_LABELS
from ..stats import balanced_accuracy_from_counts, cluster_bootstrap


def _counts(rows, arm):
    out = np.zeros((len(rows), len(VERDICT_LABELS), 2))
    ok = np.zeros(len(rows), bool)
    for w, r in enumerate(rows):
        st = r["arms"].get(arm)
        if st is None:
            continue
        ok[w] = True
        for k, c in enumerate(VERDICT_LABELS):
            out[w, k] = st["by_class"][c]
    return out, ok


def contrast_balanced(rows, a, b, reps=5000, seed=20261109):
    ca, oka = _counts(rows, a)
    cb, okb = _counts(rows, b)
    keep = oka & okb
    ca, cb = ca[keep], cb[keep]
    if not len(ca):
        return None
    stat = lambda idx: balanced_accuracy_from_counts(ca[idx].sum(0)) - balanced_accuracy_from_counts(cb[idx].sum(0))  # noqa: E731
    r = cluster_bootstrap(stat, len(ca), reps, seed)
    r.update(a=a, b=b, metric="balanced_accuracy", mean_a=balanced_accuracy_from_counts(ca.sum(0)),
             mean_b=balanced_accuracy_from_counts(cb.sum(0)))
    return r


def contrast_accuracy(rows, a, b, reps=5000, seed=20261109):
    pairs = [(r["arms"][a]["correct"] / r["arms"][a]["n_items"], r["arms"][b]["correct"] / r["arms"][b]["n_items"])
             for r in rows if a in r["arms"] and b in r["arms"] and r["arms"][a]["n_items"] and r["arms"][b]["n_items"]]
    if not pairs:
        return None
    d = np.array([x - y for x, y in pairs])
    r = cluster_bootstrap(lambda idx: float(d[idx].mean()), len(d), reps, seed)
    r.update(a=a, b=b, metric="per-world accuracy (paired)")
    return r


def contrast_transfer(rows, arm, reps=5000, seed=20261109):
    pairs = [(r["transfer"][arm]["correct"], r["transfer"][arm]["A_target_correct"]) for r in rows
             if arm in r.get("transfer", {})]
    if not pairs:
        return None
    d = np.array([x - y for x, y in pairs], dtype=float)
    r = cluster_bootstrap(lambda idx: float(d[idx].mean()), len(d), reps, seed)
    r.update(a=arm, b="A(target item)", metric="target-item accuracy (paired)")
    return r


def shortcut_baselines(salt: str, indices: list[int]) -> dict:
    """Trivial/surface baselines on the same S3 items (no model): always the most common verdict, and a
    surface rule (observation budget, horizon, intervention kind) -> most common verdict, fit on even world
    indices and evaluated on odd ones.  Detects label shortcuts in the task construction."""
    from collections import Counter, defaultdict

    from ..s3_tasks import make_s3_items
    items = []
    for i in indices:
        d = make_s3_items(salt, i)
        for it in d["private"]["items"]:
            q = it["query"]
            items.append((i, (d["private"]["budget"], q["horizon"], q["intervention"]["kind"]), it["verdict"]))
    train = [x for x in items if x[0] % 2 == 0]
    test = [x for x in items if x[0] % 2 == 1]
    maj = Counter(v for _, _, v in train).most_common(1)[0][0]
    table = defaultdict(Counter)
    for _, f, v in train:
        table[f][v] += 1
    rule = {f: c.most_common(1)[0][0] for f, c in table.items()}

    def score(pred):
        by = {c: [0, 0] for c in VERDICT_LABELS}
        for (_, _f, v), p in zip(test, pred):
            by[v][0] += 1
            by[v][1] += int(p == v)
        rec = [by[c][1] / by[c][0] for c in VERDICT_LABELS if by[c][0]]
        return {"accuracy": sum(b[1] for b in by.values()) / len(test), "balanced_accuracy": sum(rec) / len(rec)}
    return {"n_test_items": len(test), "majority_verdict": maj, "majority": score([maj] * len(test)),
            "surface_rule": score([rule.get(f, maj) for _, f, _ in test])}


def analyze(run_ids: list[str], out_dir: Path, reps: int = 5000) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {}
    for rid in run_ids:
        recs = read_jsonl(ROOT / "runs" / rid / "records.jsonl")
        fails = read_jsonl(ROOT / "runs" / rid / "failures.jsonl")
        if not recs:
            result[rid] = {"status": "no records"}
            continue
        rows = per_world_scores(recs)          # refuses mock/replay mixing
        sc = score(recs)
        res = {"n_worlds": len(rows), "runner_failures": len(fails), "provider_kind": sc["provider_kind"],
               "provider_metadata": recs[0].get("provider_metadata"), "pooled": sc,
               "primary_D_minus_B_balanced_accuracy": contrast_balanced(rows, "D", "B", reps),
               "secondary": {
                   "C-B_balanced": contrast_balanced(rows, "C", "B", reps),
                   "D_label-B_balanced": contrast_balanced(rows, "D_label", "B", reps),
                   "D-A_balanced": contrast_balanced(rows, "D", "A", reps),
                   "B-A_balanced": contrast_balanced(rows, "B", "A", reps),
                   "E-A_balanced": contrast_balanced(rows, "E", "A", reps),
                   "D-B_accuracy": contrast_accuracy(rows, "D", "B", reps),
                   "T_D-A_target": contrast_transfer(rows, "T_D", reps),
                   "T_A-A_target": contrast_transfer(rows, "T_A", reps)}}
        # natural verdict distribution of the items actually asked
        res["verdict_distribution"] = {c: int(sum(r["arms"]["A"]["by_class"][c][0] for r in rows if "A" in r["arms"]))
                                       for c in VERDICT_LABELS}
        # verdict/probability coherence per call kind (a model may use the probability channel as
        # P(claim true/false) instead of confidence over the three statuses; Brier is then not calibration)
        from collections import Counter
        coh = {}
        for r in recs:
            calls = r["calls"].values() if isinstance(r["calls"], dict) else r["calls"]
            for c in calls:
                kind = c["call_id"].split("/")[-1].split("#")[0]
                p = c.get("parsed") or {}
                if p.get("probs_valid") and p.get("verdict_valid"):
                    coh.setdefault(kind, Counter())["mismatch" if "verdict_prob_mismatch" in p.get("flags", []) else "coherent"] += 1
        res["verdict_probability_coherence_by_call"] = {k: {**dict(v), "mismatch_rate": v["mismatch"] / sum(v.values())}
                                                       for k, v in sorted(coh.items())}
        res["shortcut_baselines"] = shortcut_baselines(recs[0]["salt"], sorted(r["world_index"] for r in recs))
        result[rid] = res
    (out_dir / "s3_summary.json").write_text(json.dumps(result, indent=1, sort_keys=True, default=str))
    digest = hashlib.sha256((out_dir / "s3_summary.json").read_bytes()).hexdigest()
    return {"digest": digest, "runs": {k: {kk: v.get(kk) for kk in ("n_worlds", "primary_D_minus_B_balanced_accuracy")}
                                       for k, v in result.items() if isinstance(v, dict)}}


# =========================================================================== iteration 2 (task s3-tasks-v2)
#
# Reads the SAVED task objects of each record (never regenerates defaults).  Unit = base world; transformed
# items (complements, renamings) are nested diagnostics, never extra worlds.  Baselines are fitted on separate
# development TRAINING worlds (salt S3_BASELINE_TRAIN_SALT), persisted, and evaluated on the identical saved
# panel items the models answered.  Prospective pilot focus: T_cert - T_label target-item accuracy.

S3_BASELINE_TRAIN_SALT = "dev-v2-s3-train"
S3_BASELINE_TRAIN_WORLDS = 300
V2_ITEM_ARMS = ("A", "B2", "C", "D_cert", "D_label", "D_sample", "E")
V2_TARGET_ARMS = ("A_T", "T_A", "T_B2", "T_cert", "T_label", "T_sample")


def _features(item: dict, budget: int) -> tuple:
    q = item["query"]
    return (budget, q["horizon"], q["intervention"]["kind"], q["target"]["value"])


def fit_baselines(out_path: Path, n_worlds: int = S3_BASELINE_TRAIN_WORLDS) -> dict:
    """Fit trivial + surface baselines on development TRAINING worlds only (no model calls) and persist them."""
    from collections import Counter, defaultdict

    from ..s3_tasks import make_s3_items_v2
    tab, allv = defaultdict(Counter), Counter()
    roles = Counter()
    for i in range(n_worlds):
        d = make_s3_items_v2(S3_BASELINE_TRAIN_SALT, i)
        B = d["private"]["budget"]
        for it in d["private"]["items"]:
            role = it["role"].split(":")[0]
            if role not in ("balanced", "natural", "transfer_target"):
                continue
            roles[role] += 1
            tab[_features(it, B)][it["verdict"]] += 1
            allv[it["verdict"]] += 1
    maj = sorted(allv.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    rule = {"|".join(map(str, f)): sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for f, c in tab.items()}
    art = {"artifact": "s3-baselines-v2", "train_salt": S3_BASELINE_TRAIN_SALT, "train_worlds": n_worlds,
           "train_items_by_role": dict(roles), "features": ["budget", "horizon", "intervention_kind", "target_value"],
           "majority_verdict": maj, "surface_rule": rule, "train_verdict_counts": dict(allv),
           "tie_break": "most frequent, then alphabetical"}
    Path(out_path).write_text(json.dumps(art, indent=1, sort_keys=True))
    art["sha256"] = hashlib.sha256(Path(out_path).read_bytes()).hexdigest()
    return art


def _final_v2(r: dict, arm: str, i: int) -> dict | None:
    v = r["arms"].get(arm, {}).get(str(i))
    return v["final"] if v else None


def _brier(f: dict | None, y: str) -> float | None:
    if not f or not f.get("probs_valid"):
        return None
    return sum((f["probabilities"][k] - (1.0 if k == y else 0.0)) ** 2 for k in VERDICT_LABELS)


def per_world_v2(records: list[dict], baselines: dict) -> list[dict]:
    from ..s3_tasks import COMPLEMENT_VERDICT
    rows = []
    for r in records:
        tp = r["task_private"]
        items = tp["items"]
        B = tp["budget"]
        y = [it["verdict"] for it in items]
        role = [it["role"] for it in items]
        bal = [i for i, x in enumerate(role) if x == "balanced"]
        nat = [i for i, x in enumerate(role) if x == "natural"]
        tgt = [i for i, x in enumerate(role) if x == "transfer_target"]
        row = {"world_id": r["world_id"], "world_index": r["world_index"], "budget": B, "status": r["world_status"],
               "arms": {}, "target": {}, "baselines": {}, "confusion": {}, "transforms": {}, "revisions": {}}
        for arm in V2_ITEM_ARMS:
            for name, idx in (("balanced", bal), ("natural", nat)):
                fs = [(_final_v2(r, arm, i), y[i]) for i in idx]
                if not fs or any(f is None for f, _ in fs):
                    continue
                row["arms"][f"{arm}|{name}"] = {
                    "n": len(fs), "correct": sum(int(f["verdict_valid"] and f["verdict"] == t) for f, t in fs),
                    "valid": sum(int(f["verdict_valid"]) for f, _ in fs),
                    "brier": [_brier(f, t) for f, t in fs],
                    "by_class": {c: [sum(1 for f, t in fs if t == c),
                                     sum(1 for f, t in fs if t == c and f["verdict_valid"] and f["verdict"] == c)]
                                 for c in VERDICT_LABELS}}
                if name == "balanced":
                    conf = {}
                    for f, t in fs:
                        k = f"{t}->{f['verdict'] if f['verdict_valid'] else 'invalid:' + f['status']}"
                        conf[k] = conf.get(k, 0) + 1
                    row["confusion"][arm] = conf
        for arm in V2_TARGET_ARMS:
            for i in tgt:
                f = _final_v2(r, arm, i)
                if f is not None:
                    row["target"][arm] = {"correct": int(f["verdict_valid"] and f["verdict"] == y[i]),
                                          "valid": int(f["verdict_valid"]), "truth": y[i], "brier": _brier(f, y[i])}
        for arm in ("B2", "C", "D_cert", "D_label", "D_sample"):
            c = {"wrong_to_correct": 0, "correct_to_wrong": 0, "correct_to_correct": 0, "wrong_to_wrong": 0}
            for i in bal + nat:
                a, b = _final_v2(r, "A", i), _final_v2(r, arm, i)
                if a is None or b is None:
                    continue
                ca = int(a["verdict_valid"] and a["verdict"] == y[i])
                cb = int(b["verdict_valid"] and b["verdict"] == y[i])
                c[{(0, 1): "wrong_to_correct", (1, 0): "correct_to_wrong", (1, 1): "correct_to_correct",
                   (0, 0): "wrong_to_wrong"}[(ca, cb)]] += 1
            row["revisions"][arm] = c
        # transformed items (arm A only, nested under the world)
        comp, ren = [], []
        for i, x in enumerate(role):
            if x.startswith("complement_of") or x.startswith("renamed_of"):
                b = int(x.split(":")[1])
                fa, fb = _final_v2(r, "A", b), _final_v2(r, "A", i)
                if fa is None or fb is None:
                    continue
                both = fa["verdict_valid"] and fb["verdict_valid"]
                if x.startswith("complement_of"):
                    comp.append({"consistent": int(both and fb["verdict"] == COMPLEMENT_VERDICT[fa["verdict"]]),
                                 "both_valid": int(both), "correct_transformed": int(fb["verdict_valid"] and
                                                                                    fb["verdict"] == y[i])})
                else:
                    ren.append({"same_verdict": int(both and fb["verdict"] == fa["verdict"]), "both_valid": int(both),
                                "correct_transformed": int(fb["verdict_valid"] and fb["verdict"] == y[i])})
        row["transforms"] = {"complement": comp, "renaming": ren}
        # baselines on the identical saved items
        for name in ("majority", "surface_rule"):
            st = {}
            for lab, idx in (("balanced", bal), ("natural", nat), ("target", tgt)):
                preds = [baselines["majority_verdict"] if name == "majority" else
                         baselines["surface_rule"].get("|".join(map(str, _features(items[i], B))),
                                                       baselines["majority_verdict"]) for i in idx]
                st[lab] = {"n": len(idx), "correct": sum(int(p == y[i]) for p, i in zip(preds, idx)),
                           "by_class": {c: [sum(1 for i in idx if y[i] == c),
                                            sum(1 for p, i in zip(preds, idx) if y[i] == c and p == c)]
                                        for c in VERDICT_LABELS}}
            row["baselines"][name] = st
        rows.append(row)
    return rows


def _boot_mean_diff(vals_a, vals_b, reps, seed):
    d = np.array(vals_a, float) - np.array(vals_b, float)
    if not len(d):
        return None
    r = cluster_bootstrap(lambda idx: float(d[idx].mean()), len(d), reps, seed)
    r.update(mean_a=float(np.mean(vals_a)), mean_b=float(np.mean(vals_b)))
    return r


def _bal_acc(rows, key):
    cnt = np.zeros((len(VERDICT_LABELS), 2))
    for r in rows:
        st = r["arms"].get(key)
        if st:
            for k, c in enumerate(VERDICT_LABELS):
                cnt[k] += st["by_class"][c]
    return balanced_accuracy_from_counts(cnt) if cnt[:, 0].sum() else None


def summarize_v2(records: list[dict], baselines: dict, reps: int = 5000, seed: int = 20261109) -> dict:
    rows = per_world_v2(records, baselines)
    n = len(rows)
    out = {"n_worlds": n, "world_status": {}, "arms": {}, "target": {}, "contrasts": {}, "baselines": {},
           "transforms": {}, "revisions": {}, "confusion_balanced": {}}
    for r in rows:
        out["world_status"][r["status"]] = out["world_status"].get(r["status"], 0) + 1
    for key in sorted({k for r in rows for k in r["arms"]}):
        sts = [r["arms"][key] for r in rows if key in r["arms"]]
        br = [b for s in sts for b in s["brier"] if b is not None]
        nit = sum(s["n"] for s in sts)
        out["arms"][key] = {"items": nit, "accuracy": sum(s["correct"] for s in sts) / nit,
                            "balanced_accuracy": _bal_acc(rows, key), "valid_rate": sum(s["valid"] for s in sts) / nit,
                            "brier_valid_only_mean": float(np.mean(br)) if br else None,
                            "probability_vector_valid_rate": len(br) / nit}
    for arm in V2_TARGET_ARMS:
        t = [r["target"][arm] for r in rows if arm in r["target"]]
        if t:
            out["target"][arm] = {"n_worlds": len(t), "accuracy": float(np.mean([x["correct"] for x in t])),
                                  "valid_rate": float(np.mean([x["valid"] for x in t]))}

    def paired_target(a, b):
        pr = [(r["target"][a]["correct"], r["target"][b]["correct"]) for r in rows
              if a in r["target"] and b in r["target"]]
        return _boot_mean_diff([x for x, _ in pr], [y for _, y in pr], reps, seed) if pr else None

    def paired_items(a, b, part="balanced"):
        pr = [(r["arms"][f"{a}|{part}"]["correct"] / r["arms"][f"{a}|{part}"]["n"],
               r["arms"][f"{b}|{part}"]["correct"] / r["arms"][f"{b}|{part}"]["n"]) for r in rows
              if f"{a}|{part}" in r["arms"] and f"{b}|{part}" in r["arms"]]
        return _boot_mean_diff([x for x, _ in pr], [y for _, y in pr], reps, seed) if pr else None

    out["contrasts"]["FOCUS|T_cert-T_label|target_accuracy"] = paired_target("T_cert", "T_label")
    for a, b in (("T_sample", "T_B2"), ("T_cert", "T_B2"), ("T_label", "T_B2"), ("T_A", "A_T"), ("T_B2", "A_T"),
                 ("T_cert", "A_T")):
        out["contrasts"][f"secondary|{a}-{b}|target_accuracy"] = paired_target(a, b)
    for a, b in (("D_cert", "D_label"), ("D_sample", "B2"), ("B2", "A"), ("C", "A"), ("D_label", "B2"),
                 ("D_cert", "B2"), ("C", "B2")):
        out["contrasts"][f"secondary|{a}-{b}|balanced_items_accuracy"] = paired_items(a, b)
    for name in ("majority", "surface_rule"):
        for lab in ("balanced", "natural", "target"):
            st = [r["baselines"][name][lab] for r in rows]
            nit = sum(s["n"] for s in st)
            cnt = np.zeros((len(VERDICT_LABELS), 2))
            for s in st:
                for k, c in enumerate(VERDICT_LABELS):
                    cnt[k] += s["by_class"][c]
            out["baselines"][f"{name}|{lab}"] = {"items": nit, "accuracy": sum(s["correct"] for s in st) / nit if nit else None,
                                                 "balanced_accuracy": balanced_accuracy_from_counts(cnt) if nit else None}
    comp = [c for r in rows for c in r["transforms"]["complement"]]
    ren = [c for r in rows for c in r["transforms"]["renaming"]]
    out["transforms"] = {
        "complement_pairs": len(comp),
        "complement_consistency_given_both_valid": (sum(c["consistent"] for c in comp) / max(1, sum(c["both_valid"] for c in comp))),
        "complement_item_accuracy_A": float(np.mean([c["correct_transformed"] for c in comp])) if comp else None,
        "renaming_pairs": len(ren),
        "renaming_same_verdict_given_both_valid": (sum(c["same_verdict"] for c in ren) / max(1, sum(c["both_valid"] for c in ren))),
        "renamed_item_accuracy_A": float(np.mean([c["correct_transformed"] for c in ren])) if ren else None,
        "note": "transformed items are nested under their base world (arm A only); not independent worlds"}
    for arm in ("B2", "C", "D_cert", "D_label", "D_sample"):
        tot = {}
        for r in rows:
            for k, v in r["revisions"].get(arm, {}).items():
                tot[k] = tot.get(k, 0) + v
        out["revisions"][f"{arm}_vs_A"] = tot
    for arm in V2_ITEM_ARMS:
        tot = {}
        for r in rows:
            for k, v in r["confusion"].get(arm, {}).items():
                tot[k] = tot.get(k, 0) + v
        out["confusion_balanced"][arm] = dict(sorted(tot.items()))
    return out


def costs_v2(records: list[dict]) -> dict:
    """Realized tokens/time per arm (standalone logical cost) and parse/truncation status of every call."""
    from collections import Counter
    st, fin, coh = Counter(), Counter(), Counter()
    per_arm = {}
    for r in records:
        for arm, c in r["cost"]["logical_standalone_by_arm"].items():
            a = per_arm.setdefault(arm, {"attempts": 0, "latency_s": 0.0, "prompt_tokens": 0, "completion_tokens": 0})
            a["attempts"] += c["attempts"]
            a["latency_s"] += c["latency_s"]
            a["prompt_tokens"] += c["prompt_tokens"] or 0
            a["completion_tokens"] += c["completion_tokens"] or 0
        for call in r["calls"].values():
            st[call["parsed"]["status"]] += 1
            fin[str(call["attempts"][-1].get("finish_reason"))] += 1
            p = call["parsed"]
            if p.get("probs_valid") and p.get("verdict_valid"):
                coh["mismatch" if "verdict_prob_mismatch" in p.get("flags", []) else "coherent"] += 1
    ctx = {}
    for r in records:
        for arm in V2_TARGET_ARMS[1:]:
            for v in r["arms"].get(arm, {}).values():
                ctx.setdefault(arm, []).append(v.get("context_chars", 0))
    return {"physical_attempts": sum(r["cost"]["physical"]["attempts"] for r in records),
            "physical_latency_s": round(sum(r["cost"]["physical"]["latency_s"] for r in records), 1),
            "logical_standalone_by_arm": per_arm, "parse_status": dict(st), "finish_reason": dict(fin),
            "verdict_probability_coherence": dict(coh),
            "probe_source_context_chars_median": {k: float(np.median(v)) for k, v in ctx.items()}}


def analyze_v2(run_dirs: list[Path], out_dir: Path, baselines_path: Path, reps: int = 5000) -> dict:
    from ..experiments.s3 import check_kinds
    from ..runner import load_run
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base_bytes = Path(baselines_path).read_bytes()
    baselines = json.loads(base_bytes)
    result = {"analysis_version": "s3-analysis-v2", "baselines": {"path": str(baselines_path),
                                                                   "sha256": hashlib.sha256(base_bytes).hexdigest(),
                                                                   "train_salt": baselines["train_salt"]},
              "runs": {}}
    panels = {}
    for d in run_dirs:
        lr = load_run(Path(d))
        if lr["layout"] != "v2":
            raise SystemExit(f"{d}: legacy S3 layout; v1 pilots are analysed by the historical code")
        recs = list(lr["results"].values())
        kind = check_kinds(recs)
        if any(r["salt"] == baselines["train_salt"] for r in recs):
            raise SystemExit("panel worlds overlap the baseline training salt")
        plan = lr["plan"]
        rid = plan["run_id"]
        model = plan["config"]["provider"]["model"]
        panel = plan["config"].get("panel")
        bal_short = {}
        for r in recs:
            for s in r["task_private"]["balance_shortfalls"]:
                k = f"B{s['budget']}|h{s['horizon']}|{s['kind']}|want={s['target_verdict']}|{s['role']}"
                bal_short[k] = bal_short.get(k, 0) + 1
        res = {"model": model, "panel": panel, "provider_kind": kind, "plan_sha256": plan["plan_sha256"],
               "source_tree_sha256": plan["source_tree_sha256"], "planned_worlds": len(plan["items"]),
               "ok_worlds": len(recs), "failed_worlds": len(lr["failures"]), "missing_worlds": len(lr["missing"]),
               "provider_metadata": recs[0].get("provider_metadata") if recs else None,
               "balance_shortfalls": dict(sorted(bal_short.items())),
               "summary": summarize_v2(recs, baselines, reps) if recs else None, "cost": costs_v2(recs) if recs else None}
        result["runs"][rid] = res
        panels.setdefault((model, panel), []).append(rid)
    (out_dir / "s3_v2_summary.json").write_text(json.dumps(result, indent=1, sort_keys=True, default=str))
    digest = hashlib.sha256((out_dir / "s3_v2_summary.json").read_bytes()).hexdigest()
    return {"digest": digest, "summary": str(out_dir / "s3_v2_summary.json"),
            "focus": {rid: (v["summary"] or {}).get("contrasts", {}).get("FOCUS|T_cert-T_label|target_accuracy")
                      for rid, v in result["runs"].items()}}
