# R6 execution plan

Branch `iteration-6` (local; created by the reviewer from `05be285`). Reviewer commits on it:
`f640e70` (XDC implementation, pre-calibration) and the lock commit that follows it (`docs/R6_DESIGN_LOCK.json`).
Inspect `git log iteration-5..iteration-6` first and record what you find in `reports/R6_TASK_LEDGER.md`.

| WP | Work | Gate to pass before the next WP |
|---|---|---|
| WP0 | Takeover: read the R5 review, `docs/R6_PROTOCOL.md`, the lock, the reviewer's diff. Verify the two evaluation runs completed from the lock snapshot; resume if not. Start the ledger. | Runs complete or resumed; diff recorded |
| WP1 | Track X audit: derivation, independent oracle, exchangeability, normalisation, planted-defect control, event order. | Audit passes, or a defect is recorded and v2 reruns are planned |
| WP2 | Track G6 analysis, figures and `reports/R6_GENERALIZATION.md`. | Report written against the lock's predictions |
| WP3 | Track S build: XDC-EB with certified fit, sparse per-node compatible sets through the support schema, tests against exact XDC at n = 8 and against brute force on tiny cases. | Tests pass; cost measured at n = 16, 32, 64 |
| WP4 | Track S inventory, group split, calibration, `docs/R6S_DESIGN_LOCK.json` committed. | Lock committed before any evaluation-group score |
| WP5 | Track S evaluation, analysis, `reports/R6_SCALE.md`. | — |
| WP6 | Track A2 pilot (can run alongside WP3–WP5; lower offline concurrency while a model server is busy). | Calibration validity ≥ 90 % parsable actions on 4 smoke worlds before the 32 |
| WP7 | Claim ledger, evidence matrix, acceptance JSON, funding brief update, review package, release `v0.6.0-dev`. | Fresh-clone check as in R5 |

Engineering rules:

- One owner per concept. XDC-EB belongs beside `XDC` in `src/causalguard/r5/priors.py` or a new `r6/` package that
  imports it; do not copy the type aggregation or the phi construction. The independent oracle of WP1 is the one
  deliberate exception (it must share no code) and lives in the tests.
- Default arguments must keep every R5 and R6 n = 8 output byte-identical. Prove it by regenerating the R5 analyses
  and the R6 calibration analysis and comparing with `cmp`.
- Every gate prints its denominator and refuses on empty input.
- Runs execute from committed snapshots with `scripts/run_from_snapshot.sh`.
- Do not stop to ask routine implementation questions. If a population gate fails (for example too few intact
  models), follow the fallback in the protocol, record it, and continue.
- Publishing: push branch `iteration-6` and cut prerelease `v0.6.0-dev` in `albertoHdzE/causalguard-epistemics`,
  as in previous iterations, older tags and assets untouched.
