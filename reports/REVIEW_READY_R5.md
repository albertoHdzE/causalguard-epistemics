# R5 review package — reviewer entry point

Implementation agent: Claude Opus. This is an implementation-agent audit, **not** independent scientific approval.
Development only: no freeze record, no confirmatory run, no paid inference, no weight changes.

| Identity | Value |
|---|---|
| Branch | `iteration-5` (from `e6483a6`; R4 content `957c8d7`) |
| Reviewed content commit | `b6aeab3d4e26cc9344001116838fde8f6d668024` (CI green: ubuntu, macOS, upstream parity) |
| Design lock | `docs/R5_DESIGN_LOCK.json`, committed in `dd193ce` before every evaluation run |
| Tag / release | `v0.5.0-dev` (peeled commit in `reports/RELEASE_CHECK_R5.md`), prerelease asset `causalguard-dev-runs-v0.5.0-dev.tar.gz`, sha256 `e0627fe50efc2bc414c2524e6f9c67828e13d1b057ef04206b196a6353f65089` |
| Manifest | `artifacts/manifest_r5.json` (1,525 required files, COMPLETE locally); older manifests untouched |
| Tests | 469 passed (`reports/test-output-r5.txt`) |

## Results by track (completion and scientific outcome are separate)

| Track | Completion | Outcome | Key number |
|---|---|---|---|
| G unseen inference | complete (320/320; external 4 + 159) | **no detected advantage** | gate − full CGH = +0.0020 [−0.0041, 0.0082]; hierarchy +0.0004; CGH − uniform −0.017 |
| C counting/cost | implementation partial (external compiler not run), evaluation complete | **adverse vs generic counter; positive vs SAT** | GEN-VE 4–11× faster than D at n = 32–64; D 128/128 vs SAT 99/128 at n = 64; 640 counts, 0 mismatches |
| A AI investigator | complete (2 × 64 × 2 arms) | **adverse** | resolved@4 AI+D − EIG: −0.109 (mistral), −0.344 (qwen); D vs generic 0.000 |
| M wrong assumptions | complete (3 × 40) | **supported in scope** | current gate 10/103 false verified; challenge policy 5 false at 0.231 vs 0.291 coverage, no realizable loss |

Reports: `R5_GENERALIZATION.md`, `R5_COUNTING_AND_COST.md`, `R5_AI_INVESTIGATION.md`, `R5_ASSUMPTION_FAILURES.md`,
`CLAIM_LEDGER_R5.csv`, `R5_EVIDENCE_MATRIX.md`, `acceptance_r5.json`, `docs/R5_FUNDING_BRIEF.md`,
`docs/R5_COUNTING_DERIVATION.md`, `docs/R5_PROTOCOL.md`, `R5_BASELINE_AUDIT.md`, `R5_TASK_LEDGER.md`.

## Plain-English answers

- **What OUR method contributed:** exact, auditable counts and probabilities over all compatible mechanisms, a
  checking gate that blocked every unsupported AI claim, and a measured account of when proofs depend on assumptions.
- **Where it helped:** weighting by description length (ours or a generic codec) beats uniform averaging; our
  representation is much faster than the generic SAT workspace; the gate stopped 138 unsupported Qwen certainty claims.
- **Where it did not:** the hierarchical prior did not beat a generic codec on held-out structure; our counter was
  slower than an independent generic counter at k = 3.
- **What the AI contributed:** in investigation, negative — both models stopped early and resolved fewer targets
  than the exact controller they were given.
- **What remains unsafe:** a verified claim is only as good as the declared class; with consistent-but-wrong
  assumptions ~10 % of releases were false; the challenge policy halves that, not eliminates it.
- **Next funding tranche:** assumption-aware verified inference on externally authored systems (see brief).

## Deviations and defects (all disclosed in `DECISIONS.md` D54–D61)

- D55: ganak/d4 not run (permission / arm64 build) — knowledge-compiler comparison incomplete.
- R5-02 (calibration only): AI stop action rejected; v1 smoke failed gate; prompt v2.
- R5-03: C v1 failed before timing (daemonic workers); rerun v2.
- R5-04: GEN-VE int64 overflow at n = 64 (8 cells); rerun v3; counts then matched D 128/128.
- Intact external panel has 4 source groups (descriptive only). Learned order/dictionaries not attempted.
- `docs/R5_COUNTING_DERIVATION.md` §7 says "benchmark pending" (hashed in the lock; not edited). The result is in
  the C report.

## Resources

1,081 / 3,072 model requests; ≤ 3.86 offline CPU-h (+ ≈ 0.3 h untracked probes) / 64; 1.23 server-h / 12.

## Recommended next decision (not self-authorized)

Lead with an exact, assumption-aware verification layer, not with a simplicity-prior advantage or AI-led
investigation: one main study on externally authored systems comparing the current gate, the challenge policy and an
improved public falsification policy at matched coverage; include a knowledge-compiler comparator on a machine where
it is authorized. Review this package first: `delegation/REVIEW_R5_REQUEST_PROMPT.md`.
