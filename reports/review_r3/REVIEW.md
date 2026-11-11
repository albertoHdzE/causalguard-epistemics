# Codex review R3 and new research direction

Date: 2026-11-10 (review environment date). Content reviewed: `ed719eac96580d19b4ded1b563d1e402b01ec05e`; local HEAD `f506d0adc996de1afde780317663a77c312e3cd6`. Tag `v0.3.0-dev` peels to `a02e29e91789371b2c7c58f5e87f0c4a32623ee3`. Changes from the content commit to HEAD are release documentation only.

Decision: **substantial repair accepted; two bounded defects remain before a production freeze**. Existing scientific estimates remain usable as development evidence. No freeze record or confirmatory run is created. Do not spend another iteration on large replacements of historical experiments. Repair the two defects and proceed with the new S4 implementation/pilot specified in the accompanying delegation.

## Independent verification

- `scripts/verify_artifacts.py artifacts/manifest_r3.json`: all **2,620 required files** and three optional assets match. This verifies local bytes, not a new independent GitHub download.
- Full suite with pinned upstream: **218 passed, one setup error** in 125.05 s. The HTTP adapter test cannot bind a localhost socket in this sandbox (`PermissionError`); this is an environment limitation, not an observed application failure. Log: `test-output.txt`.
- Additional runner review: 37 targeted tests pass. Scientific reviewer: 29 completeness/S3 tests pass. These are subsets, not additional independent tests to add to 218.
- S1/S2/S3 analyses regenerated from saved raw runs; exact byte comparison recorded in `verification.json`. S1 correctness and S2/S3 effects remain unchanged. No inference service was called.
- All 364,320 ordinary saved S2 rows were audited for the missing-prediction defect below: zero affected rows. The prospective bug does not invalidate the reported effect.

## R3-01: missing method predictions can silently change S2 denominators (high)

Locations: `src/causalguard/analysis/s2_analysis.py:421`, `:648`, `:661`, `:705` at reviewed content.

`_check_row_values` checks values that happen to exist in `pred`, without requiring the planned method keys. `world_scores` infers available methods from the first query, and `_contrast` then filters out worlds lacking those method scores.

Read-only reproduction on in-memory copies of published records:

| Mutation | Validator result | Primary effect |
|---|---|---|
| Remove index prediction from first intervention query | Accepts, `primary_complete=True` | N silently drops 250→249; estimate changes +0.000875→+0.0011403 |
| Remove it from a later correctly predicted query | Accepts, complete | Missing prediction scored wrong; estimate +0.000625 |
| Set it to None in nonempty V | Accepts, complete | Missing prediction scored wrong |
| Set it to Boolean | Refuses | Correct existing validation |

Evidence: `repro_missing_prediction.py`, `missing_prediction_evidence.json`. The reproduction uses only 100 bootstrap replicates for speed; its intervals are not a new scientific estimate. The changed denominators/point estimates demonstrate the defect.

Required repair: derive required keys from the fixed study contract, validate every row and enforce state-dependent value semantics. Missing method outputs must refuse or explicitly mark an incomplete endpoint, with planned denominators retained. Never infer method inclusion from one row. Explicit nulls for genuinely empty version spaces remain distinguished from missing outputs in a nonempty space. Cover ordinary/noise cells according to their own declared methods. No large run is required; reanalyse preserved records and prove scientific values unchanged.

## R3-02: work can begin after the supervisor is already dead (medium)

Location: `src/causalguard/runner.py:789–814`; existing startup test `tests/test_runner_r3.py:269–278`.

The worker obtains its shared lock, starts the watchdog asynchronously and can execute a queued payload before the watchdog observes a closed lifeline. In both the independent subreview and root replay, **5/5** immediate marker payloads executed with the lifeline already closed; workers then exited by SIGKILL. The current test sleeps 30 seconds and checks only that no result arrives, missing the side effect at startup.

Evidence: `repro_worker_start.py`, `worker_start_evidence.json`. No published result corruption was demonstrated. A late-starting old worker could pass the worker-lock acquisition after a new owner has drained it, so startup needs its own synchronous guard.

Required repair: after acquiring the workers lock and before invoking a payload, synchronously refuse work for an already-dead supervisor/closed lifeline; retain the watchdog for later death. Add an immediate side-effect test and controlled late-start/resume regression. Do not claim this can prevent all instructions after a simultaneous supervisor death; the guarantee is startup refusal for an already-closed lifeline plus prompt ongoing cleanup. Preserve existing ownership/no-clobber/ledger behavior. Small lifecycle smokes are sufficient.

## Repairs accepted and limitations retained

Exclusive owner locking, no-clobber attempt publication, stored-identity validation, truthful no-op resume status, ordinary parent-death cleanup, planned query reconciliation, separate null completeness, RSS metadata propagation, and S3 offline shortcut/coherence/novelty disclosures are substantially repaired.

Legacy S2 rows lack unique query IDs; identical-row substitutions remain undetectable in those historical files, as disclosed. New rows carry IDs. Watchdog support is POSIX and process-group scoped. Do not expand these boundaries into unsupported platform guarantees.

## Scientific interpretation and next priority

S2 retains its original revised endpoint and allocation. No clear index-selected-model advantage was detected over exact compatible-set majority. S3 retains the negative transfer result and its task shortcut disclosure. Neither should be rewritten as a success.

However, the user correctly points out a scope mismatch: shortest flat index model selection is narrower than an ordered hierarchical representation of possibilities used for inquiry. The original CausalBool HID specification contains capabilities missing here. The next study should directly implement and isolate those capabilities, while acknowledging related unsuccessful tests in the original research history.

Read `reports/FAMILY_MAP_AND_METHOD_SCOPE.md` for measured family boundaries and `docs/RESEARCH_DIRECTION_S4.md` for the new study. The new direction is not an inference that hierarchy must win; it is a better operational test of the user's actual hypothesis.

## Reproduction commands

Run from the repository; use a temporary output directory and preserve source records:

```sh
CAUSALBOOL_ROOT=/Users/alberto/.cache/causalguard/CausalBool .venv/bin/python -m pytest -o addopts='' -q
.venv/bin/python scripts/verify_artifacts.py artifacts/manifest_r3.json
.venv/bin/python reports/review_r3/repro_worker_start.py
.venv/bin/python reports/review_r3/repro_missing_prediction.py
.venv/bin/python -m causalguard analyze-s1-v2 --run-dir runs/S1-dev-v2-panel --out /tmp/causalguard-review-r3/s1
.venv/bin/python -m causalguard analyze-s2-v2 --run-dir runs/S2-dev-v2 --mc-run-dir runs/S2-dev-v2-mcdiag --out /tmp/causalguard-review-r3/s2
.venv/bin/python -m causalguard analyze-s3-v2 --run-dir runs/s3v2-diag-gemma3_12b-dev --run-dir runs/s3v2-diag-qwen25_7b-dev --run-dir runs/s3v2-heldout-qwen25_7b-dev --out /tmp/causalguard-review-r3/s3
```

No remote CI rerun or release download was performed by this reviewer. Public release/CI claims remain author-reported. No production implementation, historical artifact, or experiment configuration was modified during this review.
