# S4 family / cost table (development, offline)

Sources: `reports/development_r4/s4_map_summary.json` (run `s4-map-dev-v2`, 20 worlds/stratum, n = 8, k = 3) and `s4_stress_summary.json` (run `s4-stress-dev-v2`). Medians over worlds. Description lengths are of the HIDDEN mechanism (evaluator-side; complete serialized codes in each language; upper bounds in that language, not K). Replay wall times were measured while other jobs ran (contended; indicative only); the authoritative scaling numbers are the stress table.

## Description length of the hidden mechanism (bits, median) and CGH-1 mode chosen

| family | flat index | gate | circuit | LUT | CGH-1 flat (analytic, no hierarchy) | CGH-1 no-order | CGH-1 no-analytic | CGH-1 full | full mode (worlds) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| bounded_random | 324 | 272 | 328 | 240 | 161 | 161 | 142 | 161 | flat 20 |
| canalizing | 244 | 240 | 284 | 224 | 121 | 121 | 124 | 121 | flat 20 |
| order_disrupted | 288 | 280 | 316 | 248 | 139 | 77 | 78 | 77 | dict 20 |
| ordered_motif | 288 | 280 | 316 | 248 | 139 | 98 | 36 | 35 | template 20 |
| parity | 456 | 208 | 284 | 228 | 125 | 114 | 116 | 114 | dict 20 |
| repeated_modules | 276 | 248 | 296 | 224 | 131 | 121 | 79 | 81 | module 20 |
| sparse_conj | 220 | 204 | 248 | 208 | 107 | 107 | 109 | 107 | flat 18, dict 2 |
| uniform_H | 336 | 280 | 352 | 248 | 175 | 175 | 147 | 175 | flat 20 |

Flat-index/gate/circuit/LUT figures are `codec.encode_network` complete archives (they include a byte-level envelope, CGH-1 does not use one: compare within the CGH-1 columns, and use the others for ordering only).

## Verdict mix, version-space size and replay cost at evidence budget 12 and 16

| family | B | entailed | refuted | underdetermined | median log10 |V(D)| | replay s (B / C / D), 8 claims | median structured models in V(D) |
|---|---:|---:|---:|---:|---:|---|---:|
| bounded_random | 12 | 9 | 14 | 137 | 8.4 | 0.08 / 0.42 / 0.63 | 0 |
| bounded_random | 16 | 33 | 34 | 93 | 4.7 | 0.06 / 0.35 / 0.14 | 0 |
| canalizing | 12 | 5 | 3 | 152 | 11.5 | 0.11 / 0.32 / 0.80 | 0 |
| canalizing | 16 | 25 | 22 | 113 | 6.7 | 0.08 / 0.22 / 0.17 | 0 |
| order_disrupted | 12 | 10 | 7 | 143 | 9.4 | 0.08 / 0.46 / 0.72 | 0 |
| order_disrupted | 16 | 31 | 32 | 97 | 5.7 | 0.06 / 0.34 / 0.14 | 0 |
| ordered_motif | 12 | 9 | 8 | 143 | 9.7 | 0.08 / 0.38 / 0.53 | 36 |
| ordered_motif | 16 | 24 | 27 | 109 | 5.9 | 0.06 / 0.36 / 0.14 | 2 |
| parity | 12 | 12 | 12 | 136 | 7.2 | 0.05 / 0.35 / 0.41 | 0 |
| parity | 16 | 29 | 28 | 103 | 4.4 | 0.05 / 0.33 / 0.12 | 0 |
| repeated_modules | 12 | 10 | 7 | 143 | 10.1 | 0.08 / 0.27 / 0.57 | 24 |
| repeated_modules | 16 | 35 | 28 | 97 | 6.0 | 0.06 / 0.26 / 0.15 | 2 |
| sparse_conj | 12 | 8 | 3 | 149 | 12.8 | 0.12 / 0.47 / 1.32 | 0 |
| sparse_conj | 16 | 20 | 12 | 128 | 8.8 | 0.09 / 0.38 / 0.57 | 0 |
| uniform_H | 12 | 10 | 10 | 140 | 8.1 | 0.06 / 0.39 / 0.57 | 0 |
| uniform_H | 16 | 28 | 21 | 111 | 5.0 | 0.05 / 0.38 / 0.14 | 0 |

Fixed-request replay agreement B = C = D: 5120/5120 claims (all prefixes).

## Scaling (random bounded networks, k = 3, 16 one-step observations, 4 claims with h <= 2, 300 s cap per item, 3 seeds)

| n | backend | claims answered | items over cap | median item wall s |
|---:|---|---:|---:|---:|
| 8 | B | 12/12 | 0 | 1.82 |
| 8 | C | 12/12 | 0 | 1.78 |
| 8 | D | 12/12 | 0 | 0.02 |
| 10 | B | 12/12 | 0 | 3.97 |
| 10 | C | 12/12 | 0 | 3.91 |
| 10 | D | 12/12 | 0 | 0.03 |
| 12 | B | 12/12 | 0 | 0.35 |
| 12 | C | 0/12 | 0 | 0.0 |
| 12 | D | 12/12 | 0 | 0.09 |
| 16 | B | 12/12 | 0 | 1.16 |
| 16 | C | 0/12 | 0 | 0.0 |
| 16 | D | 12/12 | 0 | 0.16 |
| 20 | B | 12/12 | 0 | 3.54 |
| 20 | C | 0/12 | 0 | 0.0 |
| 20 | D | 12/12 | 0 | 0.57 |
| 24 | B | 12/12 | 0 | 6.07 |
| 24 | D | 12/12 | 0 | 0.48 |
| 32 | B | 12/12 | 0 | 21.3 |
| 32 | D | 12/12 | 0 | 2.15 |
| 48 | B | 12/12 | 0 | 116.5 |
| 48 | D | 12/12 | 0 | 12.78 |
| 64 | B | 4/12 | 2 | 254.18 |
| 64 | D | 12/12 | 0 | 24.64 |

B = generic CNF/SAT with sequential-counter at-most-one (verdicts only above n = 10; explicit counts at n <= 10); C = flat explicit workspace (materialization refused above n = 10 by declaration); D = support-schema mechanism space (verdicts and exact counts). Stress v1 (pairwise AMO, B timed out at n >= 32) is preserved in `s4_stress_summary.json` and is NOT used as evidence of a D advantage (DECISIONS D49). Agreement where both finished: {'agree': 100, 'disagree': 0}.
