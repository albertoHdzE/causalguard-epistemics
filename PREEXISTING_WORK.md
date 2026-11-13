# Pre-existing work and dating

| Item | Date | Status |
|---|---|---|
| CausalBool programme, index-set method, upstream code and papers | before 2026-11-09 | pre-sprint, upstream, not part of this repository |
| `delegation/` v2 specification, `preparation/RESEARCH_PLAN.md`, `tools/check_causalbool_feasibility.py`, `preparation/feasibility_result.json` | 2026-11-09 07:50–08:48 local | pre-sprint preparation (commit 3900eb2) |
| Original idea conversation (`doc/Gemini-Talk.txt`) | 2026-11-09 07:50 | kept local, not published; idea source only |
| Implementation iteration 1 (package, tests, experiments, reports; release `v0.1.0-dev`) | 2026-11-09 | **pre-sprint** development (see git history) |
| Codex review R1 (`reports/review_r1/`) | 2026-11-09 | pre-sprint independent review |
| Implementation iteration 2 (repairs P1–P7, new development runs, release `v0.2.0-dev`) | 2026-11-10 | **pre-sprint** development |
| Implementation iterations 3–6 (S2–S4, R5 Tracks G/C/A/M, R6 XDC, Track S, Track A2; releases `v0.3.0-dev` … `v0.6.0-dev`) | 2026-11-10 to 2026-11-12 | **pre-sprint** development |
| Iteration 7 (R7): the sprint benchmark (`src/causalguard/sprint/`, `tests/test_r7_sprint.py`), smoke runs and three pilots (466 local requests), the pre-run gates (which FAILED after two revisions, so no design lock and no main-panel run in R7), online adapters with connectivity probes only (no benchmark item sent online), related work, report skeleton (`report/`) | 2026-11-12 | **pre-sprint** (the day before the sprint opens); must be disclosed as preexisting in the report |

| Iteration 7b (R7b): Tier W (wiring given) with two exact implementations + SAT and a cross-tier test, derivations, a verifier and forged checks (P4), per-tier scoring and analysis, pilot 4, the six R7b gates, the design lock and the local main panel (`src/causalguard/sprint/tierw.py`, `tests/test_r7b_*.py`, `reports/R7B_*.md`, `docs/SPRINT_DESIGN_LOCK.json`, `reports/SPRINT_LOCAL_RESULTS.md`) | 2026-11-12 (panel may run into the early hours of 2026-11-13; every request is timestamped in the ledger) | **pre-sprint**: designed, locked and launched before the sprint opens; must be disclosed as preexisting |

**Dating (corrected 2026-11-10, review R1 decision).** The AI × Epistemics research sprint runs 2026-11-13 to 2026-11-15 (https://apartresearch.com/sprints/ai-x-epistemics-research-sprint-2026-11-13-to-2026-11-15). All work in this repository up to and including iteration 2 (2026-11-09 and 2026-11-10) is therefore **pre-sprint work** and must be disclosed as such in any submission, following the organizers' pre-existing-work rules. The date classification does not by itself decide eligibility. Git timestamps are the authoritative record. (The iteration-1 text, which conditioned on an unknown start date, is superseded.)

## Sprint work (2026-11-13 to 2026-11-15)

Everything committed on branch `sprint` after `66e4065` is sprint work. One row per commit.

| Commit | Time (CST) | What |
|---|---|---|
| `b55110f` | 2026-11-13 | Director's review of R7b and the iteration-8 assignment (sprint addendum, D87–D89) |
| (lock v2 commit; see the line below) | 2026-11-13 | Sprint build: reasoning storage (record only), DeepSeek cost record and spend stop, P5 verify-first (manifest, templates, scorer, gates, tests), SPRINT_TASKS P5 section, P5 worked example, run configs, lock addendum v2 with the predictions (D90–D96) |
