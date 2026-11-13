"""R7 sprint episode (pre-sprint): Task S (turn 1) then Task P (turn 2) in ONE conversation.

The follow-up is sent unconditionally (whatever turn 1 returned), with the condition, wording and named claims
fixed by the manifest (hash assignment).  The evaluator's reference is computed only after both turns are fixed and
is written last in the record.  Reasoning-model think blocks are kept in the raw record and removed from the
visible answer (and from the conversation history passed to turn 2).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from ..s4.pilot import parse_final_json, parse_status_answers, strip_reasoning
from . import population as P
from . import tasks as T

PHASE = "SPRINT"


class ProviderFailure(RuntimeError):
    """R7b D85: a turn whose provider call failed after its transport retries (server crash, empty reply).  The
    world item fails (runner status 'error') so the identical plan can retry it; it is never scored as a
    model answer."""


def _ledger_path(p: str | None) -> str | None:
    if p and p.startswith("RUNS/"):
        return str(Path(os.environ.get("CAUSALGUARD_RUNS", "runs")) / p[len("RUNS/"):])
    return p


def answers_from_raw(raw: str | None, cids: list[str]) -> tuple[bool, dict]:
    """The ONE parse path from a raw reply to answers (used at run time and by the analysis, which always re-derives
    answers from the stored raw outputs with the current parser)."""
    obj = parse_final_json(strip_reasoning(raw)) if raw else None
    return obj is not None, parse_status_answers((obj or {}).get("answers"), cids)


def check_errors_from_raw(raw: str | None) -> list[dict] | None:
    """SPRINT (P5): the ``check_errors`` entries of the final JSON object of a reply (the same object the answers
    come from).  None when the reply has no final object; [] when the object has no usable list.  Entries keep only
    string ``cid`` and ``line`` values; anything else is dropped (counted by the scorer as no quote)."""
    obj = parse_final_json(strip_reasoning(raw)) if raw else None
    if obj is None:
        return None
    ce = obj.get("check_errors")
    if not isinstance(ce, list):
        return []
    return [{"cid": e["cid"].strip(), "line": e["line"]} for e in ce
            if isinstance(e, dict) and isinstance(e.get("cid"), str) and isinstance(e.get("line"), str)]


def reparse(rec: dict) -> tuple[dict, int]:
    """A copy of a run record with every turn's answers re-derived from its raw output; returns (record, number of
    claim answers that differ from the recorded ones)."""
    import copy
    cids = sorted(rec["reference"], key=lambda c: int(c[1:]))
    out = copy.deepcopy(rec)
    changed = 0
    for t in out["episode"].get("turns", []):
        parsed, a = answers_from_raw(t.get("raw_output") if t.get("ok") else None, cids)
        changed += sum(1 for c in cids if a.get(c) != t.get("answers", {}).get(c))
        t["parsed"], t["answers"] = parsed, a
    return out, changed


def _turn(provider, msgs, budget, seed, wid, label) -> tuple[dict, dict, str | None]:
    from ..llm.harness import derive_seed
    budget.current = label
    res = provider.chat(msgs, 0.0, derive_seed(seed, wid, label), budget.before_attempt)
    rec = {k: res[k] for k in ("ok", "raw_output", "failure", "request_hash")}
    rec["attempts"] = res["attempts"]
    # SPRINT (lock v2, D88): the provider's separate reasoning text, stored as returned; never read by a scorer
    # (answers come from ``raw_output`` only; test_reasoning_field_never_scored)
    rec["reasoning"] = res.get("reasoning")
    visible = strip_reasoning(res["raw_output"]) if res["ok"] else None
    obj = parse_final_json(visible)
    last = res["attempts"][-1] if res["attempts"] else {}
    rec.update(parsed=obj is not None, truncated=last.get("finish_reason") == "length",
               finish_reason=last.get("finish_reason"), latency_s=last.get("latency_s"),
               prompt_tokens=last.get("prompt_tokens"), completion_tokens=last.get("completion_tokens"))
    return rec, (obj or {}), visible


def run_episode(pub: dict, assignment: dict, provider, budget, seed: int | None, two_turns: bool = True,
                wording: str = T.DEFAULT_WORDING) -> dict:
    cids = [c["cid"] for c in pub["claims"]]
    wid = pub["task_id"]
    msgs = [{"role": "system", "content": T.system()}, {"role": "user", "content": T.user_prompt(pub, wording)}]
    out = {"assignment": assignment, "task_wording": wording, "turns": []}
    rec1, obj1, vis1 = _turn(provider, msgs, budget, seed, wid, "S|t1")
    if not rec1["ok"]:
        raise ProviderFailure(f"turn 1: {str(rec1['failure'])[:300]}")
    a1 = parse_status_answers(obj1.get("answers"), cids)
    out["turns"].append({**rec1, "answers": a1})
    if not two_turns:
        return out
    if rec1["ok"]:
        msgs.append({"role": "assistant", "content": vis1 if vis1 is not None else ""})
    else:                                   # the conversation continues; the failed turn is recorded as empty
        msgs.append({"role": "assistant", "content": ""})
    fu = T.followup(pub, assignment["condition"], assignment["wording"], assignment["named"],
                    assignment.get("salt"))
    msgs.append({"role": "user", "content": fu})
    rec2, obj2, _ = _turn(provider, msgs, budget, seed, wid, f"P|{assignment['condition']}|t2")
    if not rec2["ok"]:
        raise ProviderFailure(f"turn 2: {str(rec2['failure'])[:300]}")
    out["turns"].append({**rec2, "answers": parse_status_answers(obj2.get("answers"), cids),
                         "followup_sha256": hashlib.sha256(fu.encode()).hexdigest()})
    if assignment["condition"] in T.P5_CONDS:
        out["turns"][-1]["check_errors"] = check_errors_from_raw(rec2["raw_output"] if rec2["ok"] else None)
    out["followup"] = fu
    return out


def sprint_world(p: dict) -> dict:
    """Runner item: one (model, world).  Payload: the manifest item + provider + caps + ledger."""
    from ..llm.harness import CallBudget
    from ..llm.providers import HardStop, make_provider
    k = P.WorldKey.from_json(p["world"])
    tier = p.get("tier", "H")                       # R7b (D79): 'W' wiring given, 'H' wiring hidden
    ev, pub = P.tier_public(k, tier, p.get("design_salt"))     # design_salt: P5 worlds (lock v2)
    if p.get("public_sha256") and hashlib.sha256(json.dumps(pub, sort_keys=True).encode()).hexdigest() != \
            p["public_sha256"]:
        raise AssertionError("public task differs from the manifest")
    provider = make_provider(p["provider"])
    budget = CallBudget(p.get("world_cap", 4), p.get("global_cap"), _ledger_path(p.get("call_ledger")),
                        world_id=pub["task_id"], phase=p.get("phase", PHASE), phase_cap=p.get("phase_cap"))
    t0 = time.perf_counter()
    assignment = {x: p[x] for x in ("condition", "wording", "named")}
    for x in ("tier", "salt", "checker_status", "forged_status", "forgery_kind", "design_salt"):
        if x in p:
            assignment[x] = p[x]
    try:
        episode = run_episode(pub, assignment, provider, budget, p["provider"].get("seed", 0),
                              two_turns=p.get("two_turns", True), wording=p.get("task_wording", T.DEFAULT_WORDING))
        status = "ok"
    except (ProviderFailure, HardStop):    # v2-a3: a hard-stopped world is not finished (runner status error)
        raise
    except Exception as e:     # CapExceeded or harness error: recorded, never dropped
        episode, status = {"assignment": assignment, "turns": [], "error": f"{type(e).__name__}: {str(e)[:400]}"}, \
            f"error:{type(e).__name__}"
    wall = time.perf_counter() - t0
    # ---- evaluator (after every answer is fixed)
    ref = P.tier_reference(ev, pub, tier, crosscheck_sat=True)
    return {"wkey": k.wkey, "world": k.to_json(), "tier": tier, "task_id": pub["task_id"],
            "model": p["provider"]["model"],
            "provider_metadata": provider.metadata(), "budget": ev.design.budget, "status": status,
            "public_sha256": hashlib.sha256(json.dumps(pub, sort_keys=True).encode()).hexdigest(),
            "task_version": T.TASK_VERSION, "episode": episode, "wall_s": wall, "calls_used": budget.n,
            "reference": ref}
