# R7 execution plan (pre-sprint day)

Branch `iteration-7` (local; from `iteration-6` at `7316350` plus the director's commits). Keep
`reports/R7_TASK_LEDGER.md` from the first step. Every item of R7 is dated pre-sprint by its timestamp.

| WP | Work | Gate to pass before the next WP |
|---|---|---|
| WP0 | Takeover. Read the R6 review, this package and `docs/SPRINT_AUTHORISATION.md`. Confirm the unaided-arm harness (`s4/pilot.py`) still runs on a current world and that both exact engines agree on status for 200 fresh items. Open ledger phase `SPRINT`. | Engines agree 200 / 200. |
| WP1 | Reference probability p*, Task S scoring, reference rows, surface rule. Tests, including a planted scoring defect. | Tests pass with printed denominators. |
| WP2 | Task P: four conditions, two wordings each, hash assignment, public-information audit of every follow-up. Tests. | Audit passes on all pilot items. |
| WP3 | Smoke gate and throughput probe on every candidate local model. | At least four models pass, or report the block. |
| WP4 | Pilot: 32 pilot worlds, two models, Tasks S and P. `reports/R7_PILOT.md` with figures. | — |
| WP5 | The five gates of protocol §7 stage 2. Panel sizing. `docs/SPRINT_DESIGN_LOCK.json`, main-panel manifest and configs. A dry run of the full pipeline on a mock provider. | All gates pass. Lock committed. Dry run completes end to end. |
| WP6 | Main local panel from the lock snapshot, every model that passed the smoke gate. | Every planned item finished or accounted for. |
| WP7 | Analysis of the local panel with the multi-run analysis command. `reports/SPRINT_LOCAL_RESULTS.md` with figures. | Regenerating the analysis from the raw runs is byte-identical. |
| WP8 | Online adapters (DeepSeek, Claude Opus 5.5 through the command line): mock dry run, connectivity check, isolation proof, launch-ready configs. | No benchmark item sent. Isolation shown, or the block recorded. |
| WP9 | Related work with verified references (`docs/SPRINT_RELATED_WORK.md`). Report template in `report/`, building to PDF. `PREEXISTING_WORK.md` and README updated. | Every reference has a URL that was opened and a one-line note of what was checked. |
| WP10 | Push branch `iteration-7`. Return the summary. No release tag in R7; the sprint release follows the online runs. | — |

Order and priority: WP0–WP7 are the critical path. WP8 can be built while the main panel runs; keep offline work
light while a model server is busy so timings stay honest. WP9 can finish during the sprint if time runs short.

Engineering rules:

- One owner per concept. Task P extends the existing episode code; do not copy the prompt builder or the parser.
  Scoring lives in one module. The exact engines are used as they are. Provider adapters live beside the existing
  providers.
- Default arguments keep every R5 and R6 output byte-identical (`scripts/r6_regen_check.sh`).
- Every gate prints its denominator, refuses on empty input and exits non-zero on failure. Check that loop bodies
  actually ran.
- Every model request goes through the ledger, phase `SPRINT`, cap 6,000. Online connectivity requests are logged
  separately, at most 5 per provider.
- Runs execute from committed snapshots with `scripts/run_from_snapshot.sh`.
- Render before quoting: reports show per-world points, not only means.
- The API key is read at run time and never printed, logged, recorded or committed.
- Do not stop to ask routine questions. Record choices in `DECISIONS.md` (D70 onward).

Ceilings: 6,000 local model requests; 14 model-server hours for the main panel plus 3 for smoke and pilot;
24 CPU-hours offline. No weight changes. No benchmark item to an online model.
