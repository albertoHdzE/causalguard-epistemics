"""Independently decodable bit codecs for node functions and whole networks.

Owner of every description length reported by CausalGuard (docs/CODEC.md).
All lengths are ACTUAL integer bit counts of a written bitstring that the
matching decoder reconstructs exactly; no floating log2 formula is reported as
an archive length.  Each codec encodes the SAME target object: the network
function F : {0,1}^n -> {0,1}^n (per node: a function of the n-bit state).

Node codecs
-----------
index   polarity(1) | gamma(#families+1) | per family: k:fixed(ceil log2(n+1)) |
        rank of fixed coordinate set among C(n,k):fixed(ceil log2 C(n,k)) | k value bits
dnf     polarity(1) | gamma(#terms+1) | per term: gamma(#lits+1) | per literal:
        coordinate:fixed(ceil log2 n) + value(1)               (same cover as index)
gate    catalogue id:fixed(4) | d:fixed(ceil log2(n+1)) | rank of input set |
        gate parameters | LUT fallback 2**d table bits
circuit d | rank of input set | prefix formula over {LEAF,NOT,AND,OR,XOR}
bdd     d | rank of input set | gamma(#internal nodes+1) | per node (bottom-up):
        level:fixed(ceil log2 d) + low/high refs:fixed(ceil log2(i+2))
lut     d | rank of input set | 2**d table bits
full    2**n table bits (literal repertoire column; n <= 20)

Archive framing (network level): magic 'CGA1'(32) | codec id(8) | codec
version(8) | gamma(n) | delta(payload bit length) | payload | zero padding to a
byte boundary | CRC-32 of all preceding bytes (32).  Decoding rejects bad
magic/version/codec, CRC mismatch, nonzero padding, truncation and trailing
bytes.
"""
from __future__ import annotations

import functools
import gzip
import hashlib
import itertools
import lzma
import math
import zlib
from dataclasses import dataclass
from pathlib import Path

from .index_repr import Family, NodeIndex, from_rule
from .schema import Network, Rule, SemanticsError

CODEC_VERSION = 1
MAGIC = b"CGA1"
CODEC_IDS = {"index": 1, "dnf": 2, "gate": 3, "circuit": 4, "bdd": 5, "lut": 6, "full": 7}
CODEC_NAMES = {v: k for k, v in CODEC_IDS.items()}


class DecodeError(ValueError):
    pass


# --------------------------------------------------------------------------- bit IO

class BitWriter:
    def __init__(self):
        self.bits: list[int] = []

    def write(self, value: int, width: int) -> None:
        if width < 0 or value < 0 or (value >> width):
            raise ValueError(f"value {value} does not fit {width} bits")
        for i in range(width - 1, -1, -1):
            self.bits.append((value >> i) & 1)

    def gamma(self, x: int) -> None:
        if x < 1:
            raise ValueError("gamma needs x >= 1")
        L = x.bit_length()
        self.bits.extend([0] * (L - 1))
        self.write(x, L)

    def delta(self, x: int) -> None:
        if x < 1:
            raise ValueError("delta needs x >= 1")
        L = x.bit_length()
        self.gamma(L)
        self.write(x - (1 << (L - 1)), L - 1)

    def __len__(self):
        return len(self.bits)


class BitReader:
    def __init__(self, bits: list[int], start: int = 0, end: int | None = None):
        self.bits = bits
        self.pos = start
        self.end = len(bits) if end is None else end

    def read(self, width: int) -> int:
        if self.pos + width > self.end:
            raise DecodeError("truncated bitstream")
        v = 0
        for _ in range(width):
            v = (v << 1) | self.bits[self.pos]
            self.pos += 1
        return v

    def gamma(self) -> int:
        z = 0
        while True:
            if self.pos >= self.end:
                raise DecodeError("truncated gamma code")
            if self.bits[self.pos] == 0:
                z += 1
                self.pos += 1
                if z > 64:
                    raise DecodeError("gamma code too long")
            else:
                break
        return self.read(z + 1)

    def delta(self) -> int:
        L = self.gamma()
        if L > 64:
            raise DecodeError("delta length too large")
        return (1 << (L - 1)) | self.read(L - 1)


def width_for(count: int) -> int:
    """Bits for a fixed-width index into ``count`` alternatives (0 if count<=1)."""
    return 0 if count <= 1 else (count - 1).bit_length()


# --------------------------------------------------------------------------- combinatorial ranking

def rank_subset(subset: tuple[int, ...], n: int) -> int:
    """Colex rank of an ascending k-subset of range(n) among C(n,k)."""
    r = 0
    for i, c in enumerate(subset):
        r += math.comb(c, i + 1)
    return r


def unrank_subset(r: int, k: int, n: int) -> tuple[int, ...]:
    if r >= math.comb(n, k):
        raise DecodeError("subset rank out of range")
    out = []
    for i in range(k, 0, -1):
        c = i - 1
        while math.comb(c + 1, i) <= r:
            c += 1
        out.append(c)
        r -= math.comb(c, i)
    return tuple(sorted(out))


def write_subset(w: BitWriter, subset: tuple[int, ...], n: int) -> None:
    w.write(len(subset), width_for(n + 1))
    w.write(rank_subset(subset, n), width_for(math.comb(n, len(subset))))


def read_subset(rd: BitReader, n: int) -> tuple[int, ...]:
    k = rd.read(width_for(n + 1))
    if k > n:
        raise DecodeError("subset size exceeds n")
    return unrank_subset(rd.read(width_for(math.comb(n, k))), k, n)


# --------------------------------------------------------------------------- local helpers

def _local_table_of(node_fn, inputs: tuple[int, ...]) -> int:
    t = 0
    for y in range(1 << len(inputs)):
        x = 0
        for j, i in enumerate(inputs):
            if (y >> j) & 1:
                x |= 1 << i
        t |= node_fn(x) << y
    return t


# --------------------------------------------------------------------------- index / dnf

def encode_index(w: BitWriter, node: NodeIndex) -> None:
    n = node.n
    w.write(node.polarity, 1)
    w.gamma(len(node.families) + 1)
    for f in node.families:
        pos = tuple(i for i in range(n) if (f.fixed >> i) & 1)
        write_subset(w, pos, n)
        for i in pos:
            w.write((f.anchor >> i) & 1, 1)


def decode_index(rd: BitReader, n: int) -> NodeIndex:
    pol = rd.read(1)
    m = rd.gamma() - 1
    fams = []
    conn = 0
    for _ in range(m):
        pos = read_subset(rd, n)
        F = A = 0
        for i in pos:
            F |= 1 << i
            A |= rd.read(1) << i
        fams.append(Family(F, A))
        conn |= F
    return NodeIndex(n, pol, tuple(fams), tuple(i for i in range(n) if (conn >> i) & 1), True, "decoded")


def encode_dnf(w: BitWriter, node: NodeIndex) -> None:
    n = node.n
    w.write(node.polarity, 1)
    w.gamma(len(node.families) + 1)
    wv = width_for(n)
    for f in node.families:
        pos = [i for i in range(n) if (f.fixed >> i) & 1]
        w.gamma(len(pos) + 1)
        for i in pos:
            w.write(i, wv)
            w.write((f.anchor >> i) & 1, 1)


def decode_dnf(rd: BitReader, n: int) -> NodeIndex:
    pol = rd.read(1)
    m = rd.gamma() - 1
    fams = []
    wv = width_for(n)
    conn = 0
    for _ in range(m):
        k = rd.gamma() - 1
        F = A = 0
        for _ in range(k):
            i = rd.read(wv)
            if i >= n or (F >> i) & 1:
                raise DecodeError("bad DNF literal")
            F |= 1 << i
            A |= rd.read(1) << i
        fams.append(Family(F, A))
        conn |= F
    return NodeIndex(n, pol, tuple(fams), tuple(i for i in range(n) if (conn >> i) & 1), True, "decoded")


# --------------------------------------------------------------------------- lut / full

def encode_lut(w: BitWriter, rule: Rule, n: int) -> None:
    write_subset(w, rule.inputs, n)
    w.write(rule.table, 1 << rule.arity)


def decode_lut(rd: BitReader, n: int) -> Rule:
    ins = read_subset(rd, n)
    if len(ins) > 24:
        raise DecodeError("LUT arity too large")
    return Rule(ins, rd.read(1 << len(ins)))


def encode_full(w: BitWriter, rule: Rule, n: int) -> None:
    if n > 20:
        raise SemanticsError("full repertoire column refused for n > 20")
    col = 0
    for x in range(1 << n):
        y = 0
        for t, i in enumerate(rule.inputs):
            if (x >> i) & 1:
                y |= 1 << t
        col |= ((rule.table >> y) & 1) << x
    w.write(col, 1 << n)


def decode_full(rd: BitReader, n: int) -> Rule:
    if n > 20:
        raise DecodeError("full repertoire column refused for n > 20")
    col = rd.read(1 << n)
    return Rule(tuple(range(n)), col).canonical()


# --------------------------------------------------------------------------- gate catalogue

GATE_CATALOGUE = ("CONST0", "CONST1", "COPY", "NOT", "AND", "OR", "NAND", "NOR", "XOR", "XNOR",
                  "IMPLIES", "NIMPLIES", "MAJORITY", "KOFN", "LUT")
_GATE_W = width_for(16)  # 4 bits; 15 entries + 1 reserved


def _gate_table(g: str, d: int, param: int = 0) -> int | None:
    """Local table over d ascending inputs; None if g not applicable to d."""
    rng = range(1 << d)
    pc = [bin(y).count("1") for y in rng]
    if g == "CONST0":
        return 0 if d == 0 else None
    if g == "CONST1":
        return 1 if d == 0 else None
    if g in ("COPY", "NOT"):
        if d != 1:
            return None
        return 0b10 if g == "COPY" else 0b01
    if d < 2 and g not in ("KOFN", "LUT"):
        return None
    f = {
        "AND": lambda y: pc[y] == d, "OR": lambda y: pc[y] > 0, "NAND": lambda y: pc[y] != d,
        "NOR": lambda y: pc[y] == 0, "XOR": lambda y: pc[y] % 2 == 1, "XNOR": lambda y: pc[y] % 2 == 0,
        "MAJORITY": lambda y: 2 * pc[y] > d,
    }
    if g in f:
        if g == "MAJORITY" and d % 2 == 0:
            return None
        return sum(1 << y for y in rng if f[g](y))
    if g in ("IMPLIES", "NIMPLIES"):
        if d != 2:
            return None
        a, b = (0, 1) if param == 0 else (1, 0)   # param: which input is the antecedent
        t = sum(1 << y for y in rng if (not ((y >> a) & 1)) or ((y >> b) & 1))
        return t if g == "IMPLIES" else ((1 << 4) - 1) ^ t
    if g == "KOFN":
        if d < 2 or not (1 <= param <= d):
            return None
        return sum(1 << y for y in rng if pc[y] >= param)
    return None


def _gate_param_width(g: str, d: int) -> int:
    if g in ("IMPLIES", "NIMPLIES"):
        return 1
    if g == "KOFN":
        return width_for(d + 1)
    return 0


def encode_gate(w: BitWriter, rule: Rule, n: int) -> None:
    rule = rule.canonical()
    d = rule.arity
    best = None
    for gi, g in enumerate(GATE_CATALOGUE[:-1]):
        params = range(1 << _gate_param_width(g, d)) if _gate_param_width(g, d) else [0]
        for p in params:
            if _gate_table(g, d, p) == rule.table:
                best = (gi, g, p)
                break
        if best:
            break
    if best is None:
        w.write(GATE_CATALOGUE.index("LUT"), _GATE_W)
        encode_lut(w, rule, n)
        return
    gi, g, p = best
    w.write(gi, _GATE_W)
    write_subset(w, rule.inputs, n)
    pw = _gate_param_width(g, d)
    if pw:
        w.write(p, pw)


def decode_gate(rd: BitReader, n: int) -> Rule:
    gi = rd.read(_GATE_W)
    if gi >= len(GATE_CATALOGUE):
        raise DecodeError("unknown gate id")
    g = GATE_CATALOGUE[gi]
    if g == "LUT":
        return decode_lut(rd, n)
    ins = read_subset(rd, n)
    d = len(ins)
    pw = _gate_param_width(g, d)
    p = rd.read(pw) if pw else 0
    t = _gate_table(g, d, p)
    if t is None:
        raise DecodeError(f"gate {g} not applicable at arity {d}/param {p}")
    return Rule(ins, t)


# --------------------------------------------------------------------------- circuit (formula) code
# Prefix formula over the node's d inputs: LEAF '0'+var(ceil log2 d); NOT '100'; AND '101'; OR '110';
# XOR '111'.  d=0: a single bit gives the constant.  Minimum formulas are exhaustively searched for
# d <= 3 (exact minimum under this code); for d > 3 a constructive formula (gate-structured or DNF)
# gives an upper bound and is labelled as such.

_OPS = {"NOT": (0b100, 3), "AND": (0b101, 3), "OR": (0b110, 3), "XOR": (0b111, 3)}


def _formula_bits(expr, d: int) -> int:
    if expr[0] == "LEAF":
        return 1 + width_for(d)
    if expr[0] == "NOT":
        return 3 + _formula_bits(expr[1], d)
    return 3 + _formula_bits(expr[1], d) + _formula_bits(expr[2], d)


def _eval_formula(expr, d: int) -> int:
    full = (1 << (1 << d)) - 1
    if expr[0] == "LEAF":
        v = expr[1]
        return sum(1 << y for y in range(1 << d) if (y >> v) & 1)
    if expr[0] == "NOT":
        return full ^ _eval_formula(expr[1], d)
    a, b = _eval_formula(expr[1], d), _eval_formula(expr[2], d)
    return {"AND": a & b, "OR": a | b, "XOR": a ^ b}[expr[0]]


@functools.lru_cache(maxsize=None)
def _min_formulas(d: int) -> dict[int, tuple]:
    """Exhaustive minimum-bit formula for every function of d<=3 inputs that
    depends on all d inputs is not required: we search all tables."""
    if d > 3:
        raise ValueError("exhaustive formula search limited to d <= 3")
    leafw = 1 + width_for(d)
    best: dict[int, tuple] = {}
    by_cost: dict[int, dict[int, tuple]] = {}
    for v in range(d):
        e = ("LEAF", v)
        t = _eval_formula(e, d)
        by_cost.setdefault(leafw, {})[t] = e
    target_count = 1 << (1 << d)
    cost = leafw
    max_cost = 80
    while cost <= max_cost:
        layer = by_cost.get(cost, {})
        for t, e in list(layer.items()):
            if t not in best:
                best[t] = e
        if len(best) == target_count:
            break
        # build expressions of cost+1 .. using known best (dynamic programming over costs)
        cost += 1
        new: dict[int, tuple] = {}
        full = (1 << (1 << d)) - 1
        # NOT
        for c1, lay in by_cost.items():
            if c1 + 3 == cost:
                for t, e in lay.items():
                    nt = full ^ t
                    if nt not in best and nt not in new:
                        new[nt] = ("NOT", e)
        for c1, lay1 in list(by_cost.items()):
            c2 = cost - 3 - c1
            if c2 < leafw or c2 not in by_cost:
                continue
            for t1, e1 in lay1.items():
                for t2, e2 in by_cost[c2].items():
                    for op, f in (("AND", t1 & t2), ("OR", t1 | t2), ("XOR", t1 ^ t2)):
                        if f not in best and f not in new:
                            new[f] = (op, e1, e2)
        if new:
            by_cost.setdefault(cost, {}).update(new)
    return best


def _constructive_formula(table: int, d: int):
    """DNF-structured formula (upper bound) for d > 3 or fallback."""
    from .index_repr import minimum_cover, prime_implicants
    mts = [y for y in range(1 << d) if (table >> y) & 1]
    if not mts:
        return ("AND", ("LEAF", 0), ("NOT", ("LEAF", 0)))
    if len(mts) == 1 << d:
        return ("OR", ("LEAF", 0), ("NOT", ("LEAF", 0)))
    cover, _ = minimum_cover(mts, prime_implicants(mts, d), 20000)
    terms = []
    for m, v in cover:
        lits = [("LEAF", i) if (v >> i) & 1 else ("NOT", ("LEAF", i)) for i in range(d) if (m >> i) & 1]
        t = lits[0]
        for x in lits[1:]:
            t = ("AND", t, x)
        terms.append(t)
    out = terms[0]
    for t in terms[1:]:
        out = ("OR", out, t)
    return out


def _xor_chain(d: int, negate: bool):
    e = ("LEAF", 0)
    for i in range(1, d):
        e = ("XOR", e, ("LEAF", i))
    return ("NOT", e) if negate else e


def circuit_formula(rule: Rule) -> tuple[tuple | None, bool]:
    """(formula, exact_minimum) for a canonical rule.  formula None for d=0.

    d <= 3: exhaustive minimum under this code.  d > 3: the shortest of three declared
    constructions (on-set DNF, NOT of off-set DNF, XOR chain when the function is a parity),
    an UPPER BOUND, flagged exact=False."""
    r = rule.canonical()
    d = r.arity
    if d == 0:
        return None, True
    if d <= 3:
        return _min_formulas(d)[r.table], True
    full = (1 << (1 << d)) - 1
    cands = [_constructive_formula(r.table, d), ("NOT", _constructive_formula(full ^ r.table, d))]
    par = sum(1 << y for y in range(1 << d) if bin(y).count("1") % 2)
    if r.table in (par, full ^ par):
        cands.append(_xor_chain(d, r.table != par))
    return min(cands, key=lambda e: _formula_bits(e, d)), False


def _write_formula(w: BitWriter, e, d: int) -> None:
    if e[0] == "LEAF":
        w.write(0, 1)
        w.write(e[1], width_for(d))
        return
    code, width = _OPS[e[0]]
    w.write(code, width)
    for sub in e[1:]:
        _write_formula(w, sub, d)


def _read_formula(rd: BitReader, d: int, depth: int = 0):
    if depth > 200:
        raise DecodeError("formula too deep")
    if rd.read(1) == 0:
        v = rd.read(width_for(d))
        if v >= d:
            raise DecodeError("leaf variable out of range")
        return ("LEAF", v)
    op = {0b00: "NOT", 0b01: "AND", 0b10: "OR", 0b11: "XOR"}[rd.read(2)]
    if op == "NOT":
        return ("NOT", _read_formula(rd, d, depth + 1))
    return (op, _read_formula(rd, d, depth + 1), _read_formula(rd, d, depth + 1))


def encode_circuit(w: BitWriter, rule: Rule, n: int) -> None:
    r = rule.canonical()
    write_subset(w, r.inputs, n)
    if r.arity == 0:
        w.write(r.table, 1)
        return
    e, _ = circuit_formula(r)
    _write_formula(w, e, r.arity)


def decode_circuit(rd: BitReader, n: int) -> Rule:
    ins = read_subset(rd, n)
    d = len(ins)
    if d == 0:
        return Rule((), rd.read(1))
    e = _read_formula(rd, d)
    return Rule(ins, _eval_formula(e, d))


# --------------------------------------------------------------------------- BDD code

def build_robdd(table: int, d: int):
    """ROBDD (variable order: local input 0 at the top) as a bottom-up node list.

    Returns (nodes, root) where nodes[i] = (level, low_ref, high_ref) and refs
    0/1 are terminals, ref 2+i is nodes[i]."""
    nodes: list[tuple[int, int, int]] = []
    unique: dict[tuple[int, int, int], int] = {}

    @functools.lru_cache(maxsize=None)
    def mk(level: int, sub: int) -> int:
        # sub: table of the remaining variables level..d-1 (2**(d-level) entries)
        if level == d:
            return sub & 1
        half = 1 << (d - level - 1)
        # variable `level` is the LSB of the remaining local index
        lo_tab = hi_tab = 0
        for y in range(half):
            lo_tab |= ((sub >> (2 * y)) & 1) << y
            hi_tab |= ((sub >> (2 * y + 1)) & 1) << y
        lo, hi = mk(level + 1, lo_tab), mk(level + 1, hi_tab)
        if lo == hi:
            return lo
        key = (level, lo, hi)
        if key not in unique:
            nodes.append(key)
            unique[key] = len(nodes) + 1
        return unique[key]

    root = mk(0, table)
    mk.cache_clear()
    return nodes, root


def encode_bdd(w: BitWriter, rule: Rule, n: int) -> None:
    r = rule.canonical()
    d = r.arity
    write_subset(w, r.inputs, n)
    nodes, root = build_robdd(r.table, d)
    w.gamma(len(nodes) + 1)
    if not nodes:
        w.write(root, 1)
        return
    lw = width_for(d)
    for i, (lev, lo, hi) in enumerate(nodes):
        w.write(lev, lw)
        rw = width_for(i + 2)
        w.write(lo, rw)
        w.write(hi, rw)
    # root is always the last node created (reduced, bottom-up construction)
    if root != len(nodes) + 1:
        raise AssertionError("ROBDD root is not the last node")


def decode_bdd(rd: BitReader, n: int) -> Rule:
    ins = read_subset(rd, n)
    d = len(ins)
    m = rd.gamma() - 1
    if m == 0:
        return Rule(ins, ((1 << (1 << d)) - 1) if rd.read(1) else 0)
    lw = width_for(d)
    nodes = []
    for i in range(m):
        lev = rd.read(lw)
        rw = width_for(i + 2)
        lo, hi = rd.read(rw), rd.read(rw)
        if lev >= d or lo >= i + 2 or hi >= i + 2:
            raise DecodeError("bad BDD node")
        nodes.append((lev, lo, hi))
    table = 0
    for y in range(1 << d):
        ref = m + 1
        while ref >= 2:
            lev, lo, hi = nodes[ref - 2]
            ref = hi if (y >> lev) & 1 else lo
        table |= ref << y
    return Rule(ins, table)


# --------------------------------------------------------------------------- dispatch

def _node_of(rule: Rule, n: int, cache: dict | None = None) -> NodeIndex:
    return from_rule(rule.canonical(), n)


def encode_node(codec: str, rule: Rule, n: int, node: NodeIndex | None = None) -> list[int]:
    w = BitWriter()
    if codec in ("index", "dnf"):
        nd = node if node is not None else _node_of(rule, n)
        (encode_index if codec == "index" else encode_dnf)(w, nd)
    elif codec == "gate":
        encode_gate(w, rule, n)
    elif codec == "circuit":
        encode_circuit(w, rule, n)
    elif codec == "bdd":
        encode_bdd(w, rule, n)
    elif codec == "lut":
        encode_lut(w, rule.canonical(), n)
    elif codec == "full":
        encode_full(w, rule, n)
    else:
        raise SemanticsError(f"unknown codec {codec!r}")
    return w.bits


def decode_node(codec: str, rd: BitReader, n: int) -> Rule:
    if codec in ("index", "dnf"):
        nd = (decode_index if codec == "index" else decode_dnf)(rd, n)
        return nd.to_rule().canonical()
    return {"gate": decode_gate, "circuit": decode_circuit, "bdd": decode_bdd,
            "lut": decode_lut, "full": decode_full}[codec](rd, n).canonical()


def node_bits(codec: str, rule: Rule, n: int, node: NodeIndex | None = None) -> int:
    return len(encode_node(codec, rule, n, node))


@dataclass(frozen=True)
class Archive:
    codec: str
    data: bytes
    header_bits: int
    payload_bits: int
    framing_bits: int

    @property
    def total_bits(self) -> int:
        return len(self.data) * 8


def encode_network(net: Network, codec: str, nodes: list[NodeIndex] | None = None) -> Archive:
    payload = BitWriter()
    for j, r in enumerate(net.rules):
        payload.bits.extend(encode_node(codec, r, net.n, nodes[j] if nodes else None))
    w = BitWriter()
    for b in MAGIC:
        w.write(b, 8)
    w.write(CODEC_IDS[codec], 8)
    w.write(CODEC_VERSION, 8)
    w.gamma(net.n)
    w.delta(len(payload) + 1)
    header_bits = len(w) - 48  # header fields after magic+codec+version
    w.bits.extend(payload.bits)
    pad = (-len(w)) % 8
    w.write(0, pad)
    body = _to_bytes(w.bits)
    crc = zlib.crc32(body)
    data = body + crc.to_bytes(4, "big")
    return Archive(codec, data, header_bits, len(payload), 48 + pad + 32)


def decode_network(data: bytes) -> Network:
    if len(data) < 4 + 2 + 4:
        raise DecodeError("archive too short")
    body, crc = data[:-4], int.from_bytes(data[-4:], "big")
    if zlib.crc32(body) != crc:
        raise DecodeError("CRC mismatch (corrupt or truncated archive)")
    bits = _from_bytes(body)
    rd = BitReader(bits)
    if bytes(rd.read(8) for _ in range(4)) != MAGIC:
        raise DecodeError("bad magic")
    cid = rd.read(8)
    if cid not in CODEC_NAMES:
        raise DecodeError("unknown codec id")
    if rd.read(8) != CODEC_VERSION:
        raise DecodeError("unsupported codec version")
    n = rd.gamma()
    plen = rd.delta() - 1
    start = rd.pos
    end = start + plen
    if end > len(bits):
        raise DecodeError("payload length exceeds archive")
    prd = BitReader(bits, start, end)
    rules = [decode_node(CODEC_NAMES[cid], prd, n) for _ in range(n)]
    if prd.pos != end:
        raise DecodeError("payload not fully consumed (trailing malformed content)")
    rest = bits[end:]
    if len(rest) >= 8 or any(rest):
        raise DecodeError("nonzero padding or trailing bytes")
    return Network(n, tuple(rules))


def _to_bytes(bits: list[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(bits), 8):
        b = 0
        for bit in bits[i:i + 8]:
            b = (b << 1) | bit
        out.append(b)
    return bytes(out)


def _from_bytes(data: bytes) -> list[int]:
    return [(byte >> (7 - i)) & 1 for byte in data for i in range(8)]


# --------------------------------------------------------------------------- generic compressors

def canonical_lut_serialization(net: Network) -> bytes:
    """Canonical serialization of the target object for generic compressors."""
    import json
    c = net.canonical()
    return json.dumps({"n": c.n, "rules": [[list(r.inputs), r.table] for r in c.rules]},
                      separators=(",", ":")).encode()


def generic_bits(net: Network, method: str = "lzma") -> int:
    raw = canonical_lut_serialization(net)
    if method == "lzma":
        return 8 * len(lzma.compress(raw, format=lzma.FORMAT_RAW, filters=[{"id": lzma.FILTER_LZMA2, "preset": 9}]))
    if method == "gzip":
        return 8 * len(gzip.compress(raw, compresslevel=9, mtime=0))
    if method == "raw":
        return 8 * len(raw)
    raise ValueError(method)


def decoder_identity() -> dict:
    """Decoder identity and size (bytes of this module's source, and gzip-9 size) so
    amortized totals can charge the decoder: decoder + sum(payloads)."""
    src = Path(__file__).read_bytes()
    return {"decoder": "causalguard.codec", "codec_version": CODEC_VERSION,
            "sha256": hashlib.sha256(src).hexdigest(), "source_bytes": len(src),
            "gzip_bytes": len(gzip.compress(src, compresslevel=9, mtime=0))}


def _local_import_closure(start: Path) -> list[Path]:
    """Package-local modules transitively imported by ``start`` (AST walk; relative imports only)."""
    import ast
    pkg = start.parent
    seen, todo = [], [start]
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.append(p)
        for node in ast.walk(ast.parse(p.read_text())):
            if isinstance(node, ast.ImportFrom) and node.level == 1:
                if node.module:
                    q = pkg / (node.module.replace(".", "/") + ".py")
                    if q.exists():
                        todo.append(q)
                else:
                    for a in node.names:
                        q = pkg / f"{a.name}.py"
                        if q.exists():
                            todo.append(q)
    return sorted(seen)


def decoder_bundle() -> dict:
    """COMPLETE decoder dependency bundle (repairs R10): every package-local module the decoder imports,
    concatenated deterministically (relative path header + bytes), with its gzip-9 size.  Runtime assumed:
    CPython 3.12 standard library only (no third-party imports in the closure; checked by
    tests/test_codec_bundle.py, which runs the bundle in an isolated interpreter)."""
    mods = _local_import_closure(Path(__file__).resolve())
    blob = b"".join(b"# file: " + m.name.encode() + b"\n" + m.read_bytes() for m in mods)
    return {"modules": [m.name for m in mods], "bundle_sha256": hashlib.sha256(blob).hexdigest(),
            "source_bytes": len(blob), "gzip_bytes": len(gzip.compress(blob, compresslevel=9, mtime=0)),
            "runtime": "CPython 3.12 standard library (+ package __init__ stub)",
            "codec_version": CODEC_VERSION}


ALL_NODE_CODECS = ("index", "dnf", "gate", "circuit", "bdd", "lut", "full")

__all__ = ["encode_network", "decode_network", "node_bits", "encode_node", "decode_node", "Archive",
           "DecodeError", "generic_bits", "decoder_identity", "decoder_bundle", "ALL_NODE_CODECS", "circuit_formula",
           "build_robdd", "rank_subset", "unrank_subset", "itertools"]
