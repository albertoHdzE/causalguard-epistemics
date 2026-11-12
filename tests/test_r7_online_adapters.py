# ruff: noqa: E501
"""R7 online adapters, dry runs with no network and no model: the DeepSeek key handling and the Claude CLI route
(a fake ``claude`` binary that records its arguments and writes a transcript like the real CLI)."""
from __future__ import annotations

import json
import sys
import textwrap

import pytest

from causalguard.llm.providers import ClaudeCLIProvider, ProviderConfig, make_provider

KEY = "test-key-0123456789"


class _Resp:
    def __init__(self, body: dict):
        self.body = json.dumps(body).encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_deepseek_key_sent_only_to_deepseek_and_never_recorded(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", KEY)
    seen = []

    def fake_urlopen(req, timeout=None):
        seen.append((req.full_url, dict(req.header_items()), json.loads(req.data)))
        return _Resp({"model": "deepseek-v4-pro", "choices": [{"message": {"content": '{"answers": []}',
                                                                           "reasoning_content": "hidden"},
                                                               "finish_reason": "stop"}],
                      "usage": {"prompt_tokens": 10, "completion_tokens": 5}})
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    from causalguard.sprint.online import TARGETS
    cfg = dict(TARGETS["deepseek"])
    cfg["extra"] = {**cfg["extra"], "env_file": None}
    p = make_provider(cfg)
    r = p.chat([{"role": "system", "content": "s"}, {"role": "user", "content": "u"}], 0.0, 1)
    assert r["ok"] and r["raw_output"] == '{"answers": []}'
    url, headers, body = seen[0]
    assert url == "https://api.deepseek.com/chat/completions"
    assert headers["Authorization"] == "Bearer " + KEY
    assert body["thinking"] == {"type": "enabled"} and body["model"] == "deepseek-v4-pro"
    assert KEY not in json.dumps(r) and KEY not in repr(p) and KEY not in json.dumps(p.cfg.__dict__)


def test_deepseek_refuses_other_hosts(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", KEY)
    with pytest.raises(ValueError):
        make_provider({"kind": "openai_compatible", "backend": "deepseek", "base_url": "https://example.com",
                       "model": "x", "allow_remote": True, "extra": {}})


FAKE = textwrap.dedent(r'''
    import json, os, re, sys
    a = sys.argv[1:]
    prompt = sys.stdin.read()
    sysp = a[a.index("--system-prompt") + 1]
    sess = a[a.index("--session-id") + 1] if "--session-id" in a else a[a.index("--resume") + 1]
    d = os.path.join(os.environ["HOME"], ".claude", "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(os.getcwd())))
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, sess + ".jsonl")
    with open(os.path.join(os.environ["HOME"], "argv.jsonl"), "a") as fh:
        fh.write(json.dumps({"argv": a, "cwd_files": os.listdir(os.getcwd())}) + "\n")
    inject = os.environ.get("FAKE_INJECT")
    with open(path, "a") as fh:
        rows = [{"type": "api-request-shape", "shape": {"system": [{"type": "text", "text": "You are a Claude agent, built on Anthropic's Claude Agent SDK."}, {"type": "text", "text": sysp}], "tools": []}}]
        if "--session-id" in a:
            rows.append({"type": "api-request-blob", "message": {"role": "user", "content": [{"type": "text", "text": "<system-reminder>\nAs you answer the user's questions, you can use the following context:\n# userEmail\nx\n</system-reminder>\n"}, {"type": "text", "text": prompt}]}})
            rows.append({"type": "api-request-blob", "message": {"role": "system", "content": [{"type": "text", "text": "# Environment\nYou have been invoked in the following environment: x"}]}})
        else:
            rows.append({"type": "user", "message": {"role": "user", "content": prompt}})
        if inject:
            rows.append({"type": "api-request-blob", "message": {"role": "user", "content": [{"type": "text", "text": inject}]}})
        rows.append({"type": "api-request"})
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(json.dumps({"result": '{"answers": [{"cid": "c0", "verdict": "true", "probability": 1}]}', "is_error": False,
                      "usage": {"input_tokens": 3, "cache_creation_input_tokens": 500, "cache_read_input_tokens": 0, "output_tokens": 9},
                      "modelUsage": {"claude-opus-5-5": {}}, "stop_reason": "end_turn"}))
''')


@pytest.fixture
def fake_claude(tmp_path, monkeypatch):
    b = tmp_path / "claude"
    b.write_text("#!" + sys.executable + "\n" + FAKE)
    b.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return str(b), home


def test_claude_cli_two_turns_one_session_isolated(fake_claude):
    binary, home = fake_claude
    p = ClaudeCLIProvider(ProviderConfig(kind="claude_cli", model="claude-opus-5-5", max_transport_retries=0,
                                         seed=None, extra={"binary": binary}))
    m = [{"role": "system", "content": "SYS"}, {"role": "user", "content": "TURN1"}]
    r1 = p.chat(m, 0.0, None)
    assert r1["ok"], r1["failure"]
    assert r1["attempts"][0]["isolation"]["ok"]
    m2 = m + [{"role": "assistant", "content": r1["raw_output"]}, {"role": "user", "content": "TURN2"}]
    r2 = p.chat(m2, 0.0, None)
    assert r2["ok"], r2["failure"]
    calls = [json.loads(x) for x in (home / "argv.jsonl").read_text().splitlines()]
    a1, a2 = calls[0]["argv"], calls[1]["argv"]
    for a in (a1, a2):
        for flag in ("--system-prompt", "--tools", "--strict-mcp-config", "--setting-sources",
                     "--disable-slash-commands", "--output-format"):
            assert flag in a
        assert a[a.index("--tools") + 1] == "" and a[a.index("--setting-sources") + 1] == ""
    assert a2[a2.index("--resume") + 1] == a1[a1.index("--session-id") + 1]
    assert calls[0]["cwd_files"] == [] and calls[1]["cwd_files"] == []
    # a conversation it does not hold cannot be continued
    bad = m + [{"role": "assistant", "content": "something else"}, {"role": "user", "content": "TURN2"}]
    assert not p.chat(bad, 0.0, None)["ok"]


def test_claude_cli_audit_fails_on_injected_context(fake_claude, monkeypatch):
    binary, _ = fake_claude
    monkeypatch.setenv("FAKE_INJECT", "<system-reminder>Contents of CLAUDE.md: project rules</system-reminder>")
    p = ClaudeCLIProvider(ProviderConfig(kind="claude_cli", model="claude-opus-5-5", max_transport_retries=0,
                                         seed=None, extra={"binary": binary}))
    r = p.chat([{"role": "system", "content": "SYS"}, {"role": "user", "content": "TURN1"}], 0.0, None)
    assert not r["ok"] and "isolation audit failed" in r["failure"]


def test_claude_cli_mock_episode_through_sprint_harness(fake_claude, tmp_path):
    """The full two-turn sprint episode runs through the CLI adapter (fake binary; no model, no benchmark item
    leaves the machine)."""
    binary, _ = fake_claude
    from causalguard.sprint import population as P
    from causalguard.sprint.episode import sprint_world
    ks = P.world_keys("smoke")
    a = P.assign(ks)
    rec = sprint_world({"world": ks[0].to_json(), **a[ks[0].wkey], "global_cap": 10,
                        "call_ledger": str(tmp_path / "l.jsonl"),
                        "provider": {"kind": "claude_cli", "model": "claude-opus-5-5", "seed": None,
                                     "max_transport_retries": 0, "extra": {"binary": binary}}})
    assert rec["status"] == "ok" and rec["calls_used"] == 2
    assert all(t["ok"] for t in rec["episode"]["turns"])
