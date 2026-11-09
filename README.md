# CausalGuard — compressed symbolic models for auditable epistemic improvement

**Status: development release `v0.1.0-dev` (implementation iteration 1, 2026-11-09). Not a final study release. No confirmatory result exists yet.** The sealed confirmatory experiments are prepared but deliberately not run before external review (`reports/REVIEW_READY.md`).

## What this is

A reproducible research system that asks, operationally, whether *compact executable symbolic models* help reasoning about mechanisms from **incomplete evidence**:

1. **Representation / computation (S1).** Boolean network repertoires are represented as unions of *schema (index) families* — the CausalBool anchor + offset-family method, where don't-cares may sit on **connected** inputs (Rule 110) — and queried (membership, ∃, ∀, bounded reachability with interventions) without expanding the repertoire. Every codec is an executable, independently decodable bitstring; lengths are real archive bits.
2. **Induction (S2, primary).** Given incomplete observations, all mechanisms in a declared complete hypothesis class that fit them form the version space V(D). We test whether the mechanism with the **shortest index code** predicts hidden *intervention* outcomes better than a uniformly chosen compatible mechanism — and we report where it does not.
3. **AI reasoning (S3).** Local LLMs answer the same evidence-relative questions (entailed / refuted / underdetermined) under controlled arms: initial answer, self-critique, majority of three, symbolic-witness feedback, a privileged label-disclosure control, and the exact symbolic solver.

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

## Reproduce

| Step | Command | Measured (M3 Ultra, shared load) |
|---|---|---|
| Fixture table | `python -m causalguard fixtures` | < 1 s |
| Fast smoke (3 S2 worlds) | `python -m causalguard run --config configs/s2_dev.json --run-id smoke --limit 3 --workers 3` | ~5 s |
| S2 development corpus (420 worlds) | `python -m causalguard run --config configs/s2_dev.json --quiet` | ~65 s wall on 24 workers (~25 CPU-min), ~70 MB records |
| S2 analysis | `python -m causalguard analyze-s2 --run-id S2-dev-v1 --out reports/development` | ~2 min |
| S1 development grid (335 worlds × 7 backends) | `python -m causalguard run --config configs/s1_dev.json --quiet` then `... --config configs/s1_dev_rerun.json` | ~15 min + ~15 min on 16 workers |
| S1 analysis | `python -m causalguard analyze-s1 --run-id S1-dev-v1 --run-id S1-dev-v1-rerun --out reports/development` | < 1 min |
| S3 pilot (local model server required) | `python -m causalguard.experiments.s3 --config configs/s3_pilot_qwen25_7b.json --run-id s3-pilot-qwen25-7b-dev-v2 --worlds 80 --quiet` (resumable: rerun the same command) | see docs/S3_HARNESS.md |
| S3 analysis | `python -c "from causalguard.analysis.s3_analysis import analyze; from pathlib import Path; print(analyze(['s3-pilot-qwen25-7b-dev-v2','s3-pilot-gemma3-12b-dev-v2'], Path('reports/development')))"` | < 1 min |
| Upstream parity (optional) | `scripts/fetch_upstream.sh /tmp/cb && CAUSALBOOL_ROOT=/tmp/cb python -m pytest -m upstream -o addopts="" -q` | < 10 s after clone |
| Verify artifact checksums | `python scripts/verify_artifacts.py` | < 1 s |

Raw run records (`runs/`) are large and not in git; `artifacts/manifest.json` lists their SHA-256 and the release asset that contains them. Every number in `reports/` is produced by the analysis commands above from those raw records.

## Results so far (development only)
See `reports/DEVELOPMENT_REPORT.md` (labelled development, not confirmatory), `reports/DESIGN_SIZING.md` and `reports/CLAIM_LEDGER.csv`.

## Repository map
`src/causalguard/` — `schema` (types), `semantics`, `reference` (independent oracle), `index_repr` (index families), `codec`, `query` (index backends), `bdd_ref` (independent BDD), `proofcheck` (RUP), `versionspace`, `generators`, `dedup`, `s3_tasks`, `llm/`, `runner`, `stats`, `experiments/`, `analysis/`, `upstream_adapter`.
`docs/` — SEMANTICS, CODEC, S3_HARNESS, PROTOCOL. `delegation/` — dated design history (pre-sprint). `reports/` — development evidence and the review package.

## Provenance and license
Original code: MIT (LICENSE). The license covers only the original CausalGuard code and documentation in this repository, not the upstream CausalBool repository. The upstream CausalBool method (pinned `376a11dd`) is cited and used read-only for parity tests; no upstream code is redistributed (UPSTREAM.md). Dating: PREEXISTING_WORK.md.
