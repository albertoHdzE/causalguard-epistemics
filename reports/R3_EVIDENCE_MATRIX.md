# R2 finding → repair → test → evidence (iteration 3)

Test files: `tests/test_runner_r3.py` (runner), `tests/test_completeness_r3.py` (S2/S1 completeness, phase),
`tests/test_s3_r3.py` (S3), `tests/test_owners.py` (single-owner guards). Reanalysis: `reports/development_r3/`. Audit:
`reports/development_r3/before_after_audit.json`.

| finding | repair (owner) | regression tests (require corrected behaviour) | evidence |
|---|---|---|---|
| R2-01 concurrent resume clobbers an attempt | exclusive `flock` ownership before any inspection; `RunBusy`; atomic dir creation; no-clobber `link()` publication; locked shared registry/access ledger (`runner.py`) | `test_concurrent_resume_is_refused_and_attempt_bytes_survive`, `test_second_opener_refused_and_live_temporary_not_quarantined`, `test_publication_never_replaces_an_existing_attempt`, `test_shared_registry_concurrent_writers_do_not_corrupt` | docs/EXECUTION.md; D37 |
| R2-02 supervisor death leaves workers alive | lifeline watchdog in each worker group; shared workers lock; exclusive drain (≤30 s) before recovery (`runner.py`) | `test_hard_supervisor_group_kill_cleans_worker_group_and_resume_does_not_overlap` (fails if the watchdog kill is disabled: mutation check), `test_worker_started_after_supervisor_death_never_runs_work`, `test_normal_end_leaves_no_watchdog_or_worker` | smoke interruption `runs/logs/dev-r3-smoke-s1.interruption.json` (D40) |
| R2-03 unresolved failure becomes `complete` on resume | `run_status` from the latest stored attempts; separate `invocation` counts; CLI/ledger/`load_run` share it; `retry_failed` development-only | `test_failure_then_noop_resume_stays_complete_with_failures`, `test_same_object_can_execute_twice_and_reacquires_as_resume`, `test_published_attempt_without_ledger_end_is_reconciled_on_resume` (D44); updated `test_resume_does_not_duplicate` | end events of all four smoke runs |
| R2-04 stored identities not bound | `validate_plan` and `validate_attempt` on every attempt incl. superseded failures, before recovery | `test_altered_stored_plan_with_old_digest_is_refused`, `test_wrong_identity_on_any_attempt_is_corruption_before_mutation` (7 fields × 2 positions; storage unchanged) | all iteration-2 runs pass unchanged |
| R2-05 terminal success ≠ endpoint completeness | `validate_world_v2` against the regenerated world/design; missing vs fatal; structured/null/overall completeness; family-safe estimates; `qid` rows (`s2_analysis.py`, `experiments/s2.py`); S1 24-query grid (`s1_analysis.py`) | 24 cases in `test_completeness_r3.py`: absent B16, 1-of-16, duplicate (qid and legacy), wrong identity ×6, malformed counts ×6, missing/failed null, missing family, zero worlds, S1 missing/duplicate rows | S2 reanalysis: 250/250 + 250/250 complete; CSV byte-identical; primary identical |
| R2-06 S1 RSS false zeros | envelope metadata via `load_run.attempt_meta`; null when missing; coverage and units | `test_s1_rss_from_envelope_and_missing_is_null` | 49/49 cells, 546/546 items measured; ERRATA E1 |
| R2-07 S3 budget shortcut | design-known rule derived from generator constants; role-specific rules fitted on training worlds, persisted (`s3_role_baselines_v3.json`) | `test_design_known_rule_is_the_generator_coupling` | 80/100 held-out, 18/20 per diagnostic; role rule 79/100 |
| R2-08 C coherence not recomputed | single rule `llm.parse.verdict_vector_coherent`; `aggregate_verdict_prob_mismatch`; `coherence_audit` | `test_mean_vector_can_disagree_with_majority_verdict`, `test_probability_ties_are_coherent_and_counted`, `test_coherence_audit_recomputes_c_after_aggregation`; owner guard | 134/297 (saved flag 0); 28/60; 2/60 |
| R2-09 duplicate target claim | `semantic_claim`, `target_novelty_audit`; exploratory exclusion | `test_semantic_novelty_normalizes_noop_initial_edits_and_labels_complements` | world 2 only; focus −0.08 retained; −0.081 (99) exploratory |
| sizing per-tail wording | ERRATA E2 | — | two-sided 0.046–0.0545 |
| Bayes strict-loss wording | ERRATA E3 | — | — |
| gemma/D29 interpretation | ERRATA E9 | — | — |
| balanced-accuracy labels | ERRATA E4 | — | 125/300 = 0.417 ordinary |
| exogenous vs oracle-balanced | ERRATA E8; docs/S3_HARNESS.md corrected | — | — |
| certificate assurance attribution | ERRATA E10; S3 future design | — | — |
| Brier / coherence denominators | ERRATA E11; `coherence_audit` | coherence tests | — |
| phase-aware labels, sizing | `runner.run_phase`; analyses refuse mixed phases; sizing development-only | `test_fixture_phase_is_rendered_and_sizing_refused`, `test_mixed_phases_refused`, `test_phase_provenance_contradiction_is_corruption` | ERRATA E12 |
| structured isomorphism conditioning | ERRATA E14 | — | — |
