# S3 — bounded future-design proposal (iteration 3; proposal only)

Status: **proposal, not authorized, not run.** No model was called for this note. S3 stays exploratory in the
present handoff; the R2 review (R2-07..R2-09) asked only for offline corrections plus this note. Nothing here
changes the saved S3 records, the original focus estimate (−0.08 [−0.16, 0.00], qwen2.5:7b held-out, 100 worlds) or
the S1/S2 freeze path.

## Why the current target task cannot be reused as is

The generator `s3_tasks.make_s3_items_v2` sets both the evidence budget `S3_BUDGETS[index % 3]` and the requested
target verdict `VERDICT_LABELS[index % 3]` from the same world index. Budget alone therefore names the requested
target verdict: B3→entailed, B5→refuted, B8→underdetermined. On the saved items:

| panel | design-known budget rule (not fitted) | role-specific surface rule (fitted on 300 training worlds) | pooled surface rule (R2) | majority |
|---|---|---|---|---|
| qwen held-out, 100 targets | 80/100 | 79/100 | 47/100 | 29/100 |
| qwen diagnostic, 20 targets | 18/20 | 18/20 | 11/20 | 4/20 |
| gemma diagnostic, 20 targets | 18/20 | 18/20 | 11/20 | 4/20 |

(Source: `reports/development_r3/s3_v2_summary.json`, `before_after_audit.json`.) The target probes' realized
accuracies were 0.33–0.41. A label-free reader of public design features does far better than any probe, so the
target task measures little beyond the budget coupling. This does not change the paired T_cert − T_label difference
arithmetically, but it weakens what that difference can mean.

## Proposed changes (all fixed before any future call)

1. **Independent target verdicts.** Draw the requested target verdict from its own stream, independent of world
   index, budget, horizon, intervention kind and target value. Counterbalance it within each (budget × horizon ×
   kind) cell, using a fixed Latin-square allocation over world blocks. Report every realized feasibility shortfall
   by cell. Do not resample worlds to hide a shortfall.
2. **Semantic novelty audit before release of a panel.** Canonicalize each point claim by its effective initial
   state (after initial edits and clamp initial values), horizon, target node and persistent clamps. Compare the
   target value separately. Then:
   - reject a target that repeats the source claim, and redraw it from the design stream with the redraw logged;
   - label complements (same claim, opposite target value) separately rather than counting them as fresh;
   - publish the audit with the panel.
   Held-out world 2 of the R2 panel (identical claim after a no-op edit of x1 to its existing value) is the
   motivating case.
3. **Baselines scored on the identical items, persisted before calls:**
   - majority;
   - pooled surface rule;
   - role-specific surface rules fitted on training worlds only;
   - the design-known allocation rule for whatever coupling remains.
   A gate requires the design-known and role-specific rules to stay at or below a declared ceiling on the
   training/diagnostic items (proposal: within 0.10 of the majority baseline on target items). Otherwise the
   generator is revised before any model call.
4. **Separating label, assurance and mechanism.** The R2 certificate prompt combined verbal solver assurance with
   mechanistic material. Proposed arms, crossed with the existing matched self-critique turn:
   - label only;
   - label + equal verbal assurance;
   - label + valid mechanistic certificate;
   - optionally, an invalid-mechanism control at equal length.
   Prompt lengths are reported, and context length is matched where feasible.
5. **Coherence.** Use the parser's single rule (`llm.parse.verdict_vector_coherent`: the verdict's probability
   equals the vector maximum, and ties count as coherent but are reported). Report direct-response contradictions and
   post-aggregation C disagreements as separate quantities, each with valid-vector denominators. Brier stays a score
   of supplied vectors, not a calibration claim.
6. **Wording carried forward:**
   - "balanced accuracy" and "accuracy" are always labelled;
   - observation inputs are exogenous, while oracle-balanced query selection is outcome-stratified and is not called
     exogenous;
   - gates chosen after partial inspection are labelled as such.

## Fixed diagnostic gate (to be frozen with the design, before any future call)

- **G0 (offline):** the generator audit passes items 1–3 on 300 training worlds and 20 diagnostic worlds, with
  shortfalls reported.
- **G1:** 0 runner failures; truncation ≤ 2 %; every arm's valid-verdict rate ≥ 0.90 on a 20-world diagnostic.
- **G2:** the valid-mechanism arm beats arm A on balanced items by ≥ 0.20 balanced accuracy. This checks that the
  certificate content is usable; it is not evidence of transfer.
- **G3:** arm A balanced accuracy ≥ 0.383 (above chance plus margin, as in D29).
- A failed gate stops expansion for that model. The stop is reported as a scope reduction.
- No held-out panel is drawn until all gates pass. Gate values are not tuned after seeing diagnostic outcomes.

This is a new development design. It would need its own review before any calls, and it is not part of the S1/S2
freeze.
