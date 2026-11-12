"""R6 Track S: sparse support-signature masses, XDC-EB fit certificates and brute-force agreement."""
from __future__ import annotations

import itertools
import math
import random
import sys
from pathlib import Path

import numpy as np
import pytest

from causalguard.schema import Query

sys.path.insert(0, str(Path(__file__).parent))
import test_r6_xdc_oracle as O  # noqa: E402  (own rule space, own simulator)


def _h1_case(rng, n, k, base, i):
    ev, q = O.make_case(rng, n, k, base, i)
    q = Query.point(O._point_state(q, n), n, q.intervention, 1, q.target)
    return ev, q


def test_sparse_masses_equal_dense_xdc():
    """At small n the support-signature counts give exactly the dense type masses, and the flat code, exact XDC and
    XDC-EB predictions equal the dense implementations (h = 1)."""
    from causalguard.r5.priors import XDC, XDCEB
    from causalguard.r6.scale import SparseMasses, base_weights, predict_sparse
    rng = random.Random(3)
    checked = 0
    for i in range(24):
        n, k = [(4, 2), (5, 2), (5, 3), (6, 3)][i % 4]
        base = ("gate", "cgh_flat")[i % 2]
        ev, q = _h1_case(rng, n, min(k, 2), base, i)
        x = XDC(ev, k, base=base)
        if x.vs.empty:
            continue
        sm = SparseMasses(ev, k)
        assert np.allclose(sm.u(base), x.u, rtol=1e-12, atol=0)
        assert np.allclose(base_weights(n, k, base)[5], x.G0, rtol=1e-12, atol=0)
        out = predict_sparse(ev, [("q", q)], bases=(base,), eb_bases=(base,), a_grid=(4.0,), exact_bases=(base,), k=k)
        pr = out["queries"][0]["predictions"]
        dense = x.probabilities(q)
        eb = XDCEB(ev, k, base=base, a=4.0).probabilities(q)["xdc_eb"]
        # all three return P(target node = 1) (the literal convention is applied by the caller)
        assert abs(pr[f"xdc[{base}]"] - dense["xdc"]) < 1e-10
        assert abs(pr[f"flat[{base}]"] - dense["xdc_tinf"]) < 1e-10
        assert abs(pr[f"xdc_eb[{base}]|a4|full"] - eb) < 1e-10
        checked += 1
    assert checked >= 20


def _eb_bruteforce(ev, k, q, base, p, names):
    """Enumerate mechanisms of the oracle's own rule space under rule weights p_type w / W(type)."""
    n = ev.n
    rules, W = O.rule_space(n, k, base)
    # oracle types are permutation orbits; map them to the XDC type order through the orbit's minimum table
    pidx = {(d, min(orb)): i for i, (d, orb) in enumerate(sorted({r[2] for r in rules}, key=lambda t: (t[0], min(t[1]))))}
    pos = {nm: i for i, nm in enumerate(names)}
    per_node = [[r for r in rules if O._fits(r, j, ev)] for j in range(n)]
    x0 = O._point_state(q, n)
    num = den = 0.0
    for mech in itertools.product(*per_node):
        m = math.prod(p[pos[(r[2][0], min(r[2][1]))]] * r[3] / W[r[2]] for r in mech)
        s = O._start(q.intervention, x0)
        for _ in range(q.horizon):
            s = O._step(mech, q.intervention, s)
        den += m
        num += m if ((s >> q.target.node) & 1) == 1 else 0.0
    assert pidx  # (types exist)
    return num / den


def test_xdc_eb_matches_bruteforce_given_fitted_weights():
    from causalguard.r5.priors import XDCEB
    rng = random.Random(9)
    done = 0
    for i in range(24):
        n, k = O.GRID[i % 4]
        base = ("gate", "cgh_flat")[(i // 4) % 2]
        ev, q = O.make_case(rng, n, k, base, i)
        for loo in (False, True):
            m = XDCEB(ev, k, base=base, a=2.0, loo=loo)
            if m.vs.empty:
                break
            pr = m.probabilities(q)
            f = m.fit_for(q.target.node)
            assert f["certified"] and f["gap"] <= 1e-6
            assert abs(pr["xdc_eb"] - _eb_bruteforce(ev, k, q, base, f["p"], m.type_names)) < 1e-9
            done += 1
    assert done >= 30


def test_fit_is_optimal_and_regulariser_limits():
    from causalguard.r5.priors import fit_type_weights
    rng = np.random.default_rng(1)
    for _ in range(20):
        L, n = 12, int(rng.integers(3, 30))
        u = rng.random((n, L)) ** 3
        G0 = rng.random(L)
        G0 /= G0.sum()
        for a in (0.0, 1.0, 16.0):
            f = fit_type_weights(u, G0, a, tol=1e-10)
            assert f["certified"]
            F = lambda p: np.log(u @ p).sum() + (a * G0 * np.log(np.maximum(p, 1e-300))).sum()  # noqa: E731
            for _ in range(50):                                  # no simplex point beats the fit by more than the gap
                z = rng.dirichlet(np.ones(L))
                assert F(z) <= f["objective"] + f["gap"] + 1e-9
    f = fit_type_weights(rng.random((5, 7)), np.full(7, 1 / 7), 1e9)
    assert np.allclose(f["p"], 1 / 7, atol=1e-6)                  # a -> inf: the base code's type masses


def test_fit_refuses_empty_rows():
    from causalguard.r5.priors import fit_type_weights
    with pytest.raises(ValueError):
        fit_type_weights(np.zeros((2, 3)), np.full(3, 1 / 3), 1.0)


def test_make_design_defaults_unchanged_and_h1_variant():
    from causalguard.r5 import data as D
    a = D.make_design("s", "key", 8)
    b = D.make_design("s", "key", 8, max_budget=max(D.BUDGETS), horizons=(1,) * 4 + (2,) * 4)
    assert a.to_json() == b.to_json()
    c = D.make_design("s", "key", 24, max_budget=64, horizons=(1,) * 8)
    assert len(c.obs_specs) == 64 and all(q.horizon == 1 for _, q in c.queries) and len(c.queries) == 8


@pytest.mark.skipif(not (Path.home() / ".cache/causalguard/ext/biodivine-boolean-models/models").exists(),
                    reason="pinned Biodivine checkout not present")
def test_s_world_smoke_and_public_only():
    from causalguard.r6.scale import s_world
    key = "intact:[id-110]__[var-9]__[in-0]__[ASYMMETRIC-CELL-DIVISION-B]"
    r = s_world({"key": key, "panel": "intact", "group": "g", "split": "calibration", "design_salt": "t",
                 "budgets": [4, 8]})
    assert r["n"] == 9 and set(r["predictions"]) == {"4", "8"}
    pr = r["predictions"]["8"]["queries"][0]["predictions"]
    assert {"flat[gate]", "xdc_eb[cgh_flat]|a4|loo", "xdc[cgh_flat]"} <= set(pr)
    assert all(f["certified"] for f in r["predictions"]["8"]["fits"].values())
    assert set(r["outcomes"]) == {f"q{i}" for i in range(8)}
