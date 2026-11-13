# Iteration 9 — assignment to Claude Opus: the two online decisions, the Claude resume, the analysis and the report

Work in `/Users/alberto/Documents/projects/AI-security/AI-x-epistemics`, branch `sprint`, from the director's commit
that follows your `242184f`.

Your day-1 work is accepted. I verified lock v2 (09:15:16 CST) against the first P5 request (09:17:12) and the
first online request (09:18:03); the five finished P5 runs (60/60 each); the Claude main run (6 ok, 173
`usage_limit_reached`, 1 timeout); and the DeepSeek spend record, which has a defect: 12 of 20 lines carry only
`usd_upper` ($1.52 in total) and no `usd` ($0.50 on the other 8). Fix it as described.

Both decisions are taken. Read `delegation/iteration_9/01_ONLINE_DECISIONS_AND_DAY2_PLAN.md` in full and
`DECISIONS.md` D101–D106; your decisions continue from D107.

In one sentence each:

1. **DeepSeek**: the high-effort failure is a finding, reported with its token counts. One further smoke, as a new
   labelled model condition (reasoning effort medium; thinking off only if the API has no effort step), cap 32 000,
   same pass rule. Pass → main + P5 in the priority order, 8 workers, upper-bound spend stop at $25. Fail → out.
2. **Claude**: lock amendment v2-a3 fixes the priority order (Tier W P3+P4 → P5 → Tier W P0–P2 → Tier H P3+P4 →
   Tier H P0–P2; locked hash order inside each block). The runner pauses on the first usage-limit rejection,
   records it outside the 520 cap, and resumes at the window reset; 2 workers. **Hard stop for Claude benchmark
   requests: Saturday 12:00 CST.** The benchmark has the window to itself from your stop tonight (target 22:00)
   until 08:00. Cells are reported with n finished / n planned; contrasts only when both cells have ≥ 12 worlds.
3. The report stands on the six local models; online cells slot in through `report/fill.py`. Write the draft from
   local data first.
4. P5 descriptors D93/D95: report (sensitivity row; visible-contradiction split, post-hoc), do not repair.
5. qwen2.5:72b is out. r1 P5 finishes on its own.

Order of work: amendment v2-a3 (priority order, usage-limit pause, spend-record fix, DeepSeek medium config), tests,
commit, push → resume Claude and run the DeepSeek smoke → analysis, figures, fill, report text from local data,
coding of the local sample tonight → stop at 22:00 → Saturday: online coding sample, appendices, 12:00 freeze,
regenerate twice, build PDF and DOCX, `PREEXISTING_WORK.md` rows, README, push → `reports/REVIEW_READY_SPRINT.md`
to me by **Saturday 20:00 CST**.

What matters most is unchanged from iteration 8: lock before request; every number through `fill.py`; read the
replies and the stored reasoning; pre-sprint against sprint work with commits; predictions against outcomes
including the ones that fail (a prediction whose cell has fewer than 12 worlds is "not testable in this run"); the
key and account e-mail in no file; the scan before every push. Say "thinking summaries" wherever you mean the
stored Claude reasoning.

Stop conditions: iteration 8 §7 plus the ones in §6 of the new file. Do not stop to ask routine questions. Return
what §7 of the new file asks for.
