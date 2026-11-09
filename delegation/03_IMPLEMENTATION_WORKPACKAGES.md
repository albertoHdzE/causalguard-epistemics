# Implementation work packages

## Ownership and working rules

Claude owns implementation under `AI-x-epistemics/`, including tests, experiment configuration, public release and the handoff. Treat CausalBool as a pinned, read-only upstream. Do not change neighboring projects or copy the entire monorepo. Existing preparation remains dated and attributable.

You may delegate bounded work to Claude subagents. Assign file ownership; tell each worker they are not alone, must preserve others' edits, and must adapt to shared changes. Useful parallel lanes after interfaces stabilize: oracle/representation; dataset/statistics; model runner/release. The lead owns integration and scientific semantics. Do not run multiple expensive experiments against the same hardware without a shared resource cap.

Use a package such as `src/causalguard/` with a `pyproject.toml`, pinned environment and `python -m causalguard` CLI. Prefer a minimal CPU-installable core; model training and additional solvers may be extras. Never require a commercial Wolfram installation for the public core.

## WP0 — inventory, isolation and provenance

Inspect applicable instructions, hardware, Python, available local model server, disk and Git/GitHub state. Do not print credentials or unrelated personal files. Record public-safe environment metadata. Establish the standalone repository and dependency strategy from document 04.

Deliver `ENVIRONMENT.md`, `UPSTREAM.md`, `DECISIONS.md`, `PREEXISTING_WORK.md`, `STATUS.md`, a dependency lock and tested install instructions. Pin upstream commit plus relevant file hashes. Verify the temporary clone before using it; recover from the public remote if absent. Date each work item as pre-sprint or sprint work based on its actual timestamp.

Acceptance: installation works in a clean environment independent of the original monorepo path; upstream origin/revision verifiable; no dependency on `/tmp` in ordinary commands. If upstream cannot be distributed under a clear license, use a pinned fetch adapter and independent original reference; record the unresolved redistribution question without relicensing third-party code.

## WP1 — typed semantics and fixtures

Implement immutable/validated types for world, ordered node rules, evidence, hypothesis class, quantifier, intervention, horizon, predicate, query result and certificate. Separate public model-facing payload from oracle/private labels. Reject invalid arities, nonbinary states, malformed constraints and unsupported operators. Serialization must round-trip without changing meanings.

Deliver `schema.py`, `semantics.py`, `fixtures/`, and tests. Add hand-derived AND/OR indistinguishability, XOR, NOT, Rule-110, overlap counts, input-order asymmetric gates when enabled, initial-edit versus clamp, synchronous versus sequential-update counterexample, zero horizon, impossible domains, inconsistent observations, resource-unknown and class-misspecification fixtures.

Acceptance: semantic fixture table explains each expected answer independently of the implementation. Typed invalid/unknown statuses cannot be coerced into truth values. Keep the original feasibility probe as historical evidence, not the new test oracle.

## WP2 — independent reference and query certificates

Implement a deliberately simple direct-rule simulator and exhaustive bounded query evaluator. This reference must not call the production index decoder/query implementation. Define result semantics using document 01. Certificates carry model/evidence/query hashes, scope, witness state or model pair, witness trace, and verification level.

Acceptance: every witness is independently replayable; incorrect witness, ordering flip, sequential update bug and quantifier swap are detected by tests. For unsatisfiability/universality, record exhaustive domain size or independent solver evidence; a lack of sampled counterexamples is not a certificate.

## WP3 — real index-family adapter and codec

Integrate the upstream mechanism using documented owners. If a new minimal representation is required, explicitly describe it as a compatible implementation and compare it against upstream on fixtures. Preserve anchor/offset-family semantics with don't-care positions on connected inputs. Provide membership, restricted-state existence, universality and bounded temporal queries. A supported hybrid with BDD/SAT is acceptable if conversions and backends are labelled.

Implement an independently decodable binary/archive codec with versioned spec, explicit lengths and deterministic serialization. Reject corrupted/truncated encodings and trailing malformed content. Charge complete metadata and decoder overhead according to the scientific contract. Do not equate a floating formula with actual archive bits.

Deliver `index_repr.py`, `codec.py`, `query.py`, `upstream_adapter.py`, `docs/CODEC.md`, independent decoder tests and parity fixtures. Codec baseline implementations must encode the same target object.

Acceptance: exact small-domain round trips; queries agree with the independent reference; Rule-110 compresses appropriately under the declared representation; OR/parity expose representation-specific scaling; overlap union/count handling is correct. Memory guards prevent hidden repertoire/offset expansion at large n. Prove what is possible to prove and label empirical parity as such.

## WP4 — incomplete evidence, version spaces and selection

Implement complete bounded candidate classes, compatibility filtering, version-space consensus, index-code selection and the required comparison selectors. Maintain distinction between explicit candidate pool and grammar-complete search. Add random and disagreement-guided measurement policies with equal evidence budgets. Keep chosen-model prediction separate from evidence entailment.

Acceptance: incomplete evidence does not silently collapse to one model; an omitted true world can produce wrong-but-class-consistent answers and is reported; incomplete search cannot certify agreement. Small classes cross-check against independent full enumeration. The selection API cannot access private hidden labels or full hidden repertoires.

## WP5 — dataset generator, grouping and audit

Implement S1/S2/S3 development and frozen-test generation from deterministic configs. Create opaque IDs unrelated to truth labels. Keep world derivatives within a split. Audit renamed/isomorphic duplicates at feasible sizes; log larger-size limitations. Track generator failures rather than rerolling until favorable results appear.

Deliver public task JSONL, separate private oracle records, split manifests, hashes, rejected-generation records, feature/label balance report and a leakage audit. Class balance must not destroy the intended prevalence estimates: publish natural and any balanced evaluation distributions separately.

Acceptance: byte-identical regeneration under fixed supported environment; no gold label in public payload/path/ID; sensitivity pairs change only intended premises; task grammar matches the renderer; all candidate methods get the same observations. Include trivial/majority and surface-feature-only baselines to detect shortcuts.

## WP6 — experiment runner and analysis

Implement resumable append-only runs with item/condition/seed IDs, configuration hashes, raw outputs, validation status, costs and failure records. Resume must not duplicate or overwrite results; reject mixed configurations. Bound resources and record wall-clock/model tokens separately. Offline analysis reads raw records and never calls a model.

Implement every metric and denominator from document 02, paired cluster bootstrap, power/precision simulation, timeout handling and deterministic tables/figures. Validate statistics with manufactured records having hand-computable answers, all-abstain/invalid cases, balanced/perfect/chance predictions, and known world clustering. Test shuffled condition labels and world pairing integrity.

Acceptance: all report numbers trace to run IDs; repeated analysis gives identical numeric tables; mocked/perfect-oracle output cannot appear in genuine model results; bootstrap resamples worlds rather than rows; power simulation outputs assumptions and uncertainty, not only a single N.

## WP7 — model harness and feedback controls

Implement an adapter for existing local HTTP model endpoints, with explicit configuration and a mock/replay provider only for tests. Do not assume a particular installed model. Store model revision where exposed, precision, chat template/settings, token cap and server version. If backend cannot honor random seeds or expose revisions, record this limitation instead of inventing them.

Implement A/B/C/D/D-label/E exactly as specified. Feedback derived only from permitted evidence, with its provenance. API transport errors get bounded declared retries; content errors stay content errors. Every retry consumes cost and is logged. Use timeouts and resumability. No autonomous secret discovery, paid model calls or downloading large weights just to fill a demo.

Acceptance: instrumented mock tests demonstrate arm isolation, call caps, shared initial-answer rules, no hidden-label leakage in D, intentionally labelled disclosure in D-label, and deterministic aggregation. A successful real pilot is distinguished from a transport-only smoke test.

## WP8 — substantial development experiments and freeze proposal

Run the minimum development programme from document 02, not just unit tests. Profile the larger grids with honest caps. Run S2 on at least 200 independent worlds and S3 on the development target if local inference is available. If unavailable, complete all symbolic work and produce exact pending model commands.

Produce `reports/DEVELOPMENT_REPORT.md`, machine-readable tables/figures, `reports/DESIGN_SIZING.md`, and proposed `configs/confirmatory.json`. Include model-independent symbolic results, negative cases, resource use, uncertainty and the actual remaining workload. Scope changes follow measured feasibility and are logged, never hidden reductions presented as the original protocol.

Acceptance: development evidence supports a runnable design; failures are explained or honestly unresolved; N comes from pilot sizing; confirmatory dataset has not been used for tuning. A ceiling/floor pilot requires development refinement before freeze, not fishing through final tests.

## WP9 — public release and first review package

Complete document 04, including a real separate GitHub URL if authentication permits. Run clean-clone installation and offline reproduction. Publish scripts/configs and releasable development evidence; keep sealed test material out until evaluation. Prepare document 05 artifacts and stop at the scientific review boundary.

Acceptance: review package identifies exact commit, commands, pass/fail counts, scientific limits and unresolved items. The public repository requirement is marked incomplete if no remote exists; never say “shared” based on a local repository alone.

## WP10 — persistent improvement after first review

Implement matched-budget prompt optimization on development failures versus independent prompt proposals. Select on validation only. Candidate count initially eight per arm; include the unchanged prompt. Freeze winner and evaluate new worlds/questions with no feedback. Compare per-world gains and cost. Clearly name this system/prompt improvement.

Acceptance: lineage records every candidate and selection query; both arms have matched search/validation opportunities; no final test used to select prompts. If no gain, preserve that result.

## WP11 — weight evolution after feasibility review

Retain the owner's neural mutation objective as a real experiment. Choose one compatible small base; train two adapters on disjoint skill-focused development subsets and a pooled-data adapter control. Merge effective deltas or use an equivalent adapter sum, not elementwise averaging of low-rank factors. Fixed coefficient grid includes both parents, base and uniform merge. Add equal-budget random and evolutionary coefficient search; use the same validation objective and candidate-evaluation budget.

Use ≥3 independent training/search seeds for an initial study, target 5 if resources permit; final sizing follows development variance and budget. Charge all training/search data and compute. Preserve unchanged base, both parents, pooled adapter, fixed merge and random search controls. Report functional regression and false-entailment changes alongside accuracy. All candidate selection is validation-only. Test weights actually differ and record tensor/revision hashes.

Acceptance: genuine held-out weight-level results with controls, or an explicit blocked/inconclusive status and measured resource requirement. A tiny neural Boolean predictor may be an auxiliary experiment but cannot stand in for language-model weight results. No claim of recursive self-improvement is supported solely by this experiment.
