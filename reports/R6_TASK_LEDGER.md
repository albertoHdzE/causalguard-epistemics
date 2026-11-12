# R6 task ledger (resumable)

Branch `iteration-6` (reviewer commits `f640e70` XDC, `246d3cd` lock, `19643dd` delegation). Implementation agent:
Claude Opus, from 2026-11-12 01:15 UTC. Resume: read this file, `delegation/iteration_6/*.md`, `docs/R6_PROTOCOL.md`,
`docs/R6_DESIGN_LOCK.json`, `docs/R6S_DESIGN_LOCK.json` (once committed), then `git log iteration-6`.

## Takeover inspection (WP0)

`git log iteration-5..iteration-6`: 24 files, +11,408 / −32.
- `r5/priors.py`: `GSR._phi` extracted from `GSR.masses` (shared by XDC); `rule_type`, `_partition_mass`, `XDC`,
  `xdc_bruteforce`, `XDC_THETAS`. `r5/forecast.py`: optional `xdc_bases` (default () = R5 table), evaluator-side
  `hidden_rule_reuse` only when `xdc_bases` is set. `r5/data.py`: split `evaluation_r6` (salt `r6-G-eval-v1`).
  `r5/external.py`: `inventory(transformed_groups=(lo, hi))` slice. `analysis/r5_analysis.py::analyze_g_r6`.
  `__main__.py`: `--track g-r6`, `--external`, `--method`, `r5-inventory --transformed-groups`.
- Configs `configs/r6/*.json` (4), manifest `artifacts/r6_source_manifest.json`, lock, protocol, review, figures script.
- Live process at takeover: `causalguard run --config configs/r6/g_external_fresh.json` (pid 31128) — not touched;
  it completed on its own (449/449, 01:12–01:24 UTC).

## State by work package

| WP | Task | State | Evidence / next |
|---|---|---|---|
| WP0 | takeover, runs complete | done | `r6-g-eval-v1` 320/320, `r6-g-ext-fresh-v1` 449/449, both from `246d3cd`, one attempt per item |
| WP1 | XDC audit | done — no defect | `docs/R6_XDC_DERIVATION.md`, `reports/R6_XDC_AUDIT.md`, `tests/test_r6_xdc_oracle.py` (216 cases, 2.9e-12) |
| WP2 | G6 analysis and report | done | `reports/R6_GENERALIZATION.md`, `reports/development_r6/g_*` |
| WP3 | XDC-EB + sparse compatible sets | next | |
| WP4 | S inventory, split, calibration, lock | pending | |
| WP5 | S evaluation, report | pending | |
| WP6 | A2 pilot | pending | |
| WP7 | ledger, acceptance, release v0.6.0-dev | pending | |

## Resources (cumulative R6, implementation agent)

| Resource | Used | Ceiling |
|---|---|---|
| Model requests (new in R6) | 0 | 512 (global 1,081 / 3,072) |
| Offline CPU | < 0.2 h (oracle tests, analyses) | 48 h, 4 workers |
| Model server | 0 | 3 h |

Reviewer-run evaluation compute (not counted above): `r6-g-eval-v1` ≈ 7 min × 4 workers, `r6-g-ext-fresh-v1` ≈ 12 min × 4.
