# CausalGuard — compressed symbolic models for auditable epistemic improvement

**Status: development release `v0.2.0-dev` (iteration 2, 2026-11-10, pre-sprint; the AI × Epistemics sprint runs 2026-11-13 to 11-15). Not a final study release. No confirmatory result exists; confirmatory runs are prepared but NOT authorized (no freeze record).** The review package is `reports/REVIEW_READY_R2.md`; the iteration-1 release `v0.1.0-dev` and its records are preserved unchanged.

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

## Reproduce (iteration 2)

Long runs are resumable (`--resume`, identical plan required) and are normally launched from an immutable snapshot:
`scripts/run_from_snapshot.sh <commit> <log-name> python -m causalguard run --config ...`.

| Step | Command | Measured (M3 Ultra) |
|---|---|---|
| Tests (offline) | `python -m pytest -o addopts="" -q -rs` | ~3 min |
| Fast smoke (3 S2 worlds) | `python -m causalguard run --config configs/s2_ci_smoke.json --runs-root /tmp/runs --quiet` | ~2 s |
| S2 development v2 (670 worlds) | `python -m causalguard run --config configs/s2_dev_v2.json --quiet` | ~25 s wall on 24 workers |
| S2 MC diagnostic (200 worlds) | `python -m causalguard run --config configs/s2_dev_v2_mcdiag.json --quiet` | ~16 s |
| S2 analysis v2 | `python -m causalguard analyze-s2-v2 --run-dir runs/S2-dev-v2 --mc-run-dir runs/S2-dev-v2-mcdiag --out reports/development_r2` | ~3 min |
| S1 repair panel | `python -m causalguard run --config configs/s1_dev_v2_panel.json --quiet`; `python -m causalguard analyze-s1-v2 --run-dir runs/S1-dev-v2-panel --out reports/development_r2` | see report |
| S3 v2 panels (local model servers) | `python -m causalguard.experiments.s3 --config configs/s3v2_<panel>_<model>.json --run-id <id> --quiet` | see report |
| S3 analysis v2 | `python -m causalguard analyze-s3-v2 --run-dir runs/<id> ... --out reports/development_r2` | < 1 min |
| Iteration-1 byte-level reproduction | `scripts/reproduce_v1.sh` (historical code from tag `v0.1.0-dev`) | ~3 min |
| Verify artifacts | `python scripts/verify_artifacts.py artifacts/manifest_r2.json` (extract both release assets into the checkout for COMPLETE) | < 1 min |

Raw run records (`runs/`) are not in git; `artifacts/manifest_r2.json` lists every required file with its SHA-256 and the release assets that contain them.

## Results so far (development only)
`reports/DEVELOPMENT_REPORT_R2.md` (iteration 2) and `reports/DEVELOPMENT_REPORT.md` (iteration 1, historical); sizing proposal `reports/DESIGN_SIZING_R2.md`; claims `reports/CLAIM_LEDGER_R2.csv`.

## Repository map
`src/causalguard/` — `schema` (types), `semantics`, `reference` (independent oracle), `index_repr` (index families), `codec`, `query` (index backends), `bdd_ref` (independent BDD), `proofcheck` (RUP), `versionspace` (incl. exact posterior counts), `generators` (incl. exogenous S2 design v2), `freeze` (confirmatory lifecycle, not authorized), `dedup`, `s3_tasks`, `llm/`, `runner`, `stats`, `experiments/`, `analysis/`, `upstream_adapter`.
`docs/` — SEMANTICS, CODEC, S3_HARNESS, PROTOCOL. `delegation/` — dated design history (pre-sprint). `reports/` — development evidence and the review package.

## Provenance and license
Original code: MIT (LICENSE). The license covers only the original CausalGuard code and documentation in this repository, not the upstream CausalBool repository. The upstream CausalBool method (pinned `376a11dd`) is cited and used read-only for parity tests; no upstream code is redistributed (UPSTREAM.md). Dating: PREEXISTING_WORK.md.
