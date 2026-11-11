# S4 protocol draft: development pilot contract and proposed main study

Iteration 4, 2026-11-11. Pre-sprint development document. The **pilot contract** below (§2–§6) was fixed and
committed before the first pilot call; its commit is named in `reports/REVIEW_READY_R4.md`. The **main study**
(§7) is a proposal for review and is **not authorized and not run**. S1/S2 sealed plans, endpoints and
historical results are unchanged.

Method definitions: `docs/S4_METHOD_COVERAGE.md`. Scientific direction: `docs/RESEARCH_DIRECTION_S4.md`, as
amended by `docs/S4_FOUNDATIONS_AND_PRECOMMIT_CHECKING.md`.

## 1. Question

Does arm D (our compressed structured representation: the analytic index-set vocabulary, support-schema
mechanism space and CGH-1 hierarchy) help an AI reach more correct, checkable conclusions about unseen
intervention claims than a strong generic symbolic workspace (B)? Equally: does it reach the same conclusions
with less evidence or computation?

**Expected agreement (stated before the pilot).** B, C and D are exact over the same declared class. Wherever
all three finish, their verdicts coincide (§4 of the coverage document). A verdict-accuracy difference between
tool arms can therefore come only from (i) the AI's use of the interface, (ii) presentation of witnesses and
summaries, or (iii) resource refusals. At pilot sizes (n = 8) no backend refuses, so **a D − B tie on verdict
accuracy is the expected pilot outcome**. A tie is not a failure, and it is not evidence of an index-specific
advantage. The representation-specific questions are measured separately:

- cost and scaling (offline stress map);
- codec-induced forecasts under less evidence (offline secondary);
- measurement choice (S4-B).

## 2. Population and tasks (pilot)

- **Strata:** sparse_conj, canalizing, repeated_modules, ordered_motif, parity, bounded_random, order_disrupted
  (matched to ordered_motif), uniform_H null (`s4/tasks.py`, design version `s4-design-v1`).
- **Size:** n = 8, H = bounded indegree k = 3 (complete class).
- **Development salts (all distinct):**
  - `dev-s4-pilot-v1`: pilot worlds, indices 0–4 per stratum, 40 worlds; the same 40 worlds for both models;
  - `dev-s4-map-v1` / `v2`: offline map;
  - `dev-s4-active-v1`: S4-B;
  - `dev-s4-train-v1`: surface baselines;
  - `dev-s4-pilot-rev1`: the only permitted interface revision (§5), if needed.
- **Evidence:** B ∈ {12, 16, 24}, drawn by the design RNG. Of these, B − B//4 are uniform one-step
  full-state observations and B//4 are one-step persistent-clamp observations.
- **Claims:** eight per world. Each has a novel effective start state, an initial_edit or persistent_clamp on
  1–2 nodes, h ∈ {1, 2, 3}, and a target node and value drawn independently of hidden answers. Duplicates and
  complements are excluded; redraws are counted.
- **Reference:** exact verdicts from the explicit engine. The D engine and the complete SAT encoding must agree,
  or the world is a gate failure. The hidden target value is used only for the forecast score.

## 3. Arms and interface

| Arm | Tool | Turns |
|---|---|---|
| A | none: evidence table + claims + matched definitions | 1 |
| B | generic CNF/SAT + explicit counts | ≤ 8 |
| C | flat index explicit workspace | ≤ 8 |
| D | index-set mechanism space + analytic vocabulary + CGH-1 | ≤ 8 |

- **Same tool protocol for B/C/D:** `check`, `status`, `propose`, `commit` (`s4/pilot.py`). The response schema
  is identical; only the representation of example mechanisms and the status summary differs by arm.
- **Common initial proposal batch:** arm A's single turn. It is persisted and replayed offline through the
  B/C/D checkers with no extra model calls.
- **Pre-release gate:** `s4/checking.py`. A commit releases an answer as *verified* only for an authentic,
  sealed checker decision bound to the exact claim and assumptions. Forecasts never get a badge.
- **Deterministic no-LLM controller (analysis only):** copies the exact tool verdict and uses the exact
  uniform-majority forecast. It is the ceiling that shows whether the AI adds or loses anything.

## 4. Resource contract (pilot)

| Item | Cap |
|---|---|
| Models | two local models (§6); local inference only; no paid service; no weight change |
| Worlds | 40 per model (5 per stratum) |
| Model turns | ≤ 8 per tool-arm episode; 1 for arm A; ≤ 25 calls per world (cap enforced) |
| Total calls | ≤ 2,560 including retries and the pre-pilot smokes (append-only ledger `runs/s4-calls/ledger.jsonl`, flock'd) |
| Tokens | max_tokens 1,200 per call; context 16,384 (Ollama `num_ctx`; LM Studio loaded with `--context-length 16384`); prompt tokens recorded per call |
| Tool limits | h = 3 enumeration cap 2^14 states; explicit materialization n ≤ 10; SAT unlimited at n = 8 |
| Wall time | per call timeout 300 s; per world item timeout 3,600 s; failures recorded, never retried silently |
| Temperature | 0, seed derived per (world, arm, turn) |
| Storage | one immutable attempt file per (model, world), including every raw model output |

A call that exhausts a cap is a recorded, failed outcome. The S4-B offline prototype uses no model calls.

## 5. Validity and usability gates (not statistical success)

All gates are applied per model.

1. Zero semantic correctness mismatches: B/C/D vs reference on every replayed claim.
2. No hidden-data flow: payload audit for every world, plus a prompt scan.
3. At least 90% parsable verdicts per arm, counted over scheduled claims.
4. No systematic truncation: at most 2% of calls with `finish_reason = length`.
5. Every missing outcome accounted for.

Low baseline accuracy is reported, never used to drop a model. If an interface gate fails, at most **one**
logged revision is allowed, on fresh development worlds (salt `dev-s4-pilot-rev1`, 16 worlds per model). Its
cost, ≤ 400 calls per model, is declared before it starts and is inside the 2,560 ceiling. All failed
diagnostics are kept. A second failure returns the blocked component.

**Pre-pilot interface development (disclosed).** Two one-world smokes on qwen2.5:7b (salt `dev-s4-smoke-llm`,
36 calls, inside the ceiling) found that the model wrote bare tool names without claim ids. Before the pilot,
the tool instructions gained two concrete examples, a specific error message and a last-turn reminder. These
smokes are not pilot data.

## 6. Models (selection rule declared before any S4 outcome)

Rule: two instruction-tuned, non-reasoning local models from different families and serving stacks, at most
30B parameters, with a context of at least 16k tokens available on this machine. Previously used local models
are preferred. A model is kept regardless of its accuracy or treatment effect.

| Model | Server | Artifact |
|---|---|---|
| qwen2.5:7b (Q4_K_M) | Ollama 0.40.16, native `/api/chat`, num_ctx 16,384 | digest `845dbda0ea48…` (full digest and template hash in each record) |
| mistral-small-3.2-24b-instruct-2506 (MLX 4-bit) | LM Studio, loaded with context 16,384 | no digest exposed by LM Studio (recorded limitation) |

gemma-3-12b-it, the S3 second model, is **not** used: this MLX build reports a maximum context of 4,096
tokens, too small for a tool episode. This is a technical criterion, not an outcome. Its S3 floor result played
no role.

## 7. Proposed main study (for review; not run)

- **Primary (proposed):** world-level S4-A verdict accuracy, D − B. Per-world accuracy over eight scheduled
  claims, equal family weights, stratified paired cluster bootstrap (10,000 replicates, seed 20261111). Holm
  across the two models (familywise 0.05).
- **Secondaries:**
  - D − A (system benefit) and D − C (fuller representation vs flat);
  - forecast accuracy on underdetermined claims;
  - wrong definitive claims;
  - verified-release coverage;
  - prevention metrics on the common batch;
  - costs.
- **Attribution:** offline no-hierarchy (`cgh_flat`) and no-analytic (`*_noanalytic`) ablations. D − C alone
  does not isolate the hierarchy.
- **Sizing:** `reports/S4_DESIGN_SIZING.md`, computed from pilot per-world variance with an upper-variance
  scenario. Planning target 320 worlds per model, up to 800 if justified.
- **Reviewer decision needed before any main-study run:** whether the primary should stay D − B accuracy at
  sizes where a tie is expected, or move to one of:
  1. accuracy at sizes where B hits declared resource caps;
  2. cost at equal accuracy;
  3. the codec-averaging forecast endpoint, which is where the representation can change answers.

  The pilot and the offline map are designed to inform this choice. The data needed are in
  `reports/S4_DEVELOPMENT_REPORT.md`.
