# R7 execution plan (pre-sprint day)

Branch `iteration-7` (local; from `iteration-6` at `7316350` plus the director's commits). Keep
`reports/R7_TASK_LEDGER.md` from the first step. Every item of R7 is dated pre-sprint.

| WP | Work | Gate to pass before the next WP |
|---|---|---|
| WP0 | Takeover. Read the R6 review and this package. Confirm the unaided-arm harness (`s4/pilot.py`) still runs on a current world and that both exact engines agree on status for 200 fresh items. | Engines agree 200 / 200. |
| WP1 | Reference probability p*, Task S scoring, reference rows, surface-rule audit. Tests, including a planted scoring defect. | Tests pass with printed denominators. Surface rule well below the checker on pilot worlds, or generator settings changed and recorded. |
| WP2 | Task P: four conditions, two wordings each, hash assignment, public-information audit of every follow-up message. Tests. | No hidden value appears in any follow-up outside a P3 witness (audited on all pilot items). |
| WP3 | Smoke gate and throughput probe on every candidate model. | At least four models pass, or report the block. |
| WP4 | Pilot: 32 pilot worlds, two models, Tasks S and P. Analysis and `reports/R7_PILOT.md` with figures. | — |
| WP5 | Panel sizing, `docs/SPRINT_DESIGN_LOCK.json`, main-panel manifest and configs, a dry run of the full pipeline on a mock provider. | Lock committed. Dry run completes end to end. |
| WP6 | Related work with verified references (`docs/SPRINT_RELATED_WORK.md`). Report template in `report/`, building to PDF. `PREEXISTING_WORK.md` and README updated. | Every reference has a URL that was opened and a one-line note of what was checked. |
| WP7 | Push branch `iteration-7`. Return the summary. No release tag in R7; the sprint release comes after the main run. | — |

Priority if time runs short: WP0–WP5 first. WP6 can finish during the sprint.

Engineering rules:

- One owner per concept. Task P extends the existing episode code; do not copy the prompt builder or the parser.
  Scoring lives in one module. The exact engines are used as they are.
- Default arguments keep every R5 and R6 output byte-identical (`scripts/r6_regen_check.sh`).
- Every gate prints its denominator, refuses on empty input and exits non-zero on failure. Check that loop bodies
  actually ran.
- Every model request goes through the existing ledger with phase `R7`, cap 600.
- Runs execute from committed snapshots with `scripts/run_from_snapshot.sh`.
- Render before quoting: the pilot report shows the per-world points, not only means.
- Do not stop to ask routine questions. Record choices in `DECISIONS.md` (D70 onward).

Ceilings: 600 model requests; 4 model-server hours; 16 CPU-hours offline. No paid inference, no weight changes, no
main-panel run.
