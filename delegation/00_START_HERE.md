# Claude implementation handoff — v2

Prepared 2026-11-09. Owner: Alberto. Implementer: Claude. Reviewer: Codex, with owner oversight. This package delegates substantial implementation sessions; it does not claim implementation or research completion.

## Objective

Build **CausalGuard: compressed symbolic models for auditable epistemic improvement**, a standalone public research repository and reproducible experimental system. Test whether index-based representations enable exact queries over large Boolean repertoires, and whether executable description length helps select predictive mechanisms from incomplete evidence. Add a carefully controlled LLM interface and a subsequent weight-improvement experiment. Do not replace this project with a generic LLM correction demo.

The owner's clarification is substantive: scientific knowledge is model-mediated and fallible; compact executable representations may constitute useful explanatory understanding. We will evaluate that proposition operationally through reconstruction, queries, held-out prediction, interventions, uncertainty and cost. We will not presume compression implies truth or that every repertoire compresses efficiently.

## Read in order

1. `01_SCIENTIFIC_CONTRACT.md` — current claims, semantics and complexity definitions.
2. `02_EXPERIMENTS_AND_STATISTICS.md` — studies, sizing, controls, stopping rules.
3. `03_IMPLEMENTATION_WORKPACKAGES.md` — ownership, dependencies, acceptance criteria.
4. `04_PUBLIC_REPOSITORY.md` — mandatory separate GitHub repository and reproducibility.
5. `05_REVIEW_AND_CONTINUATION.md` — evidence package and successive review cycles.
6. `CLAUDE_PROMPT.md` — executable delegation instructions.

Historical inputs: `../doc/Gemini-Talk.txt`, `../preparation/RESEARCH_PLAN.md`, and the feasibility script/results. The Gemini conversation is an idea source, not a scientific authority. The v2 contract supersedes the old plan wherever they differ. A current owner instruction supersedes this package. Maintain `DECISIONS.md` for refinements rather than silently changing this contract.

## First long session: required endpoint

Complete work packages WP0–WP9: standalone package, genuine index representation path, independent reference, codecs, query certificates, incomplete-evidence benchmark, controls and analysis, LLM harness, substantial development experiments and review-ready public release. Use multiple sessions if needed, persisting state. Complete all independent work despite a blocked model endpoint or remote authentication.

Do not run the sealed confirmatory evaluation until the implementation and pilot design have been reviewed in the next Codex iteration. This is a scientific freeze boundary in our requested iterative workflow, not a request for approval after each task. Development experiments are authorized now. Prepare the complete confirmatory commands and resource estimates.

WP10 (persistent prompt improvement) and WP11 (weight evolution) have fully specified prerequisites and later review points. They are retained in the programme, not abandoned. The first handoff must not claim weight improvement from a prompt-only or toy-network result.

## Existing resources and unknowns

- Project root: `/Users/alberto/Documents/projects/AI-security/AI-x-epistemics`.
- No Git repository existed at that root during this preparation. Create a standalone repository here; never initialize the enclosing `AI-security` directory.
- Public upstream: `https://github.com/albertoHdzE/CausalBool`, reviewed revision `376a11ddf25063d49dc8f6cd98bbb3baf2e1cc43`.
- Temporary reference checkout: `/tmp/epistemics-causalbool-review`; replace with a reproducible pinned dependency path rather than relying on `/tmp`.
- Existing probe checked 60 networks/5,040 states. It is a feasibility check only, not the substantial experiment required here.
- Hardware, local model availability, permitted API spending and collaborators have not been confirmed. Inspect available resources without exposing secrets; default to CPU symbolic work and existing local model endpoints. Do not incur unbudgeted paid inference.
- The upstream README mentions particular hardware; that is not evidence it is available to this project.

## Completion vocabulary

Use `implemented`, `tested`, `development-measured`, `review-ready`, `confirmatory-measured`, `publicly-reproducible`, or `blocked`, with evidence. Never use `validated` without saying exactly what was checked. A mock provider proves harness behavior only. A missing experiment is not a zero effect.
