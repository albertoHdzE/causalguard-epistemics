# Iteration 9 — the two online decisions and the day-2 plan (director, 2026-11-13 14:30 CST)

Read after `reports/SPRINT_STATUS_DAY1.md` and `reports/sprint_online/DEEPSEEK_STOP.md`. Decisions D101–D106 in
`DECISIONS.md`. Implementation-agent decisions continue from D107.

## 0. What the director verified before deciding (objects, not the status note)

| claim | object | result |
|---|---|---|
| lock v2 precedes every P5 and online request | `git show -s f8e1fb3` = 09:15:16 CST (15:15:16Z); first `events.jsonl` line of `p5-qwen25_7b-v1` 15:17:12Z, `p5-gemma3_4b-v1` 15:17:20Z, both smokes 15:18:03Z, Claude main 15:37:22Z | holds |
| local P5 complete for 5 models | status counts per `p5-*` run | 60/60 ok each; r1 10/60 ok at 14:07 CST, running |
| Claude main stopped by the usage window | 180 `attempts/*/001.json` | 6 ok (all Tier W: P0 1, P2 2, P3 2, P4 1), 173 `usage_limit_reached` (154 in under 2 s, 19 slower), 1 `claude_cli timeout`; run 15:37–15:48Z |
| DeepSeek spend | `runs/sprint-online-calls/deepseek_spend.jsonl`, 20 lines | `usd` present on 8 lines only, sum $0.50; `usd_upper` on all 20, sum $1.52. **Defect**: 12 lines (smoke v1 and the probe) carry no off-peak figure |
| ledgers | local 3132 lines (2509 + P5); Claude 196 lines; DeepSeek 16 | all inside the ceilings |

The status note says "rejected in under a second each": 154 of 173 were; 19 took 2–600 s. Say it that way.

## 1. Decision 1 — DeepSeek (D101)

The failure is real and is itself a result: at the provider's default reasoning effort the model does not finish a
Tier H turn inside 32 000 completion tokens and finishes 2 of 4 Tier W turns; the stored reasoning shows hand
enumeration of the hypothesis class. That goes into the report as a finding, with the token counts.

**One further smoke is allowed, as a new, labelled model condition, not as a repair**: `deepseek-v4-pro` with
`reasoning_effort` lowered one step (to `medium`; if the API accepts only on/off, thinking **off**, labelled as a
non-reasoning condition), completion cap 32 000, the same 4 pilot-4 worlds, the same pass rule fixed in v2-a2
(≥ 6 of 8 turns parsed and every Tier W turn parsed). Cost under $1 at the upper bound.

- Pass → run DeepSeek in the **priority order of §2(a)** at 8 workers, from the lock-v2 snapshot, config
  `r7b_online_main_deepseek_v4_pro_medium.json`, run id `r7b-main-deepseek_v4_pro_medium-v1`; then P5. Every table
  and figure labels it "DeepSeek V4-Pro, reasoning effort medium (high-effort smoke failed; §x)". Spend stop at
  $25 **on the upper bound**.
- Fail → DeepSeek is out. No further DeepSeek request of any kind. The two smokes and the medium smoke are reported.

Spend-record fix (record only): every spend line carries `usd`, `usd_upper`, `peak`, `t`; the lines without `usd`
are back-filled from the recorded tokens and the list price, each marked `backfilled: true`. The report quotes both
sums.

## 2. Decision 2 — Claude Opus 5.5 under the subscription window (D102)

(a) **Priority order** (lock amendment v2-a3, committed and pushed before any further Claude request). Blocks, in
this order; inside a block the locked hash order:

| block | cells | worlds | why |
|---|---|---|---|
| B1 | Tier W P3, Tier W P4 | 48 (6 already done) | the headline contrast |
| B2 | P5v, P5f | 60 | the headline control |
| B3 | Tier W P0, P1, P2 | 72 (3 done) | Task S, Task P baseline and the pressure gradient |
| B4 | Tier H P3, P4 | 24 | P-D5 |
| B5 | Tier H P0, P1, P2 | 36 | completeness |

The run order is not a scientific quantity (items, assignments, prompts and scoring are unchanged); the lock fixed it
only as a reproducibility convenience. The amendment says this, and the report says which blocks finished.

(b) **Usage-limit handling** (harness, record only): on the first `usage_limit_reached` the runner **pauses the
queue** instead of firing it (no more burning 174 slots in 11 minutes); it records the rejection in the online
ledger with `kind: usage_limit_rejected`, which **does not count toward the 520 cap** (no model was reached) but is
counted and reported separately; it resumes when the window reopens (use the reset time if the CLI error carries
one, otherwise one probe request every 15 minutes). Workers: 2. The 173 rejected items are re-queued; the one
timeout is a D85 retry; the 6 finished worlds stand.

(c) **Window discipline.** The subscription is shared by the benchmark, the implementation agent and the director's
session. Rule: from the moment the agent stops work tonight (target 22:00 CST) until 08:00 CST Saturday the
benchmark runner has the window to itself. **Hard stop for Claude benchmark requests: Saturday 14 Nov 12:00 CST.**
Whatever has finished by then is the Claude panel. After that the window belongs to analysis and writing.

(d) **Reporting incomplete cells** (pre-declared now): every cell is reported with `n finished / n planned`; a
contrast (P3 against P4, P5f against P4, P5v against P3) is computed only when both cells have at least 12 finished
worlds; cells below 12 appear in the table with their n and no interval interpretation. Nothing is dropped.

(e) The stored Claude reasoning is the CLI's **summarised** thinking, not the raw reasoning. Every mention in the
report says "thinking summaries".

## 3. Other decisions

- **D103 — the report stands on the local data.** Six local models on the main panel and six on P5 are the
  evidence base; the online cells are the frontier anchor and slot in through `report/fill.py`. No sentence, table
  or figure may require an online result to exist. Write the Saturday draft with local data first, then fill.
- **D104 — the two P5 descriptors (D93, D95) are reported, not repaired.** (i) Exact detection counts a hit on any
  altered line; add a sensitivity row excluding the 5 multi-line claims. (ii) Compute per forged message whether the
  two statements of the same table entry disagree (a "visible contradiction"), and report detection split by that
  flag, labelled post-hoc. Both apply to P4 as well; say so.
- **D105 — r1 P5 and qwen-72b.** r1 P5 finishes on its own (about 18:30 CST). If it has not finished by 20:00 CST
  the analysis uses the finished worlds, labelled. **qwen2.5:72b is out**: condition 4 of the addendum (every locked,
  online and P5 run finished before Saturday noon) cannot hold. Reported as not run.
- **D106 — spend and request accounting in the report.** Report, per online model: requests sent, requests rejected
  without inference, worlds finished per cell, recorded spend (DeepSeek: off-peak and upper bound; Claude:
  `totalCostUSD` per session summed, labelled notional).

## 4. Day-2 plan (CST)

| when | agent | benchmark |
|---|---|---|
| Fri 14:30–16:30 | amendment v2-a3 (priority order, usage-limit pause, spend-record fix, DeepSeek medium config), tests, commit, push; DeepSeek medium smoke | Claude main resumed at 2 workers in priority order as soon as the amendment is pushed |
| Fri 16:30–22:00 | analysis over all runs (`sprint-analyze` + `sprint-p5 analyze` combined), figures 1–3, `report/fill.py`, report text from local data; reasoning coding of the **local** sample | DeepSeek main + P5 if its smoke passed (background, 8 workers); Claude continues |
| Fri 22:00 – Sat 08:00 | **idle** | Claude alone on the window |
| Sat 08:00–12:00 | coding of the online sample (whatever exists), figure polish, Appendix A/B/C | Claude until the 12:00 hard stop |
| Sat 12:00 | Claude panel frozen; DeepSeek stopped if still running (whatever finished stands) | — |
| Sat 12:00–20:00 | regenerate analysis twice (byte-identical), fill, build PDF + DOCX, `PREEXISTING_WORK.md` rows, README, push; `reports/REVIEW_READY_SPRINT.md` to the director by **20:00** | — |
| Sun | director review → fixes → final PDF 18:00 → Alberto submits | — |

## 5. Report: what changes against the §5 plan of iteration 8

- Results open with Table 1 (forged adoption, corruption, discernment per model and tier; online rows with their
  n per cell), then Table 2 (P5: exact and lenient detection, false alarm, verified discernment, adoption drop
  against P4), then Table 3 (Task S). Figures as planned. A short subsection "Frontier models under the benchmark's
  cost": DeepSeek's token-bound failure at high effort, with numbers; Claude's finished blocks.
- Appendix A adds: the benchmark's reasoning cost as a limitation; the shared subscription window as the reason for
  incomplete online cells; thinking summaries, not raw reasoning, for Claude.
- Predictions: all of lock v1 and v2 against outcomes. Any prediction whose cell did not reach 12 worlds is "not
  testable in this run", not "not met".

## 6. Stop conditions (unchanged from iteration 8 §7, plus)

DeepSeek upper-bound spend reaches $25; the Claude isolation audit flags anything; any v1 or v2 lock key changes; a
usage-limit pause lasts past Sat 12:00 (then stop, do not wait).

## 7. Return contract

`reports/REVIEW_READY_SPRINT.md` as in iteration 8 §8, plus: the v2-a3 commit hash and time against the first
resumed Claude request; the DeepSeek medium smoke outcome; per-cell n for every online cell; the usage-limit
rejection count; spend both ways; and the PDF.
