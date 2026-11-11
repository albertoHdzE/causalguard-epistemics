# S4 method coverage: what is encoded, what is ours, what is generic

Iteration 4, 2026-11-11. Development document required before any S4 model call (`docs/RESEARCH_DIRECTION_S4.md`,
"Mandatory method-coverage document"). It covers items 1–7 of that section and the amendment
`docs/S4_FOUNDATIONS_AND_PRECOMMIT_CHECKING.md`. Pre-sprint work (the sprint runs 2026-11-13 to 11-15).

The framing is **algorithmic models for verifiable AI reasoning, evaluated first in finite deterministic
systems**. Boolean networks are the first test environment, not the limit of the program. Nothing below claims
universal truth detection, minimum Kolmogorov complexity, arbitrary-program inference, or superiority to Zenil
et al.

## 0. Pinned sources

| Source | Identity | Use |
|---|---|---|
| Formal method paper `CausalBool/papers/method/manuscript_formal/method_paper.tex` | sha256 `04ea352c0aff664180d68a395b09bd7311e634d1e975ab7edf3531b08b029366`, CausalBool HEAD `50b3d48cef9743ddbe7535752c61566360c15e98` | analytic index-set calculus (Sections 2–5, 7, 8) |
| HID-v1 wire format `index-deconvolution/protocols/hierarchy_v1/WIRE_FORMAT.md` | sha256 `030fcbe58f705b26b14101a6a31c1e118a780224286e4cfd278a7a604122d16b` | ordered/shared hierarchy vocabulary (CONCAT, REPEAT, references, PATCH) |
| HID README `index-deconvolution/hierarchy/README.md` | sha256 `f5656d72867bf55bb82f181f9b5754dc94bc7c923ac3a2221dd3a64c66c52314` | "archive bits are a code length in one language, not K" |
| HID dictionary protocol `index-deconvolution/PROTOCOL_hierarchy_dictionary_v1.md` | sha256 `7f48a0af4a3369eeccea803022cdd4155d8642a428bba826e267aef087ffd43a` | shared-dictionary history |
| Causal-target closure review | sha256 `6d7554d7451c518f85f2bd6b367c0fea608b53080d28b399bd43e174166c202c` | withdrawn query-recovery proposal (history) |
| Gap-ranking review | sha256 `ebe2ed171b9abe348b6cc8da4c60de863346fc620904feb3d16480876677a03f` | gap ordering not better than random (history) |

The CausalBool repository has no top-level LICENSE. **No upstream code was copied.** Every module below is an
independent implementation from the manuscript text and the published specifications. Local agent instructions
were inspected: `CausalBool/CLAUDE.md` (governance of that repository) and `luminal-challenge/AGENTS.md`
(unrelated). Nothing in the CausalBool tree was modified; the manuscript is not edited by this assignment.

## 1. Three artifacts that are not synonyms

| Artifact | What it is | Where here |
|---|---|---|
| **Analytic index-set calculus** (formal paper) | Exact one-sets of KNOWN gates over an ordered repertoire: bit bands, parity and Hamming-weight classes, deconvolution Dec(L,S), canonical reconstruction, support locality, LSB/MSB transport by phi | `src/causalguard/s4/analytic.py` (new port) |
| **Flat schema codec** (sprint S1/S2) | Per-node unions of coordinate-fixed schema families with a per-node code length; one selected model in S2 | `index_repr.py`, `codec.py` (`index`), arm C |
| **HID ordered/shared program language** | Ordered DAG over bit strings: LITERAL, CONCAT, REPEAT, AP_UNION, SCHEMA_UNION, PATCH, XFORM, explicit shared references | not implemented as HID; its ideas are ported into CGH-1 (`s4/hcode.py`), a mechanism code |

The flat codec's XOR disadvantage (S2/S1 family map) is a property of the flat codec. The analytic calculus has
exact parity and threshold predicates, now implemented and tested (`tests/test_s4_analytic.py`).

## 2. The encoded object, the evidence and V(D) (item 1)

- **Mechanism.** A network M on n nodes, synchronous update F(x) = (g_1(x_{N_1}), …, g_n(x_{N_n})). The public
  node order is the declared physical order of the system. Local tables use LSB-first local order: input
  N_i[t] is local bit t. In the paper's 1-based terms this is LSB-first ordering with index j = state + 1.
- **Class H.** All networks whose node functions each have at most k essential inputs (all functions, all
  supports, constants included). This is `HypothesisClass(n, k)`, a **complete bounded class**, not a sampled
  library. S4 pilot: n = 8, k = 3; |H_j| = 12,506 distinct functions per node.
- **Evidence D.** One-step observations (horizon 1): a start state, an intervention (none / persistent clamp),
  and observed next values of the unclamped nodes.
- **V(D) = {M in H : M reproduces every observation}.** With one-step evidence, V(D) is exactly the product
  of per-node sets V_j. That is why exact per-node reasoning is sound here. **Multi-step evidence is refused**
  (`UnsupportedClaim`): the factorization is not proved for it (item 7).
- **Claims.** Point claims: a start state, an intervention (initial_edit or persistent_clamp), a horizon
  h ∈ {1, 2, 3}, and a single-node literal target. These are novel multi-step and intervention targets over
  one-step observations, as item 7 requires.

### Complete state repertoires vs complete compatible-mechanism sets

These are different objects. The paper's repertoire is the 2^n ordered states of ONE known mechanism. S4's
uncertainty object is the set of ALL compatible mechanisms, V(D). A compact representation of the first
does not automatically compact the second. S4 represents V(D) completely, with no sampling and without the
hidden mechanism. The bound is the declared class (k ≤ 3, one-step evidence, h ≤ 3 claims); beyond it the
answer is an explicit resource or unsupported status.

## 3. Arm D's representation of V(D): support schemas (items 2, 4, 5)

For node j and support F (|F| ≤ k), the observations of node j project to **fixed addresses** of the local
repertoire {0, …, 2^|F|−1}. The rest are free addresses. This gives a schema over the local truth table, i.e.
the index-set idea applied to the space of mechanisms:

```text
g_j(F) = 2^(2^|F| − #observed local patterns)      (0 if two observations conflict on F)
```

**Multiplicity.** A function with fewer essential inputs is consistent on every superset support, so supports
overlap. Distinct mechanisms are counted once, by their unique essential support E, using Möbius inversion:

```text
e_j(E) = Σ_{F ⊆ E} (−1)^{|E∖F|} g_j(F)
|V_j|  = Σ_{|E| ≤ k} e_j(E) = Σ_{|F| ≤ k} g_j(F) μ(|F|),   μ(f) = Σ_{m=0}^{k−f} (−1)^m C(n−f, m)
```

These are counts of **distinct canonical functions**. They are not counts of (support, table) encodings or of
SAT assignments. They equal the candidate-class counts exactly (tests).

**Exact claim counts (support-local).** #{M ∈ V(D) : q(M)} is computed without enumerating V(D):

- h = 1: closed form, Π_{j≠t} |V_j| × #{f_t ∈ V_t : f_t(s0) = c}.
- h = 2: the target's step-2 value depends on s1 only through its essential support E. For each E, enumerate
  the at most 2^{|E ∪ {t}|} ≤ 2^{k+1} local assignments. Every other node contributes a closed-form factor.
  This is the formal paper's support locality (Proposition "Support Locality"), transported from states of a
  known mechanism to the unknown-mechanism setting. Cost is polynomial in n for fixed k.
- h = 3: the intermediate state s1 is **enumerated** over its possible values. This is a metered fallback,
  capped at 2^14 states by default; above the cap the result is `ResourceLimit`, never a sampled answer.

**Witnesses** are constructed support-locally: an explicit network for each side of the claim. Every witness
is **independently replayed** by the reference simulator against all evidence and the claim before it is
returned (`workspace.check`).

**Exact vs estimate.** Every S4 count is an exact integer. Monte Carlo is not used. Universal claims are never
certified from samples or timeouts: a timeout or cap returns `unsupported_or_resource`.

### Worked example (hand-checkable; reproduced by code)

n = 2 nodes (x0, x1), k = 1. Each node is a constant, a copy or a negation of one node: 6 functions per node.
Evidence: one observation from state (x0, x1) = (0, 0) with x0' = 1 observed; x1 is not observed.

| Support F of node 0 | fixed local addresses | g_0(F) | e_0(F) | distinct functions |
|---|---|---:|---:|---|
| ∅ | {0 ↦ 1} | 1 | 1 | CONST1 |
| {x0} | {0 ↦ 1} | 2 | 2 − 1 = 1 | NOT x0 |
| {x1} | {0 ↦ 1} | 2 | 2 − 1 = 1 | NOT x1 |

μ(0) = C(2,0) − C(2,1) = −1 and μ(1) = 1, so |V_0| = 1·(−1) + 2 + 2 = 3. Node 1 is unconstrained:
|V_1| = 6, and |V(D)| = 18.

**Claim:** starting from (0, 0) with no intervention, x0 = 1 after 2 steps. Then x0'' = f0(1, f1(0,0)):

- CONST1 gives true for all 6 choices of f1;
- NOT x0 gives f0 = 1 − 1 = 0, false for all 6;
- NOT x1 gives 1 − f1(0,0), true for the 3 functions with f1(0,0) = 0.

Count: 9 / 18, so the claim is **underdetermined**. Opposing witnesses: M+ = (CONST1, CONST0) and
M− = (NOT x0, CONST0); both are replayed.

**A measurement that separates them:** observe x0' from state (1, 0). The outcome is 0 only under NOT x0, so
the claim becomes *refuted* (count 0/6). Outcome 1 leaves {CONST1, NOT x1} and count 9/12 (still
underdetermined). P(outcome 0) = 6/18. EIG = 1 − (12/18)·H(0.75) = **0.459 bits**. The alternative "observe
x1' from (0, 0)" has EIG 0.082 bits.

The code reproduces all of these numbers: `MechanismSpace` counts [3, 6], claim 9/18, outcome sets 6 and 12,
EIG 0.4591 and 0.0817. The explicit engine gives the same (9, 18).

## 4. The three backends behind one semantic API (item 2: which operations use OUR representation)

`s4/workspace.py`: `status`, `check`, `witness`, `measurement_values`, `update`. All three backends get the
same public task and the same verification capabilities, and return the same response schema.

| Operation | B generic | C flat index | D index-set (ours) |
|---|---|---|---|
| construction | complete CNF of H restricted by D (existing `versionspace._Enc`, with the linear sequential-counter at-most-one encoding added in iteration 4; the historical pairwise default is unchanged for S2); explicit candidate class when n ≤ 10 | materialized candidate class (2^n-column tables), n ≤ 10 | per-node support schemas, no materialization |
| verdict | SAT: UNSAT of either side (RUP proof check available) | exact explicit counts | exact support-local counts |
| counts | explicit enumeration grid (n ≤ 10), else resource refusal | explicit enumeration grid | Möbius + support-local (h ≤ 2 polynomial; h = 3 metered fallback) |
| witnesses | SAT models, replayed | constrained explicit search, shortest flat code first, replayed | support-local construction, replayed |
| rendering | explicit truth tables | flat schema families | named analytic rules (formal-paper families) + CGH-1 description |
| EIG of a measurement | exact, by its own counts | exact, by its own counts | exact, by its own counts |

**The operations that use OUR representation are D's construction, counting, witness construction and
rendering.** The SAT solver is used by B and by the **common** commit-gate cross-check. The cross-check is the
same for every arm, so it is not a hidden engine behind D. Since all backends are exact over the same H, their
logical answers **must coincide** wherever they finish; they agree in every test and in the offline replay.
Any difference between arms is therefore one of cost, feasibility, or how the workspace is presented to the AI.
A difference in logical truth would be a bug.

## 5. Capability map (item 2)

| User-proposed capability | Original source | Before iteration 4 | Iteration 4 | Boundary |
|---|---|---|---|---|
| Ordered exhaustive repertoire, LSB/MSB, phi transport | paper Defs 1–2, Thm "Ordering invariance" | implicit LSB only | `analytic.coord/phi`, transport tested for every gate | — |
| Bit bands, parity, weight classes | paper Defs 3–4 | flat schemas only | `analytic.band/parity_class/weight_class` | — |
| Gate one-sets incl. XOR/XNOR, KOFN, EXACT-k, IMPLIES, canalizing | paper Prop "Gate-family one-sets" | gate codec subset (no EXACT-k, no canalizing; MAJORITY odd only) | `analytic.one_set`, `gate_value`; cross-checked vs codec tables | — |
| Strict majority | paper §3 (contains a ceil/tie inconsistency) | MAJORITY odd d only | `MAJORITY_STRICT` = weight ≥ floor(d/2)+1; `KOFN(ceil(d/2))` kept distinct; tie difference tested at d = 4 (6 tie states) | the manuscript is not edited here |
| Dec(L, S), offset families | paper Def "Deconvolution" | — | `analytic.dec/offset_family`, Prop "Overlap factorisation" tested | — |
| Canonical exact reconstruction | paper Thm | — | `analytic_predictor` vs reference simulator | — |
| Support-local query of a KNOWN mechanism | paper Prop "Support locality", Cor "Shared-input reduction" | — | `support_local_query` reports c, d, mu, 2^c enumerated, 2^mu, 2^(n−c) separately | refuses c > 22 |
| Support locality for UNKNOWN mechanisms (over V(D)) | new (transport of the paper's idea) | — | `mechspace.claim_counts` h ≤ 2 | h = 3 is a capped enumeration |
| Ordered repetition (REPEAT), shared references, PATCH | HID-v1 W3 | — | CGH-1 TEMPLATE (ordered cyclic offsets), MODULE (block repetition), DICT (shared rule definitions), PATCH exceptions | a versioned mechanism code, not a HID archive |
| CONCAT/AP_UNION/XFORM over bit strings | HID-v1 | — | not ported (they describe strings, not mechanisms) | unsupported here |
| Reasoning over possibilities (complete V(D)) | user proposal | S2: one selected model | `MechanismSpace` + B/C equivalents; verdicts, counts, witnesses, EIG | one-step evidence, k ≤ 3, h ≤ 3 |
| Codec-induced model averaging | amendment | — | `s4/prior.py` (offline secondary) | DICT mode excluded from the prior (Section 7) |
| Check before release | amendment | S3 certificates (no gate) | `s4/checking.py` | finite, structured claims only |

## 6. Construction from public data only (item 3)

The workspace input is `tasks.public_task(...)`, a serialized JSON payload. It contains n, k, opaque node
labels in physical order, the evidence, its hash, and the claims. There are no rules, tables, family labels,
seeds or answers; `audit_public_payload` checks this recursively and a test runs it for every family.
`evaluator.Evaluator` is the only holder of the hidden mechanism. It is consulted after every episode of a
world has finished, and its reference block is written last in each pilot record.

Truth is never used for ordering, dictionaries or templates. CGH-1 descriptions of the hidden mechanism are
computed only in the evaluator-side family map and are never shown to an agent.

## 7. Description length, complexity, probability, proof: four different objects (amendment)

1. **Upper bounds on program complexity.** A complete CGH-1 archive p decodes, under the fixed decoder
   (`hcode.decode`), to exactly one mechanism. With the decoder and this specification as the fixed auxiliary
   information, K_U(M) ≤ |p| + c_decoder. Every field is serialized and counted: header, variant, n, k, ordering
   bit, mode, rule ids, supports, offsets, references and patches. `encode` asserts that its field ledger equals
   the transmitted length. Two upper bounds do **not** order the true complexities. The search is bounded and
   deterministic, so it gives a canonical description, not a minimum. The paper's fractional analytic
   descriptor D_formula is **not** a complete code length and is not used numerically here.
   - Golden length, derived by hand in `tests/test_s4_hcode.py`: the ring node_i = XOR(x_i, x_{i+1}), n = 4,
     k = 2, costs 25 bits (header 15, rule 6, offsets 3, empty patch list 1). The same network costs 51 bits
     in FLAT mode.
2. **Codec-induced probabilities** (offline secondary only):
   `w_L(M | D) = 2^−L(M) / Σ_{M′ ∈ V(D)} 2^−L(M′)`. L is a fixed prefix code with **one canonical description
   per distinct mechanism**. This is a testable preference over models within the declared finite class. It is
   not a measured universal algorithmic probability m_U, and not a frequency. An empty V(D) is a diagnostic,
   not a posterior. The prior language `cgh_prior` = FLAT ∪ TEMPLATE ∪ MODULE (no patches). The shared-DICT
   mode is excluded from the prior because it couples every node and makes the exact sum infeasible; it stays
   in the description-length map. Nodewise-additive codes are summed exactly with weighted integer counts
   (`versionspace.exact_query_counts(weights=…)`, exact 26-bit-limb arithmetic, tested against brute force with
   weights up to 2^70). Template and module models in V(D) are enumerated exactly (cap 50,000, else refusal).
3. **Formal proof / verification.** A verified definite claim has (a) an exact count of 0 for the opposite
   side, (b) agreement of the complete SAT encoding (UNSAT, RUP-checkable), and (c) one replayed witness of the
   asserted side. No numerical prior is used. Small weights never remove positive-weight alternatives from
   logical verification.
4. **Forecast, underdetermination, resource refusal.**
   - A forecast is a predicted value on an underdetermined claim. It never receives a verification badge.
   - Underdetermination is two replayed opposing witnesses.
   - A resource refusal is "did not finish" and is neither of the above.

## 8. Enumeration and cost accounting (item 6)

Metered separately (`mechspace.Meter`, workspace `cost`):

- schema evaluations (`g_evals`);
- support terms;
- **enumerated intermediate states** (the h = 3 fallback);
- witness constructions;
- per-backend build time (cold start) vs per-claim time;
- SAT variables and clauses;
- materialization refusals.

Explicit materialization by B and C (2^n-column candidate tables) is refused above n = 10 by declaration.
The CGH-1 encoder search is deterministic and bounded:

- FLAT;
- one DICT;
- every distinct node signature as a TEMPLATE;
- every divisor m as a MODULE.

Cold-start costs (build) and per-claim costs are reported separately in the offline map and stress runs.

## 9. Supported initial sizes (offline computational evidence, not treatment effect)

Pilot sizes are n = 8, k = 3, one-step evidence of 12/16/24 observations, and h ≤ 3. They were chosen because:

- every backend is exact there, and their mutual agreement is the correctness gate;
- the explicit engines fit in memory (12,506 functions × 256 columns per node);
- the h = 3 grid is 65,536 cells.

Larger symbolic stress cases (`configs/s4/stress_dev.json`, n up to 48, h ≤ 2) record where each backend
finishes; see `reports/S4_DEVELOPMENT_REPORT.md`. These sizes were set from computational feasibility before
any model call, not from outcomes.

## 10. Known-mechanism checking (separate panel)

With a public mechanism, `analytic.support_local_query` checks mixed queries over parity, thresholds, mixed
gates and overlapping supports exactly. At n ≤ 14 it is cross-checked against full enumeration; above that the
panel reports labelled corroboration. This uses the formal paper directly. **It establishes nothing about
discovering a hidden mechanism**, and it is never pooled with the S4-A endpoint.

## 11. Tests (paths)

| File | What it pins |
|---|---|
| `tests/test_s4_analytic.py` | orderings, phi, every gate one-set vs direct semantics, transport, codec tables, strict majority vs ceil, Dec, support-locality c/d/mu, refusal, reconstruction |
| `tests/test_s4_mechspace.py` | D counts = explicit engine (40 random worlds, all h, all intervention kinds); 2-node networks: V(D) by brute force over all 256 networks (52 truth networks × 144 claims); inconsistent evidence; unsupported claims; h = 3 cap; duplicates and no-op interventions; n = 20 without materialization; witness replay |
| `tests/test_s4_hcode.py` | golden 25-bit length; DICT vs TEMPLATE on order-disrupted sharing; modules; 100 random round trips over 4 variants; variant ordering; signature inversion; rejection of trailing, truncated, reserved-bit and out-of-class archives |
| `tests/test_s4_checking.py` | status semantics per case and arm; wrong quantifier; stale proof; order mismatch; changed assertion; off-by-one state and wrong horizon; forged, edited, dict and proof-text decisions; empty V; correlation-based claims; resource refusal; revision needs a fresh check |
| `tests/test_s4_system.py` | determinism and realizability; matched control; leakage audit; claim novelty; B = C = D on every family; isomorphism; codec average = brute force; structured models ⊂ V(D); weighted counts exact with weights up to 2^70; sequential-counter AMO = pairwise (with RUP checks); offline items |
