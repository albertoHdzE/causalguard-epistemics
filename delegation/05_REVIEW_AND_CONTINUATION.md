# Review loop and evidence contract

## Iteration structure

| Iteration | Claude work | Codex review focus | Next boundary |
|---|---|---|---|
| 1 | WP0–WP9, substantial development results, public development repository | Semantics, genuine index method, oracle independence, inference/complexity validity, sizing, reproducibility | Approve or repair confirmatory design |
| 2 | Review repairs, protocol freeze, S1/S2/S3 confirmatory execution as feasible | Leakage, completeness, raw-data accounting, statistical conclusions, failure handling | Freeze defensible core claims |
| 3 | WP10 and feasible WP11 with new frozen tests; or deepen unresolved core study | Persistent versus assisted improvement, actual weight changes, search controls | Final scientific/release review |
| 4 | Final report, figures, limitations appendix and reproducibility release | Claim-to-evidence consistency and sprint requirements | Owner submits |

Adjust iteration count to the event calendar; never sacrifice core controls to finish an optional extension. Review failures lead to a specific repair packet. Do not rerun untouched experiments merely because a reviewer asks a documentation question.

## Long-session persistence

Maintain these files from the first implementation session:

- `STATUS.md`: current package, completed evidence, next exact actions, live process IDs and run IDs, blocked dependencies.
- `DECISIONS.md`: dated change, reason, affected hypotheses/data, whether pre- or post-freeze, owner/reviewer input.
- `RUNS.jsonl`: run ID, mode, config/commit/environment hashes, start/end, status, artifact paths. Never store secrets.
- `reports/CLAIM_LEDGER.csv`: claim, evidence class, scope, artifact/run IDs, limitations, publication status.
- `reports/REVIEW_READY.md`: final handoff below.

After compaction/restart, read these files and current Git status, recover active jobs and resume. Do not relaunch already-running experiments or regenerate a split with a new seed unintentionally. Work through the full assigned package rather than ending after a plan, scaffold or a few tests. If one dependency is blocked, complete independent packages.

## Mandatory first review packet

Create `reports/REVIEW_READY.md` with these sections:

1. Exact local root, public GitHub URL, branch, commit, release tag and dirty state.
2. Work-package table: each acceptance criterion `pass`, `fail`, `not_run` or `blocked`, linked evidence.
3. Commands executed, environment/versions, test counts and raw output locations. Avoid listing tests as passing from their mere existence.
4. Architecture and boundary diagram; upstream files/revisions; actual representation and query backends.
5. Codec specification and measured accounting, with a round-trip example.
6. Semantic fixtures and adversarial cases, especially uncertainty versus resource unknown, overlaps and persistent clamps.
7. Dataset composition, independent world counts, duplicate audit, class completeness and leakage checks.
8. Development results including null/negative findings, exclusions, failures and compute use. Mock results isolated.
9. Power/precision assumptions, selected confirmatory N, estimated full runtime/cost and exact frozen-run commands proposed.
10. Public clone/CI/reproduction status and license/provenance inventory.
11. Protocol deviations, scientific risks and unresolved questions that genuinely affect conclusions.
12. A concise proposed next prompt for the next Claude iteration, without assuming reviewer approval.

Include `reports/acceptance.json` (machine-readable statuses), `reports/test-output.txt`, analysis tables, plots and manifest hashes. Keep enormous raw logs outside Git with checksummed release paths if necessary. A reviewer must be able to reconstruct reported aggregates from the raw records.

## Reviewer acceptance tests

Codex should independently inspect/run, not merely read Claude's summary:

- Reproduce clean installation without the implementer's environment.
- Compare production oracle with independently hand-worked/evaluated cases; deliberately corrupt an order, witness, quantifier and serialized payload.
- Check that global claims require global evidence and selected-model predictions remain distinct from consensus.
- Inspect representation internals: connected-input don't-cares, offset materialization, overlap handling, and whether a BDD replaced rather than supplemented the claimed index method.
- Reconstruct code lengths including decoder/metadata and confirm target-object equality across comparators.
- Verify version-space completeness claims, model-class misspecification, and no data access from selector to hidden truth.
- Trace representative prompts, feedback and raw outputs; detect label leakage and privileged-control mislabelling.
- Recompute a primary table and bootstrap interval from raw runs; check world-level clustering and denominator rules.
- Inspect split grouping, final test access history, candidate selection and null controls.
- Verify public remote, exact commit, license scope, clone reproduction and provenance dates.

## Review verdict vocabulary

`accept_for_confirmatory`: first-stage implementation/design meets its evidence contract.

`accept_with_narrower_claim`: some planned claims are unsupported but remaining ones are defensible; name the changed scope.

`revise`: specific repairs are required before meaningful confirmatory execution.

`invalidated_run`: a defect/leakage invalidates some results; preserve historical records, document scope, freeze a correction and use new tests as necessary.

None means “the scientific hypothesis is true.” Acceptance concerns the validity of testing it.

## What Alberto should bring back

The public repository URL, `reports/REVIEW_READY.md`, exact commit hash and Claude's final summary. The files remain available locally, so copying the entire output into chat is unnecessary. Codex then reviews against this packet and writes a bounded repair/next-experiment prompt.
