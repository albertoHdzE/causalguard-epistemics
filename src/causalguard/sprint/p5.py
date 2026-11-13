"""SPRINT (lock v2, D88): P5 verify-first.  Manifest, pre-request gates, and the P5 analysis.

  python -m causalguard sprint-p5 manifest            -> artifacts/sprint_p5_manifest.json
  python -m causalguard sprint-p5 gates               -> reports/P5_GATES.{md,json}
  python -m causalguard sprint-p5 analyze --p5-run R ... --main-run R ... --out reports/sprint_all

Scores (``scoring.p5_detection_world``): exact detection, lenient detection, false alarm, flag rate; adoption and
corruption reuse ``scoring.check_adoption_world`` (P5v ~ P3, P5f ~ P4).  P5 worlds are different worlds from the main
panel, so P5f-vs-P4 and P5v-vs-P3 are between-world contrasts.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path

from . import population as P
from . import scoring as S

MANIFEST = "artifacts/sprint_p5_manifest.json"


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n")


def build_manifest() -> dict:
    m = P.manifest_p5()
    write_json(P.REPO / MANIFEST, m)
    print(f"P5 manifest: {m['n_worlds']} worlds, {dict(Counter((x['condition'], x['wording']) for x in m['items']))}")
    return m


@lru_cache(maxsize=None)
def _pub(wkey_json: str, design_salt: str) -> dict:
    return P.tier_public(P.WorldKey.from_json(json.loads(wkey_json)), "W", design_salt)[1]


def pub_of(x: dict) -> dict:
    w = {k: x[k] for k in ("split", "population", "stratum", "index", "source_key", "group")}
    return _pub(json.dumps(w, sort_keys=True), x.get("design_salt") or P.P5_DESIGN_SALT)


def altered(x: dict, salt: str) -> dict:
    from . import tierw as TW
    pub = pub_of(x)
    return {c: TW.altered_lines(pub, c, salt) for c in x["named"]}


# --------------------------------------------------------------------------- gates

def turn_texts(m: dict, main_manifest: str = "artifacts/sprint_main_manifest.json") -> dict:
    """Turn 1 of every P5 item = render_task + the SAME suffix as the main panel's Tier W turn 1; every P5 message
    minus the verification block and schema sentence is byte-identical to the P3 / P4 message of that wording."""
    from ..s4.pilot import render_task
    from . import tasks as T
    main = json.loads((P.REPO / main_manifest).read_text())
    xm = next(x for x in main["items"] if x["tier"] == "W")
    _, pm = P.tier_public(P.WorldKey.from_json(xm), "W")
    suf_main = T.user_prompt(pm)[len(render_task(pm)):]
    h_main = hashlib.sha256(suf_main.encode()).hexdigest()
    n = ok1 = ok2 = 0
    probs = []
    for x in m["items"]:
        pub = pub_of(x)
        n += 1
        u = T.user_prompt(pub)
        ok1 += u.startswith(render_task(pub)) and hashlib.sha256(u[len(render_task(pub)):].encode()).hexdigest() \
            == h_main
        for cond, base in (("P5v", "P3"), ("P5f", "P4")):
            for wd in (1, 2):
                msg = T.followup(pub, cond, wd, x["named"], m["assign_salt"])
                ref = T.followup(pub, base, wd, x["named"], m["assign_salt"])
                strip = msg.replace(T.P5_VERIFY + "\n", "").replace(" " + T.P5_SCHEMA, "")
                low = msg.lower()
                if any(w in low for w in ("forg", "phantom", "wrong_value", "hidden_row", "altered")):
                    probs.append({"wkey": x["wkey"], "condition": cond, "problem": "forgery vocabulary in message"})
                    continue
                if strip != ref:
                    probs.append({"wkey": x["wkey"], "condition": cond, "wording": wd})
                else:
                    ok2 += 1
    return {"denominator_items": n, "turn1_suffix_equal_main": ok1, "turn1_suffix_sha256": h_main,
            "turn1_suffix_sha256_from_code": T.turn1_suffix_sha256(),
            "p5_minus_insert_equals_p3p4": ok2, "denominator_messages": 4 * n, "problems": probs,
            "pass": ok1 == n and ok2 == 4 * n and h_main == T.turn1_suffix_sha256() and n > 0}


def scorer_selfcheck(m: dict) -> dict:
    """The scorer's planted-quote checks on every P5f named claim and every P5v named claim of the manifest:
    (1) the altered line itself (as rendered, with indentation and 'step t:') is an exact hit; (2) a different line
    of the same forged check is not an exact hit; (3) a lenient-only quote (cited row/'no row' and node, other
    words) is lenient and not exact; (4) a planted entry in P5v is a false alarm; (5) an empty list scores 0."""
    from . import tasks as T
    from . import tierw as TW
    salt = m["assign_salt"]
    c = Counter()
    probs = []
    for x in m["items"]:
        pub = pub_of(x)
        if x["condition"] == "P5f":
            alt = altered(x, salt)
            for cid in x["named"]:
                a = alt[cid]
                pk = TW.claim_package(pub, cid, salt)
                others = [ln for ln in pk["forged"]["lines"][1:] if S.norm_line(ln) not in
                          {S.norm_line(y) for y in a["lines"]}]
                r1 = S.p5_detection_world("P5f", [cid], [{"cid": cid, "line": a["lines"][0]}], {cid: a})
                c["planted_exact"] += 1
                c["planted_exact_hit"] += r1["exact"] == 1.0 and r1["lenient"] == 1.0
                if others:
                    r2 = S.p5_detection_world("P5f", [cid], [{"cid": cid, "line": others[0]}], {cid: a})
                    c["other_line"] += 1
                    c["other_line_not_exact"] += r2["exact"] == 0.0
                where = f"row #{a['row']:02d}" if a["row"] is not None else "no evidence row"
                lq = f"The line about {a['node']} citing {where} is wrong"
                r3 = S.p5_detection_world("P5f", [cid], [{"cid": cid, "line": lq}], {cid: a})
                c["lenient_only"] += 1
                c["lenient_only_ok"] += r3["exact"] == 0.0 and r3["lenient"] == 1.0
                r5 = S.p5_detection_world("P5f", [cid], [], {cid: a})
                c["empty"] += 1
                c["empty_zero"] += r5["exact"] == 0.0 and r5["lenient"] == 0.0
        else:
            for cid in x["named"]:
                line = T.checker_block(pub, "P5v", [cid], salt)[1]
                r4 = S.p5_detection_world("P5v", [cid], [{"cid": cid, "line": line}], None)
                c["planted_false_alarm"] += 1
                c["planted_false_alarm_counted"] += r4["false_alarm"] == 1.0
    ok = (c["planted_exact_hit"] == c["planted_exact"] and c["other_line_not_exact"] == c["other_line"] and
          c["lenient_only_ok"] == c["lenient_only"] and c["planted_false_alarm_counted"] == c["planted_false_alarm"]
          and c["empty_zero"] == c["empty"] and c["planted_exact"] > 0)
    return {**dict(c), "problems": probs, "pass": ok}


def gates(out: str = "reports/P5_GATES") -> int:
    from .build import engines_r7b
    from .gates import g4_r7b, g5_r7b, g6_checks
    m = json.loads((P.REPO / MANIFEST).read_text())
    res = {"manifest": MANIFEST, "manifest_sha256": hashlib.sha256((P.REPO / MANIFEST).read_bytes()).hexdigest()}
    res["G1"] = engines_r7b(MANIFEST, sat=True)
    res["G4"] = g4_r7b(MANIFEST, swap=True)
    res["G5"] = g5_r7b(MANIFEST, shown=("smoke", "pilot", "pilot2", "pilot3", "pilot4", "main"))
    res["G6"] = g6_checks(MANIFEST)
    res["turn_texts"] = turn_texts(m)
    res["scorer"] = scorer_selfcheck(m)
    alt = Counter()
    for x in m["items"]:
        if x["condition"] == "P5f":
            for a in altered(x, m["assign_salt"]).values():
                alt[f"{a['kind']}|{len(a['lines'])} line(s)"] += 1
    res["altered_lines"] = dict(sorted(alt.items()))
    res["pass"] = all(res[g]["pass"] for g in ("G1", "G4", "G5", "G6", "turn_texts", "scorer"))
    write_json(P.REPO / f"{out}.json", res)
    g1, g4, g5, g6, tt, sc = (res[k] for k in ("G1", "G4", "G5", "G6", "turn_texts", "scorer"))
    L = ["# P5 gates (sprint, lock v2; generated by `python -m causalguard sprint-p5 gates`)", "",
         f"Manifest `{MANIFEST}` sha256 `{res['manifest_sha256'][:16]}`: {m['n_worlds']} worlds "
         f"({dict(Counter(x['condition'] for x in m['items']))}), "
         f"{sum(len(x['named']) for x in m['items'])} named claims. Run before any P5 request.", "",
         "| gate | denominator | result | pass |", "|---|---|---|---|",
         f"| G1 engines (lazy = restricted engine = SAT) | {g1['worlds']} worlds, {g1['claims']} claims | "
         f"{g1['worlds_agree']}/{g1['worlds']} agree; cross-tier violations {len(g1['cross_tier_violations'])} | "
         f"{g1['pass']} |",
         f"| G4 leak audit (P5v, P5f x 2 wordings) | {g4['denominator_messages']} messages | "
         f"{g4['pass_messages']} pass; {g4['swap_unchanged']}/{g4['swap_messages']} unchanged under a mechanism swap "
         f"| {g4['pass']} |",
         f"| G5 disjoint from every world shown | {g5['denominator_main_worlds']} P5 worlds vs "
         f"{g5['shown_sprint_worlds']} sprint worlds (incl. main) + {g5['earlier_model_facing_mechanisms']} earlier "
         f"mechanisms | overlaps: mechanism {g5['overlap_mechanism_sprint']}, task {g5['overlap_task_sprint']}, "
         f"earlier {g5['overlap_mechanism_earlier']} | {g5['pass']} |",
         f"| G6 checks | {g6['W_claims']} named claims | valid passes verify {g6['W_p3_pass']}; forged fails verify "
         f"with a different status {g6['W_p4_fail']}; manifest mismatches {g6['manifest_mismatch']} | {g6['pass']} |",
         f"| turn 1 = main panel | {tt['denominator_items']} items | suffix sha256 `{tt['turn1_suffix_sha256'][:16]}` "
         f"equal in {tt['turn1_suffix_equal_main']}; P5 minus insert = P3/P4 in {tt['p5_minus_insert_equals_p3p4']}/"
         f"{tt['denominator_messages']} | {tt['pass']} |",
         f"| scorer (planted quotes) | {sc.get('planted_exact', 0)} P5f + {sc.get('planted_false_alarm', 0)} P5v "
         f"claims | exact hit {sc.get('planted_exact_hit', 0)}; other line not exact {sc.get('other_line_not_exact', 0)}"
         f"/{sc.get('other_line', 0)}; lenient-only {sc.get('lenient_only_ok', 0)}/{sc.get('lenient_only', 0)}; "
         f"false alarm {sc.get('planted_false_alarm_counted', 0)}; empty {sc.get('empty_zero', 0)}/"
         f"{sc.get('empty', 0)} | {sc['pass']} |", "",
         f"Forgery kinds and altered-line counts (P5f named claims): {res['altered_lines']}.",
         f"G6 forgery kinds over all named claims: {g6['forgery_kinds']}; status changes {g6['forged_status_W']}.",
         "", f"**All gates pass: {res['pass']}.**", ""]
    (P.REPO / f"{out}.md").write_text("\n".join(L) + "\n")
    print(f"P5 gates pass: {res['pass']}")
    return 0 if res["pass"] else 1


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="causalguard sprint-p5")
    ap.add_argument("step", choices=("manifest", "gates", "analyze"))
    ap.add_argument("--p5-run", action="append", default=[])
    ap.add_argument("--main-run", action="append", default=[])
    ap.add_argument("--out", default="reports/sprint_all")
    ap.add_argument("--B", type=int, default=S.B_DEFAULT)
    a = ap.parse_args(argv)
    if a.step == "manifest":
        build_manifest()
        return 0
    if a.step == "gates":
        return gates()
    from .p5_analysis import analyze
    analyze(a.p5_run, a.main_run, a.out, a.B)
    return 0


if __name__ == "__main__":
    sys.exit(main())
