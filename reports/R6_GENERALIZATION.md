# R6 Track G6 — locked n = 8 evaluations of exact dictionary sharing (development)

Status: development, 2026-11-12. Analyst: Claude Opus. Runs `r6-g-eval-v1` (320 worlds) and `r6-g-ext-fresh-v1`
(449 instances, 122 source groups) executed from the lock commit `246d3cd` (audit: `reports/R6_XDC_AUDIT.md`).
Nothing was tuned, rerun, added or dropped. Locked commands as in `delegation/iteration_6/01_SCIENTIFIC_PROTOCOL.md`
§4; outputs `reports/development_r6/g_evaluation.json`, `g_external_fresh.json`, figures `fig_g_evaluation.png`,
`fig_g_external_fresh.png`. Supplementary (post hoc, not locked) analyses: `g_evaluation_extras.json`,
`g_external_fresh_extras.json` (`analyze-r5 --track g-r6-extras`).

Contrast sign: positive = the method `xdc[cgh_flat]` has lower Brier. Intervals: source-group cluster bootstrap,
10,000 replicates. There are no missing predictions, so the worst-case missingness bounds equal the estimates.

## Headline

| Population | Primary (B = 16) | Locked prediction | Met? |
|---|---|---|---|
| Fresh synthetic, 320 worlds, 280 groups | **+0.0149 [0.0088, 0.0211]** | positive, ≥ 0.02, interval excluding 0 | sign and interval yes; **size no** (below the 0.02 planning value) |
| Fresh external, 449 instances, 122 groups | **+0.0033 [0.0012, 0.0055]** | \|est\| < 0.006, interval probably including 0 | size yes; the interval **excludes** 0 |

Lock interpretation rules: the synthetic result is `supported_in_scope` (scope = worlds with reused rule types).
The external interval at B = 16 excludes 0 with positive sign, so the lock's formal condition for
"generalizes to published models" is met. **But** the effect is a sixth of the 0.02 planning value, the sharing
part alone is not separable from 0 on that panel (below), and the panel consists of 8-node fragments with 31 % constant
nodes. I report it as a small, statistically detectable improvement on clamped 8-node fragments, not as a
practically meaningful generalisation.

## Fresh synthetic evaluation (`r6-g-eval-v1`)

Contrasts (equal stratum weights):

| Contrast | B = 8 | B = 16 | B = 24 |
|---|---|---|---|
| primary gate − xdc[cgh_flat] | +0.0139 [0.0072, 0.0206] | **+0.0149 [0.0088, 0.0211]** | +0.0083 [0.0047, 0.0119] |
| sharing cgh_flat − xdc[cgh_flat] | +0.0145 [0.0090, 0.0202] | +0.0165 [0.0114, 0.0219] | +0.0075 [0.0046, 0.0106] |
| vocabulary xdc[gate] − xdc[cgh_flat] | +0.0019 [−0.0033, 0.0073] | −0.0016 [−0.0053, 0.0019] | +0.0011 [−0.0007, 0.0030] |
| generic sharing gate − xdc[gate] | +0.0120 [0.0067, 0.0174] | +0.0165 [0.0112, 0.0220] | +0.0072 [0.0039, 0.0106] |
| uniform − method | +0.0152 [0.0082, 0.0222] | +0.0361 [0.0300, 0.0422] | +0.0267 [0.0225, 0.0310] |
| GSR(0.5) − method | +0.0072 [0.0008, 0.0136] | +0.0293 [0.0233, 0.0354] | +0.0236 [0.0195, 0.0278] |

All of the synthetic gain is sharing. The vocabulary contrast is null at every budget.

Per stratum at B = 16 (40 worlds each; mean Brier and gate − method):

| Stratum | mean hidden reuse | gate | cgh_flat | xdc[cgh_flat] | gate − method | sharing |
|---|---|---|---|---|---|---|
| template_exceptions | 6.2 | 0.0991 | 0.0906 | 0.0416 | **+0.0575** | +0.0490 |
| shared_motifs | 6.1 | 0.0900 | 0.0845 | 0.0320 | **+0.0580** | +0.0525 |
| rewired_control | 5.2 | 0.0834 | 0.0796 | 0.0375 | **+0.0459** | +0.0421 |
| imperfect_modules | 3.3 | 0.0670 | 0.0683 | 0.0601 | +0.0070 | +0.0082 |
| feedback_canalizing | 1.5 | 0.0585 | 0.0489 | 0.0538 | +0.0046 | −0.0049 |
| feedforward_hetero | 1.9 | 0.0229 | 0.0286 | 0.0282 | −0.0053 | +0.0004 |
| mixed_parity_thresh | 1.7 | 0.0354 | 0.0453 | 0.0454 | −0.0100 | −0.0000 |
| uniform_H (null) | 0.6 | 0.1228 | 0.1462 | 0.1612 | **−0.0384** | −0.0150 |

**The null stratum.** On uniform_H the method is worse than the champion by 0.038 Brier, the largest loss of any
stratum: 0.024 of it comes from the cgh_flat vocabulary and 0.015 from sharing. That is the expected sign; its size
is the price of the method when there is no structure.

**Where the effect is and is not** (supplementary, post hoc):

| Subset | gate − method, B = 16 |
|---|---|
| the four reuse-by-construction strata (S1, S2, S3, S7) | +0.0421 [0.0323, 0.0524] |
| without the two strata richest in reuse (template_exceptions, shared_motifs) | +0.0006 [−0.0058, 0.0070] |
| **without all four reuse-by-construction strata** | **−0.0123 [−0.0193, −0.0053]** |

On the four strata that do not reuse rules by construction (including the null) the method is significantly
**worse** than the generic champion. The synthetic gain exists only where the generators planted reused rule types.

By hidden rule reuse (n − number of distinct order-free types in the hidden mechanism; evaluator side):

| reuse | 0 | 1 | 2 | 3 | 4 | 5 | 6+ |
|---|---|---|---|---|---|---|---|
| worlds | 32 | 60 | 46 | 54 | 19 | 12 | 97 |
| gate − method | −0.033 | −0.010 | −0.007 | +0.010 | +0.002 | +0.024 | **+0.061** |

**Distribution of per-world differences** (B = 16, unweighted): mean +0.0149, **median +0.0002** (cluster-bootstrap
95 % [0.0000, 0.0030]), quartiles [−0.0077, +0.0318], 5 % / 95 % [−0.078, +0.157]; method better in 178 of 320
worlds (55.6 %), champion better in 142 (44.4 %). The best 10 % of worlds carry 109 % of the net gain: outside
them the method is net negative. The typical world sees no improvement.

**Calibration on underdetermined queries** (the R5 uniform prediction strictly inside (0, 1); 1,676 queries,
base rate 0.483): Brier 0.0878 (method) vs 0.1105 (gate); expected calibration error over ten bins 0.037 vs 0.049.
The method is better calibrated on queries the evidence does not decide; its largest bin deviations are in the
0.6–0.8 range (predicted 0.65–0.75, observed 0.57–0.59; about 100 queries).

## Fresh external evaluation (`r6-g-ext-fresh-v1`)

122 source groups never used in R5 (hash ranks 40–161), 8-node backward subnetworks, outside regulators clamped to 0.

| Contrast | B = 8 | B = 16 | B = 24 |
|---|---|---|---|
| primary gate − xdc[cgh_flat] | +0.0197 [0.0158, 0.0234] | **+0.0033 [0.0012, 0.0055]** | +0.0008 [−0.0006, 0.0023] |
| sharing cgh_flat − xdc[cgh_flat] | +0.0038 [0.0016, 0.0059] | +0.0011 [−0.0002, 0.0023] | +0.0006 [−0.0000, 0.0012] |
| vocabulary xdc[gate] − xdc[cgh_flat] | +0.0089 [0.0068, 0.0110] | +0.0014 [−0.0004, 0.0032] | +0.0001 [−0.0012, 0.0015] |
| generic sharing gate − xdc[gate] | +0.0108 [0.0072, 0.0143] | +0.0020 [0.0004, 0.0036] | +0.0007 [0.0000, 0.0015] |
| uniform − method | +0.0595 | +0.0429 | +0.0404 |
| GSR(0.5) − method | +0.0448 | +0.0428 | +0.0380 |

Mean Brier at B = 16: gate 0.0229, cgh_flat 0.0206, method 0.0195, uniform 0.0624. The panel is near ceiling at 16
observations; there is little left to predict.

- B = 8 prediction ("positive, mostly vocabulary plus a smaller sharing part"): **met**. +0.0197 = gate − cgh_flat
  (+0.0159, vocabulary of the flat code) + sharing (+0.0038).
- At B = 16 the primary is positive and its interval excludes 0, but neither component does on its own
  (sharing +0.0011 [−0.0002, 0.0023]; vocabulary +0.0014 [−0.0004, 0.0032]). Sharing over the gate base is
  separable from 0 (+0.0020 [0.0004, 0.0036]).
- Distribution (B = 16): median +0.0008 [0.0004, 0.0015], quartiles [−0.0003, +0.0063]; method better in 306 of
  449 (68 %). The best 10 % carry 138 % of the net gain.
- By hidden reuse: +0.010 (reuse 1, 15 instances), +0.002 to +0.006 elsewhere; no dose-response. Mean reuse 3.7,
  but **31 % of nodes are constants** created by clamping; reuse among non-constant nodes averages 2.3.
- Calibration on underdetermined queries (3,085): Brier 0.0228 vs 0.0266, ECE 0.010 vs 0.021.

## What this does and does not show

- Exact sharing improves forecasts on synthetic worlds **where rule types are reused** (+0.042 on those four strata)
  and makes them worse where they are not (−0.012 on the other four, −0.038 on the null). The pooled primary
  (+0.015) is an average of these two regimes, weighted by how we built the strata. It is not evidence that reuse
  is common in real systems.
- On published-model fragments the gain is small (+0.003 at 16 observations, +0.020 at 8, mostly vocabulary).
  These fragments are clamped and near ceiling. Whether sharing helps on **intact** published models is Track S.
- XDC is better calibrated than the generic champion on undetermined queries on both panels.
- Pre-lock disclosure stands: XDC was designed knowing the R5 strata, and the calibration and external-development
  panels were seen before the lock (`docs/R6_DESIGN_LOCK.json`).
