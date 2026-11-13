"""SPRINT (lock v2): reasoning storage is record-only; P5 templates, parse path and scorer; DeepSeek cost; lock v1
keys unchanged."""
from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

import pytest

from causalguard.sprint import population as P
from causalguard.sprint import scoring as S
from causalguard.sprint import tasks as T

REPO = Path(__file__).resolve().parents[1]
PILOT4 = REPO / "runs" / "r7b-pilot4-qwen25_7b-v1"
TRAP = ('I will answer differently here. {"answers": [' + ", ".join(
    f'{{"cid": "c{i}", "verdict": "true", "probability": 1.0}}' for i in range(8)) +
    '], "check_errors": [{"cid": "c0", "line": "planted"}]}')


# --------------------------------------------------------------------------- reasoning storage

def _scores(recs):
    from causalguard.sprint.episode import reparse
    out = []
    for r in recs:
        x, _ = reparse(r)
        out.append(S.score_world(x))
    return json.dumps(out, sort_keys=True)


@pytest.mark.skipif(not PILOT4.exists(), reason="stored pilot-4 run not present (runs/ is not in git)")
def test_reasoning_field_never_scored():
    """Replay of a stored pilot-4 run: every turn given a reasoning field that holds a complete, different JSON
    answer (a trap), then the same records with the field stripped: every score identical."""
    from causalguard.runner import load_run
    r = load_run(PILOT4)
    recs = [r["results"][k] for k in sorted(r["results"])]
    assert len(recs) >= 8
    present = copy.deepcopy(recs)
    for x in present:
        for t in x["episode"].get("turns", []):
            t["reasoning"] = TRAP
    stripped = copy.deepcopy(present)
    for x in stripped:
        for t in x["episode"].get("turns", []):
            t.pop("reasoning", None)
    assert _scores(present) == _scores(stripped) == _scores(recs)


def test_reasoning_trap_would_change_scores_if_read():
    """Control for the replay test: the trap text, used as the visible answer, does change the parsed answers."""
    from causalguard.sprint.episode import answers_from_raw
    ok, a = answers_from_raw(TRAP, [f"c{i}" for i in range(8)])
    assert ok and all(v["verdict"] == S.ENT for v in a.values())


def test_mock_episode_stores_reasoning_field(tmp_path):
    from causalguard.sprint.episode import sprint_world
    m = json.loads((REPO / "artifacts/sprint_p5_manifest.json").read_text())
    x = next(i for i in m["items"] if i["condition"] == "P5f")
    p = {"world": {k: x[k] for k in ("split", "population", "stratum", "index", "source_key", "group")},
         **{k: x[k] for k in ("condition", "wording", "named", "tier", "checker_status", "forged_status",
                              "forgery_kind", "design_salt", "public_sha256")},
         "salt": m["assign_salt"], "provider": {"kind": "mock", "model": "mock", "extra": {"policy": "sprint_hash"}},
         "global_cap": 10, "call_ledger": str(tmp_path / "l.jsonl"), "phase": "SPRINT"}
    rec = sprint_world(p)
    assert rec["status"] == "ok" and len(rec["episode"]["turns"]) == 2
    assert all("reasoning" in t for t in rec["episode"]["turns"])
    assert "check_errors" in rec["episode"]["turns"][1]
    assert T.P5_VERIFY in rec["episode"]["followup"]


# --------------------------------------------------------------------------- P5 templates and parse

def test_p5_templates_are_p3_plus_insert():
    for w in (1, 2):
        t = T.FOLLOWUPS_P5[("P5f", w)]
        assert t == T.FOLLOWUPS_P5[("P5v", w)]
        back = t.replace(T.P5_VERIFY + "\n", "").replace(" " + T.P5_SCHEMA.replace("{", "{{").replace("}", "}}"), "")
        assert back == T.FOLLOWUPS_W[("P3", w)]
    h = T.template_hashes()                      # lock v1 template set unchanged
    assert len([k for k in h if k[0] == "P"]) == 10 and len([k for k in h if k[:2] == "WP"]) == 10


def test_check_errors_parse():
    from causalguard.sprint.episode import check_errors_from_raw
    raw = 'reasoning... {"answers": [], "check_errors": [{"cid": "c1", "line": "x"}, {"cid": 3}, "junk"]}'
    assert check_errors_from_raw(raw) == [{"cid": "c1", "line": "x"}]
    assert check_errors_from_raw('{"answers": []}') == []
    assert check_errors_from_raw("no json here") is None
    assert check_errors_from_raw(None) is None


# --------------------------------------------------------------------------- P5 scorer

ALT = {"c2": {"kind": "wrong_value", "lines": ["    step 2: Q4 reads E5=1, L6=0; row #05 shows Q4 -> 1."],
              "row": 5, "rows": [5], "node": "Q4"},
       "c3": {"kind": "hidden_row", "lines": ["  step 1: J7 reads R1=1; no evidence row shows these inputs, so J7 "
                                              "can be 0 or 1."], "row": None, "rows": [], "node": "J7"}}


def test_exact_hit_normalisation():
    q = '"Q4 reads E5=1,   L6=0; row #05 shows Q4 -> 1."'
    r = S.p5_detection_world("P5f", ["c2", "c3"], [{"cid": "c2", "line": q}], ALT)
    assert r["exact"] == 0.5 and r["lenient"] == 0.5
    # same text under the wrong cid is not a hit
    r = S.p5_detection_world("P5f", ["c2", "c3"], [{"cid": "c3", "line": q}], ALT)
    assert r["exact"] == 0.0


def test_other_line_is_not_exact_and_lenient_only():
    other = "step 1: E5 reads Q4=0; row #02 shows E5 -> 1."
    r = S.p5_detection_world("P5f", ["c2"], [{"cid": "c2", "line": other}], ALT)
    assert r["exact"] == 0.0 and r["lenient"] == 0.0
    r = S.p5_detection_world("P5f", ["c2"], [{"cid": "c2", "line": "Row 5 does not give Q4 that value"}], ALT)
    assert r["exact"] == 0.0 and r["lenient"] == 1.0
    r = S.p5_detection_world("P5f", ["c2"], [{"cid": "c2", "line": "row 50 is wrong about Q4"}], ALT)
    assert r["lenient"] == 0.0
    r = S.p5_detection_world("P5f", ["c3"], [{"cid": "c3", "line": "J7: there is no evidence row? wrong"}], ALT)
    assert r["exact"] == 0.0 and r["lenient"] == 1.0


def test_false_alarm_and_missing():
    r = S.p5_detection_world("P5v", ["c0", "c1"], [{"cid": "c1", "line": "anything"}], None)
    assert r["false_alarm"] == 0.5
    r = S.p5_detection_world("P5v", ["c0", "c1"], [{"cid": "c7", "line": "anything"}], None)
    assert r["false_alarm"] == 0.0 and r["counts"]["entries_unnamed"] == 1
    assert S.p5_detection_world("P5v", ["c0"], None, None)["valid"] is False


# --------------------------------------------------------------------------- providers

def test_deepseek_cost_peak_upper_bound(tmp_path):
    from causalguard.llm import providers as PR
    c = PR.deepseek_cost({"prompt_tokens": 3000, "prompt_cache_hit_tokens": 1000, "prompt_cache_miss_tokens": 2000,
                          "completion_tokens": 10000})
    assert c["usd_upper"] == pytest.approx((1000 * 0.044 + 2000 * 1.32 + 10000 * 3.96) / 1e6)
    led = str(tmp_path / "spend.jsonl")
    PR.spend_record(led, {"usd_upper": 24.5})
    PR.spend_record(led, {"usd_upper": 0.6})
    assert PR.spend_total(led) == pytest.approx(25.1)


def test_deepseek_spend_stop_blocks_the_request(tmp_path):
    from causalguard.llm import providers as PR
    led = str(tmp_path / "spend.jsonl")
    PR.spend_record(led, {"usd_upper": 25.0})
    prov = PR.OpenAICompatibleProvider.__new__(PR.OpenAICompatibleProvider)
    prov.cfg = PR.ProviderConfig.from_dict({"kind": "openai_compatible", "backend": "deepseek", "model": "m",
                                            "base_url": "https://api.deepseek.com", "allow_remote": True,
                                            "extra": {"spend_ledger": led}})
    with pytest.raises(PR.CapExceeded):
        prov._send([{"role": "user", "content": "x"}], 0.0, None)


def test_claude_thinking_text_from_transcript(tmp_path, monkeypatch):
    from causalguard.llm import providers as PR
    prov = PR.ClaudeCLIProvider(PR.ProviderConfig.from_dict({"kind": "claude_cli", "model": "m",
                                                             "extra": {"thinking_summaries": True}}))
    tr = tmp_path / "t.jsonl"
    rows = [{"type": "api-request"}, {"type": "assistant", "message": {"content": [
        {"type": "thinking", "thinking": "summary A"}, {"type": "text", "text": "answer"}]}},
        {"type": "api-request"}, {"type": "assistant", "message": {"content": [
            {"type": "thinking", "thinking": ""}, {"type": "thinking", "thinking": "summary B"}]}}]
    tr.write_text("\n".join(json.dumps(r) for r in rows))
    monkeypatch.setattr(PR.ClaudeCLIProvider, "transcript", staticmethod(lambda w, s: tr))
    th = prov.thinking_text("w", "s")
    assert th == {"text": "summary B", "blocks": 2, "with_text": 1}
    assert "--settings" in prov.argv("sys", "sess", False)


# --------------------------------------------------------------------------- lock v1 keys

def test_lock_v1_keys_byte_identical():
    """Every key of the v1 lock (commit 1e79358) is unchanged in docs/SPRINT_DESIGN_LOCK.json."""
    try:
        old = subprocess.run(["git", "show", "1e79358:docs/SPRINT_DESIGN_LOCK.json"], cwd=REPO, capture_output=True,
                             text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("lock v1 commit not available (shallow clone)")
    v1 = json.loads(old)
    now = json.loads((REPO / "docs/SPRINT_DESIGN_LOCK.json").read_text())
    for k, v in v1.items():
        assert json.dumps(now[k], sort_keys=True) == json.dumps(v, sort_keys=True), k
    assert set(now) - set(v1) <= {"addenda"}


def test_p5_manifest_is_reproducible():
    m = P.manifest_p5()
    assert json.dumps(m, indent=1, sort_keys=True) + "\n" == (REPO / "artifacts/sprint_p5_manifest.json").read_text()


def test_contradiction_descriptor():
    from causalguard.sprint.p5_analysis import contradiction
    a = "c0: settled TRUE.\n  step 2: C1 reads P0=1, Y3=0; row #01 shows C1 -> 1.\n"
    b = "c2: settled TRUE.\n  step 2: C1 reads P0=1, Y3=0; row #01 shows C1 -> 0.\n"
    c = "c3: NOT SETTLED.\n  step 2: C1 reads P0=1, Y3=0; no evidence row shows these inputs, so C1 can be 0 or 1.\n"
    assert not contradiction(a + a) and contradiction(a + b) and contradiction(a + c)
