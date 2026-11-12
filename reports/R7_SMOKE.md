# R7 smoke gate (pre-sprint)

Each candidate local model: 4 smoke worlds (smoke manifest, hash order), Task S and one Task P turn = 8 requests. Pass: valid claim answers >= 90%, no truncated response, no failed item.
A claim answer is valid when its verdict is valid; the probability is reported separately (D73).

| model | requests | valid answers | with probability | full 8/8 replies | truncated | median s / request | median / max completion tokens | max prompt tokens | quantization | pass | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|
| google/gemma-3-4b | 8 | 0/64 (0%) | 0 | 0/8 | 0 | 2.1 | 122.0 / 125 | 1452 | 4bit | NO | valid answers 0/64 < 90% |
| google/gemma-3-4b | 8 | 64/64 (100%) | 0 | 8/8 | 0 | 1.1 | 122.0 / 125 | 1452 | 4bit | yes | - |
| qwen2.5:7b | 8 | 64/64 (100%) | 64 | 8/8 | 0 | 2.8 | 206.0 / 268 | 1506 | Q4_K_M | yes | - |
| gemma-4-12b-it-mlx | 8 | 48/64 (75%) | 48 | 6/8 | 0 | 11.4 | 193.0 / 1121 | 2252 | 4bit | NO | valid answers 48/64 < 90% |
| gemma-4-12b-it-mlx | 8 | 64/64 (100%) | 64 | 8/8 | 0 | 6.5 | 195.0 / 1247 | 2378 | 4bit | yes | - |
| mistral-small-3.2-24b-instruct-2506-mlx | 8 | 56/64 (88%) | 56 | 7/8 | 0 | 14.2 | 262.0 / 262 | 1560 | 4bit | NO | valid answers 56/64 < 90% |
| mistral-small-3.2-24b-instruct-2506-mlx | 8 | 64/64 (100%) | 56 | 8/8 | 0 | 8.5 | 262.0 / 262 | 1560 | 4bit | yes | - |
| deepseek-r1-distill-qwen-32b | 0 | 0/0 (0%) | 0 | 0/0 | 0 | - | None / None | None | None | NO | no request completed; valid answers 0/0 < 90%; 4 failed or missing items |
| deepseek-r1-distill-qwen-32b | 8 | 64/64 (100%) | 64 | 8/8 | 0 | 81.0 | 2326.0 / 5087 | 1487 | 4bit | yes | - |
| llama-3.3-70b-instruct | 8 | 64/64 (100%) | 64 | 8/8 | 0 | 24.8 | 202.0 / 204 | 1268 | 4bit | yes | - |
| qwen2.5:72b | 8 | 64/64 (100%) | 64 | 8/8 | 0 | 30.8 | 246.5 / 254 | 1501 | Q4_K_M | yes | - |

Notes. Rows appear in run order; v1 and v2 are separate runs on the same four smoke worlds. v2 runs follow the
harness repairs of D73 (last-JSON-object parser; an answer is valid when its verdict is; max_tokens 3000), which
were made before any pilot request. gemma-3-4b passes under D73 but never gives a probability, so it can be scored
on status only. The R1-distill v1 row is the run stopped by operator error after about 4 minutes (D75); it carries
no timing information. R1 v2 ran with no other model generating: median 81 s per request, up to 5,087
completion tokens. All smoke runs used task wording v1 (tasks v2/v3 came later, D76/D78). Seconds per request for
llama-70B were measured while the mistral pilot was running on the same machine.
