"""R7 sprint gates (no model calls): the smoke gate and the five pre-run gates of protocol section 7, stage 2.

  python -m causalguard sprint-gates smoke --run-dir runs/r7-smoke-<tag>-v1 [...]  -> reports/R7_SMOKE.{md,json}
  python -m causalguard sprint-gates prerun --pilot-run-dir A --pilot-run-dir B     -> reports/R7_GATES.{md,json}

Every gate prints its denominator, refuses empty input and exits non-zero on failure.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from . import population as P
from . import scoring as S

SMOKE_PARSABLE = 0.90


def _load(run_dir: str) -> tuple[dict, list[dict]]:
    from ..runner import load_run
    r = load_run(Path(run_dir))
    recs = [r["results"][k] for k in sorted(r["results"])]
    return r, recs


def smoke_row(run_dir: str) -> dict:
    r, recs = _load(run_dir)
    model = r["plan"]["config"]["provider"]["model"]
    turns = [t for x in recs for t in x["episode"].get("turns", [])]
    n_req = len(turns)
    claims = sum(len(x["reference"]) for x in recs for _ in x["episode"].get("turns", []))
    valid = sum(len(t["answers"]) for t in turns)
    full = sum(len(t["answers"]) == 8 for t in turns)
    with_p = sum(a.get("probability") is not None for t in turns for a in t["answers"].values())
    trunc = sum(bool(t.get("truncated")) for t in turns)
    lat = [t["latency_s"] for t in turns if t.get("latency_s") is not None]
    comp = [t["completion_tokens"] for t in turns if t.get("completion_tokens") is not None]
    prompt = [t["prompt_tokens"] for t in turns if t.get("prompt_tokens") is not None]
    failures = len(r["failures"]) + len(r["missing"])
    share = valid / claims if claims else 0.0
    reasons = []
    if n_req == 0:
        reasons.append("no request completed")
    if share < SMOKE_PARSABLE:
        reasons.append(f"valid answers {valid}/{claims} < {SMOKE_PARSABLE:.0%}")
    if trunc:
        reasons.append(f"{trunc} truncated responses")
    if failures:
        reasons.append(f"{failures} failed or missing items")
    md = recs[0]["provider_metadata"] if recs else {}
    return {"run_dir": run_dir, "model": model, "worlds": len(recs), "requests": n_req, "claims": claims,
            "valid_answers": valid, "valid_share": share, "with_probability": with_p, "full_requests": full, "truncated": trunc,
            "failed_or_missing_items": failures, "seconds_per_request_median": statistics.median(lat) if lat else None,
            "seconds_per_request_mean": statistics.mean(lat) if lat else None,
            "completion_tokens_median": statistics.median(comp) if comp else None,
            "completion_tokens_max": max(comp) if comp else None,
            "prompt_tokens_max": max(prompt) if prompt else None,
            "quantization": md.get("quantization"), "model_digest": md.get("model_digest"),
            "chat_template_sha256": md.get("chat_template_sha256"),
            "pass": not reasons, "reasons": reasons}


def smoke(run_dirs: list[str], out: str = "reports/R7_SMOKE") -> int:
    if not run_dirs:
        raise SystemExit("smoke: no runs given")
    rows = [smoke_row(d) for d in run_dirs]
    Path(out + ".json").write_text(json.dumps({"gate": "smoke", "threshold_valid_share": SMOKE_PARSABLE,
                                                "rows": rows}, indent=1, sort_keys=True) + "\n")
    lines = ["# R7 smoke gate (pre-sprint)", "",
             f"Each candidate local model: 4 smoke worlds (smoke manifest, hash order), Task S and one Task P turn = "
             f"8 requests. Pass: valid claim answers >= {SMOKE_PARSABLE:.0%}, no truncated response, no failed item.",
             "A claim answer is valid when its verdict is valid; the probability is reported separately (D73).",
             "", "| model | requests | valid answers | with probability | full 8/8 replies | truncated | median s / request | "
             "median / max completion tokens | max prompt tokens | quantization | pass | reason |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        sec = f"{r['seconds_per_request_median']:.1f}" if r["seconds_per_request_median"] is not None else "-"
        lines.append(f"| {r['model']} | {r['requests']} | {r['valid_answers']}/{r['claims']} "
                     f"({r['valid_share']:.0%}) | {r['with_probability']} | {r['full_requests']}/{r['requests']} | {r['truncated']} | {sec} | "
                     f"{r['completion_tokens_median']} / {r['completion_tokens_max']} | {r['prompt_tokens_max']} | "
                     f"{r['quantization']} | {'yes' if r['pass'] else 'NO'} | {'; '.join(r['reasons']) or '-'} |")
    Path(out + ".md").write_text("\n".join(lines) + "\n")
    print(f"smoke: {sum(r['pass'] for r in rows)}/{len(rows)} models pass")
    return 0


# --------------------------------------------------------------------------- the five pre-run gates

def _scored(run_dir: str) -> tuple[str, list[dict]]:
    r, recs = _load(run_dir)
    return r["plan"]["config"]["provider"]["model"], [S.score_world(x) for x in recs]


def prerun(pilot_runs: list[str], surface_rule_path: str = "artifacts/sprint_surface_rule.json",
           prior_runs_roots: tuple[str, ...] = ("runs",), out: str = "reports/R7_GATES") -> int:
    if len(pilot_runs) < 2:
        raise SystemExit("prerun: two pilot runs are required")
    rule = json.loads((P.REPO / surface_rule_path).read_text())
    gates = {}
    main = json.loads((P.REPO / "artifacts/sprint_main_manifest.json").read_text())
    pilot = json.loads((P.REPO / "artifacts/sprint_pilot_manifest.json").read_text())
    smoke_m = json.loads((P.REPO / "artifacts/sprint_smoke_manifest.json").read_text())
    if not main["items"] or not pilot["items"]:
        raise SystemExit("prerun: empty manifest")

    # G1 ground truth: both exact engines (and SAT) agree on every main-panel claim
    from .build import engines
    e = engines("main")
    gates["G1_ground_truth"] = {"denominator_worlds": e["worlds"], "denominator_claims": e["claims_agree"] +
                                8 * e["worlds_fail"], "agree_worlds": e["worlds_agree"],
                                "pass": e["worlds_fail"] == 0 and e["worlds_agree"] == len(main["items"])}

    # G2 surface: surface rule balanced accuracy on pilot worlds <= midpoint(majority, checker)
    items = []
    for x in pilot["items"]:
        k = P.WorldKey.from_json(x)
        ev = P.evaluator(k)
        items.append((ev.public(), P.reference(ev, crosscheck_sat=False), k.to_json()))
    rows = S.reference_rows(items, rule)
    ba = {name: S.balanced_accuracy(ws) for name, ws in rows.items()}
    acc = {name: S.mean_of(ws, lambda w: w["S"]["accuracy"])[0] for name, ws in rows.items()}
    mid = (ba["majority_status"] + ba["checker"]) / 2
    gates["G2_not_readable_from_surface"] = {"denominator_worlds": len(items),
                                             "denominator_claims": sum(len(r) for _, r, _ in items),
                                             "balanced_accuracy": ba, "accuracy": acc, "threshold": mid,
                                             "pass": ba["surface_rule"] <= mid}

    # G3 floor / ceiling: each pilot model > 0.05 away from the checker and from the majority rule, on balanced
    # accuracy AND on plain accuracy (declared before the pilot: both must hold)
    g3 = {"denominators": {}, "models": {}, "pass": True}
    for d in pilot_runs:
        model, ws = _scored(d)
        mba = S.balanced_accuracy(ws)
        macc = S.mean_of(ws, lambda w: w["S"]["accuracy"])[0]
        ok = all(v is not None for v in (mba, macc)) and \
            abs(mba - ba["checker"]) > 0.05 and abs(mba - ba["majority_status"]) > 0.05 and \
            abs(macc - acc["checker"]) > 0.05 and abs(macc - acc["majority_status"]) > 0.05
        g3["models"][model] = {"balanced_accuracy": mba, "accuracy": macc, "pass": ok}
        g3["denominators"][model] = {"worlds": len(ws), "answered_claims": sum(w["S"]["answered"] for w in ws)}
        g3["pass"] &= ok
    gates["G3_not_at_floor_or_ceiling"] = g3

    # G4 no leak: every main-panel follow-up message passes the public-information audit
    from . import tasks as T
    n = ok = 0
    probs = []
    for x in main["items"]:
        k = P.WorldKey.from_json(x)
        pub = P.evaluator(k).public()
        r = T.leak_audit(pub, x["condition"], x["wording"], x["named"])
        n += 1
        ok += r["ok"]
        if not r["ok"]:
            probs.append({"wkey": x["wkey"], "problems": r["problems"]})
    gates["G4_no_leak"] = {"denominator_messages": n, "pass_messages": ok, "problems": probs, "pass": n > 0 and ok == n}

    # G5 disjoint: no main-panel mechanism or public task in the pilot, the smoke runs or any earlier model-facing run
    seen_mech, seen_task = set(), set()
    for m in (pilot, smoke_m):
        seen_mech |= {x["mechanism_sha256"] for x in m["items"]}
        seen_task |= {x["task_id"] for x in m["items"]}
    earlier = earlier_model_facing(prior_runs_roots)
    main_mech = {x["mechanism_sha256"] for x in main["items"]}
    main_task = {x["task_id"] for x in main["items"]}
    gates["G5_disjoint"] = {"denominator_main_worlds": len(main["items"]),
                            "pilot_and_smoke_worlds": len(pilot["items"]) + len(smoke_m["items"]),
                            "earlier_model_facing_mechanisms": earlier["mechanisms"],
                            "earlier_model_facing_runs": earlier["runs"],
                            "overlap_mechanism_pilot_smoke": len(main_mech & seen_mech),
                            "overlap_task_pilot_smoke": len(main_task & seen_task),
                            "overlap_mechanism_earlier": len(main_mech & earlier["mechanism_set"]),
                            "pass": not (main_mech & seen_mech) and not (main_task & seen_task) and
                            not (main_mech & earlier["mechanism_set"]) and len(main["items"]) > 0}
    allpass = all(g["pass"] for g in gates.values())
    Path(out + ".json").write_text(json.dumps({"gates": gates, "all_pass": allpass}, indent=1, sort_keys=True,
                                              default=sorted) + "\n")
    lines = ["# R7 pre-run gates (pre-sprint)", "", "| gate | denominator | value | threshold | pass |",
             "|---|---|---|---|---|"]
    g = gates
    lines.append(f"| G1 ground truth | {g['G1_ground_truth']['denominator_worlds']} main worlds, "
                 f"{g['G1_ground_truth']['denominator_claims']} claims | {g['G1_ground_truth']['agree_worlds']} worlds "
                 f"agree | all | {'yes' if g['G1_ground_truth']['pass'] else 'NO'} |")
    g2 = g["G2_not_readable_from_surface"]
    lines.append(f"| G2 surface | {g2['denominator_worlds']} pilot worlds, {g2['denominator_claims']} claims | surface "
                 f"balanced acc {g2['balanced_accuracy']['surface_rule']:.3f} (majority "
                 f"{g2['balanced_accuracy']['majority_status']:.3f}, checker {g2['balanced_accuracy']['checker']:.3f})"
                 f" | <= {g2['threshold']:.3f} | {'yes' if g2['pass'] else 'NO'} |")
    for m, v in g3["models"].items():
        lines.append(f"| G3 floor/ceiling: {m} | {g3['denominators'][m]['worlds']} pilot worlds, "
                     f"{g3['denominators'][m]['answered_claims']} answered claims | balanced acc "
                     f"{v['balanced_accuracy']:.3f}, acc {v['accuracy']:.3f} | > 0.05 from checker and majority "
                     f"(acc: checker {acc['checker']:.3f}, majority {acc['majority_status']:.3f}) | "
                     f"{'yes' if v['pass'] else 'NO'} |")
    g4 = g["G4_no_leak"]
    lines.append(f"| G4 no leak | {g4['denominator_messages']} main-panel follow-ups | {g4['pass_messages']} pass | all | "
                 f"{'yes' if g4['pass'] else 'NO'} |")
    g5 = g["G5_disjoint"]
    lines.append(f"| G5 disjoint | {g5['denominator_main_worlds']} main worlds vs {g5['pilot_and_smoke_worlds']} pilot+"
                 f"smoke worlds and {g5['earlier_model_facing_mechanisms']} earlier model-facing mechanisms | overlaps "
                 f"{g5['overlap_mechanism_pilot_smoke']}/{g5['overlap_task_pilot_smoke']}/"
                 f"{g5['overlap_mechanism_earlier']} | 0 | {'yes' if g5['pass'] else 'NO'} |")
    lines += ["", f"All gates pass: **{'yes' if allpass else 'NO'}**."]
    Path(out + ".md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-1:]))
    return 0 if allpass else 1


def earlier_model_facing(roots: tuple[str, ...]) -> dict:
    """Mechanisms of every model-facing run before R7: S4 pilot (S4 evaluator worlds), R5 Track A and R6 A2
    (investigation worlds).  Rebuilt from their run plans (salt/index/family or split/stratum/index)."""
    import hashlib
    mech, runs = set(), []

    def sha(net):
        return hashlib.sha256(json.dumps(net.canonical().to_json(), sort_keys=True).encode()).hexdigest()
    for root in roots:
        for d in sorted(Path(P.REPO / root).iterdir()):
            pl = d / "plan.json"
            if not pl.exists():
                continue
            plan = json.loads(pl.read_text())
            study = plan.get("study") or plan.get("config", {}).get("study")
            if study not in ("S4-PILOT", "R5-A-AI"):
                continue
            runs.append(d.name)
            for it in plan["items"]:
                p = it.get("payload") or {}
                if study == "S4-PILOT":
                    from ..s4.tasks import make_s4_world
                    mech.add(sha(make_s4_world(p["salt"], p["index"], p["family"]).net))
                else:
                    from ..r5.investigation import world
                    w = world(p["split"], p["stratum"], p["index"])
                    if w is not None:
                        mech.add(sha(w["net"]))
    return {"mechanisms": len(mech), "runs": runs, "mechanism_set": mech}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="causalguard sprint-gates")
    ap.add_argument("step", choices=("smoke", "prerun"))
    ap.add_argument("--run-dir", action="append", default=[])
    ap.add_argument("--pilot-run-dir", action="append", default=[])
    a = ap.parse_args(argv)
    if a.step == "smoke":
        return smoke(a.run_dir)
    return prerun(a.pilot_run_dir)


if __name__ == "__main__":
    sys.exit(main())
