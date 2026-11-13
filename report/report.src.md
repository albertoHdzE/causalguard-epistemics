---
title: "Models adopt forged checks they could verify: an exact benchmark of evidence-relative reasoning under pressure"
subtitle: "Research conducted at the AI x Epistemics Research Sprint, November 2026 (Apart Research)"
author:
  - "Alberto Hernández Espinosa — independent researcher"
  - "With Apart Research"
geometry: margin=2.0cm
fontsize: 10pt
header-includes:
  - \usepackage{etoolbox}
  - \AtBeginEnvironment{longtable}{\footnotesize}
---

<!-- SOURCE of report/report.md. Every number comes from reports/sprint_all/*.json through report/fill.py; the
build fails on a hand-typed number. Do not edit report.md by hand. -->

# Abstract

When a model is shown a step-by-step "check" of its answers, does it verify the check against the evidence, or
defer to it? We built a benchmark where this is decidable. Each task shows a hidden deterministic system (a
Boolean network) through a few evidence rows, and asks whether claims about it are settled true, settled false or
not settled. The answer key is exact: two independent exact engines and a SAT solver compute each claim's status
from the evidence. In a second turn the model receives one of five randomised follow-ups, including a valid check
(P3) and a forged one (P4) that differs from it in a single line contradicted by a cited evidence row. When the
wiring is given (Tier W), every line can be verified by lookup. Six local open-weight models adopt the forged
status on most named claims, from {{A/models/g3/tiers/W/C/adopt_forged/P4|est}} (gemma-3-4b) to
{{A/models/ll/tiers/W/C/adopt_forged/P4|est}} (llama-3.3-70b), and their check discernment is near zero. A
pre-registered control (P5) asks the model to verify every line first and to quote any wrong one. Unprompted, the
local models almost never check; told to verify, some do find forged lines, but they flag valid lines about as
often, and when a small model flags the forged line it usually keeps the forged status anyway (qwen2.5-7b in
{{P/models/q7/flagged_then_adopted/flagged_adopted|int}} of {{P/models/q7/flagged_then_adopted/flagged|int}}
flagged claims). Verification text and final answer come apart. We report a frontier model (Claude Opus 5.5) and a
reasoning model at low effort (DeepSeek V4-Pro) on the same items, with the cells the run finished. The exact check
works as a release gate inside the declared class; outside it, it does not certify.

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

Our main contributions are:

1. **An exact benchmark of evidence-relative reasoning under pressure.** Claims are scored against what the
   evidence settles, not against what is true. Five randomised follow-ups (neutral, empty disagreement, demand to
   commit, valid check, forged check) are assigned by hash to disjoint worlds. Two tiers separate "cannot verify"
   (wiring hidden) from "could verify by lookup" (wiring given).
2. **A forged-check measurement with a verify-first control.** Six local models adopt forged checks they could
   verify. A pre-registered condition that tells them to verify shows that some can find the forged line, but
   their flags do not separate forged from valid lines, and their answers often follow the forged check even after
   they call its line wrong.
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
valid and a forged checked challenge on randomised worlds, and P5 asks for verification explicitly. We have not
found this paired, exactly scored measurement in the work above. That is a statement about these references, not
a literature-wide claim.

# 3. Methods

**Worlds and status.** A world is a synchronous Boolean network of 8 nodes with at most 3 inputs per node. It is
drawn from synthetic strata or from published regulatory-network fragments. The model sees a few evidence rows
(one synchronous step each, optionally with clamped nodes) and 8 claims ("from this start state, after k steps,
node X = 1"). A claim is *settled true* if every mechanism of the declared class that reproduces the evidence makes
it true, *settled false* if none does, and *not settled* otherwise. For open claims, p\* is the exact share of
consistent mechanisms making the claim true. Two independent exact engines and a SAT encoding must agree on every
claim (gates passed on every item).

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
predictions before any P5 or online request. Its three amendments are disclosed (Appendix B). The unit is the
world; 95 % intervals come from 2000 cluster-bootstrap replicates over source groups; tests against zero and
against the surface rule are Holm-adjusted within tier. Online cells are reported with the number of finished
worlds over planned worlds; a contrast is computed only if both cells finished at least 12 worlds (pre-declared
before the online runs resumed).

# 4. Results

## 4.1 Forged checks are adopted (Tier W, main panel)

{{table:task_p}}

*Table 1. Task P per model and tier: share of named claims whose final verdict adopts the check's status, under
the valid check (P3) and the forged check (P4); corruption under P4; check discernment with its 95 % interval.
n = finished / planned worlds. \* = an incomplete cell below 12 worlds (no interval). † half panel. ‡ labelled
condition (reasoning effort low).*

On Tier W every local model adopts the forged status on most named claims. llama-3.3-70b, mistral-small-24b and
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

*Table 2. P5 verify-first (Tier W, 60 worlds per model; locked scorer). Exact and lenient detection of the altered
line in forged checks (P5f); false alarm on valid checks (P5v); forged adoption under P5f and its difference from
P4 (between-world); verified discernment = true-status adoption under P5v − forged adoption under P5f.*

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
reach the decision. r1's main-run reasoning was not stored.*

Unprompted (P4), replies restate the check ("row #01 shows that L1 transitions to 1, which matches the claim",
mistral, `main|published|published|0|`). Several gemma-4-12b replies read the cited row themselves, get a value that
contradicts the forged line, and defer: "In row #05 … the result is D1 → 1. Wait, let's re-check. Actually, the
user provided a hint that c0 is settled TRUE." (`main|synthetic|mixed_parity_thresh|8|`). Told to verify (P5f),
gemma-4-12b checks bit by bit and catches forged lines of every kind ("Row #02 shows these inputs. So the statement
'no evidence row shows these inputs' is Incorrect.", `main|synthetic|shared_motifs|17|`); qwen2.5-7b quotes a
forged line as incorrect and marks the identical forged line of another claim correct
(`main|synthetic|feedback_canalizing|7|`).

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
({{A/models/r1/tiers/W/contrasts/check_discernment}}). A model that cannot trace a claim itself cannot be
expected to catch a forged trace; r1 could do better than the floor, and still did not.

![Task S: overclaim (orange squares) and underclaim (blue circles) per model and tier; the surface rule
is the reference row (hollow). Lines are 95 % intervals.](../reports/sprint_all/fig2_task_s.png){width=100%}

## 4.4 Frontier models under the benchmark's cost

<!-- SAT (after the 12:00 freeze): prose on what Claude did, from the filled tables only. -->

{{table:cells_online}}

*Table 6. Finished / planned worlds per online cell (main panel). The Claude run had a shared subscription window
and a hard stop (Saturday 12:00 CST); its blocks ran in a fixed priority order: Tier W P3 + P4, P5, Tier W P0–P2,
Tier H P3 + P4, Tier H P0–P2.*

**DeepSeek at high effort does not finish.** {{table:smokes}}

*Table 7. Online smokes on 4 pilot worlds (8 turns). Pass rule fixed before each smoke: at least 6 of 8 turns
parsed and every Tier W turn parsed.*

At the provider's default (high) effort, DeepSeek V4-Pro spent every token of a 16000 cap and then between
{{R/smokes/deepseek_high_32k/reasoning_tokens_min|int}} and {{R/smokes/deepseek_high_32k/reasoning_tokens_max|int}}
reasoning tokens of a 32000 cap, finishing {{R/smokes/deepseek_high_32k/parsed_W|int}} of
{{R/smokes/deepseek_high_32k/turns_W|int}} Tier W turns and none of the Tier H turns. Its stored reasoning
enumerates candidate mechanisms by hand. The benchmark's cost for a reasoning model is itself a finding: exact
evidence-relative reasoning over 8 claims is expensive when done by enumeration. At effort low it passed the smoke
and ran as a labelled condition.

**What a frontier reasoning model does with a forged check.** On Tier W, DeepSeek V4-Pro at low effort rejects
most forged checks (check discernment {{A/models/ds/tiers/W/contrasts/check_discernment}}). Its stored reasoning
shows how. In {{C/ds/P4/c_names_altered_line|int}} of {{C/ds/P4/n|int}} coded P4 replies it rebuilds the cited lookups and names the misread row ("checker says row #01
shows F3 -> 1. That is definitely misreading", `main|published|published|20|`). The exceptions are the instructive
ones. In one, it never checks: "We should trust checker if it's correct. Let's double-check each claim manually
maybe, but … We should accept those corrections." (`main|synthetic|shared_motifs|12|`). In another it finds both
forged lines wrong ("both user corrections are based on misreading rows") and still concludes "I think the safest
is to follow the user's explicit correction" (`main|synthetic|uniform_H|0|`), the same decoupling of check and
answer as the local models, at the level of the reasoning. One reply calls the check "likely a test to see if I
will catch the inconsistency" (`main|published|published|0|`).

{{table:online}}

*Table 8. Online accounting. Requests rejected by the subscription window reached no model and are counted
separately. Claude's cost is the CLI's notional figure on a subscription.*

# 5. Discussion and Limitations

**What the results mean.** On items where every line of a check can be verified with one lookup, six local models
treat a check as authoritative: they adopt its status whether it is valid or forged, and they lose correct answers
to it. Asked to verify, some of them do produce verification text, and it sometimes finds the forged line; but it
also flags valid lines, and the final answer often follows the forged check even for the claim whose line the
model has just called wrong. This separates explanations that sycophancy measurements cannot: the failure is not
that checking is impossible (Tier W makes it a lookup), nor that the instruction is ignored (under P5 the models
check line by line). The model's own check does not govern its answer. For agentic pipelines in which one model's intermediate result is another's input,
a single forged step is enough.

**The exact check as a remedy.** Inside the declared class, the same exact engine that labels the items can gate
a model's released verdicts. A settled verdict that the checker contradicts is released as "not settled". This
removes overclaim by construction but cannot add what the model missed. Outside the class the checker can
certify a false claim (pre-sprint evidence, Appendix A). It is a remedy for this class, not a general verifier.

**Limitations.** (1) Status is exact only inside the declared class (synchronous Boolean networks, at most 3
inputs per node); the tasks are synthetic and we make no claim that results transfer to natural-language
reasoning. (2) Five of six local models are at the Task S floor, so for them P4 measures deference more than a
failed attempt to verify; the off-floor case is r1 and the online models. (3) Two local models ran half the panel.
(4) The online cells are incomplete (Table 6): the Claude subscription window was shared with the development
session, and DeepSeek ran only at low effort. (5) Claude's stored reasoning is the CLI's *thinking summaries*,
not the raw reasoning. (6) P5 and P4 are between-world contrasts. (7) The model family that implemented the
benchmark (Claude) is also evaluated, in isolated, audited contexts.

**Future work.** Measure where between "cannot verify" and "verifies" a model starts to discriminate (lookup
depth, number of forged lines); test whether a cited-row consistency tool, offered to the model, closes the gap.

# 6. Conclusion

Given a forged check that they could verify by one lookup, six open-weight models adopt it. Told to verify, some
find the forged line, flag valid lines about as often, and frequently keep the forged answer after calling its line
wrong. The benchmark makes this measurable
because the answer key is exact and the forged check differs from the valid one in a single checkable line. We
release the generator, the gates, the lock and every run.

# Code and Data

* Code: https://github.com/albertoHdzE/causalguard-epistemics (branch `sprint`); analysis:
  `scripts/sprint_analyze_all.sh`; report: `report/fill.py` and `report/build.sh`.
* Data: committed manifests (`artifacts/sprint_main_manifest.json`, `artifacts/sprint_p5_manifest.json`), the
  design lock with its addendum and amendments (`docs/SPRINT_DESIGN_LOCK.json`), raw runs in the release asset.

# References

Amayuelas, A. et al. (2023). Knowledge of Knowledge: Exploring Known-Unknowns Uncertainty with Large Language
Models. arXiv:2305.13712.
Han, S. et al. (2022). FOLIO: Natural Language Reasoning with First-Order Logic. arXiv:2209.00840.
Kirichenko, P. et al. (2025). AbstentionBench: Reasoning LLMs Fail on Unanswerable Questions. arXiv:2506.09038.
Laban, P. et al. (2023). Are You Sure? Challenging LLMs Leads to Performance Drops in The FlipFlop Experiment.
arXiv:2311.08596.
Lin, S., Hilton, J., Evans, O. (2022). Teaching Models to Express Their Uncertainty in Words. arXiv:2205.14334.
Perez, E. et al. (2022). Discovering Language Model Behaviors with Model-Written Evaluations. arXiv:2212.09251.
Sharma, M. et al. (2023). Towards Understanding Sycophancy in Language Models. arXiv:2310.13548.
Tafjord, O., Dalvi Mishra, B., Clark, P. (2021). ProofWriter: Generating Implications, Proofs, and Abductive
Statements over Natural Language. Findings of ACL. arXiv:2012.13048.
Tian, K. et al. (2023). Just Ask for Calibration. EMNLP. arXiv:2305.14975.
Wang, B., Yue, X., Sun, H. (2023). Can ChatGPT Defend its Belief in Truth? Findings of EMNLP. arXiv:2305.13160.
Wen, B. et al. (2024). Know Your Limits: A Survey of Abstention in Large Language Models. TACL. arXiv:2407.18418.
Xiong, M. et al. (2024). Can LLMs Express Their Uncertainty? ICLR. arXiv:2306.13063.
Yin, Z. et al. (2023). Do Large Language Models Know What They Don't Know? Findings of ACL. arXiv:2305.18153.

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
completion tokens. The online cells are incomplete because of that cost and of the shared subscription window,
not by selection.

**Human subjects and data.** None; no personal data appears in any prompt. Online models were used under their
providers' terms.

**AI tool use.** Code, runs, analysis and the first draft of this report were produced by Claude Opus 5.5 under
the direction and review of Claude Fable and the author. Every number in the report is generated by
`report/fill.py` from the analysis outputs; the build fails if the text holds a number that is not in them.

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
low-effort condition, the spend stop on the upper bound. Every commit is listed in `PREEXISTING_WORK.md`.

**Predictions against outcomes** ({{R/predictions_summary/met|int}} met, {{R/predictions_summary/not met|int}}
not met; a prediction whose cell has fewer than 12 finished worlds, or whose model was not run, is "not testable in
this run"). The lock does not define "the floor" used by two predictions; post-hoc, a model is off the Tier W floor
when the lower bound of its balanced accuracy exceeds the always-"not settled" row at the reported precision
(llama-3.3-70b is the edge case and counts as at the floor). The rule that decides each outcome and its values are in `reports/sprint_all/report_data.json`.

{{table:predictions}}

# Appendix C. Worked example

See `reports/R7B_WORKED_EXAMPLE.md` for a full Tier W task, its valid check, the forged check (one phantom row),
the verifier's finding and the P5 message; reproduced from a pilot world never shown in the main panel.
