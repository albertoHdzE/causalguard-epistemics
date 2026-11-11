"""CGH-1: a fully charged hierarchical/analytic code for bounded-indegree MECHANISMS (networks).

Versioned format of this repository (not a HID-v1 archive: HID-v1 describes finite bit strings; CGH-1 describes
networks).  It ports HID's ideas of explicit ordering, ordered repetition (REPEAT), shared references to one
rule definition, and PATCH exceptions, and the formal paper's analytic gate families as rule vocabulary.  Every
field below is serialized and counted; nothing is implicit except this specification and the decoder.

    archive  := variant:4  gamma(n)  gamma(k+1)  ordering:1(=0, LSB local order; 1 reserved)  mode:2  body
    mode 0 FLAT     := NODE^n
    mode 1 DICT     := gamma(q) LOCAL^q  ( ref:width_for(q) SUPPORT(arity of ref) )^n
    mode 2 TEMPLATE := LOCAL  OFFSETS(arity)  PATCHES          node i: LOCAL on {(i+o) mod n : o in OFFSETS}
    mode 3 MODULE   := gamma(m)  (LOCAL OFFSETS)^m  PATCHES      m | n, 1 < m < n; node b*m+p: module p on
                                                                {(b*m+o) mod n : o in OFFSETS_p}
    PATCHES  := gamma(np+1) ( node:width_for(n)  NODE )^np        strictly increasing node ids
    NODE     := LOCAL SUPPORT(arity)
    LOCAL    := arity:width_for(k+1)  [id:width_for(|CAT_d|+1)]  [table:2^arity if id = LUT]
    SUPPORT(d) := rank:width_for(C(n,d))       (colex rank of an ascending d-subset)
    OFFSETS(d) := rank:width_for(C(n,d))       (ascending offset set; local input t <-> t-th smallest offset)

Variants (declared languages; the decoder reads the variant nibble): 0 full; 1 flat (mode 0 only, analytic
vocabulary); 2 no_order (modes 0-1: sharing without ordered templates/modules); 3 no_analytic (all modes, LOCAL
without an id field: every rule is a LUT).  The encoder is a bounded deterministic search; its output is the
CANONICAL description of a mechanism (one per mechanism) and an upper bound on code length in this language,
never a minimum or a Kolmogorov complexity.
"""
from __future__ import annotations

import functools
import math
from collections import Counter

from ..codec import BitReader, BitWriter, DecodeError, rank_subset, unrank_subset, width_for
from ..schema import Network, Rule
from .analytic import Gate, gate_to_rule

VARIANTS = {"full": 0, "flat": 1, "no_order": 2, "no_analytic": 3}
VARIANT_MODES = {0: (0, 1, 2, 3), 1: (0,), 2: (0, 1), 3: (0, 1, 2, 3)}
MAX_K = 4


@functools.lru_cache(maxsize=None)
def local_catalogue(d: int) -> tuple[tuple[str, int], ...]:
    """Named analytic tables over d ordered local inputs (LSB local order), deduplicated by table, first name
    kept.  Families from the formal paper's Proposition (gate-family one-sets)."""
    out: dict[int, str] = {}

    def add(name, g):
        r = gate_to_rule(g, d)                     # built from the gate's analytic one-set
        t = r.table if r.inputs == tuple(range(d)) else _expand(r, d)
        out.setdefault(t, name)
    if d == 0:
        return (("CONST0", 0), ("CONST1", 1))
    if d == 1:
        add("COPY", Gate("COPY", (1,), (1,)))
        add("NOT", Gate("NOT", (1,), (1,)))
        return tuple((nm, t) for t, nm in out.items())
    I = tuple(range(1, d + 1))
    for f in ("AND", "OR", "NAND", "NOR", "XOR", "XNOR", "MAJORITY_STRICT"):
        add(f, Gate(f, I))
    for k in range(1, d + 1):
        add(f"KOFN{k}", Gate("KOFN", I, (k,)))
    for k in range(d + 1):
        add(f"EXACTK{k}", Gate("EXACTK", I, (k,)))
    if d == 2:
        for a, b in ((1, 2), (2, 1)):
            add(f"IMPLIES{a}{b}", Gate("IMPLIES", (a, b), (a, b)))
            add(f"NIMPLIES{a}{b}", Gate("NIMPLIES", (a, b), (a, b)))
    for r in I:
        rest = tuple(i for i in I if i != r)
        for fb_name, fb_table in local_catalogue(d - 1):
            fb = _table_gate(fb_table, rest)
            for cv in (0, 1):
                for o in (0, 1):
                    add(f"CANAL{r}{cv}{o}[{fb_name}]", Gate("CANALIZING", I, (r, cv, o, fb)))
    return tuple((nm, t) for t, nm in out.items())


def _expand(r: Rule, d: int) -> int:
    """Table of r over local inputs 0..d-1 (r's inputs are a subset)."""
    t = 0
    for y in range(1 << d):
        z = sum(((y >> i) & 1) << s for s, i in enumerate(r.inputs))
        t |= r.local_value(z) << y
    return t


def _table_gate(table: int, inputs: tuple[int, ...]) -> Gate:
    """A fallback gate given by an explicit local table (analytic.AUX_FAMILIES, for canalizing recursion)."""
    return Gate("TABLE", inputs, (table,))


def cat_index(d: int) -> dict[int, int]:
    return {t: i for i, (_, t) in enumerate(local_catalogue(d))}


# --------------------------------------------------------------------------- local records

def _w_local(w: BitWriter, d: int, table: int, k: int, analytic: bool) -> None:
    w.write(d, width_for(k + 1))
    if analytic:
        cat = local_catalogue(d)
        idx = cat_index(d).get(table)
        w.write(len(cat) if idx is None else idx, width_for(len(cat) + 1))
        if idx is not None:
            return
    w.write(table, 1 << d)


def _r_local(rd: BitReader, k: int, analytic: bool) -> tuple[int, int]:
    d = rd.read(width_for(k + 1))
    if d > k:
        raise DecodeError("local arity exceeds k")
    if analytic:
        cat = local_catalogue(d)
        i = rd.read(width_for(len(cat) + 1))
        if i < len(cat):
            return d, cat[i][1]
        if i > len(cat):
            raise DecodeError("unknown catalogue id")
    return d, rd.read(1 << d)


def _local_bits(d: int, table: int, k: int, analytic: bool) -> int:
    b = width_for(k + 1)
    if analytic:
        cat = local_catalogue(d)
        b += width_for(len(cat) + 1)
        if table in cat_index(d):
            return b
    return b + (1 << d)


def _w_subset_fixed(w: BitWriter, S: tuple[int, ...], n: int) -> None:
    w.write(rank_subset(S, n), width_for(math.comb(n, len(S))))


def _r_subset_fixed(rd: BitReader, d: int, n: int) -> tuple[int, ...]:
    return unrank_subset(rd.read(width_for(math.comb(n, d))), d, n)


# --------------------------------------------------------------------------- relative (template) rules

def offset_rule(base: int, offsets: tuple[int, ...], table: int, n: int) -> Rule:
    """Rule of a node whose t-th local input is node (base + offsets[t]) mod n (offsets ascending)."""
    absn = [(base + o) % n for o in offsets]
    ins = tuple(sorted(absn))
    pos = [ins.index(a) for a in absn]
    t = 0
    for y in range(1 << len(ins)):
        z = sum(((y >> pos[s]) & 1) << s for s in range(len(offsets)))
        t |= ((table >> z) & 1) << y
    return Rule(ins, t).canonical()


def signature(rule: Rule, base: int, n: int) -> tuple[tuple[int, ...], int]:
    """(ascending offsets relative to base, local table in offset order) of a canonical rule."""
    r = rule.canonical()
    offs = sorted(((i - base) % n, i) for i in r.inputs)
    order = [r.inputs.index(i) for _, i in offs]
    t = 0
    for z in range(1 << r.arity):
        y = sum(((z >> s) & 1) << order[s] for s in range(r.arity))
        t |= r.local_value(y) << z
    return tuple(o for o, _ in offs), t


def _local_table(rule: Rule) -> tuple[int, int]:
    r = rule.canonical()
    return r.arity, r.table


# --------------------------------------------------------------------------- encoder

def _node_bits(rule: Rule, n: int, k: int, analytic: bool) -> int:
    d, t = _local_table(rule)
    return _local_bits(d, t, k, analytic) + width_for(math.comb(n, d))


def flat_node_bits(rule: Rule, n: int, k: int, variant: str = "flat") -> int:
    """Per-node cost of a FLAT-mode NODE record (used by the nodewise-additive part of the prior)."""
    return _node_bits(rule, n, k, VARIANTS[variant] != 3)


def header_bits(n: int, k: int) -> int:
    return 4 + _gamma_len(n) + _gamma_len(k + 1) + 1 + 2


def _gamma_len(x: int) -> int:
    return 2 * x.bit_length() - 1


def _patch_bits(patches: list[int], net: Network, n: int, k: int, analytic: bool) -> int:
    return _gamma_len(len(patches) + 1) + sum(width_for(n) + _node_bits(net.rules[i], n, k, analytic)
                                              for i in patches)


def _plans(net: Network, k: int, variant: int):
    """All candidate descriptions (mode, bits, plan) of a network under a variant."""
    n = net.n
    analytic = variant != 3
    if not (0 <= k <= min(n, MAX_K)):
        raise ValueError("declared k out of range (0 <= k <= min(n, 4))")
    rules = [r.canonical() for r in net.rules]
    if any(r.arity > k for r in rules):
        raise ValueError("network outside the declared class (indegree > k)")
    H = header_bits(n, k)
    modes = VARIANT_MODES[variant]
    yield 0, H + sum(_node_bits(r, n, k, analytic) for r in rules), ("flat",)
    if 1 in modes:
        locs = list(dict.fromkeys(_local_table(r) for r in rules))
        q = len(locs)
        b = H + _gamma_len(q) + sum(_local_bits(d, t, k, analytic) for d, t in locs)
        b += sum(width_for(q) + width_for(math.comb(n, r.arity)) for r in rules)
        yield 1, b, ("dict", locs)
    if 2 in modes:
        sigs = [signature(r, i, n) for i, r in enumerate(rules)]
        for sig in dict.fromkeys(sigs):
            offs, t = sig
            patches = [i for i in range(n) if sigs[i] != sig]
            b = H + _local_bits(len(offs), t, k, analytic) + width_for(math.comb(n, len(offs)))
            b += _patch_bits(patches, net, n, k, analytic)
            yield 2, b, ("template", sig, patches)
    if 3 in modes:
        for m in range(2, n):
            if n % m:
                continue
            mods = []
            patches = []
            for p in range(m):
                sigs = [signature(rules[b * m + p], b * m, n) for b in range(n // m)]
                best = Counter(sigs).most_common()
                top = max(c for _, c in best)
                sig = next(s for s in sigs if Counter(sigs)[s] == top)      # first most common (deterministic)
                mods.append(sig)
                patches += [b * m + p for b in range(n // m) if sigs[b] != sig]
            patches.sort()
            b = H + _gamma_len(m) + sum(_local_bits(len(o), t, k, analytic) + width_for(math.comb(n, len(o)))
                                        for o, t in mods)
            b += _patch_bits(patches, net, n, k, analytic)
            yield 3, b, ("module", m, mods, patches)


def describe(net: Network, k: int, variant: str = "full") -> tuple[int, int, tuple]:
    """Canonical description: (bits, mode, plan) = minimum over this variant's plans, ties by plan order."""
    v = VARIANTS[variant]
    best = None
    for mode, b, plan in _plans(net, k, v):
        if best is None or b < best[0]:
            best = (b, mode, plan)
    return best


def encode(net: Network, k: int, variant: str = "full") -> list[int]:
    v = VARIANTS[variant]
    analytic = v != 3
    n = net.n
    rules = [r.canonical() for r in net.rules]
    _, mode, plan = describe(net, k, variant)
    w = BitWriter()
    w.write(v, 4)
    w.gamma(n)
    w.gamma(k + 1)
    w.write(0, 1)
    w.write(mode, 2)

    def node(r):
        d, t = _local_table(r)
        _w_local(w, d, t, k, analytic)
        _w_subset_fixed(w, r.inputs, n)

    def patches(ps):
        w.gamma(len(ps) + 1)
        for i in ps:
            w.write(i, width_for(n))
            node(rules[i])
    if mode == 0:
        for r in rules:
            node(r)
    elif mode == 1:
        locs = plan[1]
        w.gamma(len(locs))
        for d, t in locs:
            _w_local(w, d, t, k, analytic)
        idx = {lt: i for i, lt in enumerate(locs)}
        for r in rules:
            w.write(idx[_local_table(r)], width_for(len(locs)))
            _w_subset_fixed(w, r.inputs, n)
    elif mode == 2:
        (offs, t), ps = plan[1], plan[2]
        _w_local(w, len(offs), t, k, analytic)
        _w_subset_fixed(w, offs, n)
        patches(ps)
    else:
        m, mods, ps = plan[1], plan[2], plan[3]
        w.gamma(m)
        for offs, t in mods:
            _w_local(w, len(offs), t, k, analytic)
            _w_subset_fixed(w, offs, n)
        patches(ps)
    assert len(w) == describe(net, k, variant)[0], "field ledger disagrees with transmitted bits"
    return w.bits


def decode(bits: list[int]) -> tuple[Network, int, dict]:
    """Exact decoder; consumes the whole bitstream.  Returns (network, k, info)."""
    rd = BitReader(bits)
    v = rd.read(4)
    if v not in VARIANT_MODES:
        raise DecodeError("unknown variant")
    analytic = v != 3
    n = rd.gamma()
    k = rd.gamma() - 1
    if not (0 <= k <= min(n, MAX_K)):
        raise DecodeError("declared k out of range")
    if rd.read(1) != 0:
        raise DecodeError("ordering bit 1 (MSB) is reserved in CGH-1")
    mode = rd.read(2)
    if mode not in VARIANT_MODES[v]:
        raise DecodeError(f"mode {mode} not allowed in variant {v}")

    def node():
        d, t = _r_local(rd, k, analytic)
        S = _r_subset_fixed(rd, d, n)
        return Rule(S, t).canonical()

    def read_patches(rules):
        npt = rd.gamma() - 1
        last = -1
        for _ in range(npt):
            i = rd.read(width_for(n))
            if i <= last or i >= n:
                raise DecodeError("patch nodes must be strictly increasing and < n")
            last = i
            rules[i] = node()
    if mode == 0:
        rules = [node() for _ in range(n)]
    elif mode == 1:
        q = rd.gamma()
        locs = [_r_local(rd, k, analytic) for _ in range(q)]
        rules = []
        for _ in range(n):
            i = rd.read(width_for(q))
            if i >= q:
                raise DecodeError("dictionary reference out of range")
            d, t = locs[i]
            rules.append(Rule(_r_subset_fixed(rd, d, n), t).canonical())
    elif mode == 2:
        d, t = _r_local(rd, k, analytic)
        offs = _r_subset_fixed(rd, d, n)
        rules = [offset_rule(i, offs, t, n) for i in range(n)]
        read_patches(rules)
    else:
        m = rd.gamma()
        if not (1 < m < n and n % m == 0):
            raise DecodeError("module size must divide n with 1 < m < n")
        mods = []
        for _ in range(m):
            d, t = _r_local(rd, k, analytic)
            mods.append((_r_subset_fixed(rd, d, n), t))
        rules = [offset_rule(b * m, mods[p][0], mods[p][1], n) for b in range(n // m) for p in range(m)]
        # offset_rule with base b*m gives inputs relative to the BLOCK start, as specified
        read_patches(rules)
    if rd.pos != len(bits):
        raise DecodeError("trailing bits")
    if any(r.arity > k for r in rules):
        raise DecodeError("decoded rule exceeds declared k")
    return Network(n, tuple(rules)), k, {"variant": v, "mode": mode, "bits": len(bits)}


def bits(net: Network, k: int, variant: str = "full") -> int:
    return describe(net, k, variant)[0]
