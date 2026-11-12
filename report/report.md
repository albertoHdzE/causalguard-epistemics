---
title: "What does the evidence settle? An exact benchmark and checker for AI overclaiming"
subtitle: "Research conducted at the AI x Epistemics Research Sprint, November 2026 (Apart Research)"
author:
  - "Alberto Hernández Espinosa — affiliation TBD"
  - "With Apart Research"
geometry: margin=2.2cm
fontsize: 10pt
---

<!-- Structure follows the official Apart template (report/apart_official_template.docx, downloaded 2026-11-12 from
https://docs.google.com/document/d/17b3JWki-ZkaqdmqGI5d0gof-HwlGuWU9Mc1_klNZXKs). Limit: 8 pages excluding
references and appendices. Build: report/build.sh -> report/report.pdf (and report.docx in the official styles).
STATUS: SKELETON written pre-sprint (R7). Every number marked TBD is filled during the sprint from
reports/SPRINT_*_RESULTS.md; no number may be typed in by hand. -->

# Abstract

TBD (150–250 words, written last): the problem (models assert what their evidence does not settle, and yield to
pressure), the approach (exact evidential status as ground truth, a randomised pressure turn, the exact check as a
remedy), key results per model with intervals, and the main takeaway.

# 1. Introduction

TBD. Calibration and honesty benchmarks usually score a model against what is *true*. A model can be right by luck
about a claim its evidence does not settle, and wrong to commit to it. We score against what the evidence
*supports*. In a controlled family of hidden mechanisms, the status of every claim (settled true, settled false,
or not settled) and the probability of every open claim are computed exactly.

Our main contributions are:

1. TBD — the benchmark (exact status and exact p*, two independent engines, synthetic and published-mechanism
   worlds).
2. TBD — the pressure measurement (four randomised follow-up conditions; discernment).
3. TBD — the check as a remedy, and where it stops working (outside the declared class).

# 2. Related Work

TBD from `docs/SPRINT_RELATED_WORK.md` (verified references only).

# 3. Methods

TBD: worlds and the declared class; status and p*; Task S; Task P conditions and hash assignment; scores; reference
rows; gates; lock; models; analysis (world-level cluster bootstrap, Holm).

# 4. Results

TBD. Figure 1: overclaim against underclaim, one point per model. Figure 2: Task P by condition. Table 1: Task S.
Table 2: discernment.

# 5. Discussion and Limitations

TBD.

**Limitations.** Status is exact *inside the declared class* (synchronous Boolean networks, at most three inputs per
node). The task is a controlled one; we make no claim that results transfer to natural-language reasoning in
general. Local models ran at temperature 0; the Claude route cannot set temperature. The model family that built the
benchmark (Claude) is also evaluated, in fresh contexts with no access to the repository.

**Future work.** TBD.

# 6. Conclusion

TBD.

# Code and Data

* Code repository: https://github.com/albertoHdzE/causalguard-epistemics (branch / tag TBD)
* Data: committed manifests (`artifacts/sprint_*_manifest.json`), raw runs in the release asset (TBD)

# Preexisting work and sprint work

| Done before the sprint (preexisting, disclosed) | Done during the sprint (2026-11-13 to 2026-11-15) |
|---|---|
| CausalGuard engines: exact version-space counting, the independent D engine, SAT cross-check (iterations 1–6) | TBD |
| R5/R6 development evidence used as motivation only (Track A investigation pilot, Track A2 gate-in-the-loop, Track M assumption failures) | |
| R7 (2026-11-12, the day before the sprint): this benchmark's code, the smoke runs and three pilots, the pre-run gates, the online adapters (no benchmark item sent online). The main panel was NOT run in R7 (gates failed) | |

Commit timestamps in the repository date every item. See `PREEXISTING_WORK.md`.

# References

TBD (from `docs/SPRINT_RELATED_WORK.md`; author, year, title, venue, URL).

# Appendix A. Limitations and Dual-Use / Ethical Considerations

TBD (required). Draft points: (1) dual use: a measurement of how models yield to pressure could be used to tune
persuasion; the benchmark measures yielding to *unsupported* pressure and rewards yielding only to checked
evidence. (2) The exact check certifies only inside the declared class; when the class is wrong it can pass a false
claim (preexisting evidence, R5 Track M). Presenting it as general verification would overclaim. (3) No human
subjects; the published models are third-party and not redistributed. (4) Online models were run through their
providers' terms; no personal data is in any prompt.

# Appendix B. Prompts

TBD from `docs/SPRINT_TASKS.md` (exact text and hashes).

# LLM Usage Statement

TBD. Draft: the benchmark code, runs and analysis were implemented by Claude Opus 5.5 (Claude Code) and directed
and reviewed by Claude Fable, under the author's instructions. Every number in this report is generated from the
raw runs by the committed analysis command.
