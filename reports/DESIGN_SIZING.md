# Design sizing — from development data only (2026-11-09)

The confirmatory split does not exist yet. Its salt is derived from the future freeze commit, so no confirmatory data informed anything below. Sources: `reports/development/s2_summary.json["design_simulation"]` and `reports/development/s2_sizing_extra.json`; for S3, `s3_summary.json`.

## S2 (primary)

**Development variability of the primary per-world paired difference** (index − uniform, budget 16, 250 worlds):
- per-family SD: 0.074 (canalizing), 0.090 (conjunctive), 0.101 (modular), 0.097 (parity), 0.087 (random lookup);
- pooled SD: 0.095.

The protocol's rough planning formula (σ = 0.5 → 784 worlds) assumed a far noisier endpoint. The measured σ is about 5× smaller, because each world's value is an average over 16 queries and is paired within the world.

**Monte Carlo design simulation.** Development worlds are resampled within the 5 family strata with equal allocation, using 2,000 simulated datasets per N. The scenarios are:
- the observed distribution;
- null (each stratum recentred to 0);
- an effect of 0.05;
- the same effect with deviations inflated ×1.25 (conservative).

| N (total) | median 95% half-width (observed) | conservative | power, effect 0.05 | one-sided false-positive rate under null |
|---|---|---|---|---|
| 200 | 0.012 | 0.016 | 1.00 | 0.028 |
| 400 | 0.009 | 0.011 | 1.00 | 0.020 |
| 1,000 | 0.0055 | 0.007 | 1.00 | 0.024 |
| 2,000 | 0.0039 | 0.005 | 1.00 | 0.026 |

**Bootstrap validity.** Coverage of the stratified paired cluster bootstrap when sampling from the development worlds as a known population: 0.930 at 50 worlds per stratum and 0.947 at 200 per stratum (300 simulations, 1,000 replicates each; `s2_sizing_extra.json`).

**Recommendation and rationale.**
- The primary precision target (half-width ≤ 0.03) is already met by about 50 worlds, so N is not driven by it.
- N is chosen for the comparisons that development showed to be decisive (D21). Index − majority-of-V(D) has development SD 0.111 and estimate +0.007; at N = 1,000 its half-width is about 0.007, so a difference of about 0.015 is resolvable. Per-family half-widths at 200 per family are about 0.013–0.015.
- **Proposed: 1,000 realizable worlds (200 per family)**, plus separately labelled populations: 250 misspecified, 250 shift, 250 noise stress, and 250 null (uniform-H, pending review).
- N was not chosen to reach significance; the development primary already excludes 0 at 250 worlds.
- Cost: about 2,000 worlds × 3.6 s ≈ 120 CPU-minutes (≈ 5 min wall on 24 workers) and about 350 MB of raw records.

## S1 (engineering)

Sized as specified in the protocol rather than by power, because S1 is a correctness/efficiency study:
- small grid: 50 worlds per cell, 4 sizes × 6 families = 1,200 worlds;
- large grid: 30 worlds per cell, 5 sizes × 5 families = 750 worlds.

Exact-mismatch counts must be 0, so the useful quantity is coverage. With 0 mismatches observed in M comparisons, a 95% upper bound on the per-comparison mismatch rate is ≈ 3/M (≈ 3 × 10⁻⁵ for the expected M ≈ 1.1 × 10⁵ reference comparisons). Caps were fixed from development: 20 s per query, 20,000 cubes, 2 × 10⁶ BDD nodes, and a RUP check budget of 2 × 10⁶ steps. Estimated cost: about 132,000 CPU-s, ≈ 2.3 h wall on 16 workers, from per-cell development item means.

## S3 (secondary)

See the S3 section appended below once the v2 pilots complete.
