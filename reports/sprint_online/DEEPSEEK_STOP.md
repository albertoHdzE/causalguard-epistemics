# DeepSeek V4-Pro: stopped at the smoke (stop condition §7, sprint addendum)

**Status: no DeepSeek main-panel or P5 request was sent.** Stop condition: "an online smoke fails parsing after one
harness repair". Recorded 2026-11-13 by the implementation agent.

| run | cap (completion tokens) | turns parsed | finish `length` | reasoning tokens per turn | spend (list price at request time) |
|---|---|---|---|---|---|
| `r7b-smoke-deepseek_v4_pro-v1` (lock v2) | 16 000 | 0 / 8 | 8 / 8 | 16 000 (all of the output) | $0.26 (off-peak; peak upper bound $0.51) |
| `r7b-smoke-deepseek_v4_pro-v2` (amendment v2-a2, the one repair) | 32 000 | 2 / 8 | 6 / 8 | 28 707–32 000 | $0.50 |

Pass rule for v2, fixed in amendment v2-a2 before it ran: at least 6 of 8 turns parsed and every Tier W turn parsed.
Result: 2 of 8 parsed (both Tier W turn 2); every Tier H turn and both Tier W turn 1 stopped inside reasoning.
**Fail.** Both smokes use pilot-4 worlds only (never main panel, never P5).

What the reasoning shows (read, not scored): on Tier H the model enumerates candidate input sets node by node
("Try support {K1,P5,G6}? ... conflict with R11. no."), i.e. it searches the hypothesis class by hand; at 75–80 k
characters it is still searching. The two Tier W turns that finished used 28.7 k and 31.2 k reasoning tokens.

Options for the director (none taken):

1. Leave DeepSeek out; the frontier anchor is Claude Opus 5.5 alone (running).
2. Re-run with `reasoning_effort` lowered (a different model condition, to be labelled), cap 32 000.
3. Cap 64 000 or more at effort high. Expected off-peak cost for the 360 main requests at about 50 k tokens each:
   about $36, above the $25 stop; Tier H turns may still not finish.

Spend so far (DeepSeek): see `runs/sprint-online-calls/deepseek_spend.jsonl` (probe, 16 smoke requests, 3 fake
test lines of $0.00003 each from a test that wrote into runs/ before it was fixed).
