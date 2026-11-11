# REVIEW READY: iteration 4 (P0 repairs + S4 implementation, offline programs and bounded local pilot)

Development release `v0.4.0-dev`, pre-sprint (2026-11-11; the sprint runs 2026-11-13 to 11-15).

**No confirmatory result exists.** There is no freeze record, no confirmatory run and no S4 main study. There
was no paid inference, no weight change, and no WP10/WP11. The only model calls were 888 local calls (37
pre-pilot + 851 pilot) against a ceiling of 2,560. This file names the release identity, so it is excluded from
`artifacts/manifest_r4.json`.

Read in this order:

1. this file;
2. `reports/R4_EVIDENCE_MATRIX.md` (and `reports/acceptance_r4.json`);
3. `reports/development_r4/p0_repair_evidence.json` (**P0 repair validation; separate from S4 science**);
4. `docs/S4_METHOD_COVERAGE.md`, then `docs/S4_PROTOCOL_DRAFT.md`;
5. `reports/S4_DEVELOPMENT_REPORT.md`, `reports/S4_FAMILY_COST_TABLE.md`, `reports/S4_DESIGN_SIZING.md`;
6. `docs/S4_FUNDING_BRIEF.md`;
7. `DECISIONS.md` D45–D53.

## 1. P0: bounded repairs (independently reviewable; commit `c8a13e1`)

- **R3-01.** Method keys now come from the study contract, nulls are state-dependent, and no denominator is
  filtered. Reanalysis of the preserved S2 records gives a byte-identical per-world CSV and a summary with 0
  field differences. The S2 primary is unchanged: +0.000875 [−0.0111, +0.0121], N = 250.
- **R3-02.** The worker refuses work synchronously when the supervisor is already dead. The reviewer's
  reproduction now writes 0/5 markers (it wrote 5/5 before).
- **Tests.** There are 24 new P0 tests. Full suite at P0: 243 passed.
- **Later test change.** After the content push, an R3 test assertion was widened because Ubuntu raises
  `ConnectionResetError` where macOS raises `EOFError` once the worker is refused earlier. Commit `957c8d7`
  records this; behavior is unchanged.

## 2. S4 science (development)

Headline results:

- **Correctness agreement.** B, C and D agree on 5,120/5,120 map claims and 100/100 stress claims, and the EIG
  choices are identical for 80/80 targets.
- **Pilot, two models × 40 worlds.** All gates passed and no revision was used.
  - D − A is +0.350 [0.269, 0.431] for qwen2.5:7b and +0.363 [0.278, 0.450] for mistral-small-3.2-24b.
  - **D − B is a tie**: 0.000 for qwen, and +0.022 [0, 0.066] recorded for mistral (0.000 under the D52
    merged-commit sensitivity).
  - The release gate blocked all 228 wrong unaided proposals and verified 0 wrong ones.
  - The unaided models answer "underdetermined" on 99% of claims.
  - The no-LLM controller beats every AI arm at forecasting (0.782 vs 0.54–0.59).
- **Cost and scale.** These figures are with a competent SAT baseline, after D49 withdrew v1.
  - At n = 48 (h ≤ 2), D takes 12.8 s and B takes 116.5 s.
  - At n = 64, D answers 12/12 claims and B answers 4/12.
  - Exact counts are available from D only above n = 10.
- **Offline secondary: codec-induced averaging.**
  - With 12 observations, cgh_prior − uniform is +0.089 [0.064, 0.115] and cgh_prior − cgh_flat is +0.049
    [0.036, 0.063].
  - The hierarchy part comes entirely from the two families built with ordered or module structure. It is 0 in
    the order-disrupted control and in the uniform-H null.
- **S4-B.** EIG minus random gives +0.075 [0.025, 0.125] in resolved targets. This gain is not specific to our
  encoding.
- **Known-mechanism panel.** 72/72 queries are exact at n ≤ 14; 48 queries are corroboration only.
- **Misspecification.** 26/40 worlds are exposed as inconsistent. 21 verified conclusions were executed, with
  0 postcondition violations; the sample is small.

## 3. Defects and course corrections found during the iteration (all disclosed, none hidden)

| ID | What | Consequence |
|---|---|---|
| D48 | The float64 range guard refused 16/160 map-v1 worlds; D's h = 2 witness search was exponential | exact limb arithmetic; map v2 rerun; v1 preserved; support-local witnesses |
| D49 | The generic SAT baseline used a quadratic AMO; stress v1 overstated D's speed | sequential-counter AMO; stress v2; the v1 contrast is withdrawn |
| D50 | Pre-pilot smoke: qwen wrote bare tool names | tool-instruction examples added before the pilot; not pilot data |
| D52 | Pilot harness kept only the last of several commit calls in one turn (1 mistral B episode) | recorded result reported; merged re-parse as a sensitivity; harness fixed; no rerun |
| Owner guard | the S4-B tie rule and the controller majority rule were local copies of `versionspace.posterior_from_counts` | both now use the owner; the controller's forecast accuracy changed from 0.772 to 0.782 (reports updated); the S4-B stored curves were computed with an equivalent rule |

## 4. Identities

| Item | Value |
|---|---|
| reviewed **content commit** | `957c8d73be5a3a5a6c301929f7f4036d70d70ac3` (branches `main` and `iteration-4`; supersedes the untagged `bae41b7`, whose Ubuntu CI failed on the platform-dependent test assertion only) |
| P0 repair commit | `c8a13e1` |
| content source digest (`runner.source_tree_digest`) | `a8252d9555887fe52ddc3d9efbe9cf0725c9a6b01f892a4c408974ea6449ae35` |
| run snapshots (plan `source_tree_sha256` prefix) | map v1, stress v1, active, known: `df04a6e` (`c939e3c3…`); stress v2: `125f9dc` (`03fed274…`); map v2, misspec: `82209f0` (`5fdc013e…`); both pilots: `15752d4` (`4244a328…`) |
| code changes after the runs | analysis-side only (sensitivity scoring, owner tie rule, controller), the harness commit-merge fix (future runs), the misspec CLI, docs. No stored record was edited. |
| pilot model artifacts | qwen2.5:7b Q4_K_M digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`, chat template sha256 `eb4402837c7829a690fa845de4d7f3fd842c2adee476d5341da8a46ea9255175`, Ollama 0.40.16, num_ctx 16384; mistral-small-3.2-24b-instruct-2506 MLX 4-bit via LM Studio, context 16384 (no digest exposed) |
| configs (sha256) | `configs/s4/pilot_qwen25_7b.json` `fa94e32a…`, `pilot_mistral_small_24b.json` `9fea6236…`, `map_dev.json` `4793959d…` (run_id v2), `stress_dev.json` `ed5ddf82…` (run_id v2), `active_dev.json` `7c12d8c1…`, `known_dev.json` `ad9c5303…`, `misspec_dev.json` `a0ad854f…`. Every run's exact config is inside its `plan.json` |
| surface baselines | `reports/development_r4/s4_surface_baselines.json`, file sha256 `9ea3b71e…`; internal body digest `1fb5dc40…`; committed in `125f9dc` before the first pilot call |
| manifest | `artifacts/manifest_r4.json` sha256 `46cd8612a033359aafd5faf771716aeabe9d1e0e0ae419ec867d3845d1acafa7`; 842 entries, 840 required (652 raw iteration-4 run files + the S4 call ledger + registry, 147 reports, 29 configs, 12 docs); local verification **COMPLETE** |
| release asset | `causalguard-dev-runs-v0.4.0-dev.tar.gz`, 1,347,011 B, sha256 `0e96b2912e268f94bb69388b4fd6de37784a80c1cf443acc5247e04f6fcb57b9` |
| previous manifests and assets | unchanged. `manifest_r3.json` now reports `runs/registry.jsonl` as changed because the registry is append-only: its r3 copy (12,379 B) is a verified byte prefix of the current file. Verify r3 raw runs from the v0.1–v0.3 assets as before |
| tests | local: **448 passed** (`reports/test-output-r4.txt`; macOS, Python 3.12, upstream `CAUSALBOOL_ROOT`). CI on `957c8d7`: runs `43057603544` (main) and `43057599956` (iteration-4) **success**; Ubuntu and macOS 443 passed + 5 skipped (no upstream checkout); upstream-parity 5/5; ruff clean; manifest check INCOMPLETE by design (raw runs live in release assets) |
| release commit / tag | the docs-only commit adding this file and `delegation/REVIEW_R4_REQUEST_PROMPT.md`, tagged **`v0.4.0-dev`** (GitHub prerelease) |
| download-back and fresh clone | `reports/RELEASE_CHECK_R4.md` (post-tag, docs-only) |

## 5. Pre-sprint vs sprint (official rules)

All iteration-4 work, including the code, runs, pilot, reports and this release, was done on **2026-11-11,
before the sprint**. It is preexisting work to be disclosed as such. Nothing was produced during the sprint
window.

## 6. Reproduction

```sh
CAUSALBOOL_ROOT=~/.cache/causalguard/CausalBool .venv/bin/python -m pytest -o addopts='' -q
.venv/bin/python scripts/verify_artifacts.py artifacts/manifest_r4.json        # after extracting the v0.4.0-dev asset
.venv/bin/python -m causalguard analyze-s2-v2 --run-dir runs/S2-dev-v2 --mc-run-dir runs/S2-dev-v2-mcdiag --out /tmp/r4/s2
.venv/bin/python -m causalguard analyze-s4 --map runs/s4-map-dev-v2 --active runs/s4-active-dev-v1 \
   --known runs/s4-known-dev-v1 --misspec runs/s4-misspec-dev-v1 --stress runs/s4-stress-dev-v1 \
   --stress runs/s4-stress-dev-v2 --pilot runs/s4-pilot-qwen25_7b-v1 --pilot runs/s4-pilot-mistral_small_24b-v1 --out /tmp/r4/s4
.venv/bin/python -m causalguard s4-demo
.venv/bin/python reports/review_r3/repro_worker_start.py            # expect 5 x {'marker': False, 'exit': -9}
```

## 7. Decisions requested from the reviewer

1. Accept or reject P0 (R3-01, R3-02).
2. **Re-decide the S4 main-study primary before any main run.** D − B accuracy is an exact tie at feasible
   sizes; the options are in `reports/S4_DESIGN_SIZING.md` §1.
3. Decide whether the forecast endpoint needs held-out, externally chosen structure, since the
   hierarchy-positive families were designed by us.
4. Decide whether the generic comparator must add a knowledge compiler (d-DNNF/#SAT) for counts.
5. Approve or deny a new call budget (about 16–18 k local calls for 2 × 800 worlds).

## 8. Remaining limitations

- One-step evidence, k = 3, and n = 8 in the pilot.
- No BDD or grammar reasoning backend; their description lengths are reported only.
- The isomorphism test is not applied as a filter to the pilot panel.
- LM Studio exposes no model digest.
- Latencies are contended.
- The S2 legacy-row limitation and the S3 limitations from R3 still apply.
