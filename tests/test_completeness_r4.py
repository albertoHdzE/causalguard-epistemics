"""R3-01: planned method keys come from the fixed study contract; missing outputs refuse (never shrink a
denominator or silently score wrong); state-dependent null semantics; noise cells carry their own methods."""
import copy

import pytest

from causalguard.analysis.s2_analysis import (V2_CODECS, AnalysisRefused, OutputDefect, _check_row_values, _contrast,
                                              required_pred_keys, validate_world_v2, world_scores)
from causalguard.experiments.s2 import V2_SELECTORS, run_world_v2

from test_completeness_r3 import _analyze, _b16_rows, _copy, _edit, s2_store  # noqa: F401  (module fixture reuse)

ITEM = "realizable|parity|1"


def _iv(o):
    return [q for q in _b16_rows(o) if q["kind"] == "intervention"]


def test_contract_is_the_experiment_selector_set():
    assert V2_CODECS == V2_SELECTORS
    assert required_pred_keys("noise") == V2_SELECTORS + tuple(f"mdl_two_part_{c}" for c in V2_SELECTORS)
    with pytest.raises(ValueError):
        required_pred_keys("other")


@pytest.mark.parametrize("where", ["first", "middle", "last"])
@pytest.mark.parametrize("method", ["index", "circuit"])
def test_missing_prediction_key_is_refused_at_any_row(s2_store, tmp_path, where, method):
    d = _copy(s2_store, tmp_path)

    def mut(o):
        rows = _iv(o)
        q = {"first": rows[0], "middle": rows[len(rows) // 2], "last": rows[-1]}[where]
        q["pred"].pop(method)
    _edit(d, ITEM, mut)
    with pytest.raises(OutputDefect, match="study contract"):
        _analyze(d, tmp_path)


def test_null_prediction_in_nonempty_space_is_refused(s2_store, tmp_path):
    d = _copy(s2_store, tmp_path)

    def mut(o):
        rows = _iv(o)
        assert not o["regimes"]["uniform_states"]["16"]["empty"]
        rows[5]["pred"]["index"] = None
    _edit(d, ITEM, mut)
    with pytest.raises(OutputDefect, match="nonempty version space"):
        _analyze(d, tmp_path)


def test_extra_prediction_key_is_refused(s2_store, tmp_path):
    d = _copy(s2_store, tmp_path)
    _edit(d, ITEM, lambda o: _iv(o)[3]["pred"].update(mdl_two_part_index=1))
    with pytest.raises(OutputDefect, match="extra"):
        _analyze(d, tmp_path)


def test_unmutated_store_keeps_full_denominator(s2_store, tmp_path):
    res = _analyze(s2_store, tmp_path)
    assert res["primary"]["n_worlds"] == 10


def _empty_row(**over):
    r = {"kind": "intervention", "truth": 1, "observed_majority": 0, "pred": {c: None for c in V2_CODECS},
         "p": None, "num": None, "den": None, "vs_majority": None, "tie": None,
         "verdict": "inconsistent_evidence_or_class"}
    r.update(over)
    return r


def test_empty_space_semantics():
    _check_row_values(_empty_row(), True, "t")
    with pytest.raises(OutputDefect, match="empty version space"):
        _check_row_values(_empty_row(pred={**{c: None for c in V2_CODECS}, "index": 1}), True, "t")
    # missing key is refused in the empty state too (an explicit null is distinct from an absent output)
    with pytest.raises(OutputDefect, match="study contract"):
        _check_row_values(_empty_row(pred={c: None for c in V2_CODECS[1:]}), True, "t")
    # empty rows are scored wrong for every selector, with the planned denominator
    sc = world_scores([_empty_row()] * 4)
    assert sc["n_queries"] == 4 and all(sc[c] == 0.0 for c in V2_CODECS)


def test_empty_space_noise_cell_requires_mdl_predictions():
    noise_pred = {**{c: None for c in V2_CODECS}, **{f"mdl_two_part_{c}": 0 for c in V2_CODECS}}
    _check_row_values(_empty_row(pred=noise_pred), True, "t", "noise")
    with pytest.raises(OutputDefect, match="noise-cell"):
        _check_row_values(_empty_row(pred={**noise_pred, "mdl_two_part_bdd": None}), True, "t", "noise")
    with pytest.raises(OutputDefect, match="study contract"):
        _check_row_values(_empty_row(pred=noise_pred), True, "t", "ordinary")


@pytest.fixture(scope="module")
def noise_world():
    p = {"salt": "t-r4", "design_version": "s2-design-v2", "budgets": [16], "regimes": ["uniform_states"],
         "index": 0, "family": "canalizing", "population": "realizable", "label": "realizable",
         "noise_rates": [0.05], "noise_budgets": [16]}
    return p, run_world_v2(p)


def test_noise_cell_reconciles_and_missing_mdl_key_refuses(noise_world):
    p, out = noise_world
    v = validate_world_v2("w", p, out)
    assert all(c == "complete" for c in v["cells"].values()) and ("noise0.05", "16") in v["cells"]
    for pos in (0, 11, -1):
        o = copy.deepcopy(out)
        o["noise"]["0.05"]["budgets"]["16"]["queries"][pos]["pred"].pop("mdl_two_part_dnf")
        with pytest.raises(OutputDefect, match="study contract"):
            validate_world_v2("w", p, o)


def test_world_scores_never_infers_methods_from_first_row():
    full = {"kind": "intervention", "truth": 1, "observed_majority": 1, "pred": {c: 1 for c in V2_CODECS},
            "p": 1.0, "tie": False, "vs_majority": 1}
    first_lacking = copy.deepcopy(full)
    first_lacking["pred"].pop("index")
    with pytest.raises(AnalysisRefused):
        world_scores([first_lacking, full, full])
    with pytest.raises(AnalysisRefused):
        world_scores([full, full, first_lacking])


def test_contrast_refuses_instead_of_dropping_a_world():
    rows = [{"world_id": f"w{i}", "family": "f", "n_queries": 16, "index": 0.5, "vs_majority": 0.5} for i in range(6)]
    assert _contrast(rows, "index", "vs_majority", 50)["n_worlds"] == 6
    broken = copy.deepcopy(rows)
    broken[0].pop("index")
    with pytest.raises(AnalysisRefused, match="denominator"):
        _contrast(broken, "index", "vs_majority", 50)
    # a genuinely empty query subset is excluded and REPORTED
    sub = copy.deepcopy(rows) + [{"world_id": "w9", "family": "f", "n_queries": 0}]
    c = _contrast(sub, "index", "vs_majority", 50)
    assert c["n_worlds"] == 6 and c["excluded_empty_query_subset_rows"] == 1
