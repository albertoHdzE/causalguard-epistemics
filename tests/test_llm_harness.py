"""WP7 acceptance tests: instrumented mock runs of the S3 harness (no real model calls)."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from causalguard.experiments import s3
from causalguard.llm.harness import CRITIQUE_PROMPT, CallBudget, WorldHarness, aggregate_c, contains_label
from causalguard.llm.parse import parse_answer
from causalguard.llm.providers import MockProvider, OpenAICompatibleProvider, ProviderConfig, ReplayProvider, TransportError
from causalguard.runner import Run, read_jsonl
from causalguard.s3_tasks import INSTRUCTIONS, VERDICT_LABELS, make_s3_items, render_item_prompt

SALT = "test-wp7"


def ans(v="entailed", p=(0.8, 0.1, 0.1)):
    return json.dumps({"verdict": v, "probabilities": dict(zip(VERDICT_LABELS, p)), "reason": "r"})


def mk_world(index=1):
    d = make_s3_items(SALT, index)
    return d["public"], d["private"]


def mock(script=None, **kw):
    cfg = ProviderConfig(kind="mock", model="mock-model", seed=7, **kw)
    return MockProvider(cfg, script if script is not None else (lambda m, t, s: ans()))


def run_h(prov, index=1, hcfg=None, budget=None):
    pub, priv = mk_world(index)
    return pub, priv, WorldHarness(prov, pub, priv, hcfg, budget).run()


def users(msgs):
    return [m["content"] for m in msgs if m["role"] == "user"]


# ------------------------------------------------------------------ arm isolation and sharing
def test_call_structure_and_shared_first_answer():
    prov = mock()
    pub, priv, res = run_h(prov)
    n_items = len(pub["items"])
    assert len(prov.calls) == n_items * 7 + 2 == len(res["call_order"])
    for i in range(n_items):
        first = [{"role": "user", "content": render_item_prompt(pub, i)}]
        # the A prompt at temperature 0 is sent exactly once and reused by B/C/D/D_label
        assert sum(1 for c in prov.calls if c["messages"] == first and c["temperature"] == 0.0) == 1
        a = f"i{i}/A"
        assert res["arms"]["B"][str(i)]["logical"][0] == a
        assert res["arms"]["C"][str(i)]["members"][0] == a
        assert res["arms"]["D"][str(i)]["logical"][0] == a
        assert res["arms"]["D_label"][str(i)]["logical"][0] == a
        for cid in (f"i{i}/B", f"i{i}/D1", f"i{i}/DL"):
            assert res["calls"][cid]["messages"][:2] == first + [{"role": "assistant",
                                                                   "content": res["calls"][a]["raw_output"]}]
    cost = res["cost"]
    assert cost["physical"]["attempts"] == len(prov.calls)
    assert cost["logical_standalone_by_arm"]["B"]["attempts"] == 2 * n_items
    assert cost["logical_standalone_by_arm"]["C"]["attempts"] == 3 * n_items
    assert cost["logical_standalone_by_arm"]["T_D"]["attempts"] == 4
    assert cost["attempts_saved_by_sharing"] > 0


def test_b_sees_no_external_information():
    prov = mock()
    pub, priv, res = run_h(prov)
    for i in range(len(pub["items"])):
        u = users(res["calls"][f"i{i}/B"]["messages"])
        assert u == [render_item_prompt(pub, i), CRITIQUE_PROMPT]
        assert not contains_label(CRITIQUE_PROMPT)


def test_c_draws_are_fresh_contexts():
    prov = mock()
    pub, priv, res = run_h(prov)
    for i in range(len(pub["items"])):
        seeds = set()
        for s in (1, 2):
            c = res["calls"][f"i{i}/C{s}"]
            assert c["messages"] == [{"role": "user", "content": render_item_prompt(pub, i)}]
            assert c["temperature"] == 0.7
            seeds.add(c["seed"])
        seeds.add(res["calls"][f"i{i}/A"]["seed"])
        assert len(seeds) == 3


def test_d_feedback_has_no_label_and_dlabel_has_it():
    prov = mock()
    pub, priv, res = run_h(prov)
    for i, it in enumerate(priv["items"]):
        d = res["arms"]["D"][str(i)]
        assert len(d["rounds"]) == 2
        for r in d["rounds"]:
            assert r["feedback_provenance"]["source"] == "symbolic_checker_witnesses"
            fb = users(res["calls"][r["call"]]["messages"])[-1]
            assert "checker found this system" in fb and not contains_label(fb)
        dl = users(res["calls"][f"i{i}/DL"]["messages"])[-1]
        assert it["verdict"] in dl


def test_prompts_never_leak_label_outside_instructions():
    prov = mock()
    pub, priv, res = run_h(prov)
    for cid, c in res["calls"].items():
        for u in users(c["messages"]):
            stripped = u.replace(INSTRUCTIONS, "")
            if cid.endswith("/DL") and u == users(c["messages"])[-1]:
                assert contains_label(stripped)
            else:
                assert not contains_label(stripped), cid


def test_transfer_contexts():
    prov = mock()
    pub, priv, res = run_h(prov)
    ta, td = res["calls"]["T_A"]["messages"], res["calls"]["T_D"]["messages"]
    target = render_item_prompt(pub, 1)
    assert users(ta) == [render_item_prompt(pub, 0), target]
    assert len(users(td)) == 4 and users(td)[-1] == target  # prompt0, fb1, fb2, target
    assert res["arms"]["T_A"]["1"]["final"]["verdict"] == "entailed"


def test_e_has_no_llm_call():
    prov = mock()
    pub, priv, res = run_h(prov, hcfg={"arms": ["E"]})
    assert prov.calls == [] and res["arms"]["E"]["0"]["final"]["verdict"] == priv["items"][0]["verdict"]


# ------------------------------------------------------------------ caps, retries, content errors
def test_world_cap_enforced_and_recorded():
    prov = mock()
    pub, priv, res = run_h(prov, budget=CallBudget(5, None))
    assert res["world_status"] == "world_cap_reached" and len(prov.calls) == 5


def test_global_cap_via_ledger(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    p1, p2 = mock(), mock()
    _, _, r1 = run_h(p1, 1, budget=CallBudget(40, 33, ledger, "w1"))
    _, _, r2 = run_h(p2, 2, budget=CallBudget(40, 33, ledger, "w2"))
    assert r1["world_status"] == "complete" and len(p1.calls) == 30
    assert r2["world_status"] == "global_cap_reached" and len(p2.calls) == 3
    assert len(ledger.read_text().splitlines()) == 33


def test_transport_retry_bounded_and_logged():
    prov = mock(script=lambda m, t, s: (_ for _ in ()).throw(TransportError("conn refused")),
                max_transport_retries=2)
    pub, priv, res = run_h(prov, hcfg={"arms": ["A", "B", "D"]})
    a = res["calls"]["i0/A"]
    assert len(a["attempts"]) == 3 and not a["ok"] and all("transport" in x["error"] for x in a["attempts"])
    assert a["parsed"]["status"] == "provider_failure"
    assert res["arms"]["B"]["0"]["final"]["flags"] == ["dependent_on_failed_first_answer"]
    assert "i0/B" not in res["calls"] and "i0/D1" not in res["calls"]
    assert res["cost"]["physical"]["attempts"] == 3 * len(pub["items"]) == len(prov.calls)


def test_retry_then_success_and_content_error_not_retried():
    prov = mock(script=[TransportError("reset"), "this is not json"], max_transport_retries=2)
    pub, priv, res = run_h(prov, hcfg={"arms": ["A"]}, budget=CallBudget(2, None))
    a = res["calls"]["i0/A"]
    assert [x["ok"] for x in a["attempts"]] == [False, True]
    assert a["parsed"]["status"] == "invalid_json"
    assert res["world_status"] == "world_cap_reached"  # item 1 would need a third attempt


class _Handler(BaseHTTPRequestHandler):
    codes: list = []
    seen: list = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).seen.append(body)
        code = type(self).codes.pop(0) if type(self).codes else 200
        out = (json.dumps({"model": body["model"], "choices": [{"message": {"content": ans()}, "finish_reason": "stop"}],
                           "usage": {"prompt_tokens": 11, "completion_tokens": 5}}).encode() if code == 200 else b"{}")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


@pytest.fixture
def server():
    _Handler.codes, _Handler.seen = [], []
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    yield srv
    srv.shutdown()


def test_http_adapter_retries_5xx_not_4xx(server):
    cfg = ProviderConfig(base_url=f"http://127.0.0.1:{server.server_port}/v1", model="m", backend="other",
                         timeout_s=5, seed=3)
    prov = OpenAICompatibleProvider(cfg)
    _Handler.codes = [503]
    r = prov.chat([{"role": "user", "content": "hi"}], 0.0, 3)
    assert r["ok"] and len(r["attempts"]) == 2 and r["attempts"][1]["prompt_tokens"] == 11
    assert _Handler.seen[-1]["seed"] == 3 and _Handler.seen[-1]["max_tokens"] == 400
    _Handler.codes = [400]
    r = prov.chat([{"role": "user", "content": "hi"}], 0.0, 3)
    assert not r["ok"] and len(r["attempts"]) == 1 and r["attempts"][0]["error"].startswith("fatal")


def test_non_local_refused():
    with pytest.raises(ValueError):
        OpenAICompatibleProvider(ProviderConfig(base_url="https://api.example.com/v1", model="m"))


# ------------------------------------------------------------------ aggregation and parsing
def P(v, p=(0.6, 0.2, 0.2)):
    return parse_answer(ans(v, p))


def test_c_aggregation_deterministic():
    m = [P("entailed", (1, 0, 0)), P("refuted", (0, 1, 0)), P("entailed", (0.5, 0.5, 0))]
    a = aggregate_c(m)
    assert a["verdict"] == "entailed" and a["n_valid_vectors"] == 3
    assert a["probabilities"] == pytest.approx({"entailed": 0.5, "refuted": 0.5, "underdetermined": 0.0})
    tie = aggregate_c([P("entailed"), P("refuted"), P("underdetermined")])
    assert tie["status"] == "abstain" and tie["verdict"] is None and "vote_tie" in tie["flags"]
    bad = parse_answer("nope")
    tie2 = aggregate_c([P("entailed", (1, 0, 0)), P("refuted", (0, 1, 0)), bad])
    assert tie2["status"] == "abstain" and tie2["invalid_members"] == [2] and tie2["n_valid_vectors"] == 2
    badp = parse_answer(json.dumps({"verdict": "refuted", "probabilities": {"entailed": 2}}))
    one = aggregate_c([bad, badp, P("refuted", (0.2, 0.8, 0))])
    assert one["verdict"] == "refuted" and one["n_valid_vectors"] == 1 and one["invalid_members"] == [0, 1]
    none = aggregate_c([bad, bad, badp])   # one valid vote of three: no strict majority -> abstain
    assert none["probabilities"] is None and not none["probs_valid"] and none["verdict"] is None
    assert none["status"] == "abstain" and "no_strict_majority" in none["flags"]
    two_bad_probs = aggregate_c([badp, badp, bad])   # 2/3 valid votes, no valid probability vector
    assert two_bad_probs["verdict"] == "refuted" and two_bad_probs["status"] == "invalid_probabilities"
    assert aggregate_c(m) == aggregate_c(m)


@pytest.mark.parametrize("raw,status,vv,pv", [
    (None, "provider_failure", False, False),
    ("I think it is entailed", "invalid_json", False, False),
    ('{"verdict": "entailed", "probabilities": {', "invalid_json", False, False),
    ('[1, 2]', "semantic_error", False, False),
    ('{"answer": "entailed"}', "semantic_error", False, False),
    (ans("abstain"), "abstain", False, True),
    (ans("maybe"), "invalid_verdict", False, True),
    (ans("entailed", (0.5, 0.2, 0.2)), "invalid_probabilities", True, False),
    (ans("entailed", (1.2, -0.2, 0.0)), "invalid_probabilities", True, False),
    (json.dumps({"verdict": "refuted", "probabilities": {"entailed": "0.5", "refuted": 0.5,
                                                         "underdetermined": 0}}), "invalid_probabilities", True, False),
    (json.dumps({"verdict": "refuted", "probabilities": {"entailed": 0.5, "refuted": 0.5}}),
     "invalid_probabilities", True, False),
    (ans("entailed", (0.99, 0.0, 0.0)), "ok", True, True),
    ("Sure!\n```json\n" + ans("refuted", (0.1, 0.8, 0.1)) + "\n```\nDone.", "ok", True, True),
    ("<think>maybe {\"verdict\": \"refuted\"}</think>" + ans("entailed"), "ok", True, True),
])
def test_parser_taxonomy(raw, status, vv, pv):
    r = parse_answer(raw, provider_ok=raw is not None)
    assert (r["status"], r["verdict_valid"], r["probs_valid"]) == (status, vv, pv)


def test_parser_flags():
    r = parse_answer(ans("refuted", (0.6, 0.3, 0.1)))
    assert r["status"] == "ok" and "verdict_prob_mismatch" in r["flags"]
    r = parse_answer("<think>x</think>" + ans(" Entailed "))
    assert r["verdict"] == "entailed" and {"think_stripped", "verdict_normalized"} <= set(r["flags"])
    assert parse_answer("```json\n" + ans() + "\n```")["flags"] == ["extracted_object"]


# ------------------------------------------------------------------ scoring
def test_brier_hand_values():
    assert s3.brier({"entailed": 1, "refuted": 0, "underdetermined": 0}, "entailed") == 0
    assert s3.brier({"entailed": 0, "refuted": 1, "underdetermined": 0}, "entailed") == 2
    assert s3.brier({k: 1 / 3 for k in VERDICT_LABELS}, "entailed") == pytest.approx(2 / 3)


def _mock_records(policy="always_underdetermined", worlds=(0, 1, 2)):
    cfg = {"salt": SALT, "provider": {"kind": "mock", "model": "mock-model", "extra": {"policy": policy}},
           "harness": {}, "caps": {"calls_per_world": 40}}
    return [s3.run_world(s3.build_payload(cfg, i)) for i in worlds]


def test_score_mock_and_mixing_refused():
    recs = _mock_records()
    with pytest.raises(ValueError):
        s3.score(recs)
    s = s3.score(recs, allow_mock=True)
    ys = [it["verdict"] for r in recs for it in r["oracle"]["items"]]
    acc = sum(y == "underdetermined" for y in ys) / len(ys)
    assert s["arms"]["A"]["accuracy"] == pytest.approx(acc)
    assert s["arms"]["E"]["accuracy"] == 1 and s["arms"]["E"]["brier_worst_case"] == 0
    assert s["arms"]["A"]["validity_coverage"] == 1
    # always 'underdetermined' with p=0.8: balanced accuracy = recall(underdetermined)/n_classes_present
    n_cls = len(set(ys))
    assert s["arms"]["A"]["balanced_accuracy"] == pytest.approx(1 / n_cls)
    pw = s3.per_world_scores(recs, allow_mock=True)
    assert [r["world_id"] for r in pw] == sorted(r["world_id"] for r in recs)
    fake_real = json.loads(json.dumps(recs[0]))
    fake_real["provider_kind"] = "real"
    for c in fake_real["calls"].values():
        c["provider_kind"] = "real"
    with pytest.raises(ValueError):
        s3.score(recs + [fake_real], allow_mock=True)
    s3.score([fake_real])  # a homogeneous real set is accepted


def test_worst_case_and_revisions():
    rec = _mock_records(worlds=(0,))[0]
    y0 = rec["oracle"]["items"][0]["verdict"]
    wrong = next(v for v in VERDICT_LABELS if v != y0)
    rec["arms"]["A"]["0"]["final"] = {"status": "ok", "verdict": y0, "verdict_valid": True,
                                      "probabilities": {k: float(k == y0) for k in VERDICT_LABELS},
                                      "probs_valid": True}
    rec["arms"]["B"]["0"]["final"] = {"status": "invalid_json", "verdict": None, "verdict_valid": False,
                                      "probabilities": None, "probs_valid": False}
    rec["arms"]["D"]["0"]["final"] = {"status": "invalid_probabilities", "verdict": wrong, "verdict_valid": True,
                                      "probabilities": None, "probs_valid": False}
    row = s3.per_world_scores([rec], allow_mock=True)[0]
    assert row["revisions"]["B_vs_A"]["correct_to_wrong"] >= 1
    assert row["revisions"]["D_vs_A"]["correct_to_wrong"] >= 1
    assert row["arms"]["B"]["status_counts"]["invalid_json"] == 1
    n = row["arms"]["B"]["n_items"]
    assert row["arms"]["B"]["brier_worst_sum"] == pytest.approx(2.0 + (row["arms"]["B"]["brier_valid_sum"]))
    assert row["arms"]["B"]["validity_coverage"] == pytest.approx((n - 1) / n)


def test_replay_reproduces_record():
    recs = _mock_records(worlds=(0,))
    cfg = ProviderConfig(kind="replay", model="mock-model", seed=0)
    rp = ReplayProvider.from_records(cfg, recs)
    p = s3.build_payload({"salt": SALT, "provider": {"kind": "replay", "model": "mock-model", "seed": 0},
                          "harness": {}, "caps": {}}, 0)
    r = s3.run_world_with(rp, p)
    assert r["provider_kind"] == "replay"
    assert {k: c["raw_output"] for k, c in r["calls"].items()} == {k: c["raw_output"] for k, c in recs[0]["calls"].items()}


def test_resume_does_not_duplicate(tmp_path):
    cfg = {"salt": SALT, "world_index_start": 0, "world_index_stop": 2,
           "provider": {"kind": "mock", "model": "mock-model", "extra": {"policy": "always_entailed"}},
           "harness": {"arms": ["A", "E"]}, "caps": {"calls_per_world": 10}}
    kw = dict(runs_root=tmp_path / "runs", registry=tmp_path / "RUNS.jsonl")
    items = [(f"w{i}", s3.build_payload(cfg, i)) for i in range(2)]
    run = Run("t", cfg, **kw)
    run.execute(items[:1], s3.run_world, timeout_s=60)
    run = Run("t", cfg, **kw)
    end = run.execute(items, s3.run_world, timeout_s=60)
    assert end["skipped_already_done"] == 1 and end["ok"] == 1
    recs = read_jsonl(run.records)
    assert sorted(r["item_id"] for r in recs) == ["w0", "w1"]
    assert all(r["provider_kind"] == "mock" for r in recs)
    with pytest.raises(RuntimeError):
        Run("t", {**cfg, "salt": "other"}, **kw)
