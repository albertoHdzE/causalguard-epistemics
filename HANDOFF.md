# Research handoff — start here

Prepared 2026-11-11 for Alberto and a successor research agent (for example Fable).
This is a context transfer, not a freeze, publication approval, or authorization for a larger experiment.
It does not depend on access to the previous chat.

## Mission and freedom to rethink

Alberto's central question is: **Can OUR compact algorithmic representation of possible mechanisms help an AI infer unseen facts, recognize uncertainty, and check claims before relying on them?**

The intellectual background is algorithmic information and complexity science: short generative rules, executable descriptions, causality and inference. Boolean networks are the first controlled test environment. The research program is broader than Boolean logic. The original method includes analytic index-set rules and ordered/shared hierarchical descriptions; it is not synonymous with the flat index codec used in the first experiments.

Alberto wants a rigorous, reproducible, publicly shared result strong enough to support a research funding proposal. A positive result must be earned, not assumed. He prefers sustained autonomous work, substantial implementation assignments, and iterative independent review. Preserve negative results and failed attempts. Ask for missing information only when it actually blocks progress.

You are invited to improve or replace the current research strategy. Do not inherit the previous agents' choices as scientific authority. First reconstruct the strongest plausible mechanism of benefit, its strongest alternative explanation, and an experiment that distinguishes them. Preserve the historical record when proposing a new endpoint or language.

## Exact starting state

| Item | Value |
|---|---|
| Public repository | https://github.com/albertoHdzE/causalguard-epistemics |
| Local repository | `/Users/alberto/Documents/projects/AI-security/AI-x-epistemics` |
| R4 content under review | `957c8d73be5a3a5a6c301929f7f4036d70d70ac3` |
| `v0.4.0-dev` peeled commit | `7a6196fdbdc3593ab8a138e4757eb4014fcc826c` |
| HEAD inspected for this handoff | `e6483a673303d69f0fbf43d52e30a6725b072542` |
| Changes after content commit | Release identity/check documentation |
| Latest implementation package | `reports/REVIEW_READY_R4.md` |
| Independent takeover inspection | `reports/takeover_r4/INSPECTION.md` and its evidence files |
| Status of experiments | S1–S4 development only; no confirmatory run or S4 main study |
| Freeze | `docs/FREEZE_RECORD.json` absent at inspection |
| Model calls used in R4 | 888 local calls including pre-pilot, within the old 2,560 ceiling |

**Orientation caveat:** the existing README and package version still refer to iteration 3. `STATUS.md` and the R4 handoff describe iteration 4. Older delegation files are history, not instructions to start those runs again. This handoff does not silently supersede a frozen protocol: there is no freeze.

## Read in this order

1. This file, then `reports/takeover_r4/INSPECTION.md`.
2. `reports/REVIEW_READY_R4.md`, `reports/S4_DEVELOPMENT_REPORT.md`, `reports/S4_DESIGN_SIZING.md`.
3. `docs/S4_METHOD_COVERAGE.md` (especially the worked example and boundaries).
4. `docs/S4_FOUNDATIONS_AND_PRECOMMIT_CHECKING.md`, `docs/RESEARCH_DIRECTION_S4.md`, `docs/S4_PROTOCOL_DRAFT.md`.
5. `delegation/FABLE_RESEARCH_PROMPT.md` and `delegation/REVIEW_R4_REQUEST_PROMPT.md` for the unfinished independent-review agenda.
6. `DECISIONS.md` D45–D53, `reports/R4_EVIDENCE_MATRIX.md`, `reports/acceptance_r4.json`.
7. For history: `reports/review_r3/REVIEW.md`, `reports/FAMILY_MAP_AND_METHOD_SCOPE.md`, R2/R3 development reports. Read earlier delegation packages only as needed.

## What the results currently support

| Question | Evidence | Interpretation |
|---|---|---|
| Can the implemented symbolic backends answer these formal questions correctly? | R4 map: 5,120 matched claims; stress: 100 jointly completed claims agree | Strong development corroboration within the tested class, not proof of all implementations on all inputs |
| Does the old shortest-flat-index selector beat compatible-model majority? | S2 difference +0.000875, CI approximately [−0.0111, +0.0121] | No detected advantage; retain this result |
| Do tools help these local LLMs? | R4 D−A verdict accuracy +0.350 and +0.363 | Yes in this pilot; B/C give essentially the same benefit |
| Does D give more accurate logical verdicts than B at n=8? | Tie after the disclosed D52 commit-parsing sensitivity | No representation-specific accuracy benefit shown; exact backends should agree when they finish |
| Does the gate prevent model errors? | All 228 wrong initial verdicts blocked; 226 were false claims of underdetermination, two were wrong definite assertions | Mostly evidence of correcting excessive uncertainty; very little evidence about preventing confident false claims |
| Does structured averaging improve unseen predictions? | At 12 observations, full prior−uniform +0.089; full prior−flat analytic +0.049 | Promising development evidence; hierarchy gain is confined to the two generator-matched structured families |
| Does our computation scale better? | n=48 stress median 12.8 s vs SAT 116.5 s; n=64 D 12/12 vs B 4/12 claims | A useful lead, bounded by h≤2, this implementation/comparator and backend timing; not yet full verified-release timing |
| Does the LLM add forecasting value? | Deterministic uniform controller 0.782; AI arms about 0.54–0.59 | Current AI discards available information; solve this system-design issue before expanding calls |

These are development findings. A successful reproduction does not independently establish mathematical novelty, freedom from leakage, or generalization.

## Essential distinctions

- A complete state repertoire of ONE known mechanism differs from the complete set of mechanisms compatible with incomplete evidence.
- Majority is a decision rule over a distribution, not a competing storage format. Exact compressed and explicit counting with the same models and weights must agree.
- A shorter executable code gives an upper bound on description complexity. It is not the exact Kolmogorov complexity, nor automatically universal algorithmic probability.
- Codec-induced averaging changes the prior. Better forecasts can reflect an appropriate prior, an overly convenient generator, or both. Distinguish them experimentally.
- Verification proves a structured statement under explicit assumptions. It does not prove that the assumed mechanism class includes the actual world.
- Correctly saying “underdetermined,” forecasting a value, and proving a definite value are different accomplishments.
- A sealed Python decision object protects an application boundary. It is not by itself an independently checkable mathematical proof.

## Code map and reproduction

`src/causalguard/s4/mechspace.py`: factorized compatible mechanism sets, distinct counting via essential supports, support-local claims and witnesses.
`analytic.py`: formal-paper gate/index calculus.
`hcode.py`: CGH-1 mechanism language; inspired by HID, not a byte-compatible HID implementation.
`prior.py`: exact finite codec-weighted averaging; DICT excluded from the averaging language.
`workspace.py`: B/C/D API; B generic SAT plus explicit counts, C flat explicit, D support-schema symbolic.
`checking.py`: proposal/check/revision/commit and binding.
`tasks.py`, `evaluator.py`, `pilot.py`, `offline.py`: public tasks, hidden oracle, model episodes and offline panels.
`analysis/s4_analysis.py`: all S4 summaries and sensitivity analysis.
`runner.py`: immutable records, snapshots, worker lifecycle.

Use MCP graph discovery when available. It was not exposed during this inspection; filesystem fallback was used. Read local agent instructions before editing. Use `requirements-lock.txt` and the documented editable install, not an unpinned environment.

```sh
.venv/bin/python scripts/verify_artifacts.py artifacts/manifest_r4.json
CAUSALBOOL_ROOT="$HOME/.cache/causalguard/CausalBool" .venv/bin/python -m pytest -o addopts='' -q
.venv/bin/python -m causalguard analyze-s4 \
  --map runs/s4-map-dev-v2 --active runs/s4-active-dev-v1 \
  --known runs/s4-known-dev-v1 --misspec runs/s4-misspec-dev-v1 \
  --stress runs/s4-stress-dev-v1 --stress runs/s4-stress-dev-v2 \
  --pilot runs/s4-pilot-qwen25_7b-v1 --pilot runs/s4-pilot-mistral_small_24b-v1 \
  --out /tmp/causalguard-successor-analysis
```

Write regenerated analyses to a new directory. Do not overwrite published summaries, raw records or tags. Rerunning analysis uses no model calls. Tests include a localhost HTTP fixture that may be denied by a sandbox; report that separately from assertion failures.

## Portability: what a new agent needs

**Same machine:** the local repository contains the raw runs and environment. Verify them rather than assuming they are present. No conversation memory is needed for the directions in this package.

**Another machine:** a GitHub clone alone is insufficient for raw-data reproduction. Download release assets listed in the manifests. For R4 use the [v0.4.0-dev release](https://github.com/albertoHdzE/causalguard-epistemics/releases/tag/v0.4.0-dev), asset `causalguard-dev-runs-v0.4.0-dev.tar.gz`, SHA-256 `0e96b2912e268f94bb69388b4fd6de37784a80c1cf443acc5247e04f6fcb57b9`. Validate the archive and inspect extraction paths before extraction. Earlier studies require their earlier assets too. The shared registry is append-only; see the R4 release handoff for historical-manifest handling.

Foundational sources live outside this repository:

- Original formal paper: local `/Users/alberto/Documents/projects/CausalBool/papers/method/manuscript_formal/method_paper.tex`, SHA-256 `04ea352c0aff664180d68a395b09bd7311e634d1e975ab7edf3531b08b029366`.
- Original hierarchy sources: `index-deconvolution/protocols/hierarchy_v1/WIRE_FORMAT.md`, `index-deconvolution/hierarchy/README.md`, `index-deconvolution/PROTOCOL_hierarchy_dictionary_v1.md` under that CausalBool tree. Exact hashes are in `docs/S4_METHOD_COVERAGE.md`.
- Source tree cited for those readings: CausalBool commit `50b3d48cef9743ddbe7535752c61566360c15e98`; upstream repository https://github.com/albertoHdzE/CausalBool. Verify actual file hashes; remote accessibility at that revision was not checked in this handoff.
- Separate parity-test pin: `376a11ddf25063d49dc8f6cd98bbb3baf2e1cc43`; `scripts/fetch_upstream.sh` and `UPSTREAM.md` specify it. Do not conflate the two revisions.
- `doc/Gemini-Talk.txt` is an ignored, local historical idea transcript. The scientific intention is summarized here; its private conversational text is unnecessary to reproduce the research and must not be published automatically.

No upstream source was bundled or relicensed. If an external foundational source is unavailable, report the specific gap and continue code/data review; do not claim full original-method fidelity review without reading it.

This new handoff and inspection are local additions unless separately committed/pushed. Give an off-machine agent these files as attachments or a published commit; do not assume they are already in GitHub. A portable document packet is at `dist/fable-handoff-2026-11-11.zip`; it contains these directions and reports, not raw runs, model weights, secrets or the external manuscript.

## Recommended research decisions

1. **Finish the independent R4 scientific review before a larger run.** In particular: support-schema counting, canonical weights, leakage, duplicate/isomorphic worlds, coverage, proof levels, and end-to-end costs. The takeover inspection is not that full review.
2. **Make unseen inference the next main scientific target.** Use externally selected or structurally held-out systems, fixed code and charged ordering. Compare uniform averaging, analytic-only, full hierarchy, competent generic structured priors and a deterministic controller. Lock eligibility before seeing outcomes; choose networks in the supported class or call the test misspecification.
3. **Treat efficient exact counting as a separate potential contribution.** Derive the h≤2 theorem carefully and benchmark against a competent model counter/knowledge compiler with unique-mechanism counting. Include build, preprocessing, amortization, verification and memory; sweep budgets, not a single convenient timeout.
4. **Make the AI useful where symbolic tools cannot choose the question themselves.** Candidate roles: map a task to a formal claim, propose a useful intervention, retrieve missing assumptions, and explain checked results. Preserve a deterministic controller baseline. The system can improve AI reliability without changing model weights or making the LLM better at arithmetic.
5. **Investigate model inadequacy, not just empty compatible sets.** Construct evidence-consistent worlds outside H where a formally verified conclusion is false in the simulator. Test explicit abstention, assumption challenges and prospective class expansion. Do not pool these with realizable-world results.

The [knowledge-compilation map](https://arxiv.org/abs/1106.1819) motivates separating compactness from supported queries. [SatLM](https://arxiv.org/abs/2305.09656) is a prior example of solver-assisted language models; connecting an LLM to a solver alone is not the distinctive contribution. [Hutter, Legg and Vitányi](https://www.hutter1.net/ai/algprob.pdf) provide the algorithmic-probability distinctions. These sources motivate comparisons, not evidence that our method is superior.

## Boundaries and deliverable

Continue review, derivations, low-cost offline checks and preparation of a concrete next implementation assignment. No larger LLM budget, main study, freeze, confirmatory execution, paid inference, weight change or WP10/WP11 is granted by this handoff. Remaining calls under an old ceiling are not permission to change its experiment. Do not contact Fable or anyone else automatically; Alberto will provide the assignment.

Return an independent review with reproducible findings, a ranked research strategy, and ONE executable next-stage plan with a declared population, primary endpoint, comparator, cost ceiling, stopping rules and interpretation of failure. The value of a smarter successor is better questions and discriminating tests, not merely more experiments.
