# XDC — derivation (R6 Track X)

Status: development, 2026-11-12. Written by the implementation agent (Claude Opus), independently of the XDC author,
from the generative description in `docs/R6_PROTOCOL.md`. Code under audit: `src/causalguard/r5/priors.py::XDC`
(`_partition_mass`, `XDC._theta_masses`, `GSR._phi`). Independent oracle: `tests/test_r6_xdc_oracle.py`.

## 1. Objects

- H(n, k): for each node, the set R of functions with at most k essential inputs, one entry per function
  (`candidate_class` keeps canonical rules only: essential inputs, ascending order). A mechanism is m = (r_1..r_n),
  r_j in R. Distinct mechanisms are distinct functions, so "one mass per distinct mechanism" holds by construction.
- Base code: per-rule bit length b(r) (node-independent; `node_bits_table`), w(r) = 2^-b(r) up to a common factor.
- Rule type tau(r): the local truth table of r up to permutation of its inputs, together with its arity. Types
  partition R into classes R_lam. W(lam) = sum_{r in R_lam} w(r); G0(lam) = W(lam) / sum_lam' W(lam').

## 2. Generative model and normalisation

1. Seat the n nodes by a Chinese-restaurant process with concentration theta: partition pi with probability
   CRP_theta(pi) = theta^|pi| prod_{b in pi} (|b|-1)! / theta^(n), where x^(s) = x(x+1)...(x+s-1).
2. Each block b draws one type lam_b ~ G0, independently (two blocks may draw the same type).
3. Each node j in b draws r_j ~ w(r) / W(lam_b) restricted to R_{lam_b}.

Each stage is a probability distribution (sum_pi CRP_theta(pi) = 1 is the Ewens identity; G0 and each w/W sum to 1),
so the joint over (pi, lam, m) sums to 1, and so does its push-forward to mechanisms.

## 3. Push-forward to mechanisms (closed form)

Given m, the type of each node is fixed (tau_j = tau(r_j)), so a seating contributes only if each block is
type-pure, and then lam_b is forced. Hence

    P_theta(m) = prod_j w(r_j)/W(tau_j) * sum_{pi refines the type classes} CRP_theta(pi) prod_{b in pi} G0(lam_b).

The sum factorises over the type classes C_1..C_c of m (sizes s_1..s_c): a refining partition is a product of
partitions of each class, and theta^|pi| prod (|b|-1)! prod G0 factorises. For one class of size s and
x = theta G0(lam), sum over partitions of an s-set of x^{#blocks} prod (|b|-1)! = sum_K c(s, K) x^K = x^(s)
(unsigned Stirling numbers of the first kind). So

    P_theta(m) = prod_j w(r_j)/W(tau_j) * prod_c (theta G0(lam_c))^(s_c) / theta^(n).

This is the Dirichlet-process (Polya-urn) marginal over types: node i takes type lam with probability
(count_lam + theta G0(lam)) / (i - 1 + theta). The oracle evaluates this formula directly; it never enumerates
seatings and never runs the subset recursion.

## 4. theta = infinity is the base code

(theta G0)^(s) / theta^(n) -> prod_c G0(lam_c)^{s_c} as theta -> inf, so P_inf(m) = prod_j w(r_j)/W(tau_j) * G0(tau_j)
= prod_j w(r_j) / sum W: nodes independent, each with the base code's normalised weight. `base - XDC[base]` at
theta = inf is therefore 0 identically, and the finite-theta difference isolates sharing.

## 5. Evidence, the factorisation and the set-partition recursion

One-step observations from full states constrain each node's rule separately (clamped coordinates carry no
information; `node_constraints`). Let c_j(r) = 1 if r fits node j's observations. Then for a fixed seating and
type draw the evidence likelihood factorises over nodes, and

    P_theta(D) = sum_pi CRP_theta(pi) prod_{b in pi} G[b],   G[b] = sum_lam G0(lam) prod_{j in b} u_j(lam),
    u_j(lam) = sum_{r in R_lam} w(r) c_j(r) / W(lam).

`XDC._theta_masses` builds G[b] for all 2^n subsets by a depth-first product, and `_partition_mass` evaluates
F(A) = sum over partitions of A of theta^|pi| prod (|b|-1)! G[b] by fixing the block that contains the lowest
element of A: F(A) = sum_{b ∋ min A, b ⊆ A} theta (|b|-1)! G[b] F(A \ b), F(∅) = 1. Every partition of A is
generated exactly once (its block containing min A is unique). Cost O(3^n S); n = 8 gives 6,561 block steps.
Division by theta^(n) gives P_theta(D).

## 6. Queries: h = 1 and the pointwise-in-intermediate-state argument for h = 2

h = 1: the target value depends only on r_t at s0, so replace u_t by u_t^q(lam) = sum_{r in R_lam} w c_t(r)
[r(s0) = 1] / W and rerun the recursion; P(q | D) = P(D, q)/P(D).

h = 2: with s1 the intermediate state, P(D, q) = sum_{s1} P(D, path through s1, f_t(s1) = 1). For fixed s1 the
event "every node j maps s0 to s1_j, and f_t(s1) = 1, and every node fits D" is again a product over nodes of
rule-level indicators, so the recursion applies with phi_j(lam, s1) in place of u_j(lam), and the result is summed
over s1. The recursion is linear in each G[b] column, so running it column-wise over S = 2^n states and summing
is exact. Correctness needs the nodes to be conditionally independent given (pi, lam, s1), which holds because
the only coupling between nodes is through the seating and the shared types.

## 7. Clamps and initial edits

s0 = edit(x0) for both kinds. Persistent clamp: a clamped node j is set to v_j after every update; its rule is
irrelevant to the trajectory, so phi_j = u_j [s1_j = v_j] (the rule still pays its evidence factor). The target
must be unclamped (refused otherwise). Initial edit: s0 = edit(x0) and the updates are free, so no node is clamped
at s1. Both match `docs/SEMANTICS.md` and are covered by the oracle (own simulator).

## 8. theta mixture

The reported 'xdc' is P(q | D) under the prior (1/4) sum_theta P_theta, i.e. sum_theta P_theta(D, q) / sum_theta
P_theta(D). This is valid only because each P_theta(D) is a normalised probability (§2), which the oracle checks
by summing the closed form over all of H(3, 1) (total 1 to 1e-12 for every theta and both bases).

## 9. Floating-point error

All terms are nonnegative. A sum of m nonnegative floats has relative error at most (m - 1)u / (1 - (m - 1)u),
u = 2^-53, and products add their factor counts. Along any path of the computation the depth is at most
n products in G, n nested recursion sums of at most 2^(n-1) terms, and 2^n terms over s1, so the relative error of
each mass is below about (2^n + n 2^(n-1) + 2n) u < 1.5e-13 at n = 8 (1,296 u), and a ratio doubles it. The declared
GAMMA = 1e-9 and the recorded bounds p +/- 1e-9 are conservative. Underflow: the smallest products at n = 8 are
far above 1e-300. This is an a-priori bound, not interval arithmetic; the oracle agreement (§ audit) is the
empirical check.

## 10. Limits

- The prior depends on the type partition only; it does not reward shared supports or wiring.
- Sharing is learned from the same n nodes it is used on: at n = 8 there is little to learn from, and constant
  nodes (arity 0) share one type trivially.
- Exact cost O(3^n 2^n) for h = 2: infeasible above n ≈ 12–14. Track S uses an approximation (XDC-EB).
- `XDC.probabilities` returns P(target node = 1); the literal convention is applied by `forecast._node_prob`,
  which refuses value-0 literals. Callers that bypass `_node_prob` must convert.
