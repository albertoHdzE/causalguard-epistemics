# R5 scientific contract

Status: prospective DEVELOPMENT assignment, 2026-11-11. No experiment has been run under this document by Codex. Resolve feasibility details on isolated calibration data and record them before evaluation. The original S1–S4 endpoints and findings remain intact.

## 1. One argument, four tests

The proposed argument is: a compact mechanism representation makes useful uncertainty computations feasible; structured weighting may improve unseen prediction; an AI can use this workspace to investigate; and the resulting claims need explicit safeguards against incorrect assumptions. Each link has its own comparator and can fail independently. Do not combine their effects into one “success rate.”

Primary R5 scientific contrast: **full CGH prior versus a calibration-selected generic forecasting comparator**, on a structurally held-out synthetic suite. External-model validation is a separately reported generalization test, not pooled with synthetic worlds. R5 is a development stage for choosing a future independently reviewed confirmatory study.

## 2. Shared rules

- Agent/workspace inputs contain public evidence, class, declared semantics, queries and allowed actions only. Keep the hidden mechanism, target answers, family, source paper, seed and oracle evaluator out of the agent process. Record public payload hashes and evaluator access.
- Use canonical distinct mechanisms, not encoding multiplicities or auxiliary SAT assignments. State support, class completeness and order explicitly. A sample cannot certify a universal assertion.
- Main inference stays at n=8, k≤3, one-step observations, h∈{1,2} targets. Small exact oracle cases validate changes; larger stress cases are separate. Do not silently simplify external networks to fit this class.
- Split by underlying mechanism, source lineage and transformation orbit. Isomorphic relabelings, rewired paired controls and multiple evidence draws are related observations. Assign `source_group_id`, `mechanism_id`, `split`, `transformation_id`, `evidence_id`, `query_id`, and `run_snapshot`.
- Fit prompts, fallback policies, comparator selection and parameters on calibration only. All evaluation predictions are immutable before hidden target scoring. Never use evaluation effects to resize, remove a stratum or select a model.
- Treat observations and interventions as different when semantics require it. Exclude duplicate/complement target queries and observations equivalent to directly buying the target answer; log exclusions and redraws.
- Shared requested operations must have shared semantics. Cross backend with policy where practicable; otherwise explicitly limit attribution.

## 3. Track G — unseen inference and generalization (highest priority)

### G1. Populations and separation

Create a 64-instance synthetic calibration set (eight per stratum) and a new 320-instance evaluation set (40 per stratum). This is a resource-backed target, not a claim of power. Use eight documented structural strata:

1. ordered templates with rule exceptions (structural perturbations, not observation noise);
2. unequal-sized or imperfect repeated modules;
3. shared local motifs without cyclic physical order;
4. sparse feedforward networks with heterogeneous gates;
5. feedback networks with heterogeneous canalizing rules;
6. mixtures of parity, threshold and other gates;
7. degree-preserving rewired matched controls (cluster with their source mechanisms);
8. a uniform-H null.

The generator owner writes and commits specifications without examining D's evaluation scores. Fix perturbation rates, module sizes, gate mixtures, order conventions and eligibility before running evaluation. These remain our synthetic generators; do not call them externally chosen. Paired controls reduce the independent sample count below 320; report actual clusters. A scientific reason can change a stratum during calibration, but the change must be logged before evaluation and cannot depend on a favorable D contrast.

Also implement an **external-model adapter**. Candidate source: [Biodivine Boolean Models](https://github.com/sybila/biodivine-boolean-models); alternative [PyBoolNet model repository](https://github.com/hklarner/pyboolnet). Pin source commits, individual model hashes, citations, licenses, parsing semantics and inclusion/exclusion logs before scoring. These are published models, not experimental measurements of biology.

Inventory all eligible intact models within the supported class and computational limits. If too few fit, include a separately labeled transformed-model panel using a fixed, deterministic subnetwork/boundary-clamping procedure that preserves declared synchronous semantics. Select roots/boundaries without predictive scores or code lengths. Group all derivatives by source lineage. Aim for ≥20 independent source groups if available; otherwise use all eligible groups and report the limited coverage. Cap evaluation at 40 source groups, selected by a predeclared hash ordering if more are eligible, with at most four transformed instances per group. Keep all inventory/exclusion records. Do not manufacture 320 independent external worlds by resampling a few models. Do not pool intact and transformed populations. No claim of real-world biological accuracy follows.

Keep evaluation sources out of codec/prompt design. Public-source memorization is a possible LLM confound; external evaluation here is offline symbolic and uses opaque node labels. Record any prior exposure of the implementation agent; a published dataset is held out from fitting, not literally secret.

### G2. Predictors and attribution

Implement/reuse: uniform compatible-model averaging; old flat-index weighting; circuit weighting; gate-catalogue weighting; analytic-only CGH; full CGH. Retain the single-shortest-model result as a secondary, not the main interpretation of the user's method.

Add one feasible **generic structured prior**, such as a fixed generic shared-rule program catalogue mixed with full-support uniform H, or an independently specified exchangeable/shared-rule prior. Specify normalization, duplicate handling and how probabilities are computed. This must not be D's implementation renamed. A finite-catalogue mixture must retain support on H, charge its structural choices, and disclose its restriction. If exact summation cannot be implemented in budget, do not disguise sampling as exact; report certified error bounds or mark the comparator incomplete and limit claims against structured alternatives.

On the 64 calibration instances choose one comparator from {uniform, circuit, gate, implemented generic structured prior} by mean Brier score, with fixed tie order. Lock its identity globally before evaluation; no per-family oracle selection. Report every candidate on evaluation too. Analytic-only CGH is the prespecified hierarchy ablation, not a replacement for the generic comparator.

Here “full CGH prior” means R4's `cgh_prior` (FLAT + TEMPLATE + MODULE, without patches); it does **not** include the DICT mode present in the broader description-length codec. Keep that restriction visible. Hold R4 full/flat CGH prior languages fixed for the main contrast. If engineering requires a semantic language change, version it, report the original where valid, and treat improvements as a new exploratory arm. Learned order or dictionaries are secondary only: learn from public evidence, pay search/storage costs and compare against random and declared order. Hidden-mechanism compression is an evaluator diagnostic, never an inference input.

### G3. Outcomes and analysis

Per mechanism: nested evidence budgets 8, 16 and 24; eight fixed novel queries, four h=1 and four h=2, selected without target answers. **Primary:** world mean Brier score at 16 observations, over all eight scheduled queries; contrast `Brier(generic) − Brier(full_CGH)` so positive favors our method. Probabilities must refer to the target-node value, consistently with the scored 0/1 outcome. Determined and underdetermined queries are stratified secondaries; logical status is defined by the same H/evidence independently of the prior.

Also report hierarchy ablation, accuracy, calibration/reliability summaries with sample sizes, budget curves, per-family effects, exactness/refusal rates and cost. Do not substitute LLM self-reported probabilities for computed probabilities. No log-loss clipping tuned on evaluation.

Use paired cluster intervals with equal prespecified stratum weights. Resample source groups/paired transformation groups, not individual claims. Report realized group counts. External data get source-group intervals and separate population summaries. With very few groups give descriptive ranges/leave-one-source-out sensitivity rather than a spurious narrow bootstrap. Use a prespecified 0.02 Brier improvement as the practical planning target, not a promised detectable effect. Estimate precision/power from calibration only; do not enlarge the evaluation budget after observing its effect.

No successful-world filtering. For resource/method failures, report coverage and conservative score bounds using Brier's [0,1] range for missing predictions, including worst-case bounds for the paired difference. A declared deployment fallback (same policy for all arms) can have a separately labeled complete-denominator score. Claims of predictive advantage must survive the declared primary missingness treatment, not only complete cases.

## 4. Track C — exact counting, proofs and fair cost

Re-derive the factorization of V(D), essential-support/Möbius correction, h=1 and h=2 counts, self-inputs, persistent clamps and witness construction. State complexity in n, k, evidence size and integer bit complexity. Separate preprocessing from queries. k is bounded; h=3 fallback is not a general tractability result. Compare the derivation with variable elimination and knowledge compilation before calling it novel.

Add a competent generic counting comparator. Preferred investigation: pinned [d4v2](https://github.com/crillab/d4v2), following [projected knowledge compilation](https://drops.dagstuhl.de/storage/00lipics/lipics-vol341-sat2025/LIPIcs.SAT.2025.8/LIPIcs.SAT.2025.8.pdf). Pin the actual supported command/options; do not assume ordinary #SAT counts distinct mechanisms. Prove a bijection or project auxiliary/encoding multiplicities away, with exhaustive tiny counterexamples. If external compilation is infeasible on this machine, implement an independently derived variable-elimination/decision-diagram counter. Report unresolved comparator limitations, never equate explicit materialization's n=10 cap with the limits of all generic methods.

Benchmark D, strengthened SAT, and the new generic counter on n∈{8,16,32,48,64}, k=3, h≤2, with eight base instances per size. Balance four matched-structure and four neutral/rewired instances; all backends receive identical data/queries. Four queries per instance. Time cold builds and reuse at 1/4/16 queries. Matched timed repetitions belong to one instance cluster.

Instrument budget checkpoints at 1,10,60,300 seconds rather than timing only successful cases. Execute three repetitions only on a preregistered small timing subset, to fit the total budget. Randomize backend order and serialize timed trials to avoid contention. Report peak process-tree RSS, compilation/projection, counts, witness construction, proof generation/checking, caching and refusals. Include all costs in end-to-end plots. Enforce process cleanup and cumulative budgets.

Measure **workspace-only** and **full checked release** separately. A definite release includes the common SAT cross-check and actual independent proof checking where claimed. An authenticated decision is not a proof file. Do not remove the common cross-check just to retain a speedup. A new symbolic certificate/verifier is a stretch goal only after core comparisons; it needs an independent checker and negative fixtures.

Successful computation means correct counts/verdicts with declared certificate levels and resource use. The stronger research finding would be a useful cost/coverage advantage against the new comparator. Failure to beat it is publishable information about scope, not a reason to weaken it.

## 5. Track A — AI as an investigator (bounded pilot)

Implement a sequential investigation episode with an initially underdetermined target, public evidence and a menu of at most 16 permitted one-node measurements. Outcomes come only from the hidden simulator after selection. Budgets are 0,1,2,4 measurements; exclude target-equivalent purchases. All policies get the same menu and pay for observations. Query generation is independent of outcomes; conditioning on initial underdetermination is an explicit population restriction, applied by the evaluator.

Deterministic baselines: random, target-directed exact expected information gain (EIG), and a simple disagreement heuristic. Select the strongest eligible deterministic policy on separate calibration episodes. A small oracle lookahead policy may be reported as privileged upper reference, never a fair baseline if it sees hidden outcomes. Use a direct readout of exact posterior forecasts instead of asking the LLM to reconstruct them numerically.

Two technically suitable local models, preferably R4's qwen and mistral; 64 new evaluation worlds per model, shared across models and balanced over the locked eight synthetic strata. Evaluate **AI+D** and **AI+generic** with the same information, action API and limits. Cross deterministic policies with both backends on the same worlds (or replay identical requests) to distinguish policy from representation effects. Use n=8/h≤2 so generic tools work; this is an investigation test, not a timeout contest.

Limit each AI episode to eight request attempts including final output and retries. 2 models ×64 worlds ×2 arms ×8 attempts = **2,048** evaluation requests maximum. Up to 512 requests are for calibration/smokes (including their retries); 512 more are reserved for at most one validity-driven repair on fresh diagnostic worlds. No repeated model replacement or prompt tuning based on the evaluation effect. All requests, including failed requests, consume the global 3,072 ceiling and their own phase's suballocation.

Primary pilot comparison: fraction of targets correctly resolved after four measurements, AI+D minus the calibration-selected deterministic policy on D. “Resolved” requires a checked definite verdict; resource refusal is unresolved, not underdetermination. Report full measurement curves, wrong definite verdicts, forecast Brier, calls/tokens, decision latency and invalid-action rate. D−generic within the AI is a representation/interface secondary. A tie or AI loss must remain visible. This 64-world pilot provides intervals and future sizing; no promise of detecting a small policy advantage.

Validate exact measurement outcomes, isolation, accounting and ≥90% parsable valid actions on calibration; stop a semantically incorrect arm. Low accuracy is a result, not a model-exclusion gate. Any semantic bug discovered after evaluation starts invalidates the affected interpretation; preserve it and use the bounded repair allocation only for diagnostics, not a quiet replacement evaluation.

If AI simply copies the EIG recommendation, that is a useful interface result but not evidence of superior investigation. Do not hide EIG from a comparator to manufacture an AI gain. Preserve an extensible assumption-question API for Track M, but free-form natural-language formalization and learning weights are outside this batch's main experiment.

## 6. Track M — wrong assumptions, false assurances and recovery

Begin with a hand-checkable counterexample, and implement it as a regression test:

- n=2, declared H has indegree ≤1. Observe one-step outcomes (0,0) from initial states (0,0), (1,0), (0,1).
- In H, both node functions must be constant zero. For unseen initial state (1,1), node 0 after one step is therefore verified zero.
- The hidden simulator instead has node 0 = x0 AND x1 and node 1 = 0. It matches every observation but returns node 0 =1 at the unseen state.
- Widening to indegree ≤2 makes this target underdetermined. This demonstrates the difference between model-relative proof and world correctness. It is not a solver error.

If all remaining distinguishing measurements are forbidden because they reveal the target directly, acknowledge the identifiability limit. No policy can reliably detect indistinguishable worlds from identical evidence. Never invent an assumption detector with access to the hidden class label.

Build three separately scored panels of 40 base worlds each: realizable H controls; evidence-inconsistent misspecification; evidence-consistent misspecification. The last two are stress populations, not estimates of natural-world prevalence. Membership/counterexample filtering may use the evaluator but must have fixed criteria, a maximum search budget, acceptance rates and an explicit selection label. Do not rank cases by whether the proposed defense succeeds. Use k=1→2 or k=2→3 small systems when necessary for exactness; larger k=3→4 is optional, not required.

Compare: the current gate; a declared class-robust gate that verifies only across a prespecified union of plausible classes; a fixed enlarged-class baseline; and a fixed public-evidence-driven challenge/measurement policy. The union/larger class and its resource limits must be declared before outcomes. Since nested-class union equals the larger class, any difference needs a cost or policy explanation—not a new logical principle. Class expansion never receives the hidden offending rule. If checking the larger class times out, return unsupported; do not mark the old conclusion world-safe.

Report: false verified simulator outcomes/actions, definite correct release coverage, false uncertainty, unnecessary blocks, inconsistency detection, measurements, costs and class-change logs. Compare safety at matched coverage or show the full tradeoff. Abstaining on everything is a valid extreme baseline, not a practical success. Distinguish a proposed action's asserted postcondition from a causal guarantee about every action; use a fully specified simulator.

One exact counterexample establishes the limitation. The 120-world panel estimates behavior under the declared stress distribution only. Recovery must preserve realizable-case usefulness; if it does not, report the tradeoff and identify what additional evidence would be needed.

## 7. Statistical and interpretive discipline

One primary development contrast for G; C is an algorithm/cost study, A a pilot, M a diagnostic. Do not pool them into a four-way significance search. Use 95% paired cluster intervals, publish denominators and effect directions, and mark secondary/exploratory analyses. If formal significance is presented for multiple track/model claims, define and adjust the tested family prospectively; otherwise use descriptive intervals and no confirmatory language.

Design locks precede evaluation but are not independent preregistration. Report calibration use, model changes, failures, source-group dependence and all historical nulls. Complete execution can coexist with negative scientific findings. A funding brief should say what was demonstrated, what remains uncertain and the next decisive milestone.

## 8. Primary-source starting points (verify and extend)

- [A Knowledge Compilation Map](https://arxiv.org/abs/1106.1819): compactness and supported operations are separate comparisons.
- [Certifying Projected Knowledge Compilation](https://drops.dagstuhl.de/storage/00lipics/lipics-vol341-sat2025/LIPIcs.SAT.2025.8/LIPIcs.SAT.2025.8.pdf): projection and proof obligations for compiled counting; investigate the authors' implementation rather than inventing solver capabilities.
- [Biodivine Boolean Models](https://github.com/sybila/biodivine-boolean-models): externally authored Boolean models with provenance; individual model rights and transformations require explicit records.
- [SatLM](https://arxiv.org/abs/2305.09656): solver-assisted LLM reasoning already exists; novelty must be more specific.
- [Robust expected information gain](https://proceedings.mlr.press/v180/go22a.html): experiment rankings can depend on priors; this motivates a robustness comparison, not adoption of an unvalidated guarantee here.
- [Algorithmic Probability](https://www.hutter1.net/ai/algprob.pdf): distinguish finite codec priors from universal algorithmic probability.
