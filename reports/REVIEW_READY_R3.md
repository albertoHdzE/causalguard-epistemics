# REVIEW READY — iteration 3 (bounded repair after Codex review R2)

Development release `v0.3.0-dev`, pre-sprint (2026-11-10/11; the sprint runs 2026-11-13 to 11-15). The
release identity is in the last section of this file. **No confirmatory result exists:** `confirmatory_authorized`
is false, `docs/FREEZE_RECORD.json` is absent, no confirmatory run happened, no LLM was called, and WP10/WP11 were
not started. This file names the release identity, so it is excluded from `artifacts/manifest_r3.json`.

Start here, then read:
- `reports/acceptance_r3.json`;
- `reports/R3_EVIDENCE_MATRIX.md` (R2-01..R2-09 plus reporting corrections → tests → evidence);
- `reports/DEVELOPMENT_REPORT_R3.md`;
- `reports/ERRATA_R3.md`;
- `docs/EXECUTION.md`;
- `reports/development_r3/before_after_audit.json`;
- `DECISIONS.md` D36–D44.

## 1. What changed

| section | result |
|---|---|
| A execution (R2-01..04) | **Ownership:** exclusive kernel-`flock` run ownership; a second opener is refused before it touches storage. **Attempts:** published no-clobber by `link()`. **Supervisor death:** a lifeline watchdog in each worker's process group, and the new owner must drain the workers lock before recovery, so a group SIGKILL of the supervisor kills the worker and its descendants and an immediate resume never overlaps them. **Status:** derived from every latest stored attempt; invocation counts are separate. **Validation:** one strict validator for plans and every attempt, run before any mutation. **Phase:** from provenance. **Retries:** development only. |
| B completeness (R2-05, R2-06) | S2 outputs are reconciled with the regenerated world and design. Absent cells and queries are explicit missing outcomes. Completeness is reported for the structured primary, the required null and the overall study; family weights never change silently. New rows carry `qid`. S1 has a 24-query grid reconciliation, and RSS now comes from the attempt envelope. Phase-aware titles and status; sizing is development-only. |
| C S3 offline (R2-07..09) | Design-known budget rule; training-fitted role rules (persisted); single coherence rule with post-aggregation C audit; semantic novelty audit; future-design note only. |
| D reporting | Errata E1–E14; R3 report; claim ledger R3; smoke runs; before/after audit; manifest r3; release. |

## 2. Unchanged scientific results (verified, `before_after_audit.json` → PASS)

- **S2 primary (development):** index − exact compatible-set majority = **+0.000875, 95% CI [−0.0111, +0.0121]**,
  250 structured worlds, B16, 16 intervention queries. This is identical to R2, and the per-world CSV is
  byte-identical. No clear advantage was detected; this is not equivalence. The null, secondaries, stress, MC, sizing
  and curves are identical.
- **S1:** correctness, completion, latency, archive bits and amortized totals are identical.
- **S3:** arms, targets, contrasts (focus T_cert − T_label = −0.08 [−0.16, 0.00]), transforms, revisions, confusion
  and the historical baselines are identical.
- At the final code, the R3 summaries reproduce byte-for-byte from the raw runs. The R2 S1 and S3 summaries still
  reproduce from tag `v0.2.0-dev`, apart from path strings. All 2,404 preserved R1/R2 raw files are hash-identical
  to manifest r2.

## 3. Corrected values

- S1 RSS: R2 had 49/49 false zeros. R3 has 546/546 items measured, with medians of 24.9–5,003.9 MiB (worker peak,
  interpreter included).
- S3 coherence: C aggregates disagree with their own mean vector in **134/297** valid cases on the qwen held-out panel
  (28/60 and 2/60 on the diagnostics). R2 reported 0.
- S3 shortcut: the design-known budget rule scores **80/100** on held-out targets, and the training-fitted role rule
  scores 79/100. The pooled rule scored 47/100.
- S3 novelty: held-out world 2 repeats its source claim. An exploratory exclusion gives −0.081 over 99 worlds.
- Sizing: the two-sided false-positive rate is **0.046–0.0545**.
- Wording: Bayes non-exceedance; balanced accuracy (qwen A 0.433 balanced vs 0.417 ordinary); oracle-balanced
  queries; D29 timing and gemma scope; certificate assurance; Brier.

## 4. Smoke runs (execution verification only, `DEVELOPMENT_REPORT_R3.md` §5)

`dev-r3-smoke-s2` (6/6) and `dev-r3-smoke-s1` (14/14) ran at `c40c35f`. The S1 run includes one deliberate
supervisor-group SIGKILL with 4 items in flight, followed by an immediate resume, which completed (D40).

Code changed after those runs (D41, D44), so both were repeated: first as `dev-r3-final-smoke-s2/s1`, and then, after the
D44 ledger-reconciliation fix, at the release source as `dev-r3-release-smoke-s2/s1`, with plan source digest `920e3abd…`
equal to the release source. Results at the release source:
- S2: structured, null and overall completeness complete; `qid` path.
- S1: 0 mismatches against the exhaustive reference (24 comparisons per backend); 0 cross-backend disagreements;
  RSS measured.
- The scientific outputs are identical to the first smokes; only timing fields differ.

## 5. S1/S2 identities proposed for the scoped freeze review

| item | value |
|---|---|
| source tree digest (`runner.source_tree_digest`, `src/causalguard/**.py`) | `920e3abd8c7f436a01a5c1c9ee12aa29bf6007fbf2b9707f9057bce51550a50e` |
| `configs/confirmatory.json` (proposal; allocation unchanged: S2 1,000 structured + 1,000 null; S1 grid) | `438cf4f7b909b68596c43951c9e320f0d0d7298e17e0f6d9601f5c10ccead09d` |
| `configs/endpoints/S2-primary-v2.json` (unchanged) | `1b797c8b293f51eadf06a9264652aa60bd6bd29a87ddf0df3e2d3ae5d98c72ac` |
| `artifacts/manifest_r3.json` (development manifest named by the config) | `a55638c73f603e7908c5ed4e08c95259dd959c31762b152d44cf272f40264756` |

Config changes since R2:
- `development_manifest` now points to manifest r3.
- `runs/dev-r3-smoke-s2` is added to the S2 dedup corpora. This is conservative: confirmatory structured worlds
  isomorphic to those 6 observed worlds are excluded.
- Status text.

No N, endpoint, tie rule or generator changed.

## 6. Tests and checks

- Local (macOS, Python 3.12, `CAUSALBOOL_ROOT` = upstream `376a11dd`): **219 passed, 0 skipped**
  (`reports/test-output-r3.txt`). Ruff is clean.
- Mutation and plant checks:
  - disabling the watchdog kill fails the parent-death test;
  - a planted copy of the coherence rule fails the owner guard.
- CI (Ubuntu + macOS, upstream parity on Ubuntu): see the last section.

## 7. Remaining limitations (candid)

- **Legacy S2 rows.** The 670 saved worlds have no `qid`, and 8,359/15,630 saved cells contain byte-identical rows
  for distinct queries. A duplicate with the same fingerprint as the row it replaced is therefore undetectable in
  those records. Cardinality, order, identity fingerprint, recomputed truth and count consistency are all checked.
  New runs are exact.
- **Watchdog scope.** It does not cover descendants that leave the worker's process group. The drain bound is 30 s,
  after which a resume refuses rather than overlapping. Platform support is POSIX only (macOS and Linux); Windows is
  unsupported.
- **Smoke latencies** are not isolated benchmarks. The D40 driver's process-listing check matched nothing even
  before the kill, so it is not evidence; the drain lock and the PID-tracking unit test are.
- **S3** is exploratory. The target task has weak construct validity (80/100 shortcut). Gemma is a 20-world floor
  diagnostic, and D29 is not preregistration.
- **Development estimates** do not show a general truth, an ordering of Kolmogorov complexities or durable learning.
- **Public verification** of GitHub availability, CI, download-back and the fresh clone is reported by the author
  below. The R2 reviewer could not reach GitHub from its sandbox.

## Release identity (filled at publication)

| item | value |
|---|---|
| reviewed **content commit** | `ed719eac96580d19b4ded1b563d1e402b01ec05e` (branches `main` and `iteration-3`) |
| release commit / tag | the docs-only commit that adds this table (it changes only this file), tagged **`v0.3.0-dev`** (GitHub prerelease) |
| superseded, untagged content | `c2975b5` (macOS CI race; D44) |
| CI on the content commit | runs `42933004390` (main) and `42933004391` (iteration-3): **success**. Ubuntu and macOS: lint clean, 214 passed + 5 skipped (upstream tests, no checkout in that job); upstream-parity job 5/5 passed; manifest check INCOMPLETE by design (raw runs live in release assets) |
| release asset | `causalguard-dev-runs-v0.3.0-dev.tar.gz`, 353,036 B, sha256 `b6e36f77e6909aefb9b03b87a99978eba6aa70ac93f023b49b9bbea4216acb47` (dev-r3 runs + current `runs/registry.jsonl`) |
| manifest | `artifacts/manifest_r3.json` sha256 `a55638c73f603e7908c5ed4e08c95259dd959c31762b152d44cf272f40264756`; 2,623 entries, of which 2,620 required |
| previous releases | `v0.1.0-dev`, `v0.2.0-dev` and their assets are unchanged |
| download-back and fresh-clone check | recorded after tagging in `reports/RELEASE_CHECK_R3.md` (a post-tag, docs-only commit on `main`) |
