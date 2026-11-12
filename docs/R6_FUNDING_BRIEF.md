# CausalGuard: R6 funding brief (development evidence; two pages)

## What R6 adds to R5
R5 showed that weighting compatible mechanisms by description length beats uniform averaging. It also showed that our hand-built hierarchical prior added nothing over a good generic code. R6 tested a different kind of prior, **a dictionary of rule types shared across the network**, in three settings:
- exactly, at n = 8 (XDC);
- as a learned, certified approximation on published models up to 64 nodes (XDC-EB);
- with the exact gate placed inside an AI investigator's loop.

All results are development evidence. There was no confirmatory run and no freeze. Intervals are 95% source-group cluster bootstraps.

## What R6 demonstrated

| Question | Result |
|---|---|
| Is XDC computed correctly? | **Yes.** An independent oracle that shares no code with XDC matches it to 2.9e-12 on 216 cases. A planted defect fails the oracle. |
| Does sharing rule types across nodes forecast better than the best flat code? (synthetic, n = 8) | **Yes, where rules repeat.** +0.0149 Brier [0.0088, 0.0211] on 320 held-out worlds. The whole gain sits in the four strata built with rule reuse (+0.042). Elsewhere it is **adverse** (−0.012). The median world gains about 0. |
| Same question, fresh fragments of published models, n = 8 | **Small positive.** +0.0033 [0.0012, 0.0055] at 16 observations. The sharing part alone is not separable from 0. |
| Same question at 24 nodes with a learned dictionary (XDC-EB) | **Small positive.** +0.0087 [0.0037, 0.0148] on 28 held-out publication lineages, at a small evidence budget (8 observations). Null on whole published models (13 worlds) and at larger budgets. It does not grow with n and does not track rule reuse. |
| Is the learned dictionary tractable and certified? | **Yes.** All 227,280 fits carry an optimality certificate (≤ 1e-6 nats). Median cost per world is under 0.5 s up to 64 nodes. Exact XDC is limited to n ≤ 12. |
| How much does the approximation lose? | At n = 12, nothing measurable at 8–16 observations. About half of exact XDC's gain at 4 observations. Not measurable above n = 12. |
| Does feeding the gate's rejections back to an AI help? | **It stops a weak model's overclaiming** (Qwen 7B: unsupported definite claims at budget 4 fell from 15 to 2 of 32 worlds). **It does not make the model a better investigator** (resolved@4 +1 world; still 0.38 below the exact controller). No effect on a stronger model (Mistral 24B), which never overclaimed. |

## What this means
- Dictionary sharing is a real but **conditional** inductive bias. It pays where mechanisms reuse rules and costs where they do not. On published models the net effect so far is about 0.003–0.009 Brier at low budgets: honest, small, and not yet shown to transfer to unseen sources. Every published-model lineage we evaluated had also contributed 8-node fragments earlier.
- The exact gate is most useful as a **guard on AI output** (it turns unsupported certainty into honest uncertainty), not as a coach.

## Open risks
- Synthetic generators and clamped fragments of one public corpus (Biodivine, 314b2fed).
- Indegree ≤ 3; one-step evidence; h = 1 at scale.
- No held-out-source test at scale.
- The dictionary gain is bounded above by how much rules repeat, and the published corpus has few large models (13 intact lineages in range).
- Independent review of R6 is pending.

## Next milestone (costed; one study, to be authorised independently)
**A held-out-source test of dictionary priors with an adaptive concentration.**
- Fix the B = 4 approximation loss by fitting XDC-EB's concentration (a θ-mixture over the fitted dictionary). Certify the fit as now.
- Extend the corpus with a second public source of Boolean models (for example GINsim or Cell Collective exports) so that evaluation lineages are unseen at every size.
- Pre-register: primary flat − method at a low budget on unseen-source models of 16–64 nodes, at least 20 groups. Secondary: a dose-response with non-constant rule reuse.
- Cost: about 2 person-weeks of engineering, ≤ 60 CPU-hours, no model calls.
- **Negative path:** if the held-out-source primary is null, report dictionary sharing as a synthetic-only bias. Publish XDC-EB as a certified, cheap forecaster together with its measured per-stratum gains and losses.
