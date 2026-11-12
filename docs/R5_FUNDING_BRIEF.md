# CausalGuard — R5 funding brief (development evidence; two pages)

## What exists now

A reproducible, public research system that, for a declared class of mechanisms (synchronous Boolean networks with
≤ k inputs per node) and incomplete one-step evidence:

1. computes **exact** counts of all compatible mechanisms and exact probabilities of unseen outcomes (h ≤ 2), with
   witnesses, a SAT cross-check and optional independently checked RUP refutations;
2. forecasts unseen outcomes by **exact averaging under declared description-length priors** (ours: CGH; generic:
   gate, circuit, shared-rule programs);
3. chooses **informative measurements** exactly (expected information gain) and checks every definite claim
   before release;
4. exposes **when a verified claim depends on the declared class**, and a public challenge policy that buys
   falsification tests before trusting it.

## What R5 demonstrated (development, our generators unless stated; intervals 95 %)

| Question | Result |
|---|---|
| Does weighting compatible mechanisms by a description length beat uniform averaging on held-out structure? | **Yes.** Full CGH − uniform: −0.017 Brier [−0.023, −0.011] (320 synthetic worlds); −0.043 [−0.048, −0.037] on 40 published-model source groups (transformed subnetworks). |
| Does OUR hierarchical prior beat the best generic codec chosen on calibration? | **No detected advantage.** gate − CGH +0.0020 [−0.0041, 0.0082]; external +0.0013 [−0.0025, 0.0048]. The hierarchy adds ≈ 0 outside generator-matched families. |
| Does an AI improve investigation over the exact controller? | **No — it degrades it.** Resolved@4: −0.11 (Mistral 24B), −0.34 (Qwen 7B); premature stopping and (Qwen) unsupported certainty, all blocked by the gate. |
| Can verified claims be false in the world? | **Yes, by construction and in stress tests**: 10 of 103 verified releases false under evidence-consistent misspecification; a public challenge policy halves this at modest coverage cost and no loss on realizable worlds. |
| Is our exact counting computationally distinctive? | **Not against a competent counter.** An independent generic counter matches it exactly (640 comparisons, 0 mismatches) and is 4–11× faster at n = 32–64 (k = 3). It does beat generic SAT (n = 64: 128/128 vs 99/128 queries within 300 s; SAT gives no counts above n = 10). Knowledge-compiler comparison incomplete (tool not authorized). |

## Independent value even where our method did not win

- An **exact, auditable inference layer** (counts, probabilities, certificates, refusals) that any AI or analyst can
  call, and that outperformed both local LLMs as an investigator.
- A **measured failure mode**: false assurance under wrong assumptions, with a cheap public mitigation and its
  tradeoff quantified.
- Negative results that redirect effort: the hierarchy prior's earlier gains were generator-matched; AI-led
  investigation is not the right role for current local models.

## Open risks

Synthetic and transformed-published populations only; small n; k = 3; one-step evidence; h ≤ 2. No independent
review of R5 yet. No claim about universal priors, Kolmogorov complexity or real biological systems.

## Next milestone (costed; one main study, to be authorized independently)

**Assumption-aware verified inference on externally authored systems.** Preregister a study on intact published
models (wider class, k ≤ 4, multi-step evidence support) comparing: current gate, challenge policy, and an improved
public falsification policy, at matched coverage; primary = false-verified rate at fixed correct coverage.
Includes: a knowledge-compiler comparator (ganak/d4) on an authorized machine; independent review before the run.
Cost: ~3 person-weeks engineering, ≤ 100 CPU-hours, no paid inference. **Negative path:** if the improved policy
does not beat the challenge baseline at matched coverage, publish the tradeoff curves and the counterexample
catalogue as a benchmark for assumption-robust verification.
