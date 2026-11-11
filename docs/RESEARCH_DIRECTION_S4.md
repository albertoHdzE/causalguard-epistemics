# S4: Algorithmic models for checking and discovering unseen facts

Reviewer proposal, 2026-11-10. New development study; not a replacement for S2 or a frozen protocol. Implementation and bounded local development are delegated in `delegation/ITERATION_4_CLAUDE_PROMPT.md`. Large held-out evaluation follows a separate review of the concrete implementation, resource budget and protocol.

Amended 2026-11-11 at the user's request. Read `S4_FOUNDATIONS_AND_PRECOMMIT_CHECKING.md` for the formal-paper grounding, algorithmic-probability distinction, analytic parity/threshold capabilities, and checking-before-release workflow. The main endpoint and pilot budget below remain unchanged.

## The question we should actually test

Can an AI using our hierarchical index representation reach more correct, checkable conclusions about unseen interventions, under the same evidence and resource limits as strong alternatives?

The research program is algorithmic modeling for verifiable AI reasoning; Boolean systems are its initial test environment. The intended product combines a check before release with an uncertainty workspace: keep the possibilities that agree with observations, distinguish what follows from what remains unknown, and choose measurements that resolve the uncertainty. The application is an assistant for investigating a simulated system, initially a small digital circuit or Boolean process. A positive result would concern assisted AI performance, not a change to neural weights or autonomous learning.

The previous experiment asked a narrower question: select ONE compatible network with the shortest flat index code, then predict its outputs. That is a reasonable test of one induction policy. It is not a test of the entire hierarchical representation or its use as an AI workspace. Preserve its null result and endpoint.

## What the existing method actually covers

`docs/CODEC.md`, `index_repr.py` and `versionspace.py` implement coordinate-fixed schema families, their unions, per-node code lengths and bounded-indegree candidate sets. They do not implement the whole ordered hierarchy from the original project.

Original local references, to be pinned and mapped before implementation:

- `/Users/alberto/Documents/projects/CausalBool/papers/method/manuscript_formal/method_paper.tex` (analytic index-set calculus; known-mechanism reconstruction, parity, thresholds and support-local queries)

- `/Users/alberto/Documents/projects/CausalBool/index-deconvolution/protocols/hierarchy_v1/WIRE_FORMAT.md`
- `/Users/alberto/Documents/projects/CausalBool/index-deconvolution/hierarchy/README.md`
- `/Users/alberto/Documents/projects/CausalBool/index-deconvolution/PROTOCOL_hierarchy_dictionary_v1.md`
- `/Users/alberto/Documents/projects/CausalBool/index-deconvolution/results/causal_target_v1/supervision/causal-target-spec-v1-r1-closure/REVIEW.md`
- `/Users/alberto/Documents/projects/CausalBool/index-deconvolution/results/causal_grouping_gap_v1/supervision/gap-ranking-v1-r1/REVIEW.md`

The HID wire language specifies LITERAL, CONCAT, REPEAT, AP_UNION, SCHEMA_UNION, PATCH and XFORM, with explicit ordering and shared references. A DAG can share a subrule; a tree without sharing may duplicate it. The existing wire format also has finite length/resource limits. Do not silently claim that it already supports a 2^256-bit repertoire or symbolic operations over arbitrary model sets.

The original work contains unsuccessful hierarchy and inquiry comparisons as well. In particular, a bounded-indegree query-recovery proposal was withdrawn because its argument mapped to established learning methods, and gap ordering was not generally better than random. These are development history to learn from, not evidence that a new AI application must fail or succeed.

No unlicensed upstream source is to be copied into the public repository. Inspect specifications, pin identities, and implement independently unless reuse permission is established. Parity/XOR and threshold predicates already belong to the original analytic calculus. Porting them here must be distinguished from extending a particular wire format and from the previously tested flat schema codec. Map the analytic calculus, flat codec and HID hierarchy separately; see the amendment for source-level boundaries.

## Why majority does not contradict compression

A repertoire is a representation; majority is a decision rule. They can be used together. If four compatible mechanisms predict 1 and one predicts 0, exact compressed counting and exact explicit counting must give the same 4/5 result, provided they count the same distinct mechanisms with the same weights. Changing their storage cannot create new observations.

That 4/5 is a prediction, not a proof: the fifth mechanism may be the real one. Agreement of EVERY compatible mechanism can certify a model-relative conclusion. Disagreement can identify a useful measurement. A compact representation can make these computations practical without selecting a single mechanism too early.

Keep distinct: (1) states of one known mechanism, (2) different mechanisms compatible with incomplete evidence, and (3) encodings of the same mechanism. A compact representation of (1) does not automatically compact (2). Multiple encodings must not give a mechanism extra votes. The order of outputs must be explicit; if it carries information, charge its storage/construction cost.

## Scientific contribution and relevant prior work

Zenil et al.'s [causal deconvolution](https://www.nature.com/articles/s42256-018-0005-0) uses algorithmic generative models and perturbations to investigate mechanisms. Its motivation is relevant; it does not prove that our finite encoder or inference policy beats compatible-model majority. A direct superiority claim requires a matched implementation and experiment, absent here.

Generic solver-assisted AI is already established in [Logic-LM](https://arxiv.org/abs/2305.12295) and [SatLM](https://arxiv.org/abs/2305.09656). Therefore beating an unaided LLM alone cannot establish an index-specific contribution. The distinction between compactness and supported reasoning operations is also central to [A Knowledge Compilation Map](https://arxiv.org/abs/1106.1819).

Our proposed contribution is narrower and testable: the index hierarchy, including its ordering and sharing, improves the practical use of a complete uncertainty representation for AI-assisted investigation. Whether it does so is currently unknown.

## Mandatory method-coverage document before model calls

Create `docs/S4_METHOD_COVERAGE.md` with equations, one fully worked tiny example, paths and tests:

1. Precisely define the encoded object and canonical address order. Define H, observations D and V(D) = {M in H: M agrees with D}. State whether H is a full bounded class or a finite candidate library; never call a sampled library exhaustive.
2. Map each user-proposed capability to original specification, existing implementation, new implementation or unsupported. Identify the exact operations that use OUR hierarchy, rather than a generic solver hidden underneath a project name.
3. Construct from public H and D only. Hidden mechanism and held-out answers belong exclusively to an evaluator process. No hidden full truth table, mechanism-selected dictionary, or truth-based ordering may enter the workspace.
4. Explain evidence conditioning, membership, existential/universal queries, witness extraction, update and counts. SAT fallback is permitted but separately metered. A decoder alone is not a symbolic reasoning implementation.
5. Distinguish exact counts from estimates. Count distinct canonical mechanisms, not SAT auxiliary assignments or overlapping schema sizes. Correctly project nuisance variables. Never certify universal claims from samples or solver timeouts.
6. Mark every enumeration/materialization, its bound and its cost. Include compilation, candidate generation, dictionary search, ordering, decoder, cache and all query costs. Report cold-start and amortized performance separately.
7. Disclose whether the current nodewise factorization supports the proposed observations; multi-step evidence cannot reuse one-step factorization without proof. Start with supported one-step observations and novel multi-step/intervention targets.

If a full V(D) hierarchy is infeasible, deliver the bounded supported case and document the boundary. Do not substitute compression of the hidden true mechanism. Known-mechanism deduction is a separate supplementary study.

## Experimental structure

S4 has two tasks, with independent scores. Fixed-evidence reasoning is the core; active investigation is a prespecified secondary extension until its implementation is reviewed.

The checking-before-release workflow in the amendment reuses the same pilot and adds secondary prevention/coverage metrics. A small known-mechanism panel is an offline validation/demo, kept separate from the main inference results.

**S4-A, unseen claims from incomplete evidence.** Given H and D, answer novel intervention claims with entailed/refuted/underdetermined. Inconsistent evidence is a distinct diagnostic status. Independently check proofs or opposing witnesses where required. Also score a separate binary forecast against the hidden mechanism on genuinely underdetermined queries; do not conflate forecasting with entailment.

**S4-B, investigation.** Begin with a target underdetermined by D. Permit 0, 1, 2 or 4 new measurements from a predeclared intervention menu. The agent chooses a measurement, receives only its observed result, updates V(D), and answers unseen targets. The exact target experiment and semantic duplicates/complements are excluded from the measurement menu. Reaching a checked answer without directly asking for its label is the outcome of interest.

Use fresh study IDs and seeds. Existing S1/S2/S3 remain intact. Retention after self-critique is optional exploratory analysis, not the main objective.

### Comparators that isolate our contribution

| Arm | Same AI, evidence and allowed observations | Purpose |
|---|---|---|
| A | No symbolic tool; structured evidence and matched instructions | Overall assisted-system benefit |
| B | Generic symbolic workspace, ordinary direct encoding/SAT | Strong solver-augmentation control |
| C | Flat index-family workspace | Current method ablation |
| D | Analytic index-set rules plus hierarchical/ordered workspace | Fuller proposed method |

All tool arms expose the same semantic API and response schema, including equivalent witness, count and next-measurement capabilities when used. A weaker API for B would confound the comparison. Publish fixed-request replay across B/C/D to separate backend performance from different agent choices. Include a no-LLM deterministic controller on the same tasks: if it gets all the benefit, say so.

The primary new contrast is D minus B on S4-A final claim accuracy at equal resource caps, with all planned worlds retained. D minus A tests system usefulness; D minus C tests the fuller representation against the flat codec. Offline no-hierarchy and no-analytic-shortcut ablations separate sharing from analytic operators; do not attribute their combined gain to hierarchy alone. Correctness agreement on tiny exact cases is required, not a research win. If B/C/D deliver identical answers within every budget, an accuracy tie is expected. Examine total cost rather than manufacturing a difference in information or handicapping B.

For S4-B compare random measurement, exact compatible-set disagreement/information selection where feasible, and the AI policy. Cross the same deterministic policy with B/C/D first. Learning about a world via extra observations must not be presented as a fixed-evidence prediction advantage. If exact information gain is infeasible for all arms, use the same declared approximation and seeds; do not label it exact.

Ordinary circuit, BDD and grammar-based representations are offline competitors where the operation is supported. Fix a serious generic baseline using training/diagnostic performance before the main study; do not compare only against a deliberately poor encoding.

### Families and controls

Eight proposed realizable strata: sparse conjunction/disjunction, canalizing, repeated modules, ordered/repeated motifs, parity/XOR, bounded random lookup, matched order-disrupted motifs, and uniform-H null. Existing labels alone do not establish equivalent generators. Freeze the new generators and H membership checks explicitly. Order disruption must preserve the declared class, or move to the separately scored misspecification diagnostic.

Repeated-module and ordered-motif strata target the richer method's proposed strengths. They are prospective tests, not claims of already demonstrated superiority. Include transformed names and independently drawn evidence budgets, horizons and target labels. Do not derive two of these from the same index modulo expression. Test structural holdouts, not merely different random names for the same world. Deduplicate isomorphic worlds under a documented feasible equivalence test.

Generate primary target queries independently of hidden answers. An additional label-balanced diagnostic can be outcome-stratified, but label it honestly and audit surface predictability. Log feasibility shortfalls; do not redraw away difficult worlds. Future S4-B's restriction to initially underdetermined targets defines a different population and must be explicit.

### Metrics and sample sizing

Primary unit: independent world, not individual queries or model calls. Compute each world's accuracy over eight fixed novel target claims, then average equally across the eight strata. Pair arms on the same worlds. Bootstrap worlds within strata, 10,000 replicates, prespecified seed. Report per-model results, no best-model selection on the final panel. Predeclare handling for stochastic repeats; they do not multiply the number of independent worlds.

Record proof-checked coverage and wrong definitive claims separately so always answering 'unknown' cannot look like success. A timeout/invalid answer is a failed scheduled outcome; no complete-case-only headline. For genuinely underdetermined forecasts, report accuracy and proper probability scores separately, including prediction/verdict coherence. Do not call Brier scores alone calibration.

Plan two models and an initial target of **320 independent fresh evaluation worlds per model** (40 per stratum), with eight queries per world. Before that, a fixed development pilot of 40 worlds/model (five per stratum) estimates runtime, variance and interface failures. Choose model versions from the existing local inventory, record hashes/quantization/templates and retain unsuccessful diagnostics.

320 is a planning allocation, not a power guarantee. Use world-level paired variance, a declared smallest meaningful effect of 5 percentage points and 80% target power to size the main D-minus-B comparison, including two-model multiplicity. Check with simulation and use an upper variance estimate rather than a noisy optimistic pilot value. Increase the fixed plan in balanced blocks up to 800/model if justified and feasible. If the required N or cost exceeds the available budget, report the achievable precision and narrower scope before evaluation; do not promise significance or count correlated queries as independent. The main panel remains unrun until reviewed. Cross-model generalization requires both models; a single-model result is reported as such.

Use Holm adjustment across the two primary model comparisons (familywise 0.05). The 5-point value is the sizing alternative, not an automatic claim threshold: report the estimate and adjusted interval; distinguish evidence of a positive effect from evidence it exceeds 5 points. D-minus-A, D-minus-C, family effects, active-query outcomes and learning curves are secondary unless prospectively promoted in a new version before any final outcomes.

### Resource and feasibility gates

Before LLM calls, run exact differential tests over every two-node Boolean network and a fixed seeded small-world battery; separately test overlapping families, order changes, shared subrules, duplicate encodings, empty V, wrong assumptions and resource failures. Audit fresh target semantics. Run a fixed offline development family map (at least 20 worlds/stratum at small supported sizes) and larger symbolic stress cases; these are not new confirmatory data.

Write a concrete resource contract before the pilot: token cap, context policy, tool-call cap, wall/CPU/memory caps, compiler time, number of measurements and failure semantics. Defaults for the bounded pilot: four arms, at most eight model turns/episode, no more than 2,560 calls total across two models and 40 worlds/model. Local inference only in this delegation; no new paid service or weight training. Record wall time and forecast the full panel cost.

Pilot gates concern validity/usability, not statistical success: zero semantic correctness mismatches; no hidden-data flow; at least 90% parsable verdicts per arm; no systematic truncation above 2%; all missing outcomes accounted for. Low baseline accuracy is reported rather than used to exclude an inconvenient model after seeing treatment effects. If a gate fails, make at most one logged development revision and use a fresh diagnostic set; retain all outcomes. A second failure returns a concrete blocked component and remaining completed deliverables, not endless prompt search.

## Funding case and sprint deliverable

Working title: **CausalGuard: algorithmic models for verifiable AI reasoning**.

The research proposition: an AI should know which claims are supported, exhibit plausible alternatives when they are not, and choose a useful experiment instead of guessing. Our proposed contribution is a compact structured representation that makes that process efficient and auditable.

Deliver a public reproducible prototype, a family-by-resource map, a controlled comparison with generic solver augmentation, and one transparent interactive example with hidden mechanism, measurements and checked conclusions. Publish the historical negative results too. A positive D-minus-A result alone supports assisted inference; a D-minus-B or cost advantage plus ablations supports investment specifically in our representation. A tie means the distinctive advantage remains unestablished; it is not permission to rename generic SAT as our breakthrough.

Follow-on funding milestones: validate representation-specific advantage; extend observations beyond one-step; test richer mechanism classes and noisy/misspecified evidence; then evaluate a real diagnostic workflow. Neural weight changes are not necessary to answer the present question.

The [official sprint page](https://apartresearch.com/sprints/ai-x-epistemics-research-sprint-2026-11-13-to-2026-11-15) lists November 13–15, 2026 and requires explicit disclosure of preexisting work. Mark this plan and earlier code pre-sprint. Funding and acceptance are goals, not promised outcomes.
