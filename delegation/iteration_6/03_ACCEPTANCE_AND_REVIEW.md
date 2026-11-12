# R6 acceptance, reporting and return contract

## Required artifacts

| Artifact | Contents |
|---|---|
| `reports/R6_TASK_LEDGER.md` | Resumable state, takeover inspection, cumulative resources |
| `docs/R6_XDC_DERIVATION.md` | Track X derivation and limits |
| `reports/R6_XDC_AUDIT.md` | Oracle design, case counts, largest differences, planted-defect result, event-order check, verdict |
| `reports/R6_GENERALIZATION.md` | Track G6: primary, secondaries, distributions, reuse analysis, figures, against the lock's predictions |
| `docs/R6S_DESIGN_LOCK.json` | Track S pre-evaluation identities, comparator choice, budgets, predictions |
| `artifacts/r6s_source_manifest.json` | Track S inventory, exclusions, group split |
| `reports/R6_SCALE.md` | Track S: fit certificates, cost against n, primary, attribution, effect against n and reuse |
| `reports/R6_AI_GATE_LOOP.md` | Track A2: paired loop/no-loop result, accounting |
| `reports/CLAIM_LEDGER_R6.csv`, `reports/R6_EVIDENCE_MATRIX.md`, `reports/acceptance_r6.json` | As in R5, per track |
| `docs/R6_FUNDING_BRIEF.md` | What is now demonstrated, what is not, the next costed milestone |
| `artifacts/manifest_r6.json`, `reports/RELEASE_CHECK_R6.md` | As in R5 |
| `reports/REVIEW_READY_R6.md` | Reviewer entry point |

Acceptance fields per track (X, G6, S, A2): `implementation_status`, `evaluation_status`, `scientific_outcome`
(supported_in_scope / no_detected_advantage / adverse / inconclusive / not_evaluable), denominators, primary
estimate and interval with missingness bounds, gate results, defects, artifact paths. Completion and scientific
outcome are separate fields.

## What the reviewer will check

1. Does the oracle in the XDC audit really share no code with what it checks, and does the planted defect fail it?
2. Did every R6 evaluation attempt start after its lock commit, from that snapshot?
3. Is the G6 report faithful to the lock, including where the effect is absent (null stratum, non-sharing strata,
   published models at 16 observations)?
4. Is XDC-EB's fit certified on every world, fitted on public evidence only, and is its gap to exact XDC shown?
5. Was the Track S comparator chosen on calibration groups only, and are groups split before scoring?
6. Does the Track S conclusion survive missing predictions and the exclusion of groups seen earlier?
7. Is the A2 control run on the same worlds, with every request counted inside 512?
8. Are R5 and R6 n = 8 outputs byte-identical after the new code?

## Return

Give: content commit, peeled tag, release and asset identities, results by track with completion and outcome
separate, deviations and defects, resource totals, and anything you believe the reviewer got wrong in XDC or in this
plan. Your audit is an implementation-agent audit; the reviewer decides acceptance.
