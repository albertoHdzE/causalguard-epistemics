# STATUS

_Last updated: 2026-11-10 (iteration 2, after Codex review R1). Pre-sprint development (the sprint starts 2026-11-13)._

**Resume protocol.** Read this file, `DECISIONS.md` (D23+ for iteration 2), `git log` on branch `iteration-2`, and
`runs/registry.jsonl` (runtime registry; the tracked `RUNS.jsonl` is the frozen iteration-1 registry). Every run is
reconciled with `causalguard.runner.load_run(<run dir>)`. A run is continued only with `--resume` under an identical
plan (same config and source-tree digest); long runs execute from an immutable snapshot worktree via
`scripts/run_from_snapshot.sh <commit> <log> python -m ...`, so the main tree can be edited while they run.

**Not authorized:** no `docs/FREEZE_RECORD.json`, no confirmatory run, no WP10/WP11 (reports/review_r1/DECISION.json).

## Iteration-2 work items (REPAIR_SPEC P1–P7)

| Item | State | Evidence |
|---|---|---|
| P1 exactness (R01), strict logs (R04), plan/endpoint binding (R05) | implemented + tested | versionspace.exact_query_counts / boolean_support; runner v2; analysis.s2_analysis.analyze_v2; tests/test_s2_v2.py, test_runner_v2.py |
| P2 freeze lifecycle (R03), caps (R06), manifests (R08) | implemented + E2E fixture tests | src/causalguard/freeze.py, scripts/run_confirmatory.py, tests/test_freeze_lifecycle.py, scripts/verify_artifacts.py |
| P3 S2 design v2 + revised primary + MC policy | implemented | generators.make_s2_design, configs/endpoints/S2-primary-v2.json |
| P4 S2 development (670 worlds + MC diagnostic) | runs complete | runs/S2-dev-v2 (670 ok; D27), runs/S2-dev-v2-mcdiag (200 ok) |
| P5 S1 repair panel | complete: 686/686 ok, 0 mismatches | runs/S1-dev-v2-panel; reports/development_r2/s1_v2_summary.json |
| P6 S3 v2 development | qwen diag complete, passes D29; qwen held-out running; gemma diag resumed | runs/s3v2-* |
| P7 package + release | pending | — |

## Runs (iteration 2)

| run id | snapshot | state |
|---|---|---|
| s3v2-diag-qwen25_7b-dev | 915f089c1db7 | complete: 20 ok; gate D29 passed |
| s3v2-diag-gemma3_12b-dev | 915f089c1db7 | interrupted 13:45Z (operator, for S1 isolation; 9/20 done), resumed 14:02Z with --resume |
| s3v2-heldout-qwen25_7b-dev | dd63670a78b1 | running (100 worlds, 2 workers) |
| S2-dev-v2 | 01ca7072fb09 | complete: 670 ok, 0 failed (no `end` event, D27) |
| S2-dev-v2-mcdiag | 01ca7072fb09 | complete: 200 ok |
| S1-dev-v2-panel | dd63670a78b1 | complete: 686 ok |

## Next exact actions
1. When the gemma diagnostic completes: apply gate D29; if it passes, launch `s3v2-heldout-gemma3_12b-dev` from snapshot dd63670a78b1 (S3 code byte-identical to 915f089c; task generation hash-checked).
2. When both held-out panels finish: analyze-s3-v2 over all four S3 v2 runs; write the S3 section.
3. Build reports/REVIEW_READY_R2.md, acceptance_r2.json, manifest_r2, release v0.2.0-dev.
