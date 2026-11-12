# R7 execution plan

Branch `iteration-7`, created from `iteration-6` at `7316350` plus the director's review and delegation commit.
Keep `reports/R7_TASK_LEDGER.md` from the first step.

| WP | Work | Gate to pass before the next WP |
|---|---|---|
| WP0 | Takeover. Read the R6 review and this package. Reproduce the corpus census with tested code (essential indegree, nested canalizing, unate, by indegree), on all files for the aggregate table and separately on calibration groups. Compare with the director's provisional table and report every difference. Build the R7 inventory and group split; commit the manifest. | Population gate of protocol §2. Census differences explained. |
| WP1 | Track K predictors for d ≤ 6: `uniform`, `unate`, `ncf`, `formula`, `cgh`. Normalisation, brute-force and independent-oracle tests, planted defect, cost by d. | All exactness tests pass with printed denominators. Earlier outputs byte-identical. |
| WP2 | Setting W world item, evidence panels (random-state and trajectory), query schedule, public-payload audit. Calibration on calibration groups. Budget, comparator and ε chosen by the protocol rules. `docs/R7_DESIGN_LOCK.json` with your recorded predictions. | Lock committed before any evaluation-group score. |
| WP3 | Track K evaluation from the lock snapshot. Locked analysis, figures, `reports/R7_REALISTIC_INDEGREE.md`. | Every declared secondary is in the locked analysis output (R6 defect S-D1 must not recur). |
| WP4 | Track V analysis on the same runs. Risk–coverage figure, `reports/R7_CLAIM_CHECKING.md`. | — |
| WP5 | Track L pilot (`docs/R7L_DESIGN.md` first). Optional exact-XDC secondary of protocol §7. | Smoke gate ≥ 90 % parsable before the 32 worlds. |
| WP6 | Claim ledger, evidence matrix, acceptance JSON, funding brief, review entry point, release `v0.7.0-dev`. | Fresh-clone check as in R6. |

Order of priority if time runs short: WP0–WP3 complete, then WP4, then WP6, then WP5. A complete Track K with a
clean lock is worth more than three partial tracks.

Engineering rules:

- One owner per concept. The corpus parser stays in `r5/external.py`. The analytic catalogue stays in
  `s4/hcode.py`; raise its limit there rather than copying it. New per-node function-class code goes in one new
  module under `src/causalguard/r7/`. The independent oracles are the deliberate exception and live in the tests.
- Default arguments keep every R5 and R6 output byte-identical. Prove it with `scripts/r6_regen_check.sh` (or its
  R7 successor) and the replay check.
- Every gate prints its denominator, refuses on empty input and exits non-zero on failure.
- Runs execute from committed snapshots with `scripts/run_from_snapshot.sh`.
- Verification loops: check that the loop body actually ran (R6 had two that failed silently).
- Render the object before quoting a number about it. Each report states the figure first.
- Date every work item by its actual timestamp as pre-sprint (before 2026-11-13) or sprint work, and keep
  `PREEXISTING_WORK.md` current. The sprint requires this disclosure.
- Do not stop to ask routine implementation questions. Where the protocol leaves a choice open, decide it on
  calibration groups, record it in `DECISIONS.md` (D70 onward) and in the lock, and continue.
- Publishing: push branch `iteration-7` and cut prerelease `v0.7.0-dev` in `albertoHdzE/causalguard-epistemics`
  as in earlier iterations. Older tags and assets stay untouched.

Ceilings, not targets: 48 CPU-hours offline with four workers; at most 400 new model requests inside the global
3,072 (1,498 used); 2 model-server hours. No confirmatory run, no freeze record, no paid inference, no weight
changes.
