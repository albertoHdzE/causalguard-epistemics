# Development report — iteration 2 (2026-11-10, pre-sprint)

**Everything here is DEVELOPMENT evidence** (salts `dev-v2*`). It was produced after Codex review R1 and is used to
repair the implementation, test the revised design and re-size a future confirmatory proposal. No confirmatory data
exists. Iteration-1 results (`reports/DEVELOPMENT_REPORT.md`, release `v0.1.0-dev`) are preserved unchanged and
reproduce byte-for-byte from the tag (`scripts/reproduce_v1.sh`).

Sources: `reports/development_r2/s2_v2_summary.json`, `s2_v2_per_world.csv`, `s2_v1_exact_rescoring.json`,
`s1_v2_summary.json`, `s3_v2_summary.json`; raw runs in the `v0.2.0-dev` release asset, checksummed in
`artifacts/manifest_r2.json`. Intervals: 95% percentile, world-clustered (stratified for S2) bootstrap; 5,000
replicates for the primary, 2,000 for others.

## S2 — induction from incomplete evidence (design s2-design-v2)

**What changed (semantics, not only code).**
1. *Exogenous design.* Holdouts, uniform measurement inputs, trajectory start/clamp specifications and all queries
   come from a design RNG stream fixed before the mechanism is evaluated. Swapping the hidden network under the
   same design seed leaves every specification identical (`tests/test_s2_v2.py::test_review_mechanism_swap…`).
   No query is redrawn against observations; novelty is classified.
2. *Exact comparator.* The compatible-set posterior is computed by exact integer counts over intermediate states
   (h ≤ 3). Majority decisions, ties and random-compatible accuracy are exact. Checked elementwise against
   brute-force enumeration (1,160 random small-space queries, n=3–4, h=0–3, compound predicates: 0 mismatching
   (num, den) pairs) and, in the run itself, against complete SAT verdicts at B16 (14,880 queries, 0 mismatches).
3. *Revised primary* `S2-primary-v2` (machine-readable, `configs/endpoints/S2-primary-v2.json`): index-code
   selection minus compatible-set majority (ties half credit), B16, uniform designs, 16 intervention queries,
   five structured families equally weighted. The analysis refuses any other spec.

**Runs.** `S2-dev-v2`: 670 planned worlds, 670 ok, 0 failed, 0 missing (250 structured = 50 × 5 families; 250 IID
uniform-H null; 60 misspecified; 60 shift; 50 noise-stress). The run lacks an `end` ledger event because of a
runner accounting defect, disclosed in D27; every attempt is complete and plan-reconciled. `S2-dev-v2-mcdiag`: the
predeclared balanced subset (first 20 worlds per structured family, first 100 null worlds), 200 ok.

**The objects.** `s2_v2_per_world_deltas.png` shows every world. Structured index − majority deltas are spread
symmetrically around zero: 99 worlds positive, 98 negative, 53 exactly zero; range −0.31 to +0.28 per world. Null
deltas are skewed negative: 122 negative, 69 positive, 59 zero.

| Development contrast (B16, uniform designs, 16 intervention queries) | Estimate | 95% interval | Worlds |
|---|---:|---:|---:|
| **Revised primary: index − compatible-set majority (structured)** | **+0.0009** | [−0.0111, +0.0121] | 250 |
| Historical v1 primary: index − random compatible (structured) | +0.0627 | [+0.0518, +0.0730] | 250 |
| Majority − random compatible (structured) | +0.0618 | [+0.0554, +0.0681] | 250 |
| Circuit − majority (structured) | +0.0251 | [+0.0133, +0.0364] | 250 |
| Index − circuit (structured) | −0.0243 | [−0.0343, −0.0147] | 250 |
| **Null (uniform-H): index − majority** | **−0.0217** | [−0.0325, −0.0111] | 250 |
| Null: index − random compatible | +0.0133 | [+0.0035, +0.0235] | 250 |
| Null: circuit − majority | −0.0217 | [−0.0328, −0.0101] | 250 |
| Structured − null difference in index − majority (EXPLORATORY) | +0.0226 | [+0.0077, +0.0381] | 250 + 250 |

Per-family circuit − majority: parity +0.104, modular +0.052, canalizing +0.005, conjunctive −0.006,
random_lookup −0.029. The pooled +0.025 is driven by the XOR-generated families. It is a property of the circuit
code's alignment with those generators, not an index-method success. Per-family index − majority: canalizing
+0.018, modular +0.009, conjunctive +0.003, random_lookup −0.005, parity −0.020.

**Reading against the mechanism.** Under the uniform-H prior with an exogenous design, the compatible-set majority
is the Bayes predictor, so any deterministic selector must lose to it on average. The null result (−0.022) is what
that theorem predicts. An exhaustive small-class check passes: all 512 networks at n=3, k=1, three budgets, exact
fractions, majority ≥ index and ≥ random compatible on average, with index beating majority on some individual
worlds (`tests/test_s2_v2.py`). The null's location for index − random compatible (+0.013) shows again that the
historical comparator rewards deterministic selection without any simplicity in the world.

In structured worlds the index code shows **no clear advantage over the majority** (interval ±0.011 around
+0.001). The structured-minus-null difference (+0.023, exploratory) says the index selector loses less to the
majority when the world is generated simply. That is a weaker statement than "index beats majority", and it is
not a confirmatory claim.

**Subsets (exploratory; queries nested in worlds).** h=1 queries: index − majority +0.0007 [−0.014, 0.015];
h>1: +0.0010 [−0.015, 0.017]. By novelty (structured, B16): 184 h=1 queries are equivalent to an observed
transition (all methods agree on those, contrast exactly 0); 1,316 h=1 queries have a novel effective input
(+0.002 [−0.016, 0.019]); 30 multistep queries interpolate observed transitions (contrast 0); 2,470 involve an
unobserved transition (+0.001 [−0.015, 0.018]). Almost the whole primary concerns unobserved transitions, so it is
an induction question, not interpolation.

**Budget and regime (exploratory, index − majority, structured).** B4 −0.029 [−0.045, −0.015]; B8 −0.033
[−0.046, −0.019]; B16 +0.001; B32 +0.011 [+0.007, +0.015]. Observational regime B16 −0.020 [−0.030, −0.010];
clamp regime −0.008 [−0.018, +0.003]; active designs −0.0005 [−0.003, +0.002]; state-holdout queries −0.001
[−0.014, +0.011].

**Exact ties.** 191 of 4,000 primary queries (4.8%) and 304 of 4,000 null queries are exact majority ties. They
score half credit by the declared rule.

**Monte Carlo majority diagnostic (predeclared budgets 4,096 / 16,384 / 65,536; 4 independent seed streams;
100 structured + 100 null worlds; reference = exact posterior).**

| Population | M | mean abs prob. error | flips at non-ties | flips at exact ties | max world-level contrast shift |
|---|---:|---:|---:|---:|---:|
| structured | 4,096 | 0.0026 | 5 / 6,104 | 292 / 296 | 0.0050 |
| structured | 16,384 | 0.0014 | 4 / 6,104 | 294 / 296 | 0.0053 |
| structured | 65,536 | 0.0007 | 0 / 6,104 | 296 / 296 | 0.0050 |
| null | 4,096 | 0.0024 | 3 / 5,912 | 484 / 488 | 0.0056 |
| null | 16,384 | 0.0012 | 0 / 5,912 | 484 / 488 | 0.0041 |
| null | 65,536 | 0.0006 | 0 / 5,912 | 487 / 488 | 0.0044 |

(Denominators are query × repetition counts: 1,600 queries × 4 repetitions per population, split by exact-tie
status.) Away from exact ties a finite-sample MC majority almost never changes a decision. At an exact tie it
essentially always picks a side, and no fixed sample budget can recover half credit. That is why every budget
leaves a world-level contrast shift of 0.004–0.006, above the 0.002 target. **Declared policy: the exact
integer-count posterior; MC is not used for any S2 estimate.**

**The historical v1 estimate re-scored exactly** (v1 design and records, B16, 250 structured worlds; 0 truth
mismatches against the stored records over 4,000 queries). Index − majority was +0.0065 [−0.0068, +0.0198] with
v1's MC majority (tie→0). The exact majority gives +0.0055 [−0.0075, +0.0183] with the same tie rule and +0.0024
[−0.0098, +0.0146] with half-credit ties. 14 of 4,000 majority decisions changed; 215 queries are exact ties. The
v1 design's mechanism dependence (R02) is not repaired by this re-scoring.

**Stress populations (descriptive).** Misspecified worlds give an empty exact version space in 98% of worlds at
B16, so exact selectors have no output there (missing = 0). Shift: index − majority −0.041 [−0.059, −0.022].
Noise: exact methods collapse as soon as one flipped bit makes V(D) empty. Two-part MDL is computed for **every**
selection code under the identical residual code and budget; at rate 0.05, B32 the accuracies are circuit 0.948,
index 0.910, bdd 0.911, dnf 0.874. The noise-handling benefit belongs to the two-part residual model, not
uniquely to the index code.

**Changed conclusions relative to iteration 1.** (a) The headline "index beats uniform-compatible" (+0.063) is
retained only as a historical secondary; under the revised primary there is no clear index advantage. (b) The MC
approximation of v1 did not create the small v1 index − majority estimate. The tie convention mattered about as
much as the sampling did. (c) The design is now exogenous, so the null comparison has a valid Bayes
interpretation.

## S1 — repair verification panel (engineering / formal correctness)

**Run.** `S1-dev-v2-panel` (salt `dev-v2-s1`, snapshot `dd63670a`): 2 new worlds in each of the 49 originally
studied family/size cells (98 worlds), all 7 backends, original caps (20 s per query, 1,200 s per item), runner v2
supervisor. 686 planned items, 686 ok, 0 failed, 0 missing; 1,028 s wall on 8 workers. It ran with no S2/S3 job
active (the LLM servers were idle with models loaded; the gemma diagnostic was interrupted for it and later
resumed).

**Correctness (counts of elementwise comparisons; not a universal proof).** Every truth-valued answer was compared
with the exhaustive direct-rule reference for n ≤ 10: 1,152 query comparisons each for literal, index_enum,
index_sat and bdd_ref, and 1,147 for index_cube (48 worlds × 24 queries). 0 mismatches. Across all backends and
sizes, 0 cross-backend disagreements and 0 witness-replay failures. Of 329 large-n UNSAT-type answers, 296 were
confirmed by at least one other exact backend; for 33 no independent exact backend completed. Index_sat
certificate levels: 696 checked RUP proofs, 1 solver-only UNSAT, 1,655 replayed witnesses. Codec round trips: 0
failures. Exact index covers: 94 of 98 worlds (4 are upper bounds under the declared search budget).

**Scaling (completed queries, caps kept in the denominators).** index_sat completed 240/240 queries at each of
n = 64, 128 and 256 (median 0.020 s, p90 0.116 s, max 2.3 s at n = 256). At n = 256, index_cube completed 114/240
(5 timeouts, 121 `unknown_resource`) and bdd_ref 144/240 (23 timeouts, 73 `unknown_resource`). The SAT hybrid's
advantage belongs to the hybrid (index families → CNF → SAT), not to pure index cube algebra.

**Interrupt cleanup and caps** are validated by the runner tests (`tests/test_runner_v2.py`): a nested per-query
SIGALRM no longer cancels the item deadline; a hung worker that ignores SIGTERM/SIGALRM, together with its
child process, is killed and reaped; crashes are recorded. In the panel no item reached the 1,200 s item cap.
Per-query caps produced the timeouts above.

**Decoder accounting (repaired).** The decoder charge is now the complete local dependency bundle (codec.py +
index_repr.py + schema.py; 64,841 source bytes; 18,339 bytes gzip-9; sha256 `0128a124…`). It runs under CPython
3.12 with the standard library only: `tests/test_codec_bundle.py` decodes all 7 codecs in an `-I -S`
interpreter. The v1 charge measured codec.py alone (8,340 bytes gzip-9). Amortized totals now report
`archive_sum_bits` (complete archives) and `payload_sum_bits` separately, and add only the archive sum to the
decoder charge. These are encoder-specific code lengths, not an approximation ordering of Kolmogorov complexity.

**Replayability.** Proof traces and witness states are not stored in the records; the stored certificate level is
the recorded outcome of the in-run checker. To replay a certificate independently, re-run the item: it is a
deterministic function of its plan payload (`plan.json`). Iteration-1 statements that zero mismatches bound an
independent per-query error rate (3/M) are withdrawn.

Iteration-1 S1 findings (`S1-dev-v1` + rerun: 28,765 reference comparisons without disagreement, 2,569 checked
proofs + 4 uncertified UNSAT) are preserved and reproduce byte-for-byte from the tag.

## S3 — LM feedback-arm panel (task s3-tasks-v2; development only)

**Runs.** All local models, so no paid calls.
- `s3v2-diag-qwen25_7b-dev`: 20/20 worlds ok.
- `s3v2-diag-gemma3_12b-dev`: 20/20 ok, resumed once (D32).
- `s3v2-heldout-qwen25_7b-dev`: 100/100 ok, 0 failed, 5,500 physical calls, 10,222 s wall, 2 concurrent requests (D30).

Gate D29 passed for qwen and failed G3 for gemma: gemma's arm-A balanced accuracy was 0.319, below chance. So
there is no gemma held-out panel (D33), and gemma is reported as a 20-world floor diagnostic only. Salts:
diagnostic `dev-v2-s3-diag`, held-out `dev-v2-s3-panel`. Both are disjoint from the baseline training salt
`dev-v2-s3-train`, and the analysis refuses overlap. Source: `reports/development_r2/s3_v2_summary.json`.

**Per-world render (G1).** `s3_v2_per_world_<run>.png` has one row per world: balanced items correct (0–3) per item
arm, target correctness (0/1) per probe, and the surface-rule baseline on the same saved items. In the held-out
panel:
- D_cert is an almost uniform 3/3 column.
- D_label is an almost uniform 2/3 column, explained below.
- Target correctness forms horizontal bands across all six target probes, so it is driven mainly by the world (its
  target item), not by the arm. This is why the target contrasts have wide intervals relative to their small
  discordant counts.

### Held-out panel, qwen2.5:7b (100 worlds; 300 balanced, 100 natural, 100 target items)

| arm | balanced acc (balanced items) | valid | Brier (valid only) | natural-item balanced acc |
|---|---|---|---|---|
| A (initial) | 0.433 | 1.000 | 1.060 | 0.395 |
| B2 (2 self-critique turns) | 0.391 | 0.913 | 0.985 | 0.412 |
| C (independent resample) | 0.440 | 0.990 | 1.022 | 0.407 |
| D_sample (K=2 public compatible samples + critique) | 0.465 | 1.000 | 0.763 | 0.487 |
| D_label (reference label + critique) | 0.570 | 1.000 | 0.697 | 0.526 |
| D_cert (label + certificate + critique; **privileged**) | 0.970 | 0.997 | 0.356 | 0.965 |
| E (reference solver) | 1.000 | 1.000 | 0.000 | 1.000 |
| majority baseline (train-fit) | 0.333 | — | — | 0.333 |
| surface rule (train-fit; budget/horizon/kind/target value) | 0.374 | — | — | 0.507 |

On balanced items, arm A is above the fitted surface rule by 0.06 balanced accuracy. On natural items it is below
it (0.395 vs 0.507). The 20-world diagnostic had the surface rule above A on balanced items as well (0.511 vs
0.429); its balanced set is small (60 items). **A's confusion matrix on balanced items:**
- entailed: 65 correct, 31 → underdetermined, 2 → refuted.
- refuted: 1 correct of 108; 58 → entailed, 49 → underdetermined.
- underdetermined: 59 correct, 34 → entailed, 1 → refuted.

So, without feedback, the model almost never answers "refuted". It is not discriminating refuted from entailed
claims.

**Round-level paths (post hoc; `round_paths_balanced` in the summary).** Every D arm and B2 has two matched turns
after A: (feedback, then self-critique), or (critique, critique) for B2.
- **D_label:** after the label turn the model adopts the stated label on **300/300** balanced items. The second,
  self-critique turn then reverses **98/98** entailed items to "underdetermined". It also reverses 28/108 refuted
  items (27 to underdetermined, 1 to entailed) and 3/94 underdetermined items. The reversed answers usually carry
  probabilities {entailed 0.5, refuted 0.5}, which conflict with the stated verdict.
- **D_label's final accuracy of 0.57 therefore measures a reversal under critique, not a failure to read the
  label.**
- **D_cert:** 300/300 after the certificate turn, and 291/300 still correct after the critique turn.
- **gemma:** the reversal does not occur; entailed is kept on 17/17 items, and D_label round 2 is correct on 56/60.
  The reversal is specific to qwen.

This was found after the runs and is reported as a development observation. It was not a planned contrast.

**Probability coherence (construct validity of Brier).** The parser flags `verdict_prob_mismatch` when the stated
verdict is not the arg-max of the stated probabilities. For qwen, 2,342 of 5,188 parsed answers in the held-out
panel are mismatched; for gemma, 8 of 1,098 in the diagnostic. By arm on final balanced answers (qwen held-out):

| arm | A | B2 | C | D_cert | D_label | D_sample |
|---|---|---|---|---|---|---|
| mismatched | 139/300 | 67/300 | 0/300 | 68/300 | 200/300 | 166/300 |

The dominant pattern is verdict "underdetermined" with probabilities split between entailed and refuted. So qwen's
probabilities do not express its verdicts, and **Brier scores are not interpreted as calibration** here. Accuracy
uses the verdict field throughout, the same rule as in iteration 1.

**Transfer and focus contrast (paired, world-clustered bootstrap, 5,000 replicates).** Target accuracy by probe:

| probe | accuracy | valid |
|---|---|---|
| A_T (no source context) | 0.39 | 1.00 |
| T_A | 0.41 | 1.00 |
| T_B2 | 0.37 | 0.96 |
| T_sample | 0.36 | 1.00 |
| T_label | 0.41 | 0.99 |
| T_cert | 0.33 | 0.97 |

Baselines on the same target items: majority 0.29 (accuracy), surface rule 0.47.

- **Focus T_cert − T_label = −0.08, 95% CI [−0.16, 0.00]; n = 100 worlds.**
  - 2×2 table: both correct 29, both wrong 55, T_cert only 4, T_label only 12.
  - Within this development scope no clear certificate-over-label transfer is detected. The point estimate is
    negative and the interval reaches zero. This is not evidence of no effect.
  - The diagnostic panels gave −0.15 [−0.35, 0.05] (qwen) and −0.15 [−0.30, 0.00] (gemma).
- **T_cert − A_T = −0.06 [−0.18, 0.06]; T_A − A_T = +0.02 [−0.09, 0.13].** Seeing solved source items, with or
  without feedback, gives no clear improvement over answering the target cold.
- **Median source-context size:**

  | probe | T_A | T_label | T_sample | T_cert | T_B2 |
  |---|---|---|---|---|---|
  | chars | 1,859 | 2,725 | 3,561 | 4,088 | 5,298 |

  The probes are matched in turns, not in context length.

**Secondary item contrasts (balanced items, accuracy).**

| contrast | estimate | 95% CI |
|---|---|---|
| D_cert − D_label | +0.400 | [0.357, 0.443] |
| D_cert − B2 | +0.587 | [0.530, 0.643] |
| D_label − B2 | +0.187 | [0.137, 0.240] |
| D_sample − B2 | +0.087 | [0.023, 0.150] |
| B2 − A | −0.033 | [−0.100, 0.033] |
| C − A | +0.007 | [−0.020, 0.030] |

D_cert is privileged, since it states the label and a replayed certificate, so its accuracy is an upper reference.
It is not an inference result.

D_sample reveals no label: its two samples come from public evidence only. It gives a small gain over self-critique
alone. Because K=2 samples cannot certify agreement, this gain could come from copying the samples' shared answer.
The data here cannot separate the two explanations.

**Coherence under transformations (arm A only; nested under worlds, not independent).**
- Complement consistency given both answers valid: 0.42 over 300 pairs. gemma: 0.97 over 60.
- Same verdict under variable renaming: 0.78 over 200 pairs. gemma: 0.93 over 40.
- So qwen's arm-A answers change under a semantics-preserving renaming in about a fifth of pairs, and are
  complement-consistent less than half the time.

**Parse and truncation.**
- Held-out qwen: 90 invalid-JSON and 222 invalid-probability parses out of 5,500 calls. Length truncations: 3, all
  in the `D_cert` critique turn (`i2/DC2`, worlds 64, 82 and 97; 1,500 completion tokens each). Each counts as
  invalid in that arm.
- Diagnostics: 0 truncations; D29 G1 (0 failures, 0 truncations) was applied to the diagnostics, as declared.
- Balance shortfalls (target verdict unavailable for a cell within the try limit; the item is kept and its realized
  verdict recorded): 38 items over 100 worlds, listed in the summary by cell.

**Cost.**
- Held-out qwen, logical standalone tokens: 7.01 M prompt + 1.17 M completion. Physical latency sum: 20,416 s at 2
  concurrent requests.
- Diagnostics: qwen 1.40 M + 0.23 M; gemma 1.44 M + 0.31 M.
- Per-arm costs are in `cost.logical_standalone_by_arm`. B2 is the most expensive item arm (447,825 completion
  tokens) because critique turns produce long reviews.

**gemma-3-12b-it floor diagnostic (20 worlds).**

| arm | A | B2 | D_sample | D_cert | D_label |
|---|---|---|---|---|---|
| balanced acc | 0.319 | 0.394 | 0.373 | 0.790 | 0.933 |

- gemma's D_label score exceeds its D_cert score: certificate text lowers its accuracy relative to the bare label,
  −0.117 [−0.217, −0.017].
- Focus: −0.15 [−0.30, 0.00]. Its arm A is at the chance floor, so it is not suitable for transfer measurement
  under this task.

**What S3 does and does not show (development).**
1. Without feedback, qwen2.5:7b is above chance on balanced items (0.433). That is barely above a train-fit surface
   rule, below it on natural items, and the model almost never recognises refuted claims.
2. Revealed labels are adopted at once. In qwen, a generic self-critique turn then undoes entailed labels, while a
   certificate keeps them.
3. No clear transfer of certificate feedback to a fresh target item is detected. The interval is
   [−0.16, 0.00] for the planned focus contrast.
4. Coherence diagnostics (complement 0.42, renaming 0.78) and verdict/probability mismatch (45% of parsed answers)
   limit what any S3 accuracy says about the model's epistemic state.

**S3 is not proposed for freezing.**
