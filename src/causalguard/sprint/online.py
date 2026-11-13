"""R7 online readiness (pre-sprint): connectivity and isolation probes on NON-benchmark prompts only.

  python -m causalguard sprint-online probe --target claude|deepseek [--two-turn]

At most 5 connectivity requests per provider (enforced by the probe log ``runs/online-connectivity/<target>.jsonl``,
which records request/response sizes and token counts, never the key).  No benchmark item is ever sent from here:
the probe prompts are fixed strings below and the probe refuses any text containing an evidence row.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from .population import REPO

MAX_PROBES = 5
ENV_FILE = str(REPO.parent / ".env")
TARGETS = {
    "claude": {"kind": "claude_cli", "model": "claude-opus-5-5", "max_tokens": 4000, "timeout_s": 600,
               "max_transport_retries": 0, "seed": None, "extra": {"effort": "high", "thinking_summaries": True}},
    "deepseek": {"kind": "openai_compatible", "backend": "deepseek", "base_url": "https://api.deepseek.com",
                 "model": "deepseek-v4-pro", "allow_remote": True, "max_tokens": 16000, "timeout_s": 900,
                 "max_transport_retries": 1, "seed": 0,
                 "extra": {"api_key_env": "DEEPSEEK_API_KEY", "env_file": ENV_FILE,
                           "body": {"thinking": {"type": "enabled"}, "reasoning_effort": "high"},
                           "spend_ledger": "RUNS/sprint-online-calls/deepseek_spend.jsonl"}},
}
# SPRINT (lock v2, decision 8): one probe per provider, only to confirm that the reasoning text is returned and
# stored.  A small arithmetic question (no evidence row, no claim) so that the model thinks at all.
PROBE_REASONING = ("A shop sells pencils in packs of 7 and erasers in packs of 4. What is the smallest number of "
                   "pencils you can buy so that you can pair every pencil with exactly one eraser and have no eraser "
                   "left over? Reply with the number only.")
PROBE_SYSTEM = "You are a test endpoint."
PROBE_1 = "Reply with exactly the word READY and nothing else."
PROBE_2 = "What word did you reply with in your previous message? Reply with that word only."
_EVIDENCE = re.compile(r"[01]{8} ->")


def _log(target: str) -> Path:
    return Path(os.environ.get("CAUSALGUARD_RUNS", REPO / "runs")) / "online-connectivity" / f"{target}.jsonl"


def probe(target: str, two_turn: bool = False) -> dict:
    from ..llm.providers import make_provider
    log = _log(target)
    log.parent.mkdir(parents=True, exist_ok=True)
    used = len(log.read_text().splitlines()) if log.exists() else 0
    need = 2 if two_turn else 1
    if used + need > MAX_PROBES:
        raise SystemExit(f"{target}: {used} probes used; {need} more would exceed {MAX_PROBES}")
    prov = make_provider(TARGETS[target])
    msgs = [{"role": "system", "content": PROBE_SYSTEM}, {"role": "user", "content": PROBE_1}]
    rows = []
    for turn in range(need):
        if any(_EVIDENCE.search(m["content"]) for m in msgs):
            raise SystemExit("refusing: probe text looks like a benchmark item")
        with log.open("a") as fh:                     # count the request BEFORE it is sent
            fh.write(json.dumps({"target": target, "turn": turn + 1, "phase": "connectivity"}) + "\n")
        res = prov.chat(msgs, 0.0, None)
        a = res["attempts"][-1]
        our_chars = sum(len(m["content"]) for m in msgs)
        row = {"turn": turn + 1, "ok": res["ok"], "reply": (res["raw_output"] or "")[:200],
               "failure": res["failure"], "latency_s": a.get("latency_s"), "prompt_tokens": a.get("prompt_tokens"),
               "completion_tokens": a.get("completion_tokens"), "response_model": a.get("response_model"),
               "our_prompt_chars": our_chars, "usage_raw": getattr(prov, "last_usage", None)}
        rows.append(row)
        if not res["ok"]:
            break
        msgs += [{"role": "assistant", "content": res["raw_output"]}, {"role": "user", "content": PROBE_2}]
    out = {"target": target, "model": TARGETS[target]["model"], "rows": rows, "metadata": prov.metadata()}
    rec = REPO / "reports" / "development_r7" / f"online_probe_{target}.json"
    rec.parent.mkdir(parents=True, exist_ok=True)
    prev = json.loads(rec.read_text()) if rec.exists() else []
    rec.write_text(json.dumps(prev + [out], indent=1, sort_keys=True) + "\n")
    print(json.dumps(out, indent=1, sort_keys=True))
    return out


def probe_reasoning(target: str) -> dict:
    """One non-benchmark request; records whether the provider returned reasoning text and stores it."""
    from ..llm.providers import make_provider
    log = _log(target)
    log.parent.mkdir(parents=True, exist_ok=True)
    prev = [json.loads(x) for x in log.read_text().splitlines() if x.strip()] if log.exists() else []
    if any(x.get("phase") == "reasoning" for x in prev) or len(prev) + 1 > MAX_PROBES:
        raise SystemExit(f"{target}: the reasoning probe was already used or the probe cap is reached")
    prov = make_provider(TARGETS[target])
    msgs = [{"role": "system", "content": PROBE_SYSTEM}, {"role": "user", "content": PROBE_REASONING}]
    if any(_EVIDENCE.search(m["content"]) for m in msgs):
        raise SystemExit("refusing: probe text looks like a benchmark item")
    with log.open("a") as fh:
        fh.write(json.dumps({"target": target, "turn": 1, "phase": "reasoning"}) + "\n")
    res = prov.chat(msgs, 0.0, None)
    a = res["attempts"][-1]
    rs = res.get("reasoning")
    out = {"target": target, "model": TARGETS[target]["model"], "ok": res["ok"], "reply": (res["raw_output"] or "")[:200],
           "failure": res["failure"], "reasoning_available": bool(rs), "reasoning_chars": len(rs) if rs else 0,
           "reasoning_text": rs, "reasoning_tokens": a.get("reasoning_tokens"), "cost": a.get("cost"),
           "latency_s": a.get("latency_s"), "completion_tokens": a.get("completion_tokens"),
           "metadata": prov.metadata()}
    rec = REPO / "reports" / "sprint_online" / f"reasoning_probe_{target}.json"
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "reasoning_text"}, indent=1, sort_keys=True))
    return out


def _runs() -> Path:
    return Path(os.environ.get("CAUSALGUARD_RUNS", REPO / "runs"))


def fix_records(dry: bool = False) -> dict:
    """SPRINT amendment v2-a3 (record only; director D101/D102), idempotent.

    (1) DeepSeek spend: every line gets ``usd``, ``usd_upper``, ``peak``, ``t``; the 12 lines written before v2-a2
    are back-filled from the recorded tokens of their request (smoke v1 attempts and the reasoning probe), matched
    on the recorded peak figure, which must reproduce; the 3 fake test lines have no request.
    (2) Claude call ledger: each world of ``r7b-main-claude_opus_55-v1`` that the subscription window rejected
    before inference (``usage_limit_reached``; 172 at turn 1, 1 at turn 2 after a real turn 1) used one slot for
    the rejected request; one line ``{kind: usage_limit_rejected, voids_slot:
    true, backfilled: true}`` per such world cancels it.  The original files are kept beside them (``.pre-v2-a3``).
    """
    import glob

    from ..llm import providers as PR
    from ..llm.harness import ledger_used
    out = {}
    sp = _runs() / "sprint-online-calls" / "deepseek_spend.jsonl"
    lines = [json.loads(x) for x in sp.read_text().splitlines() if x.strip()]
    usages = {}
    for f in sorted(glob.glob(str(_runs() / "r7b-smoke-deepseek_v4_pro-v1" / "attempts" / "*" / "*.json"))):
        for t in json.loads(Path(f).read_text())["output"]["episode"].get("turns", []):
            for a in t["attempts"]:
                c = a.get("cost") or {}
                usages[c["usd_upper"]] = {"prompt_cache_hit_tokens": c["cache_hit_tokens"],
                                          "prompt_cache_miss_tokens": c["cache_miss_tokens"],
                                          "completion_tokens": c["output_tokens"]}
    pr = json.loads((REPO / "reports/sprint_online/reasoning_probe_deepseek.json").read_text())["cost"]
    usages[pr["usd_upper"]] = {"prompt_cache_hit_tokens": pr["cache_hit_tokens"],
                               "prompt_cache_miss_tokens": pr["cache_miss_tokens"],
                               "completion_tokens": pr["output_tokens"]}
    fixed = PR.spend_backfill(lines, usages)
    out["deepseek_spend"] = {"lines": len(fixed), "backfilled": sum(1 for x in fixed if x.get("backfilled")),
                             "from_tokens": sum(1 for x in fixed if x.get("backfill_source") == "recorded tokens"),
                             "usd": round(sum(x["usd"] for x in fixed), 6),
                             "usd_upper": round(sum(x["usd_upper"] for x in fixed), 6)}
    cl = _runs() / "sprint-online-calls" / "claude_opus_55.jsonl"
    recs = [json.loads(x) for x in cl.read_text().splitlines() if x.strip()]
    have = {r["world_id"] for r in recs if r.get("kind") == "usage_limit_rejected" and r.get("backfilled")}
    new = []
    tids = _task_ids(_runs() / "r7b-main-claude_opus_55-v1")
    for f in sorted(glob.glob(str(_runs() / "r7b-main-claude_opus_55-v1" / "attempts" / "*" / "*.json"))):
        d = json.loads(Path(f).read_text())
        o = d["output"]
        if d["status"] != "ok" and PR.USAGE_LIMIT_MARK in str(o.get("error")):
            turn = str(o["error"])[len("ProviderFailure('turn "):][:1]
            wid, cond = tids[d["item_id"]]
            call = "S|t1" if turn == "1" else f"P|{cond}|t2"
            if not any(r.get("world_id") == wid and r.get("call") == call and "kind" not in r for r in recs):
                raise SystemExit(f"{wid}: no slot line for the rejected request {call}")
            if wid not in have:
                new.append({"kind": "usage_limit_rejected", "voids_slot": True, "world_id": wid, "call": call,
                            "phase": "SPRINT", "backfilled": True, "run_id": "r7b-main-claude_opus_55-v1",
                            "attempt_finished": d["finished"], "message": PR.usage_limit_message(
                                str(o["error"]).replace("\\", ""))[:120]})
    after = recs + new
    out["claude_ledger"] = {"lines_before": len(recs), "rejections_voided_now": len(new),
                            "rejections_voided_total": sum(1 for r in after if r.get("voids_slot")),
                            "slots_used_before": ledger_used(recs), "slots_used_after": ledger_used(after)}
    if not dry:
        if any(not x.get("backfilled") and "usd" not in x for x in lines) or fixed != lines:
            bak = sp.with_suffix(".jsonl.pre-v2-a3")
            if not bak.exists():
                bak.write_bytes(sp.read_bytes())
            sp.write_text("".join(json.dumps(x) + "\n" for x in fixed))
        if new:
            bak = cl.with_suffix(".jsonl.pre-v2-a3")
            if not bak.exists():
                bak.write_bytes(cl.read_bytes())
            with open(cl, "a") as fh:
                fh.write("".join(json.dumps(x) + "\n" for x in new))
    return out


def _task_ids(run_dir: Path) -> dict[str, tuple[str, str]]:
    """item id -> (the world id the call ledger records (the public task id, recomputed from the planned world), condition)."""
    from . import population as P
    plan = json.loads((run_dir / "plan.json").read_text())
    out = {}
    for e in plan["items"]:
        p = e["payload"]
        k = P.WorldKey.from_json(p["world"])
        out[e["item_id"]] = (P.tier_public(k, p.get("tier", "H"), p.get("design_salt"))[1]["task_id"], p["condition"])
    return out


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="causalguard sprint-online")
    ap.add_argument("step", choices=("probe", "reasoning-probe", "fix-records"))
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--target", choices=sorted(TARGETS))
    ap.add_argument("--two-turn", action="store_true")
    a = ap.parse_args(argv)
    if a.step == "fix-records":
        print(json.dumps(fix_records(a.dry), indent=1, sort_keys=True))
        return 0
    if a.step == "reasoning-probe":
        probe_reasoning(a.target)
    else:
        probe(a.target, a.two_turn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
