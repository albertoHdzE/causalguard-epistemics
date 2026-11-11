"""R5 shared interfaces (Prediction, CountResult, InvestigationStep, AssumptionCheck) and cumulative resources.

Every record is a plain JSON-able dict produced by ``to_json`` after ``validate``; validation is strict (exact key
sets, integer types for exact counts, state-dependent nulls).  A record that fails validation is a defect, never
silently repaired.

Resource accounting (BATCH_CONTRACT.json "resource_limits"):
  * model requests: llm.harness.CallBudget (owner) with an R5 ledger and per-phase caps; every physical attempt
    reserves a ledger line BEFORE dispatch, so interrupted requests count as spent;
  * offline CPU-hours: the sum of ``seconds`` over EVERY stored attempt (ok and failed) of every R5 run, an upper
    bound on CPU for single-threaded workers (wall >= CPU), grouped by track;
  * model-server execution hours: the sum of request wall latencies recorded by the episode runner plus logged
    model-load time (conservative; server-side idle time is not charged).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- limits (contract copy; test-checked)

LIMITS = {
    "local_model_requests_total": 3072,
    "phase_caps": {"A-calibration": 512, "A-evaluation": 2048, "A-repair": 512},
    "offline_cpu_hours_total": 64.0,
    "offline_cpu_hour_allocations": {"G": 24.0, "C": 28.0, "M": 8.0, "A": 4.0},
    "model_server_hours": 12.0,
    "max_offline_workers": 4,
    "memory_limit_bytes": None,          # filled by memory_limit_bytes()
}
CALL_LEDGER = "RUNS/r5-calls/ledger.jsonl"


def memory_limit_bytes() -> int:
    """min(32 GiB, 25 % of physical RAM)."""
    import os
    phys = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    return min(32 << 30, phys // 4)


class ContractError(ValueError):
    pass


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _req(d: dict, keys: tuple[str, ...], where: str) -> None:
    missing = [k for k in keys if k not in d]
    extra = sorted(set(d) - set(keys))
    if missing or extra:
        raise ContractError(f"{where}: missing {missing} unexpected {extra}")


# --------------------------------------------------------------------------- Prediction (Track G)

PREDICTION_STATUS = ("exact", "bounded", "refused_resource", "unsupported", "inconsistent_evidence")


@dataclass
class Prediction:
    """P(target node = 1) for one scheduled query under one predictor.

    ``num/den`` are exact integers (or Fraction parts as decimal strings when they exceed JSON-safe ints) when
    status == 'exact'; status 'bounded' carries [lo, hi] with hi - lo the certified error; every other status
    has p = None and a reason.  ``target_value_convention`` is fixed to 'P(node=1)': literal queries are converted
    before scoring (tests check the conversion)."""
    query_id: str
    source_group_id: str
    run_snapshot: str
    predictor: str
    prior_identity: str
    status: str
    p: float | None
    num: str | None = None
    den: str | None = None
    lo: float | None = None
    hi: float | None = None
    target_value_convention: str = "P(node=1)"
    reason: str | None = None
    cost_s: float = 0.0

    def validate(self) -> "Prediction":
        if self.status not in PREDICTION_STATUS:
            raise ContractError(f"bad status {self.status}")
        if self.target_value_convention != "P(node=1)":
            raise ContractError("target convention must be P(node=1)")
        if self.status == "exact":
            if self.p is None or self.num is None or self.den is None:
                raise ContractError("exact prediction needs p, num, den")
            if not (0.0 <= self.p <= 1.0):
                raise ContractError("p outside [0,1]")
        elif self.status == "bounded":
            if None in (self.p, self.lo, self.hi) or not (0 <= self.lo <= self.p <= self.hi <= 1):
                raise ContractError("bounded prediction needs lo <= p <= hi in [0,1]")
        else:
            if self.p is not None or not self.reason:
                raise ContractError("non-exact status needs p = None and a reason")
        return self

    def to_json(self) -> dict:
        return asdict(self.validate())


# --------------------------------------------------------------------------- CountResult (Track C)

CERT_LEVELS = ("witness_replay", "trusted_exact_computation", "sat_solver_assertion", "checked_rup_proof",
               "application_authentication", "none")


@dataclass
class CountResult:
    """Distinct-mechanism counts for one query under one backend.  ``semantics`` must be
    'distinct_canonical_mechanisms' (never encodings or auxiliary SAT assignments)."""
    backend: str
    backend_version: str
    semantics: str
    projection: str
    evidence_hash: str
    query_hash: str
    status: str                          # exact | refused_resource | unsupported | inconsistent | timeout
    num: int | None
    den: int | None
    exact: bool
    certificate_levels: list[str] = field(default_factory=list)
    witness_refs: list[str] = field(default_factory=list)
    costs: dict = field(default_factory=dict)
    reason: str | None = None

    def validate(self) -> "CountResult":
        if self.semantics != "distinct_canonical_mechanisms":
            raise ContractError("CountResult semantics must be distinct_canonical_mechanisms")
        if self.status == "exact":
            if not (_is_int(self.num) and _is_int(self.den)) or not (0 <= self.num <= self.den) or not self.exact:
                raise ContractError("exact CountResult needs integer 0 <= num <= den")
        else:
            if self.num is not None or self.den is not None or self.exact:
                raise ContractError("non-exact CountResult must carry null counts")
            if not self.reason:
                raise ContractError("non-exact CountResult needs a reason")
        bad = [c for c in self.certificate_levels if c not in CERT_LEVELS]
        if bad:
            raise ContractError(f"unknown certificate levels {bad}")
        return self

    def to_json(self) -> dict:
        d = asdict(self.validate())
        d["num"] = None if self.num is None else str(self.num)
        d["den"] = None if self.den is None else str(self.den)
        return d


# --------------------------------------------------------------------------- InvestigationStep (Track A)

STEP_KEYS = ("step", "prior_state_hash", "proposed", "accepted", "menu_hash", "purchased", "measurement_cost",
             "updated_state_hash", "model_calls", "tool_calls")


def investigation_step(**kw) -> dict:
    _req(kw, STEP_KEYS, "InvestigationStep")
    if kw["purchased"] is not None and set(kw["purchased"]) != {"menu_index", "node", "value"}:
        raise ContractError("purchased must be {menu_index, node, value} or null")
    if not (_is_int(kw["model_calls"]) and _is_int(kw["tool_calls"])):
        raise ContractError("call counts must be integers")
    return dict(kw)


# --------------------------------------------------------------------------- AssumptionCheck (Track M)

AC_KEYS = ("declared_class", "alternative_classes", "evidence_consistent", "verdict_per_class",
           "aggregate_guarantee", "certificate_level", "abstention_reason")
FORBIDDEN_AC_KEYS = ("misspecified", "hidden_class", "true_class", "truth")


def assumption_check(**kw) -> dict:
    """The API never carries a hidden 'misspecified' flag; only public classes, evidence and verdicts."""
    _req(kw, AC_KEYS, "AssumptionCheck")
    blob = json.dumps(kw)
    if any(f'"{k}"' in blob for k in FORBIDDEN_AC_KEYS):
        raise ContractError("AssumptionCheck must not carry hidden-truth fields")
    if kw["aggregate_guarantee"] not in ("verified_all_classes", "verified_declared_only", "underdetermined",
                                         "abstain", "inconsistent", "unsupported"):
        raise ContractError("bad aggregate_guarantee")
    return dict(kw)


# --------------------------------------------------------------------------- cumulative offline resources

R5_RUN_PREFIX = "r5-"


def offline_usage(runs_root: Path) -> dict:
    """Conservative CPU-hours by track from every stored attempt of every R5 run (ok and failed)."""
    out: dict[str, float] = {}
    peak = 0
    per_run = {}
    for d in sorted(Path(runs_root).glob(f"{R5_RUN_PREFIX}*")):
        if not (d / "plan.json").exists():
            continue
        track = json.loads((d / "plan.json").read_text()).get("config", {}).get("r5_track", "?")
        secs = 0.0
        for f in d.glob("attempts/*/*.json"):
            try:
                rec = json.loads(f.read_text())
            except json.JSONDecodeError:
                continue
            secs += float(rec.get("seconds", 0.0))
            peak = max(peak, int(rec.get("worker_peak_rss_bytes") or 0))
        out[track] = out.get(track, 0.0) + secs / 3600
        per_run[d.name] = {"track": track, "cpu_hours_upper": secs / 3600}
    return {"by_track_cpu_hours_upper": out, "total_cpu_hours_upper": sum(out.values()),
            "max_worker_peak_rss_bytes": peak, "runs": per_run}


def call_usage(ledger: Path) -> dict:
    """Model requests by phase from the R5 call ledger (one line per physical attempt, reserved pre-dispatch)."""
    by = {}
    tot = 0
    if Path(ledger).exists():
        for line in Path(ledger).read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                by[rec.get("phase", "?")] = by.get(rec.get("phase", "?"), 0) + 1
                tot += 1
    return {"total": tot, "by_phase": by}
