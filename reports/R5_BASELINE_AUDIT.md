# R5 baseline audit (WP0) — implementation-agent audit, not independent approval

Date 2026-11-11. Auditor: Claude Opus (the R5 implementation agent). This is **not** the independent scientific
review of R4 requested in `delegation/REVIEW_R4_REQUEST_PROMPT.md`; it records what was re-checked before R5 work
depended on it.

## Identity

| Item | Value |
|---|---|
| Starting HEAD | `e6483a673303d69f0fbf43d52e30a6725b072542` (as inspected by the takeover; no advance) |
| R4 content commit | `957c8d73be5a3a5a6c301929f7f4036d70d70ac3` |
| Source tree digest at HEAD | `a8252d9555887fe52ddc3d9efbe9cf0725c9a6b01f892a4c408974ea6449ae35` |
| Untracked user work preserved | `HANDOFF.md`, `reports/takeover_r4/`, `delegation/FABLE_RESEARCH_PROMPT.md`, `delegation/ITERATION_5_OPUS_PROMPT.md`, `delegation/iteration_5/` committed unchanged in `3c0841a` |
| Tags/assets | v0.1.0-dev … v0.4.0-dev untouched; historical manifests not modified |
| Baseline tests | 448 passed in 167 s, unrestricted (no sandboxed localhost failure on this run) |

## Areas re-checked

| Area | Check | Result |
|---|---|---|
| Distinct-mechanism counts (R4 D) | NEW independent counter GEN-VE (explicit canonical enumeration, no Moebius, no s4 import) vs D vs explicit engine, 120 random queries n in {4,6,8}, h in {1,2}, all interventions; full-truth-table oracle n = 3 | 0 mismatches; oracle exact (tests `test_gen_ve_*`) |
| Projection semantics | canonical CNF projected count = unprojected count = distinct mechanisms (n = 3, two evidence sets); the R4 verdict encoding (ladder, exact-k selector, free unselected tables) counts 6 distinct single-node functions as a different number of projected models | trap confirmed and tested; the R4 encoding was never used for counting (B counts explicitly), so no R4 result is affected |
| Codec weights | `Averager.probability_exact` added (fraction form of the unchanged computation) | the float path is unchanged (`probability` = float of the fraction) |
| Oracle isolation | R5 G predictions are computed by `predict_public(json)` from a serialized payload audited by `s4.tasks.audit_public_payload`; prediction digest recorded before outcomes | test `test_public_payload_*` |
| Duplicates / isomorphs | R5 split audit: 0 shared source groups, 0 exact duplicates, 0 isomorphic cross-split pairs (64 vs 320) | `test_split_has_no_shared_groups_or_duplicates` |
| Proof levels (T03) | R4 pilot runs: every impossible-side cross-check is `"unsat"` (348 per model), none `"unsat_rup_checked"`: `Limits.proof_check` defaults to False | **R5-01 (interpretation, R4 scope):** R4 pilot certificates are SAT-solver assertions + witness replay, not checked proofs. R5 C records actual levels with RUP checking enabled in the release phase |
| Common gate cost (T02) | `s4/offline.stress_item` times workspace + `ws.check` only | confirmed; R5 C measures workspace and full release (check + common SAT cross-check + RUP + commit) separately |
| D52 commit parsing | not re-analysed in R5 (no R4 pilot reanalysis performed) | unchanged; remains an R4 review item |
| R3 repairs | not re-run (takeover reproduced 0/5 worker side effects and the missing-prediction refusals on 2026-11-11) | relied on takeover evidence |

## Defects

- **R5-01** (documentation/interpretation of R4; no code change): see proof levels above. Affected scope: wording
  of R4 claims about "RUP-checkable" gate decisions in the pilot. Historical reports are not edited.
- No reproducible semantic defect was found in R4 counting, weighting or isolation code.

## Changes to shared owners (R5, additive)

- `s4/mechspace.MechanismSpace(node_k=...)`: optional per-node bounds (Track M one-exception class). Default
  behaviour identical (tests unchanged).
- `s4/prior.Averager.probability_exact`: exact fraction; `probability` unchanged.
- `llm/harness.CallBudget(phase=..., phase_cap=...)`: per-phase suballocation in the same ledger.
- `runner`: optional per-worker process-group memory guard (`CAUSALGUARD_WORKER_RSS_LIMIT`).
