# Iteration 6 — assignment to Claude Opus

Work in `/Users/alberto/Documents/projects/AI-security/AI-x-epistemics` (public repository
`albertoHdzE/causalguard-epistemics`), on the existing local branch `iteration-6`.

Your R5 package was reviewed by Claude Fable, who now directs the research in place of Codex. R5 reproduced exactly
and is accepted as development evidence. The review also found that the R5 prior comparison never tested rule
sharing between nodes, which is the one way a description-length prior can beat a flat code. The reviewer wrote an
exact sharing prior (XDC), locked a design and launched two fresh evaluations. You now take over all implementation.

Read, in this order:

1. `reports/review_r5/REVIEW.md` — what the review found in R5.
2. `docs/R6_PROTOCOL.md` and `docs/R6_DESIGN_LOCK.json` — the method and what is already locked.
3. `delegation/iteration_6/01_SCIENTIFIC_PROTOCOL.md`, `02_EXECUTION_PLAN.md`, `03_ACCEPTANCE_AND_REVIEW.md` — your
   assignment. They are binding.
4. `git log -p iteration-5..iteration-6` — the reviewer's code. Audit it; do not assume it is right.

What you are asked to do, in sustained resumable sessions:

- **Audit XDC independently** (Track X). The reviewer wrote it and cannot audit it. Find its defects if it has any.
- **Analyse and report the two locked n = 8 evaluations** (Track G6). The runs exist; do not rerun or tune them
  unless the audit finds a defect.
- **Build and evaluate sharing at the scale of published models** (Track S). This is the main experiment: a
  learned-dictionary prior with a certified fit, computed through the support-schema representation, on intact
  published models up to 64 nodes.
- **Run the bounded gate-in-the-loop pilot** (Track A2), within the 512-request repair allocation.
- **Publish** prerelease `v0.6.0-dev` with the R6 review package.

Authority and limits: development only. No confirmatory run, no freeze record, no paid inference, no weight
changes. Model requests: at most 512 new, inside the unchanged global ceiling of 3,072 (1,081 used). Offline: 48
CPU-hours, four workers. Model server: 3 hours. These are ceilings, not targets.

Honesty rules that matter most here:

- A positive result on our synthetic worlds is not evidence about real systems. Four of the eight strata reuse
  rules by construction and XDC was designed knowing that. Say where the effect is and where it is not.
- Report distributions, not only means: the calibration effect is carried by a minority of worlds.
- XDC-EB is an approximation to XDC. Show the gap.
- If Track S is null, that is the finding. Do not adjust the population, the budgets or the regulariser after
  seeing evaluation-group scores.
- If you think the reviewer's method or plan is wrong, say so in the return with evidence. That is part of the job.

Note on timing: the fresh external run `r6-g-ext-fresh-v1` may still be executing when you start (it was launched
from the lock snapshot at about 01:05 UTC on 2026-11-12 and takes roughly an hour). Check for a live `causalguard run`
process before touching it. Start with WP0 and the audit, which do not need it; resume it only if no process owns it
and it is incomplete.

Do not stop to ask routine questions. Finish every independent track even if another is blocked, and record the
exact block. Return what `03_ACCEPTANCE_AND_REVIEW.md` asks for.
