# R1 verification evidence

All commands below were run against release commit `967fc9c8130b6d975dfc527df1ba513e38288b6f`, whose production code matches `371b04ec5be9023c9536e7088064896105eaea13`. Only review documents/diagnostic artifacts were added to the working tree. No scientific confirmatory run or inference call was made.

## Reproduction and tests

From the project root:

```sh
.venv/bin/python scripts/verify_artifacts.py
CAUSALBOOL_ROOT=/Users/alberto/.cache/causalguard/CausalBool .venv/bin/python -m pytest -o addopts='' -q -k 'not test_http_adapter_retries_5xx_not_4xx'
.venv/bin/python -m causalguard analyze-s2 --run-id S2-dev-v1 --run-id S2-dev-null-v1 --out /tmp/causalguard-review-r1/s2-reproduction
MPLCONFIGDIR=/tmp/causalguard-review-r1/mpl .venv/bin/python -m causalguard analyze-s1 --run-id S1-dev-v1 --run-id S1-dev-v1-rerun --out /tmp/causalguard-review-r1/s1-reproduction
```

- [manifest_verification.txt](manifest_verification.txt): 40 checked, 40 match, zero missing.
- [test-output.txt](test-output.txt): 137 passed, one deselected. Initial full-suite attempt hit `PermissionError: [Errno 1] Operation not permitted` in `HTTPServer(("127.0.0.1", 0), ...)` at `tests/test_llm_harness.py:194`. The deselection is an explicitly recorded sandbox limitation, not evidence that the HTTP test passed.
- [reproduction_checks.json](reproduction_checks.json): both reconstructed summary files match committed bytes and hashes. Recreated figures are not needed for this byte-for-byte claim.

The upstream path is a local read-only cache. Another machine should obtain the declared pinned upstream and use its own path. Public API verification failed with a connection error; no permissions escalation or publication was attempted by this review.

## Independent diagnostic counterexamples

```sh
.venv/bin/python reports/review_r1/repro_guard.py /Users/alberto/Documents/projects/AI-security/AI-x-epistemics
.venv/bin/python reports/review_r1/repro_s2.py
.venv/bin/python reports/review_r1/repro_timeout.py
```

| Diagnostic | Retained result | Meaning |
|---|---|---|
| [repro_guard.py](repro_guard.py) | [guard_results.json](guard_results.json) | Temporary git fixture: runtime registry dirties freeze; scope ignored; resume absent; append after torn JSON loses valid record. |
| [repro_s2.py](repro_s2.py) | [s2_diagnostic_results.txt](s2_diagnostic_results.txt) | Tautology fast/SAT disagreement and same-seed mechanism-dependent primary measurement inputs. |
| [repro_timeout.py](repro_timeout.py) | [timeout_results.json](timeout_results.json) | Nested timed operation erases the outer item cap. |

These are **diagnostics of the reviewed revision**, not the project's new acceptance suite. `repro_s2.py` asserts that the original faults reproduce; after repair those assertions should fail and production regression tests should assert the correct behavior. The guard script's temporary `FREEZE_RECORD.json` is confined to a disposable fixture, not the project. The timer test waits approximately 0.12 seconds; it runs no study.

Additional inspection checked all 256 three-input Boolean functions at n=3,7,256 against enumerated prime-implicant covers for the index bit length; it found no shorter alternative in that limited check. This supports no general optimality claim and is not needed to reproduce the reported study.

The review itself does not retroactively modify Claude's acceptance decisions or the existing release manifest. Publish these new review files with the subsequent development revision and its own manifest.
