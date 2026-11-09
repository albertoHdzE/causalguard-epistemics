# Scientific contract v2

## 1. Reassessment of the owner's argument

The owner is right that epistemics need not mean infallibility. A scientific model can be useful despite incomplete evidence and imperfect correspondence to the world. Binary encodings can represent states, conditions, paths and programs. The relevant question is whether a chosen representation preserves the distinctions needed for the intended queries and predictions. Representability alone does not establish those semantics.

Compact executable models are a defensible operational proxy for explanatory economy. Chaitin presents scientific theory as compression in [The Limits of Reason, 2006](https://www.cs.virginia.edu/~robins/The_Limits_of_Reason_Chaitin_2006.pdf). This motivates a hypothesis; it is not a theorem that a shorter empirical model must be true. [Marx and Vreeken, 2021](https://arxiv.org/abs/2105.01902) connect practical MDL reasoning with an algorithmic-independence postulate for causal inference. Their assumptions must not be silently generalized to every representation or domain.

The earlier assessment understated the value of compressed repertoires. Replace the framing “Boolean logic cannot give real-world truth” with: **symbolic models provide exact deductions conditional on assumptions; experiments determine their predictive adequacy, and uncertainty records where observations do not identify a unique answer.**

## 2. Four claims kept distinct

| Level | Testable claim | Required evidence |
|---|---|---|
| Representation | A compact object preserves the declared finite repertoire | Decoder round-trip or equivalence proof; conventions and metadata included |
| Computation | Certain queries can be answered without expanding that repertoire | Sound query result/certificate, measured time/memory; failures retained |
| Induction | Shorter compatible mechanisms predict unseen behavior better | Separated observed data, selection data and held-out interventions; baselines |
| Improvement | A changed system/model performs better out of sample | Fixed object of change, matched controls, untouched tests, uncertainty estimates |

A successful result at one level does not automatically establish the next. No restriction here says all models must be perfect; instead it makes their limitations measurable.

## 3. Core representation must remain index-based

Read upstream `GOVERNANCE/GLOSSARY.md`, `GOVERNANCE/ORDERING.md`, `GOVERNANCE/DESCRIPTION_LENGTHS.md`, and relevant canonical implementation before selecting an adapter. Prefer MCP graph tools for code discovery if available; fall back to source search if unavailable or insufficient.

Represent a node's on-set as a union of schema-generated index families. For a schema with fixed bits and don't-care positions J, define anchor a from fixed 1 bits and Ω as all sums of the bit weights in J. The represented indices are a+Ω. **J includes don't-care positions on connected inputs; it is not merely the disconnected inputs.** Store J symbolically. Do not materialize all offsets for large n. The union can overlap; counts must not sum family sizes without accounting for overlap.

The Rule-110 case is mandatory: all three inputs are connected, yet schema compression is possible (upstream cites `01*`, `10*`, `*10` in its declared order). Derive and test the ordering rather than copying a printed pattern into an incompatible bit convention. Compare OR and parity/XOR so a method blind to connected-input schemata cannot pass as the intended method.

BDD/SAT support may accelerate queries or serve as an independent reference. It must not silently replace the index method. Record `representation_backend`, `query_backend`, conversion time, representation bytes, and any materialization. A BDD-backed implementation should be described as a hybrid; any speed claim must separate contributions.

Do not claim symbolic storage implies all queries are easy. General Boolean queries can be computationally hard; some functions are expensive in a particular schema language even when another short program exists. Include difficult cases, timeouts, and ordering sensitivity.

## 4. Dynamics and questions

States are n-bit vectors with declared LSB-first index conversion. A network F maps {0,1}^n to {0,1}^n synchronously; node j reads the old state, not partially updated values. Explicitly distinct update conventions need distinct task IDs.

Allowed intervention types:

- `initial_edit`: overwrite selected coordinates at t=0, then apply F h times.
- `persistent_clamp`: clamp the initial state, then repeat `state = clamp(F(state))` h times.

Horizon h counts updates, not trajectory rows. Validate h=0 separately, including what intervention does at t=0. Validate all state constraints and distinguish an empty admissible-state set from an ordinary universal truth. In this study an empty admissible domain is invalid evidence/domain, not a vacuous success.

For a compatible mechanism M and nonempty admissible state set S, a query carries its own quantifier:

- `exists`: q(M)=true iff some s in S reaches the predicate at horizon h.
- `forall`: q(M)=true iff every s in S reaches the predicate at horizon h.

Encode necessity/sufficiency as explicit implications and universal quantifiers, not vague natural-language labels. In first implementation restrict predicates to a documented typed Boolean grammar (literals, conjunction/disjunction/negation); no executing model-supplied code.

## 5. Partial evidence and honest uncertainty

Given declared hypothesis class H and observations D, define V(D)={M in H : M matches D}. Observations specify their intervention, input, horizon and observed output coordinates. Observational trajectories and controlled interventions are not interchangeable.

For nonempty V(D):

- `entailed`: every M in V(D) has q(M)=true.
- `refuted`: every M in V(D) has q(M)=false.
- `underdetermined`: there are compatible mechanisms M+ and M− with opposite q values.

An empty V(D) is `inconsistent_evidence_or_class`, not `refuted`. A computational timeout is `unknown_resource`, not `underdetermined`. Unsupported grammar is `unsupported`, not an answer. Operational LLM abstention is another separate status.

“True under the selected shortest model” is a **prediction**, never a certificate over V(D). Selecting one of many models cannot turn uncertainty into logical entailment.

Finite explicit candidate sets are acceptable for a bounded benchmark, but claims must say “relative to this candidate set.” For a declared grammar-wide class, either enumerate it completely within a bound or use sound complete symbolic quantification; a beam or sampled population is not the entire class. Separate `candidate_set_complete` from `candidate_count`. An incomplete search may provide a valid pair of disagreeing witnesses, but failure to find one is not proof of agreement.

Two truths must be logged separately: the evidence-relative verdict and the hidden generating world's answer. The latter is for scientific assessment; it must not leak into candidate selection or the model's prompts. Include both realizable worlds (generator in H) and misspecified worlds (outside H). No method can guarantee recovering an arbitrary full repertoire from an arbitrary incomplete sample; observationally indistinguishable mechanisms are the required counterexample.

## 6. Complexity ledger

Use a frozen, independently decodable code. Record actual bit length, object encoded, decoder identity/version, headers, ordering, topology, gate parameters, schema/literal counts, padding and any shared dictionary. A code for observed data alone is not a code for the full mechanism.

With a fixed universal interpreter U and a decoder P that produces x from self-delimiting code c, the claim is of the form `K_U(x) <= length(encode(P,c)) + constant_U`. With a fixed decoder treated as side information, state the conditional bound instead. Do not assert equality with K or that the bound is tight. Record finite-prefix lengths/horizons for generated sequences.

**Ordering two available upper bounds does not prove the same ordering of the true Kolmogorov complexities.** It ranks the codes obtained under the declared representation/search budget. Do not market a heuristic proxy as a certified upper bound without an executable reconstruction path. Keep BDM/CTM, entropy, upstream analytical variants A–E, gzip bytes and archive bits separately named; consult the upstream owner before reuse.

For multiple datasets/models, report both per-object payload and amortized total `decoder + dictionary + sum(payloads)` at explicitly stated sample counts. For inference with noise use a declared two-part code `L(M)+L(D|M)` that exactly reconstructs D, including residual positions/values and metadata. In noiseless consistent selection the residual is empty, but model metadata still counts. Selection uses observations only; full hidden truth tables are evaluation targets, never compression inputs available to the learner.

Required comparators: literal truth tables at tractable sizes; direct gate/circuit program; DNF/schemata; BDD with declared variable-order budget; generic lossless compression on the same serialized object where applicable. It is legitimate for the index representation to lose. Do not compare different target objects as though they were the same coding task.

## 7. Scientific claim ladder

Allowed after corresponding evidence: exact reconstruction on a bounded corpus; conditional certificates; compactness under a named codec; measured query efficiency; held-out predictive gain; system-level or weight-level improvement.

Not established by this project alone: universal comprehension, empirical truth guaranteed by determinism, exact K, shortest possible representation, efficient compression of every Boolean function, clinical validity, or recursive general intelligence improvement.

The main paper should lead with whichever hypothesis the evidence actually supports—including null results and counterexamples—not the most ambitious phrase in the proposal.
