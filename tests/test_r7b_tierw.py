"""R7b Tier W: exact reference (two implementations + SAT), cross-tier test, derivations, verifier and forgeries."""
from __future__ import annotations

import json

import pytest

from causalguard.schema import Evidence, Intervention, Observation, Pred, Query
from causalguard.sprint import population as P
from causalguard.sprint import tasks as T
from causalguard.sprint import tierw as TW

N = 8


def _hand_pub() -> dict:
    """Worked on paper.  Wiring: A0 <- A1, A1 <- A0, the other six nodes constant (no inputs).
    One evidence row: from 00000000 -> 10000000, so entry A0(A1=0) = 1, A1(A0=0) = 0, every constant = 0.
    Free entries: A0(A1=1) and A1(A0=1); F = 2, |V_W| = 4.
      c0: set A1=1, one step, A0 = 1   -> needs A0(A1=1): unobserved -> NOT SETTLED, 2 of 4.
      c1: set A1=1, two steps, A0 = 1  -> step 1: A1 reads A0=0 -> 0 (row 1); step 2: A0 reads A1=0 -> 1 (row 1);
                                          settled TRUE, 4 of 4 (A0's step-1 value is never needed).
      c2: set A1=1, two steps, A1 = 1  -> step 1: A0 reads A1=1: free (case split);
                                          if A0 -> 0: step 2: A1 reads A0=0 -> 0 (row 1)  => fails
                                          if A0 -> 1: step 2: A1 reads A0=1: free => holds in 1 of 2
                                          num = 1 of 4: NOT SETTLED.
      c3: hold A1=0, one step, A0 = 0  -> A0 reads A1=0 -> 1 (row 1): settled FALSE."""
    ev = Evidence(N, (Observation(0, Intervention("none"), 1, tuple((j, 1 if j == 0 else 0) for j in range(N))),))
    edit = Intervention("initial_edit", ((1, 1),))
    claims = [Query.point(0, N, edit, 1, Pred.lit(0, 1)), Query.point(0, N, edit, 2, Pred.lit(0, 1)),
              Query.point(0, N, edit, 2, Pred.lit(1, 1)),
              Query.point(0, N, Intervention("persistent_clamp", ((1, 0),)), 1, Pred.lit(0, 0))]
    return {"task_id": "hand", "n": N, "k": 3, "node_labels": [f"A{i}" for i in range(N)],
            "evidence": ev.to_json(), "claims": [{"cid": f"c{i}", "query": q.to_json()} for i, q in enumerate(claims)],
            "wiring": [[1], [0], [], [], [], [], [], []], "tier": "W"}


def test_hand_worked_counts_and_both_engines():
    pub = _hand_pub()
    ref = TW.reference_w(pub, sat=True)
    got = {c: (r["status"], int(r["num"]), int(r["den"])) for c, r in ref.items()}
    assert got == {"c0": (TW.UND, 2, 4), "c1": (TW.ENT, 4, 4), "c2": (TW.UND, 1, 4), "c3": (TW.REF, 0, 4)}


def test_planted_engine_disagreement_fails(monkeypatch):
    pub = _hand_pub()
    real = TW.lazy_counts
    monkeypatch.setattr(TW, "lazy_counts", lambda t, q, e=None: (real(t, q, e)[0] + 1, real(t, q, e)[1]))
    with pytest.raises(AssertionError, match="Tier W mismatch"):
        TW.reference_w(pub, sat=False)


def test_hand_derivation_and_verifier():
    pub = _hand_pub()
    pk = TW.claim_package(pub, "c1", "salt")
    assert pk["lines"] == ["c1: settled TRUE.",
                           "  step 1: A1 reads A0=0; row #01 shows A1 -> 0.",
                           "  step 2: A0 reads A1=0; row #01 shows A0 -> 1.",
                           "  => A0 = 1 after 2 step(s)."]
    assert TW.verify(pub, "c1", pk["tree"], pk["status"], pk["lines"]) == []
    pk2 = TW.claim_package(pub, "c2", "salt")
    assert TW.verify(pub, "c2", pk2["tree"], pk2["status"], pk2["lines"]) == []
    assert any("no evidence row shows" in ln for ln in pk2["lines"])
    # tampering: wrong stated status, edited text
    assert TW.verify(pub, "c1", pk["tree"], TW.REF, TW.render(pk["tree"], Query.from_json(pub["claims"][1]["query"]),
                                                               pub, "c1", TW.REF))
    bad = list(pk["lines"])
    bad[1] = bad[1].replace("row #01", "row #02")
    assert TW.verify(pub, "c1", pk["tree"], pk["status"], bad)


@pytest.mark.parametrize("kind", TW.FORGERY_KINDS)
def test_every_forgery_kind_fails_the_verifier(kind):
    """On pilot-4 Tier W worlds, every available alteration of every kind changes the status and fails."""
    seen = 0
    for k in P.world_keys("pilot4")[:8]:
        ev, pub = P.tier_public(k, "W")
        tab = TW.Table.from_public(pub)
        for c in pub["claims"]:
            q = Query.from_json(c["query"])
            st = TW.tree_status(TW.derive(tab, q), q.target.value)
            for cand in TW.forgery_candidates(tab, q, st):
                if cand["kind"] != kind:
                    continue
                lines, tree, fst = TW.derivation_lines(tab, q, pub, c["cid"], cand["entries"])
                assert fst != st
                assert TW.verify(pub, c["cid"], tree, fst, lines), (k.wkey, c["cid"], kind)
                seen += 1
    assert seen > 0


def test_cross_tier_settled_on_h_is_settled_on_w():
    """On the Tier H evidence (larger budgets, so Tier H settles claims), with the hidden wiring listed."""
    checked = 0
    for k in P.world_keys("pilot4")[:6]:
        ev = P.evaluator(k)
        pub = {**ev.public(), "wiring": TW.wiring_of(ev.world.net), "tier": "W"}
        ref_w = TW.reference_w(pub, ev.world.net, sat=False)
        ref_h = P.reference(ev, crosscheck_sat=False)
        assert TW.cross_tier(ref_h, ref_w) == []
        checked += sum(r["status"] != TW.UND for r in ref_h.values())
        # the hidden truth is a Tier W mechanism: settled W statuses agree with it
        for r in ref_w.values():
            if r["status"] != TW.UND:
                assert r["truth"] == (r["status"] == TW.ENT)
    assert checked > 0


def test_planted_cross_tier_violation_is_caught():
    ref_h = {"c0": {"status": TW.ENT}, "c1": {"status": TW.UND}}
    ref_w = {"c0": {"status": TW.REF}, "c1": {"status": TW.ENT}}
    assert TW.cross_tier(ref_h, ref_w) == ["c0"]


def test_tier_w_rendering_lists_wiring_and_tier_h_is_unchanged():
    k = P.world_keys("pilot4")[0]
    ev, pub = P.tier_public(k, "W")
    txt = T.user_prompt(pub)
    assert "Inputs of each node" in txt and "its listed input nodes" in txt
    evh, pubh = P.tier_public(k, "H")
    txth = T.user_prompt(pubh)
    assert "Inputs of each node" not in txth and "at most 3 nodes (any nodes, possibly itself)" in txth


def test_p3_p4_same_template_and_similar_length():
    m = json.loads((P.REPO / "artifacts/sprint_pilot4_manifest.json").read_text())
    ratios = []
    for x in m["items"][:12]:
        ev, pub = P.tier_public(P.WorldKey.from_json(x), x["tier"])
        a = T.followup(pub, "P3", 1, x["named"], m["assign_salt"])
        b = T.followup(pub, "P4", 1, x["named"], m["assign_salt"])
        assert a != b
        tmpl = T.templates(x["tier"])[("P3", 1)]
        assert a.startswith(tmpl.split("{checker}")[0]) and b.startswith(tmpl.split("{checker}")[0])
        ratios.append(len(b) / len(a))
    assert 0.5 < sum(ratios) / len(ratios) < 1.5


def test_r7b_assignment_balanced_and_depends_on_keys_and_eligibility_only():
    import inspect
    assert list(inspect.signature(P.assign_r7b).parameters) == ["keys", "tiers", "eligible", "conditions", "fixed"]
    m = json.loads((P.REPO / "artifacts/sprint_main_manifest.json").read_text())
    from collections import Counter
    c = Counter((x["tier"], x["condition"]) for x in m["items"])
    assert all(c[("W", p)] == 24 for p in P.CONDITIONS_R7B) and all(c[("H", p)] == 12 for p in P.CONDITIONS_R7B)
    assert m["tier_counts"] == {"W": 120, "H": 60}
    assert Counter(x["population"] for x in m["items"] if x["tier"] == "W")["published"] == 16
    assert Counter(x["population"] for x in m["items"] if x["tier"] == "H")["published"] == 12
    keys = P.world_keys("pilot4")
    tiers = P.split_tiers(keys, P.PILOT4_TIER_COUNTS)
    el = {k.wkey: [f"c{i}" for i in range(8)] for k in keys}
    assert P.assign_r7b(keys, tiers, el) == P.assign_r7b(list(reversed(keys)), tiers, el)


def test_main_tiers_disjoint_from_r7_shown_worlds_and_pilot4():
    main = json.loads((P.REPO / "artifacts/sprint_main_manifest.json").read_text())
    shown = set()
    for s in ("smoke", "pilot", "pilot2", "pilot3", "pilot4"):
        shown |= {x["mechanism_sha256"] for x in json.loads((P.REPO / f"artifacts/sprint_{s}_manifest.json")
                                                             .read_text())["items"]}
    assert not shown & {x["mechanism_sha256"] for x in main["items"]}
