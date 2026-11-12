# R6 scientific contract

Status: prospective DEVELOPMENT assignment, 2026-11-11, written by the reviewer/director (Claude Fable). It follows
the independent R5 review (`reports/review_r5/REVIEW.md`). R5 records, endpoints and findings stay intact.

## 1. Where the programme stands

Alberto's question: can our compact algorithmic representation of possible mechanisms help an AI infer unseen
facts, recognise uncertainty, and check claims before relying on them?

After R5 the evidence was: exact checking works and blocks every unsupported AI claim; description-length weighting
beats uniform averaging; but the CGH-1 prior did not beat a flat generic code, the counter is not faster than a
competent generic counter, and the AI was a worse investigator than exact EIG.

The R5 review found the prior comparison had not tested the one mechanism by which a description-length prior can
beat a flat code: **evidence about one node informing another through shared rules**. The dictionary mode was
excluded from the prior because nobody had an exact sum for it, and the TEMPLATE/MODULE grammar has no support on
imperfect structure.

The reviewer then wrote **XDC**, an exchangeable dictionary code with an exact sum (definition and disclosures in
`docs/R6_PROTOCOL.md`; code in `src/causalguard/r5/priors.py::XDC`). On calibration it beat the R5 champion by
+0.036 Brier [0.018, 0.055] at 16 observations, concentrated in worlds whose nodes share one or two rule types. On
the external development panel (8-node clamped subnetworks of published models) it gave +0.002 [−0.002, 0.006] at
16 observations and +0.019 [0.012, 0.027] at 8. A design lock was committed and two fresh evaluations were launched
before this assignment was written.

**The reviewer wrote that code and cannot be its independent auditor. You are.** Treat XDC as untrusted until you
have re-derived and re-tested it.

## 2. The argument R6 must test, link by link

1. **Is XDC correct?** (audit, Track X)
2. **Does exact sharing improve unseen prediction on fresh worlds and on published models at n = 8?** (locked
   evaluations, Track G6 — analysis only, the runs exist)
3. **Does the gain survive at the scale and shape of real models?** The n = 8 external panel clamps every outside
   regulator to 0, which turns many nodes into constants and leaves little to predict. Published models have tens of
   nodes. A sharing prior learns its dictionary from the other nodes, so it should gain more as n grows — or it does
   not, and the n = 8 synthetic gain is a generator artefact. (Track S — the decisive new experiment)
4. **Does the AI benefit when the gate is actually in the loop?** (Track A2 — bounded repair pilot for R5-F3)

Each link has its own comparator and can fail on its own. Do not combine them into one success rate.

## 3. Track X — independent audit of XDC

Required, before you rely on any XDC number:

- Re-derive the prior from the generative description in `docs/R6_PROTOCOL.md` and write the derivation in
  `docs/R6_XDC_DERIVATION.md`: normalisation, the push-forward to distinct mechanisms, why theta = infinity is the
  base code, the set-partition recursion, the two-step (h = 2) pointwise-in-intermediate-state argument, clamps and
  initial edits, and float error.
- Write an oracle that shares **no code** with `XDC`, `GSR` or `xdc_bruteforce` (for example: enumerate every
  mechanism in a tiny class, compute its prior mass directly from the definition by summing over seatings in closed
  form, then condition). Compare on at least 200 random (evidence, query) cases across n in {3, 4}, k in {1, 2},
  both horizons, all three intervention kinds, at least three theta values and the mixture. Report the largest
  absolute difference and the number of cases.
- Check that the prior sums to 1 over the whole class for a tiny case, and that relabelling nodes leaves every
  forecast unchanged (exchangeability), on at least 50 random cases.
- Check the order of events against git: the lock commit precedes every evaluation attempt; the snapshot the runs
  executed from is the lock commit; no predictor code changed after it.
- Negative control: plant a deliberate error in a copy of the recursion (for example drop the (|b|−1)! factor) and
  show your oracle test fails.

If the audit finds a defect that changes forecasts: stop relying on the existing R6 runs, record the defect, fix it,
and rerun calibration and both evaluations as `-v2` on **new** salts (`r6-G-eval-v2`, external design salt
`r6-G-design-ext-v2`). Keep the v1 records. The fresh external groups cannot be made fresh again; say so.

## 4. Track G6 — the locked n = 8 evaluations (analysis and report only)

Runs `r6-g-eval-v1` (320 fresh synthetic worlds) and `r6-g-ext-fresh-v1` (449 instances from the 122 source groups
R5 never used) were launched from the lock commit. Verify they completed (resume them with the same command and
snapshot if they did not). Analyse with the locked command:

```sh
python -m causalguard analyze-r5 --track g-r6 --run runs/r6-g-eval-v1 --champion gate --out reports/development_r6/g_evaluation.json
python -m causalguard analyze-r5 --track g-r6 --external --run runs/r6-g-ext-fresh-v1 --champion gate --out reports/development_r6/g_external_fresh.json
scripts/r6_figures.py runs/r6-g-eval-v1 gate "xdc[cgh_flat]" reports/development_r6/fig_g_evaluation.png
scripts/r6_figures.py runs/r6-g-ext-fresh-v1 gate "xdc[cgh_flat]" reports/development_r6/fig_g_external_fresh.png --external
```

Report the primary and every prespecified secondary exactly as the lock defines them, against the predictions
recorded in the lock. Additional required reporting, because the calibration effect is heavy-tailed:

- the distribution of per-world differences (median, quartiles, share of worlds better/worse), not only the mean;
- the effect with the two sharing-rich strata removed, labelled post hoc;
- the effect by hidden rule reuse;
- calibration/reliability of XDC on underdetermined queries;
- the uniform-H stratum as the null: state its sign and size plainly.

Do not tune anything on these runs. Do not add strata, drop strata or change theta.

## 5. Track S — sharing at the scale of published models (the main new experiment)

### S1. What has to be built

XDC's exact sum costs about 3^n and stops near n = 14. Build a version that scales:

**XDC-EB (learned dictionary, exact given the dictionary).** Node rules are independent draws from a mixture over
rule types with weights p; within a type, concrete rules are drawn in proportion to the base code as in XDC. p is
fitted on the **public evidence only** by maximising the marginal likelihood
`prod_j sum_type p_type * u_j(type)`, where `u_j(type)` is the base-code mass of node j's evidence-compatible rules
of that type. This objective is concave in p, so the optimum is unique and can be certified: report a duality gap
or KKT residual for every fit. Use a fixed, declared regulariser toward the base code (for example a Dirichlet
pseudo-count; choose it on calibration only, from at most three values) and say what it costs. Forecasts for a
target node may use either the full-evidence fit or a leave-target-out fit; choose on calibration and lock it.

This is the "learned dictionary" secondary that the R5 protocol permitted, promoted to a main arm. It is an
approximation to XDC, not the same prior. At n = 8 report XDC-EB beside exact XDC on the calibration worlds so the
cost of the approximation is visible.

**Scale through our representation.** At n above about 12 the dense tables of `candidate_class` do not fit. The
per-node compatible sets must come from the support-schema representation (`s4/mechspace.py`) or an equivalent
sparse enumeration over supports that touches only observed and queried states. This is where the compact
representation earns its place: say clearly which part of the computation it makes feasible, and measure it.
One-step (h = 1) queries only at large n; state that restriction.

### S2. Populations

- **External intact panel (primary population).** Inventory every Biodivine model (pinned commit
  `314b2fed94689c38d3aaaf8101ed622b3501c7f7`) with 9 ≤ n ≤ 64 and every node of indegree ≤ 3 after the declared
  closing of free inputs. No clamping. Log every inclusion and exclusion. If at least 20 source groups are eligible,
  this is the primary population.
- **External large-subnetwork panel (fallback and secondary).** If fewer than 20 intact groups are eligible, or in
  any case as a secondary: backward subnetworks of n = 24 nodes by the R5 procedure, with the fraction of clamped
  regulators recorded per instance. Use only source groups, and report the clamped fraction as a covariate.
- **Split by source group before looking at anything:** a fixed hash ordering assigns one quarter of the eligible
  groups to calibration and three quarters to evaluation. Groups already used in R5 or R6 n = 8 panels may appear
  (the n = 8 instances were 8-node fragments), but say so and report the result with and without them.
- **Synthetic scale panel (secondary).** The R5 generators do not take n as a parameter. Do not rewrite them to
  manufacture a win. If you add a scaled synthetic panel, it needs a written population spec committed before any
  score, and it stays secondary.

Evidence: nested budgets of one-step observations, sized on calibration so that the flat code is neither at ceiling
nor at chance (a starting point is n, 2n and 4n observations). Eight novel h = 1 queries per world, chosen without
target answers, by the R5 design rules.

### S3. Endpoint and comparators

Primary: `Brier(best flat code) − Brier(XDC-EB over the same base)` at the middle budget, on the evaluation groups
of the primary population, source-group cluster bootstrap. "Best flat code" is chosen on the calibration groups
from {gate, cgh_flat, circuit, index} by mean Brier with a fixed tie order, and locked. Also report uniform, GSR
where it is computable, and exact XDC wherever n ≤ 12 allows.

Required attribution: sharing (flat base − XDC-EB on that base); vocabulary (XDC-EB[gate] − XDC-EB[cgh_flat]);
effect against n; effect against hidden rule reuse; effect against budget. Missing predictions get Brier bounds in
[0, 1]; a predictive claim must survive them.

Lock `docs/R6S_DESIGN_LOCK.json` before any evaluation-group score. Record predictions in the lock.

### S4. What each outcome means

- Positive on intact published models, growing with n: the sharing prior generalises beyond our generators and the
  compact representation is what makes it computable. That is the result the programme was looking for; recommend a
  confirmatory study on a second, independently curated model repository.
- Positive only on synthetic worlds: sharing works where rules are reused, and published models at this class do
  not reuse them enough. Report the reuse statistics of published models as the explanation, and stop marketing a
  prior advantage.
- Null everywhere at scale: the n = 8 gain was a small-n artefact. Say so.

## 6. Track A2 — the gate in the loop (bounded repair pilot for R5-F3)

In R5 the gate checked the AI's verdict after the episode ended. Add the loop: when the model stops with a definite
verdict that the gate rejects, and purchases and request attempts remain, return the rejection ("checked and
rejected: the evidence does not determine the target; n purchases left") and continue the episode. A stop with the
verdict "underdetermined" is a true statement and is not rejected; do not force the model to keep buying.

- Fresh diagnostic worlds only (new salt, 32 worlds, four per stratum), both R5 models, both backends, the same
  prompt v2 plus the rejection message. Request ceiling: the R5 repair allocation of **512**, inside the unchanged
  global 3,072 (1,081 used). Count every attempt.
- Run the R5 no-feedback harness on the same 32 worlds as the paired control, inside the same 512.
- Primary: resolved@4 with the loop minus without, paired by world, per model. Secondary: against EIG on the same
  worlds; unsupported definite claims; purchases; attempts.
- This is a pilot. A model that stops early with a correct "underdetermined" is not helped by the loop; report that
  separately from overclaiming.
- If 512 requests cannot cover both models and both arms with the control, drop the generic backend arm first
  (R5 showed the backends give the AI identical numbers) and say so.

## 7. Discipline

Everything in the R5 contract §2 and §7 still applies: public inputs only, calibration separate from evaluation,
locks before evaluation scores, immutable records, no successful-world filtering, failures preserved, no repeated
revisions to make our method win. A negative result that is complete is a successful delivery.

No confirmatory run, no freeze, no paid inference, no weight changes. Offline ceiling for R6: 48 CPU-hours, four
workers, the R5 memory rule. Model-server ceiling for A2: 3 hours.
