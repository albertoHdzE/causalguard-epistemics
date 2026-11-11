# Claude iteration 4: implement our full epistemic hypothesis and prepare a decisive evaluation

Work in `/Users/alberto/Documents/projects/AI-security/AI-x-epistemics`, public repository `albertoHdzE/causalguard-epistemics`. Continue sustained implementation sessions and maintain a resumable task ledger. The user explicitly wants a rigorous, funding-relevant investigation of **OUR** compression method helping AI infer unknown facts. A package of minor benchmark improvements alone does not meet that objective.

**Updated 2026-11-11 before implementation:** the user clarified that this is a complexity-science/algorithmic-modeling program, with Boolean systems as the first experimental tool. Implement the formal-paper mapping and pre-release checking workflow described in the amendment below. The original pilot/main-study boundaries still apply.

Read, in order:

1. `reports/review_r3/REVIEW.md` and `reports/review_r3/DECISION.json`;
2. `reports/FAMILY_MAP_AND_METHOD_SCOPE.md`;
3. `docs/S4_FOUNDATIONS_AND_PRECOMMIT_CHECKING.md` (the user-requested amendment; mandatory);
4. `docs/RESEARCH_DIRECTION_S4.md` (the scientific direction and constraints);
5. current source/docs, the original formal-method paper and HID references named in those documents;
6. `reports/REVIEW_READY_R3.md` for the accepted starting state.

Frame the paper as algorithmic models for verifiable AI reasoning, not as a Boolean-only research ambition. Upper bounds on program complexity, codec-induced probabilities and formal proofs are different objects; implement the separation in the amendment.

The reviewer found a material scope mismatch: current S2 tests shortest **flat** index-code selection, whereas the user's proposal includes a compact ordered/shared hierarchy and reasoning over possibilities. Implement a precise version of the broader method and compare it against a serious generic symbolic alternative. Do not assume superiority, relabel a SAT-only improvement as an index improvement, or hide the old null results.

## Authorized scope and boundaries

Execute the work below through a bounded local development pilot and a complete review-ready package. This supersedes iteration 3's no-new-model-call limit for the **new S4 development pilot only**. It does not authorize confirmatory runs, a production freeze, paid inference, weight modification, or WP10/WP11. Preserve the old sealed S1/S2 plans and all historical results. Do not launch the 320–800-world/model main S4 evaluation yet: the concrete new method, pilot-derived sizing and cost contract must be reviewed first.

No permission question is needed for routine implementation, tests, independent reconstruction from published specifications, offline benchmarks, bounded local pilot calls, documentation, or the established public development-release workflow. If a dependency genuinely cannot be satisfied, complete all independent work and return the exact blocker. Never fabricate a model call or substitute fixture outputs for scientific evidence.

## Work packages and ownership

If using parallel workers, assign explicit ownership below. Tell every worker they are not alone in the codebase, must not revert others' edits, and must accommodate concurrent changes. A single integration owner controls schema/API definitions and shared runner changes.

### P0 — close the two bounded R3 defects

Owner: runner/analysis maintainer; files `runner.py`, `analysis/s2_analysis.py`, associated tests.

- Fix R3-01 missing prediction keys/state semantics and denominator filtering. Add first/middle/last-row omissions, nonempty nulls, empty-V behavior and noise-method cases. Scientific output must never claim completeness when a planned method result is absent.
- Fix R3-02 dead-supervisor startup using a synchronous guard after worker-lock acquisition, plus immediate-side-effect and late-start/resume tests. Retain the watchdog for later death.
- Rerun appropriate lifecycle and completeness tests, full suite, and offline analyses. Show unchanged historical effects/CSV. No large experiment rerun.
- Keep this repair independently reviewable from S4. Do not let it consume the whole iteration.

### P1 — establish method identity and a falsifiable contract

Owner: scientific/schema integration lead; `docs/S4_METHOD_COVERAGE.md`, `docs/S4_PROTOCOL_DRAFT.md`, new S4 config/schema.

- Fulfil every item in the method-coverage section of `RESEARCH_DIRECTION_S4.md` before any model call.
- Pin the original formal-method manuscript and HID specification/source identities; map the analytic calculus, flat codec and fuller hierarchy separately. Include the manuscript's parity, threshold, ordering and support-locality capabilities, with independently checked conventions. Document the remaining assignment count `2^|C_q|` separately from the reduction factor `2^(d_q-|C_q|)`; distinguish strict majority from ties. Inspect applicable local AGENTS instructions. Do not copy upstream unlicensed implementation.
- Define the exact encoded object, public evidence, complete H versus sampled candidates, multiplicity semantics, order cost and symbolic operations. Include a hand-checkable worked example with opposing mechanisms and a measurement that separates them.
- Explicitly distinguish complete state repertoires from complete compatible-mechanism sets. If only a bounded version is feasible, name that boundary and implement it faithfully; never use hidden truth to construct the agent's model.
- Add the amendment's mathematical contract: fully charged executable descriptions give complexity upper bounds; codec-induced averaging is an optional offline secondary, not measured universal algorithmic probability. Define proof, forecast, underdetermination and resource refusal separately.
- Define supported initial sizes using offline computational evidence, not treatment effect. Preserve the intended eight family strata and strong baselines; document necessary mathematical amendments before calls.

### P2 — implement the workspace and baseline adapters

Owner: representation worker; new S4 representation/workspace modules and tests. Avoid changing historical codec meanings.

- Implement the supported analytic index-set predicates from the formal paper alongside the ordered/shared hierarchy, using the existing HID language as the starting serialization specification. Do not force analytic parity/thresholds into exponentially large flat cubes; version any wire extensions and charge all representation costs. Expose provenance/method IDs, paid ordering/shared references and exact decoding.
- Implement evidence update, query, witness and bounded counting operations over the declared object. Meter enumeration and fallback separately. An encoder/decoder alone is insufficient.
- Provide the same semantic API for generic SAT/direct encoding, current flat index and full hierarchy. Expose equivalent planning operations, not a rich API for ours and a weak one for competitors.
- Implement `propose`, `check`, `counterexample`, `revise` and a simulated proof-required `commit` gate. Bind checked evidence to the current formal claim/action, assumptions, evidence/model identity, ordering and horizon; stale proofs cannot authorize changed proposals. Gate only checked formal consequences, never a high probability or fluent explanation. Give all symbolic arms equivalent verification capabilities.
- Provide direct gate/circuit and BDD/grammar offline comparisons where feasible. Baseline selection/search budgets are fixed on development, not the final evaluation.
- Prove exact agreement on tiny cases by independent reference tests. Test overlap, duplicate mechanisms/encodings, ordering, shared subrules, inconsistent evidence, no-op interventions, incomplete enumeration and timeouts.
- Keep S1/S2 semantics stable. If hierarchy construction cannot meet its bound, return an explicit unknown/resource result and record it; do not silently expand exponentially or present a sampled answer as exact.

### P3 — build S4 tasks, evaluator and leakage audits

Owner: task/evaluation worker; new generators, reference evaluator, baseline controls and offline family map.

- Implement S4-A fixed-evidence unseen claims and a separately scored S4-B active-investigation prototype as in the research direction. Finish S4-A first. Add the amendment's small offline known-mechanism checking panel; it must not be mixed into the unknown-mechanism endpoint.
- Add pre-release checking metrics on a common frozen initial proposal batch replayed through B/C/D: wrong proposals prevented, wrong verified releases, unnecessary blocks, correct release coverage and costs. Keep natural model errors separate from intentionally planted error fixtures. The initial proposals are obtained within the existing call budget, for example the first turn of arm A.
- Test stale certificates, wrong quantifiers/order/horizon, inconsistent evidence, invalid proof text and simulator postconditions. This is a scoped formal checker, not proof that an LLM or a real-world model is globally correct.
- The evaluator alone owns the hidden mechanism. Use capability separation or serialized public payloads so the agent/encoder never receives hidden truth. Log every observation purchased during S4-B.
- Audit semantic novelty, source/target duplicates, direct-answer measurements, coupled budget/label rules, world overlap and isomorphism. Surface baselines must be fitted on training only and persisted before calls.
- Use independent random streams. Include nulls, parity, order-disrupted controls and misspecification diagnostics; do not curate only networks our method compresses well.
- Run the fixed offline map and fixed-request replay to show which representation actually executes and where any resource savings arise. Include deterministic no-LLM controllers and strong disagreement-guided inquiry.
- All planned outcomes, including errors and timeouts, remain visible. Validate complete method/target identity before scoring, applying the lesson of R3-01 to S4.

### P4 — bounded local AI pilot and prospective main-study sizing

Owner: harness/statistics worker, after P1–P3 validity gates pass.

- Pin two locally available model artifacts/quantizations/templates. Declare the model-selection rule before inspecting S4 outcomes. Do not require a positive treatment effect to keep a model.
- Record a concrete resource contract first. Pilot: 40 worlds/model, five per family, four arms, eight novel claims/world, at most eight model turns/episode; total ceiling 2,560 model calls. Local inference only. S4-B offline prototype does not expand this LLM call budget.
- Run validity/usability gates as specified. A failed interface gate permits at most one logged revision on fresh development worlds, with a separately declared bounded cost before it starts. Keep failed diagnostics and report any reduced model scope.
- The primary proposed main contrast is hierarchy minus generic symbolic workspace on world-level S4-A accuracy. Report system benefit versus unaided AI and fuller representation versus flat as secondaries. Use offline no-hierarchy/no-analytic-shortcut ablations for attribution; D-minus-C alone no longer isolates hierarchy. Report the possibility of equal accuracy with lower cost, not only significance.
- Size the fresh main evaluation for a 5-point effect and 80% target power with per-world variance, two-model multiplicity and simulation; planning target 320 worlds/model, adjustable prospectively up to 800/model if justified. Produce runtime/token/storage estimates. Do not run it yet or overstate the power of a noisy pilot.
- If all tool backends answer correctly within budget, report this expected agreement and compare total costs. Do not cripple the baseline or give our arm additional evidence to manufacture a win.

### P5 — public prototype, funding narrative and review package

Owner: integration/reporting lead after P0–P4.

- Build a reproducible CLI or small notebook demonstration of an AI proposing a claim, receiving a checked certificate or counterexample before release, inspecting uncertainty, selecting a permitted experiment and reaching a checked conclusion. Hide the mechanism until the reveal. A live website is unnecessary.
- Produce `reports/S4_DEVELOPMENT_REPORT.md`, a family/cost table, `reports/S4_DESIGN_SIZING.md`, and `docs/S4_FUNDING_BRIEF.md`: concrete problem, method-specific contribution, results with uncertainty, competitor comparison, proposed next milestone and resource request. Distinguish established evidence from hypotheses.
- Preserve S2's old null result and S3's limitations. No claims of universal truth, arbitrary-program exact inference, minimum Kolmogorov complexity, or superiority to Zenil without matched evidence.
- Include the amendment's foundation/method mapping, check-before-release API, matched prevention metrics and complexity/probability/proof claim audit in the acceptance matrix.
- Create `reports/REVIEW_READY_R4.md`, acceptance/evidence matrix, raw immutable records, source/config/model hashes, tests, reproduction commands and manifest. Keep repair validation separate from new scientific results.
- Publish a new development prerelease with public data/code and exact content commit; preserve older tags/assets. Check download-back, fresh clone and documented install. Explain what was pre-sprint versus sprint work under the official rules.
- Include `delegation/REVIEW_R4_REQUEST_PROMPT.md` naming exact commit/tag and asking Codex to review P0 plus the concrete S4 design/pilot before a scoped main-study decision.

## Completion criteria

Return implementation and measured development evidence, not only another proposal. Success for this iteration is a faithful, audited testable system and an honest pilot, not a required positive effect. If a scientific assumption fails, show the failure and finish the reproducibility/reporting work; do not search indefinitely for a favorable task.

The user is seeking a fundable research program. The credible claim we are working toward is: **our compressed structured representation helps an AI discover and justify unseen facts with less evidence or computation than strong alternatives**. The experiment must be able to tell us whether that claim is true.
