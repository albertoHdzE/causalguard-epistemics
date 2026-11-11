# Release check — v0.3.0-dev (post-tag record, docs only)

Performed 2026-11-11 after tagging, with `/tmp/cg-r3/clean_clone.sh`.

1. The tag `v0.3.0-dev` was cloned fresh from https://github.com/albertoHdzE/causalguard-epistemics. The clone HEAD is
   `a02e29e91789371b2c7c58f5e87f0c4a32623ee3`, the docs-only identity commit on content `ed719ea`.
2. Documented locked install: `pip install -r requirements-lock.txt && pip install --no-deps -e .` (Python 3.12,
   macOS).
3. Offline tests in the clone: **214 passed, 5 skipped**. The skipped tests are upstream parity, because no
   CAUSALBOOL_ROOT was set in the clone. With the upstream checkout locally the result is 219 passed
   (`reports/test-output-r3.txt`), and the CI upstream-parity job passed 5/5.
4. `gh release download` fetched the assets of `v0.1.0-dev`, `v0.2.0-dev` and `v0.3.0-dev` back from GitHub. They
   were extracted in that order.
5. `scripts/verify_artifacts.py artifacts/manifest_r3.json` gave **COMPLETE: all 2,620 required files verified**,
   0 mismatches, and all 3 optional release assets matched. The 2,404 preserved R1/R2 raw files equal their
   manifest-r2 hashes.

This commit is after the tag and changes only documentation.
