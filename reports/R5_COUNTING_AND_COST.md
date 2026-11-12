# R5 Track C — exact counting, comparators and fair cost (development)

Runs: `r5-c-bench-v1` (failed 144/144 before timing, R5-03, kept), **`r5-c-bench-v2`** (snapshot `9c1ae3f`, 144/144
ok), `r5-c-bench-n64-genve-v3` (snapshot after R5-04: the 8 GEN-VE n = 64 cells, which errored in v2 on an int64
overflow). Analyses `reports/development_r5/c_benchmark*.json`. Derivation: `docs/R5_COUNTING_DERIVATION.md`.
Serialized timing (1 worker, nothing else running, randomized order), M3 Ultra.

## Comparators and their status

| Backend | What it is | Counts distinct mechanisms? | Status |
|---|---|---|---|
| D | support-schema Moebius counting + support-local h = 2 (our method) | yes (derivation §3) | run |
| GEN-VE | independent explicit-domain variable elimination over canonical (essential support, table) encodings | yes (bijection; tested vs truth-table oracle) | run (n = 64 via v3 after R5-04) |
| B | strengthened generic SAT (ladder AMO) | verdicts only; counts only n ≤ 10 (materialized class) | run |
| ganak v2.9.0 (projected #SAT) | external projected counter on our canonical projected CNF | yes, by construction of the CNF (projection tested on tiny cases) | **not run**: download/execution not authorized in this session |
| d4v2 (projected d-DNNF) | external knowledge compiler | — | **not buildable** on arm64 (PaToH x86_64-only) |

The knowledge-compiler comparison is **incomplete**. The canonical CNF (`r5/counting.py::canonical_cnf`) is in
bijection with distinct mechanisms (projected = unprojected count = distinct on exhaustive tiny cases); the verdict
encoding used by B is not (multiplicity trap, tested).

## Exactness

512 query counts compared across backends in v2 + 128 at n = 64 (GEN-VE v3 vs D v2): **0 mismatches**. B's SAT
verdicts agreed with D wherever both finished (common gate cross-checks raised no disagreement).

## Workspace phase (build + 16 queries; 8 instances per size = 4 matched cyclic templates + 4 rewired pairs)

Queries answered within budget (of 128 per cell) — checkpoints 1 / 10 / 60 / 300 s from one execution:

| n | D | GEN-VE | B (SAT verdicts) |
|---:|---|---|---|
| 8 | 128 / 128 / 128 / 128 | 128 / 128 / 128 / 128 | 0 / 128 / 128 / 128 |
| 16 | 128 / 128 / 128 / 128 | 128 / 128 / 128 / 128 | 91 / 128 / 128 / 128 |
| 32 | 15 / 128 / 128 / 128 | 128 / 128 / 128 / 128 | 2 / 63 / 128 / 128 |
| 48 | 0 / 62 / 128 / 128 | 67 / 128 / 128 / 128 | 0 / 8 / 77 / 128 |
| 64 | 0 / 9 / 114 / 128 | 0 / 128 / 128 / 128 | 0 / 0 / 17 / **99** (4 timeouts, 1 over limit) |

Median cumulative time after 1 / 4 / 16 queries (s; includes build):

| n | D | GEN-VE | B |
|---:|---|---|---|
| 8 | 0.03 / 0.04 / 0.07 | 0.02 / 0.02 / 0.03 | 1.65 / 1.66 / 1.69 |
| 32 | 0.68 / 1.40 / 5.16 | 0.12 / 0.16 / 0.37 | 1.25 / 4.92 / 20.2 |
| 48 | 1.73 / 7.10 / 21.0 | 0.42 / 0.75 / 1.68 | 6.05 / 24.5 / 97.2 |
| 64 | 9.6 / 19.8 / 64.0 | 1.48 / 2.31 / 5.72 | 21.0 / 82.2 / 283.9 |

Peak RSS of the workspace phase at n = 64: D 520 MB, GEN-VE 759 MB, B 829 MB. Repetitions ×3 on the preregistered
subset ((8,0),(8,4),(32,0),(32,4)) were stable (e.g. n = 32 D 5.2–6.5 s, GEN-VE 0.35–0.38 s, B 15.3–16.1 s for the
full phase).

## Full checked release (4 scheduled queries: check + common SAT cross-check of every impossible side with RUP proof
checking + witness replay + commit)

| n | D: done by 1/10/60/300 s (of 32), median total | B: same | Certificate levels of impossible sides |
|---:|---|---|---|
| 8 | 32/32/32/32, 0.1 s | 0/32/32/32, 1.7 s | 20 × unsat_rup_checked (both) |
| 16 | 32/32/32/32, 0.3 s | 29/32/32/32, 0.8 s | 1 × unsat_rup_checked |
| 32 | 8/32/32/32, 2.7 s | 0/25/32/32, 11.0 s | 1 × unsat_rup_checked |
| 48 | 0/21/32/32, 12.6 s | 0/0/31/32, 52.1 s | none needed (all scheduled claims underdetermined) |
| 64 | 0/9/32/32, 34.4 s | 0/0/6/26 (2 timeouts), 152 s | none needed |

Definite claims at these evidence sizes were rare at large n, so the common SAT cross-check (which dominates the
release cost when it is needed) was exercised mostly at n ≤ 32. RUP proofs were checked where produced; process
HMAC sealing is authentication only and is not counted as a proof. GEN-VE has no witness/workspace adapter, so its
release cost is not measured (its counts alone are not a releasable certificate).

## Findings

1. **Exact counting at h ≤ 2, k = 3 is easy for a competent generic method.** The independent explicit-domain VE
   counter matches D exactly and is **4–11× faster** than D's implementation at n = 32–64 (n = 64: 5.7 s vs 64 s for
   16 queries), using somewhat more memory. The closed-form Moebius schema count is not a computational advantage at
   k = 3, where each support has only 218 essential tables to enumerate; its asymptotic advantage is in `2^(2^k)`,
   which this benchmark does not reach.
2. **D beats the generic SAT workspace** (as in R4): at n = 64 D finishes all 128 queries; SAT 99/128 within 300 s and
   gives no counts above n = 10. This is a representation-vs-SAT result, not a result against counters.
3. **Workspace vs full release:** the release adds the common SAT cross-check; with D's workspace it stayed within
   1–2× of workspace time at these sizes because few claims were definite. The R4 "backend-only" speedup is not a
   gate speedup in general (T02 stands); here the gate cost was small only because the scheduled claims were mostly
   underdetermined.

**Scientific outcome: no detected advantage** for D's counting against a competent generic counter (it is slower);
advantage against SAT confirmed. The comparison against a knowledge compiler/projected #SAT tool remains
incomplete (D55).

## Resources

C offline CPU ≤ 1.87 h (upper bound, all attempts incl. v1 failures and v3). Within the 28 h allocation.
