# R4 takeover inspection — independent, bounded review

Date: 2026-11-11. Purpose: inspect the newly delivered R4 package and prepare a successor-agent handoff.
Reviewer: Codex. This is **not** completion of the full R4 mathematical, methodological or novelty review.

Inspected local HEAD `e6483a673303d69f0fbf43d52e30a6725b072542`, content commit
`957c8d73be5a3a5a6c301929f7f4036d70d70ac3`, tag `v0.4.0-dev` peeled to
`7a6196fdbdc3593ab8a138e4757eb4014fcc826c`. Working tree was clean at the start. This inspection added only
handoff/review material; source, historical reports, raw runs and freeze state were not changed.

## Personally reproduced

- All **840 required and two optional** R4 manifest entries match local files.
- All **seven** S4 regenerated JSON analysis outputs are byte-identical to their committed counterparts.
  Full hashes are in `summary_comparison.json`. This includes sizing, not just pilot means.
- Full tests, with the pinned upstream available: **447 passed, one setup error, 179.55 seconds**.
  `test_http_adapter_retries_5xx_not_4xx` cannot bind its local HTTP socket in this sandbox:
  `PermissionError: [Errno 1] Operation not permitted`. It did not reach its assertion. See `test-output.txt`.
  The implementation author's unrestricted 448-pass claim was not independently repeated here.
- R3 worker-death reproduction: **0/5 side-effect markers**, all worker exits −9. See `worker_repro.txt`.
- R3 missing-prediction reproduction: first/later omissions, nonempty null and boolean mutations all refused.
  The audit inspected 364,320 saved ordinary rows and found no invalid required-key/null cases.
  See `missing_prediction_evidence.json`.
- Fresh read-only stratification of wrong initial AI verdicts, saved in `error_type_audit.json`:

| Model | Wrong verdicts | Wrong “underdetermined” | Wrong definite assertion |
|---|---:|---:|---:|
| qwen2.5:7b | 112 | 111 | 1: asserted refuted, actually entailed |
| mistral-small-3.2-24b | 116 | 115 | 1: asserted entailed, actually underdetermined |
| Total | 228 | 226 | 2 |

The latter mistral error is unsupported certainty relative to the evidence; it is not necessarily a false
hidden-world outcome. “All 228 wrong verdicts were blocked” is accurate. “228 confident false facts were
prevented” would be inaccurate. The correct lesson is mostly that the checker detects when the AI wrongly
claims there is insufficient information.

The repair evidence supports closing the original R3 reproductions. No full S2 reanalysis was run in this
takeover inspection; its unchanged summary remains an implementation-agent report plus the earlier review
history. No new model call or experiment was launched.

## Findings for the successor's scientific review

**T01 — interpretation, material.** Separate false certainty, false uncertainty, incorrect hidden-value
forecasts, and unsafe simulated actions in every future prevention result. The present pilot has only two
wrong definite assertions. More worlds of a policy that nearly always says “underdetermined” are unlikely to
answer the intended confident-error question efficiently. Preserve this pilot; design a separate representative
decision task, without selecting models solely for favorable error patterns. Keep adversarial fixtures separate.

**T02 — cost scope, material.** `s4/offline.py::stress_item` times workspace construction and `ws.check`.
It does not call `s4/checking.py::check` and `commit`. The latter common checker invokes SAT when a side is
impossible, so full verified-release latency can include the generic solver's costs. The stress speedup is a
backend result, not yet an end-to-end gate speedup. Before a scale-based AI claim, time the complete path,
including evidence/model validation, proof generation/checking, witnesses and refusals. Do not assume the
cross-check disappears at large sizes.

**T03 — certificate scope, material.** `Workspace.Limits.proof_check` defaults to false; the pilot creates
default workspaces. SAT cross-checks are not thereby all independently RUP-checked proofs. The reports use
“RUP-checkable,” which is narrower. Preserve that distinction. A trusted checker-process HMAC authenticates
the decision but is not a portable proof artifact. Audit the exact certificate levels and trusted code before
presenting “proof-carrying” or independently verified operation as achieved throughout.

**T04 — scientific extrapolation, open.** Full-hierarchy forecast gains occur in generator-matched template
and module families. DICT sharing is excluded from the averaging prior, so no gain on the order-disrupted
control is not a disproof of every possible use of shared dictionaries. Conversely it does not validate
generality of the current prior. Require a genuinely new structural population and strong structured priors.
Hold out mechanisms/structure, not merely seeds. Order selection must use public evidence and have its costs
charged. This inspection did not independently prove the weighted enumerator's correctness or novelty.

**T05 — handoff readiness, operational.** README and package metadata remain at iteration 3; the new state
is in STATUS and R4 reports. Raw runs and the historical idea transcript are ignored by git. The original
formal manuscript and HID sources are external. A fresh clone alone does not supply the full local workspace.
`HANDOFF.md` now supplies a single entry point, release/source pins, access caveats and a reading order.

These are takeover findings, not a new finalized R4-xx adjudication. They do not alter historical results.

## Recommended decision

Ready for a successor to take over **review and research design** with the supplied handoff. Not yet ready
to claim the full R4 review is complete, authorize 16–18k model calls, or freeze a main study.

Prioritize held-out unseen inference and a fair exact-counting benchmark. Retain the generic solver and
deterministic controller as serious comparators. Test where AI adds value in formulation, investigation and
assumption checking, instead of asking it to manually approximate probabilities already available exactly.

No confirmation or freeze is granted. No CI, remote release download or fresh remote clone was independently
performed in this inspection. The implementation's release-check report is available for follow-up.

## Evidence and portability

`audit_takeover.py` regenerates the byte comparisons and initial-error stratification from local raw records.
It never modifies raw records. `test-output.txt`, `manifest-output.txt`, `worker_repro.txt`,
`missing_prediction_evidence.json`, `summary_comparison.json`, `error_type_audit.json`, `verification.json`
and `manifest.json` record this inspection. The manifest hashes these files plus the two handoff documents;
it is separate from all historical release manifests.
