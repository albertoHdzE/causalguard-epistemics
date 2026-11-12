# R6 protocol — does exact dictionary sharing improve unseen inference? (development)

Status: development, 2026-11-11. Follows the independent R5 review (`reports/review_r5/REVIEW.md`, findings F1, F2).
Offline symbolic work only: no model calls, no freeze, no confirmatory run. R5 records and endpoints are unchanged.

## Question

R5 found that the CGH-1 prior forecasts unseen outcomes no better than the flat gate-catalogue code. The review
found that the method's sharing component was never in the tested prior. R6 asks the question R5 could not:

> If nodes are allowed to reuse rule types, and the sum over all compatible mechanisms is still exact, does the
> forecast of unseen outcomes improve over the best flat code — on fresh worlds and on published models?

## The method under test: XDC, an exchangeable dictionary code

Defined in `src/causalguard/r5/priors.py::XDC`. Nodes are seated by a Chinese-restaurant process with
concentration theta. Each dictionary entry draws one order-free rule type (a local truth table up to permutation of
its inputs) from the base code. Each node instantiates its entry's type as a concrete rule (support and pin order)
with probability proportional to the base code's weight. As a code: a node either pays the base-code price for a
new rule type or refers to a type already in use, at a price that falls with its use count.

- Full support on the declared class H(8, 3); one mass per distinct mechanism.
- theta = infinity is exactly the flat base code (tested to 1e-10), so `base − XDC[base]` isolates sharing.
- No node order, cyclic offset, module size or analytic vocabulary is assumed by the sharing step.
- theta is not fitted: the predictor is the equal-weight Bayes mixture over theta in {0.5, 2, 8, infinity}.
- The posterior is summed exactly over all set partitions of the nodes by a subset recursion, pointwise in the
  intermediate state for two-step queries. float64 over non-negative terms; tested against explicit enumeration of
  every seating, type draw and instantiation (24 cases).

"Our method" in R6 is `xdc[cgh_flat]`: the CGH-1 flat code (formal-paper analytic vocabulary) with dictionary
sharing. `xdc[gate]` is the same sharing step on the generic gate-catalogue code and is reported as the vocabulary
attribution. XDC is related to, not byte-compatible with, the DICT mode of CGH-1 and the original hierarchy
dictionary: it is the adaptive, order-free form of the same idea.

## Populations

| Panel | Role | Content |
|---|---|---|
| `r6-g-cal-v1` | calibration | R5 calibration mechanisms (64), new design salt |
| `r6-g-ext-dev-v1` | external development | the 40 published-model source groups already used in R5 (159 instances) |
| `r6-g-eval-v1` | **fresh synthetic evaluation** | 320 new mechanisms (40 per stratum) from the unchanged R5 generators, salt `r6-G-eval-v1` |
| `r6-g-ext-fresh-v1` | **fresh external evaluation** | the 122 source groups (hash ranks 40–161) never used in R5; 449 instances, at most four per group |

The generators (`G_POPULATION_SPEC`) are unchanged from the R5 lock. The fresh external panel uses R5's fixed
transformation (8-node backward subnetwork, outside regulators clamped to 0) and the same hash ordering.
Evidence budgets 8 / 16 / 24 and the eight-query schedule are unchanged.

## Endpoints

**Primary:** `Brier(gate) − Brier(xdc[cgh_flat])` at 16 observations on the fresh synthetic evaluation, world mean
over the eight scheduled queries, equal stratum weights, source-group cluster bootstrap (10,000 replicates), with
worst-case missingness bounds. `gate` is the generic champion locked in R5. Positive favours the method. Practical
planning value 0.02, as in R5.

**External primary:** the same contrast on the fresh external panel, clustered by source group. Never pooled with
synthetic worlds.

**Prespecified secondaries:** sharing (`cgh_flat − xdc[cgh_flat]`), vocabulary (`xdc[gate] − xdc[cgh_flat]`),
generic sharing (`gate − xdc[gate]`), uniform and GSR against the method, budgets 8 and 24, per-stratum means, the
distribution of per-world differences, and the difference by hidden rule reuse (number of nodes minus number of
distinct order-free rule types in the hidden mechanism; evaluator-side, never a predictor input).

## Disclosures that limit the claim

- XDC was designed after the R5 strata definitions and R5 per-stratum results were known. Four of the eight strata
  contain reused local rules by construction. A positive synthetic result is evidence that exact sharing works where
  rules are reused, not that reuse is common in real systems. The fresh external panel and the reuse analysis are
  there to bound that.
- Calibration and the external development panel were looked at before the lock; nothing was fitted on them, but the
  decision to proceed and the choice of `cgh_flat` as base were made with them in view.
- The uniform-H stratum is the built-in null: any sharing prior should lose there.
- No claim about Kolmogorov complexity, universal priors or biological accuracy follows.
