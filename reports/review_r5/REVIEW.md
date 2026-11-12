# Independent review of R5 (`v0.5.0-dev`, content `b6aeab3`)

Reviewer: Claude Fable (replacing Codex as reviewer), 2026-11-11. Local repository, branch `iteration-5` at
`05be285`. This review did not use model calls. Evidence files are in this directory and `reports/development_r6/`.

## Decision

**Accept R5 as development evidence, with four findings that change its interpretation.** The engineering,
accounting and disclosure are sound and everything reproduces. The scientific reading of Track G is too negative in
one specific way: R5 did not test the sharing component of the method, and its "generic structured" comparator was
weak. Both are repaired in R6 (`reports/R6_GENERALIZATION.md`).

## What was reproduced

| Check | Result |
|---|---|
| `scripts/verify_artifacts.py artifacts/manifest_r5.json` | COMPLETE, 1,525 / 1,525 required files |
| Full test suite | 469 passed |
| Regenerated analyses vs `reports/development_r5/` (G, M, A-det, C, A-AI) | 5 / 5 byte-identical (`cmp`) |
| Stored G predictions recomputed after the R6 refactor of `r5/priors.py` | 4,992 / 4,992 identical (16 worlds, 3 budgets, all predictors) |
| External inventory regenerated | byte-identical to `artifacts/r5_source_manifest.json` |

Not reproduced: the 1,081 model calls (records inspected only) and the timing benchmark (not rerun).

## Findings

**R5-F1 (major, Track G scope). The method's sharing component was never tested.** The "full CGH prior" is
FLAT + TEMPLATE + MODULE without patches and without the dictionary mode (`s4/prior.py` docstring: excluded because
the exact sum "couples every node"). TEMPLATE and MODULE require an exact cyclic template or equal blocks, and the
R5 strata were deliberately built not to contain those. So the hierarchy had no support on the evaluation worlds:
the ablation `cgh_flat − cgh_prior` is +0.0004 at B = 16 and exactly 0.0000 [0, 0] at B = 24 and on the external
panel. That is a statement about this grammar, not about whether shared structure helps prediction.

**R5-F2 (major, comparator). GSR is close to a two-state switch, not a competitive structured prior.** Its
full-support component is uniform over H, whose per-mechanism mass is negligible next to any shared-rule program.
The posterior is therefore "a one- or two-table program if one fits, otherwise uniform". Evidence: calibration Brier
0.0872 for all three alphas, and on evaluation GSR equals uniform to four decimals in five of eight strata
(`R5_GENERALIZATION.md` per-stratum table). It satisfies the letter of the protocol; it does not support the
sentence "the hierarchical prior did not beat a generic structured prior" as a general conclusion.

**R5-F3 (medium, Track A design). The AI could not win, and the gate was not in the loop.** Exact EIG equals the
privileged oracle at four purchases (0.766 both), so the best possible AI result was a tie. The gate check is
applied after the episode (`r5/investigation.py`: a stop ends the episode; the verdict is checked afterwards), so a
rejected claim is never returned to the model. The primary therefore measures the models' unassisted stopping and
overclaiming, which is a valid and useful result, but it is not a test of an AI working inside a propose–check–revise
loop. Mistral's errors (18 premature stops with a correct "underdetermined" verdict) would not be changed by gate
feedback; Qwen's (138 unsupported definite claims) would.

**R5-F4 (minor, Track M wording). "Halves false verifications" rests on four worlds.** Recomputed from the run
records: 10 false verified answers in 8 worlds (current gate) against 5 in 4 worlds (challenge policy). The paired
difference per query is 0.0156, world-bootstrap 95 % interval [0.0031, 0.0312]. The false share among released
answers falls from 9.7 % to 6.3 %, difference 0.034 [−0.001, 0.076]: part of the reduction is fewer releases.
"Supported in scope" is acceptable; "safer at matched coverage" is not shown. I also tested whether a passive
description-length risk score over the enlarged class could flag the false answers without buying measurements
(development salt `r5-M-v1`, 40 worlds per panel): the four false answers had risk scores 0.012, 0.012, 0.051 and
0.124 against a median of 0.012 for correct ones. It does not separate them. Reducing this error needs measurements.

**R5-F5 (minor, Track C).** D is pure Python and GEN-VE is vectorised numpy, so "4–11× faster" is an
implementation comparison. The algorithmic conclusion (no advantage for the closed-form count at k = 3) is still
reasonable, because each support has only 218 essential tables. The external compiler remains unrun (D55).

**R5-F6 (minor).** `docs/R5_COUNTING_DERIVATION.md` §7 still says "benchmark pending" (disclosed).

## The ten review questions

1. *Held out?* The strata are structurally different from what CGH-1 encodes exactly, and were fixed before scoring.
   They are our generators. External transformations are honest and logged; clamping outside regulators to 0 makes
   many nodes constant.
2. *Selection on calibration only?* Yes. The structured comparator exists but is weak (F2).
3. *Declared prior and support retained?* Yes; one mass per distinct mechanism; literal/value convention tested.
4. *All results accounted for?* Yes: 320/320, 4, 159; bounds reported where 24 queries were refused at B = 8.
5. *Counting distinct mechanisms?* Yes for D and GEN-VE (0 mismatches in 640); the verdict CNF multiplicity trap is
   tested. GEN-VE is independent of `s4/mechspace.py`.
6. *Does an advantage survive full cost?* Against SAT yes; against a competent counter there is none.
7. *AI versus controller?* Worse, with the design caveat in F3. Backend arms received identical numbers.
8. *Public information only in M?* Yes. Benefit over the fixed enlarged class is real in coverage; see F4.
9. *Proof levels?* Stated correctly: RUP-checked where produced in C; solver assertion plus witness replay in M;
   HMAC described as authentication only.
10. *Budgets, labels, history?* Preserved. 1,081 / 3,072 requests; no freeze; older releases untouched.

## What this means for the direction

R5's recommendation was to stop pursuing a prior advantage and lead with assumption-aware verification. F1 and F2
say that recommendation was premature: the one mechanism by which a description-length prior can beat a flat code —
evidence about one node informing another through shared rules — had not been given a fair test. R6 builds that
test.
