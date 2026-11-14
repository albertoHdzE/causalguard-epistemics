"""SPRINT (step H): the pre-registered reasoning coding.  Committed before any P4/P5f reply of the sprint is read.

1. Keyword screen over EVERY turn-2 reply (visible text) and stored reasoning of P4 (main runs) and P5f (P5 runs)
   worlds: does the text use row-checking vocabulary (``SCREEN``)?  Reported per model and condition as shares of
   worlds, with denominators.
2. Sample: per model and condition (P4, P5f), the 8 worlds with the smallest sha256('sprint-coding', model, wkey)
   among worlds with a stored turn 2; written to ``reasoning_coding.csv`` in that hash order with empty code
   columns.  Each is read in full (reply + stored reasoning) and coded with three binary codes:
     a  re-derives at least one cited lookup (states what a cited row shows, or recomputes an input value)
     b  names a mismatch between the check and a row (any line, right or wrong)
     c  names the altered line (the line the forgery changed: its node and cited row / 'no evidence row')
   Coder: the implementation agent (Claude Opus 5.5, an AI; disclosed).  Quotations in the results carry the
   world key.

  python -m causalguard sprint-coding sample --main-run R ... --p5-run R ... --out reports/sprint_all
  python -m causalguard sprint-coding summary --out reports/sprint_all      (after the CSV is filled)
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

SCREEN = re.compile(r"row\s*#?\s*\d+|according to (the )?row|the (cited )?row (shows|does not|doesn't)|"
                    r"does not (match|show)|doesn't (match|show)|mismatch|inconsisten|contradict|"
                    r"(is|line is|appears) (wrong|incorrect)|verif(y|ied|ying)|cross-check|double-check",
                    re.I)
N_SAMPLE = 8
CODES = ("a_rederives_lookup", "b_names_mismatch", "c_names_altered_line")


def _key(model: str, wkey: str) -> str:
    return hashlib.sha256(f"sprint-coding|{model}|{wkey}".encode()).hexdigest()


def _turn2(rec: dict) -> tuple[str, str]:
    t = rec["episode"].get("turns", [])
    if len(t) < 2 or not t[1].get("ok"):
        return "", ""
    return t[1].get("raw_output") or "", t[1].get("reasoning") or ""


def screen_and_sample(main_runs: list[str], p5_runs: list[str], out: str, add: bool = False) -> dict:
    """``add``: the sheet exists; append only the (model, condition) cells it does not hold yet (same hash rule;
    existing rows and codes untouched).  Used for runs that finish after the first draw (r1 P5, online)."""
    from .analysis import load
    res: dict = defaultdict(dict)
    rows = []
    p = Path(out) / "reasoning_coding.csv"
    old = list(csv.DictReader(p.open())) if add and p.exists() else []
    have_cells = {(r["model"], r["condition"]) for r in old}
    for runs, cond in ((main_runs, "P4"), (p5_runs, "P5f")):
        for r in load(runs):
            recs = [x for x in r["records"] if x["episode"]["assignment"]["condition"] == cond]
            have = [x for x in recs if _turn2(x)[0]]
            hit_reply = sum(bool(SCREEN.search(_turn2(x)[0])) for x in have)
            hit_reason = sum(bool(SCREEN.search(_turn2(x)[1])) for x in have)
            with_reason = sum(bool(_turn2(x)[1]) for x in have)
            res[r["model"]][cond] = {"worlds": len(recs), "with_turn2": len(have), "screen_reply": hit_reply,
                                     "with_reasoning": with_reason, "screen_reasoning": hit_reason}
            if (r["model"], cond) in have_cells:
                continue
            for x in sorted(have, key=lambda x: _key(r["model"], x["wkey"]))[:N_SAMPLE]:
                rows.append({"model": r["model"], "condition": cond, "wkey": x["wkey"], "run_id": r["run_id"],
                             "hash": _key(r["model"], x["wkey"])[:12], **{c: "" for c in CODES}, "quote": "",
                             "note": ""})
    o = Path(out)
    o.mkdir(parents=True, exist_ok=True)
    sp = o / "reasoning_screen.json"
    prev = json.loads(sp.read_text()) if add and sp.exists() else {}
    for m, v in res.items():
        prev.setdefault(m, {}).update(v)
    sp.write_text(json.dumps(prev, indent=1, sort_keys=True) + "\n")
    if p.exists() and not add:
        raise SystemExit(f"{p} exists; the sample is drawn once (use --add for cells not yet drawn)")
    if not rows:
        print("no new cells")
        return dict(res)
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(old + rows)
    print(f"screen: {sum(len(v) for v in res.values())} model x condition cells; sample {len(rows)} rows -> {p}")
    return dict(res)


def summary(out: str) -> dict:
    rows = list(csv.DictReader((Path(out) / "reasoning_coding.csv").open()))
    agg: dict = defaultdict(lambda: {"n": 0, **{c: 0 for c in CODES}})
    for r in rows:
        a = agg[(r["model"], r["condition"])]
        a["n"] += 1
        for c in CODES:
            if r[c] not in ("0", "1"):
                raise SystemExit(f"uncoded row {r['model']} {r['wkey']} {c}")
            a[c] += int(r[c])
    res = {f"{m}|{c}": v for (m, c), v in sorted(agg.items())}
    (Path(out) / "reasoning_coding_summary.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    return res


N_SECOND = 2


def second_coder_sheet(out: str, runs_root: str = "runs") -> Path:
    """Iteration 10 (optional): a blind sheet for a second, human coder: per model the N_SECOND rows of the coded
    sample with the smallest sha256('sprint-second-coder', model, condition, wkey); the visible turn-2 reply in full
    (stored reasoning only for models whose replies carry no text beyond the JSON), the three code definitions and
    empty code boxes.  The first coder's codes are not shown."""
    from .analysis import load
    rows = list(csv.DictReader((Path(out) / "reasoning_coding.csv").open()))
    by_model: dict = defaultdict(list)
    for r in rows:
        by_model[r["model"]].append(r)
    pick = [r for m in sorted(by_model) for r in sorted(by_model[m], key=lambda r: hashlib.sha256(
        f"sprint-second-coder|{r['model']}|{r['condition']}|{r['wkey']}".encode()).hexdigest())[:N_SECOND]]
    cache: dict = {}
    L = ["# Second-coder sheet (optional; blind)", "",
         f"{len(pick)} turn-2 replies, {N_SECOND} per model, hash-chosen from the coded sample of "
         "`reports/sprint_all/reasoning_coding.csv`. Read each reply in full and mark each code 1 (present) or 0.",
         "", "Codes:", "",
         "- **a** re-derives at least one cited lookup (states what a cited row shows, or recomputes an input value)",
         "- **b** names a mismatch between the check and a row (any line, right or wrong)",
         "- **c** names the altered line (the line the forgery changed: its node and cited row, or 'no evidence row')",
         "", "The altered line of each forged claim is given under the reply, so that code c can be judged.", ""]
    from . import population as P
    from . import tierw as TW
    for i, r in enumerate(pick, 1):
        if r["run_id"] not in cache:
            cache[r["run_id"]] = {x["wkey"]: x for x in load([str(Path(runs_root) / i) for i in
                                                               r["run_id"].split("+")])[0]["records"]}
        rec = cache[r["run_id"]][r["wkey"]]
        reply, reasoning = _turn2(rec)
        L += [f"## {i}. `{r['hash']}` ({r['condition']})", "", "Reply:", "", "```text", reply.strip(), "```", ""]
        if reasoning and len(re.sub(r"\{.*\}", "", reply, flags=re.S).strip()) < 40:
            L += ["Stored reasoning (the reply has no text beyond the JSON):", "", "```text", reasoning.strip(), "```", ""]
        asg = rec["episode"]["assignment"]
        pub = P.tier_public(P.WorldKey.from_json(rec["world"]), "W", asg.get("design_salt"))[1]
        L += ["Altered line(s) of each named claim's forged check:", ""]
        for c in asg["named"]:
            al = TW.altered_lines(pub, c, asg["salt"])
            L += [f"- {c} ({al['kind']}): " + " / ".join(f"`{x.strip()}`" for x in al["lines"])]
        L += [""]
        L += ["| code | a | b | c |", "|---|---|---|---|", "| your mark (0/1) |   |   |   |", ""]
    f = Path(out) / "second_coder_sheet.md"
    f.write_text("\n".join(L) + "\n")
    return f


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="causalguard sprint-coding")
    ap.add_argument("step", choices=("sample", "summary", "second-coder"))
    ap.add_argument("--main-run", action="append", default=[])
    ap.add_argument("--p5-run", action="append", default=[])
    ap.add_argument("--out", default="reports/sprint_all")
    ap.add_argument("--add", action="store_true")
    a = ap.parse_args(argv)
    if a.step == "second-coder":
        print(second_coder_sheet(a.out))
    elif a.step == "sample":
        screen_and_sample(a.main_run, a.p5_run, a.out, a.add)
    else:
        print(json.dumps(summary(a.out), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
