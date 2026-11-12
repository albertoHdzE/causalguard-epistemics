# R7 acceptance and review

## Required artifacts

| Artifact | Content |
|---|---|
| `docs/SPRINT_TASKS.md` | Exact task statement, verdict vocabulary, the four follow-up conditions in both wordings, with hashes. |
| `tests/test_r7_*.py` | Status and p* against both engines; scoring on hand-built cases; planted scoring defect; public-information audit of follow-ups. |
| `reports/R7_SMOKE.md` + JSON | Every candidate model: parsable share, truncation, seconds per request, pass or fail with reason. |
| `reports/R7_PILOT.md` + analysis JSON + figures | Pilot on two models: every score of protocol §2 and §3 with world-level intervals, per-world points, reference rows, status base rates. |
| `docs/SPRINT_DESIGN_LOCK.json` | The lock for the sprint's main run, with panel sizing, expected wall time and your predictions. |
| `artifacts/sprint_pilot_manifest.json`, `artifacts/sprint_main_manifest.json` | Disjoint world sets. |
| `configs/sprint/*.json` | One config per model and task for the main panel, ready to run from the lock snapshot. |
| `docs/SPRINT_RELATED_WORK.md` | Verified references and an honest statement of overlap. |
| `report/` | Official template, builds to PDF, with section stubs, the required appendix, and the preexisting-work section. |
| `reports/REVIEW_READY_R7.md` | Reviewer entry point. |

## What the reviewer will check

1. Status and p* are exact and both engines agree on every pilot and main-panel item.
2. The surface rule cannot read the status off the items.
3. Follow-up conditions are assigned by hash, independent of the model's answers, and leak no hidden value.
4. Scores are computed per world and bootstrapped by world (by source group for published-mechanism worlds).
5. Pilot worlds and main-panel worlds are disjoint, and no model has seen a main-panel world.
6. Wording was fixed on pilot worlds only, and the lock is committed.
7. Every request is in the ledger; the total is within 600.
8. Every reference in the related-work file was opened, and the overlap statement is fair.
9. R5 and R6 outputs remain byte-identical.
10. Nothing in the report skeleton presents preexisting work as sprint work.

## Return contract

Return a summary with: what was built; smoke results per model; pilot results with intervals, labelled as pilot;
the proposed main panel (models, worlds, wall time, precision); what already exists in the literature and what
appears to be new; deviations and defects; resources used; and a section "Where the director's plan is wrong or
will not impress the judges", with evidence. Start the reviewer at `reports/REVIEW_READY_R7.md`.
