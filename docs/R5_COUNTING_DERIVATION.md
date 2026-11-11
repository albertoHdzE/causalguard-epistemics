# R5 counting derivation: distinct compatible mechanisms under one-step evidence (h <= 2)

Status: R5 WP1 derivation by the implementation agent, with independent small-case checks (tests named below). It
is a careful re-derivation of what arm D implements, not a peer-reviewed theorem, and it does not claim a new
counting principle (see §7).

## 1. Objects

- Nodes `[n] = {0..n-1}`, states `x in {0,1}^n`, synchronous update `x' = (f_0(x), ..., f_{n-1}(x))`.
- Declared class `H(n,k)`: every node function `f_j : {0,1}^n -> {0,1}` has an **essential support**
  `E(f_j) = {i : exists x, f_j(x) != f_j(x xor e_i)}` with `|E(f_j)| <= k`. A mechanism is `M = (f_0..f_{n-1})`.
  Two mechanisms are equal iff all node functions are equal as functions (distinct canonical mechanisms; never
  encodings, supports-with-tables or SAT assignments).
- Interventions: `initial_edit` (overwrite coordinates of the start state), `persistent_clamp` (overwrite them at
  every step; clamped coordinates are not observed).
- Evidence `D`: one-step observations `(x, intervention, {(j, y_j)})`. The effective input is
  `x_eff = edit(x)`. `V(D) = {M in H : M reproduces every observed coordinate}`.

## 2. Factorization (one-step evidence)

**Claim 1.** If every observation is one-step, `V(D) = V_0 x ... x V_{n-1}` with
`V_j = {f in H_j : f(x_eff) = y for every observation of node j}` (`H_j` = functions with `<= k` essential inputs),
unless a clamp contradicts an observed clamped value, in which case `V(D)` is empty.

*Proof.* An observation of node `j` at effective input `x_eff` constrains only `f_j(x_eff)` (one synchronous step
from a fixed input). Membership in `V(D)` is a conjunction of such per-node conditions, hence a product.

*Counterexample to extension (multi-step evidence).* `n = 2`, observe node 0 after **two** steps from `00`:
`x0'' = f_0(f_0(00), f_1(00))` couples `f_0` and `f_1`; the compatible set is not a product. R4/R5 refuse
multi-step evidence (`UnsupportedClaim`).

## 3. Per-node distinct counts: schema counts and Moebius correction

Let `C_j = {(x_eff, y)}` be node `j`'s constraints. For a support `F` (`|F| <= k`, ascending, local bit `t` =
`F[t]`), let `P_F = {proj_F(x) : (x, y) in C_j}` be the observed local patterns.

- `g_j(F) = #{local tables tau on F : tau(proj_F x) = y for all (x,y) in C_j} = 2^(2^|F| - |P_F|)` if no two
  constraints project to the same pattern with different values, else `0`.

A function with essential support `E` is representable by a table on every `F superset E` (the table ignores
`F - E`), and by none on `F not superset E`. Writing `e_j(E)` for the number of compatible functions whose
essential support is **exactly** `E`:

- `g_j(F) = sum_{E subset F} e_j(E)`  (each compatible function counted once per superset support).

**Claim 2 (Moebius inversion on the Boolean lattice).**
`e_j(E) = sum_{F subset E} (-1)^{|E - F|} g_j(F)` and

`|V_j| = sum_{|E| <= k} e_j(E) = sum_{|F| <= k} g_j(F) mu(|F|)`,
`mu(f) = sum_{m=0}^{k-f} (-1)^m C(n - f, m)`.

*Proof.* The first identity is Moebius inversion of the zeta transform `g = zeta e`. For the second, swap sums:
`sum_{|E|<=k} sum_{F subset E} (-1)^{|E-F|} g(F) = sum_{|F|<=k} g(F) sum_{E: F subset E, |E|<=k} (-1)^{|E-F|}`; the
inner sum depends only on `|F| = f` and counts `m = |E - F|` new elements chosen from `n - f`.

*Small checks.* `n = 1, k = 1`, no evidence: `g(empty) = 2`, `g({0}) = 4`, `mu(0) = 1 - 1 = 0`, `mu(1) = 1`,
`|V| = 4` (two constants, COPY, NOT). `n = 2, k = 1`: `mu(0) = 1 - 2 = -1`, `|V| = -2 + 2 * 4 = 6`.
`n = 3, k = 2`: 38 functions (test `test_gen_ve_against_truth_table_oracle` enumerates all 256 truth tables).

*Overcount trap.* Counting `(support, table)` pairs, or SAT models of an encoding with an exactly-`k` support
selector and free tables, counts a function once per representation. Test
`test_projected_cnf_counts_distinct_mechanisms_and_trap` exhibits it on the R4 verdict encoding (which R4 never used
for counting).

## 4. Point queries

Query: start `x0`, intervention, horizon `h`, target literal `x_t = c` (R5 G uses `c = 1`, so the probability is
of the node value). `s0 = edit(x0)`; clamped coordinates are fixed at every step.

**h = 1.** If `t` is clamped the answer is determined. Otherwise
`#{M in V : q} = prod_{j != t} |V_j| * #{f in V_t : f(s0) = c}`, the last term by Claim 2 with the extra constraint
`(s0, c)`.

**h = 2.** Let `A_j(b) = #{f in V_j : f(s0) = b}` for unclamped `j != t` and `A_j(b) = |V_j| [b = cval_j]` for
clamped `j`. Then

`#{M : q} = sum_{f_t in V_t} sum_{s1 : s1_t = f_t(s0)} [f_t(s1) = c] prod_{j != t} A_j(s1_j)`.

Condition on the target's essential support `E` and put `W = E u {t}` (`t in E` is a **self-input**: `s1_t` is
both the target's first-step output and an input of its second step). `f_t(s1)` depends on `s1|_E` only, so the sum
over `s1` outside `W` factorizes:

`#{M : q} = sum_{|E|<=k} prod_{j notin W} (A_j(0) + A_j(1)) * sum_{a in {0,1}^W} prod_{i in W - {t}} A_i(a_i) *
e_t(E ; (s0 -> a_t), (a -> c))`,

where `e_t(E; extra)` counts compatible functions with essential support exactly `E` that also satisfy the two extra
constraints (Claim 2 restricted to subsets of `E`). This is the formal paper's support-locality transported from
states of a known network to the unknown-mechanism setting.

**Witnesses.** For each verdict side with a positive count, choose `E` and `a` with a positive term, build `f_t` on
`E` from its fixed local rows (free rows 0), and for every other node a compatible function with the required
first-step value; independently replayed against all evidence and the query (`Workspace.check`).

**Persistent clamps** fix `s1_j = cval_j` (and never constrain `f_j` through clamped observations). Clamped targets
are determined.

## 5. Complexity (k fixed)

- Preprocessing (per node): `O(sum_{f<=k} C(n,f) * B * k)` pattern projections (`B` = observations), `n` nodes.
- `g_j(F)` with extra constraints: `O((B + 2) k)`.
- h = 1 query: `O(n^k)` g-evaluations for the target plus cached totals.
- h = 2 query: `O(n^k * 2^(k+1) * 2^k)` g-evaluations (Moebius over subsets of `E` for each assignment of `W`).
- **Bit complexity.** `|V| <= prod_j |H_j|`, `|H_j| <= sum_{f<=k} C(n,f) 2^(2^f)`, so counts have
  `O(n (k log2 n + 2^k))` bits; each h = 2 term multiplies `O(n)` such integers. Total
  `O(n^k 4^k * n * M(n (k log n + 2^k)))` bit operations with `M` the multiplication cost. Polynomial in `n` and
  `B` for fixed `k`; exponential in `k` (doubly exponential through `2^(2^k)` only inside closed-form powers of two).
- **h = 3 is not covered by this result.** The target's third-step value depends on `s2|_E`, and every `s2_i`
  (`i in E`) depends on `s1|_{E_i}`: the summation couples up to `k + k^2` coordinates and conditions on the supports
  of `k + 1` functions jointly (`O(n^(k(k+1)))` support tuples). Arm D uses a metered enumeration of `s1` with a
  cap (resource refusal beyond it). No tractability claim for `h >= 3`.

## 6. Distinction from known-model state repertoires

The formal paper counts **states** of one **known** network (support-local `c`, `d`, `mu` for a queried pattern).
Here we count **mechanisms** compatible with evidence. The schema/Moebius count in §3 is a count over local truth
tables, not over states; the same algebra (projection to a support, free rows) appears in both, the objects differ.

## 7. Relation to prior methods (novelty boundary)

- The computation is **variable elimination** on the factor graph `{f_j} u {s1}`: eliminate every non-target node
  function into `A_j`, condition on the target's support (cutset conditioning on a selector), and sum the rest.
- The Moebius correction performs the job of **projection** in projected model counting: it removes the
  multiplicity of `(support, table)` representations so that each function is counted once.
- A decision-DNNF compiler (e.g. d4 with projection; Lagniez–Marquis line; certified projected compilation, SAT
  2025) would discover the node decomposition automatically; conditioning on the target selector corresponds to a
  decision node. A knowledge-compilation map (Darwiche & Marquis 2002) separates compactness from supported
  queries; our object supports exactly the queries above.
- Therefore the R5 claim is narrower: a closed-form, polynomial-for-fixed-`k`, h <= 2 projected count specialised
  to bounded-indegree synchronous networks, written in the formal paper's index-set language. Whether it is
  faster than a competent generic method is an empirical question (Track C). **R5 finding (benchmark pending at the
  time of writing): an explicit-domain VE counter written independently (GEN-VE) agrees exactly and was faster than
  D's pure-Python implementation in development probes at n = 16-48, because k = 3 keeps the explicit domain
  (218 essential tables per support) small and vectorizable.** The closed form's advantage is asymptotic in
  `2^(2^k)`, which is a constant at k = 3.

## 8. Independent checks (tests/test_r5.py)

| Check | Independent of D? |
|---|---|
| `test_gen_ve_matches_d_and_explicit_engine` (random n in {4,6}, k in {2,3}, h in {1,2}, all interventions) | GEN-VE shares no code with mechspace; explicit engine enumerates the materialized class |
| `test_gen_ve_against_truth_table_oracle` (all 256 functions on 3 inputs, product enumeration for h = 2) | yes, full truth tables |
| `test_projected_cnf_counts_distinct_mechanisms_and_trap` | yes, SAT enumeration with blocking clauses |
| `test_and_counterexample_model_relative_proof_is_not_world_truth` (§9) | uses D counts, checked by hand below |
| `test_mixed_node_bounds_match_explicit_union_space` | per-node bounds vs uniform spaces |

## 9. The n = 2 model-relative proof example (Track M)

`H = indegree <= 1`. Observations from `00`, `10` (`x0=1`), `01` (`x1=1`) all give `(0,0)`. A node function with
`<= 1` input that maps `00, 10, 01` to 0 must be constant 0 (COPY/NOT of either input fail on one of the
observations). So `|V_0| = |V_1| = 1` and `x0' = 0` from `11` is **verified**. The hidden `x0' = x0 AND x1`,
`x1' = 0` reproduces all observations and gives `x0' = 1` at `11`. Under `indegree <= 2`, `|V_0| = 2` (constant 0
and AND) and the target is underdetermined (D counts `2 of 4`). The proof is correct relative to `H`; the world is
outside `H`.
