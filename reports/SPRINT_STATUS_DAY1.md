# Sprint status, day 1 (implementation agent, 2026-11-13 ~13:45 CST) — two decisions needed from the director

Not the review-ready entry point (`reports/REVIEW_READY_SPRINT.md` comes later). Alberto chose "wait for director"
on both online questions below.

## Done (commits on `sprint`)

| commit | what |
|---|---|
| `f8e1fb3` 09:15 CST | lock v2 (reasoning storage, cost/spend stop, P5 manifest/templates/scorer/gates/analysis, configs, predictions). Precondition: ruff clean; 517 passed / 5 skipped; `sprint_local` regenerated 6/6 byte-identical (D90). P5 gates all pass (`reports/P5_GATES.md`, D94) |
| `e9d7b2c` | amendment v2-a1: Claude thinking via `--thinking-display summarized` (the `--settings` route is ignored under `-p`; D97) |
| `63a2ca0` | pre-registered reasoning coding (D98), before any sprint reply was read |
| `7c923a3` | amendment v2-a2: the one DeepSeek repair (cap 32k, time-of-day spend stop; D99) |
| `16866cb` | DeepSeek stop record (D100, `reports/sprint_online/DEEPSEEK_STOP.md`) |

Found while building (D93, D95): 5 of 228 P5 named claims have 2–3 altered lines, not exactly one (any counts as
a hit); one forged message can state the same table entry two ways (per-claim forgeries), so a contradiction is
visible without the evidence rows, in P4 (lock v1) as in P5. Counted as a post-hoc descriptor.

## Runs

| run | state |
|---|---|
| local P5: gemma-3-4b, qwen2.5:7b, mistral-24b, llama-70b, gemma-4-12b | complete, 60/60 ok each |
| local P5: r1-distill-32b | running on LM Studio (last of the queue) |
| Claude smoke | **pass**: 8/8 parsed, isolation clean 8/8, thinking summaries 8/8 |
| DeepSeek smoke | **fail after the one repair** (16k: 0/8 parsed; 32k: 2/8). Stopped; ~$1 spent. Options in `DEEPSEEK_STOP.md` |
| Claude main (`r7b-main-claude_opus_55-v1`) | 6/180 ok (all Tier W), then 174 items rejected in under a second each with `usage_limit_reached` (the subscription's 5-hour window, shared with the agent session). No inference on those, but each used a ledger slot (ledger 196/408). Not resumed |

## Decision 1: DeepSeek

Leave out / retry at lower effort (labelled) / retry at 64k (likely cut by the $25 stop). Agent recommends leaving it
out and reporting the smoke as a finding (reasoning-bound: 29–32 k reasoning tokens even when it finished).

## Decision 2: Claude under the subscription window

Measured notional cost per world: Tier W $0.14–0.34 (6 worlds), Tier H about $1.2–1.4 (smoke). The window was
exhausted after about 6 worlds plus in-flight items plus the agent's own use. The full 180 + 60 P5 worlds will not
fit by Sat 20:00 CST at this rate. Agent's recommendation: run in priority order — Tier W P3 + P4 (48 worlds), then
P5 (60), then the rest of Tier W, then Tier H — at 2 workers, resuming each window; usage-limit rejections (no
inference) excluded from the 520 cap, documented; the report states exactly which cells finished. This reorders the
locked hash run order, which the lock does not fix as a scientific quantity, but it is the director's call.

## Interim local P5 (5 of 6 models; NOT final, r1 missing; regenerated later from the runs)

`/tmp/p5_interim/P5.md` (not committed). Exact detection under P5f is 0.00–0.22 across the five models; mistral's
0.22 sits beside a 0.20 false-alarm rate on P5v. Forged adoption drops from P4 to P5f for gemma-4 (−0.43),
gemma-3 (−0.18), mistral (−0.18); llama 0.00, qwen not yet compared in this table. Between-world contrasts.

## Next action after the decisions

Resume Claude per decision 2; run `sprint-p5 analyze` and `sprint-analyze` over all runs; reasoning coding (sample
is drawn by `sprint-coding sample`, D98); report.
