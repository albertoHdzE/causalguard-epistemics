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
| P5 S1 repair panel | pending: needs the machine idle (run between S3 panels) | configs/s1_dev_v2_panel.json |
| P6 S3 v2 development | diagnostic panels running; held-out panels pending gate D29 | runs/s3v2-diag-*-dev |
| P7 package + release | pending | — |

## Runs (iteration 2)

| run id | snapshot | state |
|---|---|---|
| s3v2-diag-qwen25_7b-dev | 915f089c1db7 | running (20 worlds) |
| s3v2-diag-gemma3_12b-dev | 915f089c1db7 | running (20 worlds) |
| S2-dev-v2 | 01ca7072fb09 | complete: 670 ok, 0 failed (no `end` event, D27) |
| S2-dev-v2-mcdiag | 01ca7072fb09 | complete: 200 ok |

## Next exact actions
1. When qwen diagnostic completes: apply gate D29; interrupt the gemma diagnostic, run S1 panel on an idle machine, resume gemma diagnostic (same snapshot, `--resume`).
2. Launch held-out S3 panels (configs/s3v2_heldout_*.json) from a snapshot whose S3 code is byte-identical to 915f089c.
3. Build reports/REVIEW_READY_R2.md, acceptance_r2.json, manifest_r2, release v0.2.0-dev.
