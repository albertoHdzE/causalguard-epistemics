# Codex review R1 — revise before confirmation

Review date: 2026-11-09. Reviewed code commit: `371b04ec5be9023c9536e7088064896105eaea13`; local release commit: `967fc9c8130b6d975dfc527df1ba513e38288b6f`. The intervening diff changes only release/review metadata and its manifest. Production code was not changed during this review. No confirmatory data or model calls were generated.

**Decision: accept this as a substantial, reproducible development contribution; require revisions before any confirmatory freeze.** The disclosures and negative controls are valuable. They do not establish that index-based simplicity improves prediction beyond compatible-set majority. Several executable defects also prevent authorizing the present confirmatory runner.

The current assignment is [ITERATION_2_CLAUDE_PROMPT.md](../../delegation/ITERATION_2_CLAUDE_PROMPT.md), with requirements in [REPAIR_SPEC.md](REPAIR_SPEC.md). [DECISION.json](DECISION.json) records that no study is authorized for confirmation. It is deliberately **not** `docs/FREEZE_RECORD.json` and must not be converted into an approval by the implementer.

## Answers to the four requested decisions

1. **Dating:** the official sprint starts **November 13, 2026**, and runs through November 15. All November 9 implementation, experiments and this review are **pre-sprint work**. Correct the conditional dating text and disclose this work in the submission. Source checked during review: [Apart event page](https://apartresearch.com/sprints/ai-x-epistemics-research-sprint-2026-11-13-to-2026-11-15). This date does not itself decide eligibility; preserve the organizers' pre-existing-work disclosure requirements.
2. **S2 / D21:** change the prospective primary to **index-code selection minus compatible-set majority prediction**. Keep index-minus-random-compatible as a registered historical secondary. Require the uniform-H null population, with the repaired exogenous sampling design. Retain circuit and other code comparisons; do not relabel the circuit's advantage as an index-method success. This amendment follows development inspection, before confirmation; document it as such.
3. **S3:** approve another development iteration with the controls specified in the repair packet. Do **not** approve the proposed two-opposite-mechanisms/otherwise-no-disagreement feedback as a non-disclosing treatment: it communicates the answer. It is suitable for a transparently named certificate-assisted arm. No S3 freeze yet.
4. **Freeze record:** not issued. R01–R10 below require repair and review of a concrete revised package. This is a scientific/execution rejection of the current proposal, not a request for the user to repeat authorization for development work.

## What was independently verified

- All **40/40 locally available manifest files** match their recorded SHA-256 values; no absent files.
- Re-analysis of both S2 development runs reproduces `s2_summary.json` **byte-for-byte**: SHA-256 `1b6f8e8b70b0a30e11824a26e8f6d567908d40966f6c2b48db837e99f209efdd`.
- Re-analysis of S1 original plus declared rerun reproduces `s1_summary.json` **byte-for-byte**: SHA-256 `169fbd791279ae608de5f91786b1ecb0d3ad440a16b03f6df7c9b12bb99f28a7`. It reports 28,765 exhaustive-reference comparisons without disagreement and 2,569 checked proofs plus four uncertified UNSAT results.
- **137 tests passed** with `CAUSALBOOL_ROOT=/Users/alberto/.cache/causalguard/CausalBool`; one HTTP test was deselected after the initial full run demonstrated that this sandbox forbids its localhost socket bind. This environmental restriction is not a test-code failure. The pinned upstream parity tests passed.
- Additional small, independently constructed cases reproduce the bugs below despite the green suite. Diagnostic scripts and outputs are retained in this directory; they use temporary fixtures and do not open a real seal.
- Local remote URL/tag/history were inspected. GitHub API access failed from this sandbox, and the web fetch of the repository failed. This review therefore does **not** independently attest the current remote visibility, release download or CI run. Those claims remain supported by Claude's release record; recheck them in the next release.

## Scientific interpretation

The original epistemic argument remains reasonable: imperfect symbolic models can support useful, exact conditional reasoning; compact descriptions can express inductive biases. The study should test when those biases help. Neither a negative index-versus-majority result nor a circuit-code advantage refutes that broader research programme.

At budget 16, the reproduced structured-world means are index 0.8865, compatible-set majority 0.8800, and expected randomly chosen compatible-model accuracy 0.822626. Thus:

| Development contrast | Estimate | 95% interval |
|---|---:|---:|
| Index − random compatible | +0.06387 | [0.05323, 0.07500] |
| Majority − random compatible | +0.05737 | [0.05021, 0.06486] |
| Index − majority | +0.00650 | [−0.00675, 0.01975] |
| Circuit − majority | +0.03550 | [0.02300, 0.04826] |

The numerical decomposition is exact for these reported means: `0.06387 = 0.05737 + 0.00650`. It is **not a causal decomposition** of why the index method behaves as it does. The post-hoc intervals use 2,000 bootstrap replicates; the original primary uses 5,000.

For a true query probability `p` under a stipulated uniform-compatible posterior, the posterior-expected accuracy of independently sampling a model is `p²+(1−p)²`; majority decision accuracy is `max(p,1−p)`. Their gap is nonnegative. This shows why the original comparator is weak without invoking simplicity. The actual development sampling process does not automatically justify that posterior interpretation (R02), and much of the implemented majority comparator is Monte Carlo (R07).

Do not strengthen these results into “simplicity has no effect,” “the methods are equivalent,” or “language matching is proven to cause the gains.” The current evidence suggests language/generator alignment and leaves a small index-versus-majority effect unresolved. A well-powered negative result with explicit scope is a useful sprint result.

## Findings requiring action

Line references below refer to the reviewed implementation, before repairs.

### R01 — high: exact logical verdict from floating probability

`src/causalguard/versionspace.py:512` tests `p == 1.0` or `p == 0.0` to issue an exact verdict. A three-node one-step tautology produces `p=0.9999999999999999`, so the fast path returns `underdetermined` while SAT returns `entailed`. See `repro_s2.py`. Determine possible Boolean outputs using exact support or SAT, **not a floating tolerance**. A tolerance can erase a real rare counterexample. This counterexample does not invalidate the saved S2 single-literal results, but it invalidates the public fast-path exactness claim for supported compound predicates.

### R02 — high: primary/null designs depend on the hidden mechanism

`generators.py:244` first runs hidden-world trajectories, chooses holdouts from their unvisited states, and then excludes those states from primary measurements. Lines 256–274 also reject query keys against other regimes' hidden-world observations. Replacing a hidden zero network with an identity network under the same seed changes the first 16 primary measurement inputs. See `repro_s2.py`.

This is a sampling-design issue, not evidence that selectors directly read hidden labels. It prevents treating uniform-H generation plus simple compatibility as an automatically correct uniform posterior. Generate the primary measurement/query design independently of the hidden mechanism, and characterize semantic novelty rather than relying only on `(state, intervention, horizon)` string differences.

### R03 — high: freeze execution cannot complete its lifecycle

`scripts/run_confirmatory.py:40` requires a clean checkout, but `runner.py:83,126,151` appends to tracked `RUNS.jsonl`; after the first study subsequent invocations fail. At lines 105–106 an existing run directory is rejected with instructions to use `--resume`, which is not an argument. Run directories are created before all readiness checks. Reproduced in `repro_guard.py`.

Use immutable frozen inputs plus an external/ignored runtime area, a durable planned-item manifest, and an explicit resume path bound to the same plan/config/source. Validate readiness before opening a run. Study/model authorization must be explicit: the current preflight ignores an `approved_studies` field.

### R04 — high: corrupted logs can silently discard valid results

`runner.py:97–115,190–200` ignores malformed JSONL and appends directly after a torn final fragment. A new valid result becomes part of that malformed line and disappears from both analysis and completed-item tracking. Reproduced in `repro_guard.py`. Preserve the damaged bytes; fail closed or use documented, audited recovery. Do not silently skip malformed interior records.

### R05 — high: executable analysis is not bound to its declared design

`analysis/s2_analysis.py:25,134–140` hardcodes the primary independently of the proposed configuration. Changing the config's primary would still analyze index-minus-uniform. `load` concatenates runs; duplicate world records can enter the bootstrap despite a separate unique-world count. S2 analysis ignores `failures.jsonl` entirely; S1 records failures but derives completion denominators from successful records, so a backend item that never returned can disappear from its completion rate.

Require a planned-item manifest, exact endpoint binding, uniqueness checks, complete terminal accounting, and frozen failure handling. A failure must not silently reduce N or turn a run into a complete-case result. The present reproduction found no primary duplicate-world problem in the two supplied S2 runs.

### R06 — high for execution caps: nested alarms cancel the outer limit

`experiments/s1.py:33–45` replaces and cancels the `SIGALRM` timer established by `runner.py:169–171`. A fixture with a 0.03-second outer cap returns `ok` after approximately 0.12 seconds following a nested timed operation. See `repro_timeout.py`. The parent timeout path also does not terminate the unresponsive task immediately. Enforce caps independently of nested timers; validate cancellation and cleanup on a disposable fixture, including a solver-like noncooperating worker.

### R07 — medium, essential for the new primary: majority and its precision

`versionspace.py:290` uses 4,096 Monte Carlo models for large multistep version spaces, and `s2_analysis.py:52` thresholds the resulting estimate at 0.5. This is an approximate majority, with unstable choices near ties. Probability SE alone does not characterize classification error, and an empirical zero is not exact impossibility. Freeze the numerical comparator policy and verify it against exact small spaces and larger independent samples.

Re-size for the **revised endpoint**, not the original contrast. The existing extra sizing gives only about 47% power at N=1,000 for the observed +0.0065 difference, despite high power for a hypothetical +0.05 effect. Precision around zero can still make N=1,000 useful. Do not enlarge N until significance or switch to equivalence after viewing final outcomes.

### R08 — medium: incomplete provenance and duplicate audits

`run_confirmatory.py:63` audits only `S2-dev-v1`, omitting the development null corpus; ignored raw inputs are not hash-checked before use. Within-confirmatory semantic duplicate handling and S3 cross-split auditing are absent. `scripts/verify_artifacts.py:26` skips absent reports as well as raw files. Make required-file completeness explicit, bind all applicable development inputs, and disclose how duplicate handling affects the sampling distribution. A public commit-derived seed is reproducible, not secret or tamper-proof sealing.

### R09 — high before S3 freeze: disclosure, unequal controls and baseline leakage

The proposed feedback identifies the logical label by witness availability. Keep it as certificate-assisted correction, with a matched explicit-label control. D currently has two revision rounds against B's one (`llm/harness.py:223,244`). The transfer treatment retains a conversation about the same world; compare with equally exposed context controls and call it within-world context reuse, not learned general reasoning.

`analysis/s3_analysis.py:71–100` fits its surface baseline on even-index worlds, scores odd-index worlds, and regenerates default tasks; headline model scores cover all worlds. Those are not identical test populations. On confirmation this code would train the baseline on confirmatory labels. Freeze the baseline on development and evaluate all methods on identical saved test items. Add target-polarity/complement and variable-renaming diagnostics; all present claims target value 1.

### R10 — medium: reporting must match evidence and accounting

- Replace “no transfer” with “no clear transfer detected”; the intervals include meaningful gains and losses. “Neither recognized refuted” applies to the **initial arm**, not every arm.
- Brier remains a computable score of the supplied probability vector; probability/verdict inconsistency limits its interpretation. Brier alone is not a calibration measurement. Preserve malformed/coherence diagnostics rather than choosing a validity threshold after results.
- `DESIGN_SIZING.md` uses `3/M` over correlated query comparisons. Remove that independent-trial bound or define a defensible world-level endpoint; zero observed mismatches are not a universal correctness proof.
- `codec.py:748` measures only `codec.py`, which imports other local modules. Its gzip size is not a complete standalone decoder charge. State the conditional runtime/dependencies, or package and measure the complete required decoder. `s1_analysis.py` calls archive sums `payload_sum`; correct the field label and avoid double-counting.
- Retain the distinction between bounded-indegree S1 query scaling up to 256 nodes and S2 induction at n=7,k≤3. Additional worlds improve precision within that domain, not dimensional generality. Index code lengths are encoder-specific upper bounds; a clause-minimal cover is not a general bit-optimality theorem.
- Noise-aware index MDL beating noise-intolerant exact matching does not establish index-specific robustness. Keep this stress result descriptive unless matched noise-aware alternative-code baselines are added.

## Release disposition

Keep `v0.1.0-dev` and its raw records unchanged. Preserve this review and the implementation's decision history. The next release should version corrected generators/analyses and add new development records; it must not overwrite historical evidence. After a revised package passes review, S1/S2 can be frozen independently of S3 readiness. WP10/WP11 remain separate subsequent work.
