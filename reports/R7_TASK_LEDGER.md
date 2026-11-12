# R7 task ledger (resumable; pre-sprint work)

Branch `iteration-7` (local), from director commit `fdcfac6`. Implementation agent: Claude Opus 5.5, from
2026-11-12. Everything in R7 is **pre-sprint** work (before the Apart sprint opens 2026-11-13) and is labelled so.
Resume: read this file, `delegation/iteration_7/*.md`, `docs/SPRINT_AUTHORISATION.md`, `docs/SPRINT_DESIGN_LOCK.json`
(once committed), then `git log iteration-7`.

## State by work package

| WP | Task | State | Evidence / next |
|---|---|---|---|
| WP0 | takeover, harness check, engines agree on 200 fresh items, ledger phase SPRINT | done | 200/200 claims (25 train worlds); new ledger `runs/sprint-calls/ledger.jsonl` |
| WP1 | p*, Task S scoring, reference rows, surface rule, tests | done | `sprint/scoring.py`, `sprint/surface.py` (D71), planted defects caught |
| WP2 | Task P conditions, wordings, hash assignment, leak audit, tests | done | 256/256 pilot and 240/240 main messages pass the audit |
| WP3 | smoke gate on every candidate local model | done | 7 models pass after the D73 repairs; R1 v1 stopped by operator error (D75), v2 pass |
| WP4 | pilot | done, 3 pilots | `reports/R7_PILOT.md` (pilot numbers) |
| WP5 | five gates, sizing, lock | **STOPPED: G3 failed after two revisions (D76, D78)** | `reports/R7_GATES.md`; draft lock only; 240-world mock dry run done |
| WP6 | main local panel | not run (protocol stop rule) | option-A configs `configs/sprint/main_*.json` ready |
| WP7 | analysis of the local panel | not run (no panel); analysis command built and tested on pilots and mock | `reports/sprint_pilot*/` |
| WP8 | online adapters, dry run, connectivity, isolation proof | done | `reports/R7_ONLINE_READINESS.md`; 2 + 1 probes |
| WP9 | related work, report template, PREEXISTING_WORK, README | done | `docs/SPRINT_RELATED_WORK.md` (14 references opened), `report/` builds PDF and docx |
| WP10 | push branch, return summary | done | `reports/REVIEW_READY_R7.md` |

Requests: 466 local (phase SPRINT) of 6,000; 3 online connectivity requests (no benchmark item).
