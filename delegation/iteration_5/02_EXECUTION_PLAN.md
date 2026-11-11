# R5 execution plan and ownership

Read `01_SCIENTIFIC_PROTOCOL.md` and `BATCH_CONTRACT.json` first. This is one sustained implementation batch. Keep `reports/R5_TASK_LEDGER.md` current with done/running/blocked tasks, exact next command, source snapshots, artifacts and cumulative budgets. Resume from that ledger after context/session limits; do not repeat completed experiments.

## Ownership and independent work

Opus is the integrator. If agent delegation is available, use three bounded workers plus the integrator; otherwise perform the same responsibilities sequentially. Every worker must be told: **you are not alone in this codebase; do not revert others' work; respect assigned files and coordinate shared changes.**

| Owner | Responsibility / owned new files | Shared files requiring coordination |
|---|---|---|
| G worker | `src/causalguard/r5/data.py`, `forecast.py`, `priors.py`; G tests/configs; provenance/splits | Existing `s4/prior.py`, codec/schema owners |
| C worker | `src/causalguard/r5/counting.py`, `certificates.py`, `benchmark.py`; C tests/configs; theorem | `versionspace.py`, `s4/mechspace.py`, proofcheck |
| A/M worker | `src/causalguard/r5/investigation.py`, `misspec.py`; A/M tests/configs | `s4/checking.py`, `s4/workspace.py`, model adapter |
| Integrator | `r5/contracts.py`, `analysis/r5_analysis.py`, CLI, schemas, cumulative ledger, release/docs | All runner, shared defaults and registry changes |

These names are proposed boundaries, not a demand to duplicate existing owners. Reuse the repository's semantic owners. Record any relocation before workers edit overlapping files. Check graph tools first for code discovery when available. Do not introduce a framework rewrite or a second runner just for R5.

## Dependency graph

`WP0 → WP1 → WP2 → WP3 → {WP4, WP5, WP6} → WP7`

WP1 theorem/comparator work, population design, and misspecification fixture development may proceed in parallel. WP4/5/6 evaluation requires the relevant WP3 validity gates. A negative effect does not block another track. Timed benchmarks and model serving must be scheduled to avoid contention, even when development is parallel.

## WP0 — establish and preserve the baseline

1. Inspect status/history; create an R5 branch/worktree without discarding untracked handoff files. Record HEAD and R4 source digests. Preserve all v0.1–v0.4 tags/assets and manifests.
2. Read the takeover inspection and R4 review request. Reproduce only what is needed to establish the current base; reuse matching saved verification evidence where appropriate. Re-run tests after source changes. Record the localhost-fixture sandbox limitation separately if it recurs.
3. Audit R3 fixes and the R4 areas still awaiting scientific review: counts/weights, oracle isolation, duplicates, proof levels, D52, common gate cost. Call this an implementation audit, not independent approval. Reproducible defects get R5-xx identifiers with affected scope.
4. Update orientation docs for R5 while retaining R4 as the last completed release. Do not change historical acceptance reports. Preserve earlier negative results.

Deliverable: `reports/R5_BASELINE_AUDIT.md`, task ledger and a source/provenance snapshot. A semantic defect blocks dependent runs until repaired and checked, not all unrelated work.

## WP1 — derive, design and select comparators before evaluation

1. Write `docs/R5_COUNTING_DERIVATION.md`, including counterexamples to any overstated generalization, the n=2 example, dependency on k/horizon, bigint cost, and distinction from known-model state repertoires. Test exhaustive tiny cases and independent random cases with an oracle that does not call D.
2. Prepare source-pinned external-model retrieval and a deterministic inclusion/transformation log. Fetch only necessary data; preserve original citations/rights. Keep derivative source groups together. Do not redistribute third-party material without a clear basis; retrieval manifests can replace bundled files.
3. Design and hash synthetic generators and split rules. Ensure the held-out mechanisms exercise structures beyond exact cyclic templates/equal modules. Do not alter held-out rules after viewing their comparative forecasts.
4. Pin a generic counter/compiler and validate projected-count semantics, including duplicate support descriptions, auxiliary variables and unconstrained variables. An unavailable compiler is not evidence of its scientific inferiority. Prefer a supported build or independent variable-elimination fallback; document limits.
5. Implement the small misspecified-class AND example and a larger-class baseline. This can proceed even if external datasets or compilers are unavailable.

Deliverable: equations, source inventories, meaningful independent tests and a computational feasibility note. No LLM calls needed.

## WP2 — implement the four connected capabilities

### Required interfaces (adapt to existing owners)

- `Prediction`: query/source/snapshot IDs; exact numerator/denominator or explicit approximation bounds; target value convention; code/prior identity; fallback/refusal reason; resource costs.
- `CountResult`: unique-mechanism semantics; numerator/denominator; projection/support identity; backend/version; exactness; evidence/query hashes; witness/certificate references; build/query/checker costs.
- `InvestigationStep`: prior public state hash; proposed/accepted action; allowed menu; purchased observation; measurement cost; updated state hash; model calls and tool calls. The evaluator alone provides outcomes.
- `AssumptionCheck`: declared class; alternative classes; evidence consistency; verdict per class; aggregate guarantee; certificate level; abstention reason. Never use a hidden “misspecified” flag in this API.

### Required behavior

1. Cumulative budget accounting survives interruption/resume, retries and worker processes. Every inference request reserves a ledger slot before dispatch; classify uncertain interrupted requests as spent until reconciled. Persist offline CPU and server-execution estimates conservatively. Limit offline process-tree memory and clean up descendants.
2. Every incomplete/error/refusal result has a scheduled denominator. Never derive method availability from the first output row. Validate required method keys, query IDs, exact integer types and state-dependent nulls.
3. Fixed request replay gives equal logical operations across backends. Do not report a full gate speedup from backend-only timing.
4. Proof-level records distinguish witness replay, trusted exact computation, SAT solver assertion, independently checked RUP/other proof, and application authentication. Store independently replayable evidence where claimed.
5. The AI pilot uses the same uniform-H exact posterior/readout in both backend arms; codec-weighted forecasts stay in Track G unless introduced as a separately declared secondary. This avoids conflating prior and investigator effects.
6. A class-change action derives only from public evidence or a predeclared robust policy. Check against fixed expanded-class and always-abstain baselines.

Meaningful tests include: exhaustive tiny networks; projected counting multiplicity traps; malformed/stale certificates; impossible evidence; empty versus resource status; held-out payload leaks; duplicate/source-group split leaks; same query numerator under independent engines; wrong literal-versus-node forecast coding; interrupted budget ledger; missing rows; unsupported external semantics; and the AND misspecification counterexample.

## WP3 — calibration, design lock and validity gates

Use ONLY calibration/smoke data. Fix comparator selection, eligibility, thresholds, seeds, query generation, model artifacts, prompt hashes, budget enforcement, statistical code, fallback behavior and installed tools. Run the specified 64 G calibration instances. A/M interface calibration and computation smokes count against their stated ceilings.

Create `docs/R5_DESIGN_LOCK.json` plus versioned configs before evaluation. Include exact code hashes, population/source manifests, comparator identities, plan counts, group structure, endpoint directions, missingness rules, resource schedule, revisions already made and evidence of gate checks. Do not use `docs/FREEZE_RECORD.json` or invoke the confirmatory runner.

Mandatory gates:

- zero known semantic/count mismatches on the independent correctness suite;
- one-to-one/projection counting semantics established for the chosen baseline;
- no hidden-truth path into public payloads or policies;
- source groups and required rows accounted for;
- resource/refusal semantics and actual proof levels correct;
- AI action parsing ≥90% and no systematic truncation on calibration, separately by model/arm;
- deterministic replay and resume smoke succeed.

Effect size or “D wins” is never a gate. If a comparator remains incomplete, run independent tracks and label the dependent comparison incomplete. Do not declare a weak substitute equivalent to the intended comparator.

## WP4 — execute G and C

- G: 320 held-out synthetic instances; nested evidence budgets 8/16/24; locked external eligible source groups, with intact/transformed panels separate. No LLM calls. Full endpoint and family/coverage tables, source-group uncertainty and fallback bounds.
- C: five sizes ×eight base instances =40 base instances, matching queries across methods; instrument resource checkpoints and end-to-end gate costs. Reuse checkpoints from one timed execution where feasible, rather than blindly multiplying the full 300-second allowance across each budget. Prespecify the small repeated-timing subset.
- Freeze *run inputs* via immutable snapshots in the usual development runner. Analysis/code changes after a run get distinct identities; no silent overwrite.
- Stay within the combined 64 CPU-hour cap, including failed attempts and all four tracks' offline work. At the cap, finish analysis of scheduled attempts with explicit unrun rows and bounds; do not label an incomplete planned panel complete. Reserve resources for M instead of spending all on large C instances.

## WP5 — execute M and A

- M: 40 realizable, 40 evidence-inconsistent and 40 evidence-consistent misspecified base worlds, independent from calibration. Evaluate current gate, robust union gate, fixed expanded class and public-evidence challenge policy. Use seeded, bounded stress-case construction with an acceptance log. Count source pairs as clusters.
- A: two local models, 64 shared held-out worlds, two AI/backend arms, at most eight calls/episode. Deterministic policies and request replay are offline. Evaluate budgets 0/1/2/4 within one trajectory. Use the appropriate stopped prefix, not hindsight choice of the best round.
- Retain every recorded raw response, invalid action and failed call. At most one interface-validity repair is allowed, using the reserved 512 calls on fresh diagnostics; it cannot replace the evaluated panel after viewing its effect. If calibration consumed its allocation, stop and report rather than borrowing unrecorded calls.
- All simulator execution is local and artificial; this batch does not deploy an autonomous real-world action system.

## WP6 — integration and scientific interpretation

Build one reproducible demo: public evidence → unknown target → proposed investigation → purchased observation → checked conclusion → assumption challenge. Include a branch where the model-relative claim fails in the hidden simulator and the robust policy abstains. Make simulation, assumptions and certificate levels visible. Do not present a hidden oracle or handpicked demonstration as evaluation evidence.

Create one report per track and an integrated claim ledger. Separate these possible findings:

- generic tools improve AI;
- our representation improves computation;
- our prior improves unseen forecasts;
- AI improves investigation over a deterministic policy;
- the assumption-aware policy improves a risk/coverage tradeoff.

Any subset can hold. No evidence of one substitutes for another. Write a two-page funding brief around the actual demonstrated capability and a concrete next milestone, including a negative-results path.

## WP7 — public development release and review return

Follow `03_ACCEPTANCE_AND_REVIEW.md`. Commit original code/docs; publish a new `v0.5.0-dev` prerelease if the tag does not already exist (otherwise choose an unused version and document it). Raw development assets require checksums, download-back verification, a fresh-clone locked install and byte-identical reanalysis. Do not upload secrets, private transcripts, unpublished sealed confirmation data or third-party sources without redistribution rights.

Publishing this public development code/data follows Alberto's standing instruction to share the research. Do not publish a paper submission or send messages to third parties. If remote tooling is unavailable, finish the complete local release package and report the exact publication block.

End with `reports/REVIEW_READY_R5.md`, `reports/acceptance_r5.json`, `delegation/REVIEW_R5_REQUEST_PROMPT.md`, updated STATUS/README, and an explicit next-review decision. Do not certify your own work as independently approved.
