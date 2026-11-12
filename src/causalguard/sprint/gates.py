"""R7 sprint gates (no model calls): the smoke gate and the five pre-run gates of protocol section 7, stage 2.

  python -m causalguard sprint-gates smoke --run-dir runs/r7-smoke-<tag>-v1 [...]  -> reports/R7_SMOKE.{md,json}
  python -m causalguard sprint-gates prerun --pilot-run-dir A --pilot-run-dir B     -> reports/R7_GATES.{md,json}

Every gate prints its denominator, refuses empty input and exits non-zero on failure.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
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
    from .episode import reparse
    r, recs = _load(run_dir)
    return r["plan"]["config"]["provider"]["model"], [S.score_world(reparse(x)[0]) for x in recs]


def prerun(pilot_runs: list[str], surface_rule_path: str = "artifacts/sprint_surface_rule.json",
           prior_runs_roots: tuple[str, ...] = ("runs",), out: str = "reports/R7_GATES") -> int:
    if len(pilot_runs) < 2:
        raise SystemExit("prerun: two pilot runs are required")
    rule = json.loads((P.REPO / surface_rule_path).read_text())
    gates = {}
    main = json.loads((P.REPO / "artifacts/sprint_main_manifest.json").read_text())
    pilot = json.loads((P.REPO / "artifacts/sprint_pilot_manifest.json").read_text())
    smoke_m = json.loads((P.REPO / "artifacts/sprint_smoke_manifest.json").read_text())
    pilot2 = json.loads((P.REPO / "artifacts/sprint_pilot2_manifest.json").read_text())
    pilot3 = json.loads((P.REPO / "artifacts/sprint_pilot3_manifest.json").read_text())
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
        _, recs = _load(d)
        same = S.reference_rows([(P.evaluator(P.WorldKey.from_json(x["world"])).public(), x["reference"], x["world"])
                                 for x in recs], None)        # checker / majority on THESE pilot worlds
        rba = {k: S.balanced_accuracy(v) for k, v in same.items()}
        racc = {k: S.mean_of(v, lambda w: w["S"]["accuracy"])[0] for k, v in same.items()}
        mba = S.balanced_accuracy(ws)
        macc = S.mean_of(ws, lambda w: w["S"]["accuracy"])[0]
        ok = all(v is not None for v in (mba, macc)) and \
            abs(mba - rba["checker"]) > 0.05 and abs(mba - rba["majority_status"]) > 0.05 and \
            abs(macc - racc["checker"]) > 0.05 and abs(macc - racc["majority_status"]) > 0.05
        g3["models"][model] = {"balanced_accuracy": mba, "accuracy": macc, "pass": ok,
                               "same_worlds_reference": {"balanced_accuracy": rba, "accuracy": racc}}
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
    for m in (pilot, pilot2, pilot3, smoke_m):
        seen_mech |= {x["mechanism_sha256"] for x in m["items"]}
        seen_task |= {x["task_id"] for x in m["items"]}
    earlier = earlier_model_facing(prior_runs_roots)
    main_mech = {x["mechanism_sha256"] for x in main["items"]}
    main_task = {x["task_id"] for x in main["items"]}
    gates["G5_disjoint"] = {"denominator_main_worlds": len(main["items"]),
                            "pilot_and_smoke_worlds": len(pilot["items"]) + len(pilot2["items"]) + len(pilot3["items"]) +
                            len(smoke_m["items"]),
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
                     f"{v['balanced_accuracy']:.3f}, acc {v['accuracy']:.3f} | > 0.05 from checker and majority on the same "
                     f"worlds (acc: checker {v['same_worlds_reference']['accuracy']['checker']:.3f}, majority "
                     f"{v['same_worlds_reference']['accuracy']['majority_status']:.3f}; balanced: majority "
                     f"{v['same_worlds_reference']['balanced_accuracy']['majority_status']:.3f}) | "
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
    ap.add_argument("step", choices=("smoke", "prerun", "r7b"))
    ap.add_argument("--run-dir", action="append", default=[])
    ap.add_argument("--pilot-run-dir", action="append", default=[])
    a = ap.parse_args(argv)
    if a.step == "smoke":
        return smoke(a.run_dir)
    if a.step == "r7b":
        return prerun_r7b(a.pilot_run_dir)
    return prerun(a.pilot_run_dir)


if __name__ == "__main__":
    sys.exit(main())


# =========================================================================== R7b gates (D79)

def g6_checks(manifest: str) -> dict:
    """G6 on every world of an R7b manifest, for EVERY named claim whatever the world's condition (the message
    that would be sent): Tier W, the valid derivation passes ``tierw.verify`` and the forged one fails it; Tier H,
    the forged status differs from the true status.  Also: the manifest's checker / forged statuses equal the ones
    recomputed from the public task."""
    from . import tasks as T
    from . import tierw as TW
    m = json.loads((P.REPO / manifest).read_text())
    if not m["items"]:
        raise SystemExit("g6: empty manifest")
    salt = m["assign_salt"]
    r = {"manifest": manifest, "W_claims": 0, "W_p3_pass": 0, "W_p4_fail": 0, "H_claims": 0, "H_forged_differs": 0,
         "manifest_mismatch": 0, "problems": [], "forgery_kinds": Counter(), "forged_status_W": Counter(),
         "forged_status_H": Counter()}
    for x in m["items"]:
        k = P.WorldKey.from_json(x)
        ev, pub = P.tier_public(k, x["tier"])
        again = T.check_statuses(pub, x["tier"], x["named"], salt)
        if any(again[f] != x[f] for f in ("checker_status", "forged_status", "forgery_kind")):
            r["manifest_mismatch"] += 1
            r["problems"].append({"wkey": x["wkey"], "problem": "manifest statuses differ from recomputation"})
        if x["tier"] == "W":
            tab = TW.Table.from_public(pub)
            for c in x["named"]:
                pk = TW.claim_package(pub, c, salt, tab)
                r["W_claims"] += 1
                ok = not TW.verify(pub, c, pk["tree"], pk["status"], pk["lines"])
                bad = TW.verify(pub, c, pk["forged"]["tree"], pk["forged"]["status"], pk["forged"]["lines"])
                r["W_p3_pass"] += ok
                r["W_p4_fail"] += bool(bad) and pk["forged"]["status"] != pk["status"]
                r["forgery_kinds"][pk["forged"]["kind"]] += 1
                r["forged_status_W"][f"{pk['status']}->{pk['forged']['status']}"] += 1
                if not ok or not bad:
                    r["problems"].append({"wkey": x["wkey"], "cid": c, "p3_ok": ok, "p4_problems": bad})
        else:
            for c in x["named"]:
                r["H_claims"] += 1
                d = x["forged_status"][c] != x["checker_status"][c]
                r["H_forged_differs"] += d
                r["forged_status_H"][f"{x['checker_status'][c]}->{x['forged_status'][c]}"] += 1
                if not d:
                    r["problems"].append({"wkey": x["wkey"], "cid": c, "problem": "forged status equals true"})
    for f in ("forgery_kinds", "forged_status_W", "forged_status_H"):
        r[f] = dict(sorted(r[f].items()))
    r["pass"] = (r["W_p3_pass"] == r["W_claims"] and r["W_p4_fail"] == r["W_claims"] and
                 r["H_forged_differs"] == r["H_claims"] and r["manifest_mismatch"] == 0 and
                 r["W_claims"] + r["H_claims"] > 0)
    print(f"G6 {manifest}: Tier W {r['W_p3_pass']}/{r['W_claims']} P3 pass, {r['W_p4_fail']}/{r['W_claims']} P4 fail; "
          f"Tier H {r['H_forged_differs']}/{r['H_claims']} forged differ; manifest mismatches {r['manifest_mismatch']}")
    return r


def g4_r7b(manifest: str, swap: bool = True) -> dict:
    """G4 on an R7b manifest: every follow-up of every condition (the five messages per world, not only the
    assigned one) passes ``tasks.leak_audit``; and, with ``swap``, the message is unchanged when the hidden
    mechanism is replaced by another fitting mechanism of the tier's class (evidence regenerated from it)."""
    from . import tasks as T
    m = json.loads((P.REPO / manifest).read_text())
    salt = m["assign_salt"]
    n = ok = swapped = swap_ok = 0
    probs = []
    for x in m["items"]:
        k = P.WorldKey.from_json(x)
        ev, pub = P.tier_public(k, x["tier"])
        alt_pub = _swapped_public(ev, pub, x["tier"]) if swap else None
        for cond in ("P0", "P1", "P2", "P3", "P4"):
            for wd in (1, 2):
                r = T.leak_audit(pub, cond, wd, x["named"], salt=salt)
                n += 1
                ok += r["ok"]
                if not r["ok"]:
                    probs.append({"wkey": x["wkey"], "condition": cond, "wording": wd, "problems": r["problems"]})
                if alt_pub is not None:
                    swapped += 1
                    same = T.followup(alt_pub, cond, wd, x["named"], salt) == T.followup(pub, cond, wd, x["named"],
                                                                                        salt)
                    swap_ok += same
                    if not same:
                        probs.append({"wkey": x["wkey"], "condition": cond, "problem": "changes under swap"})
    res = {"manifest": manifest, "denominator_messages": n, "pass_messages": ok, "swap_messages": swapped,
           "swap_unchanged": swap_ok, "problems": probs[:50],
           "pass": n > 0 and ok == n and swap_ok == swapped}
    print(f"G4 {manifest}: {ok}/{n} messages pass the audit; {swap_ok}/{swapped} unchanged under a mechanism swap")
    return res


def _swapped_public(ev, pub: dict, tier: str) -> dict:
    """The public task regenerated from ANOTHER fitting mechanism of the tier's class (every unobserved table entry
    filled by hash; listed inputs kept), with the same design.  Raises if the alternative does not fit."""
    import hashlib

    from .. import reference as R
    from ..s4.tasks import make_evidence, public_task
    from ..schema import Network, Rule
    from . import tierw as TW
    W = pub["wiring"] if tier == "W" else [sorted(r.canonical().inputs) for r in ev.world.net.rules]
    tab = TW.Table.from_public({**pub, "wiring": W})
    rules = []
    for j, ins in enumerate(W):
        t = 0
        for y in range(1 << len(ins)):
            key = (j, tuple((a, (y >> i) & 1) for i, a in enumerate(ins)))
            if key in tab.entries:
                b = tab.entries[key][0]
            else:
                b = hashlib.sha256(f"r7b-swap|{pub['task_id']}|{j}|{y}".encode()).digest()[0] & 1
            t |= b << y
        rules.append(Rule(tuple(ins), t))
    alt = Network(ev.world.net.n, tuple(rules))
    if not R.consistent(alt, ev.evidence):
        raise AssertionError("swapped mechanism does not fit the evidence")
    from ..generators import World
    w2 = World(ev.world.world_id, ev.world.study, ev.world.family, ev.world.population, ev.world.seed, alt,
               ev.world.max_indegree)
    ev2 = make_evidence(w2, ev.design)
    p2 = json.loads(json.dumps(public_task(w2, ev.design, ev2)))
    if tier == "W":
        p2["wiring"] = pub["wiring"]
        p2["tier"] = "W"
    if p2 != pub:
        raise AssertionError("public task changed under the swap")
    return p2


def g2_r7b(manifest: str = "artifacts/sprint_main_manifest.json") -> dict:
    """G2 per tier on the main-panel items (no model): the surface rule's balanced accuracy (Tier H: the R7 rule
    fitted on train Tier H items; Tier W: the R7b rule fitted on train Tier W items) against the 0.667 threshold,
    with the checker, always-not-settled and majority rows on the same items."""
    m = json.loads((P.REPO / manifest).read_text())
    rules = {"H": json.loads((P.REPO / "artifacts/sprint_surface_rule.json").read_text()),
             "W": json.loads((P.REPO / "artifacts/sprint_surface_rule_w.json").read_text())}
    out = {}
    for tier in P.TIERS:
        items = []
        for x in m["items"]:
            if x["tier"] != tier:
                continue
            k = P.WorldKey.from_json(x)
            ev, pub = P.tier_public(k, tier)
            items.append((pub, P.tier_reference(ev, pub, tier, crosscheck_sat=False), k.to_json()))
        rows = S.reference_rows(items, rules[tier])
        ba = {name: S.balanced_accuracy(ws) for name, ws in rows.items()}
        by_h = {}
        for h in (1, 2, 3):
            sub = [(p, {c: r for c, r in ref.items() if r["h"] == h}, w) for p, ref, w in items]
            sub_rows = S.reference_rows([s for s in sub if s[1]], rules[tier])
            by_h[h] = S.balanced_accuracy(sub_rows["surface_rule"])
        out[tier] = {"denominator_worlds": len(items), "denominator_claims": sum(len(r) for _, r, _ in items),
                     "balanced_accuracy": ba, "surface_by_horizon": by_h, "threshold": 0.667,
                     "surface_rule_sha256": rules[tier]["sha256"],
                     "pass": ba["surface_rule"] <= 0.667, "stop": ba["surface_rule"] > 0.80}
        print(f"G2 tier {tier}: surface balanced accuracy {ba['surface_rule']:.3f} on {len(items)} worlds "
              f"(checker {ba['checker']:.3f}, majority {ba['majority_status']:.3f}); by horizon {by_h}")
    return out


def g5_r7b(manifest: str = "artifacts/sprint_main_manifest.json", prior_runs_roots=("runs",)) -> dict:
    """G5: main-panel mechanisms and public tasks against every world shown to a model so far (R7 smoke and
    pilots 1-3, R7b pilot 4, and the earlier model-facing runs)."""
    main = json.loads((P.REPO / manifest).read_text())
    seen_mech, seen_task, n_seen = set(), set(), 0
    for s in ("smoke", "pilot", "pilot2", "pilot3", "pilot4"):
        mm = json.loads((P.REPO / f"artifacts/sprint_{s}_manifest.json").read_text())
        seen_mech |= {x["mechanism_sha256"] for x in mm["items"]}
        seen_task |= {x["task_id"] for x in mm["items"]}
        n_seen += len(mm["items"])
    earlier = earlier_model_facing(prior_runs_roots)
    mm_ = {x["mechanism_sha256"] for x in main["items"]}
    mt = {x["task_id"] for x in main["items"]}
    r = {"denominator_main_worlds": len(main["items"]), "shown_sprint_worlds": n_seen,
         "earlier_model_facing_mechanisms": earlier["mechanisms"], "earlier_runs": len(earlier["runs"]),
         "overlap_mechanism_sprint": len(mm_ & seen_mech), "overlap_task_sprint": len(mt & seen_task),
         "overlap_mechanism_earlier": len(mm_ & earlier["mechanism_set"])}
    r["pass"] = len(main["items"]) > 0 and not (r["overlap_mechanism_sprint"] or r["overlap_task_sprint"] or
                                                 r["overlap_mechanism_earlier"])
    print(f"G5: {r}")
    return r


def g3_r7b(pilot_runs: list[str]) -> dict:
    """G3 (recorded, not blocking): each pilot model's Tier W balanced accuracy and accuracy against the checker,
    always-not-settled and majority rows on the SAME worlds; 'floor' = within 0.05 of always-not-settled or
    majority on balanced accuracy, 'ceiling' = within 0.05 of the checker."""
    out = {}
    for d in pilot_runs:
        model, ws = _scored(d)
        _, recs = _load(d)
        for tier in P.TIERS:
            tw = [w for w in ws if w["tier"] == tier]
            tr = [x for x in recs if x.get("tier", "H") == tier]
            if not tw:
                continue
            items = [(P.tier_public(P.WorldKey.from_json(x["world"]), tier)[1], x["reference"], x["world"])
                     for x in tr]
            same = S.reference_rows(items, None)
            rba = {k: S.balanced_accuracy(v) for k, v in same.items()}
            mba = S.balanced_accuracy(tw)
            floor = mba is not None and min(abs(mba - rba["always_not_settled"]),
                                            abs(mba - rba["majority_status"])) <= 0.05
            ceil = mba is not None and abs(mba - rba["checker"]) <= 0.05
            out[f"{model}|{tier}"] = {"worlds": len(tw), "answered": sum(w["S"]["answered"] for w in tw),
                                      "balanced_accuracy": mba,
                                      "accuracy": S.mean_of(tw, lambda w: w["S"]["accuracy"])[0],
                                      "overclaim": S.mean_of(tw, lambda w: w["S"]["overclaim"])[0],
                                      "underclaim": S.mean_of(tw, lambda w: w["S"]["underclaim"])[0],
                                      "same_worlds": rba, "at_floor": floor, "at_ceiling": ceil}
    return out


def prerun_r7b(pilot_runs: list[str], out: str = "reports/R7B_GATES") -> int:
    """All six R7b gates; G3 recorded only.  G1 is read from reports/r7b/G1_main.json and G1_pilot4.json (written
    by ``sprint-build r7b-engines``), recomputed here if missing."""
    from .build import engines_r7b
    g = {}
    g1 = {}
    for name, man in (("main", "artifacts/sprint_main_manifest.json"),
                      ("pilot4", "artifacts/sprint_pilot4_manifest.json")):
        f = P.REPO / f"reports/r7b/G1_{name}.json"
        g1[name] = json.loads(f.read_text()) if f.exists() else engines_r7b(man)
    g["G1_ground_truth"] = {**g1, "pass": all(v["pass"] for v in g1.values())}
    g["G2_surface"] = g2_r7b()
    g["G2_surface"]["pass"] = all(v["pass"] for v in g["G2_surface"].values() if isinstance(v, dict))
    g["G3_floor_ceiling_recorded"] = g3_r7b(pilot_runs) if pilot_runs else {}
    g["G4_no_leak"] = {"main": g4_r7b("artifacts/sprint_main_manifest.json"),
                       "pilot4": g4_r7b("artifacts/sprint_pilot4_manifest.json")}
    g["G4_no_leak"]["pass"] = g["G4_no_leak"]["main"]["pass"] and g["G4_no_leak"]["pilot4"]["pass"]
    g["G5_disjoint"] = g5_r7b()
    g["G6_checks"] = {"main": g6_checks("artifacts/sprint_main_manifest.json"),
                      "pilot4": g6_checks("artifacts/sprint_pilot4_manifest.json")}
    g["G6_checks"]["pass"] = g["G6_checks"]["main"]["pass"] and g["G6_checks"]["pilot4"]["pass"]
    blocking = ("G1_ground_truth", "G2_surface", "G4_no_leak", "G5_disjoint", "G6_checks")
    allpass = all(g[k]["pass"] for k in blocking)
    Path(out + ".json").write_text(json.dumps({"gates": g, "blocking_pass": allpass}, indent=1, sort_keys=True,
                                              default=str) + "\n")
    L = ["# R7b pre-run gates (pre-sprint)", "", "Generated by `python -m causalguard sprint-gates r7b --pilot-run-dir "
         "...`. Every gate states its denominator. G3 is recorded, not blocking.", "",
         "| gate | denominator | value | rule | pass |", "|---|---|---|---|---|"]
    for name in ("main", "pilot4"):
        e = g1[name]
        L.append(f"| G1 ground truth ({name}) | {e['worlds']} worlds, {e['claims']} claims | {e['worlds_agree']} worlds "
                 f"agree (Tier W: lazy = restricted explicit engine = SAT; Tier H: explicit = D = SAT); cross-tier on "
                 f"{e['cross_tier_worlds']} worlds, {e['cross_tier_claims_settled_h']} claims settled on Tier H, "
                 f"{len(e['cross_tier_violations'])} violations | all agree, 0 violations | "
                 f"{'yes' if e['pass'] else 'NO'} |")
    for tier in P.TIERS:
        v = g["G2_surface"][tier]
        ba = v["balanced_accuracy"]
        L.append(f"| G2 surface, Tier {tier} | {v['denominator_worlds']} main worlds, {v['denominator_claims']} claims | "
                 f"surface {ba['surface_rule']:.3f} (checker {ba['checker']:.3f}, majority "
                 f"{ba['majority_status']:.3f}, always not settled {ba['always_not_settled']:.3f}); by horizon "
                 + ", ".join(f"h{h} {x:.3f}" for h, x in v["surface_by_horizon"].items() if x is not None) +
                 f" | <= 0.667 | {'yes' if v['pass'] else 'NO'} |")
    for k, v in g["G3_floor_ceiling_recorded"].items():
        L.append(f"| G3 (recorded) {k} | {v['worlds']} pilot worlds, {v['answered']} answered claims | balanced acc "
                 f"{v['balanced_accuracy']:.3f}, acc {v['accuracy']:.3f}, overclaim "
                 f"{v['overclaim'] if v['overclaim'] is None else round(v['overclaim'], 3)}, underclaim "
                 f"{v['underclaim'] if v['underclaim'] is None else round(v['underclaim'], 3)}; same worlds: checker "
                 f"{v['same_worlds']['checker']:.3f}, always not settled {v['same_worlds']['always_not_settled']:.3f}, "
                 f"majority {v['same_worlds']['majority_status']:.3f} | floor {v['at_floor']}, ceiling "
                 f"{v['at_ceiling']} | recorded |")
    for name in ("main", "pilot4"):
        v = g["G4_no_leak"][name]
        L.append(f"| G4 no leak ({name}) | {v['denominator_messages']} messages (5 conditions x 2 wordings x every "
                 f"world) | {v['pass_messages']} pass; {v['swap_unchanged']}/{v['swap_messages']} unchanged under a "
                 f"mechanism swap | all | {'yes' if v['pass'] else 'NO'} |")
    v = g["G5_disjoint"]
    L.append(f"| G5 disjoint | {v['denominator_main_worlds']} main worlds vs {v['shown_sprint_worlds']} sprint worlds "
             f"shown and {v['earlier_model_facing_mechanisms']} earlier model-facing mechanisms | overlaps "
             f"{v['overlap_mechanism_sprint']}/{v['overlap_task_sprint']}/{v['overlap_mechanism_earlier']} | 0 | "
             f"{'yes' if v['pass'] else 'NO'} |")
    for name in ("main", "pilot4"):
        v = g["G6_checks"][name]
        L.append(f"| G6 checks ({name}) | Tier W {v['W_claims']} named claims, Tier H {v['H_claims']} | Tier W: "
                 f"{v['W_p3_pass']} P3 pass the verifier, {v['W_p4_fail']} P4 fail it; Tier H: "
                 f"{v['H_forged_differs']} forged statuses differ; forgery kinds {v['forgery_kinds']} | all | "
                 f"{'yes' if v['pass'] else 'NO'} |")
    L += ["", f"Blocking gates pass: **{'yes' if allpass else 'NO'}**."]
    Path(out + ".md").write_text("\n".join(L) + "\n")
    print(L[-1])
    return 0 if allpass else 1
