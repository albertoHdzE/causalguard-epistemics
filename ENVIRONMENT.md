# Environment (public-safe inventory)

Recorded 2026-11-09 (sprint implementation iteration 1). No credentials, tokens or personal paths beyond the project root are recorded.

| Item | Value |
|---|---|
| Hardware | Apple M3 Ultra, 28 CPU cores, 96 GiB unified memory (macOS 27.2, arm64) |
| Python | CPython 3.12.13 in a project-local venv created by `uv` 0.10.10 |
| Core deps | numpy 2.5.4 (only hard dependency of the core package) |
| Solver extras | python-sat 1.9.dev21 (CaDiCaL 1.5.3 default; Glucose 4 for DRUP proofs), dd 0.6.0 (pure-Python BDD) |
| Other | matplotlib 3.11.2 (figures), pytest 9.2.0, ruff 0.17.4 |
| Lock | `requirements-lock.txt` (exact versions); `pyproject.toml` extras `[solvers,plots,dev]` |
| Local model servers (S3) | Ollama 0.40.15 at 127.0.0.1:11434 (qwen2.5:7b Q4_K_M, digest 845dbda0ea48…); LM Studio at 127.0.0.1:1234 (gemma-3-12b-it, MLX 4-bit; no digest/version exposed) |
| Paid inference | none used; harness refuses non-localhost endpoints unless `allow_remote=true` |
| Wolfram | not required and not used |
| Upstream | CausalBool @ 376a11dd (read-only parity reference, see UPSTREAM.md) |

Resource sharing during development runs: S1 (16 CPU worker processes) ran concurrently with the two S3 pilots (GPU-bound local inference). Latency figures from S1 are therefore measured under a shared machine load and are reported as such; they are engineering measurements, not hardware-normalized benchmarks.

## Install (tested)

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e '.[solvers,plots,dev]'
.venv/bin/python -m pytest            # offline tests
```

Plain `pip install -e '.[solvers,plots,dev]'` in any Python >= 3.11 environment also works. Clean-clone verification: `reports/RELEASE_CHECK.md`.
