# R6 Track A2 — gate in the loop: pilot design (written before any A2 request)

Status: development pilot, 2026-11-12. Repairs R5-F3 (the gate checked the AI's verdict after the episode).

## Loop
`r5/investigation.py::ai_episode(gate_loop=True)`: when the model **stops** (`measure: null`) with a definite verdict
(entailed / refuted) and purchases and request attempts remain, the common gate checks it on the current evidence.
If it is not verified, the harness appends "Checked and rejected: <reason>; n purchase(s) left. You may buy a
measurement, or stop with a verdict the evidence supports." and the same turn continues. The reason is taken from the
target's own status ("the evidence does not determine the target" / "the evidence contradicts this verdict").
A stop with "underdetermined" is never rejected, and the model is never forced to buy. If the rejection would use the
last allowed attempt, the stop is accepted as in R5. Same prompt v2, same exact readout, same 8-attempt cap.

## Population and arms
- 32 fresh worlds, salt `r6-A2-v1`, 4 per stratum (`population("pilot_r6", 4)`), never used before.
- Models: qwen2.5:7b (Ollama, num_ctx 16384) and mistral-small-3.2-24b-instruct (LM Studio, context 16384), both as R5.
- Backend arm D only. The generic arm B is dropped before any request to fit the 512 allocation
  (R5: the backends give identical readout numbers; protocol §6 permits this).
- Arms per model: loop (`gate_loop: true`) and control (the unchanged R5 harness), same worlds, same seeds.
- Smoke: 4 worlds on salt `r6-A2-smoke-v1`, loop arm, both models. Gate: ≥ 90 % parsable actions, else stop and
  report.
- Deterministic policies (EIG, random, disagreement, privileged oracle) on the same 32 worlds (`configs/r6/a2_det.json`),
  no model calls.

## Accounting
Every physical attempt is a line in `runs/r5-calls/ledger.jsonl` with phase `A2`, phase cap 512, global cap 3,072
(1,081 used before R6). Order: smoke (both models), then qwen control, qwen loop, mistral control, mistral loop.
Estimate from R5 attempt rates: about 470 attempts.

## Endpoints
- Primary, per model: resolved@4 (loop) − resolved@4 (control), paired by world, world-bootstrap 95 % interval.
  resolved@b = a definite verdict stated at budget b that the common gate verifies.
- Secondary: both arms against EIG on the same worlds; unsupported definite claims (stated definite verdicts at
  b = 4 that the gate does not verify); purchases; attempts; rejections per episode; stops with a correct
  "underdetermined" verdict reported separately from overclaiming.

## Predictions (from R5 behaviour, recorded before any A2 request)
- qwen2.5:7b: in R5 about 40 % of its episodes stopped with an unsupported definite verdict. The loop should
  remove most unsupported claims at b = 4 and raise resolved@4 by a small amount, because a rejected model can only
  resolve by buying the right measurements.
- mistral-small: in R5 it never stopped with an unsupported definite verdict; its errors were premature
  "underdetermined" stops, which the loop does not touch. Prediction: loop − control ≈ 0.
- Neither model is predicted to reach EIG.
