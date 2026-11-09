# Release check — v0.1.0-dev (development release, not a study release)

| Item | Result |
|---|---|
| Public repository | https://github.com/albertoHdzE/causalguard-epistemics (created 2026-11-09 by authenticated `gh` as `albertoHdzE`; the name did not exist before; visibility PUBLIC; anonymous HTTP 200) |
| Branch | `main` |
| Release commit and tag | recorded in `reports/REVIEW_READY.md` §1 (tag `v0.1.0-dev`) |
| License | MIT for original code (GitHub detects `MIT` after the scope note was moved to the README); upstream not included |
| CI | GitHub Actions `ci`, least privilege (`contents: read`), no secrets, no model calls. Jobs: ubuntu + macOS (lock install, ruff, offline tests, fixture table, S2 3-world smoke) and `upstream-parity` (fetches pinned CausalBool `376a11dd`, runs 5 parity tests). First run on 4566aef: **all 3 jobs succeeded** — 132 passed and 5 skipped (upstream tests, by design) per OS; upstream job 5 passed |
| Clean clone (local) | `git clone https://github.com/albertoHdzE/causalguard-epistemics /tmp/cg-clean` at 4566aef → fresh `python3.12 -m venv` → `pip install -r requirements-lock.txt && pip install --no-deps -e .` → `pytest`: **132 passed, 5 skipped**. No dependency on `/Users/...` or `/tmp/epistemics-causalbool-review` |
| Regeneration determinism | 12 S2 development worlds regenerated in the clean clone: **12/12 records identical** to the originals apart from timing/RSS fields (incl. seeded Monte-Carlo estimates) |
| Analysis determinism | `analyze-s2` re-run into a scratch dir: identical SHA-256 for `s2_summary.json` (1b6f8e8b…) and `s2_per_world.csv` (95fa2387…) |
| Provenance audit | 90+ tracked files listed with `git ls-files`; secret-pattern scan: no hits; absolute local paths only in the owner's dated pre-sprint design documents (`delegation/`, `preparation/`), which describe the local project root by design |
| Excluded | `doc/Gemini-Talk.txt` (local idea source), `.venv`, `runs/` (raw records → release asset + manifest), `dist/`, `sealed/` (nothing exists), model weights/caches |
| Raw records | release asset `causalguard-dev-runs-v0.1.0-dev.tar.gz` attached to tag `v0.1.0-dev`; SHA-256 of the asset and of every file in `artifacts/manifest.json`; verify with `python scripts/verify_artifacts.py` |
| CI on the review commit | run 42675501260 on 371b04e: ubuntu, macOS and upstream-parity all **success** |
| Test count at the review commit | 138 passed with the pinned upstream checkout; 133 passed + 5 skipped without it (later commits added tests after the first CI run) |
| Sealed confirmatory material | none generated; the confirmatory salt is derived from the future freeze commit; `docs/FREEZE_RECORD.json` absent (test-enforced) |
