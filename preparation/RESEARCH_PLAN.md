# CausalGuard: exact feedback for bounded epistemic improvement

Prepared 2026-11-09. This is a proposal and pre-sprint feasibility assessment, not a report of model performance. Input: `../doc/Gemini-Talk.txt`.

**Superseded for implementation:** the user's subsequent clarification makes compact index representations, incomplete-evidence inference, and description-length selection central. Use `../delegation/00_START_HERE.md` and its v2 scientific contract. This file is preserved as historical rationale; its small sample proposals and oracle-feedback experiment are not the current primary study.

## Recommendation

Proceed with the idea after narrowing its claim. Build a small research instrument that tests whether explicit causal models and exact counterexamples help an AI correct false claims, recognize insufficient evidence, and retain improvements on unseen problems. Preserve neural weight evolution as a separately gated experiment. Do not make clinical validation or unrestricted model breeding prerequisites for the sprint.

The valuable insight in the original proposal is the separation between a fallible proposer and an independently checked selection signal. The difficulty is defining exactly what that signal certifies. A deterministic program can consistently implement the wrong assumptions. We should make that boundary the subject of the research.

Working research question: **Does exact counterexample feedback improve causal-claim reliability more than equal-budget self-critique or resampling, and does any improvement transfer beyond the cases used for feedback?**

The intended user is an evaluation researcher or developer deciding whether to trust a model modification. The immediate product is a reproducible evaluation harness with inspectable evidence, not a universal truth service.

## Assessment of the original premises

| Premise | Assessment | Consequence |
|---|---|---|
| Physical measurements eliminate epistemic error | False as a general inference. Measurement error, missing variables, model selection and diagnostic interpretation remain distinct problems. | Use synthetic systems with declared rules for the initial exactness claim. |
| Algocyte is an infallible deterministic diagnostic oracle | Not established. The company's materials describe physics-informed testing and AI-supported monitoring, and distinguish development/validation stages. They do not establish zero diagnostic error. | Treat it as inspiration for grounding, not a dependency or ground-truth provider. [Company source](https://algocyte.ai/) |
| A frontier model can inspect and alter other networks | There is a relevant research report, but its results are narrower than the conversation suggests. | Study constrained repair, not assume arbitrary capability creation. |
| Neural weights are interchangeable good genes | A useful metaphor, not a valid merge algorithm. Parameter coordinates and learned representations must be compatible. | Start with adapters sharing a base checkpoint if weight work becomes feasible. |
| CausalBool can certify arbitrary diagnostic prose | No demonstrated translation or clinical semantics. A formal verifier proves statements relative to a formal system. | Start with typed queries; assess natural-language translation separately. |
| A better selected candidate demonstrates recursive self-improvement | Selection, inference-time correction, prompt optimization and persistent weight updates are different interventions. | Name which object changes and evaluate it separately. |

The [weight-space report](https://rikiyat.github.io/blog/weight-space-programming/) is a November 2026 blog research report. Its larger-model experiment uses Python and budgeted forward evaluations. The reported Qwen improvement repairs a looping failure; the non-looping Gemma control does not show a comparable improvement. It also reports failure to identify sycophancy from weights alone. This supports a bounded repair hypothesis, not general weight-based truth verification. We have read the report, not independently reproduced its logs.

The [Benjamin Todd article](https://80000hours.org/2024/05/project-idea-ai-for-epistemics/) argues for better forecasting and decision support. The conversation's guaranteed-truth system, hospital mandates and military blank checks are extrapolations, not an evidence-based business case supplied by that article.

## What CausalBool actually contributes

Inspected public repository at commit `376a11ddf25063d49dc8f6cd98bbb3baf2e1cc43`, cloned into `/tmp/epistemics-causalbool-review` for this review. No codebase graph tools were available in this session, so source inspection used filesystem tools.

| Upstream component | Observed interface | Proposed use |
|---|---|---|
| `index-deconvolution/src/causalbool.py` | `Network`, `step`, `repertoire`, explicit LSB-first conventions | Forward oracle for small synchronous systems |
| `index-deconvolution/src/network_generator.py` | Seeded `random_network` | Reproducible synthetic systems |
| `index-deconvolution/src/deconvolution.py` | Reconstruction, forward checks, symbolic routines | Later consistency/recovery experiments; not needed for first benchmark |
| `self-improving/README.md` | Existing charter for exact selection and explicit improvement levels | Prior work to acknowledge; useful controls and lineage discipline |
| `src/dynamics/Boolean_Dynamics.py` | Edge-derived activation/inhibition simulator | Do not use as a general logic parser: explicit logic parsing remains a TODO in the inspected file |

The forward module uses standard Python. We ran a small independent-reference check on 60 generated networks (3–8 nodes), covering every state within each network. The saved result is `feasibility_result.json`. This validates an integration path, not the entire codebase, all gate parameters, symbolic scalability, or the project's broader theoretical claims.

The probe also demonstrates two essential benchmark cases:

1. With `C(t+1) = A(t) AND B(t)`, the claim “setting A=1 always makes C=1 next” is false. `B=0` supplies a concrete counterexample.
2. If only `00 -> 0` and `11 -> 1` have been observed, both AND and OR are compatible. The output at `10` is undetermined by that evidence. A verifier that silently chooses AND would certify an unjustified answer.

We must distinguish a synchronous transition system from an acyclic structural causal model. Initially use finite-horizon, time-indexed interventions with explicitly declared update rules. Do not claim Pearl-style counterfactual semantics merely because a network has directed edges.

## Experimental contract

### Worlds, evidence and questions

Use 4–8-node Boolean systems, indegree at most three, synchronous updates and horizons of one to three updates. Begin with AND, OR, XOR and NOT; expand the gate catalogue only after independent parity checks. Store bit order, gate input order, initial-state constraints, horizon and intervention semantics in every item.

Define a persistent clamp operationally: overwrite the selected coordinates before each update and after each update. A one-time state edit is a different task and must have a different identifier. The feasibility probe covers a one-time edit and one update only.

Two evidence regimes:

- **Specified world:** all equations and relevant initial-state information are supplied. Enumerate all admissible initial states to answer a universal claim. An existential counterexample refutes it.
- **Partial evidence:** the item supplies a small, explicitly bounded hypothesis class of candidate mechanisms and observations. Check every compatible mechanism and state. Return `entailed` if all satisfy the claim, `refuted` if all falsify it, and `underdetermined` if the compatible mechanisms disagree. Empty compatibility sets are `inconsistent_evidence`, never vacuously entailed.

Within a particular mechanism, universal claims are false when even one admissible state violates them. Across alternative mechanisms, disagreement about that universal proposition produces `underdetermined`. Keep these two quantifiers separate.

Questions: next-state prediction, finite-horizon intervention claims, necessary-versus-sufficient conditions, and evidence sufficiency. Use typed JSON with fixed labels. Require a probability vector over the three valid verdicts and allow an explicit operational abstention. Handle inconsistent evidence as a separate stress set. Invalid output is an error, never silently converted to abstention.

Initially render text from the same structured object used by the oracle. If free-form prose is later accepted, compare its parsed representation with a human-reviewed gold representation. Formal correctness after a wrong translation is not end-to-end correctness.

### Conditions and budgets

Use the same frozen model and decoding settings within each comparison. Proposed pilot: 30 development worlds, balanced task templates, approximately 120 items. Pilot difficulty and throughput; do not use these items in the final test.

| Arm | Three-call maximum per item | What it measures |
|---|---|---|
| A: unaided answer | First response only; also retained as every arm's shared baseline | Starting ability |
| B: self-critique | Answer, critique, revision; no oracle feedback | Extra reasoning budget |
| C: resampling | Three independent answers; predefined majority rule, ties abstain | Extra sampling budget |
| D: exact feedback | Answer, then up to two structured verifier-feedback/revision rounds | Benefit of external exact evidence |
| E: direct symbolic solver | Oracle answers without LLM | Accuracy ceiling and cost baseline |

Share/cache the initial response where appropriate; all arms get the identical original problem. For D, disclose that the verifier has privileged computation. Feedback contains the verdict check and at most one witness or pair of disagreeing mechanisms. Measure final answer changes, not just the verifier's own accuracy. If C uses oracle selection instead of majority, report it as an additional oracle-assisted arm, not the ordinary resampling control.

Log actual tokens, time, oracle evaluations and calls. Equal call caps are not equal computational cost. Report both; do not fabricate dummy calls for arms finishing early. The direct solver baseline is essential: if it already solves the whole structured task cheaply, an LLM adds value only at an interface or transfer boundary.

### Persistent improvement, separate from answer correction

If the core evaluation works, use development failures to propose up to eight revised instruction prompts. Select on a separate validation split and freeze one prompt. Compare the original and selected prompts **without oracle feedback at test time**. This measures system-level persistent improvement. It does not change model weights.

For a fair search control, compare with eight independently proposed prompts and the same selection budget. Record every candidate, not only the winner. Prompt selection must not consume the final test set.

### Splits and analysis

Proposed full dataset: 60 development worlds, 30 validation worlds, 60 test worlds with approximately four linked items each. Use a separately generated stress suite for larger sizes and held-out mechanism compositions. These counts are a budget proposal, not a power guarantee.

Group splits by world and detect duplicates under node renaming where feasible. Keep paraphrases, relabelings and minimally altered versions of a world in the same split. Hold out some graph/gate compositions; fresh random seeds alone do not establish out-of-distribution generalization. Candidate selection sees development/validation only. Freeze and hash the manifest before the test run; record any test access.

Primary endpoint: paired change in macro-averaged verdict accuracy for D versus B on held-out worlds. Report C as the sampling comparator. Operational abstentions and malformed outputs count as incorrect in this primary endpoint. Also report:

- False `entailed` rate, especially under partial evidence.
- Multiclass Brier score from the probability vector; invalid distributions reported separately.
- Answer coverage and error among answered items, so abstaining everywhere cannot look successful.
- Correct-to-incorrect and incorrect-to-correct revision rates.
- Cost per correctly resolved item, latency, and performance by evidence regime.
- An uncertainty interval from paired bootstrap resampling of worlds, keeping linked items together. Repeat model runs across three seeds if affordable; do not count repeated outputs as independent worlds.

Development-only shortcuts checks: majority-label baseline; simple classifier using surface features; label balance by template; node renaming; irrelevant-text insertion; removal or swapping of necessary premises. A model unaffected by a relevant premise change is not demonstrating the intended reasoning. Preserve held-out tests even when checks expose a disappointing result.

## Making the weight-evolution component real

This is feasible as a second experiment, but should not be allowed to prevent a completed evaluation submission.

1. Pick one small open-weight base supported by the actual hardware; record revision, tokenizer, license, precision and chat template. Confirm inference and fine-tuning throughput before committing to a model family. Available models and compute remain unconfirmed.
2. Train two small adapters from the **same** base, one on exact intervention examples and one on uncertainty/evidence-sufficiency examples. Train only on development data.
3. Form bounded candidates using `W_candidate = W_base + alpha*delta_1 + beta*delta_2`. Start with a fixed coefficient grid including each parent and the unchanged base. Compatible tensor shapes alone are insufficient for arbitrary unrelated model merges.
4. For LoRA, combine the effective delta matrices or preserve a sum of adapters. Independently averaging low-rank A and B factors does not generally average their represented updates. Do not splice packed quantized weights.
5. Select by validation accuracy subject to a predeclared false-entailment constraint; keep the base if no candidate qualifies. Evaluate the frozen winner once on held-out worlds.
6. Compare both parents, uniform merge, equal-budget random coefficient search, and one adapter trained on the pooled dataset. Otherwise any gain could come from training data, extra search or ensembling rather than evolutionary selection.

Only then add a bounded mutation loop over coefficients. An LLM choosing coefficients is optimization of a merge recipe; an LLM directly editing weight tensors is another experiment. Neither is automatically recursive self-improvement. For a low-compute demonstration of actual weight mutation, use a tiny neural predictor on Boolean transition data, with explicit limits on transfer to language models; report it separately.

Go/no-go: do weight work only if the oracle and core eval are stable, a complete candidate evaluation fits within 15 measured minutes, and training plus all controls fit the remaining budget. Otherwise ship the core result and document this extension.

## Novelty and relevant research

| Prior work | What it already covers | Our remaining hypothesis |
|---|---|---|
| [CLadder](https://arxiv.org/abs/2312.04350) | Symbolically grounded causal-reasoning evaluation | Explicit verifier-guided revision and evidence-sufficiency behavior under controlled intervention semantics |
| [Procedural-generation critique of CLadder](https://arxiv.org/abs/2610.38100) | Reports predictive surface patterns and brittle causal evaluation | Test premise sensitivity and template shortcuts rather than assuming generated labels imply a valid benchmark |
| [CounterExample Guided Neural Synthesis](https://arxiv.org/abs/2001.09245) | Neural proposals guided by formal counterexamples | Study bounded epistemic claims, uncertainty and transfer; do not claim invention of counterexample-guided learning |
| [Evolutionary model merging](https://arxiv.org/abs/2403.13187) | Evolutionary search over model combinations | Test exact causal evaluation as a selection signal if the weight extension runs |

These are initial positioning checks, not an exhaustive novelty review. A combination of existing techniques is not enough by itself. The strongest possible result is an informative boundary: when exact feedback helps, when it creates dependence on the verifier, and when a selected improvement fails under structural shift. A null result remains useful if the controls make it interpretable.

## Implementation sequence and completion gates

| Stage | Concrete output | Completion gate |
|---|---|---|
| Preparation, Nov 9–12 | Oracle adapter, schema, independent reference tests, pilot, draft analysis contract | Hand-worked cases and enumeration agree; runtime measured; all prior work dated |
| Friday, Nov 13 | Frozen manifest, model settings, prompt templates and pilot-informed scope | No unresolved oracle mismatch; test split isolated |
| Saturday, Nov 14 | Core comparisons with raw response/cost logs | Every arm finishes; failures retained; no test-driven prompt changes |
| Sunday, Nov 15 | Paired analysis, figures, report and reproducibility instructions | Recompute tables from logs; claims match evidence |

If throughput is low, prioritize one model and the four core LLM conditions over a large model leaderboard. If almost every baseline answer is correct, increase development difficulty before freezing. If parsing dominates failures, simplify the schema and report this limitation. If feedback helps only during the same conversation, report assisted correction rather than learned improvement.

Suggested next files: `src/oracle.py`, `src/tasks.py`, `src/model_client.py`, `src/run.py`, `src/analysis.py`, `tests/test_oracle.py`, and a frozen `protocol.json`. Use a restricted data schema, not executable model-generated Python, for the initial harness. No external publication, model download, paid inference or registration was performed during this assessment.

## Sprint fit and submission

Primary fit: Track 1 (Model Epistemics & Decision-Making Evals). A reusable verification artifact may also fit Track 2. Track 4 is an open/deployment track, not the “Safety Evolution” track named in the conversation.

The official page specifies an eight-page report limit excluding references/appendices, the official template, a 150–250-word abstract, authors/affiliations, and a required limitations/dual-use appendix. It permits existing work with explicit disclosure of what was done before the sprint. Mark this preparation and reused CausalBool code accordingly. Deadline: November 15, 23:59 AoE, equivalent to November 16, 05:59 in Mexico City. Aim to finish Sunday locally. The fetched page also contains a closed-window UI message despite the future dates; verify the live registration/submission state before relying on it. [Sprint requirements](https://apartresearch.com/sprints/ai-x-epistemics-research-sprint-2026-11-13-to-2026-11-15)

Proposed report figures: paired accuracy by condition and evidence regime; false-entailment rate against coverage; one counterexample with its complete trace; optional transfer performance before/after persistent optimization.

Required limitations should include synthetic-world scope, finite horizons, bounded mechanism classes, translation errors, model-specific results, search overfitting and uncertainty intervals. A misleading use would be presenting a certificate about an assumed model as proof about the real world. Keep the assumptions attached to every certificate. No patient data or clinical efficacy claim is needed for this study.

## Current status and unresolved inputs

- Completed: source fact-check, initial related-work positioning, public CausalBool source inspection, small executable parity/counterexample probe, proposed protocol and implementation path.
- Not completed: LLM pilot, benchmark implementation, model selection, training, weight mutation, final experiments, registration or submission.
- Needed for sizing: actual available machine/GPU, local versus hosted model preference, budget, team capacity. The upstream self-improving charter mentions an M3 Ultra with 96 GB, but that is not confirmation of availability for this sprint.
- Decision recommendation: commit to the exact-feedback evaluation; preserve weight evolution as a clearly separated extension with a measured feasibility gate.
