"""S3 arm harness: A / B / C / D / D-label / E and transfer probes T_A / T_D for one world.

Owner of: conversation construction per arm, shared-first-answer reuse, C aggregation, D feedback
loop, call caps, physical vs logical cost accounting.

Arms (per item i of a world)
  A        initial answer, temperature ``temperature`` (0).  Call ``i{i}/A``.  This single call is the
           shared first answer of B, C, D and D-label (reused, never re-sent).
  B        same conversation + one self-critique turn (no external information).  ``i{i}/B``.
  C        the shared first answer + ``c_extra_samples`` (2) FRESH-context draws at
           ``sample_temperature`` (0.7), each with its own derived seed.  ``i{i}/C1``, ``i{i}/C2``.
           Verdict: strict majority of all members (>= 2 of 3); ties, no strict majority or no valid vote => abstain.
           Probabilities: arithmetic mean of valid vectors only; none valid => invalid.
  D        same conversation + exactly min(2, feedback_rounds) witness-feedback rounds
           (s3_tasks.witness_feedback, claim = previous turn's parsed verdict or None).  Stops early
           only on provider failure.  Final = last round.  ``i{i}/D1``, ``i{i}/D2``.
  D_label  same conversation + one turn with s3_tasks.label_feedback (privileged control).  ``i{i}/DL``.
  E        s3_tasks.solver_answer (no LLM call).
  T_A      conversation of A on the source item, then the target item's prompt (no feedback).  ``T_A``.
  T_D      full D conversation on the source item, then the target item's prompt.  ``T_D``.
Hidden information: ``private`` is touched only by witness_feedback / label_feedback / solver_answer.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import re
import time
from collections import Counter
from pathlib import Path

from ..s3_tasks import VERDICT_LABELS, label_feedback, render_item_prompt, solver_answer, witness_feedback
from .parse import parse_answer, verdict_vector_coherent
from .providers import BaseProvider, CapExceeded

ARMS = ("A", "B", "C", "D", "D_label", "E", "T_A", "T_D")
LLM_ITEM_ARMS = ("A", "B", "C", "D", "D_label")
CRITIQUE_PROMPT = ("Critically review your previous answer. Check it step by step against every observation and "
                   "against the definitions given above, and look for mistakes. Keep the review concise, then END your "
                   "reply with your final answer as a single JSON object in the same format.")
_LABEL_RE = re.compile(r"\b(" + "|".join(VERDICT_LABELS) + r")\b", re.IGNORECASE)


class LeakageError(AssertionError):
    pass


def contains_label(text: str) -> bool:
    return bool(_LABEL_RE.search(text))


class CallBudget:
    """Physical-attempt caps.  Per-world cap counted in-process; the global cap is enforced across
    processes and resumes through an append-only ledger file (one line per physical attempt, flock'd).
    Without a ledger the global cap only sees this world's attempts."""

    def __init__(self, world_cap: int | None, global_cap: int | None, ledger: str | Path | None = None,
                 world_id: str = "", phase: str | None = None, phase_cap: int | None = None):
        """``phase``/``phase_cap`` (R5): an additional cap on the ledger lines carrying the same phase label
        (suballocations such as calibration / evaluation / repair); the global cap still counts every line."""
        self.world_cap, self.global_cap = world_cap, global_cap
        self.ledger = Path(ledger) if ledger else None
        self.world_id = world_id
        self.phase, self.phase_cap = phase, phase_cap
        self.n = 0
        self.current = ""

    def before_attempt(self) -> None:
        if self.world_cap is not None and self.n >= self.world_cap:
            raise CapExceeded("world_cap_reached", f"{self.n} >= {self.world_cap}")
        if self.global_cap is not None:
            if self.ledger is None:
                if self.n >= self.global_cap:
                    raise CapExceeded("global_cap_reached", f"{self.n} >= {self.global_cap}")
            else:
                self.ledger.parent.mkdir(parents=True, exist_ok=True)
                with self.ledger.open("a+") as fh:
                    fcntl.flock(fh, fcntl.LOCK_EX)
                    try:
                        fh.seek(0)
                        recs = [json.loads(line) for line in fh if line.strip()]
                        used = ledger_used(recs)
                        if used >= self.global_cap:
                            raise CapExceeded("global_cap_reached", f"{used} >= {self.global_cap}")
                        if self.phase_cap is not None:
                            pu = ledger_used([r for r in recs if r.get("phase") == self.phase])
                            if pu >= self.phase_cap:
                                raise CapExceeded("phase_cap_reached", f"{self.phase}: {pu} >= {self.phase_cap}")
                        fh.seek(0, 2)
                        rec = {"world_id": self.world_id, "call": self.current}
                        if self.phase is not None:
                            rec["phase"] = self.phase
                        fh.write(json.dumps(rec) + "\n")
                        fh.flush()
                    finally:
                        fcntl.flock(fh, fcntl.LOCK_UN)
        self.n += 1

    def void_last(self, kind: str, **info) -> None:
        """SPRINT (amendment v2-a3): the last counted attempt reached no model (a usage-limit rejection).  A ledger
        line ``{kind, voids_slot: true, ...}`` cancels its slot for the global and phase caps, and the per-world
        count is undone; the rejection itself stays on record and is counted separately."""
        self.n = max(0, self.n - 1)
        if self.ledger is None:
            return
        rec = {"kind": kind, "voids_slot": True, "world_id": self.world_id, "call": self.current, "t": time.time(),
               **info}
        if self.phase is not None:
            rec["phase"] = self.phase
        with self.ledger.open("a") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)


def ledger_used(recs: list[dict]) -> int:
    """Slots used in a call ledger: request lines (no ``kind``) minus lines that void a slot (v2-a3)."""
    return sum(1 for r in recs if "kind" not in r) - sum(1 for r in recs if r.get("voids_slot"))


def derive_seed(base: int | None, world_id: str, call_id: str) -> int | None:
    if base is None:
        return None
    h = hashlib.sha256(f"{base}|{world_id}|{call_id}".encode()).hexdigest()
    return int(h[:8], 16) & 0x7FFFFFFF


def _answer(parsed: dict) -> dict:
    return {k: parsed[k] for k in ("status", "verdict", "verdict_valid", "probabilities", "probs_valid", "flags")}


def _failed(status: str, flag: str) -> dict:
    return {"status": status, "verdict": None, "verdict_valid": False, "probabilities": None, "probs_valid": False,
            "flags": [flag]}


def aggregate_c(members: list[dict]) -> dict:
    """Deterministic C aggregation over member answers (dicts from parse_answer)."""
    votes = [m["verdict"] for m in members if m["verdict_valid"]]
    counts = Counter(votes)
    verdict = None
    flags = []
    # strict majority of ALL members (>= 2 of 3); anything else (ties, invalid members) abstains
    need = len(members) // 2 + 1
    if counts:
        top = max(counts.values())
        winners = sorted(v for v, c in counts.items() if c == top)
        if len(winners) == 1 and top >= need:
            verdict = winners[0]
        elif len(winners) > 1:
            flags.append("vote_tie")
        else:
            flags.append("no_strict_majority")
    else:
        flags.append("no_valid_votes")
    vecs = [m["probabilities"] for m in members if m["probs_valid"]]
    probs = ({k: sum(v[k] for v in vecs) / len(vecs) for k in VERDICT_LABELS} if vecs else None)
    if verdict is not None and probs is not None and not verdict_vector_coherent(verdict, probs):
        # the majority verdict and the MEAN vector disagree: an aggregate disagreement, not a model contradiction
        flags.append("aggregate_verdict_prob_mismatch")
    if verdict is None:
        status = "abstain"
    elif probs is None:
        status = "invalid_probabilities"
    else:
        status = "ok"
    return {"status": status, "verdict": verdict, "verdict_valid": verdict is not None, "probabilities": probs,
            "probs_valid": probs is not None, "flags": flags, "n_members": len(members), "n_valid_votes": len(votes),
            "n_valid_vectors": len(vecs), "vote_counts": dict(sorted(counts.items())),
            "invalid_members": [i for i, m in enumerate(members) if not (m["verdict_valid"] and m["probs_valid"])],
            "member_statuses": [m["status"] for m in members]}


DEFAULT_HARNESS = {"arms": list(ARMS), "feedback_rounds": 2, "c_extra_samples": 2,
                   "transfer": {"source_item": 0, "target_item": 1}}


class WorldHarness:
    def __init__(self, provider: BaseProvider, public: dict, private: dict, hcfg: dict | None = None,
                 budget: CallBudget | None = None):
        self.p = provider
        self.public = public
        self._private = private
        self.h = {**DEFAULT_HARNESS, **(hcfg or {})}
        bad = set(self.h["arms"]) - set(ARMS)
        if bad:
            raise ValueError(f"unknown arms {bad}")
        if "T_D" in self.h["arms"] and "D" not in self.h["arms"]:
            raise ValueError("T_D requires arm D")
        self.budget = budget or CallBudget(None, None)
        self.world_id = public["world_id"]
        self.calls: dict[str, dict] = {}
        self.order: list[str] = []
        self.arms: dict[str, dict] = {a: {} for a in self.h["arms"]}
        self.feedback: dict[str, list] = {}
        self.status = "complete"
        self.cap_detail = None

    # ---- low level -------------------------------------------------------------------------
    def _call(self, call_id: str, messages: list[dict], temperature: float) -> dict:
        assert call_id not in self.calls, f"call {call_id} would be sent twice"
        self.budget.current = call_id
        seed = derive_seed(self.p.cfg.seed, self.world_id, call_id)
        res = self.p.chat(messages, temperature, seed, before_attempt=self.budget.before_attempt)
        res["parsed"] = parse_answer(res["raw_output"], res["ok"])
        res["call_id"] = call_id
        self.calls[call_id] = res
        self.order.append(call_id)
        return res

    def _conv_after(self, call_id: str) -> list[dict] | None:
        """Messages of a call followed by its assistant reply (None if the call had no content)."""
        c = self.calls.get(call_id)
        if c is None or not c["ok"]:
            return None
        return c["messages"] + [{"role": "assistant", "content": c["raw_output"]}]

    # ---- arms --------------------------------------------------------------------------------
    def _arm_items(self) -> list[int]:
        return list(range(len(self.public["items"])))

    def run(self) -> dict:
        arms = self.h["arms"]
        t0 = self.p.cfg.temperature
        try:
            for i in self._arm_items():
                need_first = any(a in arms for a in LLM_ITEM_ARMS) or (
                    i == self.h["transfer"]["source_item"] and ("T_A" in arms or "T_D" in arms)) or (
                    i == self.h["transfer"]["target_item"] and ("T_A" in arms or "T_D" in arms))
                if not need_first:
                    continue
                a_id = f"i{i}/A"
                self._call(a_id, [{"role": "user", "content": render_item_prompt(self.public, i)}], t0)
                first = self.calls[a_id]
                if "A" in arms:
                    self.arms["A"][i] = {"final": _answer(first["parsed"]), "calls": [a_id], "logical": [a_id]}
                if "B" in arms:
                    self._arm_b(i, a_id)
                if "C" in arms:
                    self._arm_c(i, a_id)
                if "D" in arms:
                    self._arm_d(i, a_id)
                if "D_label" in arms:
                    self._arm_dl(i, a_id)
            if "E" in arms:
                for i in self._arm_items():
                    sa = solver_answer(self._private, i)
                    self.arms["E"][i] = {"final": {"status": "ok", "verdict": sa["verdict"], "verdict_valid": True,
                                                   "probabilities": sa["probabilities"], "probs_valid": True,
                                                   "flags": ["symbolic_solver"]}, "calls": [], "logical": []}
            if "T_A" in arms or "T_D" in arms:
                self._transfer()
        except CapExceeded as e:
            self.status = e.scope
            self.cap_detail = str(e)
        return self.result()

    def _arm_b(self, i: int, a_id: str) -> None:
        conv = self._conv_after(a_id)
        if conv is None:
            self.arms["B"][i] = {"final": _failed("provider_failure", "dependent_on_failed_first_answer"),
                                 "calls": [], "logical": [a_id]}
            return
        b_id = f"i{i}/B"
        self._call(b_id, conv + [{"role": "user", "content": CRITIQUE_PROMPT}], self.p.cfg.temperature)
        self.arms["B"][i] = {"final": _answer(self.calls[b_id]["parsed"]), "first": a_id, "calls": [b_id],
                             "logical": [a_id, b_id]}

    def _arm_c(self, i: int, a_id: str) -> None:
        ids = [a_id]
        for s in range(1, int(self.h["c_extra_samples"]) + 1):
            cid = f"i{i}/C{s}"
            self._call(cid, [{"role": "user", "content": render_item_prompt(self.public, i)}],
                       self.p.cfg.sample_temperature)
            ids.append(cid)
        agg = aggregate_c([self.calls[c]["parsed"] for c in ids])
        self.arms["C"][i] = {"final": agg, "members": ids, "calls": ids[1:], "logical": ids}

    def _arm_d(self, i: int, a_id: str) -> None:
        conv = self._conv_after(a_id)
        rounds = min(2, int(self.h["feedback_rounds"]))
        if conv is None:
            self.arms["D"][i] = {"final": _failed("provider_failure", "dependent_on_failed_first_answer"),
                                 "rounds": [], "calls": [], "logical": [a_id]}
            return
        prev = self.calls[a_id]
        ids = []
        rounds_log = []
        for r in range(1, rounds + 1):
            claimed = prev["parsed"]["verdict"] if prev["parsed"]["verdict_valid"] else None
            text, prov = witness_feedback(self._private, i, claimed)
            if contains_label(text):
                raise LeakageError(f"D feedback for item {i} contains a verdict label")
            did = f"i{i}/D{r}"
            self._call(did, conv + [{"role": "user", "content": text}], self.p.cfg.temperature)
            ids.append(did)
            rounds_log.append({"round": r, "call": did, "feedback_provenance": prov,
                               "answer": _answer(self.calls[did]["parsed"])})
            conv = self._conv_after(did)
            prev = self.calls[did]
            if conv is None:  # provider failure: stop, final answer is this failed round
                break
        self.arms["D"][i] = {"final": _answer(prev["parsed"]), "rounds": rounds_log, "rounds_planned": rounds,
                             "calls": ids, "logical": [a_id] + ids}

    def _arm_dl(self, i: int, a_id: str) -> None:
        conv = self._conv_after(a_id)
        if conv is None:
            self.arms["D_label"][i] = {"final": _failed("provider_failure", "dependent_on_failed_first_answer"),
                                       "calls": [], "logical": [a_id]}
            return
        lid = f"i{i}/DL"
        self._call(lid, conv + [{"role": "user", "content": label_feedback(self._private, i)}],
                   self.p.cfg.temperature)
        self.arms["D_label"][i] = {"final": _answer(self.calls[lid]["parsed"]), "calls": [lid],
                                   "logical": [a_id, lid], "feedback_provenance": {"source": "reference_verdict_label"}}

    def _transfer(self) -> None:
        src, tgt = self.h["transfer"]["source_item"], self.h["transfer"]["target_item"]
        prompt = [{"role": "user", "content": render_item_prompt(self.public, tgt)}]
        if "T_A" in self.h["arms"]:
            a_id = f"i{src}/A"
            conv = self._conv_after(a_id)
            if conv is None:
                fin, calls = _failed("provider_failure", "dependent_on_failed_source_context"), []
            else:
                self._call("T_A", conv + prompt, self.p.cfg.temperature)
                fin, calls = _answer(self.calls["T_A"]["parsed"]), ["T_A"]
            self.arms["T_A"][tgt] = {"final": fin, "calls": calls, "logical": [a_id] + calls,
                                     "source_item": src, "target_item": tgt}
        if "T_D" in self.h["arms"]:
            d = self.arms["D"].get(src)
            logical = d["logical"] if d else []
            conv = self._conv_after(d["calls"][-1]) if d and d["calls"] else None
            if conv is None or len(d["calls"]) < d.get("rounds_planned", 0):
                fin, calls = _failed("provider_failure", "dependent_on_failed_source_context"), []
            else:
                self._call("T_D", conv + prompt, self.p.cfg.temperature)
                fin, calls = _answer(self.calls["T_D"]["parsed"]), ["T_D"]
            self.arms["T_D"][tgt] = {"final": fin, "calls": calls, "logical": logical + calls,
                                     "source_item": src, "target_item": tgt}

    # ---- accounting ------------------------------------------------------------------------
    def _cost_of(self, call_ids: list[str]) -> dict:
        att = [a for c in call_ids if c in self.calls for a in self.calls[c]["attempts"]]
        def tok(key):
            vals = [a[key] for a in att if a.get(key) is not None]
            return sum(vals) if vals else None
        return {"logical_calls": sum(1 for c in call_ids if c in self.calls), "attempts": len(att),
                "latency_s": round(sum(a["latency_s"] for a in att), 4), "prompt_tokens": tok("prompt_tokens"),
                "completion_tokens": tok("completion_tokens")}

    def result(self) -> dict:
        physical = self._cost_of(self.order)
        per_arm = {}
        for arm, items in self.arms.items():
            ids = [c for v in items.values() for c in v["logical"]]
            per_arm[arm] = self._cost_of(ids)
        total_logical = sum(v["attempts"] for v in per_arm.values())
        arms_out = {arm: {str(i): v for i, v in items.items()} for arm, items in self.arms.items()}
        return {"world_status": self.status, "cap_detail": self.cap_detail, "calls": self.calls,
                "call_order": self.order, "arms": arms_out,
                "cost": {"physical": physical, "physical_attempts_counted_by_budget": self.budget.n,
                         "logical_standalone_by_arm": per_arm,
                         "attempts_saved_by_sharing": total_logical - physical["attempts"]}}


# =========================================================================== iteration 2 harness (P6)
#
# Arms on base items (roles balanced/natural; indices with role in BASE_ROLES):
#   A        initial answer (shared first turn of every revision arm; sent once)
#   B2       two self-critique turns                         i{i}/B2_1, i{i}/B2_2
#   C        A + 2 fresh-context samples at sample_temperature; strict majority of 3 (explicit 2-call budget)
#   D_cert   turn 1: label + mechanistic certificate (privileged); turn 2: the B2 critique prompt
#   D_label  turn 1: the same label, no certificate;           turn 2: the B2 critique prompt
#   D_sample turn 1: K=2 world-level uniformly sampled compatible mechanisms (public); turn 2: critique prompt
#   E        exact solver answer (oracle ceiling; not an independent validation of the backend)
# Transformed items (complement_of / renamed_of): A only.
# Transfer target item (role transfer_target, fresh question): A_T = fresh-context answer; probes
#   T_A, T_B2, T_cert, T_label, T_sample = the complete source-item conversation of that arm, then the target prompt.
# Every revision arm has exactly 2 extra turns after A; realized tokens/time are recorded per call.

V2_ARMS = ("A", "B2", "C", "D_cert", "D_label", "D_sample", "E", "A_T", "T_A", "T_B2", "T_cert", "T_label",
           "T_sample")
V2_REVISION_ARMS = ("B2", "D_cert", "D_label", "D_sample")
V2_PROBES = {"T_A": "A", "T_B2": "B2", "T_cert": "D_cert", "T_label": "D_label", "T_sample": "D_sample"}
BASE_ROLES = ("balanced", "natural")
V2_DEFAULT = {"arms": list(V2_ARMS), "c_extra_samples": 2, "transfer_source_item": 0}


class WorldHarnessV2(WorldHarness):
    def __init__(self, provider, public, private, hcfg=None, budget=None):
        h = {**V2_DEFAULT, **(hcfg or {})}
        bad = set(h["arms"]) - set(V2_ARMS)
        if bad:
            raise ValueError(f"unknown v2 arms {bad}")
        self.p = provider
        self.public = public
        self._private = private
        self.h = h
        self.budget = budget or CallBudget(None, None)
        self.world_id = public["world_id"]
        self.calls, self.order = {}, []
        self.arms = {a: {} for a in h["arms"]}
        self.status, self.cap_detail = "complete", None

    def _prompt(self, i):
        from ..s3_tasks import render_item_prompt_v2
        return [{"role": "user", "content": render_item_prompt_v2(self.public, i)}]

    def _feedback(self, arm, i):
        from ..s3_tasks import cert_feedback, label_feedback_v2, sample_feedback
        if arm == "B2":
            return CRITIQUE_PROMPT, {"source": "self_critique"}
        if arm == "D_cert":
            return cert_feedback(self._private, i)
        if arm == "D_label":
            return label_feedback_v2(self._private, i)
        if arm == "D_sample":
            text, prov = sample_feedback(self.public, i)
            if contains_label(text):
                raise LeakageError("D_sample feedback contains a verdict label")
            return text, prov
        raise ValueError(arm)

    def _revise(self, arm, i, a_id):
        conv = self._conv_after(a_id)
        if conv is None:
            self.arms[arm][i] = {"final": _failed("provider_failure", "dependent_on_failed_first_answer"),
                                 "rounds": [], "calls": [], "logical": [a_id]}
            return
        ids, rounds = [], []
        tag = {"B2": "B2", "D_cert": "DC", "D_label": "DL", "D_sample": "DS"}[arm]
        last = self.calls[a_id]
        for r in (1, 2):
            text, prov = self._feedback(arm, i) if r == 1 else (CRITIQUE_PROMPT, {"source": "self_critique"})
            cid = f"i{i}/{tag}{r}"
            self._call(cid, conv + [{"role": "user", "content": text}], self.p.cfg.temperature)
            ids.append(cid)
            last = self.calls[cid]
            rounds.append({"round": r, "call": cid, "feedback_provenance": prov, "feedback_chars": len(text),
                           "answer": _answer(last["parsed"])})
            conv = self._conv_after(cid)
            if conv is None:
                break
        self.arms[arm][i] = {"final": _answer(last["parsed"]), "rounds": rounds, "rounds_planned": 2,
                             "calls": ids, "logical": [a_id] + ids}

    def run(self) -> dict:
        arms = self.h["arms"]
        roles = [it["role"] for it in self.public["items"]]
        base = [i for i, r in enumerate(roles) if r in BASE_ROLES]
        transformed = [i for i, r in enumerate(roles) if r.startswith(("complement_of", "renamed_of"))]
        target = [i for i, r in enumerate(roles) if r == "transfer_target"]
        t0 = self.p.cfg.temperature
        try:
            for i in base:
                a_id = f"i{i}/A"
                self._call(a_id, self._prompt(i), t0)
                self.arms["A"][i] = {"final": _answer(self.calls[a_id]["parsed"]), "calls": [a_id], "logical": [a_id]}
                for arm in V2_REVISION_ARMS:
                    if arm in arms:
                        self._revise(arm, i, a_id)
                if "C" in arms:
                    self._arm_c_v2(i, a_id)
            for i in transformed:
                a_id = f"i{i}/A"
                self._call(a_id, self._prompt(i), t0)
                self.arms["A"][i] = {"final": _answer(self.calls[a_id]["parsed"]), "calls": [a_id], "logical": [a_id]}
            if "E" in arms:
                for i in range(len(roles)):
                    sa = solver_answer(self._private, i)
                    self.arms["E"][i] = {"final": {"status": "ok", "verdict": sa["verdict"], "verdict_valid": True,
                                                   "probabilities": sa["probabilities"], "probs_valid": True,
                                                   "flags": ["symbolic_solver_oracle"]}, "calls": [], "logical": []}
            for tgt in target:
                if "A_T" in arms:
                    self._call(f"i{tgt}/A", self._prompt(tgt), t0)
                    self.arms["A_T"][tgt] = {"final": _answer(self.calls[f"i{tgt}/A"]["parsed"]),
                                             "calls": [f"i{tgt}/A"], "logical": [f"i{tgt}/A"]}
                src = base[int(self.h["transfer_source_item"])]
                for probe, arm in V2_PROBES.items():
                    if probe not in arms:
                        continue
                    srcrec = self.arms.get(arm, {}).get(src)
                    if srcrec is None:
                        conv, complete = None, False
                    elif arm == "A":
                        conv, complete = self._conv_after(f"i{src}/A"), True
                    else:
                        complete = len(srcrec["calls"]) == srcrec["rounds_planned"]
                        conv = self._conv_after(srcrec["calls"][-1]) if srcrec["calls"] else None
                    if conv is None or not complete:
                        fin, calls = _failed("provider_failure", "dependent_on_failed_source_context"), []
                    else:
                        cid = f"{probe}"
                        self._call(cid, conv + self._prompt(tgt), t0)
                        fin, calls = _answer(self.calls[cid]["parsed"]), [cid]
                    self.arms[probe][tgt] = {"final": fin, "calls": calls,
                                             "logical": (srcrec["logical"] if srcrec else []) + calls,
                                             "source_item": src, "target_item": tgt,
                                             "context_chars": sum(len(m["content"]) for m in (conv or []))}
        except CapExceeded as e:
            self.status = e.scope
            self.cap_detail = str(e)
        return self.result()

    def _arm_c_v2(self, i, a_id):
        ids = [a_id]
        for s in range(1, int(self.h["c_extra_samples"]) + 1):
            cid = f"i{i}/C{s}"
            self._call(cid, self._prompt(i), self.p.cfg.sample_temperature)
            ids.append(cid)
        agg = aggregate_c([self.calls[c]["parsed"] for c in ids])
        self.arms["C"][i] = {"final": agg, "members": ids, "calls": ids[1:], "logical": ids}
