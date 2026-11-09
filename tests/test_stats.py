import numpy as np
import pytest

from causalguard.stats import (
    bootstrap_coverage,
    design_simulation,
    holm,
    normal_approx_n,
    paired_cluster_bootstrap,
    stratified_mean,
    stratified_se,
)


def test_stratified_mean_equal_weights_hand():
    v = np.array([1.0, 1.0, 1.0, 0.0])
    s = np.array(["a", "a", "a", "b"])
    assert stratified_mean(v, s) == 0.5          # not the pooled 0.75
    assert stratified_se(np.array([0.0, 2.0, 1.0, 1.0]), np.array(["a", "a", "b", "b"])) == pytest.approx(np.sqrt(2 / 2) / 2)


def test_bootstrap_constant_and_sign():
    r = paired_cluster_bootstrap(np.full(30, 0.1), np.array(["x"] * 15 + ["y"] * 15), replicates=500)
    assert r.estimate == pytest.approx(0.1) and r.lo == pytest.approx(0.1) and r.hi == pytest.approx(0.1)
    rng = np.random.default_rng(0)
    d = rng.normal(0.05, 0.3, 200)
    s = np.array(["a", "b"] * 100)
    a = paired_cluster_bootstrap(d, s, replicates=1000, seed=1)
    b = paired_cluster_bootstrap(-d, s, replicates=1000, seed=1)       # swapped condition labels
    assert a.estimate == pytest.approx(-b.estimate) and a.lo == pytest.approx(-b.hi)
    assert a.n_worlds == 200 and a.replicates == 1000
    again = paired_cluster_bootstrap(d, s, replicates=1000, seed=1)
    assert again == a                                                   # deterministic


def test_bootstrap_refuses_missing():
    with pytest.raises(ValueError):
        paired_cluster_bootstrap([0.1, np.nan], ["a", "a"])
    with pytest.raises(ValueError):
        paired_cluster_bootstrap([], [])


def test_bootstrap_coverage_near_nominal():
    rng = np.random.default_rng(3)
    pop = np.concatenate([rng.normal(0.1, 0.4, 500), rng.normal(-0.05, 0.2, 500)])
    st = np.array(["a"] * 500 + ["b"] * 500)
    cov = bootstrap_coverage(pop, st, n_per_stratum=60, sims=200, replicates=400)
    assert 0.89 <= cov["coverage"] <= 0.99


def test_design_simulation_monotone_and_null_controlled():
    rng = np.random.default_rng(4)
    d = rng.normal(0.03, 0.5, 300)
    s = np.array(["a", "b", "c"] * 100)
    res = design_simulation(d, s, n_grid=(150, 600, 1500), sims=400)
    hw = [r["observed"]["median_half_width"] for r in res["grid"]]
    assert hw[0] > hw[1] > hw[2]
    for r in res["grid"]:
        assert r["null"]["p_lower_gt_0"] < 0.06
    assert res["grid"][-1]["effect"]["p_lower_gt_0"] > res["grid"][0]["effect"]["p_lower_gt_0"]
    assert "assumptions" in res and res["assumptions"]["dev_worlds"] == 300


def test_planning_formula_matches_protocol():
    assert normal_approx_n(0.5) in (784, 785)
    assert normal_approx_n(0.7) in (1537, 1538, 1539)


def test_holm_hand():
    out = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert out == {"a": 0.03, "c": 0.06, "b": 0.06}


def test_cluster_bootstrap_balanced_accuracy_hand():
    from causalguard.stats import balanced_accuracy_from_counts, cluster_bootstrap
    bc = np.array([[2, 2], [2, 1], [0, 0]])          # recall 1.0 and 0.5; third class absent
    assert balanced_accuracy_from_counts(bc) == 0.75
    worlds = np.array([[[1, 1], [1, 0], [0, 0]], [[1, 1], [1, 1], [0, 0]]], dtype=float)
    r = cluster_bootstrap(lambda idx: balanced_accuracy_from_counts(worlds[idx].sum(axis=0)), 2, replicates=200)
    assert r["estimate"] == 0.75 and 0.5 <= r["ci95"][0] <= r["ci95"][1] <= 1.0
