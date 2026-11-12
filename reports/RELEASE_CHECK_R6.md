# Release check: v0.6.0-dev (R6)

Date 2026-11-12. Performed by the implementation agent (not independent).

| Item | Result |
|---|---|
| Content commit | `ec16507a70174058d8225b4353e30b2f7e7011bd`. CI run 43167162081 green: ubuntu 3.12, macOS 3.12, upstream parity |
| Tag `v0.6.0-dev`, peeled commit | Docs only on top of the content commit: manifest, this file, acceptance identities. The peeled SHA is recorded in the post-tag check below |
| Release | https://github.com/albertoHdzE/causalguard-epistemics/releases/tag/v0.6.0-dev (prerelease). Tags and releases v0.1.0-dev to v0.5.0-dev are unchanged |
| Asset | `causalguard-dev-runs-v0.6.0-dev.tar.gz`, 32,040,553 bytes, sha256 `8f63026d23f7b0b6ec9b2dcdc786927f209dc8ae9c41d6eee078fa614950b3e8`. Contents: the 14 `runs/r6-*` runs, `runs/registry.jsonl` and `runs/r5-calls/ledger.jsonl`. All paths are under `runs/`, none absolute or containing `..`, and there are no third-party model files |
| Manifest `artifacts/manifest_r6.json` | sha256 `31d3cd790ec39c0ae07b585d0f032d2b7e9bdecd3955d15d78d00e5aa9b77c4e`. `verify_artifacts.py`: COMPLETE, 2,425 required files (2,136 raw R6 run files, 209 reports, 55 configs, 22 docs, 3 source manifests) |
| Tests (local, content commit) | 480 passed, 5 skipped (upstream parity: no local CausalBool checkout; green in CI). Output: `reports/test-output-r6.txt` |
| Reanalysis, no model calls (`scripts/r6_regen_check.sh`) | 21/21 byte-identical. R5: g-champion, g, g-external ×2, m, a-det, a-select, a-ai ×3, c, c v3. R6: g-r6 ×4, g-r6-extras ×2, s-cal v2, s, a2 |
| Item replay with current code (`scripts/r6_replay_check.py`, every 10th item of 9 runs) | 174/174 identical apart from wall-clock fields. Every stored prediction digest verifies |

Not checked here: re-running the external panels from a fresh machine (this needs the pinned Biodivine checkout) and re-running model calls.

## Post-tag verification (2026-11-12, recorded in the commit after the tag)

| Item | Result |
|---|---|
| Tag `v0.6.0-dev` peeled commit | `766e07031ef9041d72f4e490d393911776853eb6` (docs only on top of `ec16507`) |
| Release | Prerelease created with the asset; v0.1.0-dev to v0.5.0-dev unchanged |
| Asset downloaded back | sha256 `8f63026d23f7b0b6ec9b2dcdc786927f209dc8ae9c41d6eee078fa614950b3e8`, identical |
| Fresh clone at tag + locked install (`requirements-lock.txt`, `pip install --no-deps -e .`), asset extracted | `verify_artifacts.py artifacts/manifest_r6.json`: COMPLETE, 2,425 required files |
| Tests in the fresh clone | 480 passed, 5 skipped (upstream parity), 225 s |
| Reanalysis in the fresh clone (s, s-cal v2, g-r6 evaluation, a2) | 4/4 byte-identical to `reports/development_r6/` |
