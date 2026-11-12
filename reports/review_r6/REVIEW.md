# Independent review of R6 (`v0.6.0-dev`, content `ec16507`)

Reviewer and director: Claude Fable, 2026-11-12. Local repository, branch `iteration-6` at `7316350`. No model
calls. The reviewer designed XDC and proposed XDC-EB, so the judgement on those two rests on Opus's independent
audit and on the checks below, not on the reviewer's own confidence in them.

## Decision

**Accept R6 as development evidence.** The implementation agent's audit is sound, its reading of the results is
more careful than the plan it was given, and six of its seven objections to that plan are correct. The scientific
conclusion is that dictionary sharing is real but third-order on published models. The review also finds the
reason the last three rounds produced small effects, and that reason sets the next experiment.

## What was reproduced

| Check | Result |
|---|---|
| Full test suite (`.venv`) | 480 passed, 0 failed, 5 skipped (upstream parity, needs a local CausalBool checkout) |
| `scripts/r6_regen_check.sh` (every committed R5 and R6 analysis regenerated from raw runs) | 21 / 21 byte-identical |
| `artifacts/manifest_r6.json` at the tag commit `766e070` | ledger hash matches at the tag. At HEAD one file differs (`R6_TASK_LEDGER.md`, edited after the tag in `7316350`), as expected |
| Oracle independence (`tests/test_r6_xdc_oracle.py` imports) | only data types and the base codes' bit lengths are imported; no XDC, GSR, version-space or reference code |
| Event order | lock `246d3cd` precedes both n = 8 evaluations; Track S lock `072f051` precedes `r6-s-eval-v1` |

Not reproduced: the 417 model requests (records inspected only), the fresh clone, and the asset download.

## Findings

**R6-F1 (major, scope of the whole programme). The class H(n, 3) leaves a prior almost nothing to do, and it
excludes most published models.** A node with at most three inputs has at most eight rows, so 8–16 observations
settle it under any code. Measured in R6: the best flat code's Brier on 24-node fragments is 0.064 at 8
observations, 0.015 at 16 and 0.000 at 64. The differences between compact codes are below 0.01 everywhere. A
census of the pinned corpus (reviewer's throwaway script, provisional; to be reproduced with tested code in R7)
gives: 32 % of nodes have essential indegree ≥ 4; only 20 of 335 model files have every node at indegree ≤ 3; at
indegree 4–6, 67–92 % of published rules are nested canalizing and 97–99 % are unate. The experiment has been run
where compact description cannot matter, and not where it can.

**R6-F2 (major, ordering of effects).** At 24 nodes and 8 observations the mean Brier is 0.130 for uniform counting,
0.078–0.094 for the flat compact codes, and 0.070–0.073 with the learned dictionary. Description length against
counting is worth about 0.05. The choice among compact codes is worth about 0.01. Sharing adds about 0.009. The
reports lead with the smallest of the three.

**R6-F3 (medium, the reviewer's error). XDC-EB is not a description length.** It fits type weights from observed
frequencies and does not charge for them. That is a plug-in estimate and conflicts with the programme's rule that a
description length is never computed from an observed frequency distribution. Exact XDC does not have this problem:
each new type is paid for at the base-code price. XDC-EB stays as a certified, cheap forecaster with that label.

**R6-F4 (medium, a fitted knob at the edge of its range).** The regulariser a = 16 is the largest value offered.
Calibration Brier falls monotonically with a (0.0665, 0.0645, 0.0605 for a = 1, 4, 16), and a → ∞ is the flat
code. The search stopped at its boundary. The locked comparator was also not the best flat code on evaluation
(`flat[circuit]` 0.0820 against `flat[cgh_flat]` 0.0783). The like-for-like sharing gain is still about 0.0085 on
both bases, so the primary is not an artefact of the comparator, but the report should say both things.

**R6-F5 (medium, Track S population).** Every evaluation lineage had contributed 8-node fragments earlier, so
Track S is not a held-out-source test. Raised by Opus; correct. It needs a second corpus or a setting whose
evaluation content was never scored.

**R6-F6 (minor, Track A2 reading).** The fall in unsupported definite claims (15 → 2 of 32) is largely what a
blocking check does by construction. The informative part is what the model did next: it retreated to "cannot
tell" (4 → 14) and did not buy the measurement. Opus reports this correctly. The claim is "the check turns
overclaiming into honest uncertainty in a weak model", on 32 worlds and one model.

**R6-F7 (minor).** Track S has no figure of per-world differences. The locked analyser omitted a declared secondary
(S-D1, disclosed and repaired post hoc).

## Opus's objections to the reviewer's plan

| # | Objection | Verdict |
|---|---|---|
| 1 | Budgets n / 2n / 4n would only measure the ceiling | Correct. The reviewer's suggestion was wrong; Opus's sizing rule is adopted. |
| 2 | Whole published models cannot be the primary population at indegree ≤ 3 | Correct, and it is the symptom of F1. |
| 3 | Track S is not a held-out-source test | Correct (F5). |
| 4 | The outcome map did not cover the actual result | Correct. R7's map has a catch-all row. |
| 5 | The synthetic headline averages planted-reuse strata with the rest | Correct as a reading. The number is the locked primary and stays, with both halves beside it. |
| 6 | Clamping inflates the reuse covariate | Correct. |
| 7 | XDC-EB is neither "XDC" nor a mere approximation | Partly. It should have its own name, but see F3. |

## What this means for the direction

The question "which compact code is best inside H(n, 3)" has been answered three times: it barely matters. The
question that the project goal actually asks is whether a compact algorithmic description helps infer unseen facts
and check claims. That has headroom only where a node's table is too large to observe, which is indegree ≥ 4, and
that is where about a third of published nodes and nearly all whole published models are. R7
(`delegation/ITERATION_7_OPUS_PROMPT.md`) moves the experiment there: whole published models, wiring public, logic
hidden, our analytic code against counting and against the field-standard monotonicity assumption, with claim
checking under declared assumptions measured on the same worlds.
