"""R7 sprint model ladder and config writer (pre-sprint).  Local models only run today; the two online models are
configured here and launched only after the director's review (docs/SPRINT_AUTHORISATION.md)."""
from __future__ import annotations

import json
from pathlib import Path

from .population import REPO

OLLAMA = {"kind": "openai_compatible", "backend": "ollama", "base_url": "http://127.0.0.1:11434/v1",
          "extra": {"ollama_native_options": {"num_ctx": 16384}}}
LMSTUDIO = {"kind": "openai_compatible", "backend": "lmstudio", "base_url": "http://127.0.0.1:1234/v1", "extra": {}}
CTX = 16384            # LM Studio models are loaded with `lms load <id> --context-length 16384`

# order = ascending size; 'tag' is the run-id suffix
LOCAL = [
    {"tag": "gemma3_4b", "server": LMSTUDIO, "model": "google/gemma-3-4b", "params_b": 4, "max_tokens": 4000},
    {"tag": "qwen25_7b", "server": OLLAMA, "model": "qwen2.5:7b", "params_b": 7, "max_tokens": 4000},
    {"tag": "gemma4_12b", "server": LMSTUDIO, "model": "gemma-4-12b-it-mlx", "params_b": 12, "max_tokens": 4000},
    {"tag": "mistral_small_24b", "server": LMSTUDIO, "model": "mistral-small-3.2-24b-instruct-2506-mlx",
     "params_b": 24, "max_tokens": 4000},
    {"tag": "r1_distill_qwen_32b", "server": LMSTUDIO, "model": "deepseek-r1-distill-qwen-32b", "params_b": 32,
     "max_tokens": 12000, "reasoning": True},
    {"tag": "llama33_70b", "server": LMSTUDIO, "model": "llama-3.3-70b-instruct", "params_b": 70, "max_tokens": 4000},
    {"tag": "qwen25_72b", "server": OLLAMA, "model": "qwen2.5:72b", "params_b": 72, "max_tokens": 4000},
]

COMMON = {"study": "SPRINT", "mode": "development", "global_cap": 6000, "phase": "SPRINT", "phase_cap": 6000,
          "call_ledger": "RUNS/sprint-calls/ledger.jsonl", "workers": 1, "item_timeout_s": 7200, "world_cap": 4}


def provider(m: dict) -> dict:
    s = m["server"]
    return {"kind": s["kind"], "backend": s["backend"], "base_url": s["base_url"], "model": m["model"],
            "max_tokens": m["max_tokens"], "seed": 0, "timeout_s": 1800 if m.get("reasoning") else 600,
            "max_transport_retries": 1, "extra": s["extra"]}


def write_configs(stage: str, manifest: str, max_items: int | None = None, version: str = "v1",
                  tags: list[str] | None = None, task_wording: str | None = None) -> list[Path]:
    out = []
    d = REPO / "configs" / "sprint"
    d.mkdir(parents=True, exist_ok=True)
    for m in LOCAL:
        if tags and m["tag"] not in tags:
            continue
        cfg = {**COMMON, "run_id": f"r7-{stage}-{m['tag']}-{version}", "manifest": manifest,
               "provider": provider(m), "note": f"R7 sprint {stage} (pre-sprint), local inference only"}
        if max_items:
            cfg["max_items"] = max_items
        if task_wording:
            cfg["task_wording"] = task_wording
        p = d / f"{stage}_{m['tag']}.json"
        p.write_text(json.dumps(cfg, indent=1) + "\n")
        out.append(p)
    return out


if __name__ == "__main__":
    import sys
    stage = sys.argv[1]
    man = {"smoke": "artifacts/sprint_smoke_manifest.json", "pilot": "artifacts/sprint_pilot_manifest.json",
           "main": "artifacts/sprint_main_manifest.json"}[stage]
    for p in write_configs(stage, man, max_items=4 if stage == "smoke" else None):
        print(p.relative_to(REPO))
