# R7 pre-run gates (pre-sprint)

| gate | denominator | value | threshold | pass |
|---|---|---|---|---|
| G1 ground truth | 240 main worlds, 1920 claims | 240 worlds agree | all | yes |
| G2 surface | 32 pilot worlds, 256 claims | surface balanced acc 0.512 (majority 0.333, checker 1.000) | <= 0.667 | yes |
| G3 floor/ceiling: qwen2.5:7b | 32 pilot worlds, 256 answered claims | balanced acc 0.445, acc 0.562 | > 0.05 from checker and majority (acc: checker 1.000, majority 0.617) | yes |
| G3 floor/ceiling: mistral-small-3.2-24b-instruct-2506-mlx | 32 pilot worlds, 256 answered claims | balanced acc 0.333, acc 0.652 | > 0.05 from checker and majority (acc: checker 1.000, majority 0.617) | NO |
| G4 no leak | 240 main-panel follow-ups | 240 pass | all | yes |
| G5 disjoint | 240 main worlds vs 72 pilot+smoke worlds and 148 earlier model-facing mechanisms | overlaps 0/0/0 | 0 | yes |

All gates pass: **NO**.
