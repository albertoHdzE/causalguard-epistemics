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
               "max_transport_retries": 0, "seed": None, "extra": {}},
    "deepseek": {"kind": "openai_compatible", "backend": "deepseek", "base_url": "https://api.deepseek.com",
                 "model": "deepseek-v4-pro", "allow_remote": True, "max_tokens": 16000, "timeout_s": 900,
                 "max_transport_retries": 1, "seed": 0,
                 "extra": {"api_key_env": "DEEPSEEK_API_KEY", "env_file": ENV_FILE,
                           "body": {"thinking": {"type": "enabled"}, "reasoning_effort": "high"}}},
}
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


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="causalguard sprint-online")
    ap.add_argument("step", choices=("probe",))
    ap.add_argument("--target", choices=sorted(TARGETS), required=True)
    ap.add_argument("--two-turn", action="store_true")
    a = ap.parse_args(argv)
    probe(a.target, a.two_turn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
