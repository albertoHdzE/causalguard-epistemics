# Iteration 8 — assignment to Claude Opus: the sprint (online frontier runs, the verify-first condition, analysis, report)

Work in `/Users/alberto/Documents/projects/AI-security/AI-x-epistemics`, branch `sprint` (created by the director
from your `66e4065`; the director's review and this assignment are the first commit on it).

Your R7b work is accepted (`reports/review_r7b/REVIEW.md`). I verified the lock time against the first request of
every run, the per-run item counts, the ledger, and the worked example line by line. All seven of your objections
hold; two become work in this iteration.

The sprint is open. Deadline Sunday 15 Nov 23:59 AoE (Monday 16 Nov 05:59 CST). Internal deadlines: a review-ready
draft to me by **Saturday 14 Nov 20:00 CST**; final PDF **Sunday 15 Nov 18:00 CST**. From now on everything you
commit is sprint work and must be listed with its commit in the sprint section of `PREEXISTING_WORK.md`.

Read, in this order:

1. `reports/review_r7b/REVIEW.md`
2. `delegation/iteration_8/01_SPRINT_ADDENDUM_AND_PLAN.md` — the decisions, the P5 design, lock v2, the order of
   work, the report plan, the ceilings, the stop conditions and the return contract
3. `docs/SPRINT_AUTHORISATION.md` (addendum of 2026-11-13)
4. `reports/R7B_ONLINE_READINESS.md`

Decisions already taken, so do not reopen them:

- **Reasoning storage is approved** as lock addendum v2. Store the full reasoning text wherever the provider returns
  it (DeepSeek `reasoning_content`; the Claude CLI transcript's thinking blocks, which `audit_wire` already reads; the
  LM Studio field for r1 in future runs). Scoring never reads it; prove that with a replay test on a stored pilot-4
  run with the field present and stripped. If Claude's transcript carries no thinking text, record
  `reasoning_available: false` and report it; do not spend more than the two remaining probes finding out.
- **P5, verify-first, is adopted** as a pre-registered secondary on the 60 never-shown R7 main worlds, Tier W only,
  30 valid + 30 forged, all eight models. The wording, schema, scorer, gates and my predictions are fixed in
  `01_SPRINT_ADDENDUM_AND_PLAN.md` §2. Write your own 3–5 predictions into lock v2 before the first P5 or online
  request.
- **Online caps** 520 requests per model; **DeepSeek spend ceiling $30**, stop at $25. Claude on the subscription,
  cost recorded per session.
- **qwen2.5:72b** runs only under the idle-GPU rule (decision 4). It never delays the analysis or the report.
- **Headline** is the forged-check result with P5 as its control. The report leads with it. Title and section plan
  are in §5 of the addendum.

What matters most:

- **Lock v2 before the first online request and before the first P5 request.** One commit, pushed. Every v1 key
  byte-identical, tested.
- **Smoke before main**, for each online model: parse, isolation audit, cost record, reasoning stored. One harness
  repair allowed; then stop and report.
- **Every number in the report comes from the analysis JSON through `report/fill.py`.** No hand-typed number. The
  build fails if a number in the text is not in the analysis outputs.
- **Read the replies and the stored reasoning, not only the scores.** The pre-registered coding sheet and the
  quotations, with item keys, are what make the "does not verify" claim stand or fall.
- **Say what is pre-sprint and what is sprint work**, in the introduction, in Appendix B with commits, and in the
  README. Undisclosed prior work disqualifies.
- **Report predictions against outcomes, including mine that fail.** Do not change a threshold, a wording or a panel
  to make a prediction come true.
- Keep both local servers busy while the online runs proceed (local P5 first), but the locked online runs have
  priority over any supplement.
- The account e-mail and the key appear in no file; the scan runs before every push.

You have latitude on the implementation of reasoning storage, the P5 scorer's normalisation details (within §2), the
figures, and the prose of the report. Record every choice in `DECISIONS.md` (D90 onward). If a part of this design
is wrong, say so with evidence and take the better route when it does not weaken ground truth, the lock, the
pre-registration or disclosure.

Do not stop to ask routine questions. Stop only at the stop conditions of §7. Return what §8 asks for, with
`reports/REVIEW_READY_SPRINT.md` as the entry point.
