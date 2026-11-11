# R5 operational protocol (development; not a confirmatory freeze)

This makes `delegation/iteration_5/01_SCIENTIFIC_PROTOCOL.md` concrete. Identities are pinned in
`docs/R5_DESIGN_LOCK.json`. `docs/FREEZE_RECORD.json` is absent and the confirmatory runner is not used.
Deviations from the assignment are listed in §6.

## 1. Track G — unseen inference

**Population.** `src/causalguard/r5/data.py` (`G_POPULATION_SPEC`, hashed in the lock). Eight strata, n = 8,
k = 3: template_exceptions, imperfect_modules, shared_motifs, feedforward_hetero, feedback_canalizing,
mixed_parity_thresh, rewired_control (degree-preserving rewiring of an S1/S2/S3 instance of the same split, same
source group), uniform_H. Calibration 64 (salt `r5-G-cal-v1`), evaluation 320 (salt `r5-G-eval-v1`): 280 source
groups in evaluation (40 rewired controls share their source's group). Split audit: 0 shared groups, 0 exact or
isomorphic cross-split duplicates.

**Design.** 24 distinct uniform one-step observations, every 4th a persistent clamp of 1-2 nodes; nested budgets
8/16/24 are prefixes. Eight queries (4 h = 1, 4 h = 2; none / initial_edit / persistent_clamp), literal
`target node = 1`, start and effective start never among the 24 evidence inputs, no duplicate
(s0, intervention, h, target), no clamped target. Drawn from a design stream keyed by the opaque mechanism id; never
reads the mechanism.

**Predictors** (`r5/priors.py`, `s4/prior.py`). uniform; index (old flat); circuit; gate; cgh_flat (analytic-only
CGH; the hierarchy ablation); **cgh_prior = full CGH prior (FLAT + TEMPLATE + MODULE, no PATCH, no DICT; unchanged
R4 language)**; *_noanalytic ablations; GSR(alpha) generic shared-rule programs with alpha in {0.25, 0.5, 0.75};
shortest cgh_prior / index model (secondary). Exact rational for codec averages; GSR float64 with declared relative
error 1e-9 (status `bounded`), validated against exact program enumeration.

**Champion.** On the 64 calibration instances at B = 16, minimum equal-stratum-weighted mean world Brier among
{uniform, circuit, gate, gsr_a50, gsr_a25, gsr_a75} (tie order as listed). Locked globally before evaluation.

**Primary.** Evaluation, B = 16: `mean_world_Brier(champion) - mean_world_Brier(cgh_prior)`, world Brier over all
eight queries, equal stratum weights; 95 % percentile interval from a cluster bootstrap over the 280 source groups
(10,000 replicates, seed 20261111). Positive favours full CGH. Practical planning value 0.02. Missing predictions:
worst-case bounds with Brier in [0, 1]; a claim of advantage must hold under those bounds.

**Secondaries.** All predictors at 8/16/24; hierarchy ablation (cgh_flat - cgh_prior); uniform - cgh_prior;
analytic vocabulary (cgh_flat_noanalytic - cgh_flat); shortest-model; per stratum; determined vs underdetermined
queries (logical status from exact uniform counts); accuracy; reliability bins (underdetermined, B = 16); costs and
structured-enumeration refusals.

**External panels** (`r5/external.py`, `artifacts/r5_source_manifest.json`). Biodivine Boolean Models at
`314b2fed94689c38d3aaaf8101ed622b3501c7f7`, not redistributed. Intact: whole models with 6 <= n <= 10 and every
essential indegree <= 3 (free inputs become self-memory nodes): 4 eligible source groups (all used, descriptive
range + leave-one-source-out only). Transformed: deterministic backward-BFS 8-node subnetworks, outside regulators
clamped to 0, indegree > 3 excluded (never simplified); 162 eligible groups, 40 selected by sha256 order, at most
4 instances per group (159). Same design and predictors, champion fixed from synthetic calibration. Never pooled.

## 2. Track C — counting and cost

Derivation `docs/R5_COUNTING_DERIVATION.md`. Backends: D (support-schema symbolic), B (strengthened SAT, ladder AMO;
counts only when the class is materializable, n <= 10), GEN-VE (`r5/counting.py`, independent explicit-domain VE).
External projected compiler: ganak v2.9.0 adapter (`ganak_count`), **not run** (download/execution not authorized in
this session); d4v2 not buildable on arm64. Instances `r5/benchmark.py`: n in {8,16,32,48,64}, k = 3, 8 bases
per size (4 matched cyclic templates + their 4 degree-preserving rewirings, paired clusters), 16 one-step
observations, 16 queries (first 4 scheduled; reuse at 1/4/16). Items serialized (1 worker), randomized order (seed
20261111). Workspace phase and full checked release phase (D and B: check + common SAT cross-check with RUP
checking + witness replay + commit) each in a child process with a 300 s limit; checkpoints 1/10/60/300 s from one
execution; peak RSS per phase. Repetitions x3 on {(8,0),(8,4),(32,0),(32,4)}.

## 3. Track A — AI investigation pilot

`r5/investigation.py`. Worlds: locked G generators on salts `r5-A-cal-v1` / `r5-A-eval-v1`, 8 per stratum (64
evaluation worlds shared by both models). Public evidence 8 one-step observations; target = first scheduled
query underdetermined by the public evidence. Menu (public, query-dependent): 4 target-node measurements at
states 1-2 bits from the query's effective start, 4 other-node measurements near it, 8 random (half with a
one-node clamp); target-equivalent purchases excluded; presentation order shuffled. Budgets 0/1/2/4 = prefixes of
one trajectory. Readout identical in both arms (uniform-H exact posterior, per-item P(outcome) and exact EIG);
mechanism view differs (D: named analytic candidates; generic B: per-node counts). Deterministic policies random /
eig / disagreement (selected on 64 calibration worlds by resolved@4 on D; tie order eig, disagreement, random);
oracle_lookahead privileged reference. Models: qwen2.5:7b (Ollama, num_ctx 16384) and
mistral-small-3.2-24b-instruct-2506-mlx (LM Studio, context 16384); temperature 0, seed 0, max_tokens 400; at most
8 physical attempts per episode. Primary: resolved@4 (AI+D) - resolved@4 (selected policy on D), paired by world,
world bootstrap. Calibration smoke: 8 worlds x 2 arms per model (<= 256 calls); validity gate >= 90 % valid actions
per model/arm.

## 4. Track M — assumption failures

`r5/misspec.py`. Exact n = 2 counterexample (test). Panels of 40 base worlds each, n = 6, declared k = 2:
realizable; evidence-inconsistent (hidden has 1-2 nodes of indegree 3, V_H(D) empty); evidence-consistent (same
generator, V_H(D) nonempty). Membership: construction label + PUBLIC emptiness of V_H(D); seeded search, max 4000
draws, acceptance logged (salt `r5-M-eval-v1`). Policies: current gate (H(6,2)), expanded (H(6,3)), robust_union
({H(6,2), one node indegree 3}), challenge (<= 4 public falsification measurements, class change on contradiction),
abstain. Scored after decisions: false verified outcomes, correct releases, unnecessary blocks, false uncertainty
(abstain while determined within H(6,3)), measurements, class changes, cost.

## 5. Resources and order of execution

Ceilings in `BATCH_CONTRACT.json`; accounting in `r5/contracts.py` (ledger reservation before dispatch; CPU upper
bound = sum of attempt seconds; server hours = sum of request latencies + logged load time). Worker memory guard
6 GiB per worker (4 workers; global 24 GiB). Order: G-cal + A-det-cal + A-AI-cal -> lock -> G-eval + external +
M (4 workers) -> C (serial, no model serving) -> A-det-eval -> A-AI-eval (model serving only).

## 6. Deviations from the assignment (to be completed)

- External projected compiler not run (permission) — C comparison against a knowledge compiler incomplete.
- Intact external panel has 4 source groups (< 20): descriptive only.
- Learned order/dictionaries (optional secondary) not implemented.
