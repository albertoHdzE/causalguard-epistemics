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
| P6 S3 v2 development | complete: qwen diag + held-out (100/100 ok); gemma diag = floor diagnostic (D33); analysis D34 | runs/s3v2-*; reports/development_r2/s3_v2_summary.json |
| P7 package + release | pending | — |

## Runs (iteration 2)

| run id | snapshot | state |
|---|---|---|
| s3v2-diag-qwen25_7b-dev | 915f089c1db7 | complete: 20 ok; gate D29 passed |
| s3v2-diag-gemma3_12b-dev | 915f089c1db7 | complete: 20 ok (interrupted 13:45Z and resumed 14:02Z, D32); gate D29 G3 failed (D33) |
| s3v2-heldout-qwen25_7b-dev | dd63670a78b1 | complete: 100 ok, 0 failed (16:53Z) |
| S2-dev-v2 | 01ca7072fb09 | complete: 670 ok, 0 failed (no `end` event, D27) |
| S2-dev-v2-mcdiag | 01ca7072fb09 | complete: 200 ok |
| S1-dev-v2-panel | dd63670a78b1 | complete: 686 ok |

## Next exact actions
1. P7: acceptance_r2.json, test-output-r2.txt, manifest_r2 + release asset, merge to main, tag v0.2.0-dev,
   GitHub prerelease, CI, clean-clone check, fill REVIEW_READY_R2 §8.
