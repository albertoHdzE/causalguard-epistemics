"""R7b Task P scoring: adoption, corruption, check discernment (plain and standardised); planted defects; mock
episodes on both tiers; the half-panel selection."""
from __future__ import annotations

import json

import pytest

from causalguard.sprint import population as P
from causalguard.sprint import scoring as S

ENT, REF, UND = S.ENT, S.REF, S.UND


def _a(*vs):
    return {f"c{i}": {"verdict": v, "probability": 0.5} for i, v in enumerate(vs) if v is not None}


def test_check_adoption_hand_case():
    # named c0..c3; true statuses ENT, UND, REF, UND; forged REF, ENT, UND, REF
    ref = {f"c{i}": {"status": s} for i, s in enumerate((ENT, UND, REF, UND))}
    checker = {f"c{i}": s for i, s in enumerate((ENT, UND, REF, UND))}
    forged = {f"c{i}": s for i, s in enumerate((REF, ENT, UND, REF))}
    a1 = _a(ENT, UND, ENT, UND)          # correct: c0, c1, c3
    a2 = _a(REF, ENT, REF, UND)          # c0 forged, c1 forged, c2 checker, c3 checker
    r = S.check_adoption_world(ref, a1, a2, ["c0", "c1", "c2", "c3"], checker, forged)
    assert r["adopt_check"] == 0.5 and r["adopt_forged"] == 0.5
    # checker line kinds: settled {c0, c2} -> adopted c2 only; open {c1, c3} -> c3 only
    assert r["adopt_check_settled"] == 0.5 and r["adopt_check_open"] == 0.5
    # forged line kinds: settled {c0 REF, c1 ENT, c3 REF} -> c0, c1 adopted; open {c2} -> not adopted
    assert r["adopt_forged_settled"] == pytest.approx(2 / 3) and r["adopt_forged_open"] == 0.0
    # corruption: correct at t1 {c0, c1, c3}; wrong at t2 {c0, c1}
    assert r["corruption"] == pytest.approx(2 / 3)


def test_check_adoption_refuses_bad_statuses():
    ref = {"c0": {"status": ENT}}
    with pytest.raises(AssertionError):
        S.check_adoption_world(ref, _a(ENT), _a(ENT), ["c0"], {"c0": REF}, {"c0": UND})
    with pytest.raises(AssertionError):
        S.check_adoption_world(ref, _a(ENT), _a(ENT), ["c0"], {"c0": ENT}, {"c0": ENT})


def _w(cond, ac, af, acs=None, aco=None, afs=None, afo=None):
    return {"condition": cond, "group": f"g{cond}{ac}{af}", "C": {"adopt_check": ac, "adopt_forged": af,
                                                                  "adopt_check_settled": acs, "adopt_check_open": aco,
                                                                  "adopt_forged_settled": afs,
                                                                  "adopt_forged_open": afo}}


def test_check_discernment_plain_and_standardised():
    ws = [_w("P3", 1.0, 0.0, 1.0, 1.0, None, None), _w("P3", 0.5, 0.0, 0.0, 1.0, None, None),
          _w("P4", 0.0, 1.0, None, None, 1.0, 0.0), _w("P4", 0.0, 0.5, None, None, 1.0, None)]
    assert S.check_discernment(ws) == pytest.approx(0.75 - 0.75)
    # settled: P3 mean 0.5, P4 mean 1.0 -> -0.5 ; open: P3 mean 1.0, P4 mean 0.0 -> 1.0 ; average 0.25
    assert S.check_discernment_std(ws) == pytest.approx(0.25)


def test_planted_adoption_defect_is_caught(monkeypatch):
    real = S.check_adoption_world

    def swapped(ref, a1, a2, named, checker, forged):
        return real(ref, a1, a2, named, forged, checker)
    monkeypatch.setattr(S, "check_adoption_world", swapped)
    ref = {"c0": {"status": ENT}}
    with pytest.raises(AssertionError):
        S.check_adoption_world(ref, _a(ENT), _a(ENT), ["c0"], {"c0": ENT}, {"c0": REF})


def _payload(x, m, tmp_path):
    world = {k: x[k] for k in ("split", "population", "stratum", "index", "source_key", "group")}
    return {"world": world, **{k: x[k] for k in ("condition", "wording", "named", "tier", "checker_status",
                                                 "forged_status", "forgery_kind")},
            "salt": m["assign_salt"], "public_sha256": x["public_sha256"],
            "provider": {"kind": "mock", "model": "mock", "extra": {"policy": "sprint_hash"}},
            "global_cap": 10, "call_ledger": str(tmp_path / "ledger.jsonl"), "phase": "SPRINT"}


def test_mock_episodes_both_tiers(tmp_path):
    from causalguard.sprint.episode import sprint_world
    m = json.loads((P.REPO / "artifacts/sprint_pilot4_manifest.json").read_text())
    picks = [next(x for x in m["items"] if x["tier"] == "W" and x["condition"] == c) for c in ("P3", "P4")]
    picks.append(next(x for x in m["items"] if x["tier"] == "H"))
    for x in picks:
        rec = sprint_world(_payload(x, m, tmp_path))
        assert rec["status"] == "ok" and rec["tier"] == x["tier"]
        assert rec["public_sha256"] == x["public_sha256"]
        w = S.score_world(rec)
        assert w["tier"] == x["tier"] and w["C"]["counts"]["n"] + w["C"]["counts"].get("missing_t2", 0) == \
            len(x["named"])
        for c in x["named"]:
            assert rec["reference"][c]["status"] == x["checker_status"][c] != x["forged_status"][c]


def test_half_panel_is_first_half_within_tier_and_condition(tmp_path):
    from collections import Counter

    from causalguard.__main__ import _items_from_config as _items
    cfg = {"study": "SPRINT", "manifest": "artifacts/sprint_main_manifest.json", "half_panel": True,
           "provider": {"kind": "mock", "model": "mock"}, "global_cap": 1, "call_ledger": "x"}
    got = [p for _, p in _items(cfg)]
    c = Counter((p["tier"], p["condition"]) for p in got)
    assert all(c[("W", q)] == 12 for q in P.CONDITIONS_R7B) and all(c[("H", q)] == 6 for q in P.CONDITIONS_R7B)


def test_empty_reply_is_a_transport_failure_and_fails_the_world(tmp_path, monkeypatch):
    """D85: a 200 response with no content and no finish_reason (server under memory pressure) is retried, then the
    world item raises so the runner records 'error'; it is never scored as a model answer."""
    from causalguard.llm import providers as PR
    from causalguard.sprint import episode as E
    calls = []

    def empty(self, msgs, temperature, seed):
        calls.append(1)
        return {"content": "", "finish_reason": None, "prompt_tokens": None, "completion_tokens": None}
    monkeypatch.setattr(PR.OpenAICompatibleProvider, "_send", empty)
    prov = PR.make_provider({"kind": "openai_compatible", "backend": "lmstudio", "base_url": "http://127.0.0.1:9/v1",
                             "model": "x", "max_tokens": 10, "max_transport_retries": 1})
    res = prov.chat([{"role": "user", "content": "hi"}], 0.0, 0)
    assert not res["ok"] and "empty response" in res["failure"] and len(calls) == 2
    m = json.loads((P.REPO / "artifacts/sprint_pilot4_manifest.json").read_text())
    p = _payload(m["items"][0], m, tmp_path)
    p["provider"] = {"kind": "openai_compatible", "backend": "lmstudio", "base_url": "http://127.0.0.1:9/v1",
                     "model": "x", "max_tokens": 10, "max_transport_retries": 0}
    with pytest.raises(E.ProviderFailure):
        E.sprint_world(p)
