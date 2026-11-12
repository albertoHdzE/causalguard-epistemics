# R6 evidence matrix (assignment requirement → code / test / artifact / status)

Completion and scientific outcome are separate columns. The outcome vocabulary is the one in `03_ACCEPTANCE_AND_REVIEW.md`.

| Track / requirement | Code | Test | Artifact | Completion | Outcome |
|---|---|---|---|---|---|
| WP0 takeover inspection, runs complete | — | — | `reports/R6_TASK_LEDGER.md` | done | — |
| X: independent oracle (no shared code) | `tests/test_r6_xdc_oracle.py` (own rule space, orbits, simulator, closed-form Pólya mass) | `test_oracle_*` (216 cases), relabelling (60 per base) | `reports/R6_XDC_AUDIT.md` | done | no defect: max diff 2.9e-12 |
| X: planted defect fails the oracle | monkeypatch drops (\|b\|−1)! | `test_planted_defect_*` | audit §3 | done | fails 12/24, max 0.19 |
| X: derivation and limits | — | — | `docs/R6_XDC_DERIVATION.md` | done | — |
| X: event order (lock before evaluation) | — | — | audit §5 | done | `f640e70` 00:59Z < lock `246d3cd` 01:05:01Z ≤ run open 01:05:01Z |
| G6: locked n = 8 evaluations analysed, not rerun | `analysis/r5_analysis.py::analyze_g_r6`, `analyze_g_r6_extras` | — | `reports/R6_GENERALIZATION.md`, `development_r6/g_*` | done | synthetic supported_in_scope (+0.0149), confined to reuse strata; external small positive (+0.0033) |
| G6: distributions, adverse strata | `analyze_g_r6_extras` (labelled post hoc) | — | `g_*_extras.json`, figures | done | adverse outside reuse strata (−0.012) |
| S: XDC-EB, certified fit | `r5/priors.py::fit_type_weights`, `XDCEB` | `test_r6_scale.py` (brute force, optimality, a → ∞) | `reports/R6_SCALE.md` §1 | done | 227,280/227,280 fits certified |
| S: sparse support-signature masses (no 2^n tables) | `r6/scale.py::SparseMasses`, `base_weights` | `test_sparse_masses_equal_dense_xdc` | §1 | done | ≤ 0.43 s median at n = 60 |
| S: inventory, group split before scoring | `r6/population.py`, `r5/external.py` (`backward_subnetwork`, `_tabulate`) | R5/R6 inventories `cmp`-identical | `artifacts/r6s_source_manifest.json` | done | intact 13 groups < 20 → sub24 primary (declared fallback) |
| S: comparator chosen on calibration groups only | `analyze_s_calibration` (refuses evaluation worlds) | — | `docs/R6S_DESIGN_LOCK.json` (`072f051`) | done | flat[circuit], xdc_eb[circuit]\|a16\|loo |
| S: evaluation after lock | runner from snapshot `072f051` | — | `runs/r6-s-eval-v1` (opened 04:15:44Z, lock 04:15:41Z) | done 524/524 | — |
| S: primary + missingness bounds | `analyze_s` | — | `development_r6/s_evaluation.json` | done | supported_in_scope: +0.0087 [0.0037, 0.0148], bounds equal estimate |
| S: groups seen at n = 8 excluded | `analyze_s` | — | lock `population.groups_seen_in_n8` | not computable | every evaluation group was seen |
| S: gap to exact XDC | `scripts/r6_s_supplementary.py` (post hoc; defect S-D1) | — | `s_evaluation_supplementary.json`, `eb_vs_xdc_n8.json` | done | ≈ 0 at B8/16 (n = 12); half the gain lost at B4 |
| S: effect vs n and reuse | `analyze_s` | — | `R6_SCALE.md` §4 | done | no growth with n; no dose-response with reuse |
| A2: gate in the loop | `r5/investigation.py::ai_episode(gate_loop=True)` | `tests/test_r6_gate_loop.py` (3) | `docs/R6A2_DESIGN.md` (before requests) | done | — |
| A2: paired pilot, same worlds, ≤ 512 requests | configs `configs/r6/a2_*` | — | `reports/R6_AI_GATE_LOOP.md`, `a2_gate_loop.json` | done 417/512 | resolved@4 inconclusive (qwen +0.031 [0, 0.094]); unsupported claims −0.41 [−0.59, −0.25] |
| Byte-identity of R5 and R6 outputs under the new code | `scripts/r6_regen_check.sh` | full suite | `reports/RELEASE_CHECK_R6.md` | see release check | — |
| WP7 ledger, acceptance, brief, release | `scripts/build_manifest.py r6` | — | `CLAIM_LEDGER_R6.csv`, `acceptance_r6.json`, `docs/R6_FUNDING_BRIEF.md`, `artifacts/manifest_r6.json`, `REVIEW_READY_R6.md` | see release check | — |
