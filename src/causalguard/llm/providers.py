"""Model providers for S3: a local OpenAI-compatible HTTP adapter, plus mock/replay providers for tests.

Owner of: transport, bounded transport retries, per-attempt cost logging, provider metadata.

Rules
-----
* Only local endpoints: ``base_url`` must resolve to 127.0.0.1 / localhost / ::1 unless the
  config explicitly sets ``allow_remote=true`` (default false).  No API keys or environment
  secrets are ever read; no Authorization header is sent.
* Transport errors (connection refused/reset, HTTP 5xx, timeouts) are retried at most
  ``max_transport_retries`` times (default 2).  Every attempt -- including failed ones -- is
  logged with its latency and, when the server returns them, prompt/completion token counts.
* Content problems (bad JSON, wrong labels, empty text) are NEVER retried or repaired here: the
  provider returns the raw text and parsing happens in :mod:`causalguard.llm.parse`.
* HTTP 4xx and malformed response envelopes are provider failures that are not retried
  (re-sending the same request cannot fix them).
* Every call result carries ``provider_kind`` in {'real','mock','replay'} so analysis can
  exclude non-real outputs.
"""
from __future__ import annotations

import copy
import hashlib
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

from ..schema import canonical_json

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


class TransportError(Exception):
    """Retryable transport failure (connection, HTTP 5xx, timeout)."""


class FatalProviderError(Exception):
    """Non-retryable provider failure (HTTP 4xx, malformed envelope, replay miss)."""


class CapExceeded(Exception):
    """Raised by a budget hook before an attempt would exceed a call cap."""

    def __init__(self, scope: str, detail: str = ""):
        super().__init__(f"{scope}: {detail}")
        self.scope = scope


@dataclass
class ProviderConfig:
    kind: str = "openai_compatible"        # 'openai_compatible' | 'mock' | 'replay'
    backend: str = "ollama"                # 'ollama' | 'lmstudio' | 'other' (metadata probing only)
    base_url: str = "http://127.0.0.1:11434/v1"
    model: str = ""
    temperature: float = 0.0
    sample_temperature: float = 0.7
    max_tokens: int = 400
    seed: int | None = 0
    timeout_s: float = 120.0
    max_transport_retries: int = 2
    allow_remote: bool = False
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "ProviderConfig":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


def request_hash(model: str, messages: list[dict], temperature: float, max_tokens: int, seed: int | None) -> str:
    """Identity of a chat request (used by ReplayProvider and stored in every call record)."""
    return hashlib.sha256(canonical_json({"model": model, "messages": messages, "temperature": temperature,
                                          "max_tokens": max_tokens, "seed": seed}).encode()).hexdigest()


def check_local(base_url: str, allow_remote: bool) -> None:
    host = urllib.parse.urlparse(base_url).hostname
    if host not in LOCAL_HOSTS and not allow_remote:
        raise ValueError(f"refusing non-local base_url {base_url!r} (set allow_remote=true to override)")


class BaseProvider:
    """Retry loop + attempt logging shared by all providers.  Subclasses implement ``_send``."""

    kind = "abstract"

    def __init__(self, cfg: ProviderConfig):
        self.cfg = cfg

    def _send(self, messages: list[dict], temperature: float, seed: int | None) -> dict:
        raise NotImplementedError

    def metadata(self) -> dict:
        return {"provider_kind": self.kind, "model": self.cfg.model}

    def chat(self, messages: list[dict], temperature: float, seed: int | None,
             before_attempt: Callable[[], None] | None = None) -> dict:
        """One logical call.  Returns a call result dict; never raises for transport/content problems.

        ``before_attempt`` is invoked before every physical attempt and may raise CapExceeded,
        which propagates (the caller records the cap status)."""
        msgs = copy.deepcopy(messages)
        rh = request_hash(self.cfg.model, msgs, temperature, self.cfg.max_tokens, seed)
        attempts = []
        content = None
        ok = False
        failure = None
        max_attempts = 1 + max(0, int(self.cfg.max_transport_retries))
        for a in range(max_attempts):
            if before_attempt is not None:
                before_attempt()
            t0 = time.perf_counter()
            rec = {"attempt": a, "ok": False, "error": None, "prompt_tokens": None, "completion_tokens": None,
                   "finish_reason": None}
            try:
                r = self._send(msgs, temperature, seed)
                rec.update(ok=True, prompt_tokens=r.get("prompt_tokens"), completion_tokens=r.get("completion_tokens"),
                           finish_reason=r.get("finish_reason"), response_model=r.get("response_model"))
                content = r["content"]
                ok = True
            except TransportError as e:
                rec["error"] = f"transport: {e}"
                failure = rec["error"]
            except FatalProviderError as e:
                rec["error"] = f"fatal: {e}"
                failure = rec["error"]
            rec["latency_s"] = round(time.perf_counter() - t0, 4)
            attempts.append(rec)
            if ok or rec["error"].startswith("fatal"):
                break
        return {"provider_kind": self.kind, "model": self.cfg.model, "messages": msgs, "temperature": temperature,
                "max_tokens": self.cfg.max_tokens, "seed": seed, "request_hash": rh, "ok": ok, "raw_output": content,
                "failure": None if ok else failure, "attempts": attempts}


class OpenAICompatibleProvider(BaseProvider):
    """Local OpenAI-compatible /chat/completions endpoint (Ollama, LM Studio).  urllib only."""

    kind = "real"

    def __init__(self, cfg: ProviderConfig):
        super().__init__(cfg)
        check_local(cfg.base_url, cfg.allow_remote)
        if not cfg.model:
            raise ValueError("model must be set")
        self.base = cfg.base_url.rstrip("/")
        p = urllib.parse.urlparse(self.base)
        self.root = f"{p.scheme}://{p.netloc}"

    def _http(self, url: str, body: dict | None = None, timeout: float | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, method="GET" if body is None else "POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.cfg.timeout_s) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            if e.code >= 500:
                raise TransportError(f"HTTP {e.code}") from None
            raise FatalProviderError(f"HTTP {e.code}: {e.read()[:300]!r}") from None
        except (urllib.error.URLError, ConnectionError, socket.timeout, TimeoutError) as e:
            raise TransportError(repr(getattr(e, "reason", e))) from None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            raise FatalProviderError(f"non-JSON envelope: {raw[:200]!r}") from None

    def _send(self, messages: list[dict], temperature: float, seed: int | None) -> dict:
        if self.cfg.backend == "ollama" and self.cfg.extra.get("ollama_native_options"):
            return self._send_ollama_native(messages, temperature, seed)
        body = {"model": self.cfg.model, "messages": messages, "temperature": temperature,
                "max_tokens": self.cfg.max_tokens, "stream": False}
        if seed is not None:
            body["seed"] = seed
        r = self._http(self.base + "/chat/completions", body)
        try:
            choice = r["choices"][0]
            content = choice["message"].get("content")
        except (KeyError, IndexError, TypeError, AttributeError):
            raise FatalProviderError(f"malformed envelope: {str(r)[:200]}") from None
        usage = r.get("usage") or {}
        return {"content": content if content is not None else "", "finish_reason": choice.get("finish_reason"),
                "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
                "response_model": r.get("model")}

    def _send_ollama_native(self, messages: list[dict], temperature: float, seed: int | None) -> dict:
        """Ollama native /api/chat (iteration 4): the OpenAI-compatible endpoint cannot set the context window, and
        a silently truncated prompt would invalidate multi-turn episodes.  ``extra.ollama_native_options`` (e.g.
        {"num_ctx": 16384}) is sent verbatim with temperature, seed and num_predict = max_tokens."""
        opts = {**self.cfg.extra["ollama_native_options"], "temperature": temperature,
                "num_predict": self.cfg.max_tokens}
        if seed is not None:
            opts["seed"] = seed
        r = self._http(self.root + "/api/chat", {"model": self.cfg.model, "messages": messages, "stream": False,
                                                  "options": opts})
        try:
            content = r["message"].get("content")
        except (KeyError, TypeError, AttributeError):
            raise FatalProviderError(f"malformed envelope: {str(r)[:200]}") from None
        fr = r.get("done_reason")
        return {"content": content if content is not None else "", "finish_reason": "length" if fr == "length" else fr,
                "prompt_tokens": r.get("prompt_eval_count"), "completion_tokens": r.get("eval_count"),
                "response_model": r.get("model")}

    def _try(self, fn):
        try:
            return fn(), None
        except Exception as e:  # metadata is best-effort; failures are recorded, not invented
            return None, repr(e)[:200]

    def metadata(self) -> dict:
        md = {"provider_kind": self.kind, "backend": self.cfg.backend, "base_url": self.base, "model": self.cfg.model,
              "seed_sent": self.cfg.seed is not None, "seed_honoured": "not_verified", "model_digest": None,
              "server_version": None, "quantization": None, "parameter_size": None, "format": None,
              "chat_template_sha256": None, "model_parameters": None, "models_entry": None, "limitations": []}
        to = min(10.0, self.cfg.timeout_s)
        if self.cfg.backend == "ollama":
            v, err = self._try(lambda: self._http(self.root + "/api/version", timeout=to))
            md["server_version"] = (v or {}).get("version")
            if err:
                md["limitations"].append(f"/api/version unavailable: {err}")
            tags, err = self._try(lambda: self._http(self.root + "/api/tags", timeout=to))
            entry = None
            for m in (tags or {}).get("models", []):
                if m.get("name") == self.cfg.model or m.get("model") == self.cfg.model:
                    entry = m
                    break
            if entry:
                det = entry.get("details") or {}
                md.update(model_digest=entry.get("digest"), quantization=det.get("quantization_level"),
                          parameter_size=det.get("parameter_size"), format=det.get("format"),
                          models_entry={k: entry.get(k) for k in ("name", "modified_at", "size", "digest")})
            else:
                md["limitations"].append(f"model not found in /api/tags ({err})")
            show, err = self._try(lambda: self._http(self.root + "/api/show", {"model": self.cfg.model}, timeout=to))
            if show:
                tmpl = show.get("template")
                if tmpl:
                    md["chat_template_sha256"] = hashlib.sha256(tmpl.encode()).hexdigest()
                md["model_parameters"] = show.get("parameters")
                det = show.get("details") or {}
                md["quantization"] = md["quantization"] or det.get("quantization_level")
            else:
                md["limitations"].append(f"/api/show unavailable: {err}")
        else:
            models, err = self._try(lambda: self._http(self.base + "/models", timeout=to))
            for m in (models or {}).get("data", []):
                if m.get("id") == self.cfg.model:
                    md["models_entry"] = m
            if md["models_entry"] is None:
                md["limitations"].append(f"model not listed in /v1/models ({err})")
            if self.cfg.backend == "lmstudio":
                q = urllib.parse.quote(self.cfg.model, safe="")
                info, err = self._try(lambda: self._http(self.root + f"/api/v0/models/{q}", timeout=to))
                if info:
                    md.update(quantization=info.get("quantization"), format=info.get("compatibility_type"),
                              models_entry={**(md["models_entry"] or {}), "lmstudio_v0": info})
                else:
                    md["limitations"].append(f"LM Studio /api/v0/models unavailable: {err}")
            md["limitations"].append("no model digest/revision exposed by this backend")
            md["limitations"].append("server version not exposed by this backend")
        md["limitations"].append("seed is sent but whether the backend honours it is not verified")
        return md


class MockProvider(BaseProvider):
    """Scripted provider for tests.  Records every attempt (messages, temperature, seed).

    ``script`` is either a list of responses consumed in order (a response is a string, or an
    Exception instance to raise -- use TransportError to simulate transport failures), or a
    callable ``(messages, temperature, seed) -> str`` that may raise."""

    kind = "mock"

    def __init__(self, cfg: ProviderConfig | None = None, script=None):
        cfg = cfg or ProviderConfig(kind="mock", model="mock-model")
        super().__init__(cfg)
        self.script = script if script is not None else []
        self.calls: list[dict] = []
        self._i = 0

    def _send(self, messages, temperature, seed):
        self.calls.append({"messages": copy.deepcopy(messages), "temperature": temperature, "seed": seed})
        if callable(self.script):
            out = self.script(messages, temperature, seed)
        else:
            if self._i >= len(self.script):
                raise FatalProviderError("mock script exhausted")
            out = self.script[self._i]
            self._i += 1
        if isinstance(out, Exception):
            raise out
        return {"content": out, "finish_reason": "stop", "prompt_tokens": None, "completion_tokens": None}


class ReplayProvider(BaseProvider):
    """Replays recorded raw outputs keyed by request hash.  A miss is a fatal (non-retried) failure."""

    kind = "replay"

    def __init__(self, cfg: ProviderConfig, table: dict[str, str]):
        super().__init__(cfg)
        self.table = dict(table)

    @classmethod
    def from_records(cls, cfg: ProviderConfig, records: list[dict]) -> "ReplayProvider":
        table = {}
        for r in records:
            for c in r.get("calls", {}).values():
                if c.get("ok"):
                    table[c["request_hash"]] = c["raw_output"]
        return cls(cfg, table)

    def _send(self, messages, temperature, seed):
        rh = request_hash(self.cfg.model, messages, temperature, self.cfg.max_tokens, seed)
        if rh not in self.table:
            raise FatalProviderError(f"replay miss {rh[:12]}")
        return {"content": self.table[rh], "finish_reason": "replay", "prompt_tokens": None, "completion_tokens": None}


def mock_policy(name: str) -> Callable:
    """Named deterministic mock scripts usable from (picklable) payloads."""
    def fixed(label):
        probs = {k: (0.8 if k == label else 0.1) for k in ("entailed", "refuted", "underdetermined")}
        txt = json.dumps({"verdict": label, "probabilities": probs, "reason": "mock"})
        return lambda m, t, s: txt
    if name.startswith("always_"):
        return fixed(name[len("always_"):])
    if name == "s4_tool_copier":
        return _s4_tool_copier
    if name == "sprint_hash":
        return _sprint_hash
    raise ValueError(f"unknown mock policy {name!r}")


def _sprint_hash(messages, temperature, seed):
    """R7 sprint dry-run policy: a verdict and probability per claim id, from a hash of the conversation so far
    (turn 2 differs from turn 1); exercises parsing, both turns and scoring without any model."""
    import re as _re
    user0 = next(m["content"] for m in messages if m["role"] == "user")
    cids = sorted(set(_re.findall(r"\n (c\d+):", user0)), key=lambda c: int(c[1:]))
    words = ("true", "false", "not settled")
    ans = []
    for c in cids:
        h = hashlib.sha256(f"{len(messages)}|{c}|{user0[:200]}".encode()).digest()
        ans.append({"cid": c, "verdict": words[h[0] % 3], "probability": round(h[1] / 255, 2)})
    return json.dumps({"answers": ans})


def _s4_tool_copier(messages, temperature, seed):
    """S4 test policy: without tools answer 'underdetermined'/0; with tools check every claim, then commit the
    tool verdicts (forecast = majority of fraction_true relative to the claim literal)."""
    import re as _re
    sys_txt = messages[0]["content"]
    cids = sorted(set(_re.findall(r"\n (c\d+):", messages[1]["content"])), key=lambda c: int(c[1:]))
    if "tool_calls" not in sys_txt:
        return json.dumps({"answers": [{"cid": c, "verdict": "underdetermined", "forecast": 0} for c in cids]})
    if len(messages) == 2:
        return json.dumps({"tool_calls": [{"tool": "check", "cid": c} for c in cids]})
    res = json.loads(messages[-1]["content"].split("\n", 1)[1])
    ans = []
    for r in res:
        if "verdict" in r and "cid" in r:
            ans.append({"cid": r["cid"], "verdict": r["verdict"] if r["verdict"] in ("entailed", "refuted",
                                                                                      "underdetermined") else "underdetermined",
                        "forecast": 0})
    return json.dumps({"tool_calls": [{"tool": "commit", "answers": ans}]})


def make_provider(d: dict) -> BaseProvider:
    cfg = ProviderConfig.from_dict(d)
    if cfg.kind == "openai_compatible":
        return OpenAICompatibleProvider(cfg)
    if cfg.kind == "mock":
        return MockProvider(cfg, script=mock_policy(cfg.extra.get("policy", "always_underdetermined")))
    if cfg.kind == "replay":
        return ReplayProvider(cfg, cfg.extra.get("table", {}))
    raise ValueError(f"unknown provider kind {cfg.kind!r}")
