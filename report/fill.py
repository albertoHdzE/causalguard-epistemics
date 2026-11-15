#!/usr/bin/env python3
"""Fill the report: report/report.src.md -> report/report.md, every number from the analysis outputs.

Data roots (from reports/sprint_all unless --data is given):
  A = analysis.json (main panel)   P = p5_analysis.json (P5)   R = report_data.json (accounting, smokes, predictions)
  F = fig4_background.json (Figure 4, Appendix E.1; bit counts of the objects drawn)
  X = pre-sprint development results, read from their committed analysis files (PRESPRINT; Appendix E.2, D128)

Placeholders
  {{A/models/q7/tiers/W/S/overclaim}}          a bootstrap record -> "0.514 [0.423, 0.600]"
  {{...|est}} point estimate   {{...|lo}} {{...|hi}}   {{...|n}} its n_worlds   {{...|int}}   {{...|usd}}
  {{...|pct}} a share as a percentage (no decimals)   {{...|abs}} absolute value of the estimate
  {{X/...|ci4}} a pre-sprint contrast record (estimate, ci95) -> "+0.0087 [0.0037, 0.0148]" (signed, 4 decimals)
  {{table:NAME}}                               a generated table (see TABLES)
Model aliases inside paths: g3 q7 g4 mi r1 ll cl ds (see ALIAS).

A record of a contrast that is not testable (D102(d)) renders as "not testable (n P3 x, P4 y)"; a missing model or
cell renders as "not run".  The build FAILS when a placeholder does not resolve, or when the source prose holds a
number outside a placeholder that is not a declared design constant (CONSTANTS, each with its reason).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ALIAS = {"g3": "google/gemma-3-4b", "q7": "qwen2.5:7b", "g4": "gemma-4-12b-it-mlx",
         "mi": "mistral-small-3.2-24b-instruct-2506-mlx", "r1": "deepseek-r1-distill-qwen-32b",
         "ll": "llama-3.3-70b-instruct", "cl": "claude-opus-5-5", "ds": "deepseek-v4-pro"}
NAME = {"google/gemma-3-4b": "gemma-3-4b", "qwen2.5:7b": "qwen2.5-7b", "gemma-4-12b-it-mlx": "gemma-4-12b†",
        "mistral-small-3.2-24b-instruct-2506-mlx": "mistral-small-24b", "deepseek-r1-distill-qwen-32b": "r1-distill-32b†",
        "llama-3.3-70b-instruct": "llama-3.3-70b", "claude-opus-5-5": "Claude Opus 5.5",
        "deepseek-v4-pro": "DeepSeek V4-Pro (low)‡"}
ORDER = list(NAME)
# Pre-sprint development results cited in Appendix E.2 (label, release, file, record path).  Read, never retyped.
PRESPRINT = {"r6_s": ("reports/development_r6/s_evaluation.json", "sub24/primary"),
             "r5_g": ("reports/development_r5/g_evaluation.json", "primary"),
             "r5_uniform": ("reports/development_r5/g_evaluation.json", "budgets/16/contrasts/uniform_minus_full_cgh"),
             "r5_shortest": ("reports/development_r5/g_evaluation.json",
                             "budgets/16/contrasts/shortest_cgh_prior_minus_full_cgh")}
# Numbers allowed in the prose without a placeholder: design constants fixed before any data, with the reason.
CONSTANTS = {
    "0": "zero as a bound or a share", "1": "list / one", "2": "list, two turns", "3": "list, three inputs per node, "
    "three statuses", "4": "list", "5": "list, conditions P0-P5", "6": "six local models", "8": "eight models, "
    "8-page limit", "12": "D102(d) minimum cell size; 12 Tier H worlds per cell", "24": "24 Tier W worlds per cell",
    "30": "30 P5v + 30 P5f worlds", "60": "60 P5 worlds", "95": "95 % intervals", "120": "Tier W worlds per model",
    "180": "main-panel worlds per model", "360": "main-panel requests per model", "520": "online request cap",
    "25": "DeepSeek spend stop (USD)", "32000": "DeepSeek completion cap", "16000": "token cap",
    "6000": "local token cap", "12000": "r1 token cap", "2026": "year", "0.15": "prediction thresholds (lock)",
    "0.10": "prediction threshold (lock)", "0.20": "prediction threshold (lock)", "0.25": "prediction threshold "
    "(lock)", "0.30": "prediction threshold (lock)", "0.50": "prediction threshold (lock)", "0.5": "prediction "
    "threshold (lock)", "0.60": "prediction threshold (lock)", "0.80": "prediction threshold (lock)", "14": "date",
    "13": "date", "15": "date", "12:00": "hard stop", "2000": "bootstrap replicates (lock)",
    "0.05": "D120 tolerance and D121 level (fixed by the director before computation)",
    "23:00": "v2-a4 pause deadline", "23:30": "v2-a4 hard stop", "600": "Claude request timeout (s), configs since v2-a3"}


def _get(D: dict, path: str):
    parts = path.split("/")
    cur = D[parts[0]]
    for p in parts[1:]:
        p = ALIAS.get(p, p)
        if isinstance(cur, list):
            cur = cur[int(p)] if p.isdigit() else next(x for x in cur if x.get("id") == p)
        elif isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            raise KeyError(path)
    return cur


def _num(x, nd=3) -> str:
    return "−" + f"{-x:.{nd}f}" if x < 0 else f"{x:.{nd}f}"


def fmt(v, f: str | None) -> str:
    if f == "ci4":
        def sg(x):
            return ("+" if x > 0 else "") + _num(x, 4)
        return f"{sg(v['estimate'])} [{_num(v['ci95'][0], 4)},\u00a0{_num(v['ci95'][1], 4)}]"
    if isinstance(v, dict) and v.get("not_testable"):
        return "not testable (" + ", ".join(f"n {c} {n}" for c, n in v["cell_n"].items()) + ")"
    if isinstance(v, dict) and "est" in v:
        if f == "n":
            return str(v.get("n_worlds"))
        if v["est"] is None:
            return "–"
        if f in ("est", None) and v.get("lo") is None:
            return _num(v["est"])
        if f == "est":
            return _num(v["est"])
        if f == "abs":
            return _num(abs(v["est"]))
        if f == "pct":
            return f"{round(100 * v['est'])} %"
        if f in ("lo", "hi"):
            return _num(v[f])
        return f"{_num(v['est'])} [{_num(v['lo'])},\u00a0{_num(v['hi'])}]"   # R10: never wrap inside the brackets
    if v is None:
        return "–"
    if f == "int" or isinstance(v, bool):
        return str(v)
    if f == "usd":
        return f"${v:.2f}"
    if f == "pct":
        return f"{round(100 * v)} %"
    if isinstance(v, float):
        return _num(v, 3 if f is None else int(f))
    return str(v)


# --------------------------------------------------------------------------- tables

def _models(d: dict) -> list[str]:
    return [m for m in ORDER if m in d] + [m for m in d if m not in ORDER]


def _cell(t: dict, c: str) -> str:
    x = t["cells"].get(c)
    if x is None:
        raise KeyError(f"cell {c} has no planned worlds")
    return f"{x['finished']}/{x['planned']}"


def _cell_short(t: dict, c: str) -> str:
    """R10: a complete cell shows its n (planned per cell is in the caption); an incomplete one finished/planned."""
    x = t["cells"][c]
    return str(x["finished"]) if x["finished"] == x["planned"] else f"{x['finished']}/{x['planned']}"


def _v(b, below=False) -> str:
    if below and b and b.get("est") is not None:
        return _num(b["est"]) + "*"
    return fmt(b, None)


def table_task_p(D) -> str:
    A = D["A"]
    L = ["| model | tier | n P3; P4 | P3: true adopted | P4: forged adopted | P4: corruption | "
         "check discernment |", "|" + "|".join("-" * w for w in (25, 3, 6, 17, 17, 17, 26)) + "|"]
    for m in _models(A["models"]):
        for tier in ("W", "H"):
            t = A["models"][m]["tiers"].get(tier)
            if not t:
                L.append(f"| {NAME.get(m, m)} | {tier} | 0 | | | | |")
                continue
            b3, b4 = t["cells"]["P3"]["below_min"], t["cells"]["P4"]["below_min"]
            L.append(f"| {NAME.get(m, m)} | {tier} | {_cell_short(t, 'P3')}; {_cell_short(t, 'P4')} | "
                     f"{_v(t['C']['adopt_check']['P3'], b3)} | {_v(t['C']['adopt_forged']['P4'], b4)} | "
                     f"{_v(t['C']['corruption']['P4'], b4)} | **{fmt(t['contrasts']['check_discernment'], None)}** |")
    return "\n".join(L)


def table_p5(D) -> str:
    P = D["P"]
    L = ["| model | n P5v; P5f | exact detection | lenient detection | false alarm | P5f: forged adopted | "
         "P5f − P4 | verified discern. |", "|" + "|".join("-" * w for w in (27, 6, 15, 15, 15, 15, 15, 15)) + "|"]
    for m in _models(P["models"]):
        v = P["models"][m]
        bf, bv = v["cells"]["P5f"]["below_min"], v["cells"]["P5v"]["below_min"]
        c = v.get("vs_main") or {}
        cv, cf = v["cells"]["P5v"], v["cells"]["P5f"]
        L.append(f"| {NAME.get(m, m)} | {cv['finished']}; {cf['finished']} | "
                 f"{_v(v['exact'], bf)} | {_v(v['lenient'], bf)} | {_v(v['false_alarm'], bv)} | "
                 f"{_v(v['adopt_forged_P5f'], bf)} | {fmt(c.get('adopt_forged_P5f_minus_P4'), None)} | "
                 f"{fmt(v['verified_discernment'], None) if not (bf or bv) else '–'} |")
    return "\n".join(L)


def table_task_s(D) -> str:
    A = D["A"]
    L = ["| model | tier | worlds | overclaim | underclaim | balanced accuracy | BA − surface rule |",
         "|" + "|".join("-" * w for w in (22, 3, 7, 18, 18, 18, 25)) + "|"]
    for tier in ("W", "H"):
        ref = next(v["tiers"][tier]["reference_rows"] for v in A["models"].values()
                   if tier in v["tiers"] and v["tiers"][tier]["reference_rows"])
        L.append(f"| *surface rule (reference)* | {tier} | | {fmt(ref['surface_rule']['overclaim'], None)} | "
                 f"{fmt(ref['surface_rule']['underclaim'], None)} | "
                 f"{fmt(ref['surface_rule']['balanced_accuracy'], None)} | |")
        for m in _models(A["models"]):
            t = A["models"][m]["tiers"].get(tier)
            if not t:
                continue
            n = sum(c["finished"] for c in t["cells"].values())
            p = sum(c["planned"] for c in t["cells"].values())
            L.append(f"| {NAME.get(m, m)} | {tier} | {n}/{p} | {fmt(t['S']['overclaim'], None)} | "
                     f"{fmt(t['S']['underclaim'], None)} | {fmt(t['S']['balanced_accuracy'], None)} | "
                     f"{fmt(t['contrasts'].get('balanced_accuracy_minus_surface'), None)} |")
    return "\n".join(L)


def table_predictions(D) -> str:
    L = ["| lock | by | prediction | outcome |", "|---|---|---|---|"]
    for p in D["R"]["predictions"]:
        L.append(f"| {p['lock']} | {p['by']} | {p['id']}: {p['text']} | **{p['outcome']}** |")
    return "\n".join(L)


def table_online(D) -> str:
    R, A, P = D["R"], D["A"], D["P"]
    L = ["| model | requests sent (all) | of which rejected without inference | worlds finished: main / P5 | "
         "recorded cost |",
         "|---|---|---|---|---|"]
    for m in ("claude-opus-5-5", "deepseek-v4-pro"):
        a = R["accounting"][m]
        mm = A["models"].get(m)
        main = f"{mm['completed']}/{mm['planned']}" if mm else "0"
        p5 = P["models"].get(m)
        p5s = f"{p5['completed']}/{p5['planned']}" if p5 else "0"
        cost = (f"${a['cost']['usd_notional']:.2f} (notional, subscription)" if m == "claude-opus-5-5" else
                f"${a['spend_usd_request_time']:.2f} at request-time price; ${a['spend_usd_upper']:.2f} upper bound")
        L.append(f"| {NAME[m]} | {a['requests_sent']} | {a['rejected_without_inference']} | {main} / {p5s} | {cost} |")
    return "\n".join(L)


def table_cells_online(D) -> str:
    A = D["A"]
    L = ["| model | tier | P0 | P1 | P2 | P3 | P4 |", "|---|---|---|---|---|---|---|"]
    for m in ("claude-opus-5-5", "deepseek-v4-pro"):
        mm = A["models"].get(m)
        for tier in ("W", "H"):
            t = (mm or {}).get("tiers", {}).get(tier)
            L.append(f"| {NAME[m]} | {tier} | " + " | ".join(_cell(t, c) if t else "0" for c in
                                                              ("P0", "P1", "P2", "P3", "P4")) + " |")
    return "\n".join(L)


def table_smokes(D) -> str:
    L = ["| condition | turns parsed (Tier W, Tier H) | turns stopped at the cap | completion tokens | pass |",
         "|---|---|---|---|---|"]
    names = {"deepseek_high_16k": "DeepSeek V4-Pro, effort high, cap 16 000",
             "deepseek_high_32k": "DeepSeek V4-Pro, effort high, cap 32 000",
             "deepseek_low_32k": "DeepSeek V4-Pro, effort low, cap 32 000", "claude": "Claude Opus 5.5, effort high"}
    for k, nm in names.items():
        s = D["R"]["smokes"].get(k)
        if not s:
            continue
        L.append(f"| {nm} | {s['parsed']}/{s['turns']} ({s['parsed_W']}/{s['turns_W']}, {s['parsed_H']}/"
                 f"{s['turns_H']}) | {s['stopped_at_cap']} | {s['completion_tokens_min']}–{s['completion_tokens_max']}"
                 f" | {'yes' if s['pass'] else 'no'} |")
    return "\n".join(L)


def table_p5_more(D) -> str:
    P = D["P"]
    L = ["| model | check_errors entries dropped by the locked parser (integer ids) | exact detection, ids accepted | "
         "false alarm, ids accepted | flagged the altered line | of those, forged status kept |",
         "|---|---|---|---|---|---|"]
    for m in _models(P["models"]):
        v = P["models"][m]
        h = v["health"]
        f = v["flagged_then_adopted"]
        dropped = h["check_errors_entries_int_cids_accepted"] - h["check_errors_entries"]
        L.append(f"| {NAME.get(m, m)} | {dropped} of {h['check_errors_entries_int_cids_accepted']} | "
                 f"{fmt(v['exact_int_cids'], None)} | {fmt(v['false_alarm_int_cids'], None)} | {f['flagged']} | "
                 f"{f['flagged_adopted']} |")
    return "\n".join(L)


def table_coding(D) -> str:
    C = D.get("C") or {}
    L = ["| model | P4: (a) own lookup | P4: (b) names a mismatch | P4: (c) names the altered line | "
         "P5f: (a) | P5f: (b) | P5f: (c) |", "|---|---|---|---|---|---|---|"]
    for m in _models(C):
        def cell(cond, code, m=m):
            v = C[m].get(cond)
            return f"{v[code]}/{v['n']}" if v else "–"
        L.append(f"| {NAME.get(m, m)} | " + " | ".join(cell(cd, c) for cd in ("P4", "P5f") for c in (
            "a_rederives_lookup", "b_names_mismatch", "c_names_altered_line")) + " |")
    return "\n".join(L)


def table_verdict_probability(D) -> str:
    """D120 (post-hoc): open claims given a definite verdict at turn 2, and whether the stated probability moved."""
    A = D["A"]
    L = ["| model | P2 worlds | open claims given a definite verdict (P2) | probability within 0.05 of turn 1 | "
         "mean abs. change | P0 reference: definite / kept |", "|" + "|".join("-" * w for w in (22, 6, 14, 18, 10, 16)) + "|"]
    for m in _models(A["models"]):
        t = A["models"][m]["tiers"].get("W")
        if not t:
            continue
        v, r = t["verdict_probability"]["P2"], t["verdict_probability"]["P0"]
        L.append(f"| {NAME.get(m, m)} | {v['worlds']} | {v['definite_on_open']} of {v['open_claims']} | "
                 f"{v['probability_kept']} of {v['with_both_probabilities']} | {fmt(v['mean_abs_dp'], None)} | "
                 f"{r['definite_on_open']} / {r['probability_kept']} |")
    return "\n".join(L)


def table_p5_cells(D) -> str:
    """R8: which worlds enter each P5 metric (planned -> finished -> valid turn-2 P5 object -> scored)."""
    P = D["P"]
    L = ["| model | P5v: planned / finished / valid turn 2 = in false alarm and adoption | P5f: planned / finished / "
         "valid turn 2 = in detection and adoption | turn 2 stopped at the token cap (P5v; P5f) |",
         "|" + "|".join("-" * w for w in (22, 26, 26, 16)) + "|"]
    for m in _models(P["models"]):
        h = P["models"][m]["health_by_cell"]
        v, f = h["P5v"], h["P5f"]
        L.append(f"| {NAME.get(m, m)} | {v['planned']} / {v['finished']} / {v['in_detection']} | "
                 f"{f['planned']} / {f['finished']} / {f['in_detection']} | {v['truncated']}; {f['truncated']} |")
    return "\n".join(L)


def table_supplement(D) -> str:
    """D118: Claude Tier H P3 + P4, post-freeze supplement (amendment v2-a4)."""
    s = D["R"].get("supplement")
    L = ["| post-freeze supplement (v2-a4) | n P3; P4 (finished / 12) | P3: true adopted | P4: forged adopted | "
         "P4: corruption | check discernment | Task S balanced accuracy |",
         "|" + "|".join("-" * w for w in (18, 12, 14, 14, 14, 18, 16)) + "|"]
    if not s or not s.get("cells"):
        L.append("| Claude Opus 5.5, Tier H | 0; 0 | – | – | – | – | – |")
        return "\n".join(L)
    c = s["cells"]
    b3, b4 = c["P3"]["below_min"], c["P4"]["below_min"]
    L.append(f"| Claude Opus 5.5, Tier H | {c['P3']['finished']}; {c['P4']['finished']} | "
             f"{_v(s['adopt_check_P3'], b3)} | {_v(s['adopt_forged_P4'], b4)} | {_v(s['corruption_P4'], b4)} | "
             f"{fmt(s['check_discernment'], None)} | {fmt(s['balanced_accuracy_H'], None)} |")
    return "\n".join(L)


def table_supplement_predictions(D) -> str:
    s = D["R"].get("supplement") or {}
    L = ["| prediction (lock v2) | scope | rule | supplement outcome |", "|---|---|---|---|"]
    for p in s.get("predictions") or []:
        L.append(f"| {p['id']} | {p['scope']} | {p['rule']} | **{p['outcome']}** |")
    return "\n".join(L)


TABLES = {"verdict_probability": table_verdict_probability, "p5_cells": table_p5_cells,
          "supplement": table_supplement, "supplement_predictions": table_supplement_predictions,
          "p5_more": table_p5_more, "coding": table_coding, "task_p": table_task_p, "p5": table_p5, "task_s": table_task_s, "predictions": table_predictions,
          "online": table_online, "cells_online": table_cells_online, "smokes": table_smokes}

PH = re.compile(r"\{\{\s*([^}|]+?)\s*(?:\|\s*([a-z0-9]+)\s*)?\}\}")


def check_prose(src: str) -> list[str]:
    """Numbers in the source outside placeholders, code, links, comments and identifiers."""
    s = re.sub(r"^---\n.*?\n---\n", "", src, flags=re.S)            # front matter
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = PH.sub(" ", s)
    s = re.sub(r"`[^`]*`", " ", s)
    s = re.sub(r"\]\([^)]*\)", "]", s)                               # link targets
    s = re.sub(r"https?://\S+", " ", s)
    s = re.sub(r"^#+\s*[A-Z]?\d+(\.\d+)*\.?", "#", s, flags=re.M)     # heading numbers
    s = re.sub(r"^\s*\d+\.\s", " ", s, flags=re.M)                   # numbered lists
    s = s.split("\n# References", 1)[0] + ("\n# Appendix A" + s.split("\n# Appendix A", 1)[1]
                                          if "\n# Appendix A" in s else "")   # the reference list
    s = re.sub(r"et al\.\s+\d{4}|\(\d{4}\)|arXiv:\d{4}\.\d{4,5}|Opus \d\.\d|§\d(\.\d)*|\{width=\d+%\}"
               r"|\(\d\)|#\d+|\b(?:Table|Figure) \d+", " ", s)                                     # citations, versions, refs, widths, items
    bad = []
    for m in re.finditer(r"(?<![\w.\-/])[−-]?\d+(?:[.:,]\d+)*(?![\w\-/])", s):
        tok = m.group(0).lstrip("−-").replace(",", "")
        if tok not in CONSTANTS:
            line = s[:m.start()].count("\n") + 1
            bad.append(f"line ~{line}: {m.group(0)!r} in …{s[max(0, m.start() - 40):m.end() + 20]!r}")
    return bad


def fill(src: str, D: dict) -> tuple[str, list[str]]:
    errs = []

    def rep(m):
        key, f = m.group(1), m.group(2)
        try:
            if key.startswith("table:"):
                return TABLES[key[6:]](D)
            return fmt(_get(D, key), f)
        except (KeyError, StopIteration, IndexError, TypeError, ValueError) as e:
            errs.append(f"unresolved {{{{{m.group(0)[2:-2]}}}}}: {e!r}")
            return "??"
    return PH.sub(rep, src), errs


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HERE.parent / "reports" / "sprint_all"))
    ap.add_argument("--src", default=str(HERE / "report.src.md"))
    ap.add_argument("--out", default=str(HERE / "report.md"))
    a = ap.parse_args(argv)
    d = Path(a.data)
    D = {"A": json.loads((d / "analysis.json").read_text()), "P": json.loads((d / "p5_analysis.json").read_text()),
         "R": json.loads((d / "report_data.json").read_text())}
    if (d / "reasoning_coding_summary.json").exists():
        D["C"] = {}
        for k, v in json.loads((d / "reasoning_coding_summary.json").read_text()).items():
            m, cond = k.split("|")
            D["C"].setdefault(m, {})[cond] = v
    if (d / "fig4_background.json").exists():
        D["F"] = json.loads((d / "fig4_background.json").read_text())
    D["X"] = {}
    for k, (f, path) in PRESPRINT.items():
        D["X"][k] = json.loads((HERE.parent / f).read_text())
        for p in path.split("/"):
            D["X"][k] = D["X"][k][p]
    src = Path(a.src).read_text()
    bad = check_prose(src)
    out, errs = fill(src, D)
    for e in bad:
        print("hand-typed number:", e, file=sys.stderr)
    for e in errs:
        print(e, file=sys.stderr)
    if bad or errs:
        print(f"fill: FAILED ({len(bad)} hand-typed numbers, {len(errs)} unresolved placeholders)", file=sys.stderr)
        return 1
    Path(a.out).write_text(out)
    print(f"fill: {len(PH.findall(src))} placeholders -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
