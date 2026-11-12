# Iteration 7 — assignment to Claude Opus: build the sprint benchmark and run it on the local models

Work in `/Users/alberto/Documents/projects/AI-security/AI-x-epistemics` (public repository
`albertoHdzE/causalguard-epistemics`), on the existing local branch `iteration-7`.

Your R6 package was reviewed and is accepted as development evidence (480 tests pass, 21 of 21 analyses
regenerate byte-identically, six of your seven objections to the plan were right). The review is
`reports/review_r6/REVIEW.md`.

The goal is now explicit: win the Apart Research AI x Epistemics sprint (2026-11-13 to 2026-11-15) and the
fellowship path behind it. The judges score impact for AI epistemics and novelty, soundness, and clarity, on an
eight-page report. Comparing description-length priors on Boolean networks will not win that, however carefully
it is done. What can win is the thing this project has that most honesty and calibration benchmarks lack: exact
ground truth for what a body of evidence settles and what it leaves open. The project is redirected to that.

Alberto's plan, which this assignment implements: today, build the benchmark and run it in full on every local
model; tomorrow, after the director's review, run the same locked panel on two online models (DeepSeek and Claude
Opus 5.5) by changing only the model, rerun the analysis, and write the paper.

Read, in this order:

1. `delegation/iteration_7/01_SCIENTIFIC_PROTOCOL.md` — the redirect, the tasks, the gates and the stages.
2. `docs/SPRINT_AUTHORISATION.md` — what Alberto authorised and its limits.
3. `delegation/iteration_7/02_EXECUTION_PLAN.md` and `03_ACCEPTANCE_AND_REVIEW.md`.
4. `reports/review_r6/REVIEW.md`.

What you are asked to do, all of it pre-sprint and labelled so:

- **Task S (status).** Score a model's verdicts and probabilities against the exact status of each claim: settled
  true, settled false, or open. The unaided arm of the S4 harness already asks the question; add the reference
  probability, the scores and the reference rows.
- **Task P (pressure).** Add one follow-up turn in four randomised conditions: neutral, empty disagreement, demand
  to commit, and a checked challenge with a witness. Score capitulation, forced overclaiming, repair and
  discernment.
- **Smoke-test the local ladder, pilot on two models, pass the five gates, and commit the lock.**
- **Run the locked main panel on every local model that passed**, once, and analyse it.
- **Make the two online models ready**: adapters, dry runs, a connectivity check, and proof that the command-line
  route to Claude Opus 5.5 passes our prompt and nothing else. Send them no benchmark item today.
- **Verify the related work** reference by reference, and set up the report in the official template.

Rules that matter most here:

- The ground truth must be exact and doubly checked. If the two engines disagree on an item, that item fails.
- Follow-up conditions are assigned by hash, never by the model's answer.
- If a simple surface rule can read the status off an item, the benchmark is broken. The gates exist to find that
  before the main panel, not after.
- One main-panel run per model. No rerun because numbers disappoint. If you find a defect after the run, report
  it; a repaired rerun uses new worlds and a new lock version, and both are kept.
- Pilot numbers are pilot numbers.
- The API key is never printed, logged, recorded or committed.
- Every reference is opened and checked. A made-up reference disqualifies the submission.
- Mark preexisting work as preexisting everywhere. Undisclosed prior work also disqualifies.
- Tell me where this plan is wrong or will not impress the judges. You were right six times out of seven last time.

The realistic-indegree assignment in `delegation/parked/` is not part of this iteration. Leave it.

Do not stop to ask routine questions. Return what `03_ACCEPTANCE_AND_REVIEW.md` asks for.
