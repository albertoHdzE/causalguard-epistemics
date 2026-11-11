# S4 amendment: algorithmic modeling and checking AI conclusions before release

2026-11-11. User-requested amendment to the iteration-4 assignment, before implementation/pilot. Read with `RESEARCH_DIRECTION_S4.md`. This changes the conceptual framing and adds a bounded verification workflow; it does not replace historical endpoints, authorize confirmation, or enlarge the local model-call budget.

## Research identity

The research program studies compact generative models of complex behavior and their use in reliable AI reasoning. Boolean networks are the first precisely testable environment, not the limit of the scientific ambition. The intended contribution is an executable account of possibilities: rules, explicit ordering, composition, uncertainty and checkable consequences.

Three related intellectual motivations must remain distinct:

- Algorithmic information theory motivates describing an object by a program that generates it and investigating description-dependent inductive priors.
- Simple-program complexity motivates studying how short rules yield rich behavior. It does not imply every behavior has a useful shortcut; Wolfram also emphasizes computational irreducibility. See [Wolfram's retrospective](https://writings.stephenwolfram.com/2017/05/a-new-kind-of-science-a-15-year-view/).
- Mechanistic modeling motivates deriving consequences and interventions from explicit rules. Exact consequences of an assumed mechanism and discovery of the actual mechanism are different achievements.

Do not describe this work as a universal truth detector or a demonstrated implementation of universal algorithmic probability. Describe it as **algorithmic modeling for verifiable AI reasoning, evaluated first in finite deterministic systems**. Broader generalization is a research objective.

## What was read in the original formal-method paper

Source: `/Users/alberto/Documents/projects/CausalBool/papers/method/manuscript_formal/method_paper.tex`, titled *Causal Index-Set Calculus for Boolean Networks and Deterministic Reconstruction*. Pin its hash in the method-coverage document. The reviewer inspected its introduction, definitions, gate formulas, reconstruction and support-locality results, ordering results, complexity discussion and stated limitations; this is not a new certification of the entire manuscript or its historical experiments.

The paper explicitly describes Boolean networks as an artifact for studying short rules and generative behavior. It also explicitly limits its main calculus to consequences of known mechanisms, primarily synchronous one-step updates. The main ingredients include:

1. Ordered exhaustive repertoires, with an explicit LSB/MSB transport map.
2. Bit bands, parity classes and Hamming-weight/threshold classes, not only flat schema unions.
3. Local one-set formulas and exact composition.
4. Support-local query evaluation that factors out irrelevant coordinates.
5. Separation of mechanism description, generated dataset and validation sampling.

**Correction to the previous delegation:** XOR/parity and threshold formulas already belong to the original analytic calculus. Adding their faithful implementation to this sprint repository is a port of a documented capability, although adding an opcode to a particular existing wire format is still a versioned codec extension. The flat `index` codec's XOR disadvantage does not establish that the original analytic calculus is bad at XOR.

The method-coverage map must now distinguish three artifacts: the analytic index-set calculus in this paper, the current flat schema codec, and the HID ordered/shared program language. Do not use any one as a synonym for the other two.

### Precise mathematical boundaries to carry forward

The support-locality result enumerates at most `2^c` assignments where `c = |C_q|`, the number of distinct support coordinates. With `d` the sum of queried gate arities, `mu = d-c`; `2^mu` is the reduction factor relative to independently enumerating `2^d` local assignments. It is not the remaining assignment count. The paper's abstract/discussion contain shorthand that confuses these quantities; use the stated proposition/corollary and independently checked examples rather than copying the shorthand.

Sublinear support alone does not guarantee practical computation: `2^sqrt(n)` is still rapidly growing. Record actual support and resource limits. Do not infer a general tractability theorem from the ambient size alone. For strict majority, use `floor(d/2)+1`; `ceil(d/2)` includes ties at even arity. The paper's general majority sentence and its strict four-input example need this distinction. Treat these as implementation cross-checks; do not modify the original manuscript in this assignment.

The paper's fractional analytic description scores are not automatically complete executable code lengths. The new experiment must serialize every required connection, ordering, rule, parameter and dependency. Do not transfer a numerical compression ratio from an incompletely charged descriptor into a Kolmogorov-complexity claim. Likewise, small-sample output agreement is corroboration rather than a proof for every input.

## Description length, complexity and probability

For a complete self-delimiting executable description `p` of object `x`, on a fixed universal prefix machine U, `K_U(x) <= |p|`. Our encoder supplies a computable upper bound after interpreter/decoder and auxiliary information are accounted for. It need not be close to the unknown minimum. Two upper bounds do not order the true complexities.

Universal algorithmic probability is `m_U(x) = sum_{p:U(p)=x} 2^(-|p|)`. A particular valid program contributes a lower bound to this sum; a finite sum of discovered programs is also a lower bound. The coding theorem connects `-log2 m_U(x)` to prefix complexity up to a constant. A normalized finite codec prior is not thereby a measured universal probability or a bound on real-world frequencies. Reference: [Hutter, Legg and Vitányi, Algorithmic Probability](https://www.hutter1.net/ai/algprob.pdf).

If tested, name our prediction rule **codec-induced model averaging**:

```text
w_L(M | D) = 2^(-L(M)) / sum_{M' in V(D)} 2^(-L(M'))
P_L(q | D) = sum_{M in V(D)} w_L(M | D) * indicator[M satisfies q]
```

Here H is a declared finite model class, V(D) is its evidence-compatible subset, and L is a fixed fully specified code for a canonical mechanism. This is a testable preference over models, not a guarantee that simpler models are true. Never remove positive-weight alternatives from logical verification merely because their weight is small. Empty V is an inconsistency/model-class diagnostic, not a posterior.

A bounded **offline secondary** can compare uniform model averaging, codec-induced averaging, and shortest-model selection on the same new small-world development cases. Keep the primary S4 comparison unchanged. Use one canonical description per distinct mechanism unless a separate program-mixture experiment explicitly defines multiple descriptions and their weights. Do not optimize temperature or language after observing held-out outcomes. No numerical prior is required for proof checking, and this secondary must not delay the core implementation if exact sums are infeasible.

## New operational emphasis: check before release

The AI first proposes a structured claim or a simulated action with an explicit postcondition. Before that proposal is released as verified or executed in the simulator, the checking layer returns one of:

| Status | Required meaning |
|---|---|
| Verified under assumptions | The stated conclusion holds under the declared model/evidence, quantified states and horizon, with the required independently checked evidence. |
| Refuted | A replayable counterexample violates the stated claim. |
| Underdetermined | Compatible possibilities disagree; return opposing witnesses where supported. |
| Inconsistent assumptions | No mechanism satisfies the evidence/declared class; do not exploit vacuous truth to approve claims. |
| Unsupported/resource limit | The requested semantics are unsupported or the check did not finish. This is not a proof and is distinct from epistemic underdetermination. |

The interface is domain-neutral, but the first implementation remains finite and explicitly scoped. At minimum implement `propose`, `check`, `counterexample`, `revise` and a simulated `commit` gate. A proof-required commit is allowed only for a verified result bound to the exact current proposal and assumptions. Forecasts can still be displayed as forecasts; they must not acquire a verification badge because their estimated probability is high.

Keep `proposal_check_status` separate from the target's `epistemic_verdict`. A counterexample to the AI's assertion that q is certain disproves that assertion; it does not establish that q is false in every compatible model. If compatible models support both q and not-q, the target remains underdetermined. Reserve the S4 target verdict 'refuted' for the declared semantics in which every compatible model makes q false. This distinction also applies when an unsafe counterexample blocks an action without proving that the action fails in every case.

Each decision records model/H identity, evidence hash, formal claim, quantifier, variable mapping, update semantics, horizon, assumptions, backend, proof/witness reference and verification level. Bind the proof to the proposed action when applicable. A changed claim, evidence, model, ordering or horizon invalidates the old authorization. The checker is separate from the model's self-critique. Do not accept a fluent explanation as a certificate.

The full system can still fail if a natural-language claim is translated incorrectly or if the model omits a relevant part of the real world. Start with structured proposals whose semantics are independently checkable. In an optional natural-language adapter, log both texts and the mapping, and score translation failures separately. The correct claim is **proof of this formal conclusion under these assumptions**, not proof that an LLM is globally correct.

### Known and unknown mechanisms

- **Known-mechanism checking:** the same declared rules are public to every arm; inputs or consequences are unseen by the AI. This directly uses the formal paper. Include a small offline regression/demo panel with parity, thresholds, mixed gates and overlapping supports. No claim of discovering a hidden mechanism follows from success here.
- **Incomplete-evidence inference:** the actual mechanism remains hidden; the workspace contains V(D). Verify only conclusions shared by all compatible models, and separate these from weighted predictions. This remains the main S4-A evaluation.
- **Active investigation:** when models disagree, select a permitted measurement and update V(D). This remains S4-B, with all observation costs charged.

The first route can deliver a useful verification prototype even before the harder unknown-mechanism hierarchy scales. It must not replace or be pooled with the primary inference study to improve the headline score.

## Evaluate prevention without hiding costs

Reuse the existing S4 development pilot and call budget. Obtain a common initial proposal batch from the unaided model before feedback, persist it, and replay the same proposals through B/C/D checkers. The initial batch can be the first turn of arm A; budget it explicitly so no extra panel is required. All checkers receive the same public evidence and proposal. Separate common-proposal checking results from independently interacting end-to-end arm results.

Add these secondary measures, clustered by world:

- Number and fraction of wrong proposed conclusions that are blocked or corrected before release.
- Wrong conclusions accepted as verified, with denominators and confidence intervals; zero observed errors is not a zero-risk guarantee.
- Correct proposals unnecessarily blocked, and correct verified release coverage over all scheduled items.
- Successful revisions, total time/tokens/tool calls, and resource refusals.
- For an action demonstration, postcondition violations in the simulator before/after checking, using a fixed action set and matched evidence.

Use natural model errors for the main prevention description. Add a separate fixed adversarial fixture set: wrong quantifier, off-by-one state index, stale proof, order mismatch, wrong horizon, noncausal correlation-based claim, empty V, and proof-looking invalid text. These fixtures verify the gate; they are not a representative estimate of LLM error frequency. Report label imbalance and all denominators. A checker that blocks everything must score poorly on valid release coverage.

## Attribution and scope discipline

An analytic parity operator can help for reasons unrelated to hierarchical sharing. Therefore D-minus-C now measures the contribution of the fuller symbolic representation, not hierarchy alone. Require no-hierarchy and no-analytic-shortcut ablations in the offline replay when supported, keeping semantics fixed. Give the generic comparator competent gate/parity/cardinality encodings and the same verification API. If all methods can check the same claims correctly, isolate construction/query/communication cost rather than claim different logical truths.

Keep the S4-A primary, eight strata, proposed main allocation, two-model multiplicity and pilot ceilings in the existing plan. Add the foundation mapping, checking layer, offline known-rule panel and secondary prevention metrics within P1–P5. Do not add a separate large study, weight-training project, generalized theorem prover or real-world deployment.

Suggested paper framing: **Algorithmic models for verifiable AI reasoning: checking unseen claims with causal index-set representations**. The funding case is a testable infrastructure capability: compressed mechanistic models can support checks before an AI's conclusions or actions are relied upon. Method-specific advantage, wider applicability and real-world benefit remain empirical questions.
