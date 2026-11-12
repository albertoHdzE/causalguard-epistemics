# Sprint authorisation (recorded by the director from Alberto's instruction, 2026-11-12)

Alberto's words, in the director session on 2026-11-12:

> "lets run completelly the full stack for local for all models you suggest, then if all ready, technically and
> reiviewd, tomorrow we use these two frontier and simple re run fliping the model only then re run the analysis"
>
> "for online i added my API_KEY for deepseek in /Users/alberto/Documents/projects/AI-security/.env, and we can use
> directly Opus 5.5, that the only options that we have and we will have"

What this authorises:

| Item | Authorised | Limit |
|---|---|---|
| Full local main panel today (pre-sprint), every local model that passes the smoke gate | yes | 6,000 local model requests for R7 in total (pilot and main panel), in a new ledger phase `SPRINT`. This replaces the 3,072 development ceiling for sprint work; the development ledger stays closed at 1,498. |
| DeepSeek through the API key in the parent `.env` | yes, **for the sprint main panel, after the director has reviewed the local run** | Today: at most 5 connectivity requests on a non-benchmark prompt. No benchmark item today. |
| Claude Opus 5.5 through the Claude Code command line (no Anthropic API key exists) | yes, same condition | Today: at most 5 connectivity requests on a non-benchmark prompt. No benchmark item today. |
| Any other paid service, any weight change | no | — |

Handling of the key: read it from the environment file at run time. Never print it, log it, write it into a run
record, or commit it. `.env` is ignored by git and lives outside the repository.

The earlier boundaries that still hold: no fabricated or tuned results, locks before evaluation, preexisting work
labelled as such, `doc/Gemini-Talk.txt` private.

## Addendum, 2026-11-12 (director, after the R7 review)

Alberto's authorisation is unchanged: the full local panel today, the two online models during the sprint after
the director's review. The director changes two of his own limits for the redesigned panel (R7b):

| Item | Before | Now | Why |
|---|---|---|---|
| Model-server time for the main local panel | 14 hours | 30 server-hours across the two local servers, finishing by 10:00 local time on 2026-11-13 | The locked wording is reasoning-first, which costs 5–10 times the tokens |
| Local request cap | 6,000 | 6,000 (466 used) | unchanged |
| Online requests today | at most 5 connectivity probes per provider | unchanged; 3 used | no benchmark-like item goes online today |

The online run during the sprint will begin with two smoke worlds per tier per model, after the director's review.
