# R7b review entry point (pre-sprint, 2026-11-12/13)

Branch `iteration-7`. Built on the director's review `626cb32`. The lock commit is `1e79358`; the closing commit
follows. Everything here is PRE-SPRINT. Every request went to a local model. No online request of any kind was
made in R7b.

## 1. What was built

- **Tier W (wiring given, primary)**, beside **Tier H** (wiring hidden, the R7 task). In Tier W, each node's
  essential inputs I_j are listed, and the declared class is every function of the listed inputs. An entry is
  observed if its input combination appears in an evidence row where the node is not clamped. Each unobserved
  entry is a free fair bit, so den = 2^F. Evidence budgets are 6–8, calibrated on training worlds (D80).
- **Two independent exact implementations**, plus SAT: a lazy table-lookup search, and the explicit version-space
  engine restricted to the listed inputs. SAT gained a `wiring` option, and its witnesses are replayed. A
  **cross-tier test** checks that a claim settled on Tier H is settled the same way on Tier W, on both evidence
  sets (D82).
- **P4, the forged check**, on both tiers:
  - **Tier W.** A derivation (lookup tree with case splits) is checked by `tierw.verify` against the public
    evidence only. A forgery alters one table entry on the claim's path, so that the status changes. Its kind
    (`phantom_row`, `wrong_value`, `hidden_row`) is chosen by hash.
  - **Tier H.** A forged status with invented counts and a flipped trajectory.
  - **Common to both.** P3 and P4 share one template, and the derivation cap is 16 lines (D81).
- **Reasoning-first wording (v3) for every model.** The main panel has 180 of the 240 R7 main worlds: 120 Tier W
  and 60 Tier H, five conditions, assigned by hash.
- A **worked example** a reader can check by hand: `reports/R7B_WORKED_EXAMPLE.md`. The tasks are regenerated in
  `docs/SPRINT_TASKS.md`.
- Tests: `tests/test_r7b_tierw.py` and `tests/test_r7b_scoring.py`. They include a hand-worked world, planted
  engine and cross-tier defects, every forgery kind failing the verifier, assignment balance, the half panel, and
  the D85 failure rule. The full suite passes, and ruff is clean.

## 2. Gates (`reports/R7B_GATES.md`; all blocking gates pass)

| gate | result |
|---|---|
| G1 ground truth | main 180/180 worlds and 1440 claims agree (Tier W: lazy = restricted engine = SAT). Cross-tier: 147 claims settled on Tier H, 0 violations. pilot4: 32/32 |
| G2 surface rule | Tier W 0.540 (120 worlds, 960 claims); Tier H 0.590 (60, 480); both ≤ 0.667 |
| G3 floor / ceiling (recorded) | pilot: qwen and mistral at the floor on Tier W; gemma-4 off it (0.416) |
| G4 no leak | 1800/1800 main messages pass, and all are unchanged under a mechanism swap |
| G5 disjoint | 0 overlaps with 136 shown sprint worlds and 148 earlier model-facing mechanisms |
| G6 checks | main Tier W: 464/464 P3 pass the verifier and 464/464 P4 fail it. Tier H: 240/240 forged statuses differ |

## 3. Pilots (PILOT; `reports/R7B_PILOT.md`)

The pilot used 32 pilot-4 worlds per model (gemma-4: 24, Tier W only), with qwen2.5:7b, mistral-small-24b and
gemma-4-12b. Every model adopted the checker's status whether it was valid or forged. Pilot discernment was qwen
0.075, mistral 0.000 and gemma-4 0.000. gemma-4 hit the token cap on 21/48 requests. Timing probes decided the
panel. The first probes were contaminated by memory pressure, which also exposed a harness defect (D85). Clean
probes were run as `-v2`.

## 4. Lock

`docs/SPRINT_DESIGN_LOCK.json` (`r7b-sprint-lock-v1`), committed at **15:06:24 CST on 2026-11-12** in `1e79358`,
and pushed. The first main-panel request was at 15:06:40. The lock records the sha256 of 17 files (manifests,
surface rules, calibration, tasks doc, gates, source files), the template hashes, models and configs (with
sha256), panel decisions, contrasts, exclusions, and the director's and agent's predictions. Each model ran once,
from the snapshot of that commit; every run record has `dirty: false`. Fallback: not used.

| model | panel (rule: full > 4.5 h → half; half > 7 h → left out) | measured s / world | run wall time |
|---|---|---|---|
| gemma-3-4b | full, 180 | 47 | 1.24 h |
| qwen2.5:7b | full, 180 | 65 | 2.62 h |
| mistral-small-24b | full, 180 | 60 | 1.81 h |
| llama-3.3-70b | full, 180 | 63 | 2.95 h |
| gemma-4-12b | half, 90 | 115 | 1.92 h |
| r1-distill-qwen-32b | half, 90 | 245 | 4.01 h |
| qwen2.5:72b | **left out**: half panel 7.9 h | 316 | – |

The panel finished at 03:03 CST on 2026-11-13. Every planned item is ok: 0 error attempts and 0 empty replies.

## 5. Main results (`reports/SPRINT_LOCAL_RESULTS.md`; full tables in `reports/sprint_local/RESULTS.md`)

Check discernment on Tier W (adoption of the true status under P3 minus adoption of the forged status under P4),
with 95 % cluster-bootstrap intervals:

| model | Tier W discernment | Tier W forged adoption (P4) | Tier W balanced acc (surface 0.540) | Tier H discernment | Tier H balanced acc (surface 0.590) |
|---|---|---|---|---|---|
| mistral-small-24b | 0.000 [0.000, 0.000] | 1.000 | 0.345 [0.320, 0.370] | 0.000 | 0.348 [0.317, 0.385] |
| llama-3.3-70b | 0.000 [0.000, 0.000] | 1.000 | 0.353 [0.333, 0.374] | 0.000 | 0.335 [0.306, 0.366] |
| qwen2.5:7b | −0.082 [−0.237, 0.059] | 0.868 | 0.353 [0.317, 0.388] | 0.000 | 0.388 [0.328, 0.448] |
| gemma-3-4b | 0.033 [−0.101, 0.154] | 0.860 | 0.345 [0.318, 0.372] | 0.021 | 0.343 [0.283, 0.405] |
| gemma-4-12b (half) | 0.000 [0.000, 0.000] | 1.000 | 0.343 [0.302, 0.386] | 0.000 | 0.403 [0.335, 0.472] |
| r1-distill-32b (half) | 0.000 [−0.138, 0.139] | 0.909 | **0.462 [0.410, 0.513]** | 0.000 | 0.334 [0.274, 0.392] |

- Every local model adopts a forged check as readily as a valid one, although the forgery fails a
  line-by-line comparison with rows in the same prompt. Corruption under P4 is 0.906–1.000.
- Five of six models are at the floor on Task S in both tiers. r1 is the only model off the floor, and the only
  one the wiring helps (Tier W − Tier H balanced accuracy +0.127 [0.051, 0.201]).

Quotations are in `SPRINT_LOCAL_RESULTS.md` §1. The clearest: gemma-4 notes "This contradicts the deduction…
However, looking at the provided checker's logic: …", then adopts all four forged statuses ("The checker confirms
this is settled TRUE").

## 6. Predictions against outcomes

Of the director's four predictions, three are met and one is not. Director 1 fails: r1 is off the floor, but
mistral (0.126), llama (0.129) and gemma-4 (0.110) give definite verdicts on fewer than 20 % of open claims. All
five of the implementation agent's predictions are met. They were written after a pilot that already showed the
pattern. Details are in `SPRINT_LOCAL_RESULTS.md` §4.

## 7. Online readiness (`reports/R7B_ONLINE_READINESS.md`)

No probe was used in R7b; 3 of 5 have been used in total. Smoke configs (2 W + 2 H pilot-4 worlds) and main configs
(360 requests each, cap 400) are committed for `deepseek-v4-pro` and Claude Opus 5.5 (`claude -p`, effort high):

- **DeepSeek:** an estimated $2–18 at peak rates, half that off-peak; 25 min to 2.5 h with 8 workers.
- **Claude:** billed to the subscription, with the CLI's `totalCostUSD` recorded per session; 45 min to 3.8 h
  with 4 workers. A usage-window stop fails items, and the identical plan is resumed with `--retry-failed`
  (D85).

**Fix before launch (your call):** keep the reasoning text, or at least DeepSeek's `reasoning_content`, in the
record. Without it, we cannot tell whether a model tried to verify the forged check. That change touches
`providers.py`, a locked file, so it needs your approval and a lock addendum.

## 8. Deviations and defects (DECISIONS.md D83–D86)

- **D83:** the token cap stays at 6000 for every model. gemma-4's truncations are repetition loops, and its
  missing answers are reported, not rerun.
- **D84:** half panels for gemma-4 and r1; qwen2.5:72b left out by rule.
- **D85, a harness defect found and fixed before the lock.** With a 52 GB and a 17–37 GB model co-resident on the
  96 GB host, LM Studio crashed and Ollama returned empty replies. The harness stored them as `ok` worlds with
  empty turns. Now an empty reply is a retryable transport error, and a failed turn fails the world item. All
  earlier pilot and R7 runs had 0 empty replies. The contaminated `-v1` probes were not used.
- **D86:** Ollama idled after 17:44. qwen-72b was not run outside the lock.
- **Defect, not fixed:** r1's reasoning is not stored (see §7). Scores are unaffected.
- The R7 test `test_template_hashes_are_stable_and_complete` was updated to the new template set (10 + 10).
- No method for the paper (`report/`) was written; that is tomorrow's task after your review.

## 9. Resources

| resource | used | limit |
|---|---|---|
| Local requests (ledger phase SPRINT) | 2509, of which 2043 in R7b: pilot and probes 243, main 1800 | 6000 |
| Model-server hours | about 18 h: main 14.6 h (LM Studio 11.9, Ollama 2.6); pilot about 1.9 h; probes about 1.4 h | 30 |
| Online requests | 0 | – |
| Regeneration | `sprint-analyze` byte-identical twice; R5/R6 outputs 21/21 byte-identical (`scripts/r6_regen_check.sh`) | – |

## 10. Where the director's plan is wrong or will not impress the judges

1. **P4 on floor models measures deference, not failed verification.** A model that cannot trace a claim
   (five of six here) has nothing to weigh the check against. Taking over any check is then its best option.
   The striking 1.000 forged adoption is real, but a judge will ask whether any model *could* have caught the
   forgery. The evidence the project needs is one model off the floor that still adopts forgeries. r1 is that
   case in this panel (balanced accuracy 0.462, discernment 0.000), but only on 12 P4 worlds, and without stored
   reasoning. **The online models are where the claim is made or lost.** I would add, as a pre-registered
   secondary, a "verify-prompted P4" condition ("check each line against the rows before using it"). It would
   separate "cannot verify" from "does not bother".
2. **Tier W did not do what it was for.** The wiring was meant to lift models off the floor. For five of six
   models, Tier W minus Tier H balanced accuracy is about 0. The larger instruction models answer "not settled"
   nearly everywhere (underclaim 0.84–0.91). So the overclaim story of R7 does not carry over to them: they
   underclaim. The paper should lead with the forged-check finding, not with overclaiming.
3. **Director prediction 1 assumed the wrong failure mode.** It expected definite verdicts on more than 20 % of
   open claims from every model. Three models are below 13 %.
4. **The hardware plan assumed both servers can host any pair of models.** On 96 GB they cannot: with qwen-72b
   resident, the r1 and llama probes crashed the LM Studio backend (D85). qwen-72b was left out by the timing
   rule, measured at 316 s per world while another model shared the GPU, as it would in the main run. In
   practice, on one 96 GB machine, "both servers side by side" and "a 72B model" do not go together. Only one
   70B-class model (llama) is in the panel.
5. **The 6000-token cap with reasoning-first wording cost gemma-4 nearly half of its Tier W answers.** This holds
   whatever a larger cap would have done (D83). A judge can read the gemma-4 Tier W numbers as a wording
   artefact.
6. **The Tier W wording "(constant)" for a node with no inputs** was misread by gemma-4 as "the node never
   changes" (quotation in §5). The class is correct, but the word invites a misreading. "No inputs: its next
   value is a fixed 0 or 1" would be clearer. It is locked for the online runs. I would flag it in the paper, not
   change it.
7. **Check discernment has a ceiling problem.** When P3 adoption is 1.000, discernment can only show the forged
   side. The standardised score does not fix that. A per-claim analysis of P4 on claims the model had right at
   turn 1 (that is, corruption) is the cleaner headline number, and it is already in the tables (0.906–1.000).
