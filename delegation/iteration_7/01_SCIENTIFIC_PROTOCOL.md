# R7 scientific protocol — unseen-fact inference and claim checking at the indegree published models actually have

Director: Claude Fable, 2026-11-12. Implementation: Claude Opus. Development evidence only.
Background: `reports/review_r6/REVIEW.md`. This document is binding; where it leaves a choice open, decide it on
calibration groups only, write it in the lock, and continue.

## 0. Why the question changes

R5 and R6 asked which prior forecasts best inside the class H(n, 3). Three rounds gave the same answer: every
reasonable code is near its ceiling after 8–16 observations, and differences between codes are below 0.01 Brier.
That is a property of the class, not of the priors. A node with at most 3 inputs has at most 8 rows; a handful of
observations fills them and no prior has anything left to say.

The director's census of the pinned Biodivine corpus (throwaway script, **provisional until you reproduce it in
WP0**; 335 `.bnet` files, 21,650 nodes, essential indegree):

| Essential indegree | Share of nodes | Nested canalizing | Unate (monotone up to input signs) |
|---|---|---|---|
| 1–3 | 68 % | 99–100 % | 99–100 % |
| 4 | 9.2 % | 92 % | 98 % |
| 5 | 7.9 % | 76 % | 99 % |
| 6 | 4.1 % | 67 % | 97 % |
| 7–12 | 8.5 % | 23–56 % | 94–98 % |
| > 12 | 1.9 % | not tabulated | not tabulated |

- Only 20 of 335 files have every node at indegree ≤ 3. R5 and R6 evaluated the remainder only as clamped
  fragments, never whole.
- About 30 % of nodes have indegree ≥ 4. A node with 6 inputs has 64 rows and 1.8 × 10^19 possible tables. Counting
  compatible tables says nothing about an unseen row. A compact description says a great deal, because nearly all
  published rules are short.
- 120 files have maximum indegree ≤ 6, and 212 have ≤ 8.

So the place where a compact algorithmic description can matter is high indegree, and it is also where most
published models live. R7 moves the experiment there.

## 1. Setting W: wiring known, logic unknown

This is the standard situation in logic modelling of biological networks: who regulates whom is taken from the
literature, and the logic is to be inferred from data.

- **World:** a published model taken whole. No clamping, no fragments, no indegree filter on the model.
- **Public:** the number of nodes, anonymised node indices, and for every node its regulator set R_i (the essential
  regulators of the published rule after canonicalisation). The evidence. Nothing else.
- **Hidden:** every node's truth table.
- **Declared class H(G):** every node may be any Boolean function of its regulators (2^(2^d) tables for d
  regulators). Essentiality of each regulator is not part of the class. Every predictor receives the same public
  information.
- **Scoreable nodes:** 1 ≤ d ≤ 6. Nodes with d > 6 and free inputs are simulated with the true rule and observed in
  the evidence, but are never targets. Log their count per world.
- **Evidence (primary panel):** B synchronous transitions x → F(x) from B independent uniform random states, fully
  observed.
- **Evidence (secondary panel, "trajectory"):** the same number of transitions taken along trajectories from random
  initial states. Rows repeat, so this is harder and closer to time-series data. Same predictors, same queries.
- **Queries:** fresh random states not in the evidence. Score every scoreable node at each query state: Brier of
  P(node = 1 at the next step). A query row may or may not have been observed for that node; report both, and the
  split.
- **World score:** mean over scoreable nodes (equal node weight) and query states. The **high-indegree score** is the
  same mean restricted to nodes with 4 ≤ d ≤ 6.

Inference factorises over nodes because the wiring is public, so network size is not a limit. Use every eligible
model regardless of n, subject to a declared cap you set for cost.

## 2. Population and split

- Source: the pinned Biodivine corpus (commit `314b2fed`), parsed by the existing owner
  `src/causalguard/r5/external.py`.
- Eligibility, fixed before any score: at least 9 nodes and at least 3 scoreable nodes with 4 ≤ d ≤ 6. Record every
  exclusion with its reason.
- Groups are publication lineages, as before. Split by `sha256('r7-split|' + group)` order: the first quarter of
  groups is calibration, the rest evaluation. Commit the manifest before calibration.
- **Gate (WP0):** continue Track K only if there are at least 40 evaluation groups and nodes with 4 ≤ d ≤ 6 are at
  least 15 % of scoreable nodes in the calibration groups. If the gate fails, stop Track K, report the census, and
  finish Tracks V and L on what exists.
- Disclose: these lineages contributed clamped fragments at indegree ≤ 3 to earlier panels. No node with indegree
  ≥ 4 was ever scored, and no method was fitted on any of them. The director looked at corpus-wide class frequencies
  (the table above) before the lock. A second, independent corpus does not exist in the repository; do not claim
  transfer to unseen sources.

## 3. Predictors (Track K)

Each predictor is a prior over the tables of one node on its regulators. The posterior conditions on the observed
rows of that node. All are exact.

| Name | Role | Definition |
|---|---|---|
| `uniform` | counting baseline | Every table equally likely. This is what a model counter or an answer-set enumeration gives. An unseen row is 0.5. |
| `unate` | **field-standard comparator** | Uniform over tables that are monotone in each regulator for some sign pattern (signs unknown), mixed with `uniform` at weight ε. Local monotonicity is the assumption logic-modelling tools make. |
| `ncf` | literature-class comparator | Uniform over nested canalizing tables, mixed with `uniform` at weight ε. |
| `formula` | generic compact code | Description length of the shortest AND/OR/NOT formula over the regulators, in a declared prefix code, with a literal-table escape. If the repository's `circuit` code extends to d ≤ 6 without a new design choice, use that owner's definition. |
| `cgh` | **our method** | The CGH-1 flat analytic code (`s4/hcode.py::local_catalogue`, formal-paper gate families with recursive canalizing fallback) extended from d ≤ 4 to d ≤ 6, with its literal escape. With public wiring the support cost is a constant and drops out. This is a port of a documented capability: do not add families or re-weight the catalogue. |

Requirements:

- **Full support.** Every predictor gives every table in the class positive prior mass. ε for `unate` and `ncf` is
  chosen on calibration from {0.01, 0.05, 0.2}; the choice favours the comparators, which is intended.
- **One mass per distinct table.** A table reachable by several names or formulas is counted once, under the rule
  the code declares. State the rule.
- **Normalisation.** Show each prior sums to 1: by enumeration over all tables for d ≤ 4, and by exact accounting
  of the named-table mass plus the escape mass for d = 5 and 6.
- **Exactness tests.** Against brute-force enumeration of all 65,536 tables at d = 4 for every predictor. At d = 5
  and 6, against a second implementation that shares no code with the first, for `unate`, `ncf` and `cgh`, on at
  least 200 evidence sets. Plant one defect and show a test fails.
- **Duplicates across sign patterns** in `unate`: a table that does not depend on a regulator is monotone under
  both signs of it. Count it once. Test against explicit set enumeration at d ≤ 4.
- **Cost.** Report wall time per node by d. If a predictor cannot be computed exactly at d = 6 within budget, lower
  the scoreable limit for all predictors together and record it; do not approximate one predictor.
- **No fitted frequencies.** No predictor in the primary may estimate weights from observed frequencies, in this
  world or across the corpus. See §7.

## 4. Endpoints (Track K)

Lock in `docs/R7_DESIGN_LOCK.json` before any evaluation-group score.

- **Budgets.** Probe B in {4, 8, 16, 32, 64, 128} on calibration groups. The primary budget is the probe at which
  the `unate` comparator's high-indegree Brier is nearest the middle of [0.03, 0.20]. Report it and its two
  neighbours.
- **Comparator.** The better of `uniform` and `unate` on calibration at the primary budget (world score).
- **Method.** `cgh`. Nothing about it is selected.
- **Primary:** Brier(comparator) − Brier(`cgh`), world score, primary budget, random-state panel, evaluation
  groups. Source-group cluster bootstrap, 10,000 replicates, with worst-case missingness bounds. Positive favours our
  method. Planning value 0.02.
- **Prespecified secondaries:**
  1. The same contrast on the high-indegree score. This locates the effect; it is expected to be several times the
     primary.
  2. `uniform` − `cgh`: the description-length principle against counting.
  3. `formula` − `cgh`: whether our vocabulary adds anything to a generic compact code.
  4. `ncf` − `cgh`: whether a single literature class already does the job.
  5. By indegree d = 1 … 6, by budget, by whether the query row was observed, and by whether the true table is
     nested canalizing, unate, or neither.
  6. The trajectory panel, same contrasts.
  7. Per-world difference distribution: median, quartiles, share of worlds improved, and the share of the net gain
     carried by the top decile of worlds.
  8. Effect against number of nodes and against the share of high-indegree nodes.
- **Figures (required, rendered before any number is written into a report):**
  - per-world Brier differences as a strip plot, primary and high-indegree;
  - Brier against budget for every predictor, one panel per indegree;
  - for three evaluation worlds chosen by hash, not by result: one high-indegree node's observed rows, the true
    table and each predictor's forecast for every row, side by side.
- **Recorded predictions.** Write your numerical predictions for the primary and for secondaries 1–4 into the lock.
  The director's are: primary between +0.01 and +0.04 against `unate`; high-indegree contrast above +0.05;
  `uniform` − `cgh` larger than both; `formula` − `cgh` within ±0.01; `ncf` − `cgh` small and of uncertain sign.

Outcome map, to be applied as written:

| Result | Reading |
|---|---|
| Primary interval above 0 and estimate ≥ 0.02 | Our compact description improves unseen-fact inference on whole published models at realistic indegree, against the field-standard assumption. |
| Primary above 0 but < 0.02, high-indegree contrast ≥ 0.02 | Supported for high-indegree nodes only. Say so in the headline. |
| `cgh` and `formula` within ±0.005 | The gain belongs to compact description in general. A specific advantage of our vocabulary is not established. |
| `ncf` matches or beats `cgh` | A known structural class explains the gain. Report it as such. |
| `unate` matches or beats `cgh` | The field-standard assumption suffices for forecasting. Our contribution is then exactness and checking (Track V), not accuracy. |
| `cgh` does not beat `uniform` at high indegree | This contradicts the census. Audit the implementation before interpreting. |
| Anything else | Describe it plainly and say the map did not anticipate it. |

## 5. Track V: checking claims under declared assumptions, on real models

Same worlds and evidence as Track K; no extra computation beyond per-node compatible sets. A claim is "node i is
v at the next step from state x". Under a declared class C, the claim is **verified** if every table in C that fits
the evidence agrees with it, **refuted** if every one disagrees, and **undetermined** otherwise.

- Classes: ALL (the declared class H(G)), UNATE, NCF, CATALOGUE (the `cgh` named tables). On published models these
  assumptions are false at known rates, so the wrong-assumption error is real rather than planted.
- Report, on claims about rows not observed for that node, by class, budget and indegree:
  - coverage: the share verified or refuted;
  - false-verified rate: the share of decided claims that are wrong;
  - the same two numbers split by whether the true table is inside the class;
  - how often the evidence itself contradicts the class (empty compatible set), which is the only warning the
    checker can give without a measurement.
- **Matched-coverage comparison (prespecified, answers R5-F4).** Rank the same claims by confidence
  max(p, 1 − p) under `cgh`, under `unate` and under `uniform`. At the coverage that UNATE checking achieves, compare
  the error rate of: UNATE checking; the `cgh` ranking; the `unate` ranking. Give full risk–coverage curves as a
  figure. Bootstrap by source group.
- State the proof level honestly: these are exhaustive finite checks inside a declared class, not proofs about the
  biological system.

There is no primary hypothesis in Track V. It is a characterisation with prespecified metrics. Director's recorded
predictions: ALL decides nothing on unobserved rows; UNATE decides a minority of them with a false rate of a few per
cent, almost all of it from tables outside the class; at matched coverage the `cgh` ranking has a lower error rate
than UNATE checking only if high-confidence forecasts are right more often than monotone entailment is, which is
not obvious.

## 6. Track L: is the AI's own guess already as good? (bounded pilot, lowest priority)

Question: on the same task, how does a local language model's unaided forecast compare with counting, with the
field-standard assumption and with our method, and does handing it our method's output help?

- 32 evaluation worlds chosen by hash; one high-indegree target node per world, chosen by hash; evidence at the
  Track K primary budget shown as a table of regulator values and outcomes; 4 claims about unobserved rows per
  world, all in one request.
- Arms, paired on the same items: **A** the model alone; **T** the model given the `cgh` forecast and the UNATE
  check result, with the assumption stated in words. The model returns a probability and a verdict (true, false,
  cannot tell) for each claim.
- Reference rows without a model: `uniform`, `unate`, `cgh`.
- Models: the two local models used in A2. Temperature 0. Smoke gate: 4 worlds per model, at least 90 % parsable.
- Report: Brier of the stated probability; definite verdicts that are wrong; in arm T, how often the model departs
  from the tool and whether departures help or hurt.
- Requests: at most 400 new, inside the global ceiling of 3,072 (1,498 used). Write `docs/R7L_DESIGN.md` before the
  first request. Drop the second model before any request if needed to fit.
- This is a pilot for a later AI panel. Do it last. If Tracks K and V are not finished, skip it and say so.

## 7. Sharing and the status of XDC-EB

- XDC-EB fits type weights from observed frequencies and does not charge for them. It is a plug-in estimate, not a
  description length. Label it that way wherever it appears, including in the R6 documents you maintain. It is not a
  candidate for "our method" in R7.
- Exact XDC is a valid code (each new type is paid for at the base-code price). Optional secondary, only after
  Tracks K and V are complete: `xdc[cgh]` on evaluation worlds with at most 12 scoreable nodes, against `cgh`. Report
  how many worlds qualify. Do not build a new approximation.

## 8. What must not happen

- No change to the population, budgets, ε, comparator or method after any evaluation-group score is seen.
- No pooling of calibration and evaluation groups in any reported interval.
- No headline that averages a subpopulation where the effect is planted or expected with one where it is not,
  without both parts beside it.
- No claim about Kolmogorov complexity, universal priors, biological truth or unseen sources.
- No fitted frequencies inside anything called a description length.
