# S4 development report (iteration 4)

2026-11-11. Pre-sprint development evidence: no confirmation, no freeze, no main study. The world is the unit
throughout. Intervals are stratified paired cluster bootstrap 95% (10,000 replicates, seed 20261111) unless
stated. Sources are under `reports/development_r4/`. Repair validation (P0) is reported separately in §1 and
must not be read as S4 evidence.

## 0. One-paragraph summary

We implemented the broader method: a complete, compact account of all compatible mechanisms; the formal paper's
analytic calculus; a fully charged hierarchical code; a check-before-release gate; and exact experiment
selection. We compared it against a generic SAT workspace and the flat index workspace.

- **Correctness.** All exact backends agree on every claim tested (5,120 + 100 + 80 targets).
- **Cost and capability.** With a competent generic SAT encoding, our representation is ≈9× faster at n = 48
  (h ≤ 2) and still answers at n = 64 where SAT misses its cap. It also gives exact counts, which SAT lacks
  above n = 10.
- **LLM pilot (2 models × 40 worlds).** Tools raise verdict accuracy by +35 to +36 points over the unaided
  model. **D − B is an exact tie**, as predicted. The gate blocked every wrong unaided proposal and never
  verified a wrong one.
- **The representation changes answers only through its prior, and only where the world has ordered or shared
  structure.** The hierarchical prior improves forecasts on underdetermined claims by +4.9 points over the same
  code without hierarchy (all from the two structure-matched families) and by +8.9 over uniform averaging. The
  AI models do not use the exact probabilities they are given: a no-LLM controller forecasts better than every
  AI arm.

## 1. P0 repairs (separately reviewable; `reports/development_r4/p0_repair_evidence.json`)

| Defect | Repair | Evidence |
|---|---|---|
| R3-01 planned method keys / denominators | keys from the study contract; exact key set per row; state-dependent nulls; no first-row inference; contrasts refuse instead of dropping a world | 15 new tests (first/middle/last omissions, nonempty null, empty-V, noise cells). Reanalysis of saved S2 records: per-world CSV byte-identical; summary JSON 0 differences; primary +0.000875 [−0.0111, +0.0121], N = 250, unchanged |
| R3-02 work after supervisor death | synchronous refusal after the workers lock and before every payload; watchdog kept | 9 new tests (immediate side effect ×5, late start after drain + completing resume, no false positive, mid-payload kill). Reviewer repro 0/5 markers (was 5/5) |

Full suite after P0: 243 passed. No large experiment was rerun.

## 2. What was implemented (method identity: `docs/S4_METHOD_COVERAGE.md`)

`src/causalguard/s4/`:

- `analytic` (formal-paper calculus);
- `mechspace` (arm D's representation of V(D));
- `hcode` (CGH-1);
- `workspace` (one API, B/C/D);
- `checking` (gate);
- `tasks`, `evaluator`, `prior`, `offline`, `pilot`, `demo`.

All are new, independent implementations; no upstream code was copied. The generic SAT owner (`versionspace`)
was enriched with exact weighted counts and a sequential-counter at-most-one encoding. Historical defaults are
unchanged.

## 3. Offline family map (`s4-map-dev-v2`: 8 strata × 20 worlds, n = 8, k = 3, nested evidence 8/12/16/24)

`s4-map-dev-v1` is preserved. Its 16/160 failures were refusals by the exactness guard (float64 range of code
weights; D48), not errors in reported values.

- **Replay agreement B = C = D:** 5,120/5,120 claims.
- **Verdict mix** at 12 / 16 observations: underdetermined 85–95% / 58–80% of claims, depending on family. The
  "always underdetermined" baseline is therefore strong. Full table: `reports/S4_FAMILY_COST_TABLE.md`.
- **Description length of the hidden mechanism** (evaluator side; CGH-1 complete codes; upper bounds in one
  language):
  - ordered_motif: full 35 bits vs flat analytic 139 (template mode in 20/20 worlds);
  - repeated_modules: 81 vs 131 (module mode 20/20);
  - order_disrupted: 77 vs 139 (shared dictionary 20/20);
  - parity: 114 vs flat index 456 bits, where the flat codec's XOR weakness does not carry over to the analytic
    vocabulary;
  - uniform_H: 175 full vs 147 with no analytic ids. The analytic id field costs bits on random functions; the
    code is not universally shorter.

### 3.1 Codec-induced averaging secondary (underdetermined claims; forecast of the hidden outcome)

World-level accuracy; ties score 0.5.

| Contrast (accuracy) | B = 8 | B = 12 | B = 16 | B = 24 |
|---|---|---|---|---|
| cgh_prior − uniform | +0.061 [0.041, 0.081] | +0.089 [0.064, 0.115] | +0.102 [0.075, 0.129] | +0.116 [0.078, 0.154] |
| cgh_prior − flat index | +0.084 [0.064, 0.105] | +0.116 [0.088, 0.144] | +0.078 [0.054, 0.103] | +0.068 [0.037, 0.101] |
| cgh_prior − cgh_flat (hierarchy) | +0.050 [0.038, 0.062] | +0.049 [0.036, 0.063] | +0.040 [0.025, 0.055] | +0.026 [0.012, 0.041] |
| cgh_flat − cgh_flat_noanalytic (analytic vocabulary) | +0.003 [−0.008, 0.015] | +0.017 [−0.001, 0.035] | +0.021 [0.009, 0.034] | +0.021 [0.001, 0.042] |
| flat index − uniform | −0.024 [−0.045, −0.003] | −0.026 [−0.049, −0.004] | +0.024 [−0.002, 0.051] | +0.047 [0.005, 0.090] |
| shortest cgh_prior model − uniform | +0.031 [0.006, 0.057] | +0.056 [0.027, 0.084] | +0.077 [0.047, 0.108] | +0.095 [0.046, 0.146] |
| worlds / claims | 160 / 1,259 | 160 / 1,143 | 160 / 851 | 134 / 427 |

**Attribution, per family (B = 16, accuracy).**

| Family | uniform | flat index | circuit | cgh_flat | cgh_prior |
|---|---:|---:|---:|---:|---:|
| ordered_motif | 0.776 | 0.834 | 0.785 | 0.821 | **1.000** |
| repeated_modules | 0.853 | 0.867 | 0.828 | 0.855 | **0.993** |
| order_disrupted | 0.672 | 0.718 | 0.736 | 0.734 | 0.734 |
| parity | 0.707 | 0.639 | 0.963 | 0.969 | 0.969 |
| canalizing | 0.787 | 0.877 | 0.856 | 0.862 | 0.862 |
| sparse_conj | 0.930 | 0.932 | 0.949 | 0.957 | 0.957 |
| bounded_random | 0.789 | 0.810 | 0.705 | 0.790 | 0.790 |
| uniform_H (null) | 0.678 | 0.707 | 0.653 | 0.700 | 0.700 |

Readings, all development-level:

- **(i) Where the hierarchy gain comes from.** All of it is in the two families generated with the ordered or
  module structure that the prior encodes. With 12+ observations a single structured model typically remains
  consistent, and it is the truth. This shows the prior exploits such structure from limited evidence. It does
  **not** show that real systems have that structure; the generators were chosen by us.
- **(ii) Order-disrupted control.** Sharing without order gets no gain, because the DICT mode is not in the
  averaging prior (exact sums infeasible).
- **(iii) Generic codes do as well elsewhere.** The analytic vocabulary helps on parity and canalizing, but a
  generic circuit code is comparable there.
- **(iv) The flat index code**, the S2 language, is worse than uniform at low evidence.
- **(v) The uniform-H null shows no gain.**
- **(vi) Comparisons across columns are confounded.** Underdetermined subsets differ by budget, so compare only
  within a column.

## 4. Scaling and cost (`s4-stress-dev-v2`; random bounded networks, k = 3, 16 observations, h ≤ 2, 300 s cap)

| n | B generic SAT (verdicts; counts only n ≤ 10) | C flat explicit | D index-set (verdicts + exact counts) |
|---:|---|---|---|
| 8 | 12/12, 1.8 s | 12/12, 1.8 s | 12/12, 0.02 s |
| 16 | 12/12, 1.2 s | refused (n > 10) | 12/12, 0.16 s |
| 32 | 12/12, 21.3 s | — | 12/12, 2.2 s |
| 48 | 12/12, 116.5 s | — | 12/12, 12.8 s |
| 64 | 4/12 (2 of 3 items over cap) | — | 12/12, 24.6 s |

Times are medians per 4-claim item. Agreement where both finished: 100/100.

**Withdrawn comparison (D49).** `s4-stress-dev-v1` used the historical pairwise at-most-one encoding, under
which B timed out from n = 32. That result reflects a weak baseline and is not claimed.

**Scope.** These are h ≤ 2 claims only. h = 3 uses D's capped enumeration, and a competent generic #SAT or
knowledge compiler was not tested.

## 5. Bounded local AI pilot (2 models × 40 worlds; 4 arms; 851 pilot calls + 37 pre-pilot = 888 of 2,560)

**Gates** (`docs/S4_PROTOCOL_DRAFT.md` §5), for both models:

- semantic mismatches 0;
- payload audits clean;
- parsable verdicts ≥ 97.8% per arm;
- truncated calls 0;
- 0 failed and 0 missing worlds.

No revision was used.

| Arm (verdict accuracy, world level) | qwen2.5:7b | mistral-small-3.2-24b |
|---|---:|---:|
| A unaided | 0.650 | 0.637 |
| B generic SAT | 1.000 | 0.978 (merged-commit sensitivity 1.000) |
| C flat index | 1.000 | 1.000 |
| D index-set | 1.000 | 1.000 |
| no-LLM controller (exact verdict copy) | 1.000 | 1.000 |
| always 'underdetermined' (training-fitted rule) | 0.637 | 0.637 |

| Contrast | qwen | mistral |
|---|---|---|
| **D − B (proposed primary)** | 0.000 [0.000, 0.000] | +0.022 [0.000, +0.066]; merged 0.000 [0.000, 0.000] |
| D − A | +0.350 [0.269, 0.431] | +0.363 [0.278, 0.450] |
| D − C | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |

- **Unaided models.** Arm A answered "underdetermined" on 315/320 (qwen) and 318/320 (mistral) claims. Its
  accuracy equals the base rate: the unaided models do not distinguish determined claims.
- **Forecasts on underdetermined claims** (target value vs hidden system):

  | | A | B | C | D | no-LLM controller | observed-majority surface rule |
  |---|---:|---:|---:|---:|---:|---:|
  | qwen | 0.478 | 0.586 | 0.540 | 0.543 | **0.772** | 0.571 |
  | mistral | 0.514 | 0.553 | 0.554 | 0.557 | **0.772** | 0.571 |

  The models do not use the exact `fraction_true` the tools return: the deterministic controller gets all of
  the available forecasting benefit, and more than any AI arm.
- **Pre-release checking of the common initial batch** (arm A proposals replayed through B/C/D; identical for
  all three checkers):

  | | wrong proposals | blocked | wrong verified | correct blocked | valid-release coverage |
  |---|---|---|---:|---:|---:|
  | qwen | 112/320 | 112 | 0 | 0 | 0.65 |
  | mistral | 116/320 | 116 | 0 | 0 | 0.64 |

  These are natural model errors. Zero observed wrong verifications is not a zero-risk guarantee. Adversarial
  fixtures are tested separately (`tests/test_s4_checking.py`).
- **Tool-arm episodes** committed in 3.0–3.6 turns on average, and every released "verified" answer matched the
  reference.
- **Harness defect found in the pilot (D52).** One Mistral B episode split its final answers over eight commit
  calls in one turn. The v1 harness kept only the last call, so 7 correct, verified releases were scored as
  missing. The recorded result is reported above as declared; the merged re-parse of the same raw output is a
  disclosed sensitivity. The harness now merges commit calls (tested); the pilot was not rerun.
- **Costs per world:** A 1 call; B/C/D 3.0–3.6 calls and ≈ 9.5–12 k prompt tokens. Tool wall time is negligible
  at n = 8. Raw records: `runs/s4-pilot-*-v1` (asset v0.4.0-dev).

## 6. S4-B active-investigation prototype (`s4-active-dev-v1`; offline, 40 worlds, 80 initially underdetermined targets)

| Policy | resolved at 1 measurement | 2 | 4 |
|---|---:|---:|---:|
| exact EIG (B / C / D: identical choices for 80/80 targets) | 0.075 | 0.075 | 0.087 |
| random | 0.000 | 0.000 | 0.013 |

EIG − random, resolved fraction: +0.075 [+0.025, +0.125] at both 1 and 4 measurements (40 worlds). The gain
comes from reasoning over the complete compatible set; it is **not** specific to our encoding, since every exact
backend makes the same choice. Single one-node measurements resolve few targets at this evidence level. Every
purchased observation is logged in the records.

## 7. Known-mechanism checking panel (`s4-known-dev-v1`; separate from S4-A)

- 120 mixed queries over parity, thresholds (KOFN, EXACT-k, strict majority), implications, canalizing and
  overlapping supports, at n ∈ {10, 12, 14, 32, 64}.
- 72/72 exact matches against full enumeration at n ≤ 14.
- 48 queries at n = 32 and 64 are labelled corroboration (witness replay) only.
- Support statistics reported separately (median c / d / mu: 7–8 / 8–9.5 / 0–2.5); at most 8,192 support
  assignments enumerated.

This uses the formal paper with public mechanisms and implies nothing about discovering hidden ones.

## 8. Misspecification and action diagnostic (`s4-misspec-dev-v1`; separately scored)

- One node per world is outside the declared class (four inputs; H declares k = 3).
- In 26 of 40 worlds the evidence itself was inconsistent with H. All 208 claims of those worlds were then reported
  as "inconsistent assumptions" and none was approved.
- In the remaining 14 worlds, 21 conclusions were verified and executed in the hidden simulator, with 0
  postcondition violations. Such violations are possible in principle (a proof is relative to its assumptions),
  and this small sample establishes no robustness.

## 9. Complexity / probability / proof claim audit

| Statement type | Where used | Status |
|---|---|---|
| Kolmogorov complexity | never claimed | CGH-1 lengths are upper bounds in one fixed language with a fixed decoder; two upper bounds do not order K |
| Algorithmic probability | never claimed | codec-induced weights are a finite prior over a declared class, used only offline |
| Proof | release gate | exact zero count + complete-SAT UNSAT (RUP-checkable) + replayed witness, under the declared class, one-step evidence, synchronous update, LSB ordering, horizon |
| Forecast | pilot and offline secondary | never badged as verified |
| Resource refusal | stress, h = 3 cap | reported as unsupported, never as a proof or as underdetermination |
| Formal-paper shorthand (2^d → 2^mu; ceil majority) | not copied | c, d, mu and 2^c reported separately; strict majority = floor(d/2)+1 |

## 10. Limitations

- Development data only, chosen sizes (n = 8 for the pilot), one-step evidence, k = 3.
- Families are our generators. The hierarchy-positive families were designed to contain the structure the code
  encodes.
- Pilot world counts are small. The two models shared one GPU, so latencies are indicative only.
- One generic SAT encoding was strengthened; competent knowledge compilers (d-DNNF/#SAT) were not tested.
- The forecast secondary is offline: the LLM tools did not expose codec probabilities.
- S2's null and S3's negative results stand unchanged (`reports/FAMILY_MAP_AND_METHOD_SCOPE.md`).

## 11. Reproduction

```sh
.venv/bin/python -m pytest -o addopts='' -q                                # full suite (see REVIEW_READY_R4)
.venv/bin/python -m causalguard analyze-s4 --map runs/s4-map-dev-v2 --active runs/s4-active-dev-v1 \
    --known runs/s4-known-dev-v1 --misspec runs/s4-misspec-dev-v1 --stress runs/s4-stress-dev-v1 \
    --stress runs/s4-stress-dev-v2 --pilot runs/s4-pilot-qwen25_7b-v1 --pilot runs/s4-pilot-mistral_small_24b-v1 \
    --out /tmp/s4-check
.venv/bin/python -m causalguard s4-demo
# re-running an offline program (development; writes a NEW run id): scripts/run_from_snapshot.sh <commit> <log> \
#   python -m causalguard run --config configs/s4/map_dev.json --run-id <new-id>
```
