# R7 acceptance and review

## Required artifacts

| Artifact | Content |
|---|---|
| `docs/SPRINT_TASKS.md` | Exact task statement, verdict vocabulary, the four follow-up conditions in both wordings, with hashes. |
| `tests/test_r7_*.py` | Status and p* against both engines; scoring on hand-built cases; planted scoring defect; public-information audit of follow-ups; adapter dry runs. |
| `reports/R7_SMOKE.md` + JSON | Every candidate local model: parsable share, truncation, seconds per request, pass or fail with reason. |
| `reports/R7_PILOT.md` + analysis JSON + figures | Pilot on two models, labelled as pilot, including any revision and the worlds it used. |
| `reports/R7_GATES.md` + JSON | The five pre-run gates with denominators. |
| `docs/SPRINT_DESIGN_LOCK.json` | The lock: panel, models and order, any half-panel decision with the measured timing behind it, contrasts, predictions, what was seen before the lock. |
| `artifacts/sprint_pilot_manifest.json`, `artifacts/sprint_main_manifest.json` | Disjoint world sets. |
| `configs/sprint/*.json` | One config per model for the main panel, including the two online models, launch-ready. |
| `reports/SPRINT_LOCAL_RESULTS.md` + analysis JSON + figures | The main local panel: every score of protocol §2 and §3 per model with intervals, per-world distributions, reference rows, base rates, the worked example. |
| `reports/R7_ONLINE_READINESS.md` | Adapter design, mock dry run, connectivity check, the isolation proof for the command-line route, expected cost and wall time for tomorrow. |
| `docs/SPRINT_RELATED_WORK.md` | Verified references and an honest statement of overlap. |
| `report/` | Official template, builds to PDF, with section stubs, the required appendix, and the preexisting-work section. |
| `reports/REVIEW_READY_R7.md` | Reviewer entry point. |

## What the reviewer will check

1. Status and p* are exact and both engines agree on every pilot and main-panel item.
2. The surface rule cannot read the status off the items, and no model sits at floor or ceiling in the pilot.
3. Follow-up conditions are assigned by hash, independent of the model's answers, and leak no hidden value.
4. The lock precedes the first main-panel request, and every model ran once from the lock snapshot.
5. Any model on a half panel was assigned to it before its run, from timing alone.
6. Scores are computed per world and bootstrapped by world (by source group for published-mechanism worlds).
7. Pilot and main-panel worlds are disjoint; wording was fixed on pilot worlds only.
8. Every request is in the ledger, within 6,000; no benchmark item reached an online model; the key appears in
   no file, log or record.
9. The command-line route for Claude Opus 5.5 is shown to pass our prompt and nothing else.
10. Regenerating the local analysis from raw runs is byte-identical, and R5 and R6 outputs are unchanged.
11. Every reference in the related-work file was opened, and the overlap statement is fair.
12. Nothing in the report skeleton presents preexisting work as sprint work.

## Return contract

Return a summary with: what was built; smoke results per model; the gates; pilot results labelled as pilot; the
main local results per model with intervals; each recorded prediction against its outcome (yours and the
director's); the readiness of the two online models with expected cost and time; what already exists in the
literature and what appears to be new; deviations and defects; resources used; and a section "Where the
director's plan is wrong or will not impress the judges", with evidence. Start the reviewer at
`reports/REVIEW_READY_R7.md`.
