"""Parity of the compatible index implementation with the pinned upstream CausalBool owners.

Requires CAUSALBOOL_ROOT pointing at a checkout of the pinned revision
(scripts/fetch_upstream.sh).  Skipped otherwise; skipping is reported, never counted as a pass."""
import json
import os
import random
from pathlib import Path

import pytest

from causalguard import reference
from causalguard.index_repr import from_rule
from causalguard.schema import Network, Rule

pytestmark = pytest.mark.upstream

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def up():
    from causalguard.upstream_adapter import Upstream, UpstreamUnavailable
    try:
        return Upstream(os.environ.get("CAUSALBOOL_ROOT"))
    except UpstreamUnavailable as e:
        pytest.skip(f"upstream unavailable: {e}")


def _random_net(rng, n, kmax=3):
    rules = []
    for _ in range(n):
        k = rng.randint(0, min(n, kmax))
        rules.append(Rule(tuple(sorted(rng.sample(range(n), k))), rng.getrandbits(1 << k)))
    return Network(n, tuple(rules))


def test_provenance_pinned(up):
    assert up.provenance["ok"] and up.provenance["revision_ok"]


def test_repertoire_parity(up):
    rng = random.Random(42)
    cells = 0
    for _ in range(150):
        net = _random_net(rng, rng.randint(1, 7))
        rep = up.repertoire(net)
        for x in range(1 << net.n):
            assert rep[x] == reference.step_bits(net, reference.to_bits(x, net.n))
            cells += net.n
    assert cells > 10000


def test_horizon_counts_updates_not_rows(up):
    net = Network(2, (Rule((0,), 1), Rule((0,), 2)))
    rows = up.evolve_rows(net, [0, 0], 3)          # 3 rows = 2 updates upstream
    assert len(rows) == 3
    from causalguard.schema import Intervention
    tr = reference.run(net, 0, Intervention(), 2)  # horizon 2 = 2 updates
    assert [reference.to_bits(s, 2) for s in tr] == rows


def test_minimal_dnf_cover_parity(up):
    """Same on-set; our exact cover never uses more clauses than upstream's greedy cover."""
    rng = random.Random(7)
    stats = {"tables": 0, "equal": 0, "fewer": 0}
    for _ in range(400):
        k = rng.randint(1, 6)
        table = rng.getrandbits(1 << k)
        local = [(table >> y) & 1 for y in range(1 << k)]
        ups = up.minimal_dnf(local)
        ours = from_rule(Rule(tuple(range(k)), table), k, polarity=1)
        # upstream clauses reproduce the on-set
        for y in range(1 << k):
            hit = any(all((y >> a) & 1 for a in c["activators"]) and not any((y >> b) & 1 for b in c["inhibitors"])
                      for c in ups)
            assert hit == bool(local[y])
            assert ours.output(y) == local[y]
        stats["tables"] += 1
        if ours.exact_cover:
            assert len(ours.families) <= len(ups)
        stats["equal" if len(ours.families) == len(ups) else "fewer"] += 1
    assert stats["tables"] == 400
    (ROOT / "reports" / "development").mkdir(parents=True, exist_ok=True)
    (ROOT / "reports" / "development" / "upstream_dnf_parity.json").write_text(json.dumps(stats, indent=1))


def test_rule110_upstream_three_clauses(up):
    on = {"110", "101", "011", "010", "001"}
    local = [int(format(y, "03b") in on) for y in range(8)]
    ups = up.minimal_dnf(local)
    assert len(ups) == 3
    strings = set()
    for c in ups:
        s = ["*"] * 3
        for a in c["activators"]:
            s[a] = "1"
        for b in c["inhibitors"]:
            s[b] = "0"
        strings.add("".join(s))
    ours = from_rule(Rule((0, 1, 2), sum(v << y for y, v in enumerate(local))), 3, polarity=1)
    assert len(ours.families) == 3
    # both covers place every don't-care on a connected input
    assert all(s.count("*") == 1 for s in strings)
