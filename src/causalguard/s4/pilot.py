"""S4 bounded local LLM pilot harness (development).

Per (model, world): four episodes on the SAME public task.
  A   no tool: structured evidence + matched instructions; ONE turn; its answers are also the common initial
      proposal batch replayed offline through the B/C/D checkers (pre-release checking metrics).
  B/C/D  identical tool protocol and response schema; only the backend representation differs:
      {"tool_calls": [{"tool": "check", "cid": "c3"}, {"tool": "status"},
                      {"tool": "propose", "answers": [...]}, {"tool": "commit", "answers": [...]}]}
      'check' returns the exact verdict of a claim over all consistent mechanisms with counts and example
      mechanisms; 'propose' runs the pre-release gate on answers; 'commit' ends the episode (verified answers
      are released as verified, others as unverified forecasts/answers).  At most 8 model turns.
The agent side sees only the serialized public task.  The evaluator (hidden mechanism) is consulted only after
every episode of the world has finished; its reference block is written last in the record.
"""
from __future__ import annotations

import json
import re
import time

from ..schema import Evidence, Query
from .checking import check, commit, validate_proposal
from .workspace import make_workspace

MAX_TURNS = 8
VERDICTS = ("entailed", "refuted", "underdetermined")


def _bits(x: int, n: int) -> str:
    return "".join(str((x >> i) & 1) for i in range(n))


def render_task(pub: dict) -> str:
    n, L = pub["n"], pub["node_labels"]
    ev = Evidence.from_json(pub["evidence"])
    lines = [f"System with {n} Boolean nodes, physical order: {' '.join(L)}.",
             "All nodes update synchronously. Each node's next value is a FIXED but UNKNOWN Boolean function of at "
             f"most {pub['k']} nodes (any nodes, possibly itself). A 'consistent mechanism' is any such network "
             "that reproduces every evidence row exactly.",
             "States are written as bit strings in the physical order above.",
             "", "Evidence (each row: one synchronous step from a start state; a clamped node is held fixed and "
             "its next value is not observed, shown as '.'):"]
    for i, o in enumerate(ev.observations, 1):
        clamp = dict(o.intervention.assign) if o.intervention.kind == "persistent_clamp" else {}
        m, v = o.intervention.masks
        start = (o.state & ~m) | v if clamp else o.state
        nxt = dict(o.observed)
        out = "".join(str(nxt[j]) if j in nxt else "." for j in range(n))
        c = (" clamp " + ",".join(f"{L[j]}={b}" for j, b in sorted(clamp.items()))) if clamp else ""
        lines.append(f" #{i:02d} from {_bits(start, n)}{c} -> {out}")
    lines += ["", "Claims:"]
    for c in pub["claims"]:
        lines.append(" " + render_claim(c, pub))
    return "\n".join(lines)


def render_claim(c: dict, pub: dict) -> str:
    n, L = pub["n"], pub["node_labels"]
    q = Query.from_json(c["query"])
    from ..versionspace import point_query_parts
    x0 = point_query_parts(q, n)
    iv = q.intervention
    assign = ",".join(f"{L[j]}={b}" for j, b in iv.assign)
    how = ("first set " + assign + " in the start state, then update freely") if iv.kind == "initial_edit" else \
          ("hold " + assign + " fixed at every step")
    return (f"{c['cid']}: start {_bits(x0, n)}; {how}; after {q.horizon} step(s): {L[q.target.node]} = "
            f"{q.target.value}")


INSTRUCTIONS = """For EACH claim decide its verdict with respect to ALL consistent mechanisms:
- "entailed": the claim is true in every consistent mechanism;
- "refuted": the claim is false in every consistent mechanism;
- "underdetermined": some consistent mechanisms make it true and others make it false.
Also give "forecast": your best guess (0 or 1) of the target node's ACTUAL value in the real system."""

ANSWER_FORMAT = ('{"answers": [{"cid": "c0", "verdict": "entailed|refuted|underdetermined", "forecast": 0}, ...]} '
                 "with one entry per claim")

TOOLS = """You have a symbolic checking tool that reasons exactly over all consistent mechanisms.
Reply in EVERY turn with exactly one JSON object {"tool_calls": [...]}; several calls per turn are allowed:
  {"tool": "check", "cid": "c0"}          exact verdict of a claim, counts of consistent mechanisms, example mechanisms
  {"tool": "status"}                       summary of the consistent mechanisms per node
  {"tool": "propose", "answers": [...]}    pre-release check of your answers (each returns verified / refuted with a
                                           counterexample / underdetermined = forecast only)
  {"tool": "commit", "answers": [...]}     final answers; ends the task
Answers use the format: """ + ANSWER_FORMAT + f"""
Example first turn: {{"tool_calls": [{{"tool": "check", "cid": "c0"}}, {{"tool": "check", "cid": "c1"}}]}}
Example later turn: {{"tool_calls": [{{"tool": "commit", "answers": [{{"cid": "c0", "verdict": "refuted", "forecast": 0}}]}}]}}
You have at most {MAX_TURNS} turns. Commit before the last turn."""


def system_prompt(arm: str) -> str:
    base = "You are a careful scientific assistant reasoning about a hidden deterministic system."
    return base + ("\n" + TOOLS if arm != "A" else "")


def user_prompt(pub: dict, arm: str) -> str:
    tail = (f"\nReply with ONLY one JSON object: {ANSWER_FORMAT}." if arm == "A" else
            "\nStart by calling tools.")
    return render_task(pub) + "\n\n" + INSTRUCTIONS + tail


_JSON = re.compile(r"\{.*\}", re.S)


def parse_json(text: str | None) -> dict | None:
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.M).strip()
    for cand in (t, *(m.group(0) for m in [_JSON.search(t)] if m)):
        try:
            v = json.loads(cand)
            return v if isinstance(v, dict) else None
        except json.JSONDecodeError:
            continue
    return None


def parse_final_json(text: str | None, key: str = "answers") -> dict | None:
    """R7: ``parse_json``, else the LAST JSON object in the text that carries ``key`` (a reply that reasons in prose
    and ends with the requested object).  Earlier objects are never preferred over a later one."""
    obj = parse_json(text)
    if obj is not None or not text:
        return obj
    dec = json.JSONDecoder()
    found = None
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            v, _ = dec.raw_decode(text, i)
        except json.JSONDecodeError:
            continue
        if isinstance(v, dict) and key in v:
            found = v
    return found


def parse_answers(obj, cids: list[str]) -> dict:
    """{cid: {"verdict", "forecast"}} for valid entries; invalid/missing entries are absent."""
    out = {}
    if not isinstance(obj, list):
        return out
    for a in obj:
        if not isinstance(a, dict) or a.get("cid") not in cids:
            continue
        v = a.get("verdict")
        f = a.get("forecast")
        if isinstance(f, str) and f in ("0", "1"):
            f = int(f)
        if v in VERDICTS and f in (0, 1) and not isinstance(f, bool) and a["cid"] not in out:
            out[a["cid"]] = {"verdict": v, "forecast": f}
    return out


_THINK = re.compile(r"<think>.*?</think>|^.*?</think>", re.S)


def strip_reasoning(text: str | None) -> str | None:
    """Visible answer of a reasoning model: drops <think>...</think> blocks (and a leading block whose opening tag
    the server already consumed).  Text without such tags is returned unchanged (R7)."""
    if not text or "</think>" not in text:
        return text
    return _THINK.sub("", text).strip()


# R7 sprint Task S vocabulary (plain words for the model; the internal labels are the S4 verdicts)
STATUS_WORDS = {"true": "entailed", "false": "refuted", "not settled": "underdetermined"}


def parse_status_answers(obj, cids: list[str]) -> dict:
    """R7 Task S: {cid: {"verdict": entailed|refuted|underdetermined, "probability": float in [0, 1] or None}}.
    A claim answer is valid when its verdict is valid (words matched case-insensitively after trimming); the
    probability is kept when it is a number (or numeric string) in [0, 1], else recorded as None (DECISIONS D73).
    Invalid verdicts and duplicate cids leave the claim absent."""
    out = {}
    if not isinstance(obj, list):
        return out
    for a in obj:
        if not isinstance(a, dict) or a.get("cid") not in cids or a["cid"] in out:
            continue
        v = a.get("verdict")
        v = STATUS_WORDS.get(v.strip().lower()) if isinstance(v, str) else None
        p = a.get("probability")
        if isinstance(p, str):
            try:
                p = float(p.strip())
            except ValueError:
                p = None
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not (0.0 <= float(p) <= 1.0):
            p = None
        if v is not None:
            out[a["cid"]] = {"verdict": v, "probability": None if p is None else float(p)}
    return out


def _proposals(answers: dict, claims_by_id: dict) -> dict:
    out = {}
    for cid, a in answers.items():
        out[cid] = validate_proposal({"cid": cid, "asserted": a["verdict"], "forecast": a["forecast"]}, claims_by_id)
    return out


def _render_check(r: dict) -> dict:
    out = {"cid": r["cid"], "verdict": r["verdict"]}
    if r.get("counts"):
        num, den = int(r["counts"]["num"]), int(r["counts"]["den"])
        out["fraction_true"] = round(num / den, 4)
        out["consistent_mechanisms"] = r["counts"]["den"]
    if r.get("witnesses"):
        out["example_mechanisms"] = {("claim_true" if h == "1" else "claim_false"): w for h, w in r["witnesses"].items()}
    if r.get("reason"):
        out["reason"] = r["reason"]
    return out


def _gate_view(d) -> dict:
    v = {"cid": d.cid, "status": d.proposal_check_status, "claim_status": d.epistemic_verdict, "feedback": d.feedback}
    if d.counterexample:
        v["counterexample"] = {"mechanism": d.counterexample["mechanism"], "trajectory": d.counterexample["trajectory"]}
    return v


def run_episode(arm: str, pub: dict, provider, budget, seed: int | None, world_id: str) -> dict:
    from ..llm.harness import derive_seed
    cids = [c["cid"] for c in pub["claims"]]
    cby = {c["cid"]: c for c in pub["claims"]}
    msgs = [{"role": "system", "content": system_prompt(arm)}, {"role": "user", "content": user_prompt(pub, arm)}]
    calls, tool_log, decisions = [], [], {}
    ws = make_workspace(arm, pub) if arm != "A" else None
    final, committed, status = {}, False, "no_answer"
    released: dict = {}
    for turn in range(1 if arm == "A" else MAX_TURNS):
        budget.current = f"{arm}|t{turn}"
        res = provider.chat(msgs, 0.0, derive_seed(seed, world_id, f"{arm}|{turn}"), budget.before_attempt)
        rec = {k: res[k] for k in ("ok", "raw_output", "failure", "request_hash")}
        rec["attempts"] = res["attempts"]
        calls.append(rec)
        if not res["ok"]:
            status = "call_failed"
            break
        obj = parse_json(res["raw_output"])
        msgs.append({"role": "assistant", "content": res["raw_output"]})
        if arm == "A":
            final = parse_answers((obj or {}).get("answers"), cids)
            status = "answered" if obj is not None else "unparsable"
            break
        tcs = (obj or {}).get("tool_calls")
        if not isinstance(tcs, list):
            # a bare answers object is accepted as a commit (tolerant parsing, logged)
            if obj is not None and isinstance(obj.get("answers"), list):
                tcs = [{"tool": "commit", "answers": obj["answers"]}]
                tool_log.append({"turn": turn, "note": "bare answers treated as commit"})
            else:
                msgs.append({"role": "user", "content": "Invalid reply. Reply with one JSON object {\"tool_calls\": [...]}."})
                tool_log.append({"turn": turn, "invalid": True})
                continue
        results = []
        committed_this_turn = False
        for tc in tcs[:24]:
            if not isinstance(tc, dict):
                results.append({"error": 'each tool call must be an object such as {"tool": "check", "cid": "c0"}'})
                tool_log.append({"turn": turn, "invalid_call": str(tc)[:60]})
                continue
            name = tc.get("tool")
            t0 = time.perf_counter()
            if name == "check" and tc.get("cid") in cby:
                results.append(_render_check(ws.check(cby[tc["cid"]])))
            elif name == "status":
                st = ws.status()
                results.append({k: v for k, v in st.items() if k != "analytic_summary"} |
                               ({"analytic_summary": st["analytic_summary"]} if "analytic_summary" in st else {}))
            elif name in ("propose", "commit"):
                ans = parse_answers(tc.get("answers"), cids)
                if name == "commit":
                    # several commit calls in ONE turn are merged (first answer per claim wins).  The v1 pilot
                    # harness overwrote earlier calls (DECISIONS D52); scored as recorded + merged sensitivity.
                    final = {**ans, **final} if committed_this_turn else ans
                    committed_this_turn = True
                for cid, p in _proposals(ans, cby).items():
                    d = check(p, ws)
                    decisions[cid] = d
                    if name == "commit":
                        try:
                            released[cid] = commit(p, d, ws)["verified"]
                        except Exception:
                            released[cid] = False
                    else:
                        results.append(_gate_view(d))
                if name == "commit":
                    committed = True
                    results.append({"committed": len(final), "released_verified": sum(released.values())})
                else:
                    missing = [c for c in cids if c not in ans]
                    if missing:
                        results.append({"note": f"no valid answer for {missing}"})
            else:
                results.append({"error": f"unknown tool or claim id: {str(tc)[:80]}"})
            tool_log.append({"turn": turn, "tool": name, "cid": tc.get("cid"), "wall_s": time.perf_counter() - t0})
        if committed:
            status = "committed"
            break
        if turn == MAX_TURNS - 2:
            results.append({"note": "one turn left: commit your final answers now"})
        msgs.append({"role": "user", "content": "Tool results:\n" + json.dumps(results, separators=(",", ":"))})
    if arm != "A" and not committed:
        status = "no_commit" if status not in ("call_failed",) else status
    return {"arm": arm, "status": status, "turns": len(calls), "calls": calls, "final": final,
            "released_verified": released, "tool_log": tool_log,
            "decisions": {cid: {k: v for k, v in d.to_json().items() if k not in ("seal",)}
                          for cid, d in decisions.items()},
            "workspace_cost": ws.cost if ws else None, "messages_chars": sum(len(m["content"]) for m in msgs)}


def replay_common_batch(pub: dict, answers: dict) -> dict:
    """Pre-release checking of arm A's (unaided) proposals by every checker, without new model calls."""
    cby = {c["cid"]: c for c in pub["claims"]}
    out = {}
    for arm in ("B", "C", "D"):
        ws = make_workspace(arm, pub)
        per = {}
        for cid, p in _proposals(answers, cby).items():
            d = check(p, ws)
            per[cid] = {"status": d.proposal_check_status, "claim_status": d.epistemic_verdict}
        out[arm] = per
    return out


def pilot_world(p: dict) -> dict:
    """Runner item: one (model, world).  Returns episodes + replay + evaluator reference (written last)."""
    from ..llm.harness import CallBudget
    from ..llm.providers import make_provider
    from .evaluator import Evaluator
    ev = Evaluator(p["salt"], p["index"], p["family"])
    pub = ev.public()                      # serialized copy; the episodes below never touch ``ev``
    provider = make_provider(p["provider"])
    ledger = p.get("call_ledger")
    if ledger and ledger.startswith("RUNS/"):          # the main tree's runtime runs root (snapshot-safe)
        import os
        from pathlib import Path
        ledger = str(Path(os.environ.get("CAUSALGUARD_RUNS", "runs")) / ledger[len("RUNS/"):])
    budget = CallBudget(p.get("world_cap", 1 + 3 * MAX_TURNS), p.get("global_cap"), ledger, world_id=pub["task_id"])
    t0 = time.perf_counter()
    episodes = {}
    for arm in p.get("arms", ["A", "B", "C", "D"]):
        try:
            episodes[arm] = run_episode(arm, pub, provider, budget, p["provider"].get("seed", 0), pub["task_id"])
        except Exception as e:     # CapExceeded or harness error: recorded, never dropped
            episodes[arm] = {"arm": arm, "status": f"error:{type(e).__name__}", "error": str(e)[:500], "final": {}}
    replay = replay_common_batch(pub, episodes.get("A", {}).get("final", {})) if "A" in episodes else {}
    # ---- evaluator (after all answers are fixed)
    refs = ev.reference(crosscheck_sat=True)
    reference = {r.cid: {"verdict": r.verdict, "num": str(r.num), "den": str(r.den), "truth_holds": r.truth_holds,
                         "h": r.h, "iv": r.kind} for r in refs}
    return {"task_id": pub["task_id"], "world_id": ev.world.world_id, "family": p["family"], "index": p["index"],
            "model": p["provider"]["model"], "provider_metadata": provider.metadata(), "budget": ev.design.budget,
            "public_sha256": __import__("hashlib").sha256(json.dumps(pub, sort_keys=True).encode()).hexdigest(),
            "episodes": episodes, "common_batch_replay": replay, "wall_s": time.perf_counter() - t0,
            "calls_used": budget.n, "reference": reference}
