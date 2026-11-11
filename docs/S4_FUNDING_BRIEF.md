# CausalGuard: algorithmic models for verifiable AI reasoning (funding brief)

Development brief, iteration 4, 2026-11-11. Everything here is **pre-sprint development evidence**; the sprint
runs 2026-11-13 to 11-15. No confirmatory study has been run. Established results are kept apart from
hypotheses throughout. Detailed numbers: `reports/S4_DEVELOPMENT_REPORT.md`.

## The problem

AI systems now state conclusions about systems they cannot fully observe: circuits, biological pathways,
software, plants. Two failures matter most:

- **stating a guess as a certainty**;
- **not knowing which experiment would settle the question.**

A fluent explanation is not a check. Today's solver-assisted LLM pipelines (Logic-LM, SatLM) can prove
consequences of a stated formalization. They do not, by themselves, keep an explicit account of *all*
mechanisms compatible with incomplete evidence, separate "proved under these assumptions" from "likely", and
refuse to release the rest.

## What we built (established, tested, public)

1. **Check before release** (`src/causalguard/s4/checking.py`). An AI proposes a structured claim. Before
   release, a checker returns one of five statuses:
   - verified under the declared assumptions;
   - refuted, with a replayable counterexample;
   - underdetermined, with opposing mechanisms;
   - inconsistent assumptions;
   - unsupported / resource limit.

   Decisions are sealed and bound to the exact claim, evidence, model class, ordering and horizon. Edited,
   stale, forged or proof-looking-text "certificates" are refused. Forecasts are never badged as verified.
2. **A complete, compact account of possibilities** (`s4/mechspace.py`). Given one-step observations, every
   compatible mechanism of a bounded class is represented exactly, without enumeration. The representation is
   the index-set idea applied to mechanisms: per-support schemas over local truth tables, with distinct
   mechanisms counted by Möbius inversion. Exact claim counts and witnesses are support-local, porting the
   formal paper's support-locality result to unknown mechanisms. It agrees exactly with explicit enumeration
   and with brute force over every 2-node network.
3. **A fully charged hierarchical mechanism code** (`s4/hcode.py`, CGH-1). It combines the formal paper's
   analytic vocabulary (parity, thresholds, canalizing rules) with HID-style ordered templates, modules, shared
   rules and patches. Every bit is serialized. It gives upper bounds on description length in one language,
   never Kolmogorov complexity.
4. **Experiment selection** by exact expected information over the compatible set (S4-B prototype).
5. A reproducible demo (`python -m causalguard s4-demo`). An AI's conclusions are blocked before release; the
   uncertainty of one claim is inspected; the most informative permitted experiment is bought; the claim becomes
   verified and is released; a stale decision is refused; the hidden mechanism is revealed only at the end.

## What the evidence shows so far (development; with uncertainty)

- **Correctness.** Our representation, a generic SAT encoding and the flat index workspace give identical
  verdicts: 5,120/5,120 replayed claims, 100/100 stress claims. This is a requirement, not an advantage.
- **Scale (cost, not truth).** On bounded networks with k = 3, h ≤ 2 claims and a 300 s cap:
  - our representation answers every claim up to n = 64 (median 24.6 s per 4 claims), with exact counts;
  - a *competently encoded* generic SAT baseline answers verdicts up to n = 48 (116.5 s vs our 12.8 s), but
    has no exact counts above n = 10 and misses 2 of 3 items at n = 64.

  An earlier, weaker baseline encoding made our advantage look much larger. That comparison was withdrawn
  (DECISIONS D49).
- **Less evidence via a structured prior (secondary; offline).** On claims that remain underdetermined, the
  hierarchical code's model averaging forecasts the hidden outcome better than uniform averaging: +8.9 points
  [95% CI +6.4, +11.5] at 12 observations, and +10.2 [+7.5, +12.9] at 16 (160 worlds).
  - The **hierarchy-specific** part, +4.9 [+3.6, +6.3] at 12 observations, comes **entirely** from the two
    families built with ordered/shared structure (+14 to +21 points there). It is 0 in the other six, including
    an order-disrupted control and a uniform-class null.
  - The analytic vocabulary's gain on parity is matched by a generic circuit code.
  - The honest reading: *if* a system has ordered or shared structure, our prior exploits it from fewer
    observations. Whether real systems do is the next empirical question.
- **Experiment choice.** Exact information-guided selection resolves +7.5 points more initially-underdetermined
  claims than random selection [+2.5, +12.5], 40 worlds. It makes identical choices with every backend: the
  gain comes from reasoning over possibilities, not from our encoding.
- **AI pilot** (two local models × 40 worlds, 888 of 2,560 permitted calls):
  - **System benefit:** with any exact tool, verdict accuracy rises from 0.64–0.65 (the unaided models answer
    "underdetermined" ~99% of the time) to 1.00. That is +35 to +36 points, CIs [+27, +43] and [+28, +45].
  - **Gate:** it blocked all 228 wrong unaided proposals before release, verified none wrongly, and blocked no
    correct one.
  - **Representation:** our tool ties the generic SAT tool exactly (D − B = 0.000), as predicted. The models
    did not exploit the exact probabilities offered to them; a no-LLM controller forecast underdetermined
    outcomes better (0.78 vs 0.54–0.59).
- **Prior negative results stay published.** Selecting the single shortest flat-index model (S2) did not beat
  compatible-set majority (+0.09 points, CI [−1.1, +1.2]). The S3 transfer study was negative.

## What is genuinely ours, and what is not

- **Ours:**
  - the representation of all compatible mechanisms as index-set schemas with exact distinct counting;
  - support-local exact claim evaluation over unknown mechanisms;
  - the fully charged hierarchical code and its exact codec-induced averaging;
  - the release gate integrating them.
- **Not ours, and acknowledged:**
  - SAT/UNSAT checking (generic);
  - solver-augmented LLMs (Logic-LM, SatLM);
  - knowledge-compilation trade-offs (Darwiche & Marquis);
  - algorithmic causal deconvolution (Zenil et al.). We claim no superiority to Zenil's method; no matched
    comparison exists.

## Proposed next milestone (requires review and funding)

1. **Scoped main study:** two local models, 320 worlds per model (prospectively adjustable up to 800 from the
   sizing study). Because exact tools tie, the primary endpoint should be re-decided by the reviewer:
   (a) accuracy at sizes where generic tools hit declared resource caps, (b) cost at equal accuracy, or
   (c) the forecast endpoint where the representation actually changes answers.
2. **Beyond one-step evidence:** multi-step observations, where the product factorization fails and
   hierarchical sharing could matter for inference rather than only for the prior.
3. **Noisy and misspecified evidence:** proofs are model-relative. In a first diagnostic, 26 of 40 out-of-class
   worlds were exposed as inconsistent by the evidence itself, and 21 verified conclusions held. This small
   sample establishes no robustness.
4. **A real diagnostic workflow:** for example, digital-circuit fault localization, with a fixed action set.

## Resource request (indicative)

- Main study as proposed: about 2 × 320 × 25 ≈ 16,000 local model calls at most. At the measured pilot pace
  this is roughly 4–10 GPU-days on one workstation-class machine, with no paid inference. See
  `reports/S4_DESIGN_SIZING.md`.
- One researcher for 3 months: main study, multi-step extension, and a case study.
- Funding and acceptance are goals, not promised outcomes.
