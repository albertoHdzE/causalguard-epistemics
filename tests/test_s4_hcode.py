"""CGH-1: exact round trips, a hand-derived golden length, ordering/sharing cases, ablation variants, rejection."""
import random

import pytest

from causalguard.codec import DecodeError
from causalguard.s4.hcode import VARIANTS, bits, decode, describe, encode, header_bits, local_catalogue, offset_rule, signature
from causalguard.schema import Network, Rule


def ring(n, offs, table):
    return Network(n, tuple(offset_rule(i, offs, table, n) for i in range(n)))


def rand_net(rng, n, k):
    rules = []
    for _ in range(n):
        d = rng.randint(0, k)
        rules.append(Rule(tuple(sorted(rng.sample(range(n), d))), rng.getrandbits(1 << d)))
    return Network(n, tuple(rules))


def canon(net):
    return Network(net.n, tuple(r.canonical() for r in net.rules))


def test_golden_xor_ring_length_by_hand():
    # node i = XOR(x_i, x_{i+1 mod 4}); k = 2.
    net = ring(4, (0, 1), 0b0110)
    # header: variant 4 + gamma(4)=5 + gamma(3)=3 + ordering 1 + mode 2 = 15
    assert header_bits(4, 2) == 15
    # TEMPLATE: LOCAL = arity 2 bits + id width_for(10+1)=4 -> 6; OFFSETS rank width_for(C(4,2)=6) = 3;
    # PATCHES gamma(0+1) = 1.  Total 15 + 6 + 3 + 1 = 25
    b, mode, _ = describe(net, 2, "full")
    assert (b, mode) == (25, 2)
    # FLAT: 4 x (LOCAL 6 + SUPPORT 3) + 15 = 51
    assert describe(net, 2, "flat")[0] == 51
    # no_analytic: LOCAL = 2 + 4 table bits = 6 (same here: XOR has no id field cost but a 4-bit table)
    assert describe(net, 2, "no_analytic")[0] == 25


def test_order_disrupted_sharing_is_dict_not_template():
    rng = random.Random(1)
    n = 6
    rules = []
    for _ in range(n):
        ins = tuple(sorted(rng.sample(range(n), 2)))
        rules.append(Rule(ins, 0b0110))          # same XOR rule, scrambled supports
    net = Network(n, tuple(rules))
    full = describe(net, 2, "full")
    assert full[1] == 1                         # shared dictionary beats per-node and templates
    assert describe(net, 2, "no_order")[0] == full[0]
    assert describe(net, 2, "flat")[0] > full[0]


def test_module_mode_round_trip():
    n = 6
    block = [Rule((0, 1), 0b1000), Rule((1, 2), 0b0110), Rule((0,), 0b01)]
    rules = []
    for b in range(2):
        for r in block:
            rules.append(Rule(tuple(sorted((i + 3 * b) % n for i in r.inputs)), r.table).canonical())
    net = Network(n, tuple(rules))
    bts = encode(net, 2, "full")
    dec, k, info = decode(bts)
    assert dec == canon(net) and info["bits"] == len(bts) == bits(net, 2, "full")


@pytest.mark.parametrize("variant", list(VARIANTS))
@pytest.mark.parametrize("seed", range(25))
def test_random_round_trip(variant, seed):
    rng = random.Random(seed)
    n = rng.randint(2, 9)
    k = min(rng.randint(1, 3), n)
    net = rand_net(rng, n, k)
    bts = encode(net, k, variant)
    dec, kk, info = decode(bts)
    assert dec == canon(net) and kk == k and len(bts) == bits(net, k, variant)


def test_variants_are_ordered_languages():
    rng = random.Random(4)
    for _ in range(30):
        n = rng.randint(3, 8)
        net = ring(n, tuple(sorted(rng.sample(range(n), 3))), rng.getrandbits(8)) if rng.random() < .5 else rand_net(rng, n, 3)
        assert bits(net, 3, "full") <= bits(net, 3, "no_order") <= bits(net, 3, "flat")


def test_signature_inverts_offset_rule():
    rng = random.Random(9)
    for _ in range(200):
        n = rng.randint(3, 9)
        offs = tuple(sorted(rng.sample(range(n), rng.randint(1, 3))))
        t = rng.getrandbits(1 << len(offs))
        base = rng.randrange(n)
        r = offset_rule(base, offs, t, n)
        if r.arity == len(offs):                 # non-degenerate: the signature is recovered exactly
            assert signature(r, base, n) == (offs, t)


def test_rejections():
    net = ring(4, (0, 1), 0b0110)
    b = encode(net, 2)
    with pytest.raises(DecodeError):
        decode(b + [0])                                  # trailing bits
    with pytest.raises(DecodeError):
        decode(b[:-3])                                   # truncated
    bad = list(b)
    bad[4 + 5 + 3] = 1                                   # reserved ordering bit
    with pytest.raises(DecodeError):
        decode(bad)
    with pytest.raises(ValueError):
        encode(Network(4, (Rule((0, 1, 2), 0b10010110),) + net.rules[1:]), 2)   # outside class k=2


def test_catalogue_is_distinct_and_named():
    for d in range(4):
        cat = local_catalogue(d)
        assert len({t for _, t in cat}) == len(cat)
    names = dict(local_catalogue(3))
    assert "MAJORITY_STRICT" in names and "XOR" in names and any(n.startswith("CANAL") for n in names)
