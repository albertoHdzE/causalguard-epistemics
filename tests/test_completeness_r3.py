"""Iteration 3, section B (R2-05, R2-06): endpoint completeness, identity reconciliation, truthful RSS and
phase-aware reporting.  Worlds are generated once per module through the real runner into temporary storage;
each case mutates a COPY of that storage (outputs only; attempt identities stay valid)."""
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from causalguard.analysis.s1_analysis import S1OutputDefect
from causalguard.analysis.s1_analysis import analyze_v2 as s1_analyze
from causalguard.analysis.s2_analysis import AnalysisRefused, OutputDefect, analyze_v2, completeness_v2
from causalguard.experiments.s1 import run_item
from causalguard.experiments.s2 import run_world_v2
from causalguard.freeze import _strata
from causalguard.runner import Run, RunCorruption, item_key, load_run, make_plan

ROOT = Path(__file__).resolve().parents[1]
EP = ROOT / "configs/endpoints/S2-primary-v2.json"
SPEC = json.loads(EP.read_text())
FAMS = SPEC["families"]


def _s2_items(per=2, nulls=2):
    base = {"salt": "t-r3", "design_version": "s2-design-v2", "budgets": [4, 16], "regimes": ["uniform_states"]}
    items = [(f"realizable|{f}|{i}", {**base, "index": i, "family": f, "population": "realizable", "label": "realizable"})
             for f in FAMS for i in range(per)]
    items += [(f"null|uniform_H|{i}", {**base, "index": i, "family": "uniform_H", "population": "null", "label": "null"})
              for i in range(nulls)]
    return items


def _s2_plan(run_id, items, **extra):
    ep = {"path": str(EP), "sha256": hashlib.sha256(EP.read_bytes()).hexdigest()}
    return make_plan(run_id, "S2", {"t": run_id}, items, strata_fn=_strata, extra={"endpoint": ep, **extra})


@pytest.fixture(scope="module")
def s2_store(tmp_path_factory):
    root = tmp_path_factory.mktemp("s2store")
    Run("s2", _s2_plan("s2", _s2_items()), runs_root=root).execute(run_world_v2, workers=4, timeout_s=300)
    return root / "s2"


def _copy(src: Path, tmp_path: Path) -> Path:
    dst = tmp_path / src.name
    shutil.copytree(src, dst)
    return dst


def _att(run_dir: Path, item_id: str) -> Path:
    return run_dir / "attempts" / item_key(item_id) / "001.json"


def _edit(run_dir: Path, item_id: str, fn) -> None:
    f = _att(run_dir, item_id)
    rec = json.loads(f.read_text())
    fn(rec["output"])
    f.write_text(json.dumps(rec))


def _analyze(d, tmp_path, **kw):
    return analyze_v2([d] if isinstance(d, Path) else d, tmp_path / "out", EP, reps_primary=100, reps_secondary=50,
                      development_sizing=False, **kw)


def _b16_rows(out):
    return out["regimes"]["uniform_states"]["16"]["queries"]


def test_complete_store_reconciles(s2_store, tmp_path):
    res = _analyze(s2_store, tmp_path)
    c = res["completeness"]
    assert c["structured_primary"]["status"] == "complete" and c["structured_primary"]["complete"] == 10
    assert c["required_null"]["status"] == "complete" and c["overall_study"]["status"] == "complete"
    assert res["primary"]["n_worlds"] == 10 and res["primary"]["status"] == "complete (development); not confirmatory"
    s = json.loads(Path(res["summary"]).read_text())
    assert s["runs"]["s2"]["ok_outputs_with_legacy_rows(no qid)"] == 0 and s["phase"] == "development"
    assert "design_simulation_revised_primary" not in s and "development-only" in s["design_simulation_note"]


def test_absent_b16_cell_is_a_missing_outcome(s2_store, tmp_path):
    d = _copy(s2_store, tmp_path)
    _edit(d, "realizable|parity|0", lambda o: o["regimes"]["uniform_states"].pop("16"))
    res = _analyze(d, tmp_path)
    sp = res["completeness"]["structured_primary"]
    assert sp["status"] == "incomplete" and sp["ok_but_endpoint_cell_absent"] == 1 and sp["complete"] == 9
    assert res["primary"]["n_worlds"] == 9 and res["primary"]["status"].startswith("INCOMPLETE")
    b = res["primary"]["missing_outcome_bounds"]
    assert b["worst"] <= res["primary"]["estimate"] <= b["best"]
    assert res["completeness"]["overall_study"]["ok_incomplete_grid"] == 1


def test_one_of_sixteen_grid_is_short_not_averaged(s2_store, tmp_path):
    d = _copy(s2_store, tmp_path)

    def cut(o):
        qs = _b16_rows(o)
        o["regimes"]["uniform_states"]["16"]["queries"] = [q for q in qs if q["kind"] == "state"] + \
            [q for q in qs if q["kind"] == "intervention"][:1]
    _edit(d, "realizable|modular|1", cut)
    res = _analyze(d, tmp_path)
    assert res["completeness"]["structured_primary"]["ok_but_endpoint_cell_absent"] == 1
    assert res["primary"]["n_worlds"] == 9
    s = json.loads(Path(res["summary"]).read_text())
    assert s["ties"]["primary_queries"] == 9 * 16                     # never 9*16 + 1
    assert s["runs"]["s2"]["incomplete_outputs"]["realizable|modular|1"] == {"uniform_states|B16": "short"}


def test_duplicate_query_replacing_a_missing_query_is_refused(s2_store, tmp_path):
    d = _copy(s2_store, tmp_path)

    def dup(o):
        qs = _b16_rows(o)
        qs[12] = dict(qs[11])
    _edit(d, "realizable|canalizing|0", dup)
    with pytest.raises(OutputDefect, match="duplicated query identity"):
        _analyze(d, tmp_path)


def test_legacy_rows_without_qid_wrong_fingerprint_is_refused(s2_store, tmp_path):
    d = _copy(s2_store, tmp_path)

    def legacy_dup(o):
        for byb in o["regimes"].values():
            for c in byb.values():
                for q in c["queries"]:
                    q.pop("qid")
        qs = _b16_rows(o)
        j = next(j for j in range(9, 24) if (qs[j]["h"], qs[j]["iv"], qs[j]["target_node"], qs[j]["truth"])
                 != (qs[8]["h"], qs[8]["iv"], qs[8]["target_node"], qs[8]["truth"]))
        qs[j] = dict(qs[8])
    _edit(d, "realizable|conjunctive|1", legacy_dup)
    with pytest.raises(OutputDefect):
        _analyze(d, tmp_path)


@pytest.mark.parametrize("mutation", ["world_id", "qid", "horizon", "design", "unplanned_cell", "extra_row"])
def test_wrong_identity_is_refused(s2_store, tmp_path, mutation):
    d = _copy(s2_store, tmp_path)

    def mut(o):
        if mutation == "world_id":
            o["world"]["world_id"] = "S2-other"
        elif mutation == "qid":
            _b16_rows(o)[15]["qid"] = "0" * 64
        elif mutation == "horizon":
            _b16_rows(o)[15]["h"] += 1
        elif mutation == "design":
            o["design"]["design_seed"] += 1
        elif mutation == "unplanned_cell":
            o["regimes"]["uniform_states"]["32"] = o["regimes"]["uniform_states"]["16"]
        else:
            _b16_rows(o).append(dict(_b16_rows(o)[-1]))
    _edit(d, "realizable|random_lookup|0", mut)
    with pytest.raises(OutputDefect):
        _analyze(d, tmp_path)


@pytest.mark.parametrize("mutation", ["num_text", "num_gt_den", "tie", "p", "verdict", "truth"])
def test_malformed_exact_counts_are_refused(s2_store, tmp_path, mutation):
    d = _copy(s2_store, tmp_path)

    def mut(o):
        q = next(q for q in _b16_rows(o) if q["num"] is not None and 0 < int(q["num"]) < int(q["den"]))
        if mutation == "num_text":
            q["num"] = "abc"
        elif mutation == "num_gt_den":
            q["num"] = str(int(q["den"]) + 1)
        elif mutation == "tie":
            q["tie"] = not q["tie"]
        elif mutation == "p":
            q["p"] = 0.123456
        elif mutation == "verdict":
            q["verdict"] = "entailed"
        else:
            q["truth"] = 2
    _edit(d, "realizable|parity|1", mut)
    with pytest.raises(OutputDefect):
        _analyze(d, tmp_path)


def test_missing_and_failed_null_keep_study_incomplete(s2_store, tmp_path):
    d = _copy(s2_store, tmp_path)
    shutil.rmtree(_att(d, "null|uniform_H|0").parent)                            # never-returned null world
    f = _att(d, "null|uniform_H|1")                                              # failed null world
    rec = json.loads(f.read_text())
    rec.update(status="error", output={"error": "fixture"})
    f.write_text(json.dumps(rec))
    res = _analyze(d, tmp_path)
    c = res["completeness"]
    assert c["structured_primary"]["status"] == "complete" and res["primary"]["status"].startswith("complete")
    assert c["required_null"] == {**c["required_null"], "status": "incomplete", "missing_attempt": 1, "failed": 1}
    assert c["overall_study"]["status"] == "incomplete"
    assert json.loads(Path(res["summary"]).read_text())["required_null_status"] == "incomplete"


def test_missing_family_and_zero_worlds_do_not_crash_or_reweight(s2_store, tmp_path):
    d = _copy(s2_store, tmp_path)
    for i in range(2):
        shutil.rmtree(_att(d, f"realizable|parity|{i}").parent)
    res = _analyze(d, tmp_path)
    p = res["primary"]
    assert p["estimate"] is None and p["families_without_completed_worlds"] == ["parity"]
    assert p["status"].startswith("INCOMPLETE") and set(p["missing_outcome_bounds"]) == {"worst", "best"}
    for f in FAMS:
        for i in range(2):
            a = _att(d, f"realizable|{f}|{i}").parent
            if a.exists():
                shutil.rmtree(a)
    res = _analyze(d, tmp_path)
    assert res["primary"]["estimate"] is None and res["completeness"]["structured_primary"]["complete"] == 0
    # a family that is not even planned
    items = {f"realizable|{f}|0": {"status": "ok_complete_grid", "primary_cell_complete": True,
                                   "strata": {"label": "realizable", "family": f}} for f in FAMS[:-1]}
    c = completeness_v2(items, SPEC)
    assert c["structured_primary"]["status"] == "incomplete" and c["structured_primary"]["families_not_planned"] == [FAMS[-1]]


def test_fixture_phase_is_rendered_and_sizing_refused(tmp_path):
    items = _s2_items(per=1, nulls=1)
    plan = _s2_plan("fx", items, phase="fixture", freeze={"freeze_commit": "0" * 40, "fixture": True})
    run = Run("fx", plan, runs_root=tmp_path)
    with pytest.raises(Exception, match="differs from the plan phase"):
        run.execute(run_world_v2, workers=4, timeout_s=300)                 # development mode on a fixture plan
    Run("fx", plan, runs_root=tmp_path, resume=True).execute(run_world_v2, workers=4, timeout_s=300, mode="fixture")
    assert load_run(tmp_path / "fx")["phase"] == "fixture"
    res = _analyze(tmp_path / "fx", tmp_path)
    assert res["phase"] == "fixture" and res["primary"]["status"] == "complete (fixture); not confirmatory"
    with pytest.raises(AnalysisRefused, match="development-only"):
        analyze_v2([tmp_path / "fx"], tmp_path / "o2", EP, reps_primary=50, reps_secondary=20, development_sizing=True)


def test_mixed_phases_refused(s2_store, tmp_path):
    items = [("realizable|conjunctive|7", {**_s2_items(per=1, nulls=0)[0][1], "index": 7})]
    plan = _s2_plan("fx2", items, phase="fixture", freeze={"freeze_commit": "0" * 40})
    Run("fx2", plan, runs_root=tmp_path).execute(run_world_v2, workers=1, timeout_s=300, mode="fixture")
    with pytest.raises(AnalysisRefused, match="different phases"):
        _analyze([s2_store, tmp_path / "fx2"], tmp_path)


def test_phase_provenance_contradiction_is_corruption(tmp_path):
    plan = _s2_plan("bad", _s2_items(per=1, nulls=0)[:1], phase="confirmatory")      # phase without freeze block
    Run("bad", plan, runs_root=tmp_path).close()
    with pytest.raises(RunCorruption, match="phase"):
        load_run(tmp_path / "bad")


# ---------------------------------------------------------------------------------------------- S1

@pytest.fixture(scope="module")
def s1_store(tmp_path_factory):
    root = tmp_path_factory.mktemp("s1store")
    items = [(f"sparse_conj|n8|{i}|{b}", {"salt": "t-r3", "index": i, "family": "sparse_conj", "n": 8, "backend": b,
                                          "query_timeout_s": 20, "limits": {}})
             for i in range(2) for b in ("reference", "index_sat", "codecs")]
    plan = make_plan("s1", "S1", {"t": 1}, items, strata_fn=_strata)
    Run("s1", plan, runs_root=root).execute(run_item, workers=3, timeout_s=300, maxtasks=1)
    return root / "s1"


def test_s1_rss_from_envelope_and_missing_is_null(s1_store, tmp_path):
    res = json.loads(Path(s1_analyze([s1_store], tmp_path / "a")["summary"]).read_text())
    assert all(v is not None and v > 0 for v in res["peak_rss_mib_median"].values())
    assert all(c["measured"] == c["ok_items"] for c in res["peak_rss_coverage"].values())
    assert res["query_grid_reconciliation"]["status"] == "complete" and res["phase"] == "development"
    d = _copy(s1_store, tmp_path)
    for b in ("reference",):
        for i in range(2):
            f = _att(d, f"sparse_conj|n8|{i}|{b}")
            rec = json.loads(f.read_text())
            rec["worker_peak_rss_bytes"] = None
            f.write_text(json.dumps(rec))
    res = json.loads(Path(s1_analyze([d], tmp_path / "b")["summary"]).read_text())
    assert res["peak_rss_mib_median"]["reference|n8"] is None
    assert res["peak_rss_coverage"]["reference|n8"] == {"measured": 0, "ok_items": 2}


def test_s1_missing_query_rows_counted_and_duplicates_refused(s1_store, tmp_path):
    d = _copy(s1_store, tmp_path)
    _edit(d, "sparse_conj|n8|0|index_sat", lambda o: o["queries"].pop(3))
    res = json.loads(Path(s1_analyze([d], tmp_path / "a")["summary"]).read_text())
    assert res["completion"]["index_sat|n8"]["query_missing"] == 1
    assert sum(res["completion"]["index_sat|n8"].values()) == 48
    assert res["query_grid_reconciliation"]["status"] == "incomplete"
    d2 = _copy(s1_store, tmp_path / "x")

    def dup(o):
        o["queries"][4] = dict(o["queries"][3])
    _edit(d2, "sparse_conj|n8|1|index_sat", dup)
    with pytest.raises(S1OutputDefect):
        s1_analyze([d2], tmp_path / "b")
    d3 = _copy(s1_store, tmp_path / "y")
    _edit(d3, "sparse_conj|n8|1|reference", lambda o: o.update(world_id="S1-other"))
    with pytest.raises(S1OutputDefect, match="world_id"):
        s1_analyze([d3], tmp_path / "c")
