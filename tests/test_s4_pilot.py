"""S4 pilot harness end to end with a scripted mock model: runner records, call caps, gates, scoring,
pre-release replay metrics, baselines and sizing.  No real model is called."""
import json
from pathlib import Path

from causalguard.analysis.s4_analysis import analyze_pilot, fit_surface_baselines, sizing
from causalguard.runner import Run, make_plan
from causalguard.s4.pilot import parse_answers, parse_json, pilot_world


def _cfg(tmp):
    return {"salt": "t-s4-pilot", "provider": {"kind": "mock", "model": "mock-model", "extra": {"policy": "s4_tool_copier"}},
            "global_cap": 200, "world_cap": 25, "call_ledger": str(tmp / "ledger.jsonl")}


def test_parsers():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json("text {\"a\": 2} tail") == {"a": 2}
    assert parse_json("no json") is None
    got = parse_answers([{"cid": "c0", "verdict": "entailed", "forecast": "1"}, {"cid": "c0", "verdict": "refuted",
                                                                               "forecast": 0},
                         {"cid": "c9", "verdict": "entailed", "forecast": 1}, {"cid": "c1", "verdict": "maybe"}],
                        ["c0", "c1"])
    assert got == {"c0": {"verdict": "entailed", "forecast": 1}}


def test_pilot_end_to_end_with_mock(tmp_path):
    c = _cfg(tmp_path)
    items = [(f"{f}|{i}", {**c, "index": i, "family": f}) for f in ("parity", "repeated_modules") for i in range(2)]
    plan = make_plan("p", "S4-PILOT", {"provider": c["provider"], "salt": c["salt"]}, items,
                     strata_fn=lambda p: {"family": p["family"]})
    end = Run("p", plan, runs_root=tmp_path).execute(pilot_world, workers=1, timeout_s=600)
    assert end["status"] == "complete"
    rec = json.loads(next((tmp_path / "p" / "attempts").rglob("*.json")).read_text())["output"]
    assert set(rec["episodes"]) == {"A", "B", "C", "D"} and "reference" in rec      # stored with sorted keys
    for arm in "BCD":
        ep = rec["episodes"][arm]
        assert ep["status"] == "committed" and ep["turns"] == 2
        assert all(ep["final"][cid]["verdict"] == rec["reference"][cid]["verdict"] for cid in rec["reference"])
    assert len(Path(c["call_ledger"]).read_text().splitlines()) == 4 * 7      # 1 + 3 x 2 calls per world
    bl = fit_surface_baselines(tmp_path / "bl.json", salt="t-s4-train", per_family=1)
    rep = analyze_pilot([tmp_path / "p"], tmp_path / "bl.json", tmp_path / "out", reps=200)
    m = rep["models"]["mock-model"]
    assert m["gates"]["semantic_mismatches"] == 0
    assert all(m["gates"][a]["parsable_verdict_rate"] == 1.0 for a in "ABCD")
    am = m["arm_means"]
    assert am["B"]["verdict_acc"] == am["C"]["verdict_acc"] == am["D"]["verdict_acc"] == am["controller"]["verdict_acc"] == 1.0
    assert am["A"]["verdict_acc"] == am["always_underdetermined"]["verdict_acc"]
    assert m["contrasts_verdict_acc"]["D-B"]["estimate"] == 0.0
    prev = m["prevention_common_batch"]["D"]
    assert prev["wrong_verified"] == 0 and prev["wrong_blocked"] == prev["wrong_proposed"] and prev["correct_blocked"] == 0
    assert all(r["D"]["wrong_released_verified"] == 0 for r in m["per_world"])
    sz = sizing(rep)
    assert sz["mock-model"]["D-B"]["simulation"] is None                     # an exact-tool tie is not sizable
    assert bl["sha256"]


def test_global_cap_is_enforced(tmp_path):
    c = _cfg(tmp_path)
    c["global_cap"] = 3
    out = pilot_world({**c, "index": 0, "family": "parity"})
    statuses = {a: e["status"] for a, e in out["episodes"].items()}
    assert statuses["A"] == "answered" and any(s.startswith("error:CapExceeded") for s in statuses.values())
    assert len(Path(c["call_ledger"]).read_text().splitlines()) == 3


def test_multiple_commit_calls_in_one_turn_are_merged(tmp_path):
    """D52: a model may split its final answers across several commit calls in one turn."""
    from causalguard.llm.harness import CallBudget
    from causalguard.llm.providers import MockProvider
    from causalguard.s4.evaluator import Evaluator
    from causalguard.s4.pilot import run_episode
    ev = Evaluator("t-s4-merge", 0, "parity")
    pub = ev.public()
    refs = {r.cid: r.verdict for r in ev.reference(crosscheck_sat=False)}
    split = json.dumps({"tool_calls": [{"tool": "commit", "answers": [{"cid": c, "verdict": v, "forecast": 0}]}
                                       for c, v in refs.items()]})
    ep = run_episode("D", pub, MockProvider(script=[split]), CallBudget(5, None), 0, "w")
    assert ep["status"] == "committed" and {c: a["verdict"] for c, a in ep["final"].items()} == refs
    assert sum(ep["released_verified"].values()) == 8
    from causalguard.analysis.s4_analysis import merged_commit_answers
    old = dict(ep, final={"c7": ep["final"]["c7"]})                  # what the v1 harness recorded
    assert merged_commit_answers(old, sorted(refs)) == ep["final"]
