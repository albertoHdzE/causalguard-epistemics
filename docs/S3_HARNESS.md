# S3 LLM harness (WP7)

Code: `src/causalguard/llm/{providers,parse,harness}.py`, `src/causalguard/experiments/s3.py`.
Tasks and feedback text: `src/causalguard/s3_tasks.py`. Tests: `tests/test_llm_harness.py`.

## Arms (per world; items from `s3_tasks.make_s3_items`)

| Arm | Calls | Context |
|---|---|---|
| A | `i{i}/A`, temperature 0 | the item prompt alone |
| B | `i{i}/B` | A's conversation, then a fixed self-critique turn (`CRITIQUE_PROMPT`); no external information |
| C | `i{i}/C1`, `i{i}/C2`, temperature 0.7, each with its own derived seed | fresh contexts; members = A + C1 + C2 |
| D | `i{i}/D1`, `i{i}/D2` | A's conversation, then exactly min(2, `feedback_rounds`) `witness_feedback` rounds; claim = previous turn's parsed verdict (None if invalid) |
| D_label | `i{i}/DL` | A's conversation, then `label_feedback` (privileged control: discloses the verdict) |
| E | none | `solver_answer` (exact symbolic verdict) |
| T_A | `T_A` | A's conversation on the source item (default 0), then the target item's (default 1) unchanged prompt |
| T_D | `T_D` | the full D conversation on the source item, then the target item's prompt |

* **Shared first answer.** `i{i}/A` is sent once. B, C, D and D_label reuse it; they do not re-send it.
  This reuse correlates the arms. Handle that with paired analysis. The reuse does not add samples.
* **C aggregation.** The verdict is the plurality over members with a valid verdict. A tie, or no
  valid vote, gives `abstain`. The probabilities are the arithmetic mean of the valid vectors only.
  If no vector is valid, the probabilities are invalid. The record keeps `n_valid_vectors`,
  `n_valid_votes`, `invalid_members` and `member_statuses`.
* **D.** D stops early only when the provider fails. The final answer is the last round that ran.
  Every round records its feedback provenance (`symbolic_checker_witnesses`, the answers shown and
  the claim). Before sending, each feedback text is checked: if it contains any of the three label
  words, a `LeakageError` is raised and the world becomes a runner failure. A witness can still
  reveal the answer implicitly. D is witness-assisted correction, not label-free learning.
* If A has a provider failure, B, D and D_label are not called. Their final answer is
  `provider_failure` with the flag `dependent_on_failed_first_answer`. T_A and T_D behave the same
  way when their source context failed.
* Same-item improvement in B, D or D_label is assisted correction, not persistent learning. Transfer
  is measured only by T_A and T_D against A on the target item.

## Parse statuses (`llm/parse.py`)

The statuses are checked in this order:

1. `provider_failure`
2. `invalid_json`
3. `semantic_error`: the JSON is not an object, or it has neither `verdict` nor `probabilities`.
4. `abstain`: the verdict is `abstain`, `abstention` or `unknown`.
5. `invalid_verdict`
6. `invalid_probabilities`: missing or extra keys, a non-numeric or non-finite value, a negative
   value, or a sum outside 1 ± 0.02.
7. `ok`

The verdict and the probabilities are validated independently (`verdict_valid`, `probs_valid`).

Flags (none of these is an error):
* `verdict_prob_mismatch`: the verdict is not the argmax of the probabilities.
* `verdict_normalized`: the verdict differed only in case or whitespace.
* `think_stripped`
* `extracted_object`
* `reason_missing`

Text extraction is deterministic and never uses a model:
1. Remove `<think>…</think>` blocks. An unclosed `<think>` removes everything after it.
2. Apply `json.loads` to the whole text.
3. If that fails, apply it to the first balanced `{…}` substring. The brace scan is aware of string
   literals.

No other repair is made, and content errors are never retried.

## Transport and cost accounting

* `OpenAICompatibleProvider` uses urllib only. It refuses a non-localhost `base_url` unless
  `allow_remote=true`. It never reads keys or the environment.
* Connection errors, timeouts and HTTP 5xx are retried at most `max_transport_retries` times
  (default 2). HTTP 4xx and malformed envelopes fail immediately.
* Every attempt is logged with `latency_s`, `prompt_tokens`, `completion_tokens` and
  `finish_reason`.
* The record reports two costs:
  * **Physical cost** (`cost.physical`): the attempts actually sent, including retries.
  * **Logical standalone cost** (`cost.logical_standalone_by_arm`): what each arm would cost alone,
    counting the shared A call it depends on.
  * `attempts_saved_by_sharing` is the sum of the logical costs minus the physical cost.
* There are two caps, both counted in physical attempts and checked before each attempt:
  * `caps.calls_per_world`, counted in-process.
  * `caps.calls_total`, counted through an append-only, flock'd ledger
    `runs/<run_id>/call_ledger.jsonl`. This cap holds across worker processes and across resumes.
* Reaching a cap sets `world_status` to `world_cap_reached` or `global_cap_reached` and stops that
  world. The record stays in the run. Missing arms are scored as `not_run`: incorrect, with Brier 2
  in the worst-case score. Once the global cap is reached, every later world gets status
  `global_cap_reached` and makes zero calls. To continue, raise the cap, which changes the config,
  so start a new run id.

## Leakage controls

* `private` is used only by `witness_feedback`, `label_feedback` and `solver_answer`.
* The scorer reads `record["oracle"]`, which holds the verdict and the hidden answer per item.
* Tests check that the user turns of A, B, C, D and T_* contain no label word once the fixed
  `INSTRUCTIONS` text is removed. They also check that D_label does contain the item's verdict.
* Every record and every call carries `provider_kind` (`real`, `mock` or `replay`). `score` and
  `per_world_scores` raise an error on mixed kinds. They also raise on mock or replay records unless
  `allow_mock=True` is passed.

## Scoring (`experiments/s3.py`)

`score(records)` reports, per arm:
* final-verdict accuracy, where malformed, abstained and not-run answers count as incorrect;
* balanced accuracy: the mean recall over the classes present;
* valid-only Brier, Σ_k (p_k − y_k)², which ranges from 0 to 2, together with its validity coverage;
* worst-case Brier, which assigns 2 to an invalid or missing answer;
* status counts.

It also reports:
* revision counts for B, D and D_label against A (correct→wrong, wrong→correct, …);
* T_A and T_D against A on the target item;
* costs.

`per_world_scores(records)` gives per-world sufficient statistics (per-class counts and Brier sums)
for the lead's paired cluster bootstrap. This module does no resampling.

## Commands

Run each pilot with one worker per endpoint. The runner config holds `workers: 1` and
`world_timeout_s: 3600`. To resume, repeat the same command: completed worlds are skipped, and a
changed config is refused.

```
.venv/bin/python -m causalguard.experiments.s3 --config configs/s3_pilot_qwen25_7b.json --run-id s3-pilot-qwen25-7b-dev-v1 --worlds 80 --quiet
.venv/bin/python -m causalguard.experiments.s3 --config configs/s3_pilot_gemma3_12b.json --run-id s3-pilot-gemma3-12b-dev-v1 --worlds 80 --quiet
```

Prerequisites:
* Ollama is serving `qwen2.5:7b` at 127.0.0.1:11434.
* LM Studio's server is running at 127.0.0.1:1234 with `gemma-3-12b-it` available. LM Studio loads
  the model on first use.

Do not run both pilots at the same time on the same machine without a shared resource cap.

Expected cost with the default arms, assuming 4 items per world:
* 7 calls per item plus 2 transfer calls, so 30 physical calls per world before retries;
* about 2,400 calls for 80 worlds, under the configured caps of 40 per world and 4,000 in total.

Offline scoring:

```
.venv/bin/python -c "from causalguard.runner import read_jsonl; from causalguard.experiments.s3 import score; import json; print(json.dumps(score(read_jsonl(__import__('pathlib').Path('runs/<run_id>/records.jsonl'))), indent=1))"
```

## Limitations

* **Seeds.** Seeds are sent, derived from (config seed, world id, call id). Whether the backend
  honours them is not verified (`seed_honoured: "not_verified"`).
* **Ollama metadata.** The adapter records the digest, quantisation, parameter size, the SHA-256 of
  the chat template and the server version (`/api/tags`, `/api/show`, `/api/version`).
* **LM Studio metadata.** The adapter records the `/v1/models` entry and `/api/v0/models/<id>`
  (quantisation, format, architecture, context length). LM Studio exposes no digest or server
  version, so these are null and listed under `limitations`.
* **Metadata timing.** Metadata is fetched at the start of each world. A model swapped during a run
  shows up as changed metadata, but nothing prevents the swap.
* **Context length.** `max_tokens=400` caps each completion. If a backend context window is short
  (LM Studio reports 4096 for gemma-3-12b-it), long D/T_D conversations may be truncated
  server-side. Check `finish_reason`.
* **Global cap with several workers.** The ledger makes the global cap exact. The per-world cap is
  per process.
* **Smoke test is not a pilot.** A transport smoke test (1 world, arm A) is not a pilot and must
  not be reported as one.
