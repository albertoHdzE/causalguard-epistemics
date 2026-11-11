# Codex review R4 request: P0 repairs and the concrete S4 design/pilot

Repository: `albertoHdzE/causalguard-epistemics`. Review the **content commit
`957c8d73be5a3a5a6c301929f7f4036d70d70ac3`** (branches `main` and `iteration-4`). Tag **`v0.4.0-dev`** points to
the docs-only release commit that adds `reports/REVIEW_READY_R4.md` and this file; nothing else differs from the
content commit. The release asset is `causalguard-dev-runs-v0.4.0-dev.tar.gz` (sha256
`0e96b2912e268f94bb69388b4fd6de37784a80c1cf443acc5247e04f6fcb57b9`). Extract it at the repository root before
verifying `artifacts/manifest_r4.json`. The post-tag check is in `reports/RELEASE_CHECK_R4.md`.

Start with `reports/REVIEW_READY_R4.md`, then `reports/R4_EVIDENCE_MATRIX.md`.

## Part 1: P0 (accept or reject; independent of S4)

1. **R3-01.** Verify `analysis/s2_analysis.py`: `required_pred_keys`, `_check_row_values`, `world_scores` and
   `_contrast`.
   - Re-run your `reports/review_r3/repro_missing_prediction.py` mutations. Every one should now refuse, or the
     denominator should be retained.
   - Confirm that reanalysis of `runs/S2-dev-v2` reproduces the R3 per-world CSV byte-for-byte.
2. **R3-02.** Verify `runner._refuse_if_supervisor_dead`, which is called after the shared workers lock and before
   every payload.
   - Re-run `reports/review_r3/repro_worker_start.py`; expect 0/5 markers.
   - Check `tests/test_runner_r4.py`, including the late-start-after-drain case.
   - The claimed guarantee is limited to startup refusal for an already-closed lifeline plus watchdog cleanup.
     Check that it is not overstated.
3. Confirm that the S2 historical paths are unchanged: the pairwise AMO default and unweighted counts.

## Part 2: the concrete S4 design and pilot (scoped decision before any main study)

Please assess:

1. **Method identity** (`docs/S4_METHOD_COVERAGE.md`).
   - Is arm D a faithful, method-specific implementation? This covers support-schema V(D) with Möbius
     distinct counting, support-local claims, the analytic calculus port, and CGH-1 with ordered
     templates/modules/dictionary/patches.
   - Are the boundaries honest: one-step evidence, k ≤ 4 in the code, k = 3 in the study, and the h = 3 capped
     enumeration?
   - Re-derive the worked example in §3.
2. **Correctness.** Check `tests/test_s4_mechspace.py` (B = C = D, brute force over 2-node networks),
   `tests/test_s4_system.py` (codec average vs brute force, weights up to 2^70) and the replay agreement in the
   map (5,120/5,120).
3. **Fairness of comparators.**
   - B is the existing complete CNF/SAT with the new sequential-counter AMO. Is it now competent?
   - Should counts above n = 10 require a knowledge compiler?
   - The withdrawn stress v1 is preserved; confirm it is not used as evidence.
4. **Check-before-release gate** (`s4/checking.py`, `tests/test_s4_checking.py`).
   - Status semantics: `proposal_check_status` vs `epistemic_verdict`.
   - Binding and staleness; sealed decisions.
   - Forged, edited or text certificates.
   - Empty V; resource refusal; simulated postconditions; the misspecification diagnostic.
5. **Leakage and design.**
   - Evaluator-only hidden truth and the public payload audit.
   - Claim novelty and redraw counts.
   - Training-only surface baselines committed before calls.
   - Matched order-disrupted control and the uniform-H null.
   - Gap: isomorphism deduplication is not applied as a filter.
6. **Pilot** (`runs/s4-pilot-*-v1`, `reports/development_r4/s4_pilot_summary.json`).
   - Gates: model selection rule (D50) and the pre-pilot interface change.
   - The D52 harness defect and its sensitivity treatment.
   - Prevention metrics on the common batch.
   - The finding that LLMs do not use the exact probabilities they are given.
7. **Offline codec-averaging secondary** (`reports/S4_DEVELOPMENT_REPORT.md` §3.1). Is the attribution correct?
   The claim is that the hierarchy gain is confined to the two structure-matched families, with zero gain in the
   controls and the null. Is the stated interpretation ("exploits such structure when present; does not show
   real systems have it") sufficiently conservative?
8. **Sizing and the main-study primary** (`reports/S4_DESIGN_SIZING.md`).
   - D − B is an exact tie and cannot be sized. Choose or reject: (a) resource-capped accuracy, (b) cost at equal
     accuracy, (c) the forecast endpoint with externally chosen held-out structure, or (d) something else.
   - State whether a new call budget (about 16–18 k local calls) would be authorized for the chosen design.

Not requested: a freeze, a confirmatory run, the main study, paid inference, or WP10/WP11. Record findings as
R4-xx with severity, a reproduction, and the required repair, as in R3.
