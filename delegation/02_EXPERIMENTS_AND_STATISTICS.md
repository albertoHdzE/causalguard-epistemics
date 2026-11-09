# Experimental programme and statistical analysis plan

These are design targets, not observed results or guarantees of power. Claude must implement all core studies, measure development throughput, and write the frozen executable design for review before confirmatory execution.

## Study S1 — compression and exact query scaling

Hypothesis: index-family representations preserve answers while reducing representation or query costs for specified structured families. A universal advantage is not hypothesized.

Methods: direct gate/circuit evaluation; literal repertoire at feasible sizes; index families; DNF where distinct; BDD/SAT reference with fixed ordering/search budgets. Separate representation construction, serialization, deserialization, conversion, cold query and amortized queries. Do not give one method precomputed truth tables while charging another for constructing them without a separate end-to-end comparison.

Six mechanism families: sparse conjunctive/disjunctive, canalizing, parity-heavy, modular compositional, bounded-indegree random lookup rules, and small dense random Boolean functions. Dense random functions are an explicit incompressibility stress control restricted to feasible sizes; bounded-indegree random networks are not equivalent to uniformly random global functions.

Small validation grid: n in {4,6,8,10}, six families, 50 independent worlds per feasible cell (target 1,200). Exhaustively check all states and supported gate/parameter cases; include query predicates with independently derived labels. Large grid: n in {16,32,64,128,256}, five scalable families, 30 seeds per cell (target 750). Do not fabricate dense random functions at sizes that cannot be instantiated. Report excluded-by-design cells separately from attempted failures.

At least 20 fixed queries per world spanning membership, exists, forall, and finite-horizon reachability h in {1,2,4,8}; balance satisfiable and unsatisfiable queries using development construction, not post-hoc deletion. A minimum cheap development execution is 10 worlds per small family/size cell plus 5 per large feasible cell through n=64, with failures retained. Confirmatory grids remain separate.

For large instances, validate SAT witnesses by direct replay and UNSAT/universal answers by an independent exact solver or checked proof where supported. Cross-solver agreement is not a mathematical proof. A sampled check earns only a sampled-verification tag; it cannot support a global exactness claim. Store proof/certificate level per result.

Metrics: exact mismatches, archive bits for identical objects, full decoder-plus-payload accounting, construction/query time distributions, peak resident memory, success/timeout/OOM rate, representation expansion, and scaling by family. Use subprocess isolation for meaningful peak memory measurement. Resource caps are fixed from development before confirmatory runs. Never drop timeouts from speed comparisons or replace them with zero time. Give capped completion curves and successful-pair latency summaries with explicit denominators.

S1 is an engineering/formal-correctness study, not evidence of empirical causal identification.

## Study S2 — induction from incomplete evidence (primary scientific study)

Primary hypothesis: among equally data-consistent candidate mechanisms, a shorter **decodable description** improves hidden intervention prediction relative to uniform selection over the same compatible set. The possibility of no improvement or worse performance is central.

Required methods:

1. Uniform compatible-model selection, implemented as the expected prediction over all candidates when feasible (or repeated random selection with its own Monte Carlo uncertainty).
2. Minimum index-code-length compatible model, with seeded, fixed tie-breaking.
3. Minimum direct gate/circuit-code-length model.
4. Minimum BDD/DNF-code-length model where available under the same encoding accounting rules.
5. Complete-version-space consensus, returning uncertainty when models disagree; this is an uncertainty policy, not a single-model predictor.
6. Hidden generating mechanism oracle as a labelled ceiling, never a learner.

Use complete bounded classes for correctness studies; explicit candidate pools are a separate benchmark mode. Construct candidate pools by a declared process before drawing observations. Include classes containing alternative rules/topologies rather than arranging all distractors to be longer than the planted truth. Audit true-model rank in the code-length distribution. A true mechanism must not be identifiable from its position, ID, serialization order or unique syntax.

Evidence regimes: uniform chosen input states, biased/narrow-support observational samples, and controlled interventions. For budget comparisons, random-query and disagreement-guided active-query policies spend the same number of measurements. A symbolic disagreement policy may select observations where compatible models predict different outputs; log candidate-search cost. Compare evidence budgets {2,4,8,16,32,64} subject to distinct inputs/feasible domain. For tiny domains use explicitly recorded smaller grids. Reuse nested evidence prefixes within a world but keep all budgets clustered together statistically.

Measure query answers on hidden states and interventions disjoint from observed input/intervention/horizon tuples. Separate state holdout from intervention holdout; explain that a changed intervention may reach previously visited states. The verifier cannot see hidden answers during selection. Include topological/gate-composition distribution shifts fixed in development.

Primary endpoint: per-world hidden intervention accuracy at evidence budget 16, averaged over a fixed query grid, compared between minimum index-code model and uniform compatible-model prediction. For uniform selection, compute the expected accuracy of a randomly selected model (fraction of compatible models correct), not a majority-vote predictor unless separately named. Define paired difference Δ_w and aggregate with prespecified equal stratum weights. Primary population: realizable worlds. Misspecification/noise are separate stress populations.

Secondary endpoints: risk versus coverage for consensus, false evidence-relative certification, disagreement rate, wrong hidden-world assertions, evidence required to resolve queries, model selection cost, and accuracy/length/latency trade-offs. Report conditional-on-answered accuracy alongside unconditional denominators. A consensus conclusion can be logically correct within H yet wrong for a misspecified hidden world; show both.

Noise: core study noiseless. Stress tests flip observed bits at frozen rates {0.01,0.05,0.10}; use inconsistent-class reporting for exact matching. If fitting noisy data, use the explicit residual code from the contract and label this a separate MDL experiment. Do not silently relax constraints until an answer appears.

Minimum development dataset: 200 independent worlds across at least four families, three evidence regimes, and four budgets; all methods share each world. Repeated evidence regimes/budgets are not new independent worlds. Planned confirmatory range: 1,000–2,000 independent test worlds, with final N determined below; structured shift adds a separately labelled set. Do not choose N to reach significance.

## Study S3 — AI reasoning and transfer

Implement the LLM harness now; a real development pilot is required if an existing local model is available. Mock runs are explicitly segregated. Use the same structured task objects and evidence-relative verdicts as S2.

Conditions: A initial answer; B answer/self-critique/revision; C three independent answers with deterministic majority/tie-abstain aggregation; D answer plus at most two witness/evidence-feedback rounds; D-label direct verdict disclosure as a privileged-answer control; E symbolic solver without LLM. D must not insert the final verdict label. Nevertheless a witness may reveal it; do not describe D as label-free learning. Compare fresh related questions without feedback to test transfer.

For C, aggregate probabilities by arithmetic mean of valid probability vectors; vote labels separately. Report invalid members and the number of valid vectors; no valid vectors means invalid probability output. For all arms, distinguish provider failure, invalid JSON, invalid probabilities, semantic error and operational abstention. No silent model-based JSON repair.

Freeze templates, original messages, feedback format, temperature, token limits and model revisions. Reuse the same first answer across A/B/D/D-label and as C's first independent sample; C's other draws start fresh contexts. Cost accounting must report both physical calls saved by caching and each arm's logical standalone cost. Reuse introduces correlation, handled by paired analysis; it does not create extra samples.

Primary S3 contrast: D versus B on final verdict balanced accuracy; secondary comparisons include C and D-label. Same-item improvement is assisted correction, not persistent learning. Explicitly report correct-to-wrong revisions.

Pilot: 60–100 development worlds, at least four linked items per world, preferably two existing local model families. Full primary-model target: at least 1,000 worlds if the precision analysis supports it; use a prespecified 300–500-world replication set per additional family if affordable, with wider intervals acknowledged. Do not imply a single model establishes model-independent behavior. Compute feasibility may require prioritizing S1/S2 and reporting S3 as exploratory; retain this decision in the claim ledger.

Output probabilities over {entailed,refuted,underdetermined}, sum within fixed tolerance. Brier = mean over items of sum_k (p_k-y_k)^2 (range 0–2, no division by number of classes). Report valid-only Brier with validity coverage and a prespecified worst-score sensitivity assigning 2 to invalid/missing outputs. Malformed/abstained answers count as incorrect for primary accuracy. Confidence calibration needs bins defined before evaluation; do not claim calibration from a few hand-picked examples.

## Sizing, independence and multiplicity

The independent unit is the generated world (or shared ancestor group if several worlds are mutations of one base). All queries, paraphrases, noise realizations, repeated evidence budgets and stochastic runs stay within that cluster. Splits occur before any variants are generated. Reject structural duplicates across splits using canonicalization or an explicit collision/isomorphism audit at the supported sizes; hash identity alone is insufficient for renamed copies. Report where exact deduplication is infeasible.

Target meaningful primary difference δ=0.05 absolute accuracy; target 95% interval half-width at most 0.03. Estimate the paired world-level variability and strata from development only. As a rough planning check, N≈(1.96+0.84)^2*sigma_Δ^2/δ^2 for 80% power: sigma=0.5 gives about 784 worlds; sigma=0.7 gives about 1,537. This approximation is not the final power analysis.

Implement Monte Carlo design simulation using observed development variability, stratified sampling, actual aggregation and cluster resampling. Simulate null and 5-point effect scenarios, including a conservative variance sensitivity. Select N before test access, within available resources; report expected precision/power if targets are infeasible. Increasing query count does not replace independent worlds. Freeze the resulting N, effect threshold, analysis and stopping rules. A wide-interval null result is inconclusive, not evidence of equivalence.

Use at least 5,000 fixed-seed stratified paired cluster-bootstrap replicates for primary intervals, validating coverage in simulations. Average repeated generation seeds within world or explicitly model their hierarchy. Report both raw effect and interval; optional p-values require a specified method. S2 has one primary contrast. S3 is a separately stated secondary study; if both are promoted to co-primary in the paper, predeclare multiplicity handling (e.g. Holm) before confirmatory outcomes. Other method/family/budget comparisons are exploratory unless explicitly registered.

Data exclusions must be semantic invalidity rules fixed in development, never poor performance. Missing method outputs count toward failure rates. For prediction methods use prespecified missing-output treatment (zero correctness primary; complete-case sensitivity); missing hidden ground truth invalidates the item for every method and is logged as a benchmark failure. Report exclusions by method and reason.

## Freeze and stopping rules

Record dataset generator, versions, code commit, split manifests, prompt hashes, selected models, codec specification, limits, primary endpoints, N, random seeds and analysis configuration. SHA hashes are tamper evidence, not proof nobody saw a file. Test generators/seeds and private labels remain inaccessible to candidate-selection processes; access is logged. Publish them after the final freeze/evaluation for reproduction.

Stop for a material oracle/codec defect, corrupted logs or resource exhaustion, not unfavorable effects. Retain failed run records. If a defect affects confirmatory data, invalidate and disclose that run; re-freeze and use a fresh test set for a revised claim. No repeated peeking with optional continuation until significance.

## Concrete output figures

1. S1 bits and query cost against size by family, including failures.
2. S2 intervention accuracy against evidence budget by selection method, paired intervals.
3. Consensus false-certification versus answer coverage, realizable and misspecified panels.
4. S3 correction and transfer, with the direct-label control visible.
5. Optional weight study: held-out gain versus training/search cost and false-entailment rate.

Every plotted point links to raw run IDs and a reproducible analysis command. Development and confirmatory figures must be visibly labelled and stored separately.
