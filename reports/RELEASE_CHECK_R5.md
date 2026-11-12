# Release check — v0.5.0-dev (R5)

Date 2026-11-11/12. Performed by the implementation agent (not independent).

| Item | Result |
|---|---|
| Content commit | `b6aeab3d4e26cc9344001116838fde8f6d668024` — CI run 43124522816 green (ubuntu 3.12, macOS 3.12, upstream parity) |
| Tag `v0.5.0-dev` peeled commit | `799980679c90193bba9a0f9237043024d48818ff` (docs only on top of the content commit: review package, acceptance, review request) |
| Release | https://github.com/albertoHdzE/causalguard-epistemics/releases/tag/v0.5.0-dev (prerelease); older tags/releases unchanged |
| Asset | `causalguard-dev-runs-v0.5.0-dev.tar.gz`, 6,066,660 bytes, sha256 `e0627fe50efc2bc414c2524e6f9c67828e13d1b057ef04206b196a6353f65089`; downloaded back: identical; all paths under `runs/`, none absolute or `..`; no third-party model files |
| Fresh clone at tag + locked install (`requirements-lock.txt`, `pip install --no-deps -e .`) | ok |
| `scripts/verify_artifacts.py artifacts/manifest_r5.json` after extracting the downloaded asset | COMPLETE: 1,525 required files verified |
| Tests in the fresh clone | 469 passed (184.9 s) |
| Reanalysis (no model calls): g-champion, g, g-external ×2, m, a-det, a-select, a-ai, c, c (v3) | 10/10 outputs byte-identical to `reports/development_r5/` |

Not checked: re-running the external G panels from a fresh machine (needs the pinned Biodivine checkout); re-running
model calls.
