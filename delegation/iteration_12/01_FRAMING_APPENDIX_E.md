# Iteration 12 — the intellectual framing: algorithmic modelling, causal deconvolution and symbolic computation (director, Sunday 15 Nov 2026, 08:45 CST)

Supersedes iteration 11 (its cosmetic pass is folded in as item 7). Requested by Alberto after the organisers'
briefing: the judges weigh the way of thinking at least as much as the technical result (judging rubric: impact and
innovation with a theory of change; execution; clarity; "honest limitations are welcome"). The paper must say where
the benchmark comes from and why an exact, mechanism-level answer key is the right foundation for an epistemics
benchmark. It must do so in the register of a Nature main text: short, plain, one figure, the heavy material in an
appendix.

## 0. What may be said, and what may not (binding)

The repository's own foundation documents fix the register (`docs/S4_FOUNDATIONS_AND_PRECOMMIT_CHECKING.md`,
`docs/CODEC.md`, `docs/R6_PROTOCOL.md`), and they stand:

| may be said | may not be said |
|---|---|
| The programme is **algorithmic modelling for verifiable AI reasoning**: describe a system by short executable rules that generate its behaviour, keep every rule consistent with the evidence, and derive what follows exactly. | that we measure Kolmogorov complexity or universal algorithmic probability |
| Code lengths of executable, decodable encodings are **upper bounds** on Kolmogorov complexity (Kolmogorov 1965; Chaitin 1966; Solomonoff 1964) and were used pre-sprint as an inductive prior. | "an approximation of Kolmogorov complexity" as an achieved method |
| Short rules produce rich behaviour (Wolfram 2002; Rule 110 is a fixture of the code); computational irreducibility is why exactness matters and why we enumerate rather than shortcut. | that the principle of computational equivalence is used or tested here |
| The perturbation-and-querying approach to mechanism comes from **algorithmic causal deconvolution** (Zenil, Kiani, Tegnér 2019; Zenil et al. 2019) and from the author's earlier work with that group on algorithmic complexity and dynamic querying (Hernández-Espinosa, Zenil, Kiani, Tegnér 2021). | that our method has been shown to work in biology; the biological results are theirs and are cited as such |
| Pre-sprint development evidence (releases `v0.5.0-dev`, `v0.6.0-dev`, labelled, intervals, both signs): description-length-weighted prediction beat uniform averaging by a small margin on held-out worlds; the hierarchical prior showed no detected advantage. | any pre-sprint number without its label, interval and commit/tag, or any number not produced through `fill.py` from a committed analysis file |
| The sprint benchmark uses the **exact** part of the programme only (declared class, symbolic enumeration and counting, SAT cross-check, derivations as symbolic traces). The compression part is motivation and prior work, under construction. | that the sprint result depends on, or validates, the compression method |

Every reference must exist and be verified (DOI or arXiv id resolved; recorded in `docs/SPRINT_RELATED_WORK.md`).
A fabricated reference disqualifies the submission.

## 1. Main-text changes (main text must still end on page 8)

| # | where | change (target length) |
|---|---|---|
| M1 | Abstract | one clause: "…where this is decidable: inside a programme that models mechanisms as short executable rules and derives their consequences exactly (Appendix E)". Trim elsewhere; 150–250 words. |
| M2 | §1 Introduction, new third paragraph **"Where the benchmark comes from"** (≈ 130 words) | Three sentences on the programme (describe by short generative rules; keep every rule consistent with the evidence; derive exactly), one on the lineage (algorithmic causal deconvolution; the author's 2021 chapter as inception), one on why Boolean networks first (every status computable exactly inside a declared class, so an epistemic question becomes decidable), one that says plainly: the sprint uses the exact part; the compression part is pre-sprint, mixed, Appendix E. |
| M3 | §3 Methods, "Worlds and status" | one sentence: the engines represent mechanism classes symbolically (schema families with don't-cares), count consistent mechanisms exactly, and cross-check with SAT (Appendix E.3). |
| M4 | §5 Discussion, after "The exact check as a remedy" | **Theory of change** (≈ 70 words): the same exact engine is answer key, verifier and release gate; the programme's aim is to widen the declared class with compressed generative models so that the gate reaches systems where enumeration is impossible; until then the paper claims the class it declares. |
| M5 | §2 Related Work, §4.3 prose, §4.4 DeepSeek paragraph | trim to pay for M2 and M4 (Related Work can lose the last two sentences; 4.3's last sentence; 4.4's DeepSeek paragraph to three sentences). |
| M6 | §1 contribution 1 | append ", built on an exact symbolic engine over a declared mechanism class" |

## 2. Appendix E — "Background: short rules, exact consequences, and how symbolic computation was used" (≈ 1 page + Figure 4)

Plain prose, no equations beyond one line, numbers only through `fill.py`.

- **E.1 Short rules, rich behaviour.** Rule 110 (8 bits of rule) and one benchmark world (8 nodes, two inputs each:
  32 table bits, from `pilot4|synthetic|rewired_control|0|`, the worked example) against the behaviour they
  generate. **Figure 4**, computed from the repository's own objects (`sprint/figures.py`): (a) Rule 110 space-time
  diagram from the semantics fixture; (b) the worked-example world: its eight 2-input truth tables beside the
  256-state transition graph or a 32-step trajectory raster. Caption states the bit counts of rule against the size
  of the behaviour (through `fill.py`). This is the "compression" point made visually, with no claim beyond it.
- **E.2 Description length, algorithmic probability, and what we do not claim.** Kolmogorov, Chaitin, Solomonoff
  in two sentences; the coding-theorem intuition in one; then the binding register of §0: lengths of executable
  codes are upper bounds; selection by short code is an inductive policy, not truth. Pre-sprint development
  evidence, labelled, with release tags: the Track S description-length result (+0.0087 [0.0037, 0.0148], 113
  worlds) and the hierarchical-prior null (+0.0020 [−0.0041, 0.0082]) — wire both from the committed R6/R5
  analysis JSON through `fill.py`; if a committed JSON does not hold the exact figure, cite the release and the
  file instead of typing the number.
- **E.3 Symbolic computation in this work.** Schema (index) families with don't-cares as the representation of
  rule sets; the version space V(D) of mechanisms consistent with the evidence; exact counting by Möbius inversion
  over essential supports; two engines (lazy and restricted) and a SAT encoding that must agree; derivations as
  symbolic traces (step, node, inputs, cited row); the verifier; forgeries as single-line edits. What each gave
  the sprint: the answer key and p\*, the gates, the valid and forged checks, the "exact check as a remedy".
- **E.4 Lineage and status.** Hernández-Espinosa, Zenil, Kiani, Tegnér (2021) → algorithmic causal deconvolution
  (Zenil et al. 2019) → the author's index-set calculus for Boolean networks (unpublished manuscript; not part of
  this submission) → CausalGuard iterations 1–7 (pre-sprint, releases `v0.1.0-dev`…`v0.6.0-dev`, 2026-11-09 to
  -12) → this benchmark (R7b, pre-sprint) and the sprint work (P5, online runs, report). "Under construction"
  stated in those words.

## 3. References to add (verify each; record DOI/arXiv in `docs/SPRINT_RELATED_WORK.md`)

Kolmogorov (1965) Three approaches to the quantitative definition of information; Chaitin (1966) On the length of
programs for computing finite binary sequences; Solomonoff (1964) A formal theory of inductive inference; Rissanen
(1978) Modeling by shortest data description; Wolfram (2002) A New Kind of Science; Kauffman (1969) Metabolic
stability and epigenesis in randomly constructed genetic nets; Zenil, Kiani, Tegnér (2019) Causal deconvolution by
algorithmic generative models, Nature Machine Intelligence 1:58–66; Zenil, Kiani, Marabita et al. (2019) An
algorithmic information calculus for causal discovery and reprogramming systems, iScience 19:1160–1172; Zenil,
Soler-Toscano, Kiani, Hernández-Orozco, Rueda-Toicen (2018) A decomposition method for global evaluation of
Shannon entropy and local estimations of algorithmic complexity, Entropy 20(8):605; Hernández-Espinosa, Zenil,
Kiani, Tegnér (2021) Estimations of integrated information based on algorithmic complexity and dynamic querying,
in Handbook of Unconventional Computing, World Scientific, doi:10.1142/9789811235726_0005.

## 4. Rules that do not move

Lock, data, scores, tables 1–12 and the frozen tally unchanged. No new run. Every number through `fill.py`; the
build fails otherwise. Pre-sprint material labelled pre-sprint with tag or commit. Main text ends on page 8;
abstract 150–250 words. The secret scan before every push and before the asset upload. Manifest regenerated, asset
re-uploaded, tag moved to the final commit (iteration 11 step 3).

## 5. Order and timing (CST)

Figure 4 and the `fill.py` wiring of the two pre-sprint figures first (the only code) → Appendix E → M1–M6 →
references verified → the iteration-11 cosmetic pass (table model columns) → rebuild, twice byte-identical →
manifest, asset, tag, scan, push → return by **13:00**. Director's review 13:00–14:30; final PDF by 18:00; Alberto
submits before Monday 05:59 CST.

## 6. Return
Final commit, tag, asset and PDF hashes, page count, abstract word count, the list of added references with their
resolved identifiers, and the three sentences of Appendix E you are least sure are true.
