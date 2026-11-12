# Related work for the sprint report (verified 2026-11-12, pre-sprint)

Every entry below was opened on 2026-11-12 by the implementation agent (R7) at the URL given; the "checked" column
says what was confirmed on that page. Nothing here is cited from memory. Entries marked *(PDF text checked)* were
confirmed in the paper's own text, not only the abstract page.

## 1. Three-valued entailment benchmarks (the closest relatives of our status label)

| Reference | URL | Checked | What it measures | What it cannot measure |
|---|---|---|---|---|
| Tafjord, Dalvi Mishra, Clark. *ProofWriter: Generating Implications, Proofs, and Abductive Statements over Natural Language.* Findings of ACL 2021. | https://arxiv.org/abs/2012.13048 | title, authors, venue; *(PDF text checked)* the open-world-assumption version uses answers in {True, False, Unknown} | Whether a model derives what follows from synthetic natural-language rule theories, with proofs; under the open-world assumption a statement can be Unknown. | Unknown there means "not derivable from the stated rules"; there is no probability of the unknown statement, no hidden ground truth behind it, and no test of how a model defends its label under pressure. |
| Han et al. *FOLIO: Natural Language Reasoning with First-Order Logic.* 2022 (arXiv 2209.00840). | https://arxiv.org/abs/2209.00840 | title, first author, year; *(PDF text checked)* conclusions labelled True, False or Unknown; 1,430 examples | Whether a conclusion follows from expert-written first-order premises in natural language. | Same as above: Unknown is a logical label without an exact probability, and the label set is small and hand-built. |

**Overlap stated plainly.** The three-way verdict (settled true / settled false / not settled) is the same idea as
True / False / Unknown in ProofWriter's open-world setting and in FOLIO. That part of our design already exists.
Two things differ. Our "not settled" claims come with an exact probability (p* = the share of consistent mechanisms
making the claim true). And the generator has no limit on the number of items, because status is computed exactly
from the evidence by two independent engines, not annotated.

## 2. Abstention and "known unknowns"

| Reference | URL | Checked | What it measures | What it cannot measure |
|---|---|---|---|---|
| Yin, Sun, Guo, Wu, Qiu, Huang. *Do Large Language Models Know What They Don't Know?* Findings of ACL 2023. | https://arxiv.org/abs/2305.18153 | title, authors, venue; SelfAware dataset of unanswerable vs answerable questions | Whether a model recognises questions it cannot answer. | "Unanswerable" is judged by annotators over world knowledge; no exact line between what the evidence settles and what it leaves open. |
| Amayuelas, Wong, Pan, Chen, Wang. *Knowledge of Knowledge: Exploring Known-Unknowns Uncertainty with Large Language Models.* 2023 (arXiv 2305.13712). | https://arxiv.org/abs/2305.13712 | title, authors, year; Known-Unknown Questions (KUQ) dataset, F1 | Whether models tell known from unknown queries in open-ended QA. | The unknown/known label is categorical and human-assigned; no exact probability and no settled/open distinction relative to a given body of evidence. |
| Kirichenko, Ibrahim, Chaudhuri, Bell. *AbstentionBench: Reasoning LLMs Fail on Unanswerable Questions.* 2025 (arXiv 2506.09038). | https://arxiv.org/abs/2506.09038 | title, authors, year; 20 datasets of unanswerable, underspecified, false-premise, subjective or outdated questions | Whether models abstain when they should. | Abstention is binary and judged against curated "should abstain" labels; it does not score a probability on the open items or how answers change under pushback. |
| Wen, Yao, Feng, Xu, Tsvetkov, Howe, Wang. *Know Your Limits: A Survey of Abstention in Large Language Models.* TACL 2024 (arXiv 2407.18418). | https://arxiv.org/abs/2407.18418 | title, authors, year; survey of abstention methods, benchmarks and metrics | Survey (context for the abstention literature). | — |

**Overlap.** Measuring whether a model abstains or says "unknown" when it should is established. Our underclaim and
overclaim rates are the two error directions of that measurement. What is new here is that the line between
"should answer" and "should abstain" is exact (inside the declared class) and depends on the evidence shown, not on
an annotator.

## 3. Verbalised confidence and calibration

| Reference | URL | Checked | What it measures | What it cannot measure |
|---|---|---|---|---|
| Lin, Hilton, Evans. *Teaching Models to Express Their Uncertainty in Words.* 2022 (arXiv 2205.14334). | https://arxiv.org/abs/2205.14334 | title, authors, year | Whether a model's verbalised confidence matches its probability of being right. | Calibration is scored against correctness, so a well-calibrated model can still be wrong about what the evidence supports. There is no reference probability for each item. |
| Tian et al. *Just Ask for Calibration: Strategies for Eliciting Calibrated Confidence Scores from Language Models Fine-Tuned with Human Feedback.* EMNLP 2023 (arXiv 2305.14975). | https://arxiv.org/abs/2305.14975 | title, authors, venue; TriviaQA, SciQ, TruthfulQA | Calibration of verbalised confidence against token probabilities in RLHF models. | Same: scored against outcomes, with no exact evidence-relative probability. |
| Xiong, Hu, Lu, Li, Fu, He, Hooi. *Can LLMs Express Their Uncertainty? An Empirical Evaluation of Confidence Elicitation in LLMs.* ICLR 2024 (arXiv 2306.13063). | https://arxiv.org/abs/2306.13063 | title, authors, venue; finding that verbalised confidence tends to be overconfident | Black-box confidence elicitation, calibration and failure prediction. | Same. |

**Overlap.** Eliciting a stated probability and scoring it is standard. Our addition is the exact per-item
reference p*. That lets us score probability error against what the evidence supports (mean absolute difference
from p*), not only Brier against the outcome. We report both, and we also report the Brier of p* itself, which is
the best any reasoner can achieve.

## 4. Sycophancy and answer flipping under challenge

| Reference | URL | Checked | What it measures | What it cannot measure |
|---|---|---|---|---|
| Perez et al. *Discovering Language Model Behaviors with Model-Written Evaluations.* 2022 (arXiv 2212.09251). | https://arxiv.org/abs/2212.09251 | title, first author, year; abstract reports sycophancy (repeating back a user's preferred answer) | Model-written evaluations of many behaviours, including sycophancy. | Sycophancy towards stated views; no notion of whether a challenge is evidentially justified. |
| Sharma et al. *Towards Understanding Sycophancy in Language Models.* 2023 (arXiv 2310.13548). | https://arxiv.org/abs/2310.13548 | title, authors, year | Whether assistants tilt answers towards a user's views, and whether preference data rewards it. | Challenges are uninformative. A model that never yields scores as well as one that yields exactly when it should. |
| Laban, Murakhovs'ka, Xiong, Wu. *Are You Sure? Challenging LLMs Leads to Performance Drops in The FlipFlop Experiment.* 2023 (arXiv 2311.08596). | https://arxiv.org/abs/2311.08596 | title, authors, year; about 46 % flips and an average accuracy drop of about 17 % | Whether models keep a correct answer after "Are you sure?". | Only an empty challenge, so there is no condition in which changing the answer is correct. |
| Wang, Yue, Sun. *Can ChatGPT Defend its Belief in Truth? Evaluating LLM Reasoning via Debate.* Findings of EMNLP 2023 (arXiv 2305.13160). | https://arxiv.org/abs/2305.13160 | title, authors, venue | Whether models keep correct answers against flawed user arguments. | Invalid challenges only; no verified challenge to measure appropriate updating. |

**Overlap.** Measuring capitulation to an empty or invalid challenge (our P1) is established. Our P0 condition
mirrors the "are you sure" control. What the design adds is a challenge that is *right*: a checked statement
with a witness (P3). It sits beside P1 on randomised, disjoint worlds. Discernment (repair under a valid
challenge minus capitulation under an empty one) separates a model that updates on evidence from one that yields
to any confident message and from one that never yields. We have not found this paired measurement against exact
ground truth in the work above. That is a statement about the references listed here, not a literature-wide claim.

## 5. Information seeking

| Reference | URL | Checked | What it measures | What it cannot measure |
|---|---|---|---|---|
| Li, Kim, Wang. *QuestBench: Can LLMs ask the right question to acquire information in reasoning tasks?* 2025 (arXiv 2503.22674). | https://arxiv.org/abs/2503.22674 | title, authors, year | Whether a model identifies the one clarifying question needed to solve an underspecified logic, planning or math problem. | One missing variable per problem; no exact posterior over many candidate explanations, and no stop-or-continue decision. |

**Overlap.** Our own preexisting R5/R6 work measured sequential information seeking with exact expected
information gain (Track A; see `PREEXISTING_WORK.md`). It is not part of the sprint tasks; it is cited as
motivation only.

## What appears to be new (to be argued in the report, with the caveats above)

1. **Exact evidential status as ground truth.** For each claim the answer key is the exact status relative to the
   shown evidence and the declared class, computed by two independent exact engines that must agree. "Not settled"
   claims carry an exact probability. It is not truth-relative, and it is not annotated.
2. **A randomised pressure design with a valid challenge.** Neutral / empty disagreement / demand to commit /
   checked challenge with a witness, assigned by hash, scored relative to the neutral control. Discernment is the
   headline.
3. **The check as a remedy, with its limit measured.** The same checker that labels items also gates released
   verdicts. Its failure mode outside the declared class was measured before the sprint (R5 Track M).

## What already exists and must not be claimed as ours

Three-valued (True/False/Unknown) entailment labels; abstention benchmarks; verbalised-confidence calibration;
sycophancy and flip-under-challenge measurements; synthetic, procedurally generated reasoning items.
