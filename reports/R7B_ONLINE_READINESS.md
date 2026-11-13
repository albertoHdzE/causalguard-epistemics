# R7b online readiness (pre-sprint, 2026-11-12)

**No online request of any kind was made in R7b.** The 3 connectivity probes used in R7 (DeepSeek 1, Claude 2) are
the only ones so far; 2 of the 5 allowed remain. No benchmark item has gone online.

The two online models run the locked main panel (`artifacts/sprint_main_manifest.json`, 180 worlds: 120 Tier W,
60 Tier H, five conditions) with only the model changed. They use the same worlds, assignment, prompts (v3,
reasoning first), forged checks and analysis command. The adapters, key handling and the Claude isolation audit
are unchanged from R7 (`reports/R7_ONLINE_READINESS.md`, `tests/test_r7_online_adapters.py`). The only R7b
changes are the panel and the D85 failure rule, which applies to every provider.

## Order (after the director's review)

1. Smoke for each model: `configs/sprint/r7b_online_smoke_{deepseek_v4_pro,claude_opus_55}.json`, with 2 Tier W
   and 2 Tier H pilot-4 worlds (8 requests, cap 8). Check parsing, the isolation audit (Claude) and the cost
   record.
2. Main: `configs/sprint/r7b_online_main_{deepseek_v4_pro,claude_opus_55}.json`, 360 requests each (cap 400,
   so 40 are left for D85 retries), run from the lock snapshot:

```bash
scripts/run_from_snapshot.sh 1e79358d3cbd r7b-main-deepseek_v4_pro python -m causalguard run --config configs/sprint/r7b_online_main_deepseek_v4_pro.json --quiet
scripts/run_from_snapshot.sh 1e79358d3cbd r7b-main-claude_opus_55  python -m causalguard run --config configs/sprint/r7b_online_main_claude_opus_55.json --quiet
```

   The online configs are committed in the lock commit, but the lock's model list covers local models only. The
   online runs are the planned addition named in the lock under `online_models_planned`.
3. Analysis: `python -m causalguard sprint-analyze --run-dir <every main run> --out reports/sprint_all`.

## Expected cost, time and subscription use (estimates; the actual figures are recorded per request)

Token sizes are from the local pilot and the main runs: turn-1 prompts are about 0.9–1.0 k tokens and turn-2
prompts about 2.8 k, so the mean input is about 1.9 k per request. Reasoning length is the unknown.

| | DeepSeek V4-Pro (`deepseek-v4-pro`, thinking on, effort high) | Claude Opus 5.5 (`claude -p`, effort high) |
|---|---|---|
| requests | 360 (cap 400) | 360 (cap 400) |
| input tokens | about 0.7 M | about 0.9 M (adds about 575 harness tokens per request, R7) |
| output tokens (with thinking) | 0.7–4.3 M (2 k–12 k per request) | 0.7–2.9 M (2 k–8 k per request) |
| cost | about $2–18 at peak rates, half that off-peak (V4-Pro: input $1.32, output $3.96 per 1 M tokens at peak; R7 price check) | billed to the subscription; the CLI's `totalCostUSD` is recorded per session. No dollar estimate is given because no current price was checked |
| wall time | 8 workers at 30–200 s per request: about 25 min to 2.5 h | 4 workers at 30–150 s per request: about 45 min to 3.8 h |
| other | DeepSeek's peak window is 01:00–04:00 and 06:00–10:00 UTC (19:00–22:00 and 00:00–04:00 CST). A daytime CST launch on 2026-11-13 is off-peak | counts against the subscription's usage windows. If a window runs out, requests fail; under D85 the item fails, and the run resumes under its identical plan with `--retry-failed` |

## Readiness checks done in R7b (no network)

- Both online configs point at the R7b manifest, wording v3 and the R7b run ids. The smoke configs use the
  pilot-4 manifest with `per_tier: 2`.
- The D85 failure rule is covered for every provider by `test_empty_reply_is_a_transport_failure_and_fails_the_world`.
- The key appears in no file. Configs name only the environment variable and the path of the ignored `.env`
  outside the repository. A scan for the account e-mail and key patterns runs before every push.
