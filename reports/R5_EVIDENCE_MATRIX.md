# R5 evidence matrix (assignment requirement → code / test / artifact / precise block)

| WP / requirement | Code | Test | Artifact | Status |
|---|---|---|---|---|
| WP0 baseline, preserved user files | — | full suite 448 → 469 | `reports/R5_BASELINE_AUDIT.md`, commit `3c0841a` | done |
| WP0 R4 audit (counts, isolation, proof levels, gate cost) | `r5/counting.py` | `test_gen_ve_*` | baseline audit (R5-01) | done (implementation audit) |
| WP1 counting derivation + tiny independent checks | — | `test_gen_ve_against_truth_table_oracle`, `test_projected_cnf_*` | `docs/R5_COUNTING_DERIVATION.md` | done |
| WP1 external retrieval/inclusion/transform log | `r5/external.py` | `test_external_parser_*` | `artifacts/r5_source_manifest.json` | done (intact 4 groups < 20: limited) |
| WP1 synthetic generators + splits | `r5/data.py` | `test_split_*`, `test_design_*` | spec hash in lock | done |
| WP1 generic counter, projection semantics | `r5/counting.py` | `test_projected_cnf_counts_distinct_mechanisms_and_trap` | — | partial: ganak/d4 BLOCKED (D55) |
| WP1 AND counterexample + expanded class | `r5/misspec.py` | `test_and_counterexample_*`, `test_mixed_node_bounds_*` | — | done |
| WP2 Prediction/CountResult/InvestigationStep/AssumptionCheck | `r5/contracts.py` | `test_*_contract*`, `test_assumption_check_*` | — | done |
| WP2 budget ledger survives interruption; phase caps | `llm/harness.CallBudget` | `test_call_budget_phase_cap_and_interrupted_reservation` | `runs/r5-calls/ledger.jsonl` | done |
| WP2 memory ceiling / cleanup | `runner._start_memory_guard`, benchmark child kill | — | attempt RSS fields | done |
| WP2 literal-vs-node coding, leaks, missing rows | `r5/forecast.py`, analysis | `test_outcome_*`, `test_public_payload_*`, `test_world_brier_bounds_*` | — | done |
| WP3 calibration, lock before evaluation | configs | — | `docs/R5_DESIGN_LOCK.json` (`dd193ce`) | done |
| WP3 AI validity gate ≥ 0.90 | `r5/investigation.py` | `test_stop_action_*` | `a_ai_calibration_gate_v2.json` (1.0; v1 failed, R5-02) | done |
| WP4 G evaluation + external | `r5/forecast.py` | — | `reports/R5_GENERALIZATION.md` | complete |
| WP4 C benchmark (5×8, checkpoints, reuse, release, RSS, reps) | `r5/benchmark.py` | `test_gen_ve_handles_64_bit_states` | `reports/R5_COUNTING_AND_COST.md` | complete (v2 + v3 for 8 cells, R5-03/04) |
| WP5 M panels | `r5/misspec.py` | — | `reports/R5_ASSUMPTION_FAILURES.md` | complete |
| WP5 A pilot (2 models × 64 × 2 arms) | `r5/investigation.py` | `test_ai_episode_*`, `test_menu_*` | `reports/R5_AI_INVESTIGATION.md` | complete |
| WP6 demo | `r5/demo.py` (`python -m causalguard r5-demo`) | — | — | done (illustration, not evidence) |
| WP6 claim ledger, brief | — | — | `reports/CLAIM_LEDGER_R5.csv`, `docs/R5_FUNDING_BRIEF.md` | done |
| WP7 release, checks, review package | `scripts/build_manifest.py r5` | — | `artifacts/manifest_r5.json`, `reports/RELEASE_CHECK_R5.md`, `reports/REVIEW_READY_R5.md` | see release check |
