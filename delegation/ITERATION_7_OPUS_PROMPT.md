# Iteration 7 — assignment to Claude Opus

Work in `/Users/alberto/Documents/projects/AI-security/AI-x-epistemics` (public repository
`albertoHdzE/causalguard-epistemics`), on the existing local branch `iteration-7`.

Your R6 package was reviewed and is accepted as development evidence. It reproduced: all tests pass and 21 of 21
analyses regenerate byte-identically. Six of your seven objections to the plan were right, including the budget
rule, the population limit and the missing held-out-source test. Your sizing rule for budgets is now the protocol's.

The review also found why three rounds have produced effects below 0.01. Inside H(n, 3) a node has at most eight
rows, so a few observations settle it under any prior. Meanwhile about a third of the nodes in the published
corpus have four or more regulators, almost no published model fits inside indegree ≤ 3, and at indegree 4–6
nearly all published rules are short (nested canalizing or unate). R7 moves the experiment to where a compact
description can matter and where the published models are.

Read, in this order:

1. `reports/review_r6/REVIEW.md` — the review, including which of your objections were accepted.
2. `delegation/iteration_7/01_SCIENTIFIC_PROTOCOL.md`, `02_EXECUTION_PLAN.md`, `03_ACCEPTANCE_AND_REVIEW.md` — your
   assignment. They are binding.

What you are asked to do, in sustained resumable sessions:

- **Reproduce the corpus census** with tested code (WP0). The director's table comes from a throwaway script. Find
  its errors if it has any, and apply the population gate.
- **Track K, the main experiment.** Whole published models, wiring public, logic hidden, nodes up to six
  regulators. Exact predictors: counting (`uniform`), the field-standard monotonicity assumption (`unate`), a
  literature class (`ncf`), a generic compact code (`formula`) and our analytic code (`cgh`). Calibrate, lock,
  evaluate once.
- **Track V.** On the same worlds, measure what can be checked under each declared assumption and how often a
  checked claim is wrong because the assumption is false on a real model.
- **Track L, a bounded pilot, last.** How a local language model's unaided guess compares with these predictors,
  and whether our output helps it.
- **Publish** prerelease `v0.7.0-dev` with the R7 review package.

Authority and limits: development only. No confirmatory run, no freeze record, no paid inference, no weight
changes. At most 400 new model requests inside the unchanged global ceiling of 3,072 (1,498 used). Offline: 48
CPU-hours, four workers. Model server: 2 hours. These are ceilings, not targets.

Rules that matter most here:

- Every predictor is exact, normalised and has full support. Test each against brute force and against an oracle
  that shares no code with it. If one cannot be computed exactly at six regulators, lower the limit for all of them
  together.
- Nothing called a description length may use fitted frequencies. XDC-EB is a plug-in estimate and is not a
  candidate for our method in R7.
- `cgh` is a port: raise the limit of the existing analytic catalogue. Do not add families or re-weight it.
- Choose budgets, the comparator and ε on calibration groups only, by the stated rules. Say whether each chosen
  value sits at the edge of its range.
- Report the comparisons against the generic compact code and against the literature class with the same
  prominence as the primary. If our code ties them, that is the finding.
- Render the object before quoting a number about it. Every report needs its figures.
- Date work by timestamp as pre-sprint or sprint work. The sprint runs 2026-11-13 to 2026-11-15 and requires
  disclosure of preexisting work.
- If you think the director's method or plan is wrong, say so in the return with evidence. Last time that was the
  most useful part of your report.

Priority if time runs short: a complete Track K with a clean lock first, then Track V, then the release package,
then Track L.

Do not stop to ask routine questions. Finish every independent track even if another is blocked, and record the
exact block. Return what `03_ACCEPTANCE_AND_REVIEW.md` asks for.
