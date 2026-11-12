"""R6 Track A2: the gate in the loop (mock provider; no model calls)."""
from causalguard.llm.harness import CallBudget
from causalguard.llm.providers import MockProvider
from causalguard.r5 import investigation as I


def _script(replies):
    it = iter(replies)
    return lambda m, t, s: next(it)


def test_rejected_definite_stop_is_returned_and_episode_continues():
    w = I.world("calibration", "uniform_H", 0)                    # target initially underdetermined
    prompts = []

    def script(msgs, t, s):
        prompts.append(msgs[-1]["content"])
        if len(prompts) == 1:
            return '{"verdict": "entailed", "p_target": 1, "measure": null}'     # unsupported stop
        return '{"verdict": "underdetermined", "p_target": 0.5, "measure": null}'
    e = I.ai_episode(w, "D", MockProvider(script=script), CallBudget(8, None), gate_loop=True)
    assert e["gate_loop"] and len(e["rejections"]) == 1
    r = e["rejections"][0]
    assert r["check"] == "refuted" and r["target_status"] == "underdetermined" and r["turn"] == 0
    assert prompts[1].startswith("Checked and rejected: the evidence does not determine the target; 4 purchase")
    assert e["per_turn"]["0"]["verdict"] == "underdetermined" and e["n_attempts"] == 2 and e["status"] == "stopped"


def test_without_loop_the_same_stop_ends_the_episode():
    w = I.world("calibration", "uniform_H", 0)
    e = I.ai_episode(w, "D", MockProvider(script=lambda m, t, s: '{"verdict": "entailed", "measure": null}'),
                     CallBudget(8, None))
    assert "rejections" not in e and e["n_attempts"] == 1 and e["per_turn"]["4"]["verdict"] == "entailed"
    assert e["gate"]["4"]["check"] == "refuted"                   # counterexample to the definite assertion


def test_loop_never_rejects_underdetermined_and_respects_the_attempt_cap():
    w = I.world("calibration", "uniform_H", 0)
    e = I.ai_episode(w, "D", MockProvider(script=lambda m, t, s: '{"verdict": "underdetermined", "measure": null}'),
                     CallBudget(8, None), gate_loop=True)
    assert e["rejections"] == [] and e["n_attempts"] == 1
    e = I.ai_episode(w, "D", MockProvider(script=lambda m, t, s: '{"verdict": "refuted", "measure": null}'),
                     CallBudget(8, None), gate_loop=True)
    assert e["n_attempts"] == I.MAX_CALLS and len(e["rejections"]) == I.MAX_CALLS - 1
    assert e["status"] == "stopped" and e["per_turn"]["0"]["verdict"] == "refuted"   # last attempt accepted as R5 stop
