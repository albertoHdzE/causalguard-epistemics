# R5 Track M — wrong assumptions, false assurances and recovery (development diagnostic)

Run `r5-m-eval-v1` (snapshot `dd193ce`), 120/120 base worlds, analysis `reports/development_r5/m_evaluation.json`.
A development probe of 10 worlds/panel used a different salt (`r5-M-v1`); the only change after it was an
accounting fix (challenge purchases per world, not per query). Stress populations by construction, **not** estimates
of how often real systems violate their assumptions.

## 1. The exact counterexample (test `test_and_counterexample_model_relative_proof_is_not_world_truth`)

Declared H: indegree ≤ 1, n = 2. Observations (0,0) from 00, 10, 01. In H both nodes are constant 0 (counts 1, 1), so
"x0 = 1 after one step from 11" is **refuted, i.e. x0 = 0 verified**. Hidden simulator x0' = x0 AND x1, x1' = 0
matches every observation and returns **1**. Under indegree ≤ 2 the target is underdetermined (2 of 4). The proof is
correct relative to H; the world is outside H. No solver error. If the only distinguishing measurement is the target
itself, no policy can tell these worlds apart from the evidence.

## 2. Panels (n = 6, declared k = 2; 8 queries per world; outcomes revealed only after decisions)

Membership used the generator's construction label and the PUBLIC emptiness of V_H(D). Acceptance logs are in the
plan payloads (`panel_members`). Rates are per scheduled query (320 per panel); intervals resample base worlds.

| Panel | Policy | Released | False verified (95 % CI of rate) | Correct-release coverage | Unnecessary blocks | Measurements |
|---|---|---:|---|---:|---:|---:|
| realizable | current | 122 | 0 | 0.381 | 0 | 0 |
| | expanded k = 3 | 4 | 0 | 0.013 | 118 | 0 |
| | robust union | 5 | 0 | 0.016 | 117 | 0 |
| | **challenge** | 122 | 0 | **0.381** | 0 | 138 |
| | abstain | 0 | 0 | 0 | 122 | 0 |
| evidence-consistent misspec. | **current** | 103 | **10** [0.013, 0.053] | 0.291 | 0 | 0 |
| | expanded k = 3 | 9 | 0 | 0.028 | 84 | 0 |
| | robust union | 9 | 0 | 0.028 | 84 | 0 |
| | **challenge** | 79 | **5** [0.003, 0.031] | **0.231** | 20 | 120 (8 class changes) |
| | abstain | 0 | 0 | 0 | 93 | 0 |
| evidence-inconsistent misspec. | current | 0 | 0 | 0 | 0 | 0 |
| | expanded k = 3 | 25 | 0 | 0.078 | 0 | 0 |
| | robust union | 128 | **5** [0.003, 0.028] | 0.384 | 0 | 0 |
| | challenge | 0 | 0 | 0 | 0 | 0 |
| | abstain | 0 | 0 | 0 | 0 | 0 |

## 3. Readings

- **False assurance is real.** When the evidence happens to fit the wrong class, the current gate's verified
  definite verdicts were false in the simulator for 10 of 103 releases (≈10 %), in 5+ of 40 worlds. Each was a
  correct proof relative to the declared class.
- **Enlarging the class is safe but nearly useless here:** expanded k = 3 and the union class make almost
  everything underdetermined (coverage 1–3 %). The robust union equals a fixed larger class in logic; its only
  differences are cost and, in the inconsistent panel, that the one-exception class still releases — and **it
  released 5 false verdicts there** (worlds with two outside nodes are outside the union too).
- **The public challenge policy improves the tradeoff:** it halves false verifications (10 → 5) while keeping 79 % of
  the current gate's correct coverage (0.231 vs 0.291), and costs nothing in coverage on realizable worlds (0.381
  both), at about 3–4 purchased measurements per world. It does not eliminate false assurance: 5 remained.
- **Inconsistent evidence is the easy case**: the current gate never released anything there.
- Abstaining on everything is perfectly safe and useless (reported as the extreme).

**Scientific outcome:** the assumption-aware challenge policy improves the risk/coverage tradeoff in this declared
stress distribution, without solving the identifiability limit. A fixed expanded class is not a practical
alternative at this evidence size.

## Limits

Small systems (n = 6, k 2→3), our generator, 40 worlds/panel, one challenge policy design (fixed before outcomes,
but its menu and ranking rule are ours). Certificates: current/expanded gate = SAT solver assertion + witness replay
(not RUP-checked in M); robust union = trusted exact computation (the common SAT checker supports uniform classes
only).
