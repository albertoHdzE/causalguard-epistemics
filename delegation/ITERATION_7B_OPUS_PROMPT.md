# Iteration 7b — assignment to Claude Opus: add the wiring-given tier and the forged check, lock, run the local panel

Work in `/Users/alberto/Documents/projects/AI-security/AI-x-epistemics`, branch `iteration-7` (director's review
commit on top of your `a58066d`).

Your R7 build is accepted and your stop was correct. Gate 3 was my error. All six of your objections hold. The
review is `reports/review_r7/REVIEW.md`.

I am not taking option A or B as written. I read the raw replies from your third pilot. On the same world, qwen
lists evidence rows it did not use and concludes "no evidence contradicts this claim", so true; mistral looks for
an evidence row with the same start state, finds none, and says "not settled". Neither tries to work out the
status, and with hidden wiring neither could. A panel on that task alone measures which default each model falls
back on. Your own point 2 goes further than you took it: on that task a model cannot verify a real check or catch
a forged one, so a wrong-checker condition there can only measure deference.

So the benchmark gets a second tier, and it becomes the primary one:

- **Tier W, wiring given.** Same mechanisms, with each node's inputs listed. A node's next value is settled exactly
  when its input combination was observed. A reader can derive every status by table lookup, so a wrong verdict is
  a failure to separate what was observed from what was not.
- **Tier H, wiring hidden.** What you built. It stays as the contrast tier, where the right behaviour is to hold
  back.
- **P4, a forged check**, on both tiers. On Tier W the valid check cites evidence rows and can be verified, and
  the forged one contains a statement the evidence contradicts. On Tier H neither can be verified.
- **Reasoning-first wording for every model.** The online models reason before answering; JSON-only would confound
  the model with access to a scratch space. The cost is a smaller panel: 120 Tier W worlds and 60 Tier H worlds,
  with half panels for slow models.

Read, in this order:

1. `reports/review_r7/REVIEW.md`
2. `delegation/iteration_7b/01_SCIENTIFIC_PROTOCOL.md`
3. `delegation/iteration_7b/02_PLAN_AND_ACCEPTANCE.md`
4. `docs/SPRINT_AUTHORISATION.md` (addendum of 2026-11-12)

What matters most:

- Tier W ground truth comes from two independent implementations that agree on every item, plus the cross-tier
  test. A reader must be able to verify the worked example by hand.
- Every valid check passes the verifier. Every forged check fails it.
- No gate that tests a model blocks the run. Gate 3 is recorded, not blocking.
- Lock before the first main-panel request. One run per model.
- **Deadline for the lock: 21:00 local time today.** If Tier W is not lockable by then, lock and run Tier H alone
  overnight as the protocol's fallback, and continue Tier W under a second lock version. Do not let the night pass
  with idle servers.
- Read the replies, not only the scores. Quote what the models do.
- Nothing online today. The account e-mail and the key appear in no file.
- Everything today is pre-sprint work and is labelled so.

You have latitude on the rendering of derivations, the forgery kinds, the Tier W budget, the cap on derivation
length and the second exact implementation. Record each choice in `DECISIONS.md`. If a part of this design is wrong,
say so with evidence and take the better route when it does not weaken ground truth, the lock or disclosure.

Do not stop to ask routine questions. Return what `02_PLAN_AND_ACCEPTANCE.md` asks for.
