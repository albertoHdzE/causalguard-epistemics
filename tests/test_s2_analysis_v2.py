"""R05: the v2 analysis is bound to its endpoint spec and plan; duplicates and failures are never silent."""
import json
from pathlib import Path

import pytest

from causalguard.analysis.s2_analysis import AnalysisRefused, analyze_v2
from causalguard.experiments.s2 import run_world_v2
from causalguard.runner import Run, make_plan

ROOT = Path(__file__).resolve().parents[1]
EP = ROOT / "configs/endpoints/S2-primary-v2.json"
FAMS = ["conjunctive", "canalizing", "parity", "random_lookup", "modular"]


def _run(root, run_id, start=0, per=1, fail_one=False, null=0):
    items = []
    for f in FAMS:
        for i in range(start, start + per):
            items.append((f"realizable|{f}|{i}", {"salt": "t-an", "index": i, "family": f, "population": "realizable",
                                                  "label": "realizable", "design_version": "s2-design-v2",
                                                  "budgets": [4, 16], "regimes": ["uniform_states"]}))
    for i in range(null):
        items.append((f"null|uniform_H|{i}", {"salt": "t-an", "index": i, "family": "uniform_H", "population": "null",
                                              "label": "null", "design_version": "s2-design-v2", "budgets": [4, 16],
                                              "regimes": ["uniform_states"]}))
    if fail_one:   # an item whose payload makes the worker raise (unknown design version)
        items[0] = (items[0][0], {**items[0][1], "design_version": "BROKEN"})
    strata = lambda p: {k: p[k] for k in ("family", "population", "label", "index")}  # noqa: E731
    ep = EP.read_bytes()
    import hashlib
    plan = make_plan(run_id, "S2", {"t": run_id}, items, strata_fn=strata,
                     extra={"endpoint": {"path": str(EP), "sha256": hashlib.sha256(ep).hexdigest()}})
    r = Run(run_id, plan, runs_root=root)
    r.execute(run_world_v2, workers=2, timeout_s=120)
    return r.dir


def test_complete_run_and_refusals(tmp_path):
    d = _run(tmp_path, "a", per=2, null=3)
    res = analyze_v2([d], tmp_path / "out", EP, reps_primary=200, reps_secondary=100)
    assert res["accounting"]["complete"] and res["primary"]["n_worlds"] == 10
    with pytest.raises(AnalysisRefused):
        analyze_v2([d, d], tmp_path / "o2", EP)                      # duplicate run arguments
    d2 = _run(tmp_path, "b", per=1)                                    # same worlds again in another run
    with pytest.raises(AnalysisRefused):
        analyze_v2([d, d2], tmp_path / "o3", EP)
    bad = tmp_path / "ep.json"
    bad.write_text(json.dumps({**json.loads(EP.read_text()), "method_b": "uniform"}))
    with pytest.raises(AnalysisRefused):
        analyze_v2([d], tmp_path / "o4", bad)                         # endpoint differs from executable spec
    other = tmp_path / "ep2.json"
    other.write_text(EP.read_text() + "\n")                            # same keys, different bytes -> plan mismatch
    with pytest.raises(AnalysisRefused):
        analyze_v2([d], tmp_path / "o5", other)


def test_failed_world_makes_primary_incomplete_with_bounds(tmp_path):
    d = _run(tmp_path, "f", per=2, fail_one=True)
    res = analyze_v2([d], tmp_path / "out", EP, reps_primary=200, reps_secondary=100)
    acc = res["accounting"]
    assert not acc["complete"] and len(acc["unresolved_worlds"]) == 1
    p = res["primary"]
    assert p["status"].startswith("INCOMPLETE") and p["n_worlds"] == 9
    assert p["missing_outcome_bounds"]["worst"] < p["estimate"] < p["missing_outcome_bounds"]["best"]
    s = json.loads(Path(res["summary"]).read_text())
    assert s["runs"]["f"]["failed"] == 1 and s["runs"]["f"]["failures"]
