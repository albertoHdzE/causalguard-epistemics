# Required separate public GitHub repository

The owner explicitly requires sharing the code separately on GitHub. This is a completion requirement, not an optional final polish item. Publication of this project is authorized by that instruction; do not ask the owner to reconfirm routine repository creation/push. Resolve actual authentication or rights problems explicitly if encountered.

## Destination and contents

Proposed repository: `albertoHdzE/causalguard-epistemics`. Verify authenticated account and whether that name already exists. If it belongs to this project, reuse it; if unrelated, use a clearly identified available project-specific suffix. Never overwrite an unrelated repository or force-push over someone else's work.

Initialize Git only inside `AI-x-epistemics/`. Commit new source, tests, codec/protocol documentation, configurations, dependency locks, small reproducibility fixtures, development summary evidence, and the dated delegation materials. The parent directory and CausalBool monorepo must not be imported wholesale.

The original Gemini conversation can remain a local historical input; omit it from the public release by default and publish the distilled research motivation instead. It contains unverified claims and is not necessary to reproduce the work. README links should not point to a file deliberately excluded from publication. Maintain `PRIVATE_LOCAL_FILES.md` locally if needed, ignored by Git.

For original project code, use an MIT license as a reasonable open research default and record it in `DECISIONS.md`. Do not apply that license to borrowed third-party files without established rights. The reviewed upstream root had no obvious top-level LICENSE; nested third-party licenses are not a license for the whole monorepo. Inventory actual provenance, cite upstream, and use a pinned external dependency/fetch path rather than indiscriminate vendoring. If redistribution rights for an indispensable copied component remain unclear, finish independent original code and report the specific release blocker; do not invent permission.

## Public structure (adapt implementation names consistently)

```
README.md                  # purpose, limitations, install, reproduce
LICENSE
CITATION.cff
PREEXISTING_WORK.md
UPSTREAM.md
pyproject.toml
<dependency lock>
src/causalguard/
tests/
configs/
scripts/
docs/                      # semantics, codec, protocol
delegation/                # dated design history
data/fixtures/             # tiny redistributable cases
reports/development/       # real, labelled development summaries
artifacts/manifest.json    # hashes/URLs for larger reproducibility artifacts
.github/workflows/ci.yml
```

Exclude credentials, environment files, local absolute-path inventory, model caches/weights, unrelated research, ephemeral environments, large uncurated dumps and sealed test labels. Use a reproducible generator plus checksums where raw data is too large; release final raw scientific records through an appropriate GitHub release asset or data archive after evaluation. Redaction cannot remove facts necessary for reproducing an inference without documenting the limitation.

## Release sequence

1. Audit file provenance and `.gitignore`; inspect the staged file list and changes, including tracked files (ignore rules do not remove tracked files).
2. Ensure unit/integration checks pass and instructions work in a clean temporary directory. Public core cannot depend on `/Users/alberto/...` or `/tmp/epistemics-causalbool-review`.
3. Create the standalone local repository and meaningful commits if not already present. Do not reset or amend owner work destructively.
4. Use authenticated GitHub tooling to create the separate public remote and push. Example only after prerequisites: `gh repo create albertoHdzE/causalguard-epistemics --public --source . --remote origin --push`.
5. Verify remote visibility, pushed commit, README rendering and public clone. Enable ordinary CI with least necessary permissions; no paid inference or secrets in pull-request tests.
6. Record actual URL, commit and CI result in `reports/RELEASE_CHECK.md`. Set initial tag such as `v0.1.0-dev` after a reproducible implementation exists; do not call it a final study release.
7. After final review/evaluation, publish frozen protocol, seeds, raw releasable traces, tables and figures with a distinct release tag and citation metadata. Put the repository URL in the sprint report and submission metadata.

If remote access is unavailable, prepare everything locally, save the exact failed command and sanitized error, and provide the one concrete action needed to restore access. Continue all local implementation. Public sharing remains `blocked`, never `complete`.

## Reproduction contract

The final README must provide tested commands for installation, offline tests, regenerating fixtures, S1/S2 development reproduction, model configuration, running/resuming S3, rebuilding tables/figures, and verifying artifact checksums. Supply a fast smoke path and a full study path with measured hardware/time/storage requirements. Neither substitutes for the other.

GitHub CI runs fast correctness and clean-install checks; large experiments are manually reproducible. If some upstream verification requires optional proprietary tools, list it separately and ensure core reproducibility remains available without them.
