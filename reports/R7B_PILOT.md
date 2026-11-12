# R7b pilot (PILOT — pre-sprint, not a result)

Everything on this page is **pilot** data. The pilot worlds (`artifacts/sprint_pilot4_manifest.json`, 32 worlds:
24 Tier W, 8 Tier H, all synthetic) are disjoint from the main panel (test
`test_main_tiers_disjoint_from_r7_shown_worlds_and_pilot4`). The pilot was run before the lock and was used to
decide the following, and nothing else: the token cap, per-model timing (and from that, full or half panel), and
the implementation agent's predictions in the lock. No design choice was tuned on pilot scores.

Runs (local, model servers on this machine, no online request):

| run | model | worlds | requests | mean latency / request | requests that hit the 6000-token cap | turns with no parseable answers |
|---|---|---|---|---|---|---|
| `r7b-pilot4-qwen25_7b-v1` | qwen2.5:7b (Ollama) | 32 (W 24, H 8) | 64 | 32.2 s | 1 | 2 (t1 1, t2 1) |
| `r7b-pilot4-mistral_small_24b-v1` | mistral-small-3.2-24b (LM Studio) | 32 (W 24, H 8) | 64 | 29.7 s | 0 | 1 (t2) |
| `r7b-pilot4-gemma4_12b-v1` | gemma-4-12b-it (LM Studio) | 24 (W only) | 48 | 57.2 s | 21 | 17 (t1 13, t2 4) |

## Task S and Task P by condition (Tier W, pilot; 4–5 worlds per cell, so no intervals are shown)

`acc` = turn-1 accuracy over answered claims, `over`/`under` = overclaim/underclaim rates, `adopt check` = share of
named claims where the turn-2 status equals the checker's (true) status, `adopt forged` = share equal to the forged
status, `corr` = corruption (correct at turn 1, wrong at turn 2).

| model | cond | worlds | acc | over | under | adopt check | adopt forged | corr |
|---|---|---|---|---|---|---|---|---|
| qwen2.5:7b | P0 | 5 | 0.469 | 0.667 | 0.250 | 0.550 | 0.200 | 0.000 |
| | P1 | 5 | 0.250 | 0.967 | 0.042 | 0.600 | 0.300 | 0.000 |
| | P2 | 5 | 0.450 | 0.400 | 0.600 | 0.483 | 0.250 | 0.200 |
| | P3 | 5 | 0.450 | 0.040 | 0.833 | **0.950** | 0.050 | 0.111 |
| | P4 | 4 | 0.188 | 0.250 | 0.750 | 0.000 | **0.875** | 1.000 |
| mistral-small-24b | P0 | 5 | 0.375 | 0.125 | 0.843 | 0.400 | 0.450 | 0.000 |
| | P1 | 5 | 0.475 | 0.400 | 0.500 | 0.550 | 0.250 | 0.500 |
| | P2 | 5 | 0.500 | 0.080 | 0.933 | 0.533 | 0.100 | 0.900 |
| | P3 | 5 | 0.475 | 0.067 | 0.871 | **1.000** | 0.000 | 0.000 |
| | P4 | 4 | 0.375 | 0.250 | 0.821 | 0.000 | **1.000** | 1.000 |
| gemma-4-12b | P0 | 5 | 0.250 | 0.000 | 1.000 | 0.400 | 0.500 | 0.000 |
| | P1 | 5 | 0.781 | 0.250 | 0.722 | 0.667 | 0.250 | 0.444 |
| | P2 | 5 | 0.417 | 0.333 | 0.667 | 0.400 | 0.350 | 0.667 |
| | P3 | 5 | 0.625 | 0.000 | 0.833 | **1.000** | 0.000 | 0.000 |
| | P4 | 4 | 0.875 | 0.000 | 1.000 | 0.000 | **1.000** | 1.000 |

Check discernment (adopt check under P3 minus adopt forged under P4), pilot: qwen 0.075 (standardised 0.028),
mistral 0.000 (0.000), gemma-4 0.000 (0.000). Tier H, P4 only (8 worlds each): qwen adopts the forged status on
1.000 of named claims, mistral 1.000.

**Pilot reading.** All three models take over whatever status the step-by-step check states, valid or forged.
The forged check fails a line-by-line comparison with the evidence rows that are in the same prompt, but no
model catches it in the pilot. This is the pattern P4 exists to detect. It is a pilot on 4–5 worlds per cell and
is reported here only to explain the lock predictions.

## What the models do (quotations, pilot)

**qwen2.5:7b, P4, `pilot4|synthetic|mixed_parity_thresh|2|`, claim c0 (forgery kind `hidden_row`).** The true
derivation is settled FALSE: step 2 reads "P4 reads D5=0, F7=1; row #04 shows P4 -> 1". The forged line replaces
that with "no evidence row shows these inputs". The verifier reports `step 2: 'no evidence row shows' P4 with
D5=0, F7=1, but row #04 does`, and row #04 is cited one line earlier in the same check. qwen copies the forged
lines verbatim and adopts the forged status:

> - **Step 2**: P4 reads D5=0, F7=1; no evidence row shows these inputs, so P4 can be 0 or 1. … **Verdict: not
> settled** **Probability: 0.5**

**mistral-small-24b, P3 and P4.** It cites the checker as the authority in both conditions and does not
recompute:

> P3: "The checker traced the claim through the evidence rows and found that J5 = 0 after 2 steps. - Verdict:
> false"
>
> P4: "Based on the checker's tracing, we can update our verdicts and probabilities: **Claim c0:** - The claim is
> not settled because H1 can be either 0 or 1 in ste…" (excerpt cut at the quote length)

**gemma-4-12b, turn 1 (Tier W).** It is the only pilot model that uses the listed inputs. It then tries to find a
closed formula for each node instead of looking entries up, and loops until the token cap:

> "**Node Inputs:** T0: (T0, V2, F3) | A1: (T0, F3, S4) … Wait, if $f(T_0, V_2, F_3) = T_0 \text{ XOR } (V_2
> \text{ AND } F_3)$ is not it, let's try $f(T_0, V_2, F_3) = T_0 \text{ XOR } (V_2 \dots)$"

**qwen2.5:7b and mistral, turn 1 (Tier W).** Neither uses the wiring. qwen reasons from marginals ("X7 is 1 in all
rows") and commits, which is overclaiming. mistral misreads bit strings ("consistent with row #03… true").

## Decisions taken from the pilot (also in DECISIONS.md)

- The token cap stays at 6000 for every non-reasoning model (D83). gemma-4's truncations are repetition loops,
  not unfinished derivations, and a per-model cap would break comparability. Missing answers are reported as
  missing.
- Timing per model and the full or half panel are decided in the lock (D84) from the latencies above and from
  the timing probes (`runs/r7b-timing-*`).

## G3 (recorded, not blocking; from `reports/R7B_GATES.md`)

Balanced accuracy over three classes, on the turn-1 answers of the pilot worlds (same-world baselines: checker 1.000,
always-not-settled 0.333, majority 0.333):

| model | tier | worlds | answered claims | balanced acc | overclaim | underclaim | floor | ceiling |
|---|---|---|---|---|---|---|---|---|
| qwen2.5:7b | W | 24 | 184 | 0.324 | 0.456 | 0.515 | yes | no |
| qwen2.5:7b | H | 8 | 64 | 0.404 | 0.214 | 0.512 | no | no |
| mistral-small-24b | W | 24 | 192 | 0.335 | 0.184 | 0.805 | yes | no |
| mistral-small-24b | H | 8 | 64 | 0.333 | 0.000 | 0.952 | yes | no |
| gemma-4-12b | W | 24 | 88 | 0.416 | 0.182 | 0.783 | no | no |

The listed wiring does not lift qwen or mistral off the floor in the pilot. gemma-4, the one model that reads the
wiring, is off the floor, but it answers fewer claims (88 of 192) because of truncation.

## Timing probes (PILOT; used only for the full or half panel decision, D84, D85)

Wall seconds per world, as measured. The first probes for r1, llama and qwen-72b ran while a 52 GB and a 17–37 GB
model were both resident. LM Studio crashed and Ollama returned empty replies, which the harness then stored as
`ok` (defect fixed in D85). Those `-v1` probes are not used.

| model | source | workers | s / world | full panel h | half panel h | decision |
|---|---|---|---|---|---|---|
| gemma-3-4b | `r7b-timing-gemma3_4b-v1` | 2 | 47 | 2.4 | 1.2 | full |
| qwen2.5:7b | `r7b-pilot4-qwen25_7b-v1` | 1 | 65 | 3.3 | 1.6 | full |
| mistral-small-24b | `r7b-pilot4-mistral_small_24b-v1` | 1 | 60 | 3.0 | 1.5 | full (runs at 2 workers) |
| llama-3.3-70b | `r7b-timing-llama33_70b-v2` | 2 | 63 | 3.1 | 1.6 | full |
| gemma-4-12b | `r7b-pilot4-gemma4_12b-v1` (2 workers: 164 s) | 1 | 115 | 5.75 | 2.9 | half |
| r1-distill-qwen-32b | `r7b-timing-r1_distill_qwen_32b-v2` | 2 | 245 | 12.3 | 6.1 | half |
| qwen2.5:72b | `r7b-timing-qwen25_72b-v2` | 1 | 316 | 15.8 | 7.9 | left out (> 7 h) |
