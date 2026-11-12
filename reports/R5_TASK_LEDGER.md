# R5 task ledger (resumable)

Branch `iteration-5` (from `e6483a6`; R4 content `957c8d7`). Resume: read this file, `docs/R5_PROTOCOL.md`,
`docs/R5_DESIGN_LOCK.json` (once committed), then `git log iteration-5`. Runs execute from immutable snapshots
(`scripts/run_from_snapshot.sh <commit> <log> python -m causalguard run --config configs/r5/<cfg> --quiet`).
Cumulative resources: `python -c "from causalguard.r5.contracts import offline_usage, call_usage; ..."` over
`runs/` and `runs/r5-calls/ledger.jsonl` (see §Resources).

## State by work package

| WP | Task | State | Evidence / next |
|---|---|---|---|
| WP0 | branch, preserve user files | done | commit `3c0841a` (HANDOFF, takeover_r4, iteration_5 assignment, unchanged) |
| WP0 | baseline tests at e6483a6 | done | 448 passed (167 s); source digest `a8252d95…` |
| WP0 | baseline audit | done | `reports/R5_BASELINE_AUDIT.md` |
| WP1 | counting derivation | done | `docs/R5_COUNTING_DERIVATION.md` |
| WP1 | external inventory (BBM 314b2fe) | done | `artifacts/r5_source_manifest.json` (intact 4 groups; transformed 162 eligible -> 40 selected, 159 inst.) |
| WP1 | synthetic strata + splits | done | `src/causalguard/r5/data.py` (`G_POPULATION_SPEC`), split audit: 0 shared groups / duplicates / isomorphs |
| WP1 | generic counter / compiler | partial | d4v2 not buildable on arm64 (PaToH x86_64-only); ganak v2.9.0 binary download/execution DENIED by session permission classifier -> adapter only; independent GEN-VE implemented + validated |
| WP1 | AND counterexample + expanded class | done | `r5/misspec.py::and_counterexample`, test |
| WP2 | interfaces, accounting, tests | done | `r5/contracts.py`, CallBudget phase caps, runner memory guard, `tests/test_r5.py` (19) |
| WP3 | G calibration (64) | done | `configs/r5/g_calibration.json` |
| WP3 | A deterministic calibration (64) | done | `configs/r5/a_det_calibration.json` |
| WP3 | A AI interface calibration | done | `configs/r5/a_ai_cal_*.json` (<= 512 calls) |
| WP3 | design lock | done | `docs/R5_DESIGN_LOCK.json` |
| WP4 | G eval + external, C benchmark | done | |
| WP5 | M panels, A pilot | done | |
| WP6 | reports, demo, claim ledger, brief | done | |
| WP7 | release v0.5.0-dev | in progress | see reports/RELEASE_CHECK_R5.md |

## Calibration / development use (disclosed)

- A design calibration (deterministic policies only, calibration salt): evidence 8 vs 12 vs 16 observations and
  menu composition (8/4/4 vs 4/4/8 vs 3/3/10 target-near/other-near/random) on 32 calibration worlds. Chosen: 8
  observations, 4/4/8 (EIG resolves 25/32 at budget 4, privileged oracle 25/32, random 4/32). Reason: avoid a
  ceiling where every competent policy resolves everything; no AI output was used.
- M development probe: 10 worlds per panel on salt `r5-M-v1` (policy outputs seen). Evaluation uses salt
  `r5-M-eval-v1`; no M policy was changed after the probe except the challenge policy's purchase accounting
  (bought once per world, not once per query: an accounting defect, fixed before any evaluation).
- G: cost probes on calibration instance 0-1 of two strata (timings only).

## Runs (all development; snapshot in each plan)

r5-g-cal-v1 (64), r5-a-det-cal-v1 (64), r5-a-ai-cal-*-v1 (failed gate, R5-02), r5-a-ai-cal-*-v2, [lock dd193ce],
r5-g-eval-v1 (320), r5-g-ext-intact-v1 (4), r5-g-ext-transformed-v1 (159), r5-m-eval-v1 (120), r5-a-det-eval-v1 (64),
r5-a-ai-eval-qwen25_7b-v2 (64), r5-a-ai-eval-mistral_small_24b-v2 (64), r5-c-bench-v1 (failed 144, R5-03),
r5-c-bench-v2 (144), r5-c-bench-n64-genve-v3 (8, R5-04). Every planned item ok in the valid runs.

## Resources (cumulative, final)

| Resource | Ceiling | Used |
|---|---:|---:|
| Local model requests (all phases, incl. failed calibration) | 3,072 | **1,081** (calibration 342 / 512; evaluation 739 / 2,048; repair 0 / 512) |
| Offline CPU-hours (upper bound = sum of attempt seconds; A includes LLM wait time) | 64 | **3.86** (G 0.69, C 1.87, M 0.00, A 1.29) + ≈ 0.3 untracked development probes |
| Model-server execution hours (sum of request latencies + loads) | 12 | **1.23** (+ < 1 min loads) |
| Peak memory | 24 GiB global | worker ≤ 0.6 GiB; C child phases ≤ 1.9 GiB |
