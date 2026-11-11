# STATUS

_Last updated: 2026-11-11 (iteration 3, bounded repair after Codex review R2). Pre-sprint development (the sprint
starts 2026-11-13)._

**Resume protocol.** Read, in this order:
- this file;
- `DECISIONS.md` (D36+ for iteration 3);
- `git log` on branch `iteration-3`;
- `runs/registry.jsonl` (runtime registry; the tracked `RUNS.jsonl` is the frozen iteration-1 registry).

Every run is reconciled with `causalguard.runner.load_run(<run dir>)`. A run is continued only with `--resume`
under an identical plan. Only one live process may own a run (`docs/EXECUTION.md`). Runs execute from an immutable
snapshot worktree via `scripts/run_from_snapshot.sh <commit> <log> python -m ...`.

**Not authorized:** `docs/FREEZE_RECORD.json`, any confirmatory run, new LLM panels, and WP10/WP11. None of these
exists or was started (`reports/review_r2/DECISION.json`: `confirmatory_authorized: false`).

## Iteration-3 work items (reports/review_r2/REPAIR_SPEC.md A–D)

| Item | State | Evidence |
|---|---|---|
| A ownership, no-clobber, parent death, status, strict validation (R2-01..04) | implemented + tested | runner.py; tests/test_runner_r3.py; docs/EXECUTION.md; D37 |
| B completeness, RSS, phase (R2-05, R2-06) | implemented + tested; preserved data reanalysed (estimates unchanged) | analysis/s2_analysis.py, s1_analysis.py; tests/test_completeness_r3.py; reports/development_r3/; D38, D39 |
| C S3 offline corrections (R2-07..09) | implemented + tested; no model calls | analysis/s3_analysis.py, llm/parse.py, llm/harness.py; tests/test_s3_r3.py; docs/S3_FUTURE_DESIGN_R3.md; D42 |
| D reporting, smoke, audit, release | see REVIEW_READY_R3.md | DEVELOPMENT_REPORT_R3.md, ERRATA_R3.md, CLAIM_LEDGER_R3.csv, acceptance_r3.json, before_after_audit.json |

## Runs (iteration 3: execution smokes only, not evidence)

| run id | snapshot | state |
|---|---|---|
| dev-r3-smoke-s2 | c40c35f2e64d | complete 6/6 |
| dev-r3-smoke-s1 | c40c35f2e64d | complete 14/14; one deliberate supervisor-group SIGKILL and an immediate resume (D40) |
| dev-r3-final-smoke-s2 | 2209593a0f02 | complete 6/6 (final-source repeat; identical science) |
| dev-r3-final-smoke-s1 | 2209593a0f02 | complete 14/14 (final-source repeat; identical science) |
| dev-r3-release-smoke-s2 | 78e68378190a | complete 6/6 (release source after D44; identical science) |
| dev-r3-release-smoke-s1 | 78e68378190a | complete 14/14 (release source after D44; identical science) |

The iteration-2 runs (S2-dev-v2, S2-dev-v2-mcdiag, S2-dev-v2-repro, S1-dev-v2-panel, s3v2-*) are unchanged and were
reanalysed read-only.

## Next exact actions

1. None in iteration 3. Await Codex review R3 (`delegation/REVIEW_R3_REQUEST_PROMPT.md`).
2. Do not create a freeze record or run confirmation.
