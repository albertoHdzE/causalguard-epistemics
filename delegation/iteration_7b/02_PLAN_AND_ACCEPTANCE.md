# R7b plan and acceptance (2026-11-12)

Branch `iteration-7`. Decisions from D79. Ledger phase `SPRINT`, cap 6,000 (466 used).

## Work packages

| WP | Work | Gate |
|---|---|---|
| B1 | Tier W: class, public wiring block, two exact implementations, cross-tier test, evidence-budget calibration on training worlds | Engines agree on every calibration item; cross-tier test passes |
| B2 | Derivations, verifier, P3 on Tier W, P4 on both tiers, forged status defined for every world | G6 on pilot worlds |
| B3 | Scoring: adoption, corruption, check discernment (plain and standardised), per-tier reporting. Hand-built cases and a planted defect | Tests pass with denominators |
| B4 | Pilot on fresh worlds: Tier W on three models, P4 on Tier H on two. Reasoning-first wording | — |
| B5 | Gates G1–G6, panel selection, timing decisions, lock, mock dry run of the whole panel | Lock committed |
| B6 | Main local panel from the lock snapshot | Every planned item finished or accounted for |
| B7 | Analysis and `reports/SPRINT_LOCAL_RESULTS.md`; regeneration byte-identical | — |
| B8 | While the panel runs: online configs for this panel, worked example, methods text in `report/`, `docs/SPRINT_TASKS.md` regenerated, `PREEXISTING_WORK.md` updated | — |

B1–B5 are the critical path. Keep offline work light while a server is busy. Push after B5 and again at the end.

Ceilings: 6,000 local requests in total; 30 model-server hours across the two servers for the main panel; the
main panel finishes by 10:00 local time on 2026-11-13 or the unfinished models are reported as unfinished. No
online request today beyond the unused connectivity probes.

## Required artifacts

- `docs/SPRINT_TASKS.md` regenerated: both tiers, five conditions, one P3 and one P4 example per tier.
- `tests/test_r7b_*.py`.
- `reports/R7B_PILOT.md`, `reports/R7B_GATES.md` with denominators.
- `docs/SPRINT_DESIGN_LOCK.json`, `artifacts/sprint_main_manifest.json` (tier per world), `configs/sprint/*.json`.
- `reports/SPRINT_LOCAL_RESULTS.md` with figures: overclaim against underclaim per model and tier; Task P by
  condition; adoption under P3 against adoption under P4 per model and tier; per-world points.
- One worked Tier W example, a claim whose status a reader can verify from the page, with its P3 and P4 messages.
- `reports/REVIEW_READY_R7B.md`.

## What the reviewer will check

1. On Tier W, status and counts agree between two independent implementations on every item, and the cross-tier
   test holds.
2. I can verify the worked example by hand.
3. Every P3 passes the verifier and every P4 fails it; the forged status never equals the true one.
4. Conditions and forgeries depend on the hash and public evidence only.
5. The lock precedes the first main-panel request; every model ran once from the snapshot; half-panel and
   left-out decisions were made from timing before the run.
6. Tier W budget and claim sampling were fixed on training worlds with no model output.
7. Scores are per world, bootstrapped by world or source group.
8. Ledger within the cap; no online benchmark request; key and account e-mail in no file.
9. Regeneration is byte-identical; R5 and R6 outputs unchanged.
10. Pilot replies were read, and the report says what the models actually did, with quotations.

## Return contract

Return when the local panel is analysed, or at the fallback, or at a stop. The summary gives: what was built; the
gates; the pilots labelled as pilots; the lock identity and time; main results per model and tier with intervals;
each prediction against its outcome; quotations from replies that show how models reach their verdicts; online
readiness for this panel with expected cost, time and subscription usage; deviations and defects; resources; and
"Where the director's plan is wrong or will not impress the judges". Start the reviewer at
`reports/REVIEW_READY_R7B.md`.
