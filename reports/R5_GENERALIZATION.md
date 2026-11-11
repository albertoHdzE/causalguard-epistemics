# R5 Track G — unseen inference on structurally held-out worlds (development)

Runs: `r5-g-cal-v1` (64, champion selection), `r5-g-eval-v1` (320), `r5-g-ext-intact-v1` (4),
`r5-g-ext-transformed-v1` (159). Snapshot `dd193ce` (design lock committed before every evaluation run).
Analyses: `reports/development_r5/g_*.json` (regenerate with `python -m causalguard analyze-r5 --track g ...`).
No model calls. All planned items completed; no failed attempts.

## Bottom line

On worlds whose structure was **not** generated to match the CGH code, the full CGH prior forecasts unseen
outcomes about as well as the best generic comparator chosen on calibration (the flat **gate**-catalogue code), and
the hierarchy contributes nothing measurable. Codec-weighted averaging in general (ours or generic) clearly beats
uniform averaging. The R4 hierarchy gain did not generalize beyond generator-matched families.

## Calibration (64 instances, B = 16; `g_champion_selection.json`)

| Candidate | uniform | circuit | **gate** | gsr_a50 | gsr_a25 | gsr_a75 |
|---|---:|---:|---:|---:|---:|---:|
| mean world Brier | 0.0893 | 0.0840 | **0.0727** | 0.0872 | 0.0872 | 0.0872 |

Champion locked: **gate**. (Full CGH 0.0730 on calibration was recorded but not used for selection.) GSR is
essentially insensitive to alpha: the program-mass ratio between components is extreme, so one component dominates
the posterior. GSR is a real, exactly summed generic structured prior, but it was weaker than the flat gate code here.

## Primary (evaluation, B = 16, 320 worlds, 280 source groups, complete predictions)

**Brier(gate) − Brier(full CGH) = +0.0020, 95 % CI [−0.0041, +0.0082]** (positive favours CGH).
Worst-case missingness bounds coincide with the estimate (no refusals at B = 16). Practical planning value 0.02: not
reached; the interval excludes it. **Scientific outcome: no detected advantage.**

## Secondaries (evaluation)

| Contrast (positive favours the second) | B = 8 | B = 16 | B = 24 |
|---|---|---|---|
| gate − cgh_prior (primary at 16) | bounds [−0.0009, +0.0084] (24 refused queries) | +0.0020 [−0.0041, 0.0082] | −0.0014 [−0.0053, 0.0026] |
| uniform − cgh_prior | incomplete | **+0.0169 [0.0106, 0.0229]** | **+0.0159 [0.0109, 0.0207]** |
| hierarchy: cgh_flat − cgh_prior | incomplete | +0.0004 [−0.0004, 0.0016] | 0.0000 [0, 0] |
| analytic vocabulary: cgh_flat_noanalytic − cgh_flat | 0.0000 [−0.0023, 0.0024] | −0.0014 [−0.0058, 0.0029] | −0.0016 [−0.0046, 0.0013] |
| shortest cgh_prior model − cgh_prior | incomplete | +0.0454 [0.0354, 0.0561] | +0.0161 [0.0102, 0.0224] |

Mean world Brier, B = 16: cgh_prior_noanalytic 0.0762, cgh_flat_noanalytic 0.0767, **cgh_prior 0.0776**,
cgh_flat 0.0781, gate 0.0796, gsr 0.0896, circuit 0.0911, uniform 0.0945, index 0.0958, shortest cgh_prior 0.1230.
Accuracy (threshold 0.5) at B = 16: gate 0.891, cgh_prior 0.890, uniform 0.863.

Readings: (i) averaging beats selecting one shortest model by a wide margin; (ii) weighting by any reasonable
description length helps over uniform; (iii) the analytic vocabulary does not help (slightly worse than plain LUTs,
not significant); (iv) the TEMPLATE/MODULE hierarchy is inert on these strata (B = 8: 3 worlds hit the structured
enumeration cap → 24 refused queries, reported as bounds, never dropped).

**Logical strata (B = 16).** 874 determined queries: Brier 0 for every predictor (exact). 1,686 underdetermined:
cgh_prior 0.1179, cgh_flat 0.1186, gate 0.1208, uniform 0.1436.

## Per stratum (B = 16, mean world Brier; 40 worlds each)

| Stratum | gate | cgh_prior | cgh_flat | uniform | gsr_a50 |
|---|---:|---:|---:|---:|---:|
| template_exceptions | 0.1006 | 0.0947 | 0.0983 | 0.0998 | 0.0874 |
| imperfect_modules | 0.0700 | 0.0556 | 0.0556 | 0.0900 | 0.0900 |
| shared_motifs | 0.0949 | 0.0866 | 0.0866 | 0.1028 | 0.0856 |
| feedforward_hetero | 0.0253 | 0.0293 | 0.0293 | 0.0827 | 0.0827 |
| feedback_canalizing | 0.0756 | 0.0672 | 0.0672 | 0.0953 | 0.0953 |
| mixed_parity_thresh | 0.0486 | 0.0691 | 0.0691 | 0.1035 | 0.1035 |
| rewired_control | 0.0929 | 0.0785 | 0.0785 | 0.0826 | 0.0726 |
| uniform_H (null) | 0.1287 | 0.1400 | 0.1400 | 0.0997 | 0.0997 |

Only template_exceptions shows any hierarchy effect (cgh_flat − cgh_prior +0.0036). Every simplicity prior is worse
than uniform on the uniform-H null (expected: the null has no simplicity bias). GSR wins on template_exceptions,
shared_motifs and rewired_control (its shared-rule assumption fits them) and equals uniform elsewhere. Per-stratum
values are descriptive (40 worlds; no stratum-level inference).

## External panels (separate populations; never pooled)

- **Intact** (4 source groups; descriptive only): group differences gate − cgh_prior from −0.0007 to +0.0194, mean
  +0.0065; leave-one-source-out means 0.0022–0.0089. Too few groups for an interval.
- **Transformed** (40 source groups, 159 instances; deterministic 8-node subnetworks with outside regulators
  clamped to 0): gate − cgh_prior **+0.0013 [−0.0025, +0.0048]**; hierarchy 0.0000 [0, 0];
  uniform − cgh_prior **+0.0428 [0.0374, 0.0477]**.
These are published models after a declared transformation, not biological measurements; clamping many boundary
inputs to 0 produces many constant nodes, which favours any simplicity prior over uniform.

## Cost

Exact codec averaging (Averager) build: 414 s total over 320 worlds at B = 16 (≈1.3 s/world); GSR: 0.2 s total.
Offline G CPU ≤ 0.70 h (upper bound) for all G runs.

## Limits

Our generators, our champion pool. The comparator set is finite; GSR's parameter grid was coarse and turned out
irrelevant. DICT sharing remains excluded from the CGH prior. Learned order/dictionaries were not attempted. No
claim about real systems, universal priors or Kolmogorov complexity follows.
