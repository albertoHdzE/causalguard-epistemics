# Confirmatory protocol — PROPOSED (not frozen)

This document plus `configs/confirmatory.json` is the freeze proposal for review. Nothing here has been run on confirmatory data; no confirmatory world exists (the salt is derived from the future freeze commit). Changes after review are logged in DECISIONS.md and require a new freeze.

## Units and splits
- Independent unit: the generated world. Queries, budgets, regimes, noise draws and LLM calls are nested within worlds and never counted as independent.
- Development split: salt `dev-v1` (public). Confirmatory split: salt `confirm-` + sha256(`<freeze commit>|causalguard-confirmatory-v1`)[:16].
- Cross-split duplicates: every confirmatory S2 world is checked for exact isomorphism (all 7! relabellings) against the development corpus and excluded with a log entry if isomorphic (`runs/<id>/EXCLUSIONS.json`).
- Access: `scripts/run_confirmatory.py` writes `ACCESS_LOG.jsonl`; it refuses to run without a clean tree at the freeze commit, a matching `docs/FREEZE_RECORD.json`, the authorization phrase, and an unused run id.

## S2 (primary study)
- Worlds: n = 7, hypothesis class k ≤ 3 (complete per node: 7,856 functions). Families (strata): conjunctive, canalizing, parity, random_lookup, modular. Realizable 200/family (N = 1,000). Separately labelled: misspecified 50/family (two nodes with 4 inputs), shift 250 (composed gates with negations, in-degree exactly 3), noise stress 50/family (flip rates 0.01/0.05/0.10; separate two-part MDL experiment).
- Evidence regimes per world (nested budget prefixes 2…64): uniform designed states (primary), observational trajectories, clamp trajectories, disagreement-guided active designs.
- Hidden queries per world: 8 state-holdout (unobserved states, h = 1) + 16 intervention queries (8 initial_edit, 8 persistent_clamp; h ∈ {1,2,3}); keys disjoint from every observed (state, intervention, horizon).
- **Primary endpoint:** realizable, uniform_states, budget 16, intervention queries: Δ_w = accuracy(minimum index-code compatible model, fixed tie-break) − expected accuracy(uniform compatible model). Equal-weight mean of the five family means; stratified paired cluster bootstrap (5,000 replicates, seed 20261109, percentile 95% CI). Missing outputs (empty V(D)) score 0; complete-case sensitivity. Minimum meaningful difference 0.05.
- Interpretation: the hypothesis "shorter decodable index descriptions improve hidden intervention prediction over uniform compatible selection under this class and these generators" is supported if the CI lower bound > 0; the size is judged against 0.05. A CI including 0 is inconclusive unless narrow; equivalence is not tested. A positive result does not show that shortest index codes are optimal (development already shows the circuit code doing better) or that compression implies truth.
- Registered secondary (exploratory, no multiplicity correction, no p-values): index − circuit; index − uniform on state-holdout queries; per-family index − uniform; consensus wrong-certification rate (realizable must be exactly 0 — a non-zero value is an implementation defect that stops the run); misspecified/shift/noise summaries; active − random measurement policies at budgets 4/8/16.

## S1 (engineering / formal correctness)
- Small grid n ∈ {4,6,8,10} × 6 families × 50 worlds; large grid n ∈ {16,32,64,128,256} × 5 families × 30 worlds; dense random excluded by design above n = 10.
- 24 fixed queries/world (membership; ∃/∀ with planted and free constructions; h ∈ {1,2,4,8}; clamp interventions).
- Caps fixed from development: 20 s per query; cube budget 20,000 cubes; BDD 2,000,000 nodes; RUP proof checks n ≤ 256 with a 2M-step budget.
- Endpoints: exact mismatches vs the exhaustive reference (must be 0), cross-backend disagreements, certificate levels, capped completion, latency of completed queries (with denominators), construction time, peak RSS, archive bits per codec on identical objects.

## S3 (secondary study)
Filled from the v2 development pilot in `reports/DESIGN_SIZING.md` and `configs/confirmatory.json["S3"]`. Primary S3 contrast: D vs B on final-verdict balanced accuracy (world-clustered bootstrap); D-label is a privileged control; correct→wrong revisions are reported. Mock records are excluded by construction.

## Stopping and failures
Stop only for an oracle/codec defect, corrupted logs or resource exhaustion — never for unfavourable effects. Failed and timed-out items are retained and counted. A defect affecting confirmatory data invalidates that run (kept and disclosed); a revised claim needs a re-freeze and a fresh salt.

---

## Amendments after review R1 (iteration 2, 2026-11-10; pre-sprint; made after development inspection and BEFORE any confirmation)

These amendments follow the Codex R1 decision (`reports/review_r1/DECISION.json`). The text above is preserved
as the iteration-1 protocol.

1. **S2 primary (amended).** `S2-primary-v2` (`configs/endpoints/S2-primary-v2.json`) is world-level
   intervention accuracy of the minimum index-code selection minus the compatible-set majority predictor.
   Population: realizable structured worlds (n=7, k≤3), five families equally weighted. Uniform designed
   measurements, budget 16, 16 intervention queries (h∈{1,2,3}, both intervention types). Majority ties score
   0.5; the index code keeps its fixed world-independent tie-break. The question is two-sided superiority with
   magnitude reported against 0.05; there is no equivalence claim. The analysis executes only this spec
   (`analysis.s2_analysis.check_endpoint`).
2. **Historical and named secondaries.** Index − random-compatible (the v1 primary) is a historical secondary.
   Circuit − majority and index − circuit are named secondaries with per-family breakdowns. h=1 and h>1 are
   reported separately, as are novelty classes (observed-transition equivalents, novel effective input,
   multistep interpolation, multistep with an unobserved transition). No confirmatory significance claims are
   made for exploratory collections.
3. **Exogenous design (s2-design-v2).** All measurement inputs, holdouts, trajectory start/clamp specifications
   and queries are drawn from a design RNG before the mechanism is evaluated. Observational/clamp regimes follow
   only their own acquired public history.
4. **Comparator numerics.** The posterior is exact by integer counts (h ≤ 3). Monte Carlo is a labelled
   diagnostic only.
5. **Mandatory uniform-H null.** IID canonical functions uniformly from the complete class. Development overlap is
   audited and reported, never excluded (an explicit exception to disjoint-mechanism exclusion). A sensitivity
   with semantic duplicates grouped is reported where relevant.
6. **Structured populations at confirmation.** A world isomorphic to any development world is excluded and
   replaced by the next index (deterministic replenishment, logged in the plan). Within-split duplicates are
   retained and reported.
7. **Terminal rule.** Every planned world must reach a terminal ok result. Otherwise the primary is reported as
   incomplete, with bounded missing-outcome sensitivity and no planned-N claim.
8. **S3 (development only).** Arms A, B2, C, D_cert, D_label, D_sample and E, plus probes T_A, T_B2, T_cert,
   T_label and T_sample (D28). The pilot focus is T_cert − T_label target-item accuracy (within-world context
   reuse beyond a disclosed source answer). No learning or cross-world claims; no S3 freeze.
9. **Execution.** Runtime records live outside the frozen checkout. Readiness is typed (`freeze.py`). A revise
   decision cannot authorize anything. A public-commit salt is a reproducibility identifier, not a seal.
