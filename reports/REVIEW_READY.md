# REVIEW READY — CausalGuard implementation iteration 1

State: **review-ready development package; not accepted; no confirmatory data exists.** Prepared 2026-11-09.

## 1. Location, remote, commit
- Local root: `/Users/alberto/Documents/projects/AI-security/AI-x-epistemics` (standalone git repository; the parent directory is not a repository).
- Public repository: **https://github.com/albertoHdzE/causalguard-epistemics** (public, created by this iteration).
- Branch `main`; review commit and tag: **see the final lines of this section** (filled at release).
- Dirty state at the review commit: clean (`git status --porcelain` empty). Ignored by design: `runs/` (raw records; release asset), `.venv/`, `dist/`, `doc/Gemini-Talk.txt`.

{{RELEASE_COMMIT}}

## 2. Work-package acceptance (machine-readable: `reports/acceptance.json`)

| WP | Status | Key evidence |
|---|---|---|
| WP0 inventory / isolation / provenance | pass, except dating = **blocked** (sprint start date unknown) | ENVIRONMENT.md, UPSTREAM.md, PREEXISTING_WORK.md, lock, CI clean install |
| WP1 typed semantics + fixtures | pass | schema.py, semantics.py, 14 hand-derived fixtures, statuses refuse `bool()` |
| WP2 independent reference + certificates | pass | reference.py (import-guarded, verified by planting), bdd_ref.py, proofcheck.py (RUP) |
| WP3 index representation, codec, queries, upstream parity | pass | index_repr.py, codec.py (7 codecs, framing + CRC), query.py, upstream_adapter.py; parity vs pinned upstream |
| WP4 version spaces / selection | pass | versionspace.py: complete class, SAT quantification, enumeration + brute-force cross-checks, isolation test |
| WP5 generators / audits | pass | generators.py, dedup.py, s3_tasks.py |
| WP6 runner / analysis / statistics | pass | runner.py, stats.py (coverage-validated bootstrap), analysis/*.py, byte-identical re-analysis |
| WP7 LLM harness | pass | llm/*, experiments/s3.py, 35 harness tests, real pilots on two local families |
| WP8 development experiments + freeze proposal | pass; S3 pilot complete but **not ready to freeze** (floor) | DEVELOPMENT_REPORT.md, DESIGN_SIZING.md, configs/confirmatory.json |
| WP9 public release | pass | RELEASE_CHECK.md, CI green on ubuntu + macOS + upstream parity |
| WP10 / WP11 | not_run (subsequent iterations by design) | — |

## 3. Commands, environment, tests
- Environment: ENVIRONMENT.md. Python 3.12.13, numpy 2.5.4, python-sat 1.9.dev21, dd 0.6.0; M3 Ultra (28 cores, 96 GiB). Local model servers: Ollama 0.40.15 (qwen2.5:7b Q4_K_M, digest 845dbda0…) and LM Studio (gemma-3-12b-it MLX 4-bit).
- Tests: `reports/test-output.txt` (full `pytest -v -rs` output at the review commit): **138 passed** with the pinned upstream checkout (fetched by `scripts/fetch_upstream.sh`); **133 passed, 5 skipped** without it; ruff clean. CI run IDs are in RELEASE_CHECK.md. The upstream-parity tests (5) are skipped without `CAUSALBOOL_ROOT` and pass in the dedicated CI job.
- Executed runs (RUNS.jsonl):
  - `S2-dev-v1` — 420 worlds;
  - `S2-dev-null-v1` — 250 worlds;
  - `S1-dev-v1` — 2,345 items, 1 recorded failure;
  - `S1-dev-v1-rerun` — 670 items;
  - `s3-pilot-*-dev-v1` — invalidated, kept;
  - `s3-pilot-*-dev-v2` — the pilot;
  - `S2-smoke-tmp` — smoke run, directory removed.
- Raw records: `runs/<id>/` → release asset; checksums in `artifacts/manifest.json`.

## 4. Architecture and boundaries

```
public evidence ──► versionspace (complete class H, per-node V_j) ──► selectors (index/circuit/bdd/dnf codes)
                         │                                         ├─► uniform / majority-of-V(D)
                         └─► SAT quantification over H ──► verdict + replayed witnesses (reference.py)
hidden world ──────────────────────────────────────────────► scoring only (after predictions fixed)

Network (direct rules) ──► index_repr (schema families, polarity, symbolic J) ──► codec (bit-exact archives)
        │                         ├─► query.index_enum / index_cube (pure index algebra)
        │                         └─► query.index_sat  (HYBRID: families → CNF → SAT; RUP proof check)
        ├─► reference.py  (independent oracle, exhaustive, replay)        [must not import production engines]
        ├─► bdd_ref.py    (independent BDD from direct rules)             [must not import production engines]
        └─► query.literal (literal repertoire, n ≤ 16)
LLM: s3_tasks (public payload / private oracle) ──► llm.harness arms ──► experiments.s3 ──► analysis.s3_analysis
```

- Upstream: CausalBool `376a11dd`, read-only. The pinned files and their SHA-256 are in UPSTREAM.md. No code is vendored, because upstream has no license.
- Each result records its `representation_backend` and `query_backend`. Index families are never silently replaced: the SAT path is labelled `sat_hybrid`. Materializations are logged, and none happened in the large-n tests.

## 5. Codec and accounting
Specification: docs/CODEC.md. Integer field widths, Elias γ/δ, colex subset ranks, polarity bit, archive framing (magic, codec id, version, n, payload length, zero padding, CRC-32). Truncation, trailing bytes, corruption and bad magic are rejected (tested).

Worked round trip (Rule 110 network, 3 nodes):

| codec | index | dnf | gate | circuit | bdd | lut | full |
|---|---|---|---|---|---|---|---|
| payload bits | 33 | 47 | 30 | 36 | 49 | 22 | 24 |
| archive bits | 128 | 144 | 128 | 136 | 144 | 120 | 120 |

Every codec decodes back to the identical canonical network. Amortized totals (decoder gzip size + Σ payloads) are in `s1_summary.json["amortized_totals"]`. Lengths are upper bounds under declared decoders; ordering two bounds does not order Kolmogorov complexities.

## 6. Semantic fixtures and adversarial cases
`python -m causalguard fixtures` prints the hand-derived table (data/fixtures/semantic_fixtures.json). Each case is explained independently of the code, and all six backends must reproduce it. Specific checks:
- **Uncertainty vs resource:** `unknown_resource` (budget) is never `false`, and `invalid_domain` is never a vacuous truth (fixture F07; `test_resource_unknown_is_not_false`).
- **Empty V(D):** reported as `inconsistent_evidence_or_class` (E02, E04, E05).
- **Overlaps:** union counts are exact via Shannon splitting, checked exhaustively on 200 random family sets. OR(k) gives 2ᵏ−1, not k·2^(k−1).
- **Persistent clamp vs edit:** F05/F06. A clamped coordinate's observation carries no information (E05).
- **Rule 110:** 3 on-set families with all three inputs connected; the upstream-cited cover {01*, 10*, *10} is valid in LSB-first strings; 2 off-set families.
- **Deliberate corruptions detected:** order flips, witness traces, quantifier swaps, serialized payload bits, sequential-update semantics.

## 7. Datasets, independence, duplicates, leakage
- S2: 670 independent worlds:
  - 250 realizable (5 families × 50);
  - 60 misspecified;
  - 60 shift;
  - 50 noise stress;
  - 250 null (uniform from H, post-hoc control).
  Regimes, budgets and the 24 queries are nested within worlds and analysed as clusters.
- S1: 335 worlds. S3: 80 worlds per model, 4 linked items each, with a natural verdict distribution.
- Exact isomorphism audit (all n! relabellings, invariant prefilter): 0 duplicates among 420 S2 worlds; 0 among the 80 S3 worlds (8 exact checks). The confirmatory runner excludes any world isomorphic to a development world.
- Leakage controls:
  - The selector API receives only the version space. A test swaps the hidden world under fixed evidence and finds identical predictions.
  - The S3 public payload carries no verdict. D feedback never contains a label word (asserted). D-label is a labelled privileged control.
  - The confirmatory salt does not exist yet.

## 8. Development results (DEVELOPMENT_REPORT.md; all development, some post-hoc)
**S1.**
- 0 mismatches against the exhaustive reference (≈28,700 comparisons), 0 cross-backend disagreements, 0 witness-replay failures.
- 2,569 of 2,573 UNSAT answers carry checked RUP proofs.
- Index→SAT hybrid completes 100% of queries up to n=256; pure index-cube algebra completes 47.5% at n=256.
- The index code is shortest only on canalizing networks. It loses heavily on parity: 153k vs 10.5k bits at n=256.

**S2 primary (pre-specified):** min-index-code − uniform compatible = **+0.064 [0.053, 0.075]**, 250 worlds.

**S2 decisive negatives (post-hoc controls, D21):**
- Under a null generator (rules uniform from H), index − uniform is still +0.018 [0.009, 0.027].
- Index vs majority-of-V(D) is indistinguishable (+0.007 [−0.007, 0.020]).
- Circuit beats majority-of-V(D) (+0.036) only in XOR-generated families and loses under the null (−0.033).
- Circuit beats index (−0.029 for index − circuit).
- At budget ≤ 4, index equals a trivial baseline.
- Misspecification makes V(D) empty (92% at budget 16) after a few wrong certified answers. The two-part MDL code is robust to noise where exact matching collapses.

**S3:** 80 worlds × 4 items for each of qwen2.5:7b and gemma-3-12b-it (2,400 physical calls each, 0 failures).
- **Floor pilot.** Initial accuracy is 0.478 (qwen) and 0.588 (gemma), against 0.569 for always answering "underdetermined" and 0.656 for a 3-feature surface rule. Refuted recall is 0.00 for both models.
- **Registered S3 contrast D − B (balanced accuracy):** +0.514 [0.452, 0.567] for qwen and +0.418 [0.352, 0.482] for gemma. The gain is label-revealing witness choice on entailed/refuted items, not reasoning improvement.
- **Self-critique:** no benefit, with many correct→wrong revisions (56 for qwen, 37 for gemma).
- **Transfer:** null for both models; the intervals include 0.
- **Probabilities:** qwen's vectors contradict its own verdicts in 30–80% of answers, so its Brier scores are not calibration. gemma's vectors are coherent.
- S3 is **not ready to freeze**.

**Failures and exclusions:**
- 1 S1 item failed (dd assertion after an interrupt, D20), then rerun.
- Pilot v1 invalidated (B truncated, D19).
- No performance-based exclusions.
- Compute: S2 ≈ 42 CPU-min; S1 ≈ 23 min wall on 16 workers plus an 8 min rerun; S3 pilots ≈ 1.3 h (qwen) + 2.3 h (gemma) of local inference on the shared machine; no paid inference.

## 9. Sizing and proposed confirmatory run (DESIGN_SIZING.md, configs/confirmatory.json, docs/PROTOCOL.md)
**S2:**
- Development per-world SD is 0.095, so the 0.03 half-width target needs only about 50 worlds.
- Proposed: **N = 1,000 realizable** (200 per family) so that the decisive comparisons resolve about ±0.007. Plus 250 misspecified, 250 shift, 250 noise and 250 null (null pending review).
- Cost ≈ 120 CPU-min (≈ 5 min wall).

**S1:** as protocol (1,200 small + 750 large worlds). Estimated ≈ 2.3 h wall on 16 workers.

**S3:** **not ready to freeze** (floor pilot and leaking D feedback). After refinement: qwen 500 worlds and gemma 300 worlds, sized so the transfer contrast has a half-width ≤ 0.05; ≈ 8.2 h + 8.7 h of local inference. The runner refuses S3 while it is marked NOT READY.

**Frozen-run commands** (after review writes `docs/FREEZE_RECORD.json` with the config SHA-256 and an authorization phrase at the freeze commit):
```
.venv/bin/python scripts/run_confirmatory.py --study S2 --freeze-commit <sha> --authorization "<phrase>"
.venv/bin/python scripts/run_confirmatory.py --study S1 --freeze-commit <sha> --authorization "<phrase>"
.venv/bin/python scripts/run_confirmatory.py --study S3 --model qwen25_7b --freeze-commit <sha> --authorization "<phrase>"
.venv/bin/python scripts/run_confirmatory.py --study S3 --model gemma3_12b --freeze-commit <sha> --authorization "<phrase>"
```
Configuration hash of the proposal: `sha256(configs/confirmatory.json) = b1f9978dba484484e73fe88c418a8a3065a341ae660a0588bb00e0e928e774fb`. This is the proposal at the review commit; the freeze will record its own hash.

The runner refuses on: a dirty tree, HEAD ≠ freeze commit, a missing or mismatched freeze record, a wrong phrase, or an existing run id (tested).

## 10. Public clone, CI, reproduction, license and provenance
See RELEASE_CHECK.md: clean clone, 132 passed / 5 skipped; 12/12 regenerated worlds identical; byte-identical re-analysis; CI green. License: MIT for original code. Upstream is cited and not redistributed. Dating: PREEXISTING_WORK.md (pre-sprint preparation commit 3900eb2; everything else is implementation iteration 1, 2026-11-09).

## 11. Deviations, risks, unresolved questions
1. **The pre-specified S2 primary does not isolate simplicity** (D21). The reviewer should decide whether to keep it as primary, replace the comparator with majority-of-V(D), and/or require the null population. This is the most important scientific question for the freeze.
2. The index code is not the best description language here (circuit wins). Any claim about "index-based simplicity" must be scoped to that language. Language/generator alignment (XOR) is a plausible confound for the circuit result.
3. Evidence is restricted to horizon-1 observations (V(D) factorizes). Multi-step observational evidence would need a non-factorized version space.
4. D16 / D19 / D20 process defects were disclosed and repaired; each affected run is kept.
5. The S3 D arm reveals the answer through witness choice on entailed/refuted items (by construction, acknowledged in the protocol). It measures witness-assisted correction, not learning.
6. The S3 task family is small (n=4, k=2) and the models are quantized local models. No cross-model generality is claimed.
7. Kolmogorov statements are upper bounds only. BDM, entropy and upstream Variant E are not used.
8. Sprint start date unknown (dating label).

## 12. Proposed next prompt (for the next Claude iteration; does not assume approval)
> Read `reports/REVIEW_READY.md` and the reviewer's findings. Apply the reviewer's repair packet. Then, only if the reviewer wrote `docs/FREEZE_RECORD.json` at a freeze commit, run the confirmatory S2, S1 and S3 studies with `scripts/run_confirmatory.py` exactly as frozen, analyse them with the registered analysis, and write a confirmatory report that keeps development and confirmatory figures separate. Do not change hypotheses after seeing confirmatory data. If the review asks to replace the S2 comparator (majority-of-V(D)) or to add the null population, implement that before the freeze, regenerate the freeze proposal and stop for re-approval. WP10 starts only after the confirmatory core is accepted.
