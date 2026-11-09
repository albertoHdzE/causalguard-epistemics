# STATUS

_Last updated: 2026-11-09 (implementation iteration 1). Resume protocol: read this file, DECISIONS.md, RUNS.jsonl and `git status`; never relaunch a run id that has records — `causalguard run` resumes and skips completed items._

## Work packages

| WP | State | Evidence |
|---|---|---|
| WP0 inventory/isolation/provenance | done | ENVIRONMENT.md, UPSTREAM.md, PREEXISTING_WORK.md, requirements-lock.txt |
| WP1 typed semantics + fixtures | done | src/causalguard/schema.py, semantics.py, data/fixtures/semantic_fixtures.json, tests/test_schema.py, tests/test_fixtures.py |
| WP2 independent reference + certificates | done | reference.py, bdd_ref.py, proofcheck.py, tests/test_query_backends.py, tests/test_structure.py |
| WP3 index representation + codec + queries + upstream adapter | done | index_repr.py, codec.py, query.py, upstream_adapter.py, docs/CODEC.md, tests/test_index_repr.py, test_codec.py, test_upstream_parity.py |
| WP4 version spaces / selection | done | versionspace.py, tests/test_versionspace.py, tests/test_s2_isolation.py |
| WP5 generators / audit | done | generators.py, dedup.py, s3_tasks.py, reports/development/dedup_audit.json |
| WP6 runner / analysis / statistics | done | runner.py, stats.py, analysis/*.py, tests/test_stats.py |
| WP7 LLM harness | done | llm/*.py, experiments/s3.py, tests/test_llm_harness.py, docs/S3_HARNESS.md |
| WP8 development experiments + freeze proposal | see runs below | reports/DEVELOPMENT_REPORT.md, reports/DESIGN_SIZING.md, configs/confirmatory.json |
| WP9 public release + review package | see reports/RELEASE_CHECK.md | reports/REVIEW_READY.md |
| WP10 / WP11 | not started (subsequent iterations by design) | — |

## Runs (see RUNS.jsonl)

| run id | state |
|---|---|
| S2-smoke-tmp | 3-item smoke, directory deleted after the check (registry lines kept) |
| S2-dev-v1 | complete, 420 worlds, 0 failures |
| S1-dev-v1 | complete: 2,344 ok, 1 recorded failure (dd assertion, D20) |
| S1-dev-v1-rerun | complete: 670 ok (index_sat + bdd_ref, D16/D20); source for those backends |
| S2-dev-null-v1 | complete: 250 null worlds (D21) |
| s3-pilot-qwen25-7b-dev-v1, s3-pilot-gemma3-12b-dev-v1 | stopped, **invalidated** (B truncated; D19); kept |
| s3-pilot-qwen25-7b-dev-v2 | complete: 80 worlds, 2,400 physical calls, 0 failures (interrupted once and resumed, D22) |
| s3-pilot-gemma3-12b-dev-v2 | running (resumable: `python -m causalguard.experiments.s3 --config configs/s3_pilot_gemma3_12b.json --run-id s3-pilot-gemma3-12b-dev-v2 --worlds 80 --quiet`) |

## Blocked / external input needed
- Sprint start date (for pre-sprint vs sprint labelling).
- Review approval and a FREEZE_RECORD before any confirmatory run.

Public repository: https://github.com/albertoHdzE/causalguard-epistemics (CI green).

## Next exact actions
1. When the gemma v2 pilot ends: run the S3 analysis on both v2 runs (README), write the S3 sections of DEVELOPMENT_REPORT / DESIGN_SIZING / REVIEW_READY, add the S3 block to configs/confirmatory.json.
2. Build artifacts/manifest.json (`scripts/build_manifest.py <run ids>`), save reports/test-output.txt, commit, tag `v0.1.0-dev`, push, upload the release asset, verify CI and clone.
3. Stop at the review boundary (no confirmatory run).
