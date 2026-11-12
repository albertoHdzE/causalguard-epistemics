# STATUS

_Last updated: 2026-11-11 (iteration 5: R5 batch G/C/A/M executed; development release v0.5.0-dev)._

**Resume protocol.** Read `reports/R5_TASK_LEDGER.md`, then `reports/REVIEW_READY_R5.md`, `docs/R5_DESIGN_LOCK.json`,
`DECISIONS.md` D54–D61, `git log` on branch `iteration-5`.

**Not authorized and not done:** production freeze, confirmatory runs, old S4 main study, paid inference, weight
changes. `docs/FREEZE_RECORD.json` absent.

## Next exact action

Independent review of R5 (`delegation/REVIEW_R5_REQUEST_PROMPT.md`). Optional, needs Alberto's permission: run the
ganak projected-counter comparison (`CAUSALGUARD_GANAK=<binary>`), which R5 could not run (D55).

---

## Iteration 4 status (historical)


**Resume protocol.** Read, in this order:
- this file;
- `reports/REVIEW_READY_R4.md`;
- `DECISIONS.md` (D45–D53 for iteration 4);
- `git log` on branch `iteration-4`;
- `runs/registry.jsonl`.

Runs are reconciled with `causalguard.runner.load_run`. Runs execute from immutable snapshots
(`scripts/run_from_snapshot.sh`).

**Not authorized and not done:** a production freeze, confirmatory runs, the 320–800-world S4 main study, paid
inference, weight changes, and WP10/WP11.

## Iteration-4 work packages

| WP | State | Evidence |
|---|---|---|
| P0 R3-01 / R3-02 | repaired + tested; S2 reanalysis identical | `reports/development_r4/p0_repair_evidence.json`; D46 |
| P1 method identity / contract | `docs/S4_METHOD_COVERAGE.md`, `docs/S4_PROTOCOL_DRAFT.md` | D47 |
| P2 workspace + adapters + gate | `src/causalguard/s4/`; tests `tests/test_s4_*.py` | D47–D49 |
| P3 tasks, evaluator, audits, offline map | runs `s4-map-dev-v2` (v1 preserved), `s4-stress-dev-v2` (v1 preserved), `s4-active-dev-v1`, `s4-known-dev-v1`, `s4-misspec-dev-v1` | `reports/S4_DEVELOPMENT_REPORT.md` §3–§8 |
| P4 pilot + sizing | `s4-pilot-qwen25_7b-v1`, `s4-pilot-mistral_small_24b-v1` (40/40 each); `reports/S4_DESIGN_SIZING.md` | D50–D53 |
| P5 prototype, reports, release | `python -m causalguard s4-demo`; `docs/S4_FUNDING_BRIEF.md`; review package | `reports/REVIEW_READY_R4.md` |

## Next exact action

Await Codex review R4 (`delegation/REVIEW_R4_REQUEST_PROMPT.md`). The main-study primary must be re-decided before
any main run.
