# What the evidence says about our method

Reviewer synthesis, 2026-11-10. Numbers are development results, not confirmation. Machine-readable extraction: `reports/review_r3/family_evidence.json`.

There are three separate questions: can the representation express a mechanism, is it economical to store/query, and does a prediction policy infer unseen outcomes better? Expressibility alone does not establish the other two.

Amendment 2026-11-11: the original formal-method paper contains analytic parity and threshold predicates. The weaknesses below concern the sprint's **flat schema codec**, not all of the user's analytic calculus. `docs/S4_FOUNDATIONS_AND_PRECOMMIT_CHECKING.md` makes this distinction mandatory in the next implementation.

## Existing flat index implementation

| Family | What we currently know | Practical implication |
|---|---|---|
| Sparse AND/OR-like rules | Large don't-care regions give compact families. At n=256 the repair panel uses 13,116 index bits vs 11,844 for a gate catalogue. | Useful exact representation; not best compression against a catalogue that explicitly includes those gates. |
| Canalizing rules: one input can determine the output | Index is shortest in the n=16 repair cell (660 bits). At n=256 DNF is shorter: 14,508 vs index 15,840. | Promising compactness at some sizes. My earlier unqualified 'shortest for canalizing' statement was too broad. |
| Parity/XOR | At n=256, 159,156 index bits vs 10,508 gate bits. | Flat schema unions handle parity poorly; the original analytic parity predicate and richer shared representation must be tested separately. |
| Bounded random lookup | At n=256, 34,296 index bits vs 13,636 local-table bits. | Little useful schema regularity; direct local tables can be better. |
| Existing modular generator | At n=256, 18,288 index bits vs 10,104 local-table bits. | The word 'modular' alone does not imply this encoder exploits the modules. |
| Repeated, shared, ordered hierarchical motifs | Not directly tested with the full HID representation in this sprint repository. | A justified new hypothesis, not an established family win. |

These n=256 medians use **two worlds per family**, so they illustrate mechanisms and limitations; they are not a strong estimate of every network in that family. Complete archive bits include framing, but this table is not the full decoder-amortized accounting.

For queries at n=256, index+SAT completes all 48 queries in each of the five tested family cells. Pure index-cube algebra completes respectively 28, 25, 16, 16 and 29 for sparse_conj, canalizing, parity, bounded_random and modular. This supports usability of the hybrid on these tests; it does not isolate how much of that performance comes from index representation rather than SAT. The independent exhaustive reference applies only at small sizes.

## Existing S2 prediction policy

This chooses ONE compatible model with the shortest flat index code. Difference from exact compatible-set majority at B16:

| Family | Index minus majority, percentage points | Worlds |
|---|---:|---:|
| Canalizing | +1.75 | 50 |
| Conjunctive | +0.25 | 50 |
| Modular | +0.94 | 50 |
| Parity | −2.00 | 50 |
| Random lookup | −0.50 | 50 |

These subgroup means are exploratory, not established subgroup superiority. The overall difference is +0.0875 percentage points, 95% interval [−1.1125, +1.2125]. Under the separate uniform-H null it is −2.175 points. No clear overall advantage was found for this selection policy.

## The correction to our interpretation

The full proposal is richer than the tested policy. The original HID language includes ordered composition, repetition and shared rules. A full method-coverage audit is now required. The S2 finding remains valid for what it tested; it should not be generalized to 'our entire method cannot help an AI infer unknown facts.'

Equally, storing a complete repertoire is not evidence that the method must outperform majority. Majority over compatible mechanisms can be computed within our representation. The opportunity is better supported conclusions, better experiments or lower total computational cost. `docs/RESEARCH_DIRECTION_S4.md` specifies a direct test of those opportunities.
