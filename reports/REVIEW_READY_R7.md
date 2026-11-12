# R7 review entry point (pre-sprint, 2026-11-12)

Branch `iteration-7`. Everything here is pre-sprint work. **Outcome: the benchmark, the harness, the gates, the
online adapters and the report skeleton are built and tested. The pre-run gates FAILED after the two allowed
revisions, so, as the protocol requires, R7 stopped before the main panel.** No main-panel world was shown to any
model, no design lock was committed, and no benchmark item was sent to an online model. Everything needed for an
immediate launch once you decide is in place (option A below: configs, draft lock, a 240-world mock dry run).

Read in this order: this file → `reports/R7_GATES.md` → `reports/R7_PILOT.md` → `DECISIONS.md` D70–D78 →
`reports/R7_ONLINE_READINESS.md` → `docs/SPRINT_RELATED_WORK.md`.

## 1. What was built

| Piece | Where | Tested by |
|---|---|---|
| Populations: R5 G mechanisms (8 strata, new salts) + published 8-node fragments, S4 evidence/claim design; disjoint splits train / smoke / pilot / pilot2 / pilot3 / main (D70) | `src/causalguard/sprint/population.py`, `artifacts/sprint_*_manifest.json` | `test_populations_are_disjoint_and_balanced` |
| Exact reference: status and p* = num/den. Explicit counts must equal the independent D-engine counts and the SAT verdict, or the item fails | `Evaluator.from_world` + `population.reference` | 32 claims against both engines; a planted engine disagreement fails the item |
| Task S (S4 unaided arm reused: same system prompt and task rendering; new instructions, vocabulary and probability) | `sprint/tasks.py`, `docs/SPRINT_TASKS.md` (generated, hashed) | prompt-hash reproduction of every pilot request (32/32 for v2 and v3) |
| Task P: four conditions × two wordings, hash assignment (balanced round-robin, independent of answers), 4 named claims, P3 = exact counts + two witness trajectories computed from public evidence (D72) | `sprint/tasks.py`, `sprint/population.py::assign` | leak audit on 256 pilot messages and 240 main messages; P3 invariance under swapping the hidden mechanism for another consistent one; the assignment function's signature |
| Scoring (one owner): every Task S and P score, reference rows, the exact check as a release gate, cluster bootstrap, Holm | `sprint/scoring.py` | hand-built cases worked on paper; two planted scoring defects are caught |
| Surface rule fitted on the train split before any model output (D71) | `sprint/surface.py`, `artifacts/sprint_surface_rule.json` | gate G2 |
| Multi-run analysis (one command; tomorrow's online runs are two more `--run-dir`) | `python -m causalguard sprint-analyze` | regeneration byte-identical (JSON, MD and all PNGs) |
| Gates: smoke and the five pre-run gates, each with its denominator | `python -m causalguard sprint-gates` | — |
| Online adapters: DeepSeek (key handling) and Claude Opus 5.5 through `claude -p`, with a per-request wire audit | `llm/providers.py`, `sprint/online.py` | `tests/test_r7_online_adapters.py` (fake binary, planted CLAUDE.md injection) |

Tests: 480 earlier tests + 18 new, all pass. R5/R6 analyses regenerate byte-identically: 21/21
(`scripts/r6_regen_check.sh`, after the R7 changes). Ruff clean.

## 2. Smoke (`reports/R7_SMOKE.md`)

| Model | Result | Median s / request (wording v1) |
|---|---|---|
| gemma-3-4b (LM Studio) | v1 fail: never gives a probability. v2 pass under D73, status only | 1.1 |
| qwen2.5:7b (Ollama) | pass | 2.8 |
| gemma-4-12b (LM Studio) | v1 fail: prose before the JSON, a parser defect. v2 pass | 6.5 |
| mistral-small-3.2-24b (LM Studio) | v1 88 %: one reply without probabilities. v2 pass | 8.5 |
| deepseek-r1-distill-qwen-32b (LM Studio) | v1 stopped by my error after about 4 min (D75). v2 pass | 81 (up to 5,087 completion tokens) |
| llama-3.3-70b (LM Studio) | pass | 24.8 (measured during the mistral pilot) |
| qwen2.5:72b (Ollama) | pass | 30.8 |

## 3. The gates (`reports/R7_GATES.md`)

| Gate | Result |
|---|---|
| G1 ground truth | pass: 240/240 main worlds, 1,920 claims, the explicit, D and SAT engines agree |
| G2 surface | pass: surface rule balanced accuracy 0.512 on pilot-1 worlds against a 0.667 threshold. On pilot-2 and pilot-3 worlds it is 0.605 and 0.622 (thin margin) |
| **G3 floor / ceiling** | **fail, three times.** mistral-small answered "not settled" with probability 0.5 on 765 of 768 turn-1 claims over three pilots, whatever the wording. qwen2.5:7b passed under v1 and v2 (0.413, 0.445) and fell to the floor under v3, reasoning first (0.338) |
| G4 no leak | pass: 240/240 main-panel follow-ups |
| G5 disjoint | pass: 0 overlaps between the 240 main worlds and the 104 smoke and pilot worlds, and the 148 mechanisms of earlier model-facing runs |

## 4. Pilot results (PILOT NUMBERS; `reports/R7_PILOT.md`)

- **qwen2.5:7b** (pilot 1, v1): overclaim 0.54 [0.40, 0.67], underclaim 0.35 [0.21, 0.50], balanced accuracy 0.41.
  Under P1 it gives up a correct answer 0.54 of the time, and P3 repair is 1.00, so discernment is 0.46 [0.13, 0.81].
  Under v3 it hedges far more: underclaim 0.60, P1 capitulation 0.11, discernment 0.78 [0.47, 1.00].
- **mistral-small-24b**: never commits on its own (underclaim 1.00, overclaim 0.00). It yields completely when told
  it is wrong (P1 capitulation 1.00 in pilots 1–2) or asked to commit (P2 forced overclaim 1.00).
- **Neither model uses the probability as an estimate:** qwen's values are 1.0, 0.5 or 0.0, matching its verdict.
- **P0 instability is 0 for both:** the neutral follow-up changes nothing.

## 5. Main local results

**Not run.** The gates failed after two revisions, so the protocol's stop rule applies. Requests used: 466 of the
6,000 local requests (all in ledger phase `SPRINT`: smoke 82, pilots 384). Online: 2 Claude and 1 DeepSeek
connectivity probes on non-benchmark prompts, out of 5 each.

## 6. Predictions against outcomes

The main panel was not run, so no prediction can be scored against main-panel data. Against the pilots, for
information only:

| Prediction | Pilot evidence (not a test) |
|---|---|
| Director: small models overclaim on more than a third of OPEN claims | qwen 0.54 / 0.37 / 0.29 over pilots 1–3; mistral 0.00. Mixed |
| Director: at least one model underclaims more than it overclaims | yes in every pilot (mistral; qwen in pilots 2–3) |
| Director: P2 raises overclaiming in every model | forced overclaim P2 0.43–1.00 against P0 0.00 in every pilot. Consistent |
| Director: discernment positive but well below 1 for every local model | qwen 0.23–0.78, mistral 0.00–0.14 (zero is not positive) |
| Director: the surface rule is far below the checker | 0.51–0.62 against 1.00. Yes |
| Mine (draft lock): at least two local models answer "not settled" on more than 90 % of claims | open; one model so far |

## 7. Online readiness (`reports/R7_ONLINE_READINESS.md`)

- **DeepSeek** (`deepseek-v4-pro`; the `.env` name is not an API id): connectivity ok. Thinking is on by default and
  temperature has no effect. Estimated $1–13 at peak rates for 480 requests, about 20–80 min with 8 workers.
- **Claude Opus 5.5** via `claude -p`: two-turn session ok. No CLAUDE.md, memory, hooks, tools, MCP or skills reach
  the model, and every request is audited from the CLI's own record. Not "our prompt and nothing else" in the strict
  sense: about 575 tokens of fixed harness context are added to every request (SDK identity sentence, account e-mail
  notice, environment/model/date block). My recommendation is to run it and disclose that verbatim. Your decision.
- **API key:** in no file, log, record, snapshot or git history (23,627 files scanned).

## 8. What already exists in the literature, and what appears to be new (`docs/SPRINT_RELATED_WORK.md`)

**Already exists:**
- the three-valued True/False/Unknown labels (ProofWriter's open-world assumption, FOLIO);
- abstention benchmarks (SelfAware, Known-Unknown Questions, AbstentionBench);
- verbalised-confidence calibration;
- flip-under-challenge and sycophancy measurements (FlipFlop, Sharma et al., Wang et al.).

**Appears new, judged against those references:**
- an exact, evidence-relative status with an exact probability for open claims, from two engines that must agree;
- a randomised design in which a valid, checked challenge sits beside an empty one, so that discernment can be
  measured;
- the same exact check used as a release gate, with its limit measured outside the class (R5 Track M,
  preexisting).

All 14 references were opened. ProofWriter and FOLIO were also checked in the paper text.

## 9. Deviations and defects (all in DECISIONS.md)

- **D73 (smoke repairs, before any pilot):** last-JSON-object parser; an answer is valid when its verdict is valid;
  `max_tokens` 3000.
- **D75: my operator error.** I stopped the R1 smoke after about 4 minutes on a wrong belief about elapsed time.
  Disclosed, and R1 was re-smoked.
- **D76:** pilot revision 1 (schema without example values), plus the main panel raised to 240 from qwen's SE
  estimate.
- **D77:** parser accepts integer claim ids. The analysis always re-parses from the raw outputs (500 answers
  changed in qwen's pilot-2 run, all integer ids).
- **D78:** pilot revision 2 (reasoning first). A gate-code defect was fixed: gate 3 had compared pilot-2 models with
  pilot-1 reference rows; it now uses the same worlds.
- **Not done:** the main local panel and `reports/SPRINT_LOCAL_RESULTS.md`; the lock (only a draft,
  `reports/development_r7/SPRINT_DESIGN_LOCK.DRAFT.json`); figures exist for the pilots only. No release tag (as
  instructed).

## 10. Resources

- **Local requests:** 466 / 6,000.
- **Model-server time:** about 1.5 h (smoke and pilots).
- **CPU:** under 1 CPU-hour offline (surface-rule fit, gates, tests, regeneration).
- **Online:** 3 connectivity requests (Claude $0.0096 by the CLI's own count; DeepSeek a few hundred tokens).

## 11. Where the director's plan is wrong or will not impress the judges

1. **Gate 3 tests a model, not the task, and it stops the study for the wrong reason.** A model with a constant
   policy ("not settled" everywhere) has balanced accuracy exactly 1/3 on any worlds, so no generator change and no
   wording that the model ignores can pass the gate. Meanwhile the task itself is off floor and off ceiling for
   another model (qwen 0.41–0.45 under v1/v2), and the surface rule (0.51–0.62) shows the items are neither
   trivial nor unreadable. The gate should read "at least one pilot model is off floor and ceiling, and the
   reference rows are not at ceiling". A constant-policy model is a result to report (mistral: abstain by default,
   yield on demand), not a reason to stop. Evidence: `reports/R7_GATES.md`, `reports/R7_PILOT.md`.
2. **P3 hands over the answer, so "repair" measures deference to an authoritative message, not evidential
   updating.** Repair under P3 was 1.00 for both models in pilots 1–2, and 0.89–1.00 in pilot 3. The checker line
   states each named claim's status, so a model that copies any message labelled "exact checker" gets full marks,
   and discernment collapses to 1 − capitulation(P1). Judges who know the sycophancy literature will see this. The
   remedy is one more condition: **P4, a confident checker-styled message that is wrong** (a fabricated status
   whose "witness" fails replay against the evidence). Discernment is then repair(P3) − acceptance(P4), which
   separates trust in evidence from trust in authority. P1 against P3 changes both the content and the authority
   framing at once, which confounds them.
3. **The probability task is not answerable by these models, and p* is not computable by hand.** p* is a count over
   up to 10^10 mechanisms. Both pilot models output only 0, 0.5 or 1. Probability error against p* will mostly
   measure that convention, so it should be a secondary at most. The headline should stay with status and pressure.
4. **Elicitation is first-order and the plan treats it as a detail.** Moving from JSON-only to reasoning-first
   changed qwen's underclaim from 0.35–0.49 to 0.60 and its P1 capitulation from 0.54–0.77 to 0.11. Whichever
   wording is locked, the report must say that the measured "honesty" is conditional on the elicitation. A
   two-wording design for Task S (as for Task P) would show it. Reasoning-first costs 5–10× the tokens, which
   rules out the 70B models at 240 worlds today (about 25 h for qwen2.5:72b).
5. **Overclaim and underclaim alone do not describe a model; the judges need a single honest summary.** Both
   pilot models are at or below the surface rule, a non-reasoning lookup table, on balanced accuracy. The
   strongest framing for the judges is likely: "local models either guess or abstain wholesale; neither knows what
   its evidence settles, and both yield to pressure". The exact check is the remedy that makes released claims
   correct inside the class. That needs the frontier models to look different, which is tomorrow's question.
6. **The surface-rule margin is thinner than gate 2 suggests.** Gate 2 is declared on pilot-1 worlds (0.512). On
   pilot-2 and pilot-3 worlds the same rule reaches 0.605 and 0.622 against a 0.667 threshold. Base rates vary
   between samples, from 62 to 76 % open; the main panel's is 69 %.

## 12. Decision needed from you (options; nothing has been launched)

- **A (recommended): relax gate 3 as in point 11.1 and run with wording v2 (JSON only).** Launch-ready:
  - configs: `configs/sprint/main_*.json` (all `task_wording: v2`; R1 on a half panel of 120 worlds, decided from
    smoke timing, 81 s/request), `configs/sprint/online_*.json`;
  - draft lock: `reports/development_r7/SPRINT_DESIGN_LOCK.DRAFT.json`, built from
    `reports/development_r7/lock_inputs_DRAFT.json`;
  - mock dry run: 240 worlds and 480 requests end to end, analysed in `reports/development_r7/dryrun_main_mock/`.

  Estimated server time: about 9.9 h for six models at full panel plus 5.4 h for R1's half. That is about 11 h of
  wall time with Ollama and LM Studio running side by side. Steps: commit the lock (`python -m
  causalguard.sprint.lock reports/development_r7/lock_inputs_DRAFT.json`, then edit `status`), take a snapshot,
  launch with `scripts/run_from_snapshot.sh`.
- **B:** as A, plus a P4 wrong-checker condition (point 11.2). That needs a code change, new pilot worlds and a
  short pilot first. It strengthens the main claim the most, and costs about 2 hours before the main panel.
- **C:** run wording v3 (reasoning first) on the small and mid models only (≤ 24B) at 240 worlds, and the 70B
  models on a half panel. Slower, and qwen falls to the floor under it.
- **D:** keep the gate as written: no main panel, and the sprint runs only the online models on the pilot design.
  Not recommended.
