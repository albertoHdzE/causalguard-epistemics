# Iteration 5 — assignment to Claude Opus

Work in `/Users/alberto/Documents/projects/AI-security/AI-x-epistemics` (public repository `albertoHdzE/causalguard-epistemics`). Alberto has requested one substantial implementation/research batch covering the four directions identified after R4. **Execute this batch, not just a plan.** Use long resumable sessions, bounded experiments and an auditable ledger.

## Decision and authority

We are doing all four directions in one coordinated development batch:

1. **Main scientific question:** does OUR structured representation improve inference of unseen outcomes beyond the families designed to match it?
2. **Computational foundation:** what can our exact counting method guarantee, and how does its complete cost compare with competent alternatives?
3. **AI contribution:** can AI use the workspace to conduct useful investigations rather than degrade probabilities supplied by the solver?
4. **Reliability boundary:** what happens when the assumed model class is wrong, including when the observed evidence still fits it?

Depth is deliberately unequal: tracks 1 and 2 receive the main offline evaluation; track 3 is a bounded two-model pilot; track 4 is a mathematical counterexample plus a substantial offline diagnostic. All tracks produce concrete code, evidence and a report. Do not launch four unconnected large LLM studies.

This new user-requested batch supersedes the **planning-only** scope of `delegation/FABLE_RESEARCH_PROMPT.md` and the no-new-development-runs restriction in `HANDOFF.md`, only for the R5 work specified here. It authorizes the new bounded development runs below. It does not authorize old S1/S2 confirmation, the old S4 main study, a production freeze, paid inference or training weights. Leave `docs/FREEZE_RECORD.json` absent. Do not reinterpret a development design lock as a confirmatory freeze.

Read these files before implementing:

1. `HANDOFF.md` and `reports/takeover_r4/INSPECTION.md`;
2. `reports/REVIEW_READY_R4.md`, `reports/S4_DEVELOPMENT_REPORT.md`, `reports/S4_DESIGN_SIZING.md`;
3. `docs/S4_METHOD_COVERAGE.md` and `docs/S4_FOUNDATIONS_AND_PRECOMMIT_CHECKING.md`;
4. **all three** specifications in `delegation/iteration_5/`: `01_SCIENTIFIC_PROTOCOL.md`, `02_EXECUTION_PLAN.md`, `03_ACCEPTANCE_AND_REVIEW.md`, plus `BATCH_CONTRACT.json`;
5. the original formal manuscript and HID specifications pinned in the coverage document, and relevant current source/tests.

The inspected starting HEAD is `e6483a673303d69f0fbf43d52e30a6725b072542`; R4 content is `957c8d73be5a3a5a6c301929f7f4036d70d70ac3`. If HEAD has advanced, inspect and record the delta; do not reset others' work. The untracked handoff and takeover reports are intentional user work: preserve them and include them in the new branch/release as appropriate. Do not overwrite their historical evidence manifests.

## What must remain intellectually honest

- Our method comprises analytic index-set calculus, support-schema mechanism sets and a versioned hierarchical code. Do not substitute only the old flat selector or a generic SAT engine and call it the full method.
- Exact representations of the same models/weights should agree. The opportunities are computational reach, an appropriate learned/declared prior, and better investigation—not different logical truth from identical premises.
- R4's two AI models almost always said “underdetermined.” **226/228 blocked errors were false uncertainty; only two were wrong definite assertions.** Keep those categories separate.
- R4 backend stress timing excluded the complete commit gate; the gate can invoke the generic SAT solver. Measure both costs.
- SAT “RUP-checkable,” a checked proof and a process-authenticated decision are distinct. Record actual proof levels.
- Hierarchy-positive R4 families were generator-matched. New seeds alone are not a structural generalization test.
- No theorem about universal Kolmogorov complexity, universal algorithmic probability, world truth or superiority to Zenil follows from these experiments.

## Execution and gates

Follow WP0–WP7 in `02_EXECUTION_PLAN.md`. Foundation work and dataset/comparator design can run in parallel with explicit file ownership. Downstream numerical runs require passed semantic/provenance gates, never a positive treatment effect. If a track fails its validity gate, preserve its results and finish independent tracks; document the precise block instead of declaring the whole batch complete.

Before any R5 evaluation outcome, commit the protocols/configurations and `docs/R5_DESIGN_LOCK.json`. Separate calibration from evaluation. Any discovered semantic defect invalidates only affected runs and requires a new run/version; keep original records. No repeated generator/prompt revisions to make D win.

New ceilings: **3,072 local inference requests** across all R5 smokes, retries, pilots and any permitted repair; **64 aggregate CPU-hours** of offline experiment execution; **12 hours** of model-server execution time (sum across servers, not token generation CPU time); at most four offline workers and a global memory ceiling of `min(32 GiB, 25% of physical RAM)`. Measure cumulative usage across resumes. These are ceilings, not targets, and confer no permission to spend money. Further allocation details are binding in the contract. Lower concurrency when model serving shares the machine.

Keep existing models if technically suitable; model choice is not based on treatment effects. Opus is the implementation/research agent; evaluation inference uses local models. Do not turn Opus/API calls into an unrecorded experimental arm.

Do not stop to ask routine implementation questions. Use documented engineering judgment within the scientific contract. If an external comparator cannot be installed without unavailable privileges, attempt a documented supported alternative; continue independent work. If a budget or experiment scope really needs expansion, first finish the concrete proposal and all independently executable work, then explain the specific needed decision.

## Finish line

Produce a functioning system, all four bounded evaluations (or exact validity/resource blocks), mathematical derivations with independent small-case checks, the funding brief and the exact R5 review package in `03_ACCEPTANCE_AND_REVIEW.md`. Publish the authorized original code and redistributable development assets in the existing separate public repository as a **new development prerelease**, preserving older tags/assets. Verify a fresh clone/download, hashes and reanalysis. No upstream source or third-party model is relicensed by this instruction.

Return the reviewed content hash, peeled tag hash, release/asset identities, results by track, deviations, resource totals, and a prompt for the next reviewer. Your own audit is an implementation-agent audit, not an independent final scientific approval. The scientific success of a track and completion of its work are separate fields.
