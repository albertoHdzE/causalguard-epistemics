# Revised sizing proposal — iteration 2 (for review; nothing here is frozen)

Inputs are DEVELOPMENT per-world deltas only (`reports/development_r2/s2_v2_summary.json`,
`design_simulation_*`). Method: worlds are resampled within equal-allocation family strata. The interval is the
normal interval with the stratified SE, at the requested alpha. (The v1 `design_simulation(alpha=...)` ignored its
alpha argument; this is fixed and tested.) There are 2,000 simulated studies per N. The scenarios are: observed
deltas, recentred to 0 (null), recentred to +0.05, and the latter with deviations inflated ×1.25. The supersedes
`reports/DESIGN_SIZING.md` for S2 and S3; that file is kept as the iteration-1 record. Its independent-query
"3/M" bound is **withdrawn**: queries within a world are correlated, and zero observed mismatches are a count over
world-level comparisons, not a universal correctness proof.

## S2 revised primary: index − compatible-set majority (exact), structured, B16

The development SD per world is 0.087–0.102 by family (250 worlds), and the development mean is +0.0009.

| N structured worlds (equal families) | median 95% half-width | P(lower > 0) if true = observed | P(lower > 0) if true = +0.05 | same, SD ×1.25 |
|---:|---:|---:|---:|---:|
| 200 | 0.0130 | 0.031 | 1.00 | 1.00 |
| 400 | 0.0092 | 0.036 | 1.00 | 1.00 |
| 600 | 0.0075 | 0.049 | 1.00 | 1.00 |
| 1,000 | 0.0058 | 0.059 | 1.00 | 1.00 |
| 2,000 | 0.0041 | 0.068 | 1.00 | 1.00 |

Under the recentred null, the two-sided false-positive rate is 0.021–0.032 per tail-pair (nominal 0.05).

**Proposal.** 1,000 structured worlds (200 per family) and 1,000 IID uniform-H null worlds. The question is
superiority, two-sided, with magnitude reported against the 0.05 reference and no equivalence claim. N=1,000 gives
a half-width of about ±0.006. It has essentially full power for a +0.05 effect, a minimum detectable effect of
about 0.008 at 80% power, and **no meaningful power for an effect the size of the development estimate**
(≈ 6%). We do not promise power for the observed small effect. N is fixed now and will not be adapted to
results. A result interval containing 0 is reported as "no clear index advantage detected".

## Null population (required)

Development null SD is 0.084, and the null mean of index − majority is −0.022. At N=1,000 the half-width is
≈ ±0.005; the null deltas are expected to sit below zero (the Bayes predictor wins on average under the prior).

## Structured − null interaction (EXPLORATORY only)

The SE of a difference of independent samples is ≈ √(0.0030² + 0.0027²) ≈ 0.0040 at 1,000 + 1,000 worlds, so
the half-width is ≈ ±0.008. The development estimate is +0.023 [+0.008, +0.038] (250 + 250). If this is retained
it is a named exploratory estimate, not a second primary.

## Numerical-comparator uncertainty

None: the comparator is exact (integer counts). The MC diagnostic shows why: a finite-sample MC majority shifts
the world-level contrast by 0.004–0.006 at every predeclared budget (4,096–65,536), entirely through exact ties.

## Stress populations (descriptive, separately labelled)

Misspecified 100 (20 per family), shift 100, noise 100 (20 per family): a precision ±0.02–0.03 for descriptive
curves. Misspecified worlds give an empty exact V(D) in about 98% of worlds at B16. Before confirmation the
reviewer may prefer to drop or redesign this population, because exact selectors produce no output there.

## S1

Unchanged from iteration 1 (1,950 worlds over 49 cells, caps fixed). Reporting is in completion denominators and
mismatch counts over world-level comparisons. See the S1 section of `DEVELOPMENT_REPORT_R2.md` for the repair
panel.

## S3

Development only; see the S3 section of `DEVELOPMENT_REPORT_R2.md` for the held-out panel and the re-sizing of
the T_cert − T_label pilot focus.
