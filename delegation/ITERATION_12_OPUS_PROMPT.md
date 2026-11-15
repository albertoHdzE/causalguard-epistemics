# Iteration 12 — assignment to Claude Opus: the framing (Appendix E, Figure 4, theory of change) and the final build

Work in `/Users/alberto/Documents/projects/AI-security/AI-x-epistemics`, branch `sprint`, from the director's commit
that follows `7c659ab`. This supersedes iteration 11; its cosmetic pass is item 7 below. Read
`delegation/iteration_12/01_FRAMING_APPENDIX_E.md` in full, `DECISIONS.md` D127, and
`docs/S4_FOUNDATIONS_AND_PRECOMMIT_CHECKING.md` §"Research identity" and `docs/CODEC.md` §"Accounting and claims"
(they fix what may be said). Your decisions continue from D128.

Alberto's request, after the organisers' briefing: the judges weigh the way of thinking as much as the result. The
paper must say where the benchmark comes from — a programme of algorithmic modelling (short executable rules,
evidence-consistent mechanism sets, exact consequences), with its lineage in algorithmic information theory,
Wolfram's short rules, Zenil et al.'s algorithmic causal deconvolution and the author's 2021 chapter with that
group — in the register of a Nature main text: short, plain, one figure, the heavy material in Appendix E.

In one sentence each:

1. **Register is binding (§0 of the plan):** upper bounds on Kolmogorov complexity, never "approximation of
   Kolmogorov complexity"; no universal algorithmic probability measured; biology is Zenil et al.'s, cited; the
   sprint result does not depend on the compression work; pre-sprint evidence with label, interval, tag, both signs.
2. **Main text (M1–M6):** abstract clause; a third introduction paragraph "Where the benchmark comes from" (≈130
   words); one Methods sentence on the symbolic engines; a theory-of-change paragraph in §5 (≈70 words); trims in
   Related Work, 4.3 and 4.4 so the main text still ends on page 8.
3. **Appendix E** (≈1 page): E.1 short rules, rich behaviour with **Figure 4** computed from repository objects
   (Rule 110 fixture; the worked-example world's eight truth tables against its 256-state behaviour; bit counts in
   the caption through `fill.py`); E.2 description length and algorithmic probability, what we do not claim, the two
   pre-sprint figures wired from committed analysis JSON (or cited by release and file if no JSON holds them);
   E.3 symbolic computation in this work and what each piece gave the sprint; E.4 lineage and status, "under
   construction" in those words.
4. **References (§3 of the plan):** every one resolved (DOI or arXiv) and recorded in
   `docs/SPRINT_RELATED_WORK.md`; a fabricated reference disqualifies.
5. **Nothing else moves:** lock, data, scores, Tables 1–12, frozen tally; no new run.
6. **Build:** `fill.py` passes; regenerate twice byte-identical; abstract 150–250; main text ends on page 8.
7. **Iteration 11 pass:** widen the model column of Tables 1, 2 and 5 so no model name wraps.
8. **Release:** regenerate `artifacts/manifest_sprint.json`, rebuild and re-upload the asset, move tag
   `v0.8.0-sprint` to the final commit, archive scan before upload, repo scan before push; `PREEXISTING_WORK.md`
   rows; D128+ records.

Return by **13:00 CST**: final commit, tag, asset and PDF hashes, page count, abstract word count, the added
references with their identifiers, and the three sentences of Appendix E you are least sure are true. Do not stop
to ask routine questions.
