# Iteration 13 — assignment to Claude Opus: the official template, an editable LaTeX source, the last wording fixes

Work in `/Users/alberto/Documents/projects/AI-security/AI-x-epistemics`, branch `sprint`, from the director's commit
that follows your `ceceeda`. Read `delegation/iteration_13/01_TEMPLATE_TEX_AND_LAST_FIXES.md` in full and
`DECISIONS.md` D132; your decisions continue from D133.

Iteration 12 is accepted: Appendix E, the programme paragraph, the theory of change, the references and the release
all check out. Alberto asks for two things and I add wording fixes. In one sentence each:

1. **Official template structure** (§1 of the plan; the template PDF is at
   `/Users/alberto/Downloads/Copy of Apart Research hackathon submission template.pdf`, copy it to
   `report/apart_official_template.pdf`): title between two rules with footnote 1 "Research conducted at the AI x
   Epistemics Research Sprint, November 2026" (linked), author over affiliation, **With** / Apart Research, centred
   Abstract in a narrower measure, Limitations and Future Work as sub-headings of §5, an **Author Contributions**
   paragraph (text in the plan), and an **LLM Usage Statement** as the last section (Appendix A keeps a pointer).
2. **Editable LaTeX source** (§2): `report/apart.latex` template; `build.sh` = pandoc → `report.tex` (committed)
   → xelatex → PDF, with `--from-tex` to rebuild from a hand-edited `report.tex`; `report/check_tex.py` enforces
   that the numeric tokens of `report.tex` equal those of `report.md`; README says how to rebuild both ways.
3. **Wording fixes** (§3): Levin's coding theorem for prefix complexity (cite Li & Vitányi 2008 only if
   doi:10.1007/978-0-387-49820-1 resolves on Crossref, else qualitative); Wolfram "in his terms"; the V(D) product
   form "because every evidence row is a single synchronous step", Tier H "per-node enumeration".
4. **Nothing else moves:** data, lock, Tables 1–12, frozen tally; main text ends on page 8; abstract 150–250.
5. **Housekeeping** (§4): `REVIEW_READY_SPRINT.md` hashes; manifest, asset, tag moved to the final commit; archive
   scan before upload, repo scan before push; `PREEXISTING_WORK.md`; D133+.

Return by **12:30 CST**: final commit, tag, asset and PDF hashes, main-text end page, abstract words, confirmation
that the `.tex` route and the markdown route give the same PDF text, and the one template element you could not
match. Do not stop to ask routine questions.
