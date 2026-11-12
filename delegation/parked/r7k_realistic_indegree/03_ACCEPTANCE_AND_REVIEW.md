# R7 acceptance and review

## Required artifacts

| Artifact | Content |
|---|---|
| `reports/R7_CENSUS.md` + JSON | Indegree and function-class census with tested code; differences from the director's provisional table. |
| `artifacts/r7_source_manifest.json` | Eligible models, exclusions with reasons, groups, split. Committed before calibration. |
| `docs/R7_PREDICTORS.md` | Definition of each predictor, the one-mass-per-table rule, normalisation argument, cost by indegree. |
| `tests/test_r7_*.py` | Brute force at d ≤ 4, independent oracles at d = 5 and 6, planted defect, `unate` de-duplication. |
| `docs/R7_DESIGN_LOCK.json` | Budgets, comparator, ε, primary, secondaries, interpretation rules, your predictions, what was seen before the lock. |
| `reports/R7_REALISTIC_INDEGREE.md` + analysis JSON + figures | Track K. |
| `reports/R7_CLAIM_CHECKING.md` + analysis JSON + figure | Track V. |
| `docs/R7L_DESIGN.md`, `reports/R7_AI_UNAIDED.md` | Track L, if run. |
| `reports/acceptance_r7.json`, `reports/CLAIM_LEDGER_R7.csv`, `reports/R7_EVIDENCE_MATRIX.md` | As in R6. |
| `docs/R7_FUNDING_BRIEF.md` | Two pages. Established results apart from open ones. |
| `reports/REVIEW_READY_R7.md` | Reviewer entry point. |
| `artifacts/manifest_r7.json`, `reports/RELEASE_CHECK_R7.md` | Release identities and fresh-clone check. |

## Acceptance fields (`acceptance_r7.json`)

For each track: completion (complete / partial / skipped, with the reason) and scientific outcome (supported /
supported in scope / null / adverse / inconclusive), kept separate. For Track K also: lock commit and time, run
open time, items planned / finished / missing, primary estimate with interval and bounds, each secondary, and each
recorded prediction beside its outcome.

## What the reviewer will check

1. The census is computed by tested code and its differences from the provisional table are explained.
2. Every predictor is normalised, has full support and matches brute force and an independent oracle; the planted
   defect is caught.
3. The lock precedes every evaluation-group score, and the evaluation ran once from the lock snapshot.
4. Budget, comparator and ε were chosen on calibration groups by the stated rules. Each chosen value is reported
   with the alternatives, and the report says whether it sits at the edge of its range.
5. The primary is reported with its distribution, and the high-indegree and low-indegree parts stand beside it.
6. `formula` − `cgh` and `ncf` − `cgh` are reported with the same prominence as the primary.
7. Track V counts are split by whether the true table is inside the class, and the matched-coverage comparison is
   done at the coverage UNATE checking actually achieves.
8. Track L requests are all in the ledger, and both arms ran on the same items.
9. All R5 and R6 outputs remain byte-identical.
10. Nothing called a description length uses fitted frequencies.

## Return contract

Return a summary with: release identities; results by track with completion and outcome; each recorded prediction
against its outcome (yours and the director's); deviations and defects; resources used; and a section "Where the
director's plan or method is wrong", with evidence. Start the reviewer at `reports/REVIEW_READY_R7.md`.
