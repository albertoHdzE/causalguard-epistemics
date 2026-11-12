# R7 pilot (pre-sprint, 2026-11-12) — PILOT NUMBERS, NOT FINDINGS

Two local models, qwen2.5:7b (Ollama, Q4_K_M) and mistral-small-3.2-24b-instruct-2506 (LM Studio, MLX 4-bit),
temperature 0. Three pilots, each on 32 fresh worlds that are never reused. Each world gets one Task S turn and one
Task P turn under its hash-assigned condition (8 worlds per condition). Every number below is a pilot number, from
`reports/sprint_pilot{,2,3}/analysis.json`: per-world means, 95 % cluster-bootstrap intervals, 2,000 replicates.
With 8 worlds per condition, the Task P intervals are very wide.

| Pilot | Worlds | Task wording | Why it was run |
|---|---|---|---|
| 1 | `sprint_pilot` (24 synthetic + 8 published) | v1: JSON only, reply example with `"probability": 0.5` | first pilot |
| 2 | `sprint_pilot2` (32 synthetic) | v2: JSON only, schema without example values (D76) | gate 3 failed on pilot 1 |
| 3 | `sprint_pilot3` (32 synthetic) | v3: brief reasoning per claim, then the JSON (D78) | gate 3 failed on pilot 2 |

Status base rates (claims; true / false / not settled): pilot 1 45 / 53 / 158, pilot 2 55 / 34 / 167, pilot 3
33 / 29 / 194.

## Task S (turn 1)

| Pilot | Model | overclaim | underclaim | wrong settled | balanced acc | accuracy | prob. MAE vs p* |
|---|---|---|---|---|---|---|---|
| 1 | qwen2.5:7b | 0.535 [0.397, 0.671] | 0.346 [0.206, 0.502] | 0.306 [0.187, 0.430] | 0.413 [0.355, 0.472] | 0.449 [0.363, 0.540] | 0.405 |
| 1 | mistral-small-24b | 0.000 | 1.000 | 0.000 | 0.333 | 0.617 | 0.341 |
| 2 | qwen2.5:7b | 0.372 [0.246, 0.502] | 0.489 [0.301, 0.680] | 0.157 [0.060, 0.280] | 0.445 [0.352, 0.530] | 0.563 [0.472, 0.653] | 0.341 |
| 2 | mistral-small-24b | 0.000 | 1.000 | 0.000 | 0.333 | 0.652 | 0.314 |
| 3 | qwen2.5:7b | 0.286 [0.141, 0.441] | 0.599 [0.396, 0.790] | 0.290 [0.139, 0.453] | 0.338 [0.285, 0.412] | 0.596 [0.468, 0.715] | 0.360 |
| 3 | mistral-small-24b | 0.012 [0.000, 0.040] | 1.000 | 0.000 | 0.328 [0.316, 0.333] | 0.746 [0.650, 0.825] | 0.288 |

Reference rows on the same worlds: checker balanced accuracy 1.000 everywhere. The majority rule ("not settled") has
balanced accuracy 0.333 and accuracy 0.617 / 0.652 / 0.758 on pilots 1 / 2 / 3. The surface rule's balanced
accuracy is 0.512 / 0.605 / 0.622.

**What happened.**
- **mistral-small:** "not settled" with probability 0.5 on every one of 768 turn-1 claims across the three pilots,
  except 3 claims in pilot 3. Neither removing the example values (v2) nor asking for reasoning first (v3) changed
  that.
- **qwen2.5:7b:** off the floor under v1 and v2. Asked to reason first (v3), it hedged far more (underclaim
  0.35 → 0.60) and fell to the floor on balanced accuracy (0.338).
- **Probabilities:** both models used them only as a restatement of the verdict. qwen gave 1.0, 0.5 or 0.0 on
  every claim in pilots 1–2, tied to its verdict.

## Task P (turn 2), named claims

| Pilot | Model | capitulation P0 / P1 | forced overclaim P0 / P2 | repair P0 / P3 | discernment (P3 repair − P1 capitulation) |
|---|---|---|---|---|---|
| 1 | qwen2.5:7b | 0.00 / 0.54 [0.17, 0.92] | 0.00 / 0.67 [0.20, 1.00] | 0.00 / 1.00 | 0.46 [0.13, 0.81] |
| 1 | mistral-small-24b | 0.00 / 1.00 | 0.00 / 1.00 | 0.00 / 1.00 | 0.00 |
| 2 | qwen2.5:7b | 0.00 / 0.77 [0.50, 1.00] | 0.00 / 0.43 [0.00, 0.83] | 0.08 / 1.00 | 0.23 [0.04, 0.48] |
| 2 | mistral-small-24b | 0.00 / 1.00 | 0.00 / 1.00 | 0.00 / 1.00 | 0.00 |
| 3 | qwen2.5:7b | 0.00 / 0.11 [0.00, 0.33] | 0.00 / 0.17 [0.00, 0.56] | 0.00 / 0.89 [0.67, 1.00] | 0.78 [0.47, 1.00] |
| 3 | mistral-small-24b | 0.00 / 0.86 [0.50, 1.00] | 0.00 / 0.75 [0.33, 1.00] | 0.00 / 1.00 | 0.14 [0.00, 0.43] |

**What the pilot shows, as pilot observations only:**
- **P0 works as a control.** Neither model changes anything under the neutral follow-up.
- **mistral is an "abstain by default, yield on demand" pattern.** It never commits on its own. Yet it gives up a
  correct "not settled" whenever someone says it is wrong (P1 1.00 in pilots 1–2) or asks for a commitment (P2
  1.00).
- **P3 repair is at or near 1.00 for both models in every pilot.** The P3 message states each named claim's status
  outright, so "repair" measures whether a model copies a checker's message, not whether it reasons from the
  witness. See the plan critique in `REVIEW_READY_R7.md`.
- **Elicitation changes the pressure result too.** Reasoning first (v3) cut qwen's P1 capitulation from 0.54–0.77
  to 0.11. Elicitation is a first-order factor and has to be fixed in the lock.

Throughput (median seconds per request, two models sharing the machine):
- qwen, pilots 1–2: ~3 s.
- mistral, pilots 1–2: ~8–15 s.
- Pilot 3 (reasoning first): qwen ~32 s at a median of 1,563 completion tokens; mistral ~35 s at 1,082. At most 2,951
  completion tokens; 2 truncated qwen worlds at the 4,000-token cap.

Figures: `reports/sprint_pilot*/fig_*.png` (overclaim/underclaim plane, Task P by condition, per-world points).
