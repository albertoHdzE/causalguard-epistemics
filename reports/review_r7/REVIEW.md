# Director's review of R7 (pre-sprint, 2026-11-12)

Reviewed at `a58066d` on branch `iteration-7`.

## Decision

**Accept the build. The stop before the main panel was correct. Do not run option A. Redesign before the main
panel (R7b).** The pilot replies show that the task as built cannot be worked out by the models, so a panel on it
would mostly measure guessing. R7b adds a tier where the status can be derived by hand, and a forged-check
condition.

## What I checked

| Check | Result |
|---|---|
| Full test suite | 498 tests pass (480 earlier + 18 new), 0 fail |
| Pilot analyses regenerated from raw runs (pilots 1 and 3) | identical to the committed JSON except the label argument I did not pass |
| Ledger | 466 requests, all phase `SPRINT`; 0 on a main-panel world |
| Key and account e-mail | in no tracked file and in no file under `runs/`, `reports/`, `artifacts/` |
| Assignment of follow-up conditions | `population.assign` reads the world key and salt only |
| Raw replies | read for both pilot models under the reasoning-first wording (below) |

## Findings

**R7-F1. Gate 3 was my error.** It tested a model, not the task. A constant "not settled" policy scores 1/3
balanced accuracy on any worlds, so no revision could pass it. Opus's objection 1 is right.

**R7-F2. The replies show the hidden-wiring task is beyond these models, and how each one fails.** Same world,
reasoning-first wording (`pilot3|synthetic|shared_motifs|1|`):

- qwen2.5:7b lists evidence rows it did not use ("#01, #03, … #19" for one claim, "#02, #04, … #20" for the next)
  and concludes "no evidence contradicts this claim", verdict true. Seven of eight claims are answered "true";
  three of those are settled false. It treats "consistent with the evidence" as "settled by the evidence".
- mistral-small looks for an evidence row with the same start state, finds none, and answers "not settled". Claims
  are built on never-observed start states, so this rule always returns "not settled". It is a rule, not a
  collapse.

Working out the status here means finding, for each node, every function of at most three of eight nodes that fits
16 rows. No model in the pilot attempts it. On this tier, a main panel would measure which default a model falls
back on. That is worth a contrast tier, not the whole benchmark.

**R7-F3. The JSON-only wording gives non-reasoning models no place to work.** The two online models reason before
they answer. A local-versus-online comparison under JSON-only would confound the model with access to a scratch
space. The locked wording must be reasoning-first for every model. Opus's objection 4 is right, and the cost is
real: fewer worlds and half panels for slow models.

**R7-F4. P3 hands over the answer.** Repair of 0.89–1.00 measures copying. Opus's objection 2 is right. A forged
check is needed, and on the hidden-wiring tier neither the real nor the forged check can be verified by the
reader, so that tier can only measure deference. Discernment needs a tier where a check can be verified.

**R7-F5. Probability error is secondary.** Both models return 0, 0.5 or 1. Opus's objection 3 is right.

**R7-F6. Gate 2 should be computed on the main-panel items.** The surface rule needs no model. Opus's objection 6
shows the pilot-1 figure was the favourable one (0.512 against 0.605 and 0.622).

**R7-F7. The 575 fixed tokens on the command-line route are acceptable with disclosure.** They are identical for
every item and carry no benchmark information. The audit must keep hashes and lengths of those blocks, never
their text, because one of them contains the account e-mail and the repository is public.

## Opus's objections

| # | Objection | Verdict |
|---|---|---|
| 1 | Gate 3 tests a model, not the task | Correct |
| 2 | P3 hands over the answer; add a wrong-checker condition | Correct, and it needs a tier where a check can be verified |
| 3 | Probability error should be secondary | Correct |
| 4 | Elicitation is first-order | Correct; I draw the opposite conclusion on which wording to lock |
| 5 | A single honest summary is needed | Correct |
| 6 | Gate 2's margin is thin | Correct |

## Direction

`delegation/ITERATION_7B_OPUS_PROMPT.md`. Two tiers: wiring given (status derivable by table lookup, the primary
tier) and wiring hidden (the contrast tier, already built). Five follow-up conditions including a forged check.
Reasoning-first wording. One lock, then the local panel overnight.
