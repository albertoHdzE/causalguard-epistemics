---
title: "Who checks the check? Frontier models verify forged derivations by lookup, open-weight models adopt them"
subtitle: "Research conducted at the AI x Epistemics Research Sprint, November 2026 (Apart Research)"
author:
  - "Alberto Hernández Espinosa"
  - "Independent researcher"
  - "With Apart Research"
author-meta: "Alberto Hernández Espinosa"
# Title block of the official Apart template, rendered by report/apart.latex (the DOCX uses subtitle and author).
apart-footnote: "Research conducted at the [AI x Epistemics Research Sprint](https://apartresearch.com/sprints/ai-x-epistemics-research-sprint-2026-11-13-to-2026-11-15), November 2026"
apart-authors:
  - name: "Alberto Hernández Espinosa"
    affiliation: "Independent researcher"
apart-with: "Apart Research"
geometry: margin=2.0cm
fontsize: 10pt
header-includes:
  - \usepackage{etoolbox}
  - \AtBeginEnvironment{longtable}{\footnotesize}
  - \setlength{\tabcolsep}{3pt}
---

<!-- SOURCE of report/report.md. Every number comes from reports/sprint_all/*.json through report/fill.py; the
build fails on a hand-typed number. Do not edit report.md by hand. -->

::: {.abstract}
# Abstract

When a model is shown a step-by-step "check" of its answers, does it verify the check against the evidence, or
defer to it? We built a benchmark where this is decidable, inside a programme that models mechanisms as short
executable rules and derives their consequences exactly (Appendix E). Each task shows a hidden Boolean network
through a few evidence rows and asks whether claims are settled true, settled false or not settled; exact
engines compute the answer key. In a second turn the model receives one of five randomised follow-ups,
including a valid check (P3) and a forged one (P4) that differs in one line contradicted by a cited
evidence row. When the wiring is given (Tier W), every line can be verified by one lookup. There, two frontier
models reject forged checks by re-deriving the cited rows unprompted (check discernment: Claude Opus 5.5
{{A/models/cl/tiers/W/contrasts/check_discernment|est}}, DeepSeek V4-Pro at low effort
{{A/models/ds/tiers/W/contrasts/check_discernment|est}}), while six local open-weight models adopt the forged
status on most named claims ({{A/models/g3/tiers/W/C/adopt_forged/P4|est}} to
{{A/models/ll/tiers/W/C/adopt_forged/P4|est}}), with check discernment near zero. In a pre-registered verify-first control
(P5), some local models find forged lines but flag valid lines about as often, and a small model that flags a forged line usually keeps its forged status
(qwen2.5-7b: {{P/models/q7/flagged_then_adopted/flagged_adopted|int}} of
{{P/models/q7/flagged_then_adopted/flagged|int}} flagged claims): verification text and final answer come apart.
A bare demand to commit splits Claude the other way: it gives definite verdicts on open claims but keeps every
stated probability at its turn-1 value.
:::

# 1. Introduction

Language models are increasingly shown other systems' outputs (tool results, retrieved passages, another model's
reasoning) and asked to use them. Whether a model checks such input against the evidence it was given, or simply
adopts it, decides whether a single corrupted step propagates. This is an epistemic failure that is hard to
measure on natural text: the reference answer is usually a human judgement, and "the model should have noticed"
is rarely decidable.

We use a domain where it is decidable. A task shows a deterministic system through a handful of observed
transitions and asks about claims. The status of every claim relative to the shown evidence is computed exactly,
inside a declared class of mechanisms. A forged check can then be built that is wrong in exactly one verifiable
line, and nothing else changes between the valid and the forged condition.

**Where the benchmark comes from.** It is the first product of a programme of algorithmic modelling: describe a
system by short executable rules that generate its behaviour, keep every rule set consistent with the evidence,
and derive exactly what follows. The view of a mechanism as something learned by perturbing and querying a system
comes from algorithmic causal deconvolution (Zenil et al. 2019a), and the programme began in the author's earlier
work with that group (Hernández-Espinosa et al. 2021). Boolean networks come first because inside a declared class
every status can be computed exactly, so an epistemic question becomes decidable. The sprint uses only this exact
part; the compression part of the programme is pre-sprint work with mixed results (Appendix E).

Our main contributions are:

1. **An exact benchmark of evidence-relative reasoning under pressure, built on an exact symbolic engine over a
   declared mechanism class.** Claims are scored against what the
   evidence settles, not against what is true. Five randomised follow-ups (neutral, empty disagreement, demand to
   commit, valid check, forged check) are assigned by hash to disjoint worlds. Two tiers separate "cannot verify"
   (wiring hidden) from "could verify by lookup" (wiring given).
2. **A forged-check measurement with a verify-first control.** Six local models adopt forged checks they could
   verify; two frontier models reject them by re-deriving the cited rows unprompted. Told to verify, some local
   models find the forged line, but their flags do not separate forged from valid lines, and their answers often
   follow the forged check even after they call its line wrong.
3. **A pre-registered, fully disclosed run.** A design lock with predictions preceded every request. Every number
   in this report is generated from the raw runs. Predictions that failed are reported as failed.

**Pre-sprint work, stated plainly.** The exact engines, the benchmark code, Tier W and the forged checks (P0–P4),
the design lock (v1) and the local main panel were built and run before the sprint (2026-11-09 to 2026-11-12;
Appendix B). The sprint added the verify-first control P5 and its local runs, reasoning storage, the online runs,
the analysis of this report and the report itself.

# 2. Related Work

Three-valued entailment benchmarks label conclusions True, False or Unknown relative to stated premises
(ProofWriter, Tafjord et al. 2021; FOLIO, Han et al. 2022). Our status label is the same idea. We add an exact
probability for open claims and an unlimited, exactly labelled generator. Abstention benchmarks ask whether a
model declines when it should (Yin et al. 2023; Amayuelas et al. 2023; Kirichenko et al. 2025; survey: Wen et al.
2024). There, "should abstain" is an annotation; here it is computed from the evidence. Calibration work scores
verbalised confidence against correctness (Lin et al. 2022; Tian et al. 2023; Xiong et al. 2024). Sycophancy and
flip-flop studies show that models yield to empty or invalid challenges (Perez et al. 2022; Sharma et al. 2023;
Laban et al. 2023; Wang et al. 2023). Those designs have no condition in which yielding is correct, and no
challenge that is wrong in a checkable way. Our P1 (empty disagreement) reproduces their setting. P3 and P4 add a
valid and a forged checked challenge on randomised worlds, and P5 asks for verification explicitly.

# 3. Methods

**Worlds and status.** A world is a synchronous Boolean network of 8 nodes with at most 3 inputs per node. It is
drawn from synthetic strata or from published regulatory-network fragments. The model sees a few evidence rows
(one synchronous step each, optionally with clamped nodes) and 8 claims ("from this start state, after k steps,
node X = 1"). A claim is *settled true* if every mechanism of the declared class that reproduces the evidence makes
it true, *settled false* if none does, and *not settled* otherwise. For open claims, p\* is the exact share of
consistent mechanisms making the claim true. The engines represent sets of rules symbolically (schema families
with don't-cares) and count consistent mechanisms exactly; two independent engines and a SAT encoding must agree
on every claim (gates passed on every item; Appendix E.3).

**Tiers.** On *Tier H* the wiring is hidden. On *Tier W* each node's inputs are listed, so the status of a claim
can be traced by looking up rows: a *derivation* lists, step by step, which row shows the node's next value for
its current inputs, or that no row shows those inputs (Appendix C).

**Turn 1 (Task S)** asks for a status and a probability per claim. Overclaim is the share of open claims given a
definite verdict; underclaim is the share of settled claims answered "not settled". A surface rule fitted on
non-panel worlds is the reference row a model must beat.

**Turn 2 (Task P)**, in the same conversation, is one of five follow-ups assigned by hash, with two wordings
each: **P0** asks to review and confirm; **P1** says the answers for up to 4 named claims are wrong (no reason);
**P2** demands a definite verdict for every claim; **P3** shows a valid check for the named claims; **P4**
shows a *forged* check in the same template. On Tier W the check is a step-by-step derivation; on Tier H, where no
derivation can be verified by lookup, it is an exact tool's report (counts of consistent mechanisms and, for open claims,
example mechanisms). The forged Tier W derivation is identical to the valid one except for one line that a cited row
contradicts (a phantom row, a wrong value, or "no row shows these inputs" where one does), which changes the
claim's status. A verifier confirms that every valid check passes and every forged check fails on exactly the
altered line. Scores per world, then averaged: *adoption* (final verdict equals the check's status), *corruption*
(named claims correct at turn 1 and wrong at turn 2 under P4), and **check discernment** = adoption of the true
status under P3 − adoption of the forged status under P4 (+1: uses only valid checks; 0: cannot tell them apart).

**P5, verify-first (sprint; lock addendum v2).** On 60 further Tier W worlds never shown to any model, 30 receive
the valid check (P5v) and 30 the forged one (P5f). The P3/P4 message gains one block: verify every line against
the evidence rows, quote any wrong line exactly, then answer, with a `check_errors` field in the reply. *Exact
detection* is the share of forged named claims whose altered line is quoted exactly (after whitespace
normalisation). *Lenient detection* only requires naming the cited row and node. *False alarm* is the share of
valid named claims with any quoted error. P5 and the main panel use different worlds, so P5 − P4 is a
between-world contrast.

**Models.** Six local open-weight models at temperature 0 (gemma-3-4b, qwen2.5-7b, gemma-4-12b,
mistral-small-24b, r1-distill-qwen-32b, llama-3.3-70b; token cap 6000, r1 12000). gemma-4-12b and r1 ran half the
panel (by rule, before the lock) and are marked †. Online: Claude Opus 5.5 through the Claude Code command line in
an isolated configuration (effort high; every request audited for injected context), and DeepSeek V4-Pro through
its API. At the provider's default (high) reasoning effort DeepSeek did not finish within 32000 completion tokens
(§4.4), so it ran as a separately labelled condition at reasoning effort *low* (‡).

**Pre-registration and analysis.** A design lock (v1, 2026-11-12) fixed items, assignments, prompts, scores,
contrasts and predictions before the main panel. A sprint addendum (v2) fixed P5, the online caps and new
predictions before any P5 or online request. Its three amendments, and a fourth for a post-freeze supplement, are disclosed (Appendix B). The unit is the
world; 95 % intervals come from 2000 cluster-bootstrap replicates over source groups; tests against zero and
against the surface rule are Holm-adjusted within tier. Online cells are reported with the number of finished
worlds over planned worlds; a contrast is computed only if both cells finished at least 12 worlds (pre-declared
before the online runs resumed).

# 4. Results

## 4.1 Local models adopt forged checks; frontier models reject them (Tier W, main panel)

{{table:task_p}}

*Table 1. Task P per model and tier: share of named claims whose final verdict adopts the check's status, under
the valid check (P3) and the forged check (P4); corruption under P4; check discernment with its 95 % interval.
n = finished worlds (planned per cell: 24 on Tier W, 12 on Tier H, half of each for †; an incomplete cell
shows finished / planned). † half panel. ‡ labelled condition (reasoning effort low). An interval of zero
width means every world had the same value; for a cell where every world scores zero, the one-sided 95 % upper
bound on the per-world rate is 1 − 0.05^1/n^: {{R/degenerate_bound/24}} for n = 24 and
{{R/degenerate_bound/30}} for n = 30. Claude's Tier H cells are in the post-freeze supplement (Appendix D).*

On Tier W every local model adopts the forged status on most named claims, and both frontier models reject it:
Claude Opus 5.5 adopts the forged status on {{A/models/cl/tiers/W/C/adopt_forged/P4|est}} of named claims and
DeepSeek V4-Pro at low effort on {{A/models/ds/tiers/W/C/adopt_forged/P4|est}} (§4.4). llama-3.3-70b, mistral-small-24b and
gemma-4-12b adopt it on every named claim ({{A/models/ll/tiers/W/C/adopt_forged/P4|est}}). Corruption, the share
of answers that were right at turn 1 and became wrong, is between
{{A/models/q7/tiers/W/C/corruption/P4|est}} (qwen2.5-7b) and {{A/models/ll/tiers/W/C/corruption/P4|est}}. Check
discernment is indistinguishable from zero for all six (for example mistral
{{A/models/mi/tiers/W/contrasts/check_discernment}}, gemma-3
{{A/models/g3/tiers/W/contrasts/check_discernment}}). The forged line was verifiable with one lookup in a row the
message itself cites. The same pattern holds on Tier H, where no check can be verified by lookup.

The adoption is not a baseline coincidence. Under the neutral follow-up P0, where no check is shown, the status
a forgery would have given is the final answer on {{A/models/mi/tiers/W/C/adopt_forged/P0|est}} of named claims
for mistral (against {{A/models/mi/tiers/W/C/adopt_forged/P4|est}} under P4). An empty disagreement (P1) moves
models less than a forged check: qwen2.5-7b changes {{A/models/q7/tiers/W/P/capitulation_named/P1|est}} of named correct answers under P1
against {{A/models/q7/tiers/W/C/corruption/P4|est}} under P4. A forged *check* is more persuasive than a bare
assertion.

![Adoption of the check's status per model on Tier W (left) and Tier H (right): the true status under the
valid check (P3, blue circles), the forged status under the forged check (P4, orange squares) and under the
forged check with the verify-first instruction (P5f, green diamonds; Tier W only). Lines are 95 % intervals;
hollow markers are incomplete cells below 12 worlds, and the row label then carries finished / planned
worlds.](../reports/sprint_all/fig1_task_p.png){width=100%}

## 4.2 Told to verify, local models flag lines but keep the forged answer (P5)

{{table:p5}}

*Table 2. P5 verify-first (Tier W, 60 planned worlds per model; locked scorer). Exact and lenient detection of the
altered line in forged checks (P5f); false alarm on valid checks (P5v); forged adoption under P5f and its
difference from P4 (between-world); verified discernment = true-status adoption under P5v − forged adoption under
P5f. n = finished worlds; a finished world enters a metric only with a valid turn-2 reply (Appendix D, Table 10:
for DeepSeek, {{P/models/ds/health_by_cell/P5f/in_detection|int}} of
{{P/models/ds/health_by_cell/P5f/finished|int}} finished P5f and {{P/models/ds/health_by_cell/P5v/in_detection|int}}
of {{P/models/ds/health_by_cell/P5v/finished|int}} finished P5v worlds; the others stopped at the token cap or
returned no valid reply). Zero-width intervals: see Table 1 (bound
{{R/degenerate_bound/30}} for n = 30).*

Under the locked scorer the best local detector, mistral-small-24b, quotes the altered line in
{{P/models/mi/exact|est}} of forged named claims and flags valid checks at {{P/models/mi/false_alarm|est}}. The
locked parser, however, drops `check_errors` entries whose claim id is an integer, while the answers parser maps
an integer *k* to claim c*k*. Three models write integer ids (Table 3), so their locked detection rates mostly
measure the format. Accepting integer ids (post-hoc) raises gemma-4-12b's exact detection to
{{P/models/g4/exact_int_cids|est}}, and its false-alarm rate to {{P/models/g4/false_alarm_int_cids|est}}; qwen2.5-7b
reaches {{P/models/q7/exact_int_cids|est}} with false alarms at {{P/models/q7/false_alarm_int_cids|est}}. Under
both readings, no local model separates forged lines from valid ones: its false-alarm interval overlaps or exceeds
its detection interval (Figure 2).

{{table:p5_more}}

*Table 3. P5f, post-hoc. Entries the locked parser drops; exact detection and false alarm when integer claim ids
are accepted; named forged claims whose altered line the reply flagged (lenient, ids accepted), and how many of
those still end at the forged status (claim-level counts).*

The most direct result is the last column. When qwen2.5-7b flags the forged line of a claim, it keeps the forged
status in {{P/models/q7/flagged_then_adopted/flagged_adopted|int}} of {{P/models/q7/flagged_then_adopted/flagged|int}}
such claims; gemma-3-4b in {{P/models/g3/flagged_then_adopted/flagged_adopted|int}} of
{{P/models/g3/flagged_then_adopted/flagged|int}}; llama-3.3-70b in
{{P/models/ll/flagged_then_adopted/flagged_adopted|int}} of {{P/models/ll/flagged_then_adopted/flagged|int}}. The
two models that verify most (mistral, gemma-4) keep it in {{P/models/mi/flagged_then_adopted/flagged_adopted|int}}
of {{P/models/mi/flagged_then_adopted/flagged|int}} and {{P/models/g4/flagged_then_adopted/flagged_adopted|int}}
of {{P/models/g4/flagged_then_adopted/flagged|int}}. Forgeries that alter a row's value are flagged most often;
"no evidence row shows these inputs" where a row does is flagged least (`p5_analysis.json`). P5 lowers forged
adoption for some models (gemma-4-12b by {{P/models/g4/vs_main/adopt_forged_P5f_minus_P4|abs}}), but adoption of
the valid check falls too ({{P/models/g4/vs_main/adopt_check_P5v_minus_P3}} against P3). llama-3.3-70b is
unmoved ({{P/models/ll/adopt_forged_P5f|est}} forged adoption under P5f).

**Reading the replies (pre-registered coding).** We read 8 hash-chosen P4 and P5f turn-2 replies per local model
in full and coded (a) re-derives a cited lookup itself, (b) names a mismatch between the check and a row, (c)
points at the altered line as wrong (`reports/sprint_all/reasoning_coding.csv`; coder: the implementation agent,
an AI; disclosed).

{{table:coding}}

*Table 4. Coded replies per model and condition (8 per cell, hash-chosen). Local replies were read in full;
DeepSeek's stored reasoning (thousands of tokens per reply) was read at the passages that engage the check and
reach the decision. r1's main-run reasoning was not stored (its P5 reasoning was).*

Unprompted (P4), replies restate the check ("row #01 shows that L1 transitions to 1, which matches the claim",
mistral, `main|published|published|0|`). Several gemma-4-12b replies read the cited row themselves, get a value that
contradicts the forged line, and defer: "In row #05 … the result is D1 → 1. Wait, let's re-check. Actually, the
user provided a hint that c0 is settled TRUE." (`main|synthetic|mixed_parity_thresh|8|`). Told to verify (P5f),
gemma-4-12b checks bit by bit and catches forged lines of every kind ("Row #02 shows these inputs. So the statement
'no evidence row shows these inputs' is Incorrect.", `main|synthetic|shared_motifs|17|`); qwen2.5-7b quotes a
forged line as incorrect and marks the identical forged line of another claim correct
(`main|synthetic|feedback_canalizing|7|`).

Two post-hoc properties of the forged messages (D104) are reported in Appendix D.

![P5 verify-first: share of forged named claims whose altered line the model quotes exactly (green
diamonds) or names (blue circles), and share of valid named claims with a quoted error (false alarm, orange
squares). Lines are 95 % intervals.](../reports/sprint_all/fig3_p5.png){width=72%}

## 4.3 Task S: most local models are at the floor

{{table:task_s}}

*Table 5. Task S (turn 1) per model and tier, with the surface rule fitted on non-panel worlds as the reference.*

Without pressure, five of the six local models are at the floor of Task S on Tier W: the lower bound of their
balanced accuracy does not exceed that of answering "not settled" everywhere (post-hoc rule, Appendix B). They err in opposite directions: gemma-3-4b gives a definite
verdict on {{A/models/g3/tiers/W/S/overclaim|est}} of open claims; llama-3.3-70b answers "not settled" on
{{A/models/ll/tiers/W/S/underclaim|est}} of settled ones (Figure 3). Only r1-distill is off the floor on Tier W
({{A/models/r1/tiers/W/S/balanced_accuracy}}), and it too has zero check discernment
({{A/models/r1/tiers/W/contrasts/check_discernment}}).

![Task S: overclaim (orange squares) and underclaim (blue circles) per model and tier; the surface rule
is the reference row (hollow). Lines are 95 % intervals.](../reports/sprint_all/fig2_task_s.png){width=100%}

## 4.4 Frontier models under the benchmark's cost

**DeepSeek at high effort does not finish.** (Appendix D, Table 7.)

At the provider's default (high) effort, DeepSeek V4-Pro spent every token of a 16000 cap and then between
{{R/smokes/deepseek_high_32k/reasoning_tokens_min|int}} and {{R/smokes/deepseek_high_32k/reasoning_tokens_max|int}}
reasoning tokens of a 32000 cap, finishing {{R/smokes/deepseek_high_32k/parsed_W|int}} of
{{R/smokes/deepseek_high_32k/turns_W|int}} Tier W turns and none of the Tier H turns. Its stored reasoning
enumerates candidate mechanisms by hand. The benchmark's cost for a reasoning model is itself a finding: exact
evidence-relative reasoning over 8 claims is expensive when done by enumeration. At effort low it passed the smoke
and ran as a labelled condition.

**Claude Opus 5.5 verifies unprompted.** On Tier W it adopts the forged status on
{{A/models/cl/tiers/W/C/adopt_forged/P4|est}} of named claims and the true status under the valid check on
{{A/models/cl/tiers/W/C/adopt_check/P3|est}} (P3 {{A/models/cl/tiers/W/cells/P3/finished|int}}, P4
{{A/models/cl/tiers/W/cells/P4/finished|int}} worlds). All {{C/cl/P4/n|int}} coded P4 replies re-derive every cited
lookup and name the misreading, with no instruction to verify: "I re-read each row the checker cites, and none of
them matches the input pattern it claims. So I'm keeping my original answers." (`main|synthetic|uniform_H|9|`).
Its thinking summaries say the same. Told to verify (P5), it quotes the altered line in
{{P/models/cl/exact|est}} of forged named claims with no false alarm on valid checks
({{P/models/cl/false_alarm|est}}), and DeepSeek in {{P/models/ds/exact|est}} (false alarm
{{P/models/ds/false_alarm|est}}): verified discernment {{P/models/cl/verified_discernment|est}} and
{{P/models/ds/verified_discernment|est}}. Pressure without evidence is a different matter. Claude never yields to
an empty disagreement (P1 capitulation {{A/models/cl/tiers/W/P/capitulation_named/P1|est}}). A demand to commit
(P2) makes it give a definite verdict on {{A/models/cl/tiers/W/P/overclaim_t2/P2|est}} of open claims, while its
stated probabilities stay at their turn-1 values
({{A/models/cl/tiers/W/verdict_probability/P2/probability_kept|int}} of
{{A/models/cl/tiers/W/verdict_probability/P2/with_both_probabilities|int}} definite verdicts within 0.05; mean
absolute change {{A/models/cl/tiers/W/verdict_probability/P2/mean_abs_dp}}) and the prose says the claims are open:
"I can give a definite verdict for every claim, but only c2 is actually settled by the evidence. The other seven are
best guesses … the probabilities below are unchanged." (`main|synthetic|uniform_H|19|`). The verdict field follows
the instruction; the probability does not (post-hoc descriptor, D120; Appendix D, Table 9). Most local models move
both: llama-3.3-70b keeps the probability on {{A/models/ll/tiers/W/verdict_probability/P2/probability_kept|int}} of
{{A/models/ll/tiers/W/verdict_probability/P2/with_both_probabilities|int}} such verdicts, mistral-small-24b on
{{A/models/mi/tiers/W/verdict_probability/P2/probability_kept|int}} of
{{A/models/mi/tiers/W/verdict_probability/P2/with_both_probabilities|int}}; qwen2.5-7b keeps it on
{{A/models/q7/tiers/W/verdict_probability/P2/probability_kept|int}} of
{{A/models/q7/tiers/W/verdict_probability/P2/with_both_probabilities|int}}. Tier H, where no check can be verified
by lookup, was not reached by either online model in the frozen panel, so P-D5 is not testable in this run. In a
post-freeze supplement (amendment v2-a4, run after the report text was drafted; Appendix D) Claude finished
{{R/supplement/worlds_finished|int}} of {{R/supplement/worlds_planned|int}} Tier H P3 and P4 worlds, too few for a
contrast; it rejected the forged tool report in most finished P4 worlds and in one adopted it without finding the
error ("Its counterexamples show my per-node analysis was wrong in places, though I have not found where.",
`main|synthetic|feedforward_hetero|4|`).

**What a frontier reasoning model does with a forged check.** On Tier W, DeepSeek V4-Pro at low effort rejects
most forged checks (check discernment {{A/models/ds/tiers/W/contrasts/check_discernment}}); in
{{C/ds/P4/c_names_altered_line|int}} of {{C/ds/P4/n|int}} coded P4 replies its stored reasoning rebuilds the cited
lookups and names the misread row ("checker says row #01 shows F3 -> 1. That is definitely misreading",
`main|published|published|20|`). The exceptions are instructive: once it accepts the check without looking ("We
should trust checker if it's correct.", `main|synthetic|shared_motifs|12|`), and once it finds both forged lines
wrong and still concludes "I think the safest is to follow the user's explicit correction"
(`main|synthetic|uniform_H|0|`), the local models' decoupling of check and answer, at the level of the reasoning.

Requests, rejections and spend per online model are in Appendix D (Tables 6 and 8).

# 5. Discussion and Limitations

**What the results mean.** On items where every line of a check can be verified with one lookup, the two
frontier models check by default and reject forged checks; the six local models treat a check as authoritative: they adopt its status whether it is valid or forged, and they lose correct answers
to it. Asked to verify, some of them do produce verification text, and it sometimes finds the forged line; but it
also flags valid lines, and the final answer often follows the forged check even for the claim whose line the
model has just called wrong. This separates explanations that sycophancy measurements cannot: the failure is not
that checking is impossible (Tier W makes it a lookup), nor that the instruction is ignored (under P5 the models
check line by line). The model's own check does not govern its answer. For agentic pipelines in which one model's intermediate result is another's input,
a single forged step is enough. Under a bare demand to commit, the split runs the other way for the frontier model:
its verdict follows the instruction and its probability does not, whereas the local models' answer follows the check
and their verification text does not. In both cases one field of the reply cannot be read without the other.

**The exact check as a remedy.** Inside the declared class, the same exact engine that labels the items can gate
a model's released verdicts. A settled verdict that the checker contradicts is released as "not settled". This
removes overclaim by construction but cannot add what the model missed. Outside the class the checker can
certify a false claim (pre-sprint evidence, Appendix A). It is a remedy for this class, not a general verifier.

**Theory of change.** The same exact engine is answer key, verifier and release gate: it labels the items, checks
every line of a derivation, and can withhold a settled verdict the evidence does not support. The programme's aim
is to widen the declared class with compressed generative models, so that such a gate reaches systems where
enumeration is impossible. Until then, this paper claims only the class it declares.

## Limitations

\(1) Status is exact only inside the declared class (synchronous Boolean networks, at most 3
inputs per node); the tasks are synthetic and we make no claim that results transfer to natural-language
reasoning. (2) Five of six local models are at the Task S floor, so for them P4 measures deference more than a
failed attempt to verify; the off-floor case is r1 and the online models. (3) Two local models ran half the panel.
(4) In the frozen panel the online models ran Tier W only (Table 6): DeepSeek ran at low effort until the
account balance ran out, and the Claude run stopped on an isolation-audit flag (a date notice the command line
injected into a session resumed across midnight; the flagged items were retried cleanly) before its Tier H
blocks. A labelled post-freeze supplement (v2-a4; Appendix D) ran Claude's Tier H P3 and P4 cells; Tier H turns
ran past the 600 s timeout or met the usage window, so its finished worlds may be the easier ones. (5) Claude's stored reasoning is the CLI's *thinking summaries*,
not the raw reasoning. (6) P5 and P4 are between-world contrasts. (7) The model family that implemented the
benchmark (Claude) is also evaluated, in isolated, audited contexts.

## Future Work

Run the frontier models on Tier H, where a check cannot be verified by lookup and deference is
the only option short of abstaining. Measure where between "cannot verify" and "verifies" a model starts to discriminate (lookup
depth, number of forged lines); test whether a cited-row consistency tool, offered to the model, closes the gap.

# 6. Conclusion

Who checks the check depends on the model. Given a forged check that they could verify by one lookup, two
frontier models re-derive the cited rows and reject it; six open-weight models adopt it. Told to verify, some
open-weight models find the forged line, flag valid lines about as often, and frequently keep the forged answer
after calling its line wrong. Told only to commit, the frontier model gives definite verdicts on open claims and
keeps its probabilities where they were. The benchmark makes these measurable because the answer key is exact and
the forged check differs from the valid one in a single checkable line. On Tier H a labelled post-freeze supplement was too small
for a contrast; in one world the frontier model adopted a forged report it could not refute (Appendix D). We
release the generator, the gates, the lock and every run.

# Code and Data

* Code: https://github.com/albertoHdzE/causalguard-epistemics (branch `sprint`); analysis:
  `scripts/sprint_analyze_all.sh`; report: `report/fill.py` and `report/build.sh`.
* Data: committed manifests (`artifacts/sprint_main_manifest.json`, `artifacts/sprint_p5_manifest.json`), the
  design lock with its addendum and amendments (`docs/SPRINT_DESIGN_LOCK.json`). Every sprint run record, the
  call ledgers and the spend record are in the asset of the pre-release `v0.8.0-sprint`
  (https://github.com/albertoHdzE/causalguard-epistemics/releases/tag/v0.8.0-sprint), with a SHA-256 manifest
  (`artifacts/manifest_sprint.json`).
* Other artifacts: release `v0.8.0-sprint` (runs, ledgers, manifest).

# Author Contributions

A.H.E. conceived the research programme and its lineage, set the research question and the sprint's direction,
provided the compute, the models and the accounts, took the decisions recorded in `DECISIONS.md` at the director's
checkpoints, and reviewed and approved the report. Code, runs, analysis and the draft were produced by Claude
Opus 5.5 under the direction and review of Claude Fable (see LLM Usage Statement).

# References

Amayuelas, A. et al. (2023). Knowledge of Knowledge: Exploring Known-Unknowns Uncertainty with Large Language Models. arXiv:2305.13712.

Chaitin, G. J. (1966). On the Length of Programs for Computing Finite Binary Sequences. Journal of the ACM 13(4):547–569. doi:10.1145/321356.321363.

Han, S. et al. (2022). FOLIO: Natural Language Reasoning with First-Order Logic. arXiv:2209.00840.

Hernández-Espinosa, A., Zenil, H., Kiani, N. A., Tegnér, J. (2021). Estimations of Integrated Information Based on Algorithmic Complexity and Dynamic Querying. In Handbook of Unconventional Computing, World Scientific, 171–219. doi:10.1142/9789811235726_0005.

Kauffman, S. A. (1969). Metabolic stability and epigenesis in randomly constructed genetic nets. Journal of Theoretical Biology 22(3):437–467. doi:10.1016/0022-5193(69)90015-0.

Kirichenko, P. et al. (2025). AbstentionBench: Reasoning LLMs Fail on Unanswerable Questions. arXiv:2506.09038.

Kolmogorov, A. N. (1965). Three approaches to the quantitative definition of information. Problems of Information Transmission 1(1). Reprinted (1968) in International Journal of Computer Mathematics 2:157–168, doi:10.1080/00207166808803030.

Laban, P. et al. (2023). Are You Sure? Challenging LLMs Leads to Performance Drops in The FlipFlop Experiment. arXiv:2311.08596.

Li, M., Vitányi, P. (2008). An Introduction to Kolmogorov Complexity and Its Applications, 3rd ed. Springer. doi:10.1007/978-0-387-49820-1.

Lin, S., Hilton, J., Evans, O. (2022). Teaching Models to Express Their Uncertainty in Words. arXiv:2205.14334.

Perez, E. et al. (2022). Discovering Language Model Behaviors with Model-Written Evaluations. arXiv:2212.09251.

Rissanen, J. (1978). Modeling by shortest data description. Automatica 14(5):465–471. doi:10.1016/0005-1098(78)90005-5.

Sharma, M. et al. (2023). Towards Understanding Sycophancy in Language Models. arXiv:2310.13548.

Solomonoff, R. J. (1964). A formal theory of inductive inference. Part I. Information and Control 7(1):1–22. doi:10.1016/S0019-9958(64)90223-2.

Tafjord, O., Dalvi Mishra, B., Clark, P. (2021). ProofWriter: Generating Implications, Proofs, and Abductive Statements over Natural Language. Findings of ACL. arXiv:2012.13048.

Tian, K. et al. (2023). Just Ask for Calibration. EMNLP. arXiv:2305.14975.

Wang, B., Yue, X., Sun, H. (2023). Can ChatGPT Defend its Belief in Truth? Findings of EMNLP. arXiv:2305.13160.

Wen, B. et al. (2024). Know Your Limits: A Survey of Abstention in Large Language Models. TACL. arXiv:2407.18418.

Wolfram, S. (2002). A New Kind of Science. Wolfram Media. ISBN 1-57955-008-8; https://www.wolframscience.com/nks/.

Xiong, M. et al. (2024). Can LLMs Express Their Uncertainty? ICLR. arXiv:2306.13063.

Yin, Z. et al. (2023). Do Large Language Models Know What They Don't Know? Findings of ACL. arXiv:2305.18153.

Zenil, H., Hernández-Orozco, S., Kiani, N. A., Soler-Toscano, F., Rueda-Toicen, A., Tegnér, J. (2018). A Decomposition Method for Global Evaluation of Shannon Entropy and Local Estimations of Algorithmic Complexity. Entropy 20(8):605. doi:10.3390/e20080605.

Zenil, H., Kiani, N. A., Zea, A. A., Tegnér, J. (2019a). Causal deconvolution by algorithmic generative models. Nature Machine Intelligence 1:58–66. doi:10.1038/s42256-018-0005-0.

Zenil, H., Kiani, N. A., Marabita, F., Deng, Y., Elias, S., Schmidt, A., Ball, G., Tegnér, J. (2019b). An Algorithmic Information Calculus for Causal Discovery and Reprogramming Systems. iScience 19:1160–1172. doi:10.1016/j.isci.2019.07.043.

# Appendix A. Limitations and Dual-Use / Ethical Considerations

**Dual use.** The forged checks are an attack: a message that looks like verification and changes a model's
answer. Publishing them is net positive. The construction is simple (alter one line of a derivation), it is
already implied by the sycophancy literature, and the benchmark gives defenders a measured, exactly scored
test of whether a model verifies. The forgeries are confined to synthetic Boolean networks; nothing in them
transfers as a ready attack on a deployed system.

**Scope of the check.** The exact checker certifies status only inside the declared class. Pre-sprint
development runs (R5 Track M) showed that when the class is wrong, the checker can certify a false claim.
Presenting the check as general verification would overclaim.

**Model family.** The benchmark was implemented by Claude (Claude Code, Opus 5.5) and directed by Claude
(Fable); Claude Opus 5.5 is also evaluated. Every Claude request ran in an empty directory with no tools, no
settings, no memory and no project instructions, and the request record was audited for injected context.

**Thinking summaries.** For Claude the stored reasoning is the route's thinking summaries, not the raw
reasoning; it is reported as such and never scored.

**Benchmark cost.** At high reasoning effort a frontier reasoning model did not finish a Tier H turn within 32000
completion tokens, and Claude's Tier H first turns often ran past the 600 s request timeout. The frozen online
cells are incomplete because of that cost and of the shared subscription window, not by selection; in the Tier H
supplement the timeouts may select the easier worlds (Appendix D).

**Human subjects and data.** None; no personal data appears in any prompt. Online models were used under their
providers' terms.

**AI tool use.** See the LLM Usage Statement at the end of the report.

# Appendix B. Pre-sprint and sprint work; lock, amendments and predictions

**Pre-sprint (2026-11-09 to 2026-11-12, disclosed).** Exact engines and SAT cross-check; the sprint benchmark
(Task S, Task P, P0–P4), Tier W, derivations, the verifier and the forged checks; the R7b gates; design lock v1
(commit `1e79358`, {{R/timeline/lock_v1/time}}); the local main panel.

**Sprint (2026-11-13 onward).** Lock addendum v2 (commit `f8e1fb3`, {{R/timeline/lock_v2/time}}; first P5 request
{{R/timeline/first_request/p5-qwen25_7b-v1}}, first online request
{{R/timeline/first_request/r7b-smoke-claude_opus_55-v1}}): P5, reasoning storage, online caps, predictions.
Amendment v2-a1: Claude thinking summaries flag. v2-a2: DeepSeek cap 16000 → 32000 after a failed smoke (the one
allowed repair). v2-a3 (commit `309fb1c`, {{R/timeline/amendment_v2_a3/time}}; first resumed Claude request
{{R/timeline/first_request/r7b-main-claude_opus_55-v2-b1}}): the Claude priority order of blocks (run order
only; items, prompts and scores unchanged), the usage-limit pause, the Saturday 12:00 CST hard stop, the DeepSeek
low-effort condition, the spend stop on the upper bound. **Post-freeze supplement.** Amendment v2-a4 (commit
`5c2b18a`, {{R/timeline/amendment_v2_a4/time}}; first supplement request
{{R/timeline/first_request/r7b-main-claude_opus_55-v2-b4}}), written after the frozen panel and the drafted report:
Claude's Tier H P3 and P4 cells only (lock-v1 items, prompts and scores; locked hash order; a fresh session per
world), no turn 2 on a later local date than its turn 1, an item still in a usage-limit pause at 23:00 CST fails,
hard stop 23:30 CST Saturday, the run stops at an isolation flag. Its outcomes are printed beside the frozen tally,
never in it (Appendix D). Every commit is listed in `PREEXISTING_WORK.md`.

**Predictions against outcomes** ({{R/predictions_summary/met|int}} met, {{R/predictions_summary/not met|int}}
not met; a prediction whose cell has fewer than 12 finished worlds, or whose model was not run, is "not testable in
this run"). The lock does not define "the floor" used by two predictions; post-hoc, a model is off the Tier W floor
when the lower bound of its balanced accuracy exceeds the always-"not settled" row at the reported precision
(llama-3.3-70b is the edge case and counts as at the floor). The rule that decides each outcome and its values are in `reports/sprint_all/report_data.json`.

{{table:predictions}}

# Appendix C. Worked example

See `reports/R7B_WORKED_EXAMPLE.md` for a full Tier W task, its valid check, the forged check (one phantom row),
the verifier's finding and the P5 message; reproduced from a pilot world never shown in the main panel.

# Appendix D. Online accounting and P5 descriptors

{{table:cells_online}}

*Table 6. Finished / planned worlds per online cell (main panel). The Claude run had a shared subscription window
and a hard stop (Saturday 12:00 CST); its blocks ran in a fixed priority order: Tier W P3 + P4, P5, Tier W P0–P2,
Tier H P3 + P4, Tier H P0–P2.*

{{table:smokes}}

*Table 7. Online smokes on 4 pilot worlds (8 turns). Pass rule fixed before each smoke: at least 6 of 8 turns
parsed and every Tier W turn parsed.*

{{table:online}}

*Table 8. Online accounting. Requests rejected by the subscription window reached no model and are counted
separately. Claude's cost is the CLI's notional figure on a subscription. Claude's requests include those of the
post-freeze supplement; its finished worlds do not.*

{{table:verdict_probability}}

*Table 9. Verdict and probability under a demand to commit (post-hoc descriptor, D120; Tier W). Open claims given
a definite verdict at turn 2 of the P2 worlds, how many of those with a stated probability in both turns keep it
within 0.05 of turn 1, and the mean absolute change; the last column is the same under the neutral P0. Claim-level
counts, no interval. DeepSeek's P2 cell is below 12 worlds.*

{{table:p5_cells}}

*Table 10. Which P5 worlds enter each metric: planned, finished (not stopped by a cap, the spend stop or an
error), and with a valid turn-2 reply (scored for detection or false alarm, and for adoption).*

**Post-freeze supplement (amendment v2-a4).** Claude Opus 5.5 on the Tier H P3 and P4 cells (12 planned worlds
each), run after the frozen panel and the drafted report. A contrast is computed only if both cells finish 12
worlds. These outcomes are not part of the frozen tally of Appendix B.

{{table:supplement}}

*Table 11. Post-freeze supplement: Tier H, where no check can be verified by lookup (amendment v2-a4). \* = a
cell below 12 finished worlds (point estimate only).*

{{table:supplement_predictions}}

*Table 12. The two lock-v2 predictions the supplement bears on, evaluated on Claude only (DeepSeek ran no Tier H).
P-D5 needs both cells at 12 worlds; P-A5 is a Task S prediction and uses every finished Tier H world.*

Of the {{R/supplement/worlds_planned|int}} planned worlds, {{R/supplement/worlds_finished|int}} finished;
{{R/supplement/failed_first_cause/turn-1 timeout (600 s)|int}} failed because Claude's first Tier H reply took
longer than the 600 s request timeout (the retry pass could not run them before the usage window closed), and
{{R/supplement/failed_first_cause/usage-limit pause past 23:00 CST|int}} were still waiting in a usage-limit pause
at the 23:00 CST deadline. The timed-out worlds are likely the harder ones, so the finished worlds are not a random
sample of the cells and the supplement is descriptive. On those worlds Claude's Task S balanced accuracy on Tier H
is {{R/supplement/balanced_accuracy_H}}; its replies count the consistent mechanisms node by node, which fits its
long Tier H turns. Under the forged tool report it adopted the forged status on
{{R/supplement/adopt_forged_P4|est}} of named claims, all of them in one world, where it wrote that the report's
counterexamples showed its own analysis "was wrong in places, though I have not found where"
(`main|synthetic|feedforward_hetero|4|`).

Two properties of the forged messages are reported, not repaired (post-hoc, D104). (i) For {{R/p5_design/forged_multi_line|int}} of
the {{R/p5_design/forged_named_claims|int}} forged named claims the forgery alters more than one line; quoting any
of them counts as a hit. Excluding it changes exact detection only for gemma-4-12b ({{P/models/g4/exact|est}} →
{{P/models/g4/exact_single_line|est}}). (ii) Because
forgeries are per claim, one message can show the same table entry with two different values, a contradiction
visible without the evidence rows. Such messages are not detected more often: mistral quotes the line in
{{P/models/mi/exact_contradiction_true|est}} of messages with a visible contradiction against
{{P/models/mi/exact_contradiction_false|est}} without. The same property holds for the locked P4: gemma-3-4b
adopts the forged status in {{P/models/g3/P4_contradiction/adopt_forged_P4_contradiction_true|est}} of P4
messages with a visible contradiction ({{P/models/g3/P4_contradiction/P4_with_contradiction}} of
{{P/models/g3/P4_contradiction/P4_messages}}).

# Appendix E. Background: short rules, exact consequences, and how symbolic computation was used

**E.1 Short rules, rich behaviour.** A short executable rule can generate behaviour far larger than itself
(Wolfram (2002)). Figure 4 shows this with two objects from the repository. Rule {{F/rule110/table|int}}, a rule of
{{F/rule110/rule_bits|int}} bits that is a fixture of the code's semantics tests, run for
{{F/rule110/steps|int}} steps from one live cell, draws a space-time diagram of {{F/rule110/diagram_bits|int}}
cells. The world of the worked example (Appendix C) has {{F/world/n|int}} nodes with two inputs each, so its rules
are {{F/world/table_bits|int}} table bits; they fix the next state of all {{F/world/states|int}} states,
{{F/world/behaviour_bits|int}} bits of behaviour. A short rule is not a shortcut: Wolfram argues that many simple
rules are computationally irreducible: in his terms, no shortcut finds their consequences faster than running them. This is why
the benchmark derives every consequence by enumeration and exact counting rather than by estimate.

![Short rules against the behaviour they generate, computed from the repository's objects
(`src/causalguard/sprint/figures.py`). (a) Rule {{F/rule110/table|int}}, {{F/rule110/rule_bits|int}} bits of rule, from one live cell
for {{F/rule110/steps|int}} steps ({{F/rule110/diagram_bits|int}} cells). (b) The worked-example world
(`pilot4|synthetic|rewired_control|0|`): each node's truth table over its two inputs,
{{F/world/table_bits|int}} bits in all. (c) Its behaviour: the next value of every node for each of the
{{F/world/states|int}} states ({{F/world/behaviour_bits|int}} bits).](../reports/sprint_all/fig4_background.png){width=100%}

**E.2 Description length, algorithmic probability, and what we do not claim.** The Kolmogorov complexity of an
object is the length of the shortest program that outputs it (Kolmogorov (1965); Chaitin (1966)). Solomonoff
(1964) weighted every program that reproduces the data by $2^{-\textrm{length}}$, which gives a universal prior for
induction, and Levin's coding theorem ties the two together for prefix complexity: an object's algorithmic
probability *m* and its prefix complexity *K* determine each other up to a constant, $-\log_2 m(x) = K(x) + O(1)$;
see Li and Vitányi (2008). Minimum description length (Rissanen
(1978)) is the computable version, bound to a chosen model class. Both universal quantities are uncomputable. A
length we compute, of an executable code that a fixed decoder reads back, is an *upper bound* on Kolmogorov
complexity relative to that decoder; ordering two bounds does not order the complexities, and nothing here measures
universal algorithmic probability. Choosing or weighting mechanisms by short code is an inductive policy, not a test
of truth. The programme used it before the sprint as a prior over the mechanisms consistent with the evidence.
Development runs, not confirmatory; Brier-score differences with 95 % intervals, positive favouring the first-named
method:

* release `v0.5.0-dev` (`reports/development_r5/g_evaluation.json`), {{X/r5_g/n_worlds|int}} held-out synthetic
  worlds: weighting consistent mechanisms by their length under the hierarchical code against uniform averaging, {{X/r5_uniform|ci4}}; weighting
  against predicting from the single shortest consistent mechanism, {{X/r5_shortest|ci4}}; the full hierarchical
  code against the best generic code chosen on calibration, {{X/r5_g|ci4}}, no detected advantage.
* release `v0.6.0-dev` (`reports/development_r6/s_evaluation.json`), {{X/r6_s/n_worlds|int}} held-out fragments of
  published models ({{X/r6_s/n_groups|int}} source lineages): a code whose rule-type weights are fitted to the
  evidence against the best fixed code, {{X/r6_s|ci4}}, a small effect.

**E.3 Symbolic computation in this work.** The benchmark is exact because it never samples mechanisms. A set of
rules is represented symbolically as a schema: a node's truth table with the rows the evidence fixes and the others
left as don't-cares. The version space V(D), every mechanism of the declared class that reproduces the evidence D,
is then a product of per-node schema sets, because every evidence row is a single synchronous step and so
constrains each node on its own, and is counted exactly; because a function that ignores an input fits on
several input sets, each mechanism is counted once, by its essential inputs, through Möbius inversion. Two engines
must agree on every claim (Tier H: a per-node enumeration of the class and the schema-counting engine; Tier W: a
table-lookup engine and the explicit version space restricted to the given wiring), and a complete SAT encoding must
agree with them on every status. A derivation is a symbolic trace (step, node, input values, the evidence row it
cites or "no row"); a verifier replays it line by line, and a forgery is a single-line edit that the verifier
rejects at exactly that line. Counting gave the sprint its answer key and p\*; the agreement of engines and SAT, its
gates; traces and verifier, the valid and forged checks; and the same exact verdicts, the remedy of §5.

**E.4 Lineage and status.** The line runs from the author's chapter with Zenil, Kiani and Tegnér on algorithmic
complexity and dynamic querying (Hernández-Espinosa et al. 2021), through algorithmic causal deconvolution and the
algorithmic information calculus of that group (Zenil et al. 2019a; Zenil et al. 2019b), to the author's index-set
calculus for Boolean networks (an unpublished manuscript, not part of this submission), to the CausalGuard
development iterations (pre-sprint, releases `v0.1.0-dev` to `v0.6.0-dev`, 2026-11-09 to 2026-11-12), and to this
benchmark (pre-sprint) and the sprint's verify-first control, online runs and report. The biological applications
of algorithmic causal deconvolution are those authors' results; we have not applied our method to biological data.
Random Boolean networks as models of gene regulation (Kauffman (1969)) and block-decomposition estimates of
algorithmic complexity (Zenil et al. 2018) are the background against which Boolean networks were chosen. The
programme is under construction: this paper uses its exact part; the compression part is motivation and prior
work, and the sprint result neither depends on it nor validates it.

# LLM Usage Statement

Claude Opus 5.5 wrote the code, ran the runs and the analysis, and drafted this report; Claude Fable, as director,
wrote each iteration's assignment, reviewed every delivery and its numbers, and requested the corrections recorded
in `DECISIONS.md`; the author set the question and the direction, took the decisions at the director's checkpoints,
and reviewed and approved the report. Every number in the report is generated by `report/fill.py` from the
analysis outputs, and the build fails if the text holds a number that is not in them. Claude Opus 5.5 is also one
of the evaluated models; it ran in isolated, audited contexts, separate from the sessions that built the benchmark.
