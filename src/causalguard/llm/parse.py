"""Strict, deterministic parsing of S3 model answers.  No silent repair, no model-based repair.

Expected answer: a JSON object
    {"verdict": "entailed"|"refuted"|"underdetermined",
     "probabilities": {"entailed": p1, "refuted": p2, "underdetermined": p3},
     "reason": "<short sentence>"}

Deterministic extraction (the ONLY transformations applied before ``json.loads``):
  1. ``<think>...</think>`` blocks are removed (an unclosed ``<think>`` removes everything after
     it); flag ``think_stripped``.
  2. If the whole remaining text (whitespace-trimmed) is valid JSON it is used as is.
  3. Otherwise the LAST top-level balanced ``{...}`` substring is extracted by a brace scanner that
     respects JSON string literals and escapes; this covers ```json fences and surrounding prose, and
     takes the FINAL answer when a reply (e.g. a self-critique) quotes an earlier answer first.  If that
     last object does not parse, the answer is invalid_json (no fallback to earlier objects).
     (Changed from FIRST to LAST before the v2 pilot; see DECISIONS.md D19.)
     Flag ``extracted_object``.  Nothing else (no quote fixing, no trailing-comma removal, ...).

Status taxonomy (one value per answer; precedence top to bottom):
  provider_failure       no content (transport/fatal provider failure)
  invalid_json           no parseable JSON object
  semantic_error         JSON parsed but it is not an answer object: the top-level value is not an
                         object, or the object has neither a 'verdict' nor a 'probabilities' key
  abstain                verdict is an explicit abstention ('abstain', 'abstention', 'unknown')
  invalid_verdict        verdict missing / not a string / not one of the three labels
  invalid_probabilities  probabilities missing, wrong keys, non-numeric, negative, non-finite, or
                         sum outside 1 +/- PROB_TOL
  ok                     valid verdict and valid probabilities
Verdict and probabilities are validated INDEPENDENTLY (``verdict_valid``, ``probs_valid``): an
answer with a valid verdict but invalid probabilities has status invalid_probabilities and keeps
its verdict for accuracy scoring.  A verdict that is not the argmax of the probabilities is NOT an
error; it is flagged ``verdict_prob_mismatch``.  Verdict matching is case-/whitespace-insensitive
and any such normalisation is flagged ``verdict_normalized``.
"""
from __future__ import annotations

import json
import math
import re

from ..s3_tasks import VERDICT_LABELS

PROB_TOL = 0.02
ABSTAIN_WORDS = ("abstain", "abstention", "unknown")
STATUSES = ("provider_failure", "invalid_json", "semantic_error", "abstain", "invalid_verdict",
            "invalid_probabilities", "ok")

_THINK_CLOSED = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_THINK_OPEN = re.compile(r"<think>.*\Z", re.DOTALL | re.IGNORECASE)


def strip_think(text: str) -> tuple[str, bool]:
    t = _THINK_CLOSED.sub("", text)
    t = _THINK_OPEN.sub("", t)
    return t, t != text


def first_balanced_object(text: str) -> str | None:
    """Return the first balanced {...} substring (string-literal aware), or None."""
    start = text.find("{")
    if start != -1:
        depth = 0
        in_str = False
        esc = False
        for j in range(start, len(text)):
            ch = text[j]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:j + 1]
    return None  # no '{' at all, or the first '{' never closes


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def check_probabilities(p) -> tuple[dict | None, str | None]:
    if not isinstance(p, dict):
        return None, "missing_or_not_object"
    if set(p) != set(VERDICT_LABELS):
        return None, f"keys {sorted(p)}"
    if not all(_is_number(p[k]) for k in VERDICT_LABELS):
        return None, "non_numeric"
    if any(p[k] < 0 for k in VERDICT_LABELS):
        return None, "negative"
    s = sum(float(p[k]) for k in VERDICT_LABELS)
    if abs(s - 1.0) > PROB_TOL:
        return None, f"sum={s:.4f}"
    return {k: float(p[k]) for k in VERDICT_LABELS}, None


def last_balanced_object(text: str) -> str | None:
    """Return the last top-level balanced {...} substring (string-literal aware), or None."""
    last = None
    depth = 0
    in_str = False
    esc = False
    start = -1
    for j, ch in enumerate(text):
        if depth > 0 and in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if depth > 0 and ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = j
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0:
                last = text[start:j + 1]
    return last


def parse_answer(raw: str | None, provider_ok: bool = True) -> dict:
    out = {"status": None, "verdict": None, "verdict_valid": False, "probabilities": None, "probs_valid": False,
           "prob_error": None, "reason": None, "flags": []}
    if not provider_ok or raw is None:
        out["status"] = "provider_failure"
        return out
    text, stripped = strip_think(raw)
    if stripped:
        out["flags"].append("think_stripped")
    text = text.strip()
    obj = None
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        sub = last_balanced_object(text)
        if sub is not None:
            try:
                obj = json.loads(sub)
                out["flags"].append("extracted_object")
            except (json.JSONDecodeError, ValueError):
                obj = None
    if obj is None:
        out["status"] = "invalid_json"
        return out
    if not isinstance(obj, dict) or ("verdict" not in obj and "probabilities" not in obj):
        out["status"] = "semantic_error"
        return out
    reason = obj.get("reason")
    out["reason"] = reason if isinstance(reason, str) else None
    if not isinstance(reason, str):
        out["flags"].append("reason_missing")
    probs, perr = check_probabilities(obj.get("probabilities"))
    out.update(probabilities=probs, probs_valid=probs is not None, prob_error=perr)
    v = obj.get("verdict")
    abstain = False
    if isinstance(v, str):
        norm = v.strip().lower()
        if norm in VERDICT_LABELS:
            out["verdict"], out["verdict_valid"] = norm, True
            if norm != v:
                out["flags"].append("verdict_normalized")
        elif norm in ABSTAIN_WORDS:
            abstain = True
    if out["verdict_valid"] and out["probs_valid"]:
        mx = max(probs.values())
        if probs[out["verdict"]] < mx:
            out["flags"].append("verdict_prob_mismatch")
    if abstain:
        out["status"] = "abstain"
    elif not out["verdict_valid"]:
        out["status"] = "invalid_verdict"
    elif not out["probs_valid"]:
        out["status"] = "invalid_probabilities"
    else:
        out["status"] = "ok"
    return out
