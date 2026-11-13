# Sprint status, Friday evening (implementation agent) — not the review entry point

Entry point (draft, filled from data): `reports/REVIEW_READY_SPRINT.md`. Report draft: `report/report.pdf`.
Decisions D107–D113. Commits: `PREEXISTING_WORK.md`.

Running unattended (do not restart):
- Claude blocks: `scripts/sprint_online_blocks.sh 309fb1c claude` (log `runs/logs/sprint-online-blocks-claude.log`);
  paused on the usage window until 18:41 CST, resumes itself; provider hard stop Sat 12:00 CST.
- DeepSeek (effort low) blocks: same script, `deepseek`; stops itself at $25 upper-bound spend.
- r1 P5: `scripts/sprint_local_p5.sh` (last model of the queue).

Saturday, in order:
1. 08:00 — status of the three runs; r1 P5f coding: `python -m causalguard sprint-coding sample --add --p5-run runs/p5-r1_distill_qwen_32b-v1`;
   DeepSeek P5f coding (`--add --p5-run runs/p5-deepseek_v4_pro_low-v1`); Claude P4 coding (`--add --main-run` the
   Claude runs) once B1 is complete; Claude P5f after P5 completes. Viewer used for coding: reply + stored reasoning
   per row (see D111 for the code interpretation).
2. 12:00 — Claude hard stop (automatic); stop DeepSeek if still running (kill the block script; whatever finished stands).
3. `scripts/sprint_analyze_all.sh` twice into two directories and `cmp`; `sprint-coding summary`; `python report/fill.py`;
   `report/build.sh`; `python report/fill.py --src reports/REVIEW_READY_SPRINT.src.md --out reports/REVIEW_READY_SPRINT.md`.
4. Write the online prose (§4.4, abstract one sentence) and §7 of the review-ready file; PREEXISTING_WORK rows; push.
