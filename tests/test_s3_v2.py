"""S3 task v2 + harness v2: exogenous design, balance bookkeeping, transformations, information flow."""
import json
from dataclasses import replace

from causalguard.llm.harness import V2_ARMS, WorldHarnessV2, contains_label
from causalguard.llm.providers import make_provider
from causalguard.s3_tasks import COMPLEMENT_VERDICT, make_s3_items_v2, render_item_prompt_v2, sample_feedback
from causalguard.schema import Network, Rule


def test_public_payload_has_no_oracle_fields():
    d = make_s3_items_v2("t", 3)
    pub = json.dumps(d["public"])
    for key in ('"verdict"', '"hidden_answer"', '"witnesses"', '"network"', '"target_verdict"'):
        assert key not in pub
    for i in range(len(d["public"]["items"])):
        assert "reference solver" not in render_item_prompt_v2(d["public"], i)


def test_roles_and_transformation_invariants():
    for idx in range(6):
        d = make_s3_items_v2("t", idx)
        items = d["private"]["items"]
        roles = [it["role"] for it in items]
        assert roles[:5] == ["balanced"] * 3 + ["natural", "transfer_target"]
        for it in items:
            if it["role"].startswith("complement_of"):
                base = items[int(it["role"].split(":")[1])]
                assert it["verdict"] == COMPLEMENT_VERDICT[base["verdict"]]
            if it["role"].startswith("renamed_of"):
                assert it["verdict"] == items[int(it["role"].split(":")[1])]["verdict"]
        bal = [it for it in items if it["role"] == "balanced"]
        assert sorted(it["target_verdict"] for it in bal) == ["entailed", "refuted", "underdetermined"]
        for it in bal:
            assert it["balance_shortfall"] == (it["verdict"] != it["target_verdict"])


def test_design_is_exogenous_to_mechanism(monkeypatch):
    """Swapping the hidden mechanism leaves observation states, queries and the renaming identical."""
    import causalguard.s3_tasks as st
    a = make_s3_items_v2("t", 7)
    orig = st.make_s3_world

    def swapped(salt, index, n=4, kmax=2):
        w = orig(salt, index, n=n, kmax=kmax)
        return replace(w, net=Network(n, tuple(Rule((), 0) for _ in range(n))))
    monkeypatch.setattr(st, "make_s3_world", swapped)
    b = make_s3_items_v2("t", 7)
    sa = [o["state"] for o in a["private"]["evidence"]["observations"]]
    sb = [o["state"] for o in b["private"]["evidence"]["observations"]]
    assert sa == sb and a["private"]["renaming_permutation"] == b["private"]["renaming_permutation"]


def test_d_sample_uses_public_mechanisms_only_and_reveals_no_label():
    d = make_s3_items_v2("t", 2)
    pub = d["public"]
    assert len(pub["d_sample_mechanisms"]) == 2
    for i, it in enumerate(pub["items"]):
        if it["renamed"]:
            continue
        text, prov = sample_feedback(pub, i)
        assert not contains_label(text) and prov["source"] == "uniform_compatible_sample"
    # identical across a world's items (common sample) and determined by public evidence + its own seed
    d2 = make_s3_items_v2("t", 2)
    assert d2["public"]["d_sample_mechanisms"] == pub["d_sample_mechanisms"]


def test_harness_v2_turn_matching_with_mock():
    d = make_s3_items_v2("t", 1)
    prov = make_provider({"kind": "mock", "model": "mock", "temperature": 0.0, "sample_temperature": 0.7,
                          "max_tokens": 50, "seed": 1})
    res = WorldHarnessV2(prov, d["public"], d["private"], {"arms": list(V2_ARMS)}).run()
    assert res["world_status"] == "complete"
    for arm in ("B2", "D_cert", "D_label", "D_sample"):
        for i, v in res["arms"][arm].items():
            assert len(v["calls"]) == 2 and v["logical"][0] == f"i{i}/A"
            assert v["rounds"][1]["feedback_provenance"]["source"] == "self_critique"
    assert set(res["arms"]["T_cert"]) == {"4"} and len(res["calls"]) == 55
    # the certificate/label arms are the only ones whose prompts contain the verdict label
    for cid, c in res["calls"].items():
        user = c["messages"][-1]["content"]
        if "/DS" in cid or "/B2" in cid:
            assert "reference solver" not in user
