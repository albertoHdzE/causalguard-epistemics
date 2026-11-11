# Review R2 evidence and reproduction

Run commands from the project root with its locked `.venv`. Review content is `161123c98f88f78637c81b13b93d0749ae03243f`; local HEAD `9de376bf5fee11688d82463d1a4d7808867203e1` changes only the two disclosed documentation files. The project was clean when review began. This review adds documents and diagnostic scripts only; it does not change production source, tests, configurations, raw runs or release artifacts.

## Manifest and suite

```sh
.venv/bin/python scripts/verify_artifacts.py artifacts/manifest_r2.json
CAUSALBOOL_ROOT=/Users/alberto/.cache/causalguard/CausalBool .venv/bin/python -m pytest -o addopts='' -q
```

All 2,474 required files verify, plus the two optional assets. See [manifest_verification.txt](manifest_verification.txt). The pinned upstream checkout is `376a11ddf25063d49dc8f6cd98bbb3baf2e1cc43`.

The suite produced **163 passed, one setup error** in 95.99 seconds: [test-output.txt](test-output.txt). `test_http_adapter_retries_5xx_not_4xx` could not bind its localhost HTTP server (`PermissionError: Operation not permitted`); sandbox restrictions prevented this check. The two warnings concern tiny missing-outcome fixtures with insufficient sample variance. Do not state that this review independently ran all 164 successfully.

## Byte-for-byte analysis reproduction

```sh
MPLCONFIGDIR=/tmp/causalguard-review-r2/mpl .venv/bin/python -m causalguard analyze-s2-v2 --run-dir runs/S2-dev-v2 --mc-run-dir runs/S2-dev-v2-mcdiag --out /tmp/causalguard-review-r2/s2-reproduction
MPLCONFIGDIR=/tmp/causalguard-review-r2/mpl-s1 .venv/bin/python -m causalguard analyze-s1-v2 --run-dir runs/S1-dev-v2-panel --out /tmp/causalguard-review-r2/s1-reproduction
MPLCONFIGDIR=/tmp/causalguard-review-r2/mpl-s3 .venv/bin/python -m causalguard analyze-s3-v2 --run-dir runs/s3v2-diag-qwen25_7b-dev --run-dir runs/s3v2-diag-gemma3_12b-dev --run-dir runs/s3v2-heldout-qwen25_7b-dev --out /tmp/causalguard-review-r2/s3-reproduction
```

All three summaries and the S2 per-world CSV match their committed originals byte-for-byte. Full hashes are in [verification.json](verification.json); command outputs are [S1](s1-reproduction.txt), [S2](s2-reproduction.txt) and [S3](s3-reproduction.txt). Historical v1 summaries were independently reproduced in R1; this review verified their manifest entries but did not repeat that historical analysis.

Reproducibility does not establish absence of bugs: the S1 summary reproducibly contains erroneous zero RSS values, and S3 reproducibly omits C aggregate coherence flags. The review identifies those corrections explicitly.

## Additional diagnostics

```sh
.venv/bin/python reports/review_r2/repro_runtime.py
.venv/bin/python reports/review_r2/repro_concurrent.py
.venv/bin/python reports/review_r2/repro_parent_death.py
.venv/bin/python reports/review_r2/repro_s2_contract.py
.venv/bin/python reports/review_r2/audit_s2_science.py
.venv/bin/python reports/review_r2/repro_s3.py
```

The first three create temporary fixture runs only. Parent-death diagnostics explicitly clean up their worker group and child. Their consolidated observations and raw S1 RSS examples are in [runtime_evidence.json](runtime_evidence.json). They reproduce defects at the reviewed revision; after repair their old expected behavior must not be treated as acceptance criteria. Convert them into regression tests that require the corrected behavior.

The S2 contract diagnostic copies five saved worlds to temporary storage, creates a coherent subset plan/configuration and rebinds attempt plan hashes before removing scientific outcomes. Thus its missing-cell/query findings are independent of the separate attempt-identity validation defect. It reduces bootstrap replicates and disables sizing/figures for this small accounting fixture only. Output: [s2_contract_evidence.txt](s2_contract_evidence.txt).

The S2 science audit reads all saved records, checks grid shape and count-derived fields, and independently enumerates the complete small class for 64 queries. Its 347,904-record consistency check is **not** an independent truth verification of every saved prediction. The exhaustive 256-network check is separate. Output: [s2_science_evidence.json](s2_science_evidence.json).

The S3 diagnostic reads saved calls only and reproduces label reversions, the budget shortcut, C aggregate inconsistencies and the semantic duplicate: [s3_evidence.json](s3_evidence.json). No LLM calls were made during review.

## Verification limits and authorization

GitHub API access failed in this environment and the web retrieval of the repository returned a cache miss. Remote CI, fresh public clone and download-back checks remain implementation-author reports; local history, tag content and artifact hashes were checked. The official sprint page was available and confirms November 13–15, 2026.

[DECISION.json](DECISION.json) is a **review denial**, not a production freeze record. `confirmatory_authorized` is false and `approved_studies` is empty. `docs/FREEZE_RECORD.json` remains absent. Neither confirmation nor WP10/WP11 was started. The review's file hashes are in [review_manifest.json](review_manifest.json), which excludes itself.
