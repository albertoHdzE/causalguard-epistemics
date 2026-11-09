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
| S1-dev-v1 | running/complete — check RUNS.jsonl end event |
| S1-dev-v1-satproof | to run after S1-dev-v1 (index_sat certificate levels with the fixed checker, D16) |
| s3-pilot-qwen25-7b-dev-v1, s3-pilot-gemma3-12b-dev-v1 | stopped, **invalidated** (B truncated; D19); kept |
| s3-pilot-qwen25-7b-dev-v2, s3-pilot-gemma3-12b-dev-v2 | running (resumable: rerun the same command with the same run id) |

## Blocked / external input needed
- Sprint start date (for pre-sprint vs sprint labelling).
- Review approval and a FREEZE_RECORD before any confirmatory run.

## Next exact actions
1. When S1-dev-v1 ends: `python -m causalguard run --config configs/s1_dev_satproof.json --quiet`, then `python -m causalguard analyze-s1 --run-id S1-dev-v1 --run-id S1-dev-v1-satproof`.
2. When both v2 pilots end: `python -c "from causalguard.analysis.s3_analysis import analyze; ..."` (see README) and write the S3 section.
3. Finalize DEVELOPMENT_REPORT, DESIGN_SIZING, confirmatory.json, claim ledger, release.
