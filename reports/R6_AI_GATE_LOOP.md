# R6 Track A2 — the gate in the loop (bounded repair pilot for R5-F3)

Status: development pilot, 2026-11-12. Design written before any request: `docs/R6A2_DESIGN.md` (commit `2dcf172`).
All runs executed from snapshot `2dcf172`. Analysis: `python -m causalguard analyze-r5 --track a2 --run <control>
--run <loop> ... --det-run runs/r6-a2-det-v1` → `reports/development_r6/a2_gate_loop.json`.

## What changed
In R5 the gate checked the AI's verdict after the episode, so a rejected claim never reached the model. Here, when the
model stops with a definite verdict the gate does not verify, and purchases and attempts remain, the model is told
"Checked and rejected: <reason>; n purchase(s) left" and the same turn continues. "Underdetermined" stops are never
rejected, and the model is never forced to buy.

## Population, arms, accounting
32 fresh worlds (salt `r6-A2-v1`, 4 per stratum); backend D only (generic arm B dropped **before** any request to fit
the allocation; R5 showed both backends give identical numbers). Smoke gate: 4 worlds per model, 100 % parsable
actions (13/13 qwen, 12/12 mistral), passed.

| Run | Attempts | Invalid |
|---|---|---|
| smoke qwen / mistral (loop) | 13 / 12 | 0 / 0 |
| qwen2.5:7b control / loop | 79 / 105 | 0 / 0 |
| mistral-small-3.2-24b control / loop | 104 / 104 | 0 / 0 |
| **Total A2 (ledger phase `A2`)** | **417 of 512** | 0 |

Global ledger: 1,498 of 3,072 (1,081 before R6). Model-server time about 25 minutes (01:52–02:17 UTC), ceiling 3 h.
Every episode in every arm completed (no cap hit).

## Results (32 paired worlds per model)

| | qwen2.5:7b control | qwen2.5:7b loop | mistral control | mistral loop | EIG (no model) |
|---|---|---|---|---|---|
| resolved@4 (gate-verified definite verdict at 4 purchases) | 12 | 13 | 25 | 25 | 25 |
| unsupported definite verdict at b = 4 | 15 | 2 | 0 | 0 | — |
| unsupported definite verdicts, all budgets 0/1/2/4 | 42 | 2 | 0 | 0 | — |
| stopped early with a correct "underdetermined" | 4 | 14 | 4 | 4 | — |
| rejections returned to the model | — | 15 | — | 0 | — |
| purchases | 47 | 58 | 72 | 72 | — |
| final Brier of the AI's stated p | 0.071 | 0.045 | 0.014 | 0.014 | — |

**Primary (loop − control, resolved@4, world bootstrap):**
- qwen2.5:7b **+0.031 [0.000, 0.094]** (one world gained, none lost).
- mistral-small **0.000 [0, 0]**: never rejected, and its loop and control transcripts were identical
  (104 attempts each), which also confirms the runs are deterministic at temperature 0.

**Unsupported definite claims at b = 4**, loop − control: qwen **−0.41 [−0.59, −0.25]** (15 → 2); mistral 0.

**Against EIG on the same worlds** (resolved@4, AI − EIG): qwen control −0.41 [−0.59, −0.25], loop −0.38
[−0.56, −0.22]; mistral 0.00 in both arms (25/32 each).

## Reading
- With the gate in the loop, Qwen almost stopped making claims the evidence does not support (42 → 2 across
  budgets). But the loop did not make it a better investigator: after a rejection it mostly retreated to a correct
  "underdetermined" and stopped (early stops 4 → 14) instead of buying the measurement that would settle the
  question. Resolution rose by one world.
- Mistral's errors in R5 were premature "underdetermined" stops, which the loop does not touch (as predicted). In
  these 32 fresh worlds it tied EIG at four purchases (25/32) and lagged it at two (0.56 vs 0.63).
- The predictions recorded before the run held for both models.
- What this supports: an exact gate in the loop turns a weak model's overclaiming into honest uncertainty. What it
  does not show: that feedback makes a weak model investigate well. Pilot scale: 32 worlds, two local models, one
  backend.
