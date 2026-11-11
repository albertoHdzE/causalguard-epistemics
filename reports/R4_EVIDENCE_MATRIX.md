# R4 acceptance / evidence matrix

Machine-readable form: `reports/acceptance_r4.json`. **Repair validation (P0) is separate from new scientific
results (P1–P5).** Every row points to code, tests and evidence. Development only: nothing here is
confirmatory.

## P0: bounded R3 defects

| Requirement | Code | Tests | Evidence | State |
|---|---|---|---|---|
| R3-01: required keys from the study contract; state-dependent nulls; no denominator filtering; first/middle/last omissions; nonempty nulls; empty V; noise cells | `analysis/s2_analysis.py` (`required_pred_keys`, `_check_row_values`, `world_scores`, `_contrast`) | `tests/test_completeness_r4.py` (15) | `reports/development_r4/p0_repair_evidence.json`: CSV byte-identical, summary 0 differences | done |
| R3-02: synchronous dead-supervisor refusal; immediate side-effect; late-start/resume; watchdog kept | `runner.py` (`_lifeline_closed`, `_refuse_if_supervisor_dead`) | `tests/test_runner_r4.py` (9) | reviewer repro 0/5 markers (was 5/5) | done |
| Lifecycle, completeness, full suite, offline analyses unchanged | — | 243 passed at P0; 448 at the content commit | `reports/test-output-r4.txt` | done |

## P1: method identity and contract

| Requirement | Where | State |
|---|---|---|
| Items 1–7 of the method-coverage section | `docs/S4_METHOD_COVERAGE.md` §2–§9 | done |
| Pinned manuscript + HID sources; analytic calculus / flat codec / HID mapped separately | coverage §0, §1, §5 | done |
| Parity, threshold, ordering, support locality with checked conventions; 2^c vs 2^(d−c); strict majority vs ties | `s4/analytic.py`; `tests/test_s4_analytic.py` | done |
| Encoded object, public evidence, complete H, multiplicity, order cost, symbolic operations | coverage §2–§4 | done |
| Hand-checkable worked example with opposing mechanisms + separating measurement | coverage §3 (reproduced by code) | done |
| Complete state repertoires vs complete compatible-mechanism sets; bounded case named | coverage §2 | done |
| Complexity bounds vs codec probabilities vs proof; proof / forecast / underdetermination / refusal | coverage §7; development report §9 | done |
| Initial sizes from offline computation; eight strata; strong baselines | coverage §9; `s4/tasks.py`; `docs/S4_PROTOCOL_DRAFT.md` | done |

## P2: workspace and adapters

| Requirement | Code | Tests | State |
|---|---|---|---|
| Analytic predicates alongside the ordered/shared hierarchy, versioned, fully charged, exact decoding | `s4/analytic.py`, `s4/hcode.py` (CGH-1) | `test_s4_hcode.py` (golden 25-bit length, 100 round trips, rejections) | done |
| Evidence update, query, witness, bounded counting; enumeration metered separately | `s4/mechspace.py` | `test_s4_mechspace.py` | done |
| Same semantic API for B / C / D | `s4/workspace.py` | `test_s4_system.py::test_backends_agree_on_s4_worlds` | done |
| propose / check / counterexample / revise / commit; binding; stale proofs; equal verification | `s4/checking.py` | `test_s4_checking.py` (12) | done |
| Gate / circuit / BDD offline comparisons | description-length map (index, gate, circuit, LUT, DNF, BDD vs CGH-1) | `S4_FAMILY_COST_TABLE.md` | partial: BDD and grammar lengths only; no BDD-based reasoning backend |
| Exact agreement on tiny cases; overlap, duplicates, ordering, shared subrules, inconsistent evidence, no-op interventions, incomplete enumeration, timeouts | — | `test_s4_mechspace.py`, `test_s4_hcode.py`, `test_s4_system.py` | done |
| Resource refusal, never silent expansion | h = 3 cap, materialization limit | `test_h3_enumeration_cap_is_a_resource_refusal`, `test_resource_refusal_is_not_a_proof` | done |
| S1 / S2 semantics stable | historical defaults unchanged (pairwise AMO, unweighted counts) | S1/S2 tests pass | done |

## P3: tasks, evaluator, leakage audits

| Requirement | Where | State |
|---|---|---|
| S4-A fixed-evidence claims; S4-B prototype separately scored; known-mechanism panel not mixed | `s4/tasks.py`; `offline.active_world`; `offline.known_item` | done |
| Pre-release metrics on the common frozen batch (A turn 1) replayed through B / C / D | `pilot.replay_common_batch`; report §5 | done |
| Stale certificates; wrong quantifier, order, horizon; inconsistent evidence; invalid proof text; simulator postconditions | `test_s4_checking.py`; `offline.misspec_world` | done |
| Evaluator alone holds hidden truth; serialized public payload; purchased observations logged | `s4/evaluator.py`; `audit_public_payload` | done |
| Novelty, duplicates, direct answers, overlap, isomorphism; training-only surface baselines persisted before calls | `claim_audit`, `isomorphic`; `s4_surface_baselines.json` (committed before calls) | done; isomorphism dedup is a tested function, not applied as a filter to the pilot panel (pilot worlds were not deduplicated) |
| Independent random streams; nulls, parity, order-disrupted, misspecification diagnostics | `tasks.py` seeds; `s4-misspec-dev-v1` | done |
| Fixed offline map + fixed-request replay; deterministic no-LLM controller; disagreement-guided inquiry | `s4-map-dev-v2`; pilot controller; `s4-active-dev-v1` | done |
| All outcomes visible; identity validated before scoring | runner `load_run`; `analyze_pilot` | done |

## P4: pilot and sizing

| Requirement | Evidence | State |
|---|---|---|
| Two pinned models; selection rule declared before outcomes | `docs/S4_PROTOCOL_DRAFT.md` §6; D50; provider metadata in each record | done (no LM Studio digest exposed: recorded limitation) |
| Resource contract first; ≤ 2,560 calls; local only | protocol §4; ledger 888 lines | done |
| Gates; at most one revision | report §5 (all gates passed; no revision) | done |
| Primary D − B; secondaries D − A, D − C; ablations offline | report §3, §5 | done |
| Sizing for 5 points / 80% / two-model multiplicity / simulation; runtime, tokens, storage | `reports/S4_DESIGN_SIZING.md` | done (primary tie not sizable; recommendation made) |
| Report expected agreement and costs; no handicapped baseline | report §4, §5; D49 | done |

## P5: prototype, narrative, package

| Requirement | Evidence | State |
|---|---|---|
| Reproducible CLI demo, mechanism hidden until the reveal | `python -m causalguard s4-demo`; `reports/development_r4/s4_demo_transcript.txt` | done |
| Development report, family/cost table, sizing, funding brief | `reports/S4_DEVELOPMENT_REPORT.md`, `S4_FAMILY_COST_TABLE.md`, `S4_DESIGN_SIZING.md`, `docs/S4_FUNDING_BRIEF.md` | done |
| S2 null and S3 limitations preserved; no universal, Kolmogorov or Zenil claims | report §9–§10; brief | done |
| Foundation mapping, check-before-release API, matched prevention metrics, claim audit | coverage; `checking.py`; report §5, §9 | done |
| Review package, hashes, manifest, release, download-back, fresh clone | `REVIEW_READY_R4.md`, `artifacts/manifest_r4.json`, `RELEASE_CHECK_R4.md` | see REVIEW_READY_R4 |
| Review request prompt naming the exact commit and tag | `delegation/REVIEW_R4_REQUEST_PROMPT.md` | see REVIEW_READY_R4 |
