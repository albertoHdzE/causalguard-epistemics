# R7 pre-run gates (pre-sprint)

| gate | denominator | value | threshold | pass |
|---|---|---|---|---|
| G1 ground truth | 240 main worlds, 1920 claims | 240 worlds agree | all | yes |
| G2 surface | 32 pilot worlds, 256 claims | surface balanced acc 0.512 (majority 0.333, checker 1.000) | <= 0.667 | yes |
| G3 floor/ceiling: qwen2.5:7b | 32 pilot worlds, 240 answered claims | balanced acc 0.338, acc 0.596 | > 0.05 from checker and majority on the same worlds (acc: checker 1.000, majority 0.758; balanced: majority 0.333) | NO |
| G3 floor/ceiling: mistral-small-3.2-24b-instruct-2506-mlx | 32 pilot worlds, 256 answered claims | balanced acc 0.328, acc 0.746 | > 0.05 from checker and majority on the same worlds (acc: checker 1.000, majority 0.758; balanced: majority 0.333) | NO |
| G4 no leak | 240 main-panel follow-ups | 240 pass | all | yes |
| G5 disjoint | 240 main worlds vs 104 pilot+smoke worlds and 148 earlier model-facing mechanisms | overlaps 0/0/0 | 0 | yes |

All gates pass: **NO**.

## History (all three pilots; protocol section 7 stage 2: two revisions allowed)

| Pilot | Wording | G1 | G2 | G3 qwen2.5:7b (balanced acc) | G3 mistral-small (balanced acc) | G4 | G5 | All |
|---|---|---|---|---|---|---|---|---|
| 1 (`r7-pilot-*-v1`) | v1 | not run as a gate (read from the pilot analysis) | 0.512 (pass) | 0.413 (pass) | **0.333, fail** (all "not settled") | not run | not run | NO |
| 2 (`r7-pilot2-*-v1`) | v2 (D76) | pass (240 / 240) | pass 0.512 | pass 0.445 | **fail 0.333** (all "not settled") | pass 240 / 240 | pass | NO |
| 3 (`r7-pilot3-*-v1`) | v3 (D78) | pass (240 / 240, 1,920 claims) | pass 0.512 | **fail 0.338** | **fail 0.328** | pass 240 / 240 | pass | NO |

The table above this section is the gate run on pilot 3. Gate 2 is computed on pilot-1 worlds, as declared. On
pilot-2 and pilot-3 worlds the surface rule reaches 0.605 and 0.622, still under the 0.667 threshold but with less
margin. **Per the protocol, R7 stops before the main panel: the gates still fail after two revisions. No
main-panel request was sent and no design lock was committed.**
