# R7 online readiness (pre-sprint, 2026-11-12)

**No benchmark item was sent to an online model.** The two online models are ready to run the locked main panel
(`artifacts/sprint_main_manifest.json`) with only the model changed: same worlds, same assignment, same prompts,
same analysis command. Launch after the director's review (`docs/SPRINT_AUTHORISATION.md`).

## Launch

```bash
C=$(git rev-parse --short=12 <lock commit>)
scripts/run_from_snapshot.sh $C r7-main-deepseek_v4_pro-v1 python -m causalguard run --config configs/sprint/online_deepseek_v4_pro.json --quiet
scripts/run_from_snapshot.sh $C r7-main-claude_opus_55-v1  python -m causalguard run --config configs/sprint/online_claude_opus_55.json --quiet
python -m causalguard sprint-analyze --run-dir runs/<each local main run> ... \
    --run-dir runs/r7-main-deepseek_v4_pro-v1 --run-dir runs/r7-main-claude_opus_55-v1 --out reports/sprint_all
```

Online requests go to their own ledgers (`runs/sprint-online-calls/<tag>.jsonl`, cap 400 each = 320 planned + retries).
The local `SPRINT` ledger is not touched.

## DeepSeek

| Item | Value | Source |
|---|---|---|
| Endpoint | `https://api.deepseek.com/chat/completions` (OpenAI format) | api-docs.deepseek.com, read 2026-11-12 |
| Model id | `deepseek-v4-pro` (DeepSeek-V4-Pro-0813). The `.env` value `DeepSeek_V4-Pro` is not an API id; the docs' id was used and confirmed by the probe (`response_model` = `deepseek-v4-pro`) | docs + probe |
| Reasoning | Thinking mode is the default for this model (effort `high`); the config sends `thinking: enabled`, `reasoning_effort: high` explicitly. The chain of thought is returned separately (`reasoning_content`); it is not part of the answer, and only its length is recorded | docs (thinking-mode guide) |
| Temperature | Has no effect in thinking mode (docs). We send 0; disclose that sampling is not controlled | docs |
| Other variant | `deepseek-flash` (V4.1-Flash) also exists under the same key; not authorised for the panel unless the director adds it | docs |
| Key handling | Read at construction from the environment or `../.env`; kept in a private attribute; sent only to `api.deepseek.com` over https (the adapter refuses any other host); never in a record, log, repr or metadata (`tests/test_r7_online_adapters.py`) | code + tests |
| Connectivity | 1 of 5 probes used: non-benchmark prompt, reply `READY`, 1.3 s, 100 prompt tokens, 10 completion tokens | `reports/development_r7/online_probe_deepseek.json` |
| Price | V4-Pro per 1M tokens: input cache miss $0.66 off-peak / $1.32 peak; output $1.98 / $3.96 (peak 01:00–04:00 and 06:00–10:00 UTC, weekdays) | api-docs.deepseek.com/quick_start/pricing |
| Expected cost | 320 requests × (~2.5k input + ~1k–10k output including thinking) gives about $1–13 at peak rates, half that off-peak. The output length of thinking is the unknown | estimate |
| Expected wall time | 8 workers; at ~30–120 s per request, about 20–80 min | estimate |

## Claude Opus 5.5 (Claude Code command line)

No Anthropic API key exists, so the subject model is reached through `claude -p`. The adapter is
`ClaudeCLIProvider` (`src/causalguard/llm/providers.py`).

**Command (every request).** `claude -p --model claude-opus-5-5 --system-prompt <our system message> --tools ""
--strict-mcp-config --setting-sources "" --disable-slash-commands --output-format json` plus `--session-id <new
uuid>` (turn 1) or `--resume <that uuid>` (turn 2). The prompt goes on stdin. The working directory is a fresh,
empty temporary directory, checked to be empty before each request. Flags were taken from `claude --help`
(CLI 2.1.322). `--bare` would also skip hooks, but it accepts only an API key, so it cannot be used here.

**Isolation proof.** Two probes (2 of 5 used), non-benchmark: system "You are a test endpoint.", user "Reply with
exactly the word READY and nothing else.", then a second turn in the same session.

| | turn 1 | turn 2 |
|---|---|---|
| our text (chars) | 75 | 161 |
| reported input tokens (input + cache creation + cache read) | 579 | 607 |
| reply | READY | READY (the session persisted) |

The CLI writes its own record of each API request (`~/.claude/projects/<cwd>/<session>.jsonl`:
`api-request-shape`, `api-request-blob`). For the probe, that record shows exactly:

- system: `["You are a Claude agent, built on Anthropic's Claude Agent SDK.", <our system prompt>]`; tools: `[]`;
- user side: our prompt; a fixed `<system-reminder>` with the account's e-mail notice ("userEmail … treat as
  private …"); a fixed environment block (working directory = the empty temp dir, platform, a note on untrusted
  downloads, the model identity sentence, today's date).

No CLAUDE.md content, no memory, no hook output (this machine's SessionStart hooks inject recall and
code-graph text in interactive sessions; none appears), no skills, no MCP tools.

**Verdict on isolation.** Shown for everything the protocol names: project instructions, memory, hooks,
settings, tools, MCP and skills do not reach the subject. **Not shown in the strict sense of "our prompt and
nothing else".** About 550 tokens of fixed harness context (the SDK identity sentence, the account e-mail
notice, the environment/model/date block) is added to every request and cannot be removed on this route without
an API key. It is identical for every item and contains no benchmark information. Recommendation: run, and
disclose it verbatim. The director decides. To keep it that way, **every request is audited** from the CLI's own
record (`ClaudeCLIProvider.audit_wire`). It fails the request if any system block other than [SDK sentence, ours]
appears, if any tool is present, or if any user-side block is not ours, the environment block or the account
notice. The audit result is stored per request (`attempts[].isolation`). It was tested against a planted
CLAUDE.md injection (`tests/test_r7_online_adapters.py`).

**Disclosures for the report.** Sampling temperature cannot be set on this route, and there is no seed. The model
family that implemented the benchmark (Claude) is also evaluated, in fresh contexts with no access to the
repository and no tools. Extended thinking: the probe reported 0 thinking tokens on a trivial prompt; the CLI's
default effort is used (no `--effort` flag). The director may set `extra.effort` in the config before launch;
that is a model setting and must be fixed before the run.

**Expected cost and time.** The probe's CLI-reported cost was $0.0047 for 577 cache-creation + 6 input/output
tokens. A Task S request is about 1,100 tokens of our text plus about 575 tokens of harness context. With replies of
~300–2,000 tokens, 320 requests are likely a few dollars of API-equivalent usage, billed to the subscription. The
CLI reports `totalCostUSD` per session, so the actual figure is recorded. Wall time: 4 workers at ~10–60 s per
request, about 15–80 min.

## Mock dry runs (no network)

`tests/test_r7_online_adapters.py`: DeepSeek request shape, host pinning and key absence; the Claude route with a
fake `claude` binary. The fake checks the flags, the empty working directory, `--resume` of the same session for
turn 2, refusal to continue a conversation it does not hold, failure of the isolation audit on an injected
CLAUDE.md, and one full two-turn sprint episode through the harness. The runner path was also dry-run end to end
with the `sprint_hash` mock provider on the smoke manifest.
