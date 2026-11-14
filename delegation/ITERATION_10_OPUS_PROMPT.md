# Iteration 10 — assignment to Claude Opus: the final report (title, the Tier H supplement, the P2 descriptor, the release)

Work in `/Users/alberto/Documents/projects/AI-security/AI-x-epistemics`, branch `sprint`, from the director's commit
that follows your `b91bfaf`.

Your Saturday draft is accepted. I verified the run counts (Claude 6 + 45 + 69 Tier W, 60 P5, Tier H 0; DeepSeek
48 + 4, 60 P5), the two isolation flags and their clean retries, the ledgers (554 + 179; 255), the spend record
($8.90 / $17.79), the P1/P2/P4 numbers, the qwen 19-of-20 descriptor, the prediction tally, the secret scan and the
PDF (12 pages, main text within 8, abstract 231 words). Two corrections are mine: the P2 sentence misreads the data
(Claude keeps its turn-1 probability on 67 of 67 definite verdicts under P2 and says in prose that the claims are
open), and the raw runs are in no release yet while "Code and Data" says they are.

Read `delegation/iteration_10/01_REVIEW_AND_FINAL_PLAN.md` in full and `DECISIONS.md` D117–D122; your decisions
continue from D123. In one sentence each:

1. **Title** (D117): *Who checks the check? Frontier models verify forged derivations by lookup, open-weight models
   adopt them.* The contrast leads; P5 "flag and keep" second; P2 "verdict and probability come apart" third.
2. **Tier H supplement** (D118): amendment v2-a4, then `r7b-main-claude_opus_55-v2-b4` only (Tier H P3 + P4, 24
   worlds, 2 workers, fresh session per world, no resume across a date boundary, paused items fail at 23:00 CST, hard
   stop 23:30 CST), labelled "post-freeze supplement" everywhere, frozen tally unchanged, nothing in the main text
   depending on it. **Start it first**; the window is the benchmark's.
3. **DeepSeek** (D119): no Tier H; B3 resumes only if Alberto reports a top-up by 15:00 CST, labelled post-freeze.
4. **P2 descriptor** (D120): per model, share of definite verdicts on open claims whose probability is within 0.05
   of turn 1, mean |Δp|, P0 as reference; it replaces "still overclaims on request", with the quoted reply and key.
5. **Degenerate intervals** (D121): footnote with 1 − 0.05^(1/n) for n = 24 and 30 under Tables 1 and 2.
6. **Release** (D122): pre-release `v0.8.0-sprint`, one asset with every sprint run record and ledger, SHA-256
   manifest, secret scan over the archive before upload, cited in README and "Code and Data".

Order of work: v2-a4 (commit, push, record the hash and time) → launch B4 → report changes R1–R14 of §2 in the plan
(abstract ≤ 250 words, figure legend, table widths, captions, the DeepSeek P5 n reconciliation) → rebuild, regenerate
twice byte-identical, **push with the PDF by Saturday 18:00 CST** → when B4 finishes: analysis, supplement table,
§4.4 and conclusion sentences, Appendix B/D → release and manifest → `reports/REVIEW_READY_SPRINT.md` v2 by
**Sunday 10:00 CST**. Prepare the optional second-coder sheet (16 replies, blank codes) in passing; use it only if
Alberto returns it filled.

What matters most is unchanged: lock before request; every number through `fill.py`; post-hoc labelled post-hoc;
the supplement labelled wherever it appears; predictions against outcomes with the frozen tally untouched; the key
and the account e-mail in no file and in no archive; the scan before every push and before the upload. Say
"thinking summaries" for Claude's stored reasoning.

Stop conditions: iteration 8 §7, iteration 9 §6, and §3 of the new plan. Do not stop to ask routine questions.
Return what §4 of the plan asks for.
