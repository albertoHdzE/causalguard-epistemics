# R7 smoke gate (pre-sprint)

Each candidate local model: 4 smoke worlds (smoke manifest, hash order), Task S and one Task P turn = 8 requests. Pass: valid claim answers >= 90%, no truncated response, no failed item.
A claim answer is valid when its verdict is valid; the probability is reported separately (D73).

| model | requests | valid answers | with probability | full 8/8 replies | truncated | median s / request | median / max completion tokens | max prompt tokens | quantization | pass | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|
| llama-3.3-70b-instruct | 8 | 64/64 (100%) | 64 | 8/8 | 0 | 24.8 | 202.0 / 204 | 1268 | 4bit | yes | - |
