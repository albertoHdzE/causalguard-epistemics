# Development report — implementation iteration 1 (2026-11-09)

**Everything in this report is DEVELOPMENT evidence** (public salt `dev-v1`). It was used to build and debug the system and to size the confirmatory study. It is not confirmatory evidence, and some analyses below are explicitly **post-hoc**. Sources:
- S1: `reports/development/s1_summary.json` (runs `S1-dev-v1` and `S1-dev-v1-rerun`).
- S2: `reports/development/s2_summary.json` and `s2_per_world.csv` (runs `S2-dev-v1` and `S2-dev-null-v1`).
- S3: `reports/development/s3_summary.json` (runs `s3-pilot-*-dev-v2`).

Each number can be regenerated with the commands in README.md, and raw records are checksummed in `artifacts/manifest.json`. Intervals are 95% percentile intervals from a world-clustered (stratified, paired) bootstrap. They use 5,000 replicates for the primary contrast and 2,000 for the others, all with seed 20261109.

---

## S1 — representation, compression and exact query scaling (engineering study)

**Corpus.** 335 independent worlds:
- small grid: n ∈ {4,6,8,10} × 6 families × 10 worlds;
- large grid: n ∈ {16,32,64} × 5 families × 5 worlds;
- profiling: n ∈ {128,256} × 5 families × 2 worlds.

Each world has 24 fixed queries (membership; ∃ and ∀ queries built half planted, half free; h ∈ {1,2,4,8}; clamp interventions). Seven backends were run, each item in a fresh process with a 20 s cap per query. Design exclusions are reported separately from failures: dense random functions above n=10, the reference above n=10, the literal repertoire above n=16, and index enumeration above n=12.

**Correctness (elementwise, per query).**
- Comparisons against the exhaustive direct-rule reference: 5,760 queries each for index_enum, literal, index_sat and bdd_ref, and 5,725 for index_cube (35 timed out). **0 mismatches.**
- Pairwise comparisons of every truth-valued answer for the same (world, query), across all n: **0 disagreements.**
- **0 witness-replay failures.** Every SAT-type witness was replayed by the independent reference.
- **0 codec round-trip failures**, across 7 codecs × 335 worlds; equality of the decoded canonical network means equality of the function on every state.

**Certificates.**
- index→SAT hybrid: 5,467 witness-replayed answers; 2,569 UNSAT-type answers with **independently checked RUP proofs**; 4 UNSAT answers whose proof check ran out of budget, labelled `solver_only`.
- For n > 10, 592 of 635 UNSAT-type index_sat answers were also confirmed by an independent exact method (BDD from direct rules and/or the literal repertoire). For the remaining 43, the RUP proof is the only certificate.
- The independent BDD reference itself completes only 61–71% of queries at n ≥ 64 (node budget or time cap). It is therefore *not* a universal validator, and that limit is reported.

**Outcome balance (by construction, natural outcomes retained).** Planted ∃ queries are all true (1,340) and planted ∀ counterexamples all false (1,340), by design. Free and membership queries came out near balanced: ∃ free 683 true / 657 false; ∀ free 663 / 677; membership 665 / 675; clamp-∃ 393 / 298; clamp-∀ 280 / 369.

**Capped completion (queries answered within 20 s; timeouts and unknown_resource stay in the denominator).**

| backend | n ≤ 10 | n=16 | n=32 | n=64 | n=128 | n=256 |
|---|---|---|---|---|---|---|
| index_sat (index families → CNF → SAT, hybrid) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| index_cube (pure index-family cube algebra) | 1.000 (n ≤ 8), 0.976 (n=10) | 0.898 | 0.602 | 0.495 | 0.496 | 0.475 |
| bdd_ref (independent, direct rules, one fixed order) | 1.000 | 0.935 | 0.808 | 0.722 | 0.708 | 0.608 |
| literal repertoire | 1.000 | 1.000 | excluded | excluded | excluded | excluded |

Median latency of completed queries: index_sat 1–31 ms (n=4 to n=256); index_cube 0.1–2.6 ms; bdd_ref 0.1–61 ms. Construction medians are under 0.04 s for the index representation at n=256. The machine was shared with the S3 pilots, so these are engineering measurements, not benchmarks. Plot: `reports/development/s1_completion.png`.

**Reading.** The index representation answers point and short-horizon queries without expanding the repertoire. *Pure* index-family cube algebra does not scale for temporal queries: computing complements of family unions blows up, especially for parity. The index families combined with a SAT back end answered every development query, with witnesses or checked proofs. Speed claims must separate those two contributions. The SAT hybrid is labelled as a hybrid (`representation_backend=index_families`, `query_backend=sat_hybrid`), and it never silently replaced the index method.

**Compression (median archive bits of the same canonical network, per cell).** Full table: `s1_summary.json["median_archive_bits"]`; plot: `s1_bits_vs_n.png`.

| family | n=16: index / gate / circuit / bdd / lut / lzma | n=256: index / gate / circuit / bdd / lut / lzma | best codec at n ≥ 16 |
|---|---|---|---|
| sparse conj/disj | 512 / 432 / 856 / 992 / 1,496 / 2,312 | 13,076 / 11,812 / 18,868 / 21,216 / 29,064 / 20,840 | gate (index 2nd) |
| canalizing | 672 / 832 / 920 / 960 / 776 / 1,784 | 15,584 / 16,340 / 17,400 / 18,808 / 15,588 / 21,692 | index (n ≤ 32); dnf ≤ index for n ≥ 64 |
| parity | 4,512 / 424 / 760 / 1,328 / 744 / 1,520 | 153,348 / 10,544 / 15,772 / 24,960 / 15,780 / 16,744 | gate; index worst of 8 |
| modular | 776 / 512 / 616 / 824 / 472 / 1,120 | 17,892 / 10,756 / 12,388 / 15,328 / 10,104 / 12,504 | lut |
| bounded random (k=4) | 1,232 / 688 / 1,608 / 1,296 / 624 / 1,512 | 34,252 / 14,668 / 30,196 / 24,620 / 13,648 / 19,576 | lut |

Dense random functions (n ≤ 10) are the incompressibility stress case. At n=10 they need 30,784 index bits against 10,352 bits for the literal table, and the cover search is budget-limited in all 20 dense worlds (`exact_cover=false`). **The index code is the shortest code only for canalizing networks. It loses badly on parity and is never best on random lookup tables**, as the contract anticipated: it is legitimate for the index representation to lose.

---

## S2 — induction from incomplete evidence (primary study)

**Corpus.** n = 7 nodes. The hypothesis class H contains every network whose node functions have ≤ 3 essential inputs, enumerated completely per node (7,856 functions per node).

| population | worlds | role |
|---|---|---|
| realizable main corpus | 250 (5 families × 50) | primary |
| misspecified | 60 (two 4-input nodes each) | stress |
| shift | 60 (composed gates with negations) | stress |
| noise stress | 50 | separate MDL experiment |
| NULL (rules drawn uniformly from H) | 250 | post-hoc control, D21 |

Total: 670 independent worlds. Each world contributes four evidence regimes × six nested budgets × 24 hidden queries; these are nested within the world and never counted as independent evidence. 0 runner failures. Compute: 3.9 s median per world, 0.73 GB peak RSS.

**Integrity checks.**
- Version-space verdicts agree with explicit enumeration and with brute force over whole networks (tests). SAT witnesses are replayed against every observation.
- In realizable worlds the consensus never certified a wrong answer: **0 wrong certifications at every budget**, in both the main corpus and the null population. This is a necessary invariant, not a finding.
- No isomorphic duplicates among the 420 main/stress worlds (exact canonicalization over 7! relabellings): `dedup_audit.json`.
- 77 generated rules were degenerate (fewer essential inputs than drawn); they were kept and logged. 60 query-key collisions were redrawn under the declared disjointness rule.

**Every world rendered.** `reports/development/s2_per_world_deltas.png` shows each world's paired difference by family, plus the null worlds. The per-world differences are wide and overlapping, quantized in steps of 1/16, and positive in 58–90% of worlds depending on family. A mean hides that spread.

**Primary contrast (pre-specified, D9).** Realizable worlds, uniform designs, budget 16, 16 hidden intervention queries:
- accuracy of the minimum-index-code compatible model: **0.887**;
- expected accuracy of a uniformly chosen compatible model: **0.823**;
- **Δ = +0.064, 95% CI [0.053, 0.075]**, 250 worlds. The complete-case interval is identical because no realizable version space was empty.
- Per family: conjunctive +0.076, canalizing +0.081, parity +0.018, random lookup +0.035, modular +0.109.

**Accuracy by budget** (realizable, uniform designs, intervention queries; equal-weight family means):

| budget | index | circuit | bdd | dnf | majority of V(D) (post-hoc) | uniform | observed-majority baseline | consensus coverage | consensus wrong-certified |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 0.615 | 0.610 | 0.615 | 0.615 | — | 0.532 | 0.601 | 0.007 | 0 |
| 4 | 0.631 | 0.626 | 0.630 | 0.631 | 0.669 | 0.562 | 0.639 | 0.014 | 0 |
| 8 | 0.698 | 0.731 | 0.707 | 0.698 | 0.739 | 0.635 | 0.651 | 0.059 | 0 |
| 16 | 0.887 | 0.915 | 0.902 | 0.887 | 0.880 | 0.823 | 0.660 | 0.457 | 0 |
| 32 | 0.994 | 0.996 | 0.994 | 0.994 | 0.982 | 0.981 | 0.676 | 0.960 | 0 |
| 64 | 1.000 | 1.000 | 1.000 | 1.000 | — | 1.000 | 0.677 | 1.000 | 0 |

The hidden truth prevalence of these queries is 0.507, and the plot is `s2_accuracy_vs_budget.png`. The index and dnf columns are identical because both select from the same cover.

**Negative and null findings (all development; post-hoc where marked).**
1. **The index code is not the best selector.** Index − circuit at budget 16 = −0.029 [−0.038, −0.020].
2. **At budgets ≤ 4, minimum-index-code selection is no better than a trivial baseline** that predicts the most frequently observed value of the target node: index − baseline = −0.008 [−0.028, 0.012] at budget 4.
3. **The uniform-compatible baseline is weak by construction (post-hoc G4 check, D21).** A deterministic selector can beat it with no simplicity involved.
   - Under the NULL population, where every rule is drawn uniformly from H, index − uniform is still **+0.018 [0.009, 0.027]** at budget 16.
   - The Bayes predictor under a uniform prior (majority answer of V(D)) beats uniform by +0.057 [0.050, 0.065] in the main corpus.
   - **Against that richer control, index is indistinguishable at budget 16 (+0.007 [−0.007, 0.020]), worse at budget 8 (−0.040 [−0.055, −0.026]), and slightly better at budget 32 (+0.012 [0.007, 0.017]).**
4. **Circuit simplicity looks like language/generator alignment.** Circuit − majority-of-V(D) = +0.036 [0.023, 0.048] in the main corpus and −0.033 [−0.045, −0.021] under the null. The rendered worlds show the main-corpus gain concentrated in the parity and modular families, whose generators use XOR — a primitive of the circuit code and not of the index code.
5. **Shift population:** index − uniform = +0.012 [−0.006, 0.030] (60 worlds). Inconclusive.
6. **Misspecified population:** V(D) is empty in 8% of worlds at budget 8, 92% at budget 16 and 100% from budget 32. Exact inference then *reports* inconsistency rather than answering. Before collapse, the consensus certified answers that were wrong about the hidden world: 0.73% of queries at budget 8 and 0.31% at budget 16, against 0 in realizable worlds.
7. **Noise stress** (separate MDL experiment, 50 worlds, flip rates 0.01/0.05/0.10). Exact matching collapses: V(D) is empty in 52%/94%/98% of worlds at budget 16 and in 100% at budget 64. The explicit two-part code (index model + residual positions) keeps accuracy at 0.79/0.76/0.72 at budget 16 and 0.998/0.991/0.983 at budget 64.

**Secondary contrasts (budget 16, index − uniform unless stated).**

| comparison | estimate [95% CI] |
|---|---|
| state-holdout queries | +0.050 [0.038, 0.062] |
| observational trajectories | +0.075 [0.065, 0.086] |
| clamp trajectories | +0.076 [0.065, 0.087] |
| active designs | +0.002 [0.000, 0.004] (both near ceiling) |
| active − random designs, index accuracy | +0.107 [0.095, 0.120] |
| active − random designs, consensus coverage | +0.525 [0.504, 0.548] |
| active − random designs at budget 4, index accuracy | −0.028 [−0.049, −0.007] |

**True-model rank audit (budget 16).** The generating rule has the minimum index length among its compatible candidates for 60% (random lookup) to 79% (canalizing) of nodes. On average, 3–18% of compatible candidates are strictly shorter than the truth: `s2_summary.json["true_rank_audit_B16"]`.

**Interpretation for review.**
- The pre-specified primary is positive in development. Development data cannot support the stronger reading that index-code *simplicity* drives it.
- Most of the gain over uniform selection is reproduced by the majority answer of V(D), and part of it appears even when the world contains no simplicity.
- What the data do show: decodable description lengths are informative when the description language matches the generating mechanisms (circuit/XOR on parity and modular worlds). They are neutral or harmful otherwise.
- D21 proposes co-registering the richer controls and the null population before the confirmatory freeze.

---

## S3 — LLM reasoning pilot (secondary, exploratory, real local models)

**Design.** 80 development worlds per model; n = 4 variables, class k ≤ 2 (70 functions per node); 3, 5 or 8 uniformly chosen observations per world; 4 linked point queries per world (320 items per model). The natural verdict distribution is 68 entailed / 72 refuted / 180 underdetermined; ground truth comes from the exact symbolic solver (arm E). Models:
- **qwen2.5:7b** on Ollama 0.40.15 (Q4_K_M, digest 845dbda0…);
- **gemma-3-12b-it** on LM Studio (MLX 4-bit; no digest or server version exposed — recorded as a limitation).

Temperature 0 for A/B/D/D-label, 0.7 for C's extra draws; token cap 1,500 for every arm; seeds sent but honouring not verified. Each model made 2,400 physical calls; sharing the first answer saved 1,600 logical calls. 0 runner failures; all 80 worlds completed. Mock outputs appear only in tests.

The pilot v1 runs were invalidated because arm B was truncated at a 400-token cap (D19); they are kept and excluded. The v2 qwen run was interrupted once and resumed (D22). Source: `reports/development/s3_summary.json`.

| arm | qwen accuracy / balanced | gemma accuracy / balanced | per-class recall (E / R / U), qwen · gemma |
|---|---|---|---|
| A initial | 0.478 / 0.405 | 0.588 / 0.379 | 0.59 / 0.00 / 0.63 · 0.15 / 0.00 / 0.99 |
| B self-critique | 0.456 / 0.369 (22% invalid JSON or probabilities) | 0.572 / 0.435 | 0.25 / 0.24 / 0.62 · 0.22 / 0.25 / 0.83 |
| C majority of 3 | 0.503 / 0.426 | 0.584 / 0.374 | — |
| D witness feedback (≤2 rounds) | 0.803 / 0.883 | 0.906 / 0.853 | 1.00 / 1.00 / 0.65 · 0.56 / 1.00 / 1.00 |
| D-label (privileged control) | 1.000 / 1.000 | 1.000 / 1.000 | — |
| E symbolic solver | 1.000 / 1.000 | 1.000 / 1.000 | — |
| trivial: always "underdetermined" | 0.569 / 0.333 (held-out odd worlds) | same | — |
| surface rule (budget, horizon, intervention kind) | 0.656 / 0.528 (fit on even, tested on odd worlds) | same | — |

**Contrasts** (balanced accuracy unless stated; world-clustered bootstrap, 5,000 replicates):

| contrast | qwen | gemma |
|---|---|---|
| **D − B (registered primary S3 contrast)** | **+0.514 [0.452, 0.567]** | **+0.418 [0.352, 0.482]** |
| B − A (self-critique) | −0.036 [−0.105, 0.038] | +0.056 [−0.001, 0.117] |
| C − B | +0.057 [−0.015, 0.125] | −0.061 [−0.121, −0.004] |
| D-label − B | +0.631 [0.570, 0.683] | +0.565 [0.515, 0.613] |
| transfer T_D − A, accuracy on a fresh related item | +0.013 [−0.113, 0.138] | +0.025 [−0.037, 0.100] |
| control T_A − A | +0.075 [−0.037, 0.188] | 0.000 [−0.062, 0.075] |

**Revisions relative to A** (items; correct→correct / correct→wrong / wrong→correct / wrong→wrong):

| arm | qwen | gemma |
|---|---|---|
| B | 97 / **56** / 49 / 118 | 151 / **37** / 32 / 100 |
| D | 112 / **41** / 145 / 22 | 188 / **0** / 102 / 30 |

**Probability channel.** qwen's stated verdict disagrees with the argmax of its own probability vector in 30–80% of valid answers, depending on the call. It uses the vector as P(claim true/false) despite the clarified instruction (D14), so its Brier scores (A: 1.315, worse than the 0.667 of a uniform vector) measure misuse, not calibration. gemma's vectors are coherent (mismatch ≤ 2%); its Brier scores are A 0.580, D 0.150, D-label 0.091.

**Reading (exploratory).**
1. **Floor pilot.** Both models' initial answers are at or below trivial baselines. Neither model ever identified a *refuted* claim (recall 0.00). Self-critique and majority voting do not help; B also causes many correct→wrong revisions.
2. **D's gain is witness-assisted correction that leaks the label**, as the protocol anticipated. On entailed and refuted items every compatible mechanism shown points the same way, so recall jumps to ≈1.0. On underdetermined items qwen stays at 0.65. D is not evidence of reasoning improvement, and certainly not of learning.
3. **No transfer.** Neither model shows a transfer benefit on a fresh related item.
4. **The task carries surface structure.** A three-feature rule beats both models. Before any S3 freeze, the item generator should be refined: balance verdicts within feature cells and diversify query templates. The D feedback should be made less label-revealing, for example by always showing two mechanisms (one fitting the claim and one not) when they exist, and reporting that this is impossible otherwise. A surface-rule baseline must be registered.
