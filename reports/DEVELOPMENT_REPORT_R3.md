# Development report R3: bounded repair (iteration 3)

Pre-sprint development (2026-11-10/11; the sprint runs 2026-11-13 to 11-15). **No confirmatory result exists.** No
freeze record was created, no new LLM panel was run, and WP10/WP11 were not started. This iteration repairs
execution integrity, outcome completeness and reporting, as the Codex R2 review asked (`reports/review_r2/`). It
reanalyses the **preserved** development records. No large panel was rerun and no endpoint, sample size, tie rule or
generator was changed. Historical errata: `reports/ERRATA_R3.md`. Field-level before/after audit:
`reports/development_r3/before_after_audit.json` (script `scripts/audit_r3_before_after.py`).

## 1. Execution (shared runner; R2-01 … R2-04)

The full contract is in `docs/EXECUTION.md`.

- **Exclusive ownership.** One kernel `flock` per run. A second live opener is refused deterministically, before it
  touches anything. A crashed owner leaves no stale lock.
- **No-clobber attempts.** Records are published by `link()`, which never replaces an existing attempt.
- **Parent-death cleanup.** A lifeline watchdog in each worker's process group, plus a workers lock that a new owner
  must hold exclusively before recovery. Group SIGKILL of the supervisor now kills the worker and its descendants,
  and an immediate resume waits for them to be gone.
- **Truthful status.** Status comes from the latest stored attempt of every planned item. Invocation counts are kept
  separately. The CLI, the confirmatory access ledger and `load_run` share the status.
- **One strict validator.** It recomputes plan/config/payload digests, then checks identities, the exact key set,
  statuses, numbering and supersession on every attempt, before any recovery mutates storage.
- **Phase from provenance.** `run_phase`; a mismatched execution mode is refused.

All iteration-2 run directories pass the strict validator unchanged.

The review's reproductions are now regression tests that require the corrected behaviour
(`tests/test_runner_r3.py`, 25 tests):

| review diagnostic | R2 behaviour | R3 behaviour (test) |
|---|---|---|
| `repro_concurrent.py` | two resumes both "succeeded"; one attempt silently replaced | second resume refused `RunBusy` while the first runs; one attempt; bytes unchanged after a later resume (`test_concurrent_resume_is_refused_and_attempt_bytes_survive`) |
| `repro_parent_death.py` | worker and child alive after supervisor-group SIGKILL | both dead within 5 s; immediate resume proceeds only after the group is gone (`test_hard_supervisor_group_kill_…`); mutation check: disabling the watchdog fails the test |
| `repro_runtime.py` (failure) | `complete_with_failures` → `complete` after no-op resume | stays `complete_with_failures`; invocation `{attempted: 0}` |
| `repro_runtime.py` (identity) | wrong run/plan/source accepted; altered stored plan resumed | `RunCorruption` on any field of any attempt incl. superseded failures, before mutation; altered stored plan refused at resume and read |

## 2. Scientific completeness and phase-aware reporting (R2-05, R2-06)

**S2.** Each ok output is reconciled with the world and design **regenerated from its plan payload**. The check
covers:
- world id, family, population and design JSON;
- every planned regime × budget (and noise) cell, with no unplanned cell;
- exactly 8 state + 16 intervention rows per cell, in design order;
- exact-count consistency (0 ≤ num ≤ den, p = num/den, and tie, majority and verdict derived from the counts).

How defects are handled:
- Identity defects, extra or duplicated rows and malformed values **refuse** the analysis.
- An absent cell or a short cell is a **missing outcome**. The world contributes nothing there and the endpoint
  reports INCOMPLETE with missing-outcome bounds. Queries, worlds and family weights are never silently reduced. A
  family with no completed world makes the equal-weight estimate "not estimable", not reweighted.

Completeness is reported separately for the structured primary, the required uniform-H null and the overall study.

Rows from runs after iteration 3 carry a query digest (`qid`), so identity checks are exact. The 670 saved worlds
are legacy rows with no `qid`. They are matched by fingerprint: kind, horizon, intervention kind, target node and
truth recomputed on the regenerated world. **Limitation:** 8,359 of 15,630 saved cells contain byte-identical rows
for distinct queries. A duplicated legacy row with the same fingerprint as the row it replaced is therefore
undetectable. Full-cardinality and positional checks still hold.

On the preserved data (`S2-dev-v2`, 670 worlds):
- structured primary 250/250 complete, required null 250/250 complete, overall study complete;
- no world has an incomplete grid;
- the per-world CSV is **byte-identical** to R2;
- the primary is **identical**: index − majority **+0.000875, 95% CI [−0.0111, +0.0121]**, 250 worlds. That means
  no clear index advantage detected; it is not equivalence;
- every secondary, null, stress, curve, MC and sizing block is identical.

Only the status text and new metadata fields changed. Regression cases are in `tests/test_completeness_r3.py`:
- absent B16 cell;
- 1-of-16 grid;
- duplicate replacing a missing query (qid and legacy variants);
- wrong world/query/design identity, unplanned cell, extra row;
- six malformed-count cases;
- missing and failed null;
- missing family and zero completed worlds;
- fixture-phase rendering, with sizing refused;
- mixed phases refused;
- contradictory phase provenance.

**S1.** Each ok item is reconciled with its planned family, n and backend, the world id shared across backends, and
the 24-query grid. Absent rows count as `query_missing` in completion denominators; duplicated or unplanned query
ids refuse. On the preserved panel, the grid is complete. Correctness, completion, latency, archive bits and
amortized totals are identical to R2.

**RSS was wrong in R2 and is now truthful.** All 49 R2 cells were false zeros (E1). The corrected values come from
the attempt envelope, and all 546 ok items are measured. Units: median worker peak RSS, MiB = 2^20 bytes, one fresh
worker per item (`maxtasks=1`), interpreter baseline included; — = no ok item (excluded by design):

| backend | n=4 | n=6 | n=8 | n=10 | n=16 | n=32 | n=64 | n=128 | n=256 |
|---|---|---|---|---|---|---|---|---|---|
| reference | 25 | 25 | 25 | 25 | — | — | — | — | — |
| literal | 34 | 34 | 34 | 34 | 36 | — | — | — | — |
| index_enum | 25 | 25 | 25 | 25 | — | — | — | — | — |
| index_cube | 25 | 25 | 25 | 25 | 30 | 35 | 36 | 37 | 39 |
| index_sat | 29 | 29 | 30 | 30 | 30 | 31 | 33 | 37 | 45 |
| bdd_ref | 40 | 41 | 42 | 45 | 45 | 1,458 | 5,004 | 3,552 | 4,890 |
| codecs | 94 | 95 | 95 | 95 | 124 | 95 | 95 | 95 | 96 |

The independent BDD reference needs gigabytes from n=32. The index backends stay under 50 MiB up to n=256. These
are development measurements on 10–12 items per cell, not an isolated benchmark.

**Phase.** Titles, status text and machine-readable `phase` are now derived from validated provenance; mixed phases
are refused. Prospective sizing is a development-only action: it is refused for a fixture or confirmatory analysis,
so the final analysis cannot silently re-size from outcomes.

## 3. S3 offline corrections (R2-07 … R2-09; no model calls)

All numbers are recomputed from saved records; no raw S3 call changed. `arms`, `target`, `contrasts`, `transforms`,
`revisions`, the confusion matrices and the historical baselines are identical to R2.

**Shortcut baselines on held-out targets (100 items).** The target task is dominated by a design shortcut; target
probe accuracies were 0.33–0.41.
- design-known budget rule (unfitted): **80/100**;
- role-specific surface rule fitted on the 300 training worlds: **79/100**;
- historical pooled surface rule: 47/100;
- majority: 29/100.

Each diagnostic panel gives 18/20, 18/20, 11/20 and 4/20 respectively.

**Coherence after aggregation.** Under the parser's single rule (`verdict_vector_coherent`: the verdict's
probability equals the maximum; ties count as coherent and are reported), on balanced items:
- qwen held-out: **134/297** valid C aggregates disagree with their own mean vector (separately, 117 of the 297 mean vectors have a tied maximum);
- qwen diagnostic: 28/60;
- gemma diagnostic: 2/60;
- the saved flag reported 0 in all three panels.

These are aggregate majority-verdict versus mean-vector disagreements. They are kept separate from direct model
contradictions (`r3_audits.coherence_final_answers`). Future runs flag `aggregate_verdict_prob_mismatch` directly.

**Novelty.** Held-out world 2 is the only identical source/target claim among the 120 distinct saved worlds; the
target adds a no-op initial edit. There are no complement claims. Results:
- original focus T_cert − T_label = **−0.08 [−0.16, 0.00]** (100 worlds), retained;
- exploratory exclusion sensitivity: −0.081 (99 worlds).

**Wording** (balanced vs ordinary accuracy, exogenous inputs vs oracle-balanced queries, gate timing, gemma scope,
certificate assurance, Brier): ERRATA_R3 E4, E8–E11. The bounded future design is `docs/S3_FUTURE_DESIGN_R3.md`
(proposal only). S3 remains exploratory and is not proposed for confirmation.

## 4. Reporting corrections

- **Sizing:** the two-sided false-positive rate under the recentred null is **0.046–0.0545** (sum of the two tails),
  not "0.021–0.032 per tail-pair" (E2).
- **Bayes:** non-exceedance in expectation, not strict loss (E3).
- **Proposed allocation unchanged:** 1,000 structured (200 per family) + 1,000 IID uniform-H null. Misspecification
  stays a separately labelled model-class adequacy and prediction-coverage diagnostic. Structured − null stays
  exploratory. Structured confirmatory worlds are conditioned on avoiding development isomorphism classes, while the
  null is unconditioned (E14).

## 5. Smoke runs through the repaired runner (execution verification, not evidence)

Both runs were made from the immutable snapshot `c40c35f2e64d` with fresh salts, the original limits and grids, and
no effect estimate drawn.

| run | plan | result |
|---|---|---|
| `dev-r3-smoke-s2` | one realizable world per primary family + one uniform-H null; 4 regimes × 6 budgets | 6/6 ok in 2.4 s; reanalysis: structured, null and overall complete; 0 legacy rows (qid path) |
| `dev-r3-smoke-s1` | all 7 backends on sparse_conj n=8 (reference applies) and parity n=128; 20 s/query, 1,200 s/item, `maxtasks=1` | 14/14 ok; 0 mismatches vs the exhaustive reference; 0 cross-backend disagreements; RSS measured for every ok item |

**S1 interruption (deliberate, recorded in D40).**
- The supervisor's whole process group was SIGKILLed after 10 attempts, with 4 n=128 items in flight.
- `--resume` was issued 2 s later. It obtained the workers lock exclusively, which requires every old worker to have
  exited, and finished 14/14. Each in-flight item ran again exactly once under its original identity, and no attempt
  file was lost or replaced.
- Limitation: the driver's process-listing check matched nothing even before the kill, because the snapshot path is
  not in worker command lines, so it is not evidence. Process-level evidence comes from the unit test, which tracks
  the worker and child PIDs.
- Smoke latency is not an isolated benchmark.

## 6. Remaining limitations

- Legacy S2 rows cannot reveal a duplicate with an identical fingerprint (above); new runs carry `qid`.
- Descendants that leave a worker's process group are not tracked by the watchdog.
- The workers-lock drain bound is 30 s. A worker that ignores SIGKILL, for example in uninterruptible I/O, would
  block a resume, which then refuses rather than overlapping.
- macOS was tested locally; Ubuntu depends on CI.
- The S2 primary is a development estimate. +0.0009 with an interval crossing zero means no clear advantage
  detected; it is not equivalence and not a refutation of simplicity priors.
- S3 target-task construct validity is weak (80/100 shortcut), and S3 is exploratory.
- No confirmatory result exists. `confirmatory_authorized` is false and `docs/FREEZE_RECORD.json` is absent.
