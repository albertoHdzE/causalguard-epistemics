# Codec specification v1 (`causalguard.codec`, CODEC_VERSION = 1)

All reported description lengths are **lengths of written bitstrings** that the matching decoder reconstructs exactly (round-trip tested on random networks for every codec). Every codec encodes the same target object: the network function F : {0,1}ⁿ → {0,1}ⁿ (canonical form: each node restricted to its essential inputs). Field widths: `w(c) = ⌈log₂ c⌉` (0 if c ≤ 1). `subset(S)` = |S| in w(n+1) bits + colex rank of S among C(n,|S|) in w(C(n,|S|)) bits. γ = Elias gamma, δ = Elias delta.

| codec | per-node code | notes |
|---|---|---|
| `index` | polarity(1) · γ(m+1) · per family: subset(fixed coords) · one value bit per fixed coord | the schema/offset-family representation; don't-cares include connected inputs; polarity 0 encodes the off-set (NAND = complement of AND); cover = exact minimum (count, literals) under a 20k-node branch-and-bound budget, `exact_cover` flag recorded |
| `dnf` | polarity(1) · γ(m+1) · per term: γ(k+1) · per literal: coordinate w(n) + value(1) | same cover as `index`; literal-wise coordinate coding |
| `gate` | catalogue id(4) · subset(inputs) · params | catalogue: CONST0/1, COPY, NOT, AND, OR, NAND, NOR, XOR, XNOR, IMPLIES/NIMPLIES(antecedent bit), MAJORITY, KOFN(t), LUT fallback (2^d table bits) |
| `circuit` | subset(inputs) · prefix formula: LEAF `0`+w(d), NOT `100`, AND `101`, OR `110`, XOR `111` (d = 0: one constant bit) | exhaustive minimum for d ≤ 3; for d > 3 the shortest of three declared constructions (DNF, NOT-of-off-set DNF, XOR chain for parity) — an upper bound, flagged |
| `bdd` | subset(inputs) · γ(#nodes+1) · bottom-up nodes: level w(d), low/high refs w(i+2) | ROBDD over local inputs in ascending order; one fixed order (declared budget) |
| `lut` | subset(inputs) · 2^d table bits | literal local truth table |
| `full` | 2ⁿ bits | literal repertoire column; n ≤ 16 in S1 |

Generic comparators (`generic_lzma`, `generic_gzip`, `generic_raw`): 8 × byte length of LZMA2(preset 9, raw) / gzip-9 / raw of the canonical JSON serialization of the same canonical network.

## Archive framing
`'CGA1'`(32) · codec id(8) · version(8) · γ(n) · δ(payload bits + 1) · payload · zero padding to a byte · CRC-32 (32) over all preceding bytes. Decoding **rejects**: bad magic/version/codec id, CRC mismatch, truncation, payload not consumed exactly, nonzero padding, trailing bytes (tests: `tests/test_codec.py`). `archive_bits = 8·len(bytes)`; `payload_bits`, `header_bits`, `framing_bits` are reported separately.

## Accounting and claims
- Per-object payload bits and amortized totals `decoder + Σ payloads` are reported; the decoder is charged as the gzip-9 size of `codec.py` (`decoder_identity()`: sha256, source bytes, gzip bytes).
- With a fixed decoder P, each archive length is an upper bound `K(x | P) ≤ len + O(1)`; with a universal interpreter, `K_U(x) ≤ len(P) + len + c_U`. **These are upper bounds; ordering two bounds does not order the true Kolmogorov complexities**, and no shortest-possible claim is made.
- Selection in S2 uses per-node payload lengths only (header is common to all candidates of a world, so it does not change rankings).
- Two-part MDL (noise stress only): L(M) = index payload of the node; L(D|M) = γ(e+1) + e·w(N_j) bits (positions of mismatching observations of node j among its N_j observations; values implied by flipping). Exactly reconstructs the observed bits given the observation inputs.

## Worked round trip
```python
from causalguard.schema import Network, Rule
from causalguard.codec import encode_network, decode_network
r110 = Rule((0, 1, 2), 110)                   # Rule 110: with inputs (right, centre, left) = nodes (0, 1, 2) the local table IS the Wolfram number
net = Network(3, (r110, Rule((0,), 2), Rule((1,), 2)))
a = encode_network(net, "index")
assert decode_network(a.data).canonical() == net.canonical()
print(a.payload_bits, a.total_bits)           # exact integer bit counts
```
