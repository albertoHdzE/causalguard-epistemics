# R5 acceptance, reporting and return contract

## Required artifacts

| Artifact | Required contents |
|---|---|
| `reports/R5_TASK_LEDGER.md` | Resumable task state, dependencies, exact next action, cumulative resources |
| `reports/R5_BASELINE_AUDIT.md` | R4 audit, repaired defects, unchanged history, implementation-audit label |
| `docs/R5_COUNTING_DERIVATION.md` | Definitions, assumptions, derivation, complexity including bit costs, relation to prior methods |
| `docs/R5_DESIGN_LOCK.json` | Pre-evaluation code/config/data/group/endpoint/comparator/model/proof/budget identities |
| `docs/R5_PROTOCOL.md` | Final concrete operational protocol, calibration decisions and deviations from this assignment |
| `artifacts/r5_source_manifest.json` | External model identities, citations, rights, inclusion/exclusion, transformations and source groups |
| `reports/R5_GENERALIZATION.md` | G full-denominator predictions/coverage; primary, ablations, external panels, intervals, failure bounds |
| `reports/R5_COUNTING_AND_COST.md` | C exactness, comparator validity, workspace versus full release, censored cost curves, memory |
| `reports/R5_AI_INVESTIGATION.md` | A baselines, both models, all action/call failures, policy-versus-backend attribution |
| `reports/R5_ASSUMPTION_FAILURES.md` | M exact counterexample, selected stress distributions, assumptions, false verification and coverage |
| `reports/CLAIM_LEDGER_R5.csv` | Claim, population, endpoint, evidence, status, limits, disconfirming evidence |
| `docs/R5_FUNDING_BRIEF.md` | Actual capability, independent value, open risk, costed next milestone; no promised universal truth |
| `reports/R5_EVIDENCE_MATRIX.md` | Every WP/track requirement mapped to code, test, artifact or precise block |
| `artifacts/manifest_r5.json` | Required/optional files, exact hashes, remote asset mapping; historical manifests preserved |
| `reports/RELEASE_CHECK_R5.md` | Code/tag identity, CI, download-back, fresh clone, pinned install and regenerated outputs |
| `reports/REVIEW_READY_R5.md` | Concise reviewer entry point, findings, deviations, limitations and next decisions |
| `reports/acceptance_r5.json` | Machine-readable completion and scientific outcome, separately for each track |
| `delegation/REVIEW_R5_REQUEST_PROMPT.md` | Exact review commit and tests/reproductions needed, without presuming acceptance |

Keep CSV/JSON per-group/per-world metrics and enough raw logs for reconstruction. Model artifacts, quantization, context, templates and server versions must be pinned where available; missing digests are disclosed. Original data live in immutable development run records with source snapshots.

## Acceptance fields

For each G/C/A/M track report:

- `implementation_status`: complete / partial / blocked;
- `evaluation_status`: complete / incomplete / invalidated / not_run;
- `scientific_outcome`: supported_in_scope / no_detected_advantage / adverse / inconclusive / not_evaluable;
- planned/attempted/completed/failed/unrun counts and independent source-group counts;
- primary comparator, endpoint, effect direction, estimate/interval and missingness bounds where applicable;
- exact/approximate/unsupported status and certificate levels;
- resource totals, gate results, known defects, artifact paths and hashes.

Top-level fields include content commit, peeled tag, protocol/design-lock hashes, all source snapshots, code changes after runs, calibration use, cumulative model requests (including retries), offline CPU-hours, model-server execution hours, incomplete panels, release verification, `confirmatory_authorized: false`, `confirmatory_run: false`, `freeze_record: false`, `paid_inference: false`, `weight_changes: false`, and `independent_review_complete: false`.

A track with a negative result can be complete. A track with missing planned worlds cannot be called complete merely because the completed subset is favorable. A missing strong comparator limits comparative claims even if our implementation is correct.

## Required review questions

1. Is the G primary genuinely structurally held out, or a variation on a generator/codec jointly chosen to win? Are external transformations/source groups honest?
2. Were comparator/parameters selected only on calibration? Is there a real generic structured comparator, or is its absence explicitly limiting claims?
3. Does full CGH retain its declared prior and support? Are exact distinct mechanisms weighted once? Are target value and literal truth distinguished?
4. Are all scheduled results accounted for, with correct paired/source clustering and meaningful uncertainty? Do conclusions survive failure bounds?
5. Does generic counting count mechanisms instead of auxiliary CNF encodings? Are the derivation and external comparator independent of D's implementation?
6. Does a computational advantage survive compilation, repeated queries, witness replay and full proof-check/commit cost? Are timeouts and memory measured fairly?
7. Does AI outperform a competent deterministic investigation policy, or simply reproduce/degrade it? Does the backend comparison hold information, prior and policy fixed?
8. Does the misspecification defense use only public information? Is its benefit more than a fixed expanded-class baseline or abstaining on everything?
9. Are there actual independently checked proof artifacts where claimed? Are process signatures described only as authentication?
10. Were budgets, development labels, historical findings, source rights and public release identities preserved?

## Interpretation and next decision

Recommend only one future main study based on these results and a prospectively stated rationale. Do not authorize it yourself. Examples:

- G generalizes and C is useful: propose a held-out inference study plus an end-to-end AI integration evaluation.
- C succeeds but G does not: lead with exact uncertainty computation; do not market a universal simplicity advantage.
- G succeeds but AI loses to the controller: use a deterministic inference layer; test AI in formulation/communication separately.
- M improves safety only by heavy abstention: propose better evidence collection; do not claim a solved correctness guard.
- No method-specific advantage survives: preserve the rigorous result, identify the failed assumption and propose a genuinely different mechanism rather than enlarging the same experiment.

The final plain-English report must answer: what OUR method contributed, where it helped, where it did not, what the AI contributed, what remains unsafe under wrong assumptions, and what the next funding tranche would test.
