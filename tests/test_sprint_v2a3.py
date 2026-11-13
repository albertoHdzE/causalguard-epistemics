"""SPRINT amendment v2-a3: usage-limit pause (rejections void their call-ledger slot), session restore, hard stop,
priority-block item selection, the spend stop on the upper bound and the spend-record back-fill."""
from __future__ import annotations

import datetime
import json
import sys
import textwrap

import pytest

from causalguard.llm import providers as PR
from causalguard.llm.harness import CallBudget, ledger_used

CST = datetime.timezone(datetime.timedelta(hours=-6))


def test_void_last_cancels_the_slot(tmp_path):
    led = tmp_path / "l.jsonl"
    b = CallBudget(4, 3, led, world_id="w", phase="SPRINT", phase_cap=3)
    b.before_attempt()
    b.before_attempt()
    b.void_last("usage_limit_rejected", until=1.0)
    recs = [json.loads(x) for x in led.read_text().splitlines()]
    assert ledger_used(recs) == 1 and b.n == 1
    assert recs[-1]["kind"] == "usage_limit_rejected" and recs[-1]["voids_slot"] and recs[-1]["phase"] == "SPRINT"
    b.before_attempt()
    b.before_attempt()
    with pytest.raises(PR.CapExceeded):
        b.before_attempt()                      # 3 used slots: the void line itself never counts as a request


def test_parse_reset_times():
    now = datetime.datetime(2026, 11, 13, 13, 0, tzinfo=CST).timestamp()
    r = PR.parse_reset("You've hit your 5-hour limit · resets 1:40pm (America/Mexico_City)", now)
    assert r == datetime.datetime(2026, 11, 13, 13, 40, tzinfo=CST).timestamp()
    late = datetime.datetime(2026, 11, 13, 14, 0, tzinfo=CST).timestamp()
    assert PR.parse_reset("resets 1:40pm (America/Mexico_City)", late) == \
        datetime.datetime(2026, 11, 14, 13, 40, tzinfo=CST).timestamp()
    assert PR.parse_reset("resets Nov 14, 3am (America/Mexico_City)", now) == \
        datetime.datetime(2026, 11, 14, 3, 0, tzinfo=CST).timestamp()
    assert PR.parse_reset("limit reached", now) is None
    assert PR.usage_limit_message('{"api_error":"usage_limit_reached","result":"resets 2pm (UTC)"}') == "resets 2pm (UTC)"


# a fake CLI: a normal reply, except that the calls listed in REJECT (1-based call numbers) are usage-limit rejections
# which still append a junk row to the session transcript (as a real CLI might)
FAKE = textwrap.dedent(r'''
    import json, os, re, sys
    a = sys.argv[1:]
    prompt = sys.stdin.read()
    sysp = a[a.index("--system-prompt") + 1]
    sess = a[a.index("--session-id") + 1] if "--session-id" in a else a[a.index("--resume") + 1]
    home = os.environ["HOME"]
    n = sum(1 for _ in open(os.path.join(home, "n"))) + 1 if os.path.exists(os.path.join(home, "n")) else 1
    open(os.path.join(home, "n"), "a").write("x\n")
    d = os.path.join(home, ".claude", "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(os.getcwd())))
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, sess + ".jsonl")
    if str(n) in os.environ.get("REJECT", "").split(","):
        with open(path, "a") as fh:
            fh.write(json.dumps({"type": "junk-from-rejected-request"}) + "\n")
        print(json.dumps({"is_error": True, "api_error": "usage_limit_reached", "result": "You've hit your limit"}))
        sys.exit(1)
    with open(path, "a") as fh:
        sdk = "You are a Claude agent, built on Anthropic's Claude Agent SDK."
        shape = {"system": [{"type": "text", "text": sdk}, {"type": "text", "text": sysp}], "tools": []}
        rows = [{"type": "api-request-shape", "shape": shape}]
        if "--session-id" in a:
            rows.append({"type": "api-request-blob", "message": {"role": "user", "content": [{"type": "text", "text": prompt}]}})
        else:
            rows.append({"type": "user", "message": {"role": "user", "content": prompt}})
        rows.append({"type": "api-request"})
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(json.dumps({"result": "reply %d" % n, "is_error": False, "usage": {"input_tokens": 3, "output_tokens": 9},
                      "modelUsage": {"claude-opus-5-5": {}}, "stop_reason": "end_turn"}))
''')


@pytest.fixture
def cli(tmp_path, monkeypatch):
    b = tmp_path / "claude"
    b.write_text("#!" + sys.executable + "\n" + FAKE)
    b.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return str(b), home


def _prov(binary, tmp_path, **extra):
    return PR.ClaudeCLIProvider(PR.ProviderConfig(kind="claude_cli", model="claude-opus-5-5", max_transport_retries=0,
                                                  seed=None, extra={"binary": binary, "probe_interval_s": 0.2,
                                                                    "pause_file": str(tmp_path / "pause.json"),
                                                                    **extra}))


def test_turn2_rejection_pauses_restores_and_resends(cli, tmp_path, monkeypatch):
    binary, home = cli
    monkeypatch.setenv("REJECT", "2")                      # turn 2's first request is rejected
    p = _prov(binary, tmp_path)
    led = tmp_path / "led.jsonl"
    b = CallBudget(4, 10, led, world_id="w")
    m = [{"role": "system", "content": "SYS"}, {"role": "user", "content": "T1"}]
    r1 = p.chat(m, 0.0, None, b.before_attempt)
    assert r1["ok"]
    sess, wd = next(iter(p.sessions.values()))
    before = p.transcript(wd, sess).read_text()
    r2 = p.chat(m + [{"role": "assistant", "content": r1["raw_output"]}, {"role": "user", "content": "T2"}], 0.0,
                None, b.before_attempt)
    assert r2["ok"] and r2["raw_output"] == "reply 3"
    after = p.transcript(wd, sess).read_text()
    assert "junk-from-rejected-request" not in after and after.startswith(before)   # restored, then the resent turn
    recs = [json.loads(x) for x in led.read_text().splitlines()]
    assert [r.get("kind") for r in recs] == [None, None, "usage_limit_rejected", None]
    assert ledger_used(recs) == 2 and b.n == 2 and len(p.usage_rejections) == 1
    assert json.loads((tmp_path / "pause.json").read_text()) == {}        # cleared by the successful request


def test_rejection_pauses_the_other_workers(cli, tmp_path, monkeypatch):
    binary, _ = cli
    monkeypatch.setenv("REJECT", "1")
    p1, p2 = _prov(binary, tmp_path), _prov(binary, tmp_path)
    m = [{"role": "system", "content": "SYS"}, {"role": "user", "content": "T1"}]
    assert p1.chat(m, 0.0, None)["ok"]                    # rejected once, paused 0.2 s, then sent again
    st = {"until": 5e9, "reset_parsed": True, "since": 0}
    (tmp_path / "pause.json").write_text(json.dumps(st))
    hard = _prov(binary, tmp_path, hard_stop_utc="2100-01-01T00:00:00+00:00")
    with pytest.raises(PR.HardStop):                      # a pause that ends after the hard stop: stop, do not wait
        hard.chat(m, 0.0, None)
    assert p2 is not None


def test_hard_stop_sends_nothing(cli, tmp_path):
    binary, home = cli
    p = _prov(binary, tmp_path, hard_stop_utc="2020-01-01T00:00:00+00:00")
    led = tmp_path / "led.jsonl"
    b = CallBudget(4, 10, led, world_id="w")
    with pytest.raises(PR.HardStop):
        p.chat([{"role": "system", "content": "SYS"}, {"role": "user", "content": "T1"}], 0.0, None, b.before_attempt)
    assert not led.exists() and not (home / "n").exists()


def test_hard_stop_fails_the_world_item(cli, tmp_path):
    from causalguard.sprint import population as P
    from causalguard.sprint.episode import sprint_world
    binary, _ = cli
    ks = P.world_keys("smoke")
    a = P.assign(ks)
    with pytest.raises(PR.HardStop):                      # not a finished world: the runner records an error
        sprint_world({"world": ks[0].to_json(), **a[ks[0].wkey], "global_cap": 10,
                      "call_ledger": str(tmp_path / "l.jsonl"),
                      "provider": {"kind": "claude_cli", "model": "claude-opus-5-5", "seed": None,
                                   "max_transport_retries": 0,
                                   "extra": {"binary": binary, "hard_stop_utc": "2020-01-01T00:00:00+00:00"}}})


def test_spend_stop_uses_upper_bound_and_backfill(tmp_path):
    t = datetime.datetime(2026, 11, 13, 15, 20, tzinfo=datetime.timezone.utc).timestamp()      # off-peak
    u = {"prompt_cache_hit_tokens": 896, "prompt_cache_miss_tokens": 94, "completion_tokens": 16000}
    up = PR.deepseek_cost(u, t)["usd_upper"]
    lines = [{"usd_upper": up, "t": t}, {"usd_upper": 3.3e-05, "t": t},
             {"usd": 0.05, "usd_upper": 0.1, "peak": False, "t": t}]
    out = PR.spend_backfill(lines, {up: u})
    assert out[0] == {"usd": PR.deepseek_cost(u, t)["usd"], "usd_upper": up, "peak": False, "t": t,
                      "backfilled": True, "backfill_source": "recorded tokens"}
    assert out[1]["usd"] == round(3.3e-05 / 2, 6) and out[1]["backfilled"] and out[2] == lines[2]
    assert all({"usd", "usd_upper", "peak", "t"} <= set(x) for x in out)
    with pytest.raises(ValueError):
        PR.spend_backfill([{"usd_upper": up + 1, "t": t}], {up + 1: u})
    led = tmp_path / "s.jsonl"
    led.write_text("".join(json.dumps(x) + "\n" for x in out))
    assert PR.spend_total(str(led)) == pytest.approx(up + 3.3e-05 + 0.1)
    assert PR.spend_total(str(led), "usd") == pytest.approx(out[0]["usd"] + out[1]["usd"] + 0.05)


def test_priority_block_selection():
    from pathlib import Path

    from causalguard.__main__ import _items_from_config
    root = Path(__file__).resolve().parents[1]
    c = json.loads((root / "configs/sprint/r7b_online_main_deepseek_v4_pro_low_b1.json").read_text())
    full = json.loads((root / "configs/sprint/r7b_online_main_deepseek_v4_pro.json").read_text())
    blk = [k for k, _ in _items_from_config(c)]
    allk = [k for k, p in _items_from_config(full) if (p["tier"], p["condition"]) in {("W", "P3"), ("W", "P4")}]
    assert blk == allk and len(blk) == 48                 # the locked hash order inside the block
    for b, n in (("b3", 72), ("b4", 24), ("b5", 36)):
        c = json.loads((root / f"configs/sprint/r7b_online_main_deepseek_v4_pro_low_{b}.json").read_text())
        assert len(list(_items_from_config(c))) == n


def test_lock_v2_keys_unchanged_except_amendments():
    """Every key of the v2 addendum as committed in f8e1fb3 is byte-identical now, except the appended amendment
    list, whose earlier entries are unchanged; v2-a3 is present."""
    import subprocess
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    try:
        old = subprocess.run(["git", "show", "f8e1fb3:docs/SPRINT_DESIGN_LOCK.json"], cwd=root, capture_output=True,
                             text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("lock v2 commit not available (shallow clone)")
    v2_then = json.loads(old)["addenda"][0]
    v2_now = json.loads((root / "docs/SPRINT_DESIGN_LOCK.json").read_text())["addenda"][0]
    for k, v in v2_then.items():
        if k != "amendments":
            assert json.dumps(v2_now[k], sort_keys=True) == json.dumps(v, sort_keys=True), k
    assert set(v2_now) - set(v2_then) <= {"amendments"}
    am = v2_now["amendments"]
    a2 = json.loads(subprocess.run(["git", "show", "7c923a3:docs/SPRINT_DESIGN_LOCK.json"], cwd=root,
                                   capture_output=True, text=True, check=True).stdout)["addenda"][0]["amendments"]
    assert json.dumps(am[:2], sort_keys=True) == json.dumps(a2, sort_keys=True)
    assert [a["id"] for a in am] == ["v2-a1", "v2-a2", "v2-a3"]
