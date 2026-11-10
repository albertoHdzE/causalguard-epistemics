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
