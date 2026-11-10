# Iteration 2 — repair, strengthen controls, re-pilot, return for review

Authority: [R1 review](REVIEW.md). Scope: complete all work below in sustained, resumable development sessions. Do not create an approving `docs/FREEZE_RECORD.json`, generate final confirmatory worlds, or begin WP10/WP11. Dummy fixtures for testing the freeze lifecycle are explicitly authorized and must use an unmistakably non-confirmatory salt and temporary storage.

Preserve `371b04e`, `v0.1.0-dev`, the original run directories and their interpretations as historical development. Production repairs, new development experiments, publication and a revised review package are authorized. No paid inference is necessary. Continue with local compute and the existing model families; document actual model artifacts and runtime limits.

## P1 — exactness and immutable evidence (R01, R04, R05)

1. Replace the probability-equality verdict shortcut with exact Boolean support evaluation for supported one-step predicates, or SAT fallback. Keep probabilities separate. Test the review tautology, a contradiction, correlated repeated literals, clamp/edit/horizon-zero cases, and a genuinely possible low-probability counterexample. Cross-check with explicit small-class enumeration. No epsilon-based logical certification.
2. Establish a persisted item plan before execution. Bind each item's ID, world/design seed, study, population, family, source/config identity and expected output shape. Reject duplicate/conflicting IDs. Record which attempts supersede failed attempts without deleting the latter. Analysis must reconcile every planned item to a terminal result/failure and show missingness by stratum/backend.
3. Make log readers strict. An invalid interior line or duplicate conflicting result is corruption, not an exclusion. A torn final fragment may be quarantined with exact bytes, digest, offset and recovery event; then rerun only the incomplete item under its original identity. Atomic per-item records plus an index are acceptable. Test actual interruption and boundary-safe recovery, not just parser mocks.
4. Bind primary analysis to a machine-readable endpoint spec, or reject any mismatch with the supported executable spec. Require one world-level paired contribution per endpoint; queries and repeated sampling seeds are nested. Reject duplicate run arguments and ambiguous rerun combinations. Analyses cannot silently drop whole failed worlds. For the primary, a run with unresolved whole-world failures is incomplete; show bounded missing-outcome sensitivity and do not issue the planned-N primary claim until its frozen terminal rule is satisfied. Per-method invalid predictions retain their declared scoring rule.

Acceptance: regression tests fail on the old behavior and pass on the repair; existing development analyses remain reproducible via the historical version. New analyses explicitly identify changed semantics, not silently overwrite old summaries.

## P2 — freeze lifecycle and resource enforcement (R03, R06, R08)

- Keep frozen source/protocol/config immutable while runtime records live in ignored/external storage. Export checksummed runtime records for publication after execution. Do not solve the dirty-tree problem by discarding logs, changing the freeze commit between studies, or disabling source-integrity checks.
- Validate the review decision, approved studies/model identities, source and config hashes, endpoint version, required development manifest and readiness **before** creating/opening a run. Use explicit typed readiness, not prose-string matching. A denied/revise record cannot authorize any study.
- Implement resume bound to the same immutable plan, data, code and configuration. A rerun cannot regenerate a new salt or overwrite a completed result. Make starting a study, interruption, resume, and subsequently starting another approved study work at one freeze commit. Reject unapproved study/model, changed input and unintended reruns. Preserve an access/attempt ledger.
- Separate runtime caps from nested `SIGALRM` use. Enforce item deadlines with a supervisor capable of terminating/reaping a stuck process, or an equivalently tested design. Ensure solver timeout recovery and per-query caps cannot erase the overall deadline. Test a deliberately hung worker and nested timed operations; leave no orphan computation.
- Verify every required manifest file, including all development corpora used by duplicate audits. Distinguish an optional missing release asset from a required missing report. Do not claim complete verification when files were skipped.
- Make development and test duplicate audits comprehensive and explicit. Record semantic/isomorphic overlap and the deterministic exclusion/replenishment rule where exclusions apply. Preserve sampling-distribution interpretation: see the null rule below. S3 learned/fitted components must not reuse development mechanisms as test worlds.
- A seed derived from a public commit is a reproducibility identifier, not secret sealing. Document no-peeking as a process rule. Avoid a self-referential commit hash: the final reviewer record can bind a reviewed source/config identity, with the containing freeze commit supplied/verified externally.

Acceptance: end-to-end subprocess tests with dummy scientific items demonstrate S2→interrupt→resume→S1 at a single frozen fixture commit; corruption, wrong scope, missing required artifacts and changed endpoint are refused before scientific execution. No production freeze record is created.

## P3 — revised S2 scientific design (R02, R07)

Implement a **versioned exogenous design**. Draw primary measurement inputs, holdout inputs and intervention query specifications from a design RNG before evaluating the hidden mechanism. A hidden-mechanism swap with the same design seed must leave these specifications identical. Mechanism and design RNG streams must be distinct and recorded. Observational/active regimes may adapt only to their acquired public history, never to withheld regimes' outputs.

Reserve held-out effective inputs ex ante for one-step state prediction. Distinguish syntactic key novelty, effective-input novelty and multistep novelty in reports. An initial edit can be equivalent to an observed transition: report it as such. Do not remove unfavorable cases after scoring. The primary intervention grid can keep h∈{1,2,3}, both intervention types, and the original 16 queries, but freeze the sampling/novelty rule and expose the h=1 versus h>1 results separately. State precisely which claims concern interpolation versus unobserved transitions.

**Prospective primary:** realizable structured population, n=7,k≤3; equal weight across the five original families; uniform designed measurements; budget 16; world-level intervention accuracy of the index-code selected model minus the compatible-set majority predictor. Keep the deterministic code-selection tie-break and specify majority ties. Keep the original index-minus-random-compatible endpoint as historical secondary. Keep circuit-minus-majority and index-minus-circuit as named secondary estimates with per-family breakdowns; make no confirmatory significance claims for a collection of exploratory comparisons.

**Numerical comparator:** exact probabilities when tractable; otherwise explicitly name it a finite-sample Monte Carlo majority algorithm. Never silently call this exact Bayes prediction. On new development, compare fixed predeclared budgets 4,096 / 16,384 / 65,536 using independent seed streams, with exact small-space validation. Report probability error, near-tie fraction, decision-flip frequency and world-level contrast sensitivity. Choose the final sample budget solely for numerical stability/cost, not a favorable index result. Target aggregate contrast sensitivity below 0.002 on development, or explain why that precision is unavailable and weaken the planned claim. Predefine a maximum budget and a near-tie policy; no unbounded sampling until the preferred answer appears. If sequential stopping is used, its uncertainty statement must be valid for that procedure. Distinguish MC zeros/ties from exact zeros/ties.

**Mandatory uniform-H null:** keep canonical functions uniformly sampled from the complete class. For the theorem/sanity study, primary designs must be exogenous and draws must remain IID from that stated prior. Mechanism-dependent rejection, including rejecting isomorphic development overlaps, changes that prior. Default: retain IID null draws, audit/report overlap, and do not use development labels or a fitted predictor in this null comparison. Record this explicit exception to disjoint-mechanism exclusion, and report a sensitivity with semantic duplicates grouped where relevant. Alternatively, a conditioned null is permitted only if named and interpreted as conditioned; do not invoke exact uniform-H Bayes optimality for it. Validate the posterior-sampling/majority inequality by exhaustive small-H averaging; individual worlds may favor a non-Bayes rule.

**Claims and sizing:** select a superiority question for the revised primary, with a two-sided 95% world-clustered interval; report magnitude against the original 0.05 substantive reference. Do not introduce an equivalence claim in this iteration. Target 1,000 structured worlds (200/family) and **1,000 null worlds** for the future proposal, plus separately labelled stress populations. These are starting allocations, not an instruction to run confirmation. Recalculate precision/power for the revised comparator, null contrast and any explicitly proposed interaction using the new development data and numerical-comparator uncertainty. Do not promise high power for the observed small effect or adapt N to the final results. If a structured-minus-null interaction is only exploratory, label it so.

## P4 — substantial new S2 development

Use new versioned development salts, preserving all old runs. Run at least:

- 250 structured worlds: 50 per original family, all original evidence regimes and budgets;
- 250 IID uniform-H null worlds under the repaired exogenous primary design;
- 60 misspecified, 60 shifted and 50 noise-stress worlds, unless a demonstrated technical limit requires a documented scope reduction.

This 670-world target is development, not confirmation. First validate semantics and generator independence on small cases, then execute the batch without performance-based exclusions. Run the MC convergence diagnostic on a preselected balanced subset of at least 100 structured and 100 null worlds. Report the new primary, historical primary, null controls, per-family effects, query novelty, resource/failure counts and changed conclusions.

Keep noisy-MDL results descriptive. If claiming index-specific noise robustness, add circuit/other-code selectors under the identical residual/noise model and budget. Otherwise explicitly state that the comparison with exact matching addresses noise handling, not unique advantages of the index code.

## P5 — S1 repair validation and accounting

Preserve the reproduced original S1 findings. Re-run a development verification panel after core/runner fixes: at least two worlds per originally studied family/size cell, all applicable backends, with the original caps and an isolated machine during latency measurements. Cover high-n timeouts, checked proofs, codec round trips and interrupt cleanup. Full S1 confirmation remains prepared only.

Fix failure denominators and dependency-aware decoder accounting. Report archive sums as archive sums; report payload sums separately if intended. Either measure a runnable decoder dependency bundle under a stated interpreter/stdlib or label module-size accounting as partial/conditional. Do not inflate this into an approximation ordering of true Kolmogorov complexity. Remove the independent-query `3/M` generalization statement. Keep solver-only results distinct from checked certificates and document which proof artifacts can be independently replayed from the release.

## P6 — revised S3 development, not learning claims

Use a balanced challenge panel alongside clearly labelled natural-prevalence results. Construct feasible verdict balance within budget/horizon/intervention cells; disclose impossible cells and rejection rules. Include complementary target-polarity pairs and variable renamings, clustered under their base world. Do not count these transformations as new independent worlds. Save actual task objects and analyze them; do not reconstruct assumed defaults.

Use these mechanisms/controls:

| Arm | Purpose |
|---|---|
| A | Shared initial answer |
| B2 | Two self-critique turns, matching assisted-arm turns |
| C | Independent-sampling control; explicit sample/token budget |
| D-cert | Certificate **plus explicit label**, transparently privileged; two turns |
| D-label | The same label without mechanistic certificate; two turns |
| D-sample | Fixed K=2 uniformly sampled compatible mechanisms, sampled without target query, oracle label or previous answer conditioning; two turns with a frozen policy |
| E | Oracle ceiling, clearly distinguished from independent backend validation |

For D-sample, a finite sample's agreement does not certify universal agreement. Use common sampled mechanisms across items of a world where feasible, log sampling identity and verify the sampler cannot access the private query verdict. For D-cert vs D-label, the contrast tests the value of the mechanistic material **beyond disclosed answers**, not learning from undisclosed truth. Report realized tokens/time and context sizes; identical round caps alone do not make costs equal. Preserve legacy D results separately.

Add matched source-context probes T_A, T_B2, T_cert, T_label and T_sample on fresh related target questions. Choose **T_cert − T_label** target-item accuracy as the prospective S3 focus for this pilot; it asks whether mechanistic material helps within-world context reuse beyond a disclosed source answer. Report T_sample−T_B2 and same-item corrections as secondary exploratory diagnostics. Cross-world or durable improvement is not established by these probes; defer that claim to WP10/WP11. Count the base world as the cluster.

Fit simple surface and trivial baselines on development training worlds only, persist the fitted artifacts, and evaluate models and baselines on the identical held-out development panel. For eventual confirmation the baseline must already be frozen. Report per-class confusion, parsing/truncation, complement consistency, variable-renaming sensitivity, probability/verdict coherence and probability-vector scores. Distinguish Brier performance from calibration and from construct validity. State that a wide interval crossing zero means no clear effect detected.

Development sequence: an initial diagnostic panel of about 20 independent worlds per model, then a fixed held-out **100-world panel per model** using the two original local model families once mechanics/format are sound. Total target ≥120 worlds/model, with transformed items nested. Freeze prompt/task versions between panels; if revisions follow panel inspection, version and repeat on fresh development worlds. Do not keep tuning to obtain positive effects. Stop expansion for a documented validity/floor problem and return a complete diagnostic report rather than spending further calls on an uninterpretable comparison. Re-size future S3 from the revised endpoint; old 500/300 estimates are provisional.

## P7 — revised review package and public release

Update dating, decisions, protocol, claims, tests, actual costs and acceptance status. Correct `design_simulation(alpha=...)` or remove the unsupported parameter. Keep a requirement-to-evidence table for R01–R10. Add an explicit `confirmatory_authorized: false` in the handoff; no authorization phrase belongs in a revise decision.

Publish a new development commit/release in the existing separate public repository, preserving the old tag/assets. Include checksummed new raw records, fitted baselines, actual model identity/provenance and reproducible analysis commands. Verify a clean public clone, required-file completeness, remote visibility and CI. Do not commit hidden future labels or private conversation text.

Return `reports/REVIEW_READY_R2.md`, `reports/acceptance_r2.json`, a versioned artifact manifest, test outputs, run/attempt manifests, revised sizing, and the exact public URL/commit/tag. State which findings are fixed, which evidence was rerun, and which claims changed. Leave the production freeze record absent. The reviewer can then freeze S1/S2 independently if ready; S3 may remain development-only.
