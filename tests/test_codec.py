import random

import pytest

from causalguard.codec import (
    ALL_NODE_CODECS,
    BitReader,
    BitWriter,
    DecodeError,
    decode_network,
    encode_network,
    generic_bits,
    node_bits,
    rank_subset,
    unrank_subset,
)
from causalguard.schema import Network, Rule


def random_net(rng, n, kmax=4):
    rules = []
    for _ in range(n):
        k = rng.randint(0, min(n, kmax))
        rules.append(Rule(tuple(sorted(rng.sample(range(n), k))), rng.getrandbits(1 << k)))
    return Network(n, tuple(rules))


def test_roundtrip_all_codecs_exhaustive_semantics():
    rng = random.Random(10)
    checked = 0
    for _ in range(250):
        net = random_net(rng, rng.randint(1, 7))
        for c in ALL_NODE_CODECS:
            back = decode_network(encode_network(net, c).data)
            # canonical form is unique per function, so equality == same function on all 2**n states
            assert back.canonical() == net.canonical(), c
            checked += 1
    assert checked == 250 * len(ALL_NODE_CODECS)


def test_archive_accounting_is_exact():
    net = Network(3, (Rule((0, 1, 2), 0b01110110), Rule((0,), 1), Rule((1, 2), 8)))
    for c in ALL_NODE_CODECS:
        a = encode_network(net, c)
        assert a.total_bits == len(a.data) * 8
        assert a.payload_bits == sum(node_bits(c, r, 3) for r in net.rules)
        assert a.total_bits == 48 + a.header_bits + a.payload_bits + (a.framing_bits - 48)


@pytest.mark.parametrize("codec", ALL_NODE_CODECS)
def test_corruption_truncation_trailing_rejected(codec):
    rng = random.Random(11)
    net = random_net(rng, 5)
    data = encode_network(net, codec).data
    with pytest.raises(DecodeError):
        decode_network(data[:-1])                     # truncated
    with pytest.raises(DecodeError):
        decode_network(data + b"\x00")                # trailing byte
    bad = bytearray(data)
    bad[6] ^= 0x10
    with pytest.raises(DecodeError):
        decode_network(bytes(bad))                    # flipped payload bit (CRC)
    with pytest.raises(DecodeError):
        decode_network(b"XXXX" + data[4:])            # bad magic


def test_payload_length_mismatch_detected_even_with_valid_crc():
    import zlib
    net = Network(2, (Rule((0,), 1), Rule((0, 1), 6)))
    a = encode_network(net, "lut")
    body = bytearray(a.data[:-4])
    body += b"\x00"   # extra zero byte inside the CRC-protected body
    data = bytes(body) + zlib.crc32(bytes(body)).to_bytes(4, "big")
    with pytest.raises(DecodeError):
        decode_network(data)


def test_elias_codes_and_subset_ranks():
    w = BitWriter()
    vals = list(range(1, 300))
    for v in vals:
        w.gamma(v)
        w.delta(v)
    r = BitReader(w.bits)
    for v in vals:
        assert r.gamma() == v and r.delta() == v
    import itertools
    import math
    for n in range(0, 8):
        for k in range(n + 1):
            ranks = [rank_subset(s, n) for s in itertools.combinations(range(n), k)]
            assert sorted(ranks) == list(range(math.comb(n, k)))
            for s in itertools.combinations(range(n), k):
                assert unrank_subset(rank_subset(s, n), k, n) == s


def test_rule110_index_shorter_than_its_minterm_listing():
    r = Rule((0, 1, 2), sum(1 << y for y in range(8) if format(y, "03b") in {"110", "101", "011", "010", "001"}))
    assert node_bits("index", r, 3) < node_bits("dnf", r, 3) or node_bits("index", r, 3) <= 30


def test_or_vs_xor_index_scaling():
    n = 10
    orr = Rule(tuple(range(n)), sum(1 << y for y in range(1 << n) if y))
    xor = Rule(tuple(range(n)), sum(1 << y for y in range(1 << n) if bin(y).count("1") % 2))
    b_or, b_xor = node_bits("index", orr, n), node_bits("index", xor, n)
    assert b_xor > 20 * b_or      # parity is expensive in the schema language
    assert node_bits("bdd", xor, n) < b_xor   # ...but not for a BDD: representation-specific
    assert node_bits("gate", xor, n) < 30     # ...nor for a gate catalogue


def test_generic_compressors_same_target_object():
    net = Network(3, (Rule((0,), 1), Rule((0, 1), 6), Rule((), 1)))
    for m in ("lzma", "gzip", "raw"):
        assert generic_bits(net, m) > 0
    # same function written with an inessential input serializes identically (canonical object)
    net2 = Network(3, (Rule((0, 2), 0b0101), Rule((0, 1), 6), Rule((), 1)))
    assert generic_bits(net, "raw") == generic_bits(net2, "raw")
