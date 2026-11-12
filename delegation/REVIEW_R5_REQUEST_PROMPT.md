# Request: independent review of R5 (do not presume acceptance)

Repository https://github.com/albertoHdzE/causalguard-epistemics, branch `iteration-5`.
Review content commit `b6aeab3d4e26cc9344001116838fde8f6d668024`; tag `v0.5.0-dev`; asset
`causalguard-dev-runs-v0.5.0-dev.tar.gz` (sha256 `e0627fe50efc2bc414c2524e6f9c67828e13d1b057ef04206b196a6353f65089`).
Entry point `reports/REVIEW_READY_R5.md`. Contract `delegation/iteration_5/` (03_ACCEPTANCE_AND_REVIEW.md lists the
ten review questions — answer each).

## Reproduce

```sh
git clone https://github.com/albertoHdzE/causalguard-epistemics && cd causalguard-epistemics && git checkout v0.5.0-dev
python3 -m venv .venv && .venv/bin/pip install -r requirements-lock.txt && .venv/bin/pip install --no-deps -e .
gh release download v0.5.0-dev -p 'causalguard-dev-runs-v0.5.0-dev.tar.gz'   # inspect paths before extracting
tar -xzf causalguard-dev-runs-v0.5.0-dev.tar.gz
.venv/bin/python scripts/verify_artifacts.py artifacts/manifest_r5.json
.venv/bin/python -m pytest -o addopts='' -q
for t in g:r5-g-eval-v1 m:r5-m-eval-v1 a-det:r5-a-det-eval-v1 c:r5-c-bench-v2; do
  .venv/bin/python -m causalguard analyze-r5 --track ${t%%:*} --run runs/${t#*:} --champion gate --out /tmp/r5/${t%%:*}.json; done
.venv/bin/python -m causalguard analyze-r5 --track a-ai --run runs/r5-a-ai-eval-qwen25_7b-v2 \
  --run runs/r5-a-ai-eval-mistral_small_24b-v2 --det-run runs/r5-a-det-eval-v1 --selected eig --out /tmp/r5/a_ai.json
# compare with reports/development_r5/*.json (expected byte-identical)
```

External models (Track G external panels) must be retrieved separately at Biodivine Boolean Models commit
`314b2fed94689c38d3aaaf8101ed622b3501c7f7` into `~/.cache/causalguard/ext/biodivine-boolean-models` to re-run (not
needed for reanalysis). No model calls are needed to reanalyze.

## Specific checks requested

1. G: are the eight strata genuinely structurally held out from CGH (`r5/data.py`)? Is GSR a fair generic structured
   comparator, and does its alpha-insensitivity indicate a defect? Recompute the primary with
   `analysis/r5_analysis._contrast`.
2. C: verify GEN-VE's independence from `s4/mechspace.py`, its canonical-encoding bijection, and the R5-04 fix; judge
   whether the speed comparison is fair (vectorized numpy vs pure-Python D). The external compiler was not run (D55).
3. A: inspect raw episodes for the R5-02 stop-action fix and whether stopping/certainty errors are model behaviour
   or interface artefacts; check that EIG was available to the AI (it was) and the backend arms received equal numbers.
4. M: confirm panel membership uses only construction labels and PUBLIC V_H(D) emptiness; check the challenge
   policy sees no hidden values before purchase; judge the false-uncertainty/unnecessary-block definitions.
5. Proof levels: `unsat_rup_checked` vs `unsat` vs HMAC authentication in C release and M.
6. Budgets and accounting (`reports/R5_TASK_LEDGER.md`, `runs/r5-calls/ledger.jsonl`).

Return: findings with severity, a decision (accept as development evidence / revise / reject), and which single main
study, if any, should be authorized next. Do not run confirmatory studies.
