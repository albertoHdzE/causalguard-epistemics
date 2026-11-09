import itertools
import random

from causalguard import reference
from causalguard.dedup import audit, canonical_form, relabel
from causalguard.schema import Network, Rule


def _perm_state(x, perm, n):
    return sum(((x >> i) & 1) << perm[i] for i in range(n))


def test_relabel_conjugates_dynamics():
    rng = random.Random(0)
    for _ in range(50):
        n = rng.randint(2, 5)
        net = Network(n, tuple(Rule(tuple(sorted(rng.sample(range(n), k))), rng.getrandbits(1 << k))
                               for k in (rng.randint(0, min(3, n)) for _ in range(n))))
        perm = tuple(rng.sample(range(n), n))
        rn = relabel(net, perm)
        for x in range(1 << n):
            a = reference.from_bits(reference.step_bits(net, reference.to_bits(x, n)))
            b = reference.from_bits(reference.step_bits(rn, reference.to_bits(_perm_state(x, perm, n), n)))
            assert b == _perm_state(a, perm, n)


def test_renamed_copy_detected_and_distinct_not_merged():
    net = Network(4, (Rule((1, 2), 8), Rule((0,), 1), Rule((3,), 2), Rule((0, 1, 2), 0b10010110)))
    perm = (2, 0, 3, 1)
    copy = relabel(net, perm)
    assert copy != net                                   # hash identity differs
    assert canonical_form(copy) == canonical_form(net)   # isomorphism detected
    other = Network(4, (Rule((1, 2), 14), Rule((0,), 1), Rule((3,), 2), Rule((0, 1, 2), 0b10010110)))
    assert canonical_form(other) != canonical_form(net)
    res = audit([("dev", "a", net), ("test", "b", copy), ("dev", "c", other)])
    assert res["cross_split_duplicates"] == 1 and len(res["duplicate_groups"]) == 1


def test_all_relabellings_same_canonical():
    net = Network(3, (Rule((0, 1), 6), Rule((2,), 1), Rule((), 1)))
    forms = {canonical_form(relabel(net, p)) for p in itertools.permutations(range(3))}
    assert len(forms) == 1
