# R5 Track A — AI as an investigator (bounded two-model pilot)

Runs (snapshot `dd193ce`): deterministic `r5-a-det-cal-v1` (64 calibration worlds), `r5-a-det-eval-v1` (64);
AI calibration `r5-a-ai-cal-*-v1` (failed validity gate, R5-02) and `-v2` (passed); AI evaluation
`r5-a-ai-eval-qwen25_7b-v2`, `r5-a-ai-eval-mistral_small_24b-v2` (64/64 each). Analyses
`reports/development_r5/a_*.json`, `a_ai_error_breakdown.txt`. Pilot, not a powered study.

## Design (locked in `docs/R5_DESIGN_LOCK.json`)

64 shared evaluation worlds (8 per locked G stratum), public evidence of 8 one-step observations, target = first
scheduled query underdetermined by the public evidence (population restriction, all 64 accepted on the first index
tried per slot). Menu of 16 one-node measurements (4 target-node near the query start, 4 other nodes near it, 8 random;
target-equivalent excluded). Both arms receive the same exact readout (uniform-H posterior of the target, per-item
P(outcome) and exact EIG); the D arm adds a named-analytic mechanism view, the generic arm per-node counts. ≤ 8
physical attempts per episode; temperature 0, seed 0.

## Deterministic baselines (offline)

| Policy (backend D) | resolved@1 | @2 | @4 (calibration) | @4 (evaluation) |
|---|---:|---:|---:|---:|
| **exact EIG (selected on calibration)** | 0.313 | 0.625 | 0.781 | **0.766** |
| disagreement (untargeted) | 0.016 | 0.031 | 0.141 | 0.125 |
| random | 0.063 | 0.109 | 0.156 | 0.188 |
| oracle lookahead (privileged, sees outcomes) | 0.375 | 0.672 | — | 0.766 |

D and generic B replay identically: 192/192 policy episodes with identical purchases and verdicts (exact backends
agree; only cost differs). EIG already matches the privileged oracle at budget 4 on this menu.

## Primary: resolved@4, AI+D minus EIG on D (paired by world, 10,000 world-bootstrap replicates)

| Model | AI+D @4 | EIG @4 | **Difference [95 % CI]** | AI+generic @4 | D − generic (AI) |
|---|---:|---:|---|---:|---|
| mistral-small-3.2-24b | 0.656 | 0.766 | **−0.109 [−0.188, −0.047]** | 0.656 | 0.000 [−0.047, 0.047] |
| qwen2.5:7b | 0.422 | 0.766 | **−0.344 [−0.469, −0.234]** | 0.422 | 0.000 [−0.094, 0.094] |

**Scientific outcome: adverse.** Both models resolve fewer targets than the exact-EIG controller they are given.
The representation (D vs generic) makes no difference to the AI.

## Why (all calls, raw responses and invalid actions retained in the run records)

| | qwen D | qwen B | mistral D | mistral B |
|---|---:|---:|---:|---:|
| valid action rate | 1.00 | 1.00 | 1.00 | 1.00 |
| physical attempts | 171 | 159 | 203 | 206 |
| purchases / possible 256 | 107 | 95 | 139 | 142 |
| purchases equal to the EIG argmax | 66/107 | 62/95 | 105/139 | 107/142 |
| **stopped while the target was still underdetermined** | 35 | 37 | 18 | 18 |
| stopped after resolution | 26 | 27 | 41 | 41 |
| unsupported definite assertions (readout underdetermined; all blocked by the gate) | 73 | 65 | 0 | 0 |
| … of which the asserted value was also false in the simulator | 7 | 11 | 0 | 0 |
| false uncertainty (said underdetermined when determined) | 0 | 0 | 0 | 0 |
| final forecast Brier (AI-stated / exact readout) | 0.065 / 0.066 | 0.060 / 0.040 | 0.037 / 0.037 | 0.035 / 0.035 |
| server latency (s) / tokens | 629 / 541k | 521 / 422k | 1238 / 715k | 1046 / 647k |

- The main failure is **premature stopping**: the models end the investigation with purchases left and the target
  unresolved, then often (qwen) claim certainty anyway. Mistral mostly copies the EIG ranking when it buys.
- The gate blocked every unsupported definite claim; none was released. Unlike R4 (226/228 false uncertainty), the
  dominant AI error here is **false certainty**, i.e. the confident-error case the gate is meant for — 138 qwen
  claims, 18 of which would also have been wrong in the simulator.
- When the AI reports a probability, Mistral reproduces the readout; Qwen's B arm forecasts are worse than the readout.

## Accounting

Calls: calibration v1 250 + v2 92 = 342 (≤ 512), evaluation 739 (≤ 2,048), repair 0; total **1,081 / 3,072**.
Model-server execution (sum of request latencies, upper bound): calibration ≈ 0.25 h, evaluation 0.95 h, loads < 1 min.

## Interpretation and limits

In this task the exact controller is already near the oracle, so the AI could at best tie; it lost by stopping early
and overclaiming. This is evidence for using the deterministic inference/investigation layer and testing the AI in
other roles (formulating claims, choosing among assumptions, explaining checked results), not for an AI-led
investigator. Two local models, 64 worlds, one prompt version (v2, one validity repair of the stop action on
calibration); no prompt tuning on evaluation.
