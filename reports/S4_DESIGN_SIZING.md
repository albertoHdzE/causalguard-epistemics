# S4 prospective main-study sizing (development; for review, not authorization)

2026-11-11. Inputs:

- the pilot summary (`reports/development_r4/s4_pilot_summary.json`; 40 worlds per model, two models);
- the sizing output (`s4_sizing.json`);
- the offline map (`s4_map_summary.json`).

Design simulation uses `stats.design_simulation`:

- worlds are resampled within strata, with equal allocation over the 8 strata;
- the interval is normal, with the stratified SE;
- per-model α = 0.025, which is Holm's worst case for two models;
- the "conservative" scenario inflates per-world deviations by **1.5×** (an upper-variance planning value,
  not the optimistic pilot value);
- 2,000 simulations; the effect is 5 points.

The pilot is small. Its variance estimates are themselves uncertain, and nothing here promises significance.

## 1. The proposed primary (D − B verdict accuracy) cannot be sized: it is an exact tie

| Model | D − B (recorded) | D − B (merged-commit sensitivity, D52) | worlds with a nonzero D − B delta |
|---|---|---|---:|
| qwen2.5:7b | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0/40 |
| mistral-small-3.2-24b | +0.022 [0.000, +0.066] | 0.000 [0.000, 0.000] | 1/40 (a harness artifact) |

The tie was stated before the pilot (`docs/S4_PROTOCOL_DRAFT.md` §1). Both backends are exact over the same
class, and at n = 8 neither refuses. With essentially zero per-world variance, no N gives power for a 5-point
difference: **a larger study of the same design would only confirm the tie**. Reporting "power" here would be
meaningless; the planning formula with a floor SD of 0.10 gives N = 39, an artifact of the floor.

**Recommendation for the reviewer.** Do not run 320–800 worlds per model on this primary. Re-decide the primary
endpoint first. The candidates, with evidence:

| Candidate primary | Why it can differ between arms | Development evidence | Sizing |
|---|---|---|---|
| (a) Verdict accuracy at sizes where generic tools hit declared caps | B lacks exact counts above n = 10; B's SAT misses n = 64 within 300 s | stress v2: D 12/12 claims at n = 64 vs B 4/12 | needs an LLM pilot at n ≥ 48 (not run); per-claim tool latency up to 300 s makes episodes long |
| (b) Cost at equal accuracy (tool wall time, tokens, calls) | D is ~9× faster on h ≤ 2 verdicts at n = 48 and adds counts | stress v2; pilot tool time is negligible at n = 8 | an offline benchmark; no LLM needed |
| (c) Forecast accuracy on underdetermined claims (codec-induced averaging) | the representation changes answers through the prior, not through logic | map v2, B = 12: cgh_prior − uniform +8.9 [+6.4, +11.5]; cgh_prior − cgh_flat +4.9 [+3.6, +6.3] | offline: 320 worlds give 0.93 power (conservative) for 5 points vs uniform; ≥ 160 worlds give 1.00 vs cgh_flat; cheap (no LLM) |
| (d) System benefit D − A (secondary today) | tool vs no tool | +0.35 to +0.36, CIs exclude 0 in both models | already decisive at 40 worlds per model |

Option (c) is the only one where our representation can change what is believed. Its present evidence is
offline, and the hierarchy-specific gain is confined to the generator-matched families (§3 of the development
report). A fair confirmatory version needs held-out families whose structure was not chosen by us, for example
structural holdouts or external benchmark networks.

## 2. If an LLM accuracy endpoint with real variance is kept (D − A-like variability)

With per-world SD ≈ 0.32–0.33 (pilot D − A) and 1.5× inflation, the power to detect a 5-point stratified mean
difference is:

| N per model | qwen2.5:7b power | mistral power | p90 95%-interval half-width (observed scenario) | false-positive rate under null |
|---:|---:|---:|---:|---:|
| 160 | 0.26 | 0.22 | 0.049 / 0.052 | 0.03 |
| 320 | 0.50 | 0.45 | 0.034 / 0.036 | 0.03 |
| 480 | 0.71 | 0.65 | 0.028 / 0.029 | 0.02–0.03 |
| 640 | 0.84 | 0.79 | 0.024 / 0.025 | 0.03 |
| 800 | 0.91 | 0.88 | 0.021 / 0.023 | 0.03 |

**The 320-world planning target is underpowered** (≈0.45–0.50) for a 5-point effect at this variance. About
640 (qwen) to 800 (mistral) worlds per model are needed for 80% power under the upper-variance scenario.
Increase in balanced blocks of 80 (10 per stratum).

## 3. Resource forecast (measured pilot pace; local inference only)

| Quantity | Pilot (per model, 40 worlds) | 320 worlds/model | 800 worlds/model |
|---|---|---|---|
| model calls (4 arms) | qwen 447, mistral 404 | ≈ 3,600 / 3,250 | ≈ 8,900 / 8,100 |
| world wall time, mean | qwen 78 s, mistral 93 s (both servers sharing one GPU; medians 79 s, 96 s) | ≈ 7.0 h / 8.3 h | ≈ 17.4 h / 20.8 h |
| prompt tokens (all arms) | qwen ≈ 1.36 M, mistral ≈ 1.23 M | ≈ 11 M / 10 M | ≈ 27 M / 25 M |
| max prompt tokens per call | 5,302 / 5,421 (context 16,384) | same | same |
| raw storage | 1.4 MB / 1.3 MB | ≈ 11 MB / 10 MB | ≈ 28 MB / 26 MB |

The total for 2 × 800 is under 18,000 calls. That exceeds this delegation's 2,560-call ceiling and needs an
explicit new authorization. There is no paid inference, and timing assumes the same machine.

## 4. What was NOT done

- No main-study run.
- No re-sizing from confirmatory outcomes.
- No selection of a model by effect.
- The 2,560-call ceiling was respected: 888 calls in total, including 37 pre-pilot.
