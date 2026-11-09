# AI × Epistemics sprint preparation

Start with the [current Claude implementation handoff](delegation/00_START_HERE.md), which incorporates the owner's clarification about compact symbolic models, complexity and incomplete evidence.

Send Claude [this implementation prompt](delegation/CLAUDE_PROMPT.md). After implementation, use [the Codex review prompt](delegation/REVIEW_REQUEST_PROMPT.md).

The [initial assessment](preparation/RESEARCH_PLAN.md) is preserved as historical context and is superseded for implementation by the v2 handoff. A separate public GitHub repository is a required implementation deliverable; it has not been created by this preparation step.

Original idea: [Gemini conversation](doc/Gemini-Talk.txt).

Everything currently in this directory is **pre-sprint preparation dated November 9, 2026**, including the feasibility probe. Reused CausalBool code predates this sprint. Disclose this distinction in any submission.

## Reproduce the feasibility probe

With a checkout of `https://github.com/albertoHdzE/CausalBool` at revision
`376a11ddf25063d49dc8f6cd98bbb3baf2e1cc43`:

```sh
python3 tools/check_causalbool_feasibility.py --causalbool-root /path/to/CausalBool
```

Run from this directory. The script uses Python's standard library and imports the upstream forward model. It does not modify the checkout, call an LLM, or edit neural weights. The review checkout is temporarily available at `/tmp/epistemics-causalbool-review`; it is not a permanent dependency installation.

Saved output: [feasibility_result.json](preparation/feasibility_result.json). It establishes only the limited checks described in the plan, not research efficacy.
