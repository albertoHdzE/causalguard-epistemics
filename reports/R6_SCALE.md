# R6 Track S: a learned-dictionary prior (XDC-EB) on published Boolean models up to 64 nodes

Status: development evaluation, 2026-11-12. Not a confirmatory study. No model calls.
- Design lock: `docs/R6S_DESIGN_LOCK.json`, committed in `072f051cb69a` at 04:15:41Z.
- Evaluation run `r6-s-eval-v1`: executed from that snapshot and opened at 04:15:44Z. 524 of 524 planned items finished, with no failures and no missing items. It ended at 05:43:52Z.
- Locked analysis (`analyze-r5 --track s`): `reports/development_r6/s_evaluation.json`.
- Supplementary analysis: `scripts/r6_s_supplementary.py`, output `reports/development_r6/s_evaluation_supplementary.json`. It was run after the evaluation. Section 5 explains why.

## 1. What was built
- **XDC-EB** (`r5/priors.py::fit_type_weights`, `XDCEB`).
  - It treats rules as independent draws from a mixture `p` over order-free rule types.
  - `p` is the maximiser of a concave marginal likelihood with a Dirichlet(a·G0) regulariser. The fit uses SQUAREM-accelerated EM with a monotone safeguard.
  - Each fit carries an optimality **certificate**: the Frank–Wolfe duality gap is at most 1e-6 nats.
  - Given `p`, prediction is the flat code with base `p`. This is exactly XDC at θ = ∞ with G0 = p. Brute-force agreement is tested in `tests/test_r6_scale.py`.
- **Sparse support-signature masses** (`r6/scale.py::SparseMasses`).
  - All four base codes are invariant to which inputs a rule reads. I checked this at n = 8, 24 and 64 (`base_weights`).
  - Rule-type masses are therefore counted from the distinct (care, value) schema signatures of the evidence. That takes O(C(n, 3)) supports, never 2^n states.
  - Only h = 1 queries are supported at this scale.
  - A test confirms the sparse masses equal the dense XDC computation at n = 8.
- **Exact XDC** (sum over set partitions) is exponential in n. It is computed only for n ≤ 12 (`XDC_EXACT_MAX_N`), with the gate and cgh_flat bases.

**Fit certificates.**
- Calibration v2: 89,400 of 89,400 fits certified (max gap 1.0e-6).
- Evaluation: 137,880 of 137,880 certified (max gap 1.0e-6).
- Calibration v1 used plain EM and left 27 fits uncertified (gap up to 3.8e-4). It was replaced before the lock; see the lock's `seen_before_lock`.

**Cost.** Median wall time per world and budget, all predictors together, one worker:

| n | 12 (includes exact XDC) | 24 | 48 | 55 | 60 (cal) |
|---|---|---|---|---|---|
| median s | 17.9 | 0.13 | 0.14 | 0.29 | 0.43 |
| max s | 18.5 | 3.6 | 2.6 | 2.7 | 1.0 |

The learned prior costs under a second up to 64 nodes. Exact XDC dominates the cost at n = 12.

## 2. Population: who is in it, and why the primary panel is sub24
The population is the pinned Biodivine models (commit 314b2fed) with indegree ≤ 3. Groups are publication lineages. Group-level split: the first ceil(G/4) groups by sha order go to calibration (`artifacts/r6s_source_manifest.json`).

| Panel | Instances | Groups | Evaluation groups |
|---|---|---|---|
| intact (9 ≤ n ≤ 64) | 14 | 13 | 12 |
| sub12 (backward-BFS fragments) | 562 | 122 | 91 |
| sub24 | 151 | 36 | 28 |
| sub48 | 8 | 2 | 2 |

- The protocol's intact panel has only 13 eligible groups. That is fewer than the 20 the protocol needs, so its declared fallback (sub24) is the primary panel.
- **Every evaluation group in every panel had already contributed 8-node fragments to an R5 or R6 n = 8 panel.** So the "without groups seen at n = 8" contrast cannot be computed. This is not a held-out-source test.

## 3. Primary result (locked)
Primary contrast: Brier(flat[circuit]) − Brier(xdc_eb[circuit]|a16|loo) at B = 8 on the sub24 evaluation groups. Positive means sharing helps. Intervals are from a source-group cluster bootstrap (10,000 replicates).

**+0.0087 [0.0037, 0.0148]**
- Data: 113 worlds in 28 groups, with no missing outcomes, so the worst-case bounds equal the estimate.
- Brier scores: flat 0.0820, method 0.0733.
- Per-world differences: median +0.0023, quartiles [−0.0040, +0.0171]. The method is better in 63% of worlds.

Outcome against the lock's rule: **positive on published-model fragments**. The interval excludes 0 and nothing is missing. The effect is small: about 11% of the flat code's Brier.

Recorded predictions against outcomes:

| Prediction (before evaluation) | Outcome |
|---|---|
| sub24 B8: small positive, abs < 0.01, interval may include 0 | +0.0087, interval excludes 0. **Held.** |
| sub12: about zero or negative | +0.0011 [−0.0014, 0.0037]. **Held.** |
| intact: near ceiling at B ≥ 8, too few groups | B8 −0.0037 [−0.0176, 0.0103], 13 worlds. **Held (null, uninformative).** |
| no growth with n | **Held** (see the table below) |

## 4. Secondaries (locked)
Flat − method per panel and budget; positive favours XDC-EB.

| Panel (worlds / groups) | B = 4 | B = 8 | B = 16 |
|---|---|---|---|
| sub12 (390 / 91) | +0.0035 [0.0016, 0.0054] | +0.0011 [−0.0014, 0.0037] | +0.0012 [−0.0013, 0.0038] |
| **sub24 (113 / 28)** | +0.0084 [0.0039, 0.0137] | **+0.0087 [0.0037, 0.0148]** | −0.0004 [−0.0050, 0.0041] |
| sub48 (8 / 2) | +0.0164 [0.0125, 0.0203] | +0.0076 [0.0008, 0.0144] | +0.0030 [0.0000, 0.0061] |
| intact n 9–55 (13 / 12) | +0.0073 [−0.0002, 0.0156] | −0.0037 [−0.0176, 0.0103] | +0.0056 [−0.0004, 0.0146] |

How to read the table:
- **Budget.** The gain is confined to the low budgets. At B = 16 every flat code is near its ceiling (sub24 flat Brier 0.022).
- **Size.** The sub12 < sub24 < sub48 ladder rises at B = 4 and B = 8. But sub48 has 2 groups and by the lock's own rule cannot carry a claim. On intact models the correlation of the world difference with n is +0.37 at B = 8, from 13 single worlds. The lock requires the intact correlation and the ladder to agree with a usable ladder, which is not available. **No growth with n is claimed.**
- **Reuse (dose–response).** The gain is not organised by how often non-constant rules repeat. At sub24 B = 8 the correlation of the world difference with reuse share is −0.05. For comparison, R6 G6 on synthetic n = 8 worlds showed +0.061 at reuse 6+ and −0.033 at reuse 0. Here the most-reusing stratum (12+, 84 worlds) gains +0.0088, which equals the panel average.
- **Clamping.** The effect is similar across clamped-edge fractions: at sub24 B = 8, +0.0081 below 0.1, +0.0093 for 0.1–0.3, +0.0074 at or above 0.3.
- **Vocabulary** (XDC-EB[gate] − XDC-EB[cgh_flat], same a and mode) is mixed:
  - sub24: +0.010 at B4 [0.007, 0.013]; +0.002 at B8 [−0.002, 0.006].
  - sub12: +0.010 at B4; +0.005 at B8.
  - The cgh_flat base is better at low budget.
- **Against uniform.** XDC-EB beats the uniform flat code everywhere (sub24 B8 +0.057). This is a weak comparator and is not the claim.

## 5. The gap between XDC-EB and exact XDC
This was declared as a secondary ("exact xdc[gate|cgh_flat] where n ≤ 12"). The locked analyser computes it only for the method's own base (circuit), for which exact XDC was never run. As a result, the locked JSON lacks it (**defect S-D1**, found after the evaluation). `scripts/r6_s_supplementary.py` computes the declared contrast on the sub12 evaluation groups, without changing any locked number. Columns are Brier differences; for the first two, positive favours the second term.

| Base, B | flat − exact XDC | flat − XDC-EB | XDC-EB − exact XDC (positive: EB worse) |
|---|---|---|---|
| cgh_flat, 4 | +0.0083 [0.0051, 0.0119] | +0.0050 [0.0038, 0.0063] | **+0.0033 [0.0011, 0.0057]** |
| cgh_flat, 8 | +0.0045 [0.0023, 0.0067] | +0.0047 [0.0034, 0.0061] | −0.0002 [−0.0014, 0.0010] |
| cgh_flat, 16 | +0.0022 [0.0005, 0.0040] | +0.0022 [0.0010, 0.0036] | −0.0000 [−0.0009, 0.0008] |
| gate, 4 | +0.0089 [0.0059, 0.0121] | +0.0045 [0.0035, 0.0056] | **+0.0043 [0.0022, 0.0067]** |
| gate, 8 | +0.0137 [0.0101, 0.0175] | +0.0131 [0.0106, 0.0157] | +0.0006 [−0.0008, 0.0021] |
| gate, 16 | +0.0033 [0.0015, 0.0052] | +0.0033 [0.0021, 0.0046] | +0.0000 [−0.0009, 0.0009] |

What the gap shows:
- On published 12-node fragments, XDC-EB recovers essentially all of exact XDC's gain at B = 8 and 16. At B = 4 it recovers about half: exact XDC adapts its concentration θ to very little evidence, while the plug-in `p` cannot.
- At n = 8 on synthetic calibration worlds the gap was larger (cgh_flat: +0.0031 at B8, +0.0073 at B16; `eb_vs_xdc_n8.json`).
- Exact XDC is not available above n = 12, so the gap at n = 24 is **not measured**.
- Caution on the base choice: the largest sharing gain is on a weak flat base. On sub12 B8 the gain is +0.0137 for gate, against +0.0011 on the locked circuit base. Most of what sharing gains over a poor vocabulary, a better vocabulary also gains. Sharing has been demonstrated only on top of the best flat code, and only at sub24.

## 6. What this does and does not show
- **Does show:** on fragments of published models (24 nodes, 28 held-out lineages), a learned rule-type mixture fitted to the evidence improves Brier at a small evidence budget by about 0.009 over the best fixed flat code. Every fit is certified, and the method costs under a second per world up to 64 nodes.
- **Does not show:**
  - an effect on whole published models (13 worlds; null);
  - growth with network size;
  - dose-response with rule reuse, so the mechanism behind the gain is unidentified at this scale;
  - transfer to unseen sources (every evaluation lineage contributed to an n = 8 panel);
  - any effect at higher budgets.
- The selected flat base and regulariser were chosen on 8 calibration groups. The B = 8 contrast was the primary, as locked. The effect is under 0.01 and should be treated as a pilot-scale signal.
