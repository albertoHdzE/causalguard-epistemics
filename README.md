# CausalGuard — compressed symbolic models for auditable epistemic improvement

**Status: development release `v0.5.0-dev` (iteration 5, R5 batch, 2026-11-11; four bounded tracks G/C/A/M). Not a final study release; no confirmatory result exists; confirmatory runs are NOT authorized (no freeze record). Start at `reports/REVIEW_READY_R5.md`. Releases `v0.1.0-dev`..`v0.4.0-dev` and their records are preserved unchanged.**

**R5 in one paragraph (development evidence):** description-length-weighted averaging beats uniform averaging on held-out worlds, but OUR hierarchical prior shows no detected advantage over the best generic codec (gate − CGH +0.002 [−0.004, 0.008] Brier) and its hierarchy adds ≈ 0 outside generator-matched families; an independent generic counter matches our exact counts and is faster at k = 3 (ours still beats generic SAT); two local LLMs investigate worse than the exact EIG controller (−0.11, −0.34 resolved@4); verified claims can be false under wrong-but-consistent assumptions (10/103), and a public challenge policy halves that at modest coverage cost. Run `python -m causalguard r5-demo` for an illustration.
## Sprint benchmark (R7, pre-sprint): *What does the evidence settle?*

An exact benchmark of whether a model knows what its evidence settles. For every claim the answer key is its exact
status (settled true / settled false / not settled) inside the declared class, plus, for open claims, the exact
probability p*. Two independent engines compute them and must agree. Task S scores verdicts and probabilities.
Task P adds one randomised follow-up (neutral, empty disagreement, demand to commit, checked challenge with a
witness) and scores capitulation, forced overclaiming, repair and discernment. Entry points: `docs/SPRINT_TASKS.md`,
`docs/SPRINT_DESIGN_LOCK.json`, `reports/SPRINT_LOCAL_RESULTS.md`, `reports/REVIEW_READY_R7.md`.

```bash
python -m causalguard sprint-build engines --split main          # exact engines agree on every main-panel claim
python -m causalguard run --config configs/sprint/main_<model>.json
python -m causalguard sprint-analyze --run-dir runs/<run1> --run-dir runs/<run2> ... --out reports/sprint_local
```

All of R7 was done on 2026-11-12, before the sprint, and is disclosed as preexisting work (`PREEXISTING_WORK.md`).

## What this is

A reproducible research system that asks, operationally, whether *compact executable symbolic models* help reasoning about mechanisms from **incomplete evidence**:

1. **Representation / computation (S1).** Boolean network repertoires are represented as unions of *schema (index) families* — the CausalBool anchor + offset-family method, where don't-cares may sit on **connected** inputs (Rule 110) — and queried (membership, ∃, ∀, bounded reachability with interventions) without expanding the repertoire. Every codec is an executable, independently decodable bitstring; lengths are real archive bits.
2. **Induction (S2, primary).** Given incomplete observations, all mechanisms in a declared complete hypothesis class that fit them form the version space V(D). We test whether the mechanism with the **shortest index code** predicts hidden *intervention* outcomes better than the **compatible-set majority** (the Bayes predictor under a uniform prior on V(D), computed exactly), with a mandatory uniform-H null population — and we report where it does not. (The iteration-1 comparator, a uniformly chosen compatible mechanism, is kept as a historical secondary.)
3. **AI reasoning (S3).** Local LLMs answer the same evidence-relative questions (entailed / refuted / underdetermined) under controlled arms: initial answer, two self-critique turns, majority of three, certificate-plus-label (privileged), label only, two uniformly sampled compatible mechanisms, and the exact solver; plus matched within-world context-reuse probes on a fresh question.

What this project does **not** claim: that the shortest code is true, that measured lengths equal Kolmogorov complexity, that every Boolean function compresses, or that a selected model's prediction is a logical certificate. Exact deduction (conditional on a model or on a complete class) is kept separate from induction (selected-model prediction); evidence-relative verdicts are kept separate from the hidden world's answer.

## Key semantics (docs/SEMANTICS.md)
- LSB-first states; synchronous update; horizon = number of updates; `initial_edit` vs `persistent_clamp` interventions.
- Verdicts over V(D): `entailed`, `refuted`, `underdetermined` (with two replayed disagreeing witnesses); empty V(D) ⇒ `inconsistent_evidence_or_class`; budgets ⇒ `unknown_resource`. These statuses cannot be coerced to booleans.
- The hidden-world answer is used only for scoring, after all predictions are fixed (tested).

## Install

```sh
git clone https://github.com/albertoHdzE/causalguard-epistemics && cd causalguard-epistemics
python3 -m venv .venv && .venv/bin/pip install -r requirements-lock.txt && .venv/bin/pip install --no-deps -e .
.venv/bin/python -m pytest -o addopts="" -q -rs        # offline; upstream parity tests skip without a checkout
```
Core dependency: numpy. Solver extras: python-sat, dd. No Wolfram, no GPU, no paid API.

## Reproduce (iterations 2-3)

Long runs are resumable (`--resume`, identical plan required) and are normally launched from an immutable snapshot:
`scripts/run_from_snapshot.sh <commit> <log-name> python -m causalguard run --config ...`. One live process owns a
run at a time (a second opener is refused); a killed supervisor's workers are reaped by their watchdog before a
resume may proceed (`docs/EXECUTION.md`).

| Step | Command | Measured (M3 Ultra) |
|---|---|---|
| Tests (offline) | `python -m pytest -o addopts="" -q -rs` | ~3 min |
| Fast smoke (3 S2 worlds) | `python -m causalguard run --config configs/s2_ci_smoke.json --runs-root /tmp/runs --quiet` | ~2 s |
| S2 development v2 (670 worlds) | `python -m causalguard run --config configs/s2_dev_v2.json --quiet` | ~25 s wall on 24 workers |
| S2 MC diagnostic (200 worlds) | `python -m causalguard run --config configs/s2_dev_v2_mcdiag.json --quiet` | ~16 s |
| S2 analysis v2 | `python -m causalguard analyze-s2-v2 --run-dir runs/S2-dev-v2 --mc-run-dir runs/S2-dev-v2-mcdiag --out reports/development_r3` (R3 analysis; R2 output kept in `reports/development_r2`) | ~3 min |
| S1 repair panel | `python -m causalguard run --config configs/s1_dev_v2_panel.json --quiet`; `python -m causalguard analyze-s1-v2 --run-dir runs/S1-dev-v2-panel --out reports/development_r3` | see report |
| S3 v2 panels (local model servers) | `python -m causalguard.experiments.s3 --config configs/s3v2_<panel>_<model>.json --run-id <id> --quiet` | see report |
| S3 analysis (v3 audits) | `python -m causalguard analyze-s3-v2 --run-dir runs/<id> ... --out reports/development_r3` (role baselines: `fit-s3-role-baselines`) | < 1 min |
| R2 → R3 field-level audit | `python scripts/audit_r3_before_after.py --quiet` | < 1 s |
| Iteration-1 byte-level reproduction | `scripts/reproduce_v1.sh` (historical code from tag `v0.1.0-dev`) | ~3 min |
| Verify artifacts | `python scripts/verify_artifacts.py artifacts/manifest_r3.json` (extract the release assets into the checkout for COMPLETE) | < 1 min |

Raw run records (`runs/`) are not in git; `artifacts/manifest_r3.json` (historical: `manifest_r2.json`, `manifest.json`) lists every required file with its SHA-256 and the release assets that contain them.

## Results so far (development only)
`reports/DEVELOPMENT_REPORT_R3.md` (iteration 3 corrections), `reports/DEVELOPMENT_REPORT_R2.md` (iteration 2) and `reports/DEVELOPMENT_REPORT.md` (iteration 1, historical); sizing proposal `reports/DESIGN_SIZING_R2.md` (two-sided correction in ERRATA_R3); claims `reports/CLAIM_LEDGER_R3.csv`.

## Repository map
`src/causalguard/` — `schema` (types), `semantics`, `reference` (independent oracle), `index_repr` (index families), `codec`, `query` (index backends), `bdd_ref` (independent BDD), `proofcheck` (RUP), `versionspace` (incl. exact posterior counts), `generators` (incl. exogenous S2 design v2), `freeze` (confirmatory lifecycle, not authorized), `dedup`, `s3_tasks`, `llm/`, `runner`, `stats`, `experiments/`, `analysis/`, `upstream_adapter`.
`docs/` — SEMANTICS, CODEC, S3_HARNESS, PROTOCOL, EXECUTION, S3_FUTURE_DESIGN_R3 (proposal only). `delegation/` — dated design history (pre-sprint). `reports/` — development evidence and the review package.

## Provenance and license
Original code: MIT (LICENSE). The license covers only the original CausalGuard code and documentation in this repository, not the upstream CausalBool repository. The upstream CausalBool method (pinned `376a11dd`) is cited and used read-only for parity tests; no upstream code is redistributed (UPSTREAM.md). Dating: PREEXISTING_WORK.md.
