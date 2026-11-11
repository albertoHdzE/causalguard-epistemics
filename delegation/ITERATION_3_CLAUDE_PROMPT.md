# Claude — complete iteration 3, then return for freeze review

Work in `/Users/alberto/Documents/projects/AI-security/AI-x-epistemics`, public repository `https://github.com/albertoHdzE/causalguard-epistemics`.

Codex reviewed content commit `161123c98f88f78637c81b13b93d0749ae03243f` and the docs-only release commit `9de376bf5fee11688d82463d1a4d7808867203e1`. The revised S2 science is accepted in substance, but S1/S2 confirmation is not yet authorized. This iteration is a bounded repair, not another search for favorable empirical results.

Read, in order:

1. `reports/review_r2/DECISION.json`
2. `reports/review_r2/REVIEW.md`
3. `reports/review_r2/REPAIR_SPEC.md` — complete sections A–D
4. `reports/review_r2/EVIDENCE.md` and diagnostic scripts/results
5. `reports/REVIEW_READY_R2.md`, `DECISIONS.md`, and relevant implementation/tests

Persist through substantial resumable sessions until A–D are complete and a new development release is public. You may delegate independent implementation/review tasks to agents with explicit file ownership; tell each worker it is not alone and must preserve others' edits. Coordinate the shared loader/metadata contract before parallel edits. Keep source snapshots immutable during any smoke run and record all interruptions or deviations.

Priorities: exclusive run ownership and no-clobber attempts; parent-death worker cleanup; truthful completion status; strict plan/attempt validation; exact endpoint completeness; S1 RSS correction; offline S3 shortcut/coherence/novelty corrections. Preserve existing scientific data and historical releases. Run targeted regression tests, full applicable checks, small runner smoke panels, offline reanalysis and the clean public-clone verification. No large replacement S2/S1 panel is necessary unless a demonstrated scientific defect requires one.

Do not create a production freeze record, run confirmation, call LLMs for new panels, or start WP10/WP11. Do not change the accepted S2 endpoint, fixed proposed sample sizes, tie rules or generators to improve the observed effect. Keep S3 exploratory; produce only the bounded future-design note requested by section C.

Return `reports/REVIEW_READY_R3.md`, acceptance/evidence mapping, checksummed corrected artifacts, exact public content commit, release tag and test/CI results. Report remaining limitations candidly. Keep `confirmatory_authorized: false` and `docs/FREEZE_RECORD.json` absent. Codex will review the concrete revised implementation and issue a scoped S1/S2 freeze only when the remaining requirements pass.
