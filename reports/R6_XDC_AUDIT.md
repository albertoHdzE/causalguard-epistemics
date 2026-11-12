# R6 Track X — independent audit of XDC

Auditor: Claude Opus (implementation agent), 2026-11-12. Code audited: commit `f640e70` (`r5/priors.py::XDC`,
`_partition_mass`, `GSR._phi` refactor, `forecast.predict_public`, `analysis.analyze_g_r6`). Derivation:
`docs/R6_XDC_DERIVATION.md`. This is an implementation-agent audit; the reviewer decides acceptance.

## Verdict

**No defect that changes a forecast was found.** The existing R6 runs stand; no `-v2` rerun is needed.
Two interface notes and one test-coverage note follow; none changes a number.

## Oracle design (`tests/test_r6_xdc_oracle.py`)

Shares no code with `XDC`, `GSR`, `xdc_bruteforce`, `rule_type`, `_partition_mass`, `versionspace` or `reference`.
It enumerates its own rule space (essential-input check written from scratch), computes types as the orbit of the
table under input permutations (a different representation from `rule_type`'s minimum table), runs its own
simulator for evidence and queries, and assigns each mechanism its prior mass by the **closed-form Polya-urn
formula** (derivation §3) — no seating enumeration and no subset recursion. It then enumerates every mechanism
whose nodes fit the evidence and conditions. The only package imports are input data types and the base code's
per-rule bit lengths (`codec.node_bits` for gate, `s4.hcode.flat_node_bits` for cgh_flat), which are inputs to
XDC, not part of the sharing step.

## Results

| Check | Cases | Result |
|---|---|---|
| XDC vs oracle, theta in {0.5, 2, 8, inf} and the mixture, bases gate and cgh_flat | 216 (54 each of H(3,1), H(3,2), H(4,1), H(4,2)); h = 1 and 2; none / persistent_clamp / initial_edit queries and evidence | largest absolute difference **2.9e-12** (per class: 2.0e-15, 3.3e-13, 1.2e-15, 2.9e-12) |
| Cases where sharing matters (\|P_0.5 − P_inf\| > 1e-4) | 142 of 216 | — |
| Prior normalisation, closed form summed over all of H(3,1) | 4 thetas × 2 bases | total 1 within 1e-12 |
| Exchangeability: random node relabelling of evidence and query | 60 per base, ≥ 50 non-empty | every forecast (mixture and four thetas) unchanged within 1e-9 |
| Planted defect: (\|b\|−1)! dropped in a copy of the recursion, patched in | 24 | **12 of 24 cases fail**, largest difference 0.19 (test asserts failure) |

Tests: `pytest tests/test_r6_xdc_oracle.py` — 5 passed (about 33 s). Reproduce the table:
`python tests/test_r6_xdc_oracle.py 216`.

## Event order (git and run records)

| Event | Time (UTC) | Commit |
|---|---|---|
| XDC implementation `f640e70` | 00:59:13 | — |
| `r6-g-cal-v1`, `r6-g-ext-dev-v1` (pre-lock development, declared in the lock) | from 00:59:13 | `f640e70` |
| Lock commit `246d3cd` (`docs/R6_DESIGN_LOCK.json`) | 01:05:01 | — |
| `r6-g-eval-v1` open / start (320 attempts, 320 ok) | 01:05:01 | `246d3cd`, clean tree |
| `r6-g-ext-fresh-v1` open / start (449 attempts, 449 ok) | 01:12:10 | `246d3cd`, clean tree |
| Delegation commit `19643dd` | 01:07:34 | docs only |

`git diff --stat 246d3cd 19643dd -- src scripts configs` is empty: no predictor code changed after the lock. Each
evaluation run has exactly one attempt per planned item (no reruns, no retries).

## Notes (no forecast changed)

- **X-N1 (interface).** `XDC.probabilities` returns P(target node = 1) whatever the literal's value; the caller
  `forecast._node_prob` refuses value-0 literals, so the R6 records are correct. My first oracle comparison flagged
  this as a 1 − p mismatch on value-0 targets; any future caller must convert. Documented in the derivation §10.
- **X-N2 (test coverage).** The author's test covered one evidence set in H(3, 1) (24 checks). The oracle above
  extends this to k = 2, n = 4, both bases, all intervention kinds in evidence and queries.
- **X-N3 (float).** No interval arithmetic; the a-priori bound for nonnegative sums is below 1.5e-13 relative at
  n = 8 (derivation §9), well inside the declared 1e-9.

## Method-level observations for the reviewer (not defects)

- The prior is exchangeable over nodes and shares only types, not supports. On the n = 8 external fragments 31 %
  of nodes are constants (outside regulators clamped to 0), which share the arity-0 type trivially; mean hidden
  reuse is 3.7 per instance but 2.3 among non-constant nodes. Part of "reuse" on that panel is an artefact of
  the transformation.
- The lock predicted "at or above 0.02" for the synthetic primary; see `reports/R6_GENERALIZATION.md`.
