# Review package R2 — CausalGuard iteration 2 (for Codex's next independent review)

```
confirmatory_authorized: false
production_freeze_record: absent (docs/FREEZE_RECORD.json does not exist)
confirmatory runs: NONE executed (S1, S2, S3)
WP10 / WP11: not started
dating: all work is PRE-SPRINT (sprint 2026-11-13 to 2026-11-15); iteration 2 = 2026-11-10
```

Public repository: https://github.com/albertoHdzE/causalguard-epistemics. The release commit and tag are listed in
§8. The prior review (R1: reviewed `371b04e`, release `967fc9c`, tag `v0.1.0-dev`) and all iteration-1 records
are preserved unchanged. `reports/review_r1/` is committed verbatim.

## 1. What to review, in order

1. `reports/R2_EVIDENCE_MATRIX.md`: R01–R10, each with repair, regression test and re-run evidence.
2. `reports/DEVELOPMENT_REPORT_R2.md`: new development evidence (S2 670 worlds + MC diagnostic; S1 repair panel;
   S3 v2 diagnostics + qwen held-out panel).
3. `reports/DESIGN_SIZING_R2.md`: revised sizing for the revised endpoint (no promise of power for the small
   observed effect).
4. `configs/confirmatory.json` (proposal, `confirmatory_authorized: false`),
   `configs/endpoints/S2-primary-v2.json`, `src/causalguard/freeze.py`, `scripts/run_confirmatory.py`.
5. `DECISIONS.md` D23–D35 (iteration 2), including disclosed defects/interruptions D27, D32 and D35.
6. `reports/acceptance_r2.json`, `reports/CLAIM_LEDGER_R2.csv`, `artifacts/manifest_r2.json`,
   `reports/test-output-r2.txt`.

## 2. Fixed findings (summary; details in the evidence matrix)

| ID | One-line status |
|---|---|
| R01 | Float-equality verdicts removed; exact Boolean support / integer counts / SAT. Review tautology → `entailed`. |
| R02 | Exogenous S2 design v2 (design RNG stream fixed before the mechanism); novelty classified, never used to drop cases. |
| R03 | Runner v2 + `freeze.py`: typed record, preflight before any write, external runtime root, explicit resume; E2E fixture lifecycle S2 → kill → resume → S1 at one freeze commit. |
| R04 | Strict readers; torn tails quarantined with exact bytes; atomic per-attempt files; interior corruption fails closed. |
| R05 | Analysis bound to `S2-primary-v2` (refuses other specs), plan reconciliation, duplicate refusal, terminal rule + missing-outcome bounds. |
| R06 | Parent-enforced deadlines with process-group kill/reap; nested SIGALRM cannot cancel the item cap. |
| R07 | Exact majority; MC diagnostic predeclared and reported; v1 re-scored exactly. |
| R08 | Manifest r2 with required/optional groups; verifier exits non-zero when required files are absent; dedup against all dev corpora; null overlap audited only. |
| R09 | S3 arms B2 / D_cert / D_label / D_sample with matched turns; certificate arm named as privileged; baselines fitted on separate training worlds; complements/renamings nested. |
| R10 | Wording corrected; decoder = complete bundle; archive vs payload sums; 3/M withdrawn; matched noisy-MDL codes. |

## 3. Evidence that was re-run

| Run | Worlds/items | Result |
|---|---|---|
| S2-dev-v2 | 670 worlds | 670 ok (D27: missing `end` event only) |
| S2-dev-v2-repro | 670 worlds | identical scientific outputs, 0 / 670 differ (D31) |
| S2-dev-v2-mcdiag | 200 worlds | 200 ok |
| S1-dev-v2-panel | 98 worlds, 686 items | 686 ok |
| s3v2-diag-{qwen25_7b,gemma3_12b}-dev | 20 + 20 worlds | see §5 |
| s3v2-heldout-qwen25_7b-dev | 100 worlds | 100 ok; no gemma held-out panel (gate D29 G3 failed, D33) |
| Historical byte-level reproduction | v1 S1/S2 summaries | `scripts/reproduce_v1.sh`: both MATCH |

## 4. Claims that changed

- **S2.** The registered v1 primary (index − uniform-compatible, +0.063) is now a historical secondary. Under the
  revised primary (index − compatible-set majority, exact) the development estimate is **+0.0009 [−0.011,
  +0.012]**: *no clear index advantage detected*. This is not evidence of equivalence and not a refutation of
  simplicity priors in general. Under the mandatory uniform-H null the majority wins, −0.022 [−0.033, −0.011], as
  the Bayes argument predicts. Circuit − majority, +0.025 [+0.013, +0.036], is concentrated in the XOR-generated
  families and is not an index-method result. Structured − null (+0.023) is exploratory only.
- **S1.** Decoder charges are now the complete dependency bundle (18,339 B vs 8,340 B for codec.py alone).
  Archive and payload sums are separate. The independent-query 3/M bound is withdrawn.
- **S3.** "No transfer" becomes "no clear transfer detected". "Neither recognized refuted" applied to the
  initial arm only. Iteration-1 D feedback is renamed for what it was (witness-assisted, label-revealing).
  Iteration-2 results are in §5.
- **Noise.** Robustness is attributed to the two-part residual code (all codes evaluated), not to the index code.

## 5. S3 (development only; no S3 freeze proposed)

Runs and gate:
- qwen2.5:7b passed gate D29: diagnostic 20 worlds plus held-out 100 worlds, all ok.
- gemma-3-12b-it failed G3 (arm-A balanced accuracy 0.319, below chance). Its expansion stopped, and the 20-world
  diagnostic is reported as a floor diagnostic (D33).
- There is no gemma held-out panel. This is a declared scope reduction against the "≥120 worlds/model" target.

Held-out qwen (100 worlds):
- **Focus T_cert − T_label = −0.08 [−0.16, 0.00]** (discordant pairs 4 vs 12): no clear certificate-over-label
  transfer detected. This is not evidence of no effect.
- Balanced-item accuracy:

  | arm | accuracy |
  |---|---|
  | A | 0.433 |
  | C | 0.440 |
  | B2 | 0.391 |
  | D_sample | 0.465 |
  | D_label | 0.570 |
  | D_cert (privileged) | 0.970 |

- Train-fit surface rule: 0.374 on balanced items, 0.507 on natural items (A: 0.395 on natural items).
- Unaided, A answers "refuted" correctly on 1 of 108 refuted items.
- **Post-hoc observation (D34):** qwen adopts revealed labels in round 1 (300/300). Its matched self-critique
  turn then reverses all 98 entailed labels to "underdetermined". gemma does not reverse them (17/17 kept).
- Construct-validity limits:
  - verdict/probability mismatch in 2,342 of 5,188 parsed answers, so Brier is not read as calibration;
  - complement consistency 0.42;
  - renaming invariance 0.78.
- 3 length truncations, all in the D_cert critique turn.

**S3 is not ready for a freeze proposal.** The MDE table is in DESIGN_SIZING_R2 §S3.

## 6. Proposal for the reviewer's decision

- **S2 / S1: proposed ready for an independent freeze decision.** Proposal: `configs/confirmatory.json` with
  1,000 structured + 1,000 null S2 worlds and stress populations, and the unchanged S1 grid. Only the reviewer can
  issue `docs/FREEZE_RECORD.json` (schema `causalguard-freeze-record-v2`). The record binds
  `reviewed_source_tree_sha256` (`runner.source_tree_digest()`), `config_sha256`, `endpoint_sha256`,
  `development_manifest_sha256`, the approved studies/models and typed readiness. The containing freeze commit is
  supplied with `--freeze-commit` and verified as HEAD of a clean checkout, so the record does not reference
  itself.
- **S3: not ready** (see §5).
- Open choices for the reviewer: (a) the misspecified stress population (empty exact V(D) in ~98% of worlds at
  B16) could be redesigned or dropped; (b) whether to keep the structured − null difference as a named
  exploratory estimate.

## 7. Known limitations and disclosures

- D27: a runner accounting defect left `S2-dev-v2` without an `end` event. Results are complete, and a
  reproduction run is identical.
- D32: an operator interruption and resume of the gemma diagnostic, done to isolate the S1 latency panel.
- D30: held-out S3 panels ran with concurrent requests (2 or 4). Batched inference can change temperature-0
  outputs relative to serial execution.
- Proof traces and witness states are not stored; certificate levels are recorded outcomes of in-run checks, and
  items are deterministic and re-runnable from `plan.json`.
- A public-commit salt is a reproducibility identifier, not a secret seal; no-peeking is a process rule.
- Iteration-1 S2 records keep their mechanism-dependent design (R02). Only re-scoring was done on them.

## 8. Release identity

_Filled in at publication: commit, tag `v0.2.0-dev`, release asset digests, CI run, clean-clone check._
