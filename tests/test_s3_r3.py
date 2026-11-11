"""Iteration 3, section C (R2-07..R2-09): design-known shortcut, aggregate coherence, semantic novelty.  Offline."""
from causalguard.analysis.s3_analysis import baseline_predict, coherence_audit, design_known_target_rule, semantic_claim, target_novelty_audit
from causalguard.llm.harness import aggregate_c
from causalguard.llm.parse import argmax_tied, parse_answer, verdict_vector_coherent
from causalguard.s3_tasks import S3_BUDGETS, VERDICT_LABELS, make_s3_items_v2
from causalguard.schema import Intervention, Pred, Query


def _m(verdict, probs):
    return {"status": "ok", "verdict": verdict, "verdict_valid": verdict is not None,
            "probabilities": probs, "probs_valid": probs is not None, "flags": []}


def test_design_known_rule_is_the_generator_coupling():
    rule = design_known_target_rule()
    assert rule == {"3": "entailed", "5": "refuted", "8": "underdetermined"}
    for i in range(12):
        d = make_s3_items_v2("t-r3-rule", i)
        tgt = next(it for it in d["private"]["items"] if it["role"] == "transfer_target")
        assert d["private"]["budget"] == S3_BUDGETS[i % 3] and tgt["target_verdict"] == rule[str(d["private"]["budget"])]
    assert baseline_predict("design_known_budget_rule", {"majority_verdict": "x", "design_known_budget_rule": rule},
                            {"role": "transfer_target", "query": {}}, 5) == "refuted"


def test_mean_vector_can_disagree_with_majority_verdict():
    e = {"entailed": 0.9, "refuted": 0.05, "underdetermined": 0.05}
    u_low = {"entailed": 0.45, "refuted": 0.1, "underdetermined": 0.45}
    members = [_m("underdetermined", u_low), _m("underdetermined", u_low), _m("entailed", e)]
    agg = aggregate_c(members)
    assert agg["verdict"] == "underdetermined"
    mean = agg["probabilities"]
    assert mean["entailed"] > mean["underdetermined"]          # 0.6 vs 0.3167
    assert "aggregate_verdict_prob_mismatch" in agg["flags"] and "verdict_prob_mismatch" not in agg["flags"]
    # members themselves were coherent (ties at the maximum count as coherent)
    assert all(verdict_vector_coherent(m["verdict"], m["probabilities"]) for m in members)


def test_probability_ties_are_coherent_and_counted():
    tied = {"entailed": 0.5, "refuted": 0.5, "underdetermined": 0.0}
    assert verdict_vector_coherent("entailed", tied) and verdict_vector_coherent("refuted", tied)
    assert not verdict_vector_coherent("underdetermined", tied) and argmax_tied(tied)
    agg = aggregate_c([_m("entailed", tied), _m("entailed", tied), _m("refuted", tied)])
    assert agg["verdict"] == "entailed" and "aggregate_verdict_prob_mismatch" not in agg["flags"]
    p = parse_answer('{"verdict": "underdetermined", "probabilities": {"entailed": 0.5, "refuted": 0.5, '
                     '"underdetermined": 0}, "reason": "r"}')
    assert "verdict_prob_mismatch" in p["flags"]


def test_coherence_audit_recomputes_c_after_aggregation():
    u = {"entailed": 0.6, "refuted": 0.1, "underdetermined": 0.3}
    final_c = {**_m("underdetermined", u), "flags": []}             # historical record: no aggregate flag saved
    final_a = {**_m("underdetermined", u), "flags": ["verdict_prob_mismatch"]}
    rec = {"task_private": {"items": [{"role": "balanced"}]},
           "arms": {"C": {"0": {"final": final_c}}, "A": {"0": {"final": final_a}}}}
    out = coherence_audit([rec])["by_arm"]
    assert out["C|balanced"]["mismatch"] == 1 and out["C|balanced"]["saved_flag_mismatch"] == 0
    assert out["C|balanced"]["kind"].startswith("aggregate") and out["A|balanced"]["kind"] == "direct_model_response"


def _point(state, n, iv, h, node, value=1):
    return Query.point(state, n, iv, h, Pred.lit(node, value)).to_json()


def test_semantic_novelty_normalizes_noop_initial_edits_and_labels_complements():
    n = 4
    src = {"role": "balanced", "query": _point(0b1110, n, Intervention(), 2, 0)}
    noop = {"role": "transfer_target", "query": _point(0b1110, n, Intervention("initial_edit", ((1, 1),)), 2, 0)}
    assert semantic_claim(src) == semantic_claim(noop)
    comp = {"role": "transfer_target", "query": _point(0b1110, n, Intervention(), 2, 0, value=0)}
    fresh = {"role": "transfer_target", "query": _point(0b1100, n, Intervention(), 2, 0)}
    recs = [{"world_index": k, "task_private": {"items": [src, {"role": "x", "query": src["query"]}, t]}}
            for k, t in enumerate((noop, comp, fresh))]
    out = target_novelty_audit(recs, 0)
    assert out["identical_claim_worlds"] == [0] and out["complement_claim_worlds"] == [1] and out["fresh_worlds"] == 1
    assert VERDICT_LABELS  # labels imported for the rule above
