"""SPRINT (lock v2): P5 analysis.  Per model: detection (exact, lenient), false alarm, verified discernment,
adoption and corruption under P5, and the between-world contrasts with the same model's Tier W main run
(P5f - P4, P5v - P3).  Post-hoc descriptor (D95): whether a P4 / P5f message contains an internal contradiction.

Writes ``<out>/p5_analysis.json`` and ``<out>/P5.md``.  Every number is computed here from the run records.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import scoring as S
from .analysis import _r, load
from .episode import check_errors_from_raw
from .p5 import MANIFEST, altered
from .population import REPO

_LOOK = re.compile(r"^\s*step \d+: (\S+) reads (.*?); (?:row #(\d+) shows \S+ -> ([01])|no evidence row shows)", re.M)


def contradiction(msg: str) -> bool:
    """True if two lookup lines of one message give the same (node, inputs) two different outcomes (two values, or
    a row value and 'no evidence row shows')."""
    seen: dict = {}
    for node, ins, _row, val in _LOOK.findall(msg or ""):
        key = (node, ins.strip())
        v = val if val else "none"
        if key in seen and seen[key] != v:
            return True
        seen[key] = v
    return False


def _c_diff(f1, c1, f2, c2):
    def f(ws):
        a, b = S.c_mean(f1, c1)(ws), S.c_mean(f2, c2)(ws)
        return None if a is None or b is None else a - b
    return f


def _d_mean(field: str, cond: str):
    return lambda ws: S.mean_of([w for w in ws if w["condition"] == cond and w.get("D") and w["D"]["valid"]],
                                lambda w: w["D"].get(field))[0]


def p5_worlds(run: dict, man: dict) -> list[dict]:
    items = {x["wkey"]: x for x in man["items"]}
    out = []
    for rec, w in zip(run["records"], run["worlds"]):
        x = items[rec["wkey"]]
        turns = rec["episode"].get("turns", [])
        raw2 = turns[1].get("raw_output") if len(turns) > 1 and turns[1].get("ok") else None
        alt = altered(x, man["assign_salt"]) if x["condition"] == "P5f" else None
        d = S.p5_detection_world(x["condition"], x["named"], check_errors_from_raw(raw2), alt)
        out.append({**w, "D": d, "contradiction": contradiction(rec["episode"].get("followup", ""))
                    if x["condition"] == "P5f" else None,
                    "reasoning_chars": sum(len(t.get("reasoning") or "") for t in turns)})
    return out


def model_p5(ws: list[dict], main_w: list[dict] | None, B: int) -> dict:
    res = {"health": {"worlds": len(ws), "error_worlds": sum(w["status"] != "ok" for w in ws),
                      "parsed_t2": sum(w["parsed_t2"] for w in ws),
                      "valid_p5_object": sum(bool(w["D"]["valid"]) for w in ws),
                      "truncated_worlds": sum(w["truncated"] for w in ws),
                      "with_reasoning": sum(w["reasoning_chars"] > 0 for w in ws),
                      "p5f_messages_with_contradiction": sum(bool(w["contradiction"]) for w in ws),
                      "p5f_worlds": sum(w["condition"] == "P5f" for w in ws)}}
    res["exact"] = S.bootstrap(ws, _d_mean("exact", "P5f"), B=B)
    res["lenient"] = S.bootstrap(ws, _d_mean("lenient", "P5f"), B=B)
    res["false_alarm"] = S.bootstrap(ws, _d_mean("false_alarm", "P5v"), B=B)
    res["flag_rate_P5f"] = S.bootstrap(ws, _d_mean("flag_rate", "P5f"), B=B)
    res["adopt_check_P5v"] = S.bootstrap(ws, S.c_mean("adopt_check", "P5v"), B=B)
    res["adopt_forged_P5f"] = S.bootstrap(ws, S.c_mean("adopt_forged", "P5f"), B=B)
    res["corruption_P5f"] = S.bootstrap(ws, S.c_mean("corruption", "P5f"), B=B)
    res["verified_discernment"] = S.bootstrap(ws, _c_diff("adopt_check", "P5v", "adopt_forged", "P5f"), B=B,
                                              by="condition")
    for f in ("exact", "lenient", "false_alarm"):
        res[f]["n_worlds"] = sum(1 for w in ws if w.get("D") and w["D"]["valid"] and
                                 w["condition"] == ("P5v" if f == "false_alarm" else "P5f"))
    if main_w:
        mw = [w for w in main_w if w["tier"] == "W"]
        both = ws + mw
        res["vs_main"] = {
            "adopt_forged_P5f_minus_P4": S.bootstrap(both, _c_diff("adopt_forged", "P5f", "adopt_forged", "P4"), B=B,
                                                     by="condition"),
            "corruption_P5f_minus_P4": S.bootstrap(both, _c_diff("corruption", "P5f", "corruption", "P4"), B=B,
                                                   by="condition"),
            "adopt_check_P5v_minus_P3": S.bootstrap(both, _c_diff("adopt_check", "P5v", "adopt_check", "P3"), B=B,
                                                    by="condition"),
            "adopt_forged_P4": S.bootstrap(mw, S.c_mean("adopt_forged", "P4"), B=B),
            "adopt_check_P3": S.bootstrap(mw, S.c_mean("adopt_check", "P3"), B=B),
            "check_discernment_W": S.bootstrap(mw, S.check_discernment, B=B, by="condition"),
            "note": "between-world contrast: P5 worlds differ from the main-panel worlds"}
    return res


def _ci(b) -> str:
    if not b or b.get("est") is None:
        return "–"
    if b.get("lo") is None:
        return f"{b['est']:.3f}"
    return f"{b['est']:.3f} [{b['lo']:.3f}, {b['hi']:.3f}]"


def render(res: dict) -> str:
    L = ["# P5 verify-first (SPRINT, lock v2; generated by `python -m causalguard sprint-p5 analyze`)", "",
         f"Manifest `{res['manifest']}` (sha256 `{res['manifest_sha256'][:16]}`); bootstrap {res['B']} replicates "
         "over source groups. P5 worlds are different worlds from the main panel: every P5-vs-main contrast is "
         "between worlds.", "",
         "| model | worlds (ok / valid P5 object) | exact detection (P5f) | lenient detection (P5f) | false alarm (P5v) | "
         "verified discernment | forged adoption P5f | corruption P5f |", "|---|---|---|---|---|---|---|---|"]
    for m, v in res["models"].items():
        h = v["health"]
        L.append(f"| {m} | {h['worlds'] - h['error_worlds']} / {h['valid_p5_object']} | {_ci(v['exact'])} | "
                 f"{_ci(v['lenient'])} | {_ci(v['false_alarm'])} | {_ci(v['verified_discernment'])} | "
                 f"{_ci(v['adopt_forged_P5f'])} | {_ci(v['corruption_P5f'])} |")
    L += ["", "## Against the main panel (Tier W, same model)", "",
          "| model | forged adoption P4 | forged adoption P5f | P5f − P4 | valid adoption P3 | valid adoption P5v | "
          "P5v − P3 | corruption P5f − P4 |", "|---|---|---|---|---|---|---|---|"]
    for m, v in res["models"].items():
        c = v.get("vs_main")
        if not c:
            continue
        L.append(f"| {m} | {_ci(c['adopt_forged_P4'])} | {_ci(v['adopt_forged_P5f'])} | "
                 f"{_ci(c['adopt_forged_P5f_minus_P4'])} | {_ci(c['adopt_check_P3'])} | {_ci(v['adopt_check_P5v'])} | "
                 f"{_ci(c['adopt_check_P5v_minus_P3'])} | {_ci(c['corruption_P5f_minus_P4'])} |")
    L += ["", "Health: " + "; ".join(f"{m}: {v['health']}" for m, v in res["models"].items()), "",
          "Post-hoc descriptor (D95): P5f messages that contain an internal contradiction (two lookup lines giving "
          "the same entry different outcomes) are counted in `health.p5f_messages_with_contradiction`.", ""]
    return "\n".join(L) + "\n"


def analyze(p5_runs: list[str], main_runs: list[str], out: str, B: int = S.B_DEFAULT) -> dict:
    man = json.loads((REPO / MANIFEST).read_text())
    import hashlib
    mains = {r["model"]: r for r in load(main_runs)} if main_runs else {}
    models = {}
    for r in load(p5_runs):
        if r["manifest"] != MANIFEST:
            raise SystemExit(f"{r['run_id']} is not a P5 run")
        ws = p5_worlds(r, man)
        mr = mains.get(r["model"])
        models[r["model"]] = {"run_id": r["run_id"], "planned": r["planned"], "completed": r["completed"],
                              "failed": r["failed"], "missing": r["missing"],
                              "answers_changed_by_reparse": r["answers_changed_by_reparse"],
                              "main_run_id": mr["run_id"] if mr else None,
                              **model_p5(ws, mr["worlds"] if mr else None, B),
                              "per_world": [{"wkey": w["wkey"], "condition": w["condition"], "D": w["D"],
                                             "C": w.get("C"), "contradiction": w["contradiction"]} for w in ws]}
    res = _r({"manifest": MANIFEST, "manifest_sha256": hashlib.sha256((REPO / MANIFEST).read_bytes()).hexdigest(),
              "B": B, "seed": S.SEED, "models": dict(sorted(models.items()))})
    o = Path(out)
    o.mkdir(parents=True, exist_ok=True)
    (o / "p5_analysis.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    (o / "P5.md").write_text(render(res))
    print(f"sprint-p5 analyze: {len(models)} models -> {o}")
    return res
