# Release check R4 (post-tag, docs only)

2026-11-11. Tag `v0.4.0-dev` → `7a6196fdbdc3593ab8a138e4757eb4014fcc826c` (docs-only over content commit
`957c8d73be5a3a5a6c301929f7f4036d70d70ac3`). Performed by the author from a fresh temporary directory.

| Check | Result |
|---|---|
| asset downloaded back (`gh release download v0.4.0-dev`) | sha256 `0e96b2912e268f94bb69388b4fd6de37784a80c1cf443acc5247e04f6fcb57b9`, equal to the manifest |
| fresh clone at the tag | HEAD `7a6196f` |
| documented locked install (`README.md`: `pip install -r requirements-lock.txt && pip install --no-deps -e .`, Python 3.12) | success |
| asset extracted at the repository root, `scripts/verify_artifacts.py artifacts/manifest_r4.json` | **COMPLETE**: all 840 required files verified (release assets themselves absent in the clone, optional) |
| test suite in the clone (no `CAUSALBOOL_ROOT`) | 443 passed, 5 skipped (upstream-only tests) |
| `analyze-s4` on the downloaded raw runs vs committed summaries | map, active, known, misspec, stress, pilot and sizing summaries **byte-identical** |
| CI on the content commit | runs 43057603544 (main), 43057599956 (iteration-4): success |
| previous releases | `v0.1.0-dev`, `v0.2.0-dev`, `v0.3.0-dev` and their assets unchanged |
