# R6 review package: reviewer entry point

Branch `iteration-6`; release `v0.6.0-dev` (prerelease). Release identities: `reports/RELEASE_CHECK_R6.md`.
Development evidence only: no confirmatory run, no freeze record, no paid inference, no weight changes.
This audit is by the implementation agent (Claude Opus); the reviewer decides acceptance.

Read in order:
1. `reports/R6_XDC_AUDIT.md` and `docs/R6_XDC_DERIVATION.md` (X)
2. `reports/R6_GENERALIZATION.md` (G6)
3. `docs/R6S_DESIGN_LOCK.json` and `reports/R6_SCALE.md` (S)
4. `docs/R6A2_DESIGN.md` and `reports/R6_AI_GATE_LOOP.md` (A2)
5. `reports/acceptance_r6.json`, `reports/CLAIM_LEDGER_R6.csv`, `reports/R6_EVIDENCE_MATRIX.md`
6. `docs/R6_FUNDING_BRIEF.md`

## Results by track (completion and scientific outcome are separate)

| Track | Completion | Outcome | Headline |
|---|---|---|---|
| X: audit XDC | complete | no defect | Independent oracle sharing no code: 216 cases, max difference 2.9e-12. The planted (\|b\|−1)! defect fails 12/24 (max 0.19). Lock and run event order verified. |
| G6: locked n = 8 evaluations | complete (analysed, not rerun) | supported_in_scope | Synthetic: +0.0149 [0.0088, 0.0211]. This is entirely in the four reuse-by-construction strata (+0.042); the other four are **adverse** (−0.012 [−0.019, −0.005]). Median world about 0; the top 10% of worlds carry 109% of the net gain. External fresh fragments: +0.0033 [0.0012, 0.0055]; the sharing part alone includes 0. The lock's planning value of 0.02 was not met. |
| S: XDC-EB at scale | complete (524/524) | supported_in_scope (small) | sub24, B = 8: +0.0087 [0.0037, 0.0148] (113 worlds, 28 groups, nothing missing). Intact models are null (13 worlds). No growth with n, no reuse dose-response. 227,280/227,280 fits certified. Against exact XDC at n = 12: equal at B8/16, about half the gain lost at B4. |
| A2: gate in the loop | complete (417/512 requests) | inconclusive (primary) | Qwen resolved@4 +0.031 [0, 0.094]; unsupported definite claims at b = 4 −0.41 [−0.59, −0.25] (15 → 2). Mistral identical in both arms. |

## Answers to the reviewer's eight checks (`03_ACCEPTANCE_AND_REVIEW.md`)
1. **Oracle independence and planted defect.** The oracle imports only numpy and the stdlib. It has its own rule space with an essential-input check, its own orbit types, its own simulator, and the closed-form Pólya-urn mass. The planted defect fails the oracle (`test_planted_defect_*`).
2. **Every R6 evaluation started after its lock, from that snapshot.**
   - `r6-g-eval-v1`: opened 01:05:01Z at lock `246d3cd` (01:05:01Z).
   - `r6-g-ext-fresh-v1`: opened 01:12:10Z.
   - `r6-s-eval-v1`: opened 04:15:44Z, from `072f051`, committed 04:15:41Z.
   - A2: the design was committed in `2dcf172` before the first request (01:52:08Z).
   - All R6 runs record `dirty: false`.
3. **G6 is faithful to the lock and reports where the effect is absent.** The null stratum is −0.038. The non-reuse strata are adverse. Published fragments at 16 observations are near ceiling, and the sharing part there includes 0.
4. **The XDC-EB fit is certified on every world and uses public evidence only.** Every fit is certified (Frank–Wolfe gap ≤ 1e-6). The fit is computed inside the public-payload path, which is audited before prediction. The gap to exact XDC is shown in `R6_SCALE.md` §5 and `eb_vs_xdc_n8.json`.
5. **The S comparator was chosen on calibration groups only**, and groups were split before any scoring. `analyze_s_calibration` refuses evaluation worlds, and the split is by group hash in the source manifest committed before calibration.
6. **Does S survive missingness and the exclusion of seen groups?** Missingness: yes; no outcome is missing, so the bounds equal the estimate. Seen groups: **cannot be tested**, because every evaluation group had contributed n = 8 fragments.
7. **A2 control on the same worlds, and request accounting.** The control ran on the same 32 worlds with the same seeds. All 417 attempts are in the ledger with phase `A2` (cap 512).
8. **R5 and R6 outputs byte-identical under the new code.**
   - 21/21 analyses regenerate byte-identically (`scripts/r6_regen_check.sh`).
   - Stored items recomputed with the current code (every 10th item of 9 earlier runs, `scripts/r6_replay_check.py`): 174/174 identical except wall-clock fields, and every stored prediction digest verifies (`reports/development_r6/replay_check.json`).

## Deviations and defects (`DECISIONS.md` D65–D69)
- **S-D1.** The locked S analyser omitted the declared exact-XDC secondary for the gate/cgh_flat bases. It is computed post hoc by `scripts/r6_s_supplementary.py`, and no locked number changes.
- **XDC-EB solver.** Calibration v1 used plain EM and left 27/89,400 fits uncertified. The solver was changed to SQUAREM and the tolerance declared at 1e-6. Calibration was rerun before the lock (v1 kept).
- **A2 backend.** The generic arm B was dropped before any request to fit inside 512, as the protocol permits.
- **Track S primary panel.** It is sub24, the protocol's fallback, because intact has 13 groups.
- **Track S budgets.** 4/8/16, not the suggested n/2n/4n (see below).
- **X notes**, not defects:
  - X-N1: `XDC.probabilities` returns P(node = 1).
  - X-N2: the reviewer's tests did not cover h = 2 with edits; the oracle does.
  - X-N3: a stated float bound.

## Where I believe the reviewer's plan or method is wrong (with evidence)
1. **"n, 2n and 4n observations" would have measured only the ceiling.** On sub24 calibration the best flat code's Brier is 0.064 at B = 8, 0.015 at 16, 0.004 at 32 and 0.000 at 64 (`s_calibration_v2.json`). At n = 24, the values n/2n/4n = 24/48/96 all lie at or beyond the ceiling. I used the protocol's own sizing rule (neither ceiling nor chance) and locked budgets 4/8/16.
2. **The intact panel cannot be the primary population.** Only 13 Biodivine lineages have 9 ≤ n ≤ 64 with indegree ≤ 3. The headline outcome in S4 ("positive on intact published models, growing with n") is unreachable with this corpus.
3. **"With and without groups seen at n = 8" is impossible.** All 133 evaluation groups across the four panels contributed n = 8 fragments, so S is not a held-out-source test. The plan should have required a second corpus.
4. **The S4 outcome map does not cover the actual result.** The result is a small positive on fragments, null on intact models, no growth with n and no reuse dose-response. That is neither "positive on intact" nor "synthetic only" nor "null everywhere".
5. **The G6 synthetic headline is an artefact of stratum mixing.** Equal stratum weights average four strata where reuse was planted (+0.042) with four where it was not (−0.012, adverse). The 0.02 planning value assumed a uniform effect. The lock's interpretation rule ("scope = worlds with reused rule types") is right; the headline number is not a property of any population.
6. **The external "hidden rule reuse" covariate is inflated by clamping.** 31% of nodes in the fresh n = 8 fragments are constants created by clamping outside regulators to 0. Reuse among non-constant nodes averages 2.3, against 3.7 overall. In S I report `reuse_nonconstant`.
7. **Exact XDC as the yardstick for XDC-EB.** At n = 8 on synthetic worlds, EB loses 0.003–0.007 Brier against exact XDC; at n = 12 on published fragments it loses nothing at B8/16. The plan presents XDC-EB as "an approximation to XDC", but on published fragments the gap is negligible except at the smallest budget. Calling it a promoted secondary undersells the scale result, and calling it XDC would oversell it.
8. **XDC itself:** no error found.

## Resources
- Model requests: 417 of 512 (global 1,498 of 3,072).
- Offline CPU: ≤ 18 h of 48 (4 workers).
- Model server: 0.42 h of 3.
- Reviewer-run G6 compute is not included.
