# Semantics (contract implemented by CausalGuard)

## States, rules, update
- A state of an n-node network is an integer x ∈ [0, 2ⁿ); node i is bit i (LSB-first, weight 2ⁱ). `bits_of`/`state_from_bits` are inverse (tested exhaustively for n ≤ 6).
- A rule has ascending distinct `inputs` and a local table; local index y = Σₜ bit(x, inputs[t])·2ᵗ.
- Update is **synchronous**: every node reads the old state. A sequential (in-place) convention would be a different task id; it exists only in a fixture (`F09`) to show the difference.

## Interventions and horizon
h counts **updates**, not trajectory rows.

| kind | t = 0 | t → t+1 |
|---|---|---|
| none | s₀ = s | s_{t+1} = F(s_t) |
| initial_edit(A) | s₀ = edit_A(s) | s_{t+1} = F(s_t) |
| persistent_clamp(A) | s₀ = clamp_A(s) | s_{t+1} = clamp_A(F(s_t)) |

h = 0 reads the intervened initial state (fixture `F04`).

## Queries on one mechanism
Typed predicate grammar: literals `x_i = v`, and/or/not, true/false. No model-supplied code is executed. A query is (quantifier, domain predicate, intervention, h, target predicate) over the admissible set S = {s : domain(s)}:
- exists: true iff some s ∈ S reaches the target at h;
- forall: true iff every s ∈ S does;
- S = ∅ ⇒ `invalid_domain` (never a vacuous truth; fixture `F07`).
A budget exhausted ⇒ `unknown_resource`; outside the grammar ⇒ `unsupported`. These statuses are enums whose truth value cannot be taken (`bool()` raises).

## Evidence, hypothesis class, verdicts
- An observation = (input state, intervention, horizon, observed coordinates). S2/S3 evidence uses horizon-1 observations; the version space then factorizes exactly over nodes. Observing a clamped coordinate carries no information about its rule; observing it at a non-clamp value is impossible for every model (fixture `E05`).
- H = all networks on n nodes whose node functions have ≤ k essential inputs (constants included). Per node it is enumerated completely (|H_node(7,3)| = 7,856, checked against the closed-form count). `candidate_set_complete = true`, `candidate_count = Π_j |V_j|`.
- V(D) = {M ∈ H : M matches D}. For nonempty V(D): **entailed** (all true), **refuted** (all false), **underdetermined** (a replayed pair M⁺, M⁻ disagrees). Empty V(D) ⇒ `inconsistent_evidence_or_class` (fixtures `E02`, `E04`), never `refuted`.
- Verdicts quantify over all of V(D) by a complete SAT encoding (each node selects a k-subset of inputs and a free local table — exactly the functions with ≤ k essential inputs). Witness mechanisms are replayed by the independent reference against every observation and the query. Entailment/refutation = UNSAT of the opposite side (optionally DRUP-proof-checked by `proofcheck`). Cross-checked against explicit enumeration of V(D) and against brute force over whole networks (tests).
- **A selected model's answer (e.g. the shortest code) is a prediction, not a certificate.** `predict()` and `verdict()` are separate APIs.
- Two truths are always logged separately: the evidence-relative verdict and the hidden world's answer. In misspecified worlds a correct-in-H certificate can be wrong about the world; S2 reports this rate.

## Verification levels (per result)
`exhaustive`, `witness_replayed`, `checked_proof` (independent RUP checker), `independent_exact` (BDD from direct rules), `solver_only`, `cross_solver` (not a proof), `sampled` (never global exactness), `none`.

## Fixtures
`python -m causalguard fixtures` prints the hand-derived table (`data/fixtures/semantic_fixtures.json`): AND/OR indistinguishability, XOR, NOT, Rule 110, input-order asymmetry (IMPLIES), edit vs clamp, synchronous vs sequential, zero horizon, impossible domain, inconsistent observations, misspecified class, clamped-observation semantics. Resource-unknown and overlap counting are covered in `tests/test_query_backends.py` and `tests/test_index_repr.py`.
