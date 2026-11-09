"""Typed, validated, immutable objects of the CausalGuard scientific contract.

Owner of: state/index conventions, node rules, networks, predicates (typed
Boolean grammar), interventions, queries, observations, evidence, hypothesis
classes, verdict/answer enums, certificates and canonical JSON serialization.

Conventions (docs/SEMANTICS.md):
* A state of an n-node network is an integer x in [0, 2**n); node i is bit i
  (LSB-first, weight 2**i).  ``state_from_bits([b0, b1, ...])`` is the inverse
  of ``bits_of(x, n)``.
* A node rule reads an ordered tuple of input nodes (ascending, distinct) and a
  local truth table ``table`` (int bitmask of length 2**k) where local index
  y = sum_t bit(x, inputs[t]) << t.
* Update is synchronous: node j reads the OLD state.

Status values are enums whose ``__bool__`` raises, so an invalid/unknown status
cannot be silently coerced into a truth value.
"""
from __future__ import annotations

import enum
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable

SCHEMA_VERSION = "1.0.0"
UPDATE_CONVENTION = "synchronous"
MAX_EXPLICIT_N = 4096  # hard validation bound on network size


class SemanticsError(ValueError):
    """Raised for malformed/invalid semantic objects."""


class _NoBool(enum.Enum):
    def __bool__(self):  # pragma: no cover - exercised in tests
        raise TypeError(f"{self.__class__.__name__}.{self.name} cannot be coerced to bool")

    def __str__(self) -> str:
        return self.value


class ModelAnswer(_NoBool):
    """Answer of a query against ONE fully specified mechanism."""
    TRUE = "true"
    FALSE = "false"
    INVALID_DOMAIN = "invalid_domain"        # empty admissible state set
    UNKNOWN_RESOURCE = "unknown_resource"    # computation hit a declared budget
    UNSUPPORTED = "unsupported"              # outside the supported grammar

    @staticmethod
    def of(value: bool) -> "ModelAnswer":
        if not isinstance(value, bool):
            raise TypeError("ModelAnswer.of expects a bool")
        return ModelAnswer.TRUE if value else ModelAnswer.FALSE

    def is_truth_value(self) -> bool:
        return self in (ModelAnswer.TRUE, ModelAnswer.FALSE)


class Verdict(_NoBool):
    """Evidence-relative verdict over a version space V(D)."""
    ENTAILED = "entailed"
    REFUTED = "refuted"
    UNDERDETERMINED = "underdetermined"
    INCONSISTENT = "inconsistent_evidence_or_class"   # V(D) empty
    UNKNOWN_RESOURCE = "unknown_resource"
    UNSUPPORTED = "unsupported"
    INVALID_DOMAIN = "invalid_domain"
    ABSTAIN = "abstain"   # operational abstention (LLM / tie), never a logical verdict

    @property
    def is_logical(self) -> bool:
        return self in (Verdict.ENTAILED, Verdict.REFUTED, Verdict.UNDERDETERMINED)


LOGICAL_VERDICTS = (Verdict.ENTAILED, Verdict.REFUTED, Verdict.UNDERDETERMINED)


class VerificationLevel(_NoBool):
    """How strongly a result was checked (stored per result)."""
    EXHAUSTIVE = "exhaustive"                 # every admissible state/model enumerated
    WITNESS_REPLAYED = "witness_replayed"     # SAT-type answer, witness replayed by independent simulator
    CHECKED_PROOF = "checked_proof"           # UNSAT with RUP proof checked by independent checker
    INDEPENDENT_EXACT = "independent_exact"   # independent exact method (e.g. BDD from direct rules) agrees
    SOLVER_ONLY = "solver_only"               # single solver claim, unverified
    CROSS_SOLVER = "cross_solver"             # two solvers agree; NOT a proof
    SAMPLED = "sampled"                       # sampled check only; never global exactness
    NONE = "none"


# --------------------------------------------------------------------------- states

def bits_of(x: int, n: int) -> tuple[int, ...]:
    if not (0 <= x < (1 << n)):
        raise SemanticsError(f"state {x} out of range for n={n}")
    return tuple((x >> i) & 1 for i in range(n))


def state_from_bits(bits: Iterable[int]) -> int:
    x = 0
    for i, b in enumerate(bits):
        if b not in (0, 1):
            raise SemanticsError(f"nonbinary state value {b!r}")
        x |= b << i
    return x


def _check_state(x: Any, n: int) -> int:
    if isinstance(x, bool) or not isinstance(x, int) or not (0 <= x < (1 << n)):
        raise SemanticsError(f"invalid state {x!r} for n={n}")
    return x


# --------------------------------------------------------------------------- rules

@dataclass(frozen=True)
class Rule:
    """Node update rule: output = table[ local index of inputs ]."""
    inputs: tuple[int, ...]
    table: int
    label: str | None = None   # descriptive metadata only; never semantic

    def __post_init__(self):
        if not isinstance(self.inputs, tuple):
            object.__setattr__(self, "inputs", tuple(self.inputs))
        ins = self.inputs
        if any(isinstance(i, bool) or not isinstance(i, int) or i < 0 for i in ins):
            raise SemanticsError(f"rule inputs must be nonnegative ints: {ins}")
        if list(ins) != sorted(set(ins)):
            raise SemanticsError(f"rule inputs must be ascending and distinct: {ins}")
        if len(ins) > 24:
            raise SemanticsError("local truth tables limited to in-degree <= 24")
        if isinstance(self.table, bool) or not isinstance(self.table, int):
            raise SemanticsError("rule table must be an int bitmask")
        if not (0 <= self.table < (1 << (1 << len(ins)))):
            raise SemanticsError(f"table {self.table} out of range for arity {len(ins)}")

    @property
    def arity(self) -> int:
        return len(self.inputs)

    def local_value(self, y: int) -> int:
        return (self.table >> y) & 1

    def essential_inputs(self) -> tuple[int, ...]:
        k = self.arity
        out = []
        for t in range(k):
            bit = 1 << t
            if any(((self.table >> y) & 1) != ((self.table >> (y | bit)) & 1)
                   for y in range(1 << k) if not y & bit):
                out.append(self.inputs[t])
        return tuple(out)

    def canonical(self) -> "Rule":
        """Equivalent rule restricted to essential inputs (label dropped)."""
        ess = self.essential_inputs()
        if ess == self.inputs:
            return Rule(self.inputs, self.table)
        pos = [self.inputs.index(e) for e in ess]
        table = 0
        for z in range(1 << len(ess)):
            y = 0
            for j, p in enumerate(pos):
                if (z >> j) & 1:
                    y |= 1 << p
            table |= ((self.table >> y) & 1) << z
        return Rule(ess, table)

    def to_json(self) -> dict:
        d = {"inputs": list(self.inputs), "table": self.table}
        if self.label is not None:
            d["label"] = self.label
        return d

    @staticmethod
    def from_json(d: dict) -> "Rule":
        return Rule(tuple(d["inputs"]), int(d["table"]), d.get("label"))


@dataclass(frozen=True)
class Network:
    n: int
    rules: tuple[Rule, ...]
    update: str = UPDATE_CONVENTION

    def __post_init__(self):
        if not isinstance(self.rules, tuple):
            object.__setattr__(self, "rules", tuple(self.rules))
        if isinstance(self.n, bool) or not isinstance(self.n, int) or not (1 <= self.n <= MAX_EXPLICIT_N):
            raise SemanticsError(f"invalid n={self.n}")
        if len(self.rules) != self.n:
            raise SemanticsError(f"need {self.n} rules, got {len(self.rules)}")
        if self.update != UPDATE_CONVENTION:
            raise SemanticsError(f"unsupported update convention {self.update!r} (distinct task id required)")
        for j, r in enumerate(self.rules):
            if not isinstance(r, Rule):
                raise SemanticsError(f"rule {j} is not a Rule")
            if r.inputs and r.inputs[-1] >= self.n:
                raise SemanticsError(f"rule {j} reads node {r.inputs[-1]} >= n={self.n}")

    def canonical(self) -> "Network":
        return Network(self.n, tuple(r.canonical() for r in self.rules))

    def to_json(self) -> dict:
        return {"n": self.n, "update": self.update, "rules": [r.to_json() for r in self.rules]}

    @staticmethod
    def from_json(d: dict) -> "Network":
        return Network(int(d["n"]), tuple(Rule.from_json(r) for r in d["rules"]), d.get("update", UPDATE_CONVENTION))

    def digest(self) -> str:
        return content_hash(self.canonical().to_json())


# --------------------------------------------------------------------------- predicates

PRED_OPS = ("lit", "and", "or", "not", "true", "false")


@dataclass(frozen=True)
class Pred:
    """Typed Boolean predicate over a state: literals, and/or/not, constants."""
    op: str
    node: int | None = None
    value: int | None = None
    args: tuple["Pred", ...] = ()

    def __post_init__(self):
        if self.op not in PRED_OPS:
            raise SemanticsError(f"unsupported predicate operator {self.op!r}")
        if not isinstance(self.args, tuple):
            object.__setattr__(self, "args", tuple(self.args))
        if self.op == "lit":
            if isinstance(self.node, bool) or not isinstance(self.node, int) or self.node < 0:
                raise SemanticsError("literal needs a node index")
            if self.value not in (0, 1) or isinstance(self.value, bool):
                raise SemanticsError("literal value must be 0 or 1")
            if self.args:
                raise SemanticsError("literal takes no args")
        elif self.op == "not":
            if len(self.args) != 1:
                raise SemanticsError("not takes exactly one arg")
        elif self.op in ("and", "or"):
            if len(self.args) < 1:
                raise SemanticsError(f"{self.op} needs >= 1 args")
        else:
            if self.args or self.node is not None:
                raise SemanticsError(f"{self.op} takes no operands")
        for a in self.args:
            if not isinstance(a, Pred):
                raise SemanticsError("predicate args must be Pred")

    # constructors
    @staticmethod
    def lit(node: int, value: int) -> "Pred":
        return Pred("lit", node=node, value=value)

    @staticmethod
    def and_(*args: "Pred") -> "Pred":
        return Pred("and", args=tuple(args))

    @staticmethod
    def or_(*args: "Pred") -> "Pred":
        return Pred("or", args=tuple(args))

    @staticmethod
    def not_(arg: "Pred") -> "Pred":
        return Pred("not", args=(arg,))

    @staticmethod
    def true() -> "Pred":
        return Pred("true")

    @staticmethod
    def false() -> "Pred":
        return Pred("false")

    @staticmethod
    def cube(assign: dict[int, int] | Iterable[tuple[int, int]]) -> "Pred":
        items = sorted(dict(assign).items())
        if not items:
            return Pred.true()
        return Pred.and_(*[Pred.lit(i, v) for i, v in items])

    def max_node(self) -> int:
        m = self.node if self.op == "lit" else -1
        for a in self.args:
            m = max(m, a.max_node())
        return m

    def nodes(self) -> set[int]:
        s = {self.node} if self.op == "lit" else set()
        for a in self.args:
            s |= a.nodes()
        return s

    def to_json(self) -> Any:
        if self.op == "lit":
            return {"op": "lit", "node": self.node, "value": self.value}
        if self.op in ("true", "false"):
            return {"op": self.op}
        return {"op": self.op, "args": [a.to_json() for a in self.args]}

    @staticmethod
    def from_json(d: Any) -> "Pred":
        if not isinstance(d, dict) or "op" not in d:
            raise SemanticsError(f"malformed predicate {d!r}")
        op = d["op"]
        if op == "lit":
            return Pred.lit(d["node"], d["value"])
        if op in ("true", "false"):
            return Pred(op)
        if op in ("and", "or", "not"):
            return Pred(op, args=tuple(Pred.from_json(a) for a in d.get("args", [])))
        raise SemanticsError(f"unsupported predicate operator {op!r}")

    def render(self) -> str:
        if self.op == "lit":
            return f"x{self.node}={self.value}"
        if self.op in ("true", "false"):
            return self.op.upper()
        if self.op == "not":
            return f"NOT({self.args[0].render()})"
        joiner = " AND " if self.op == "and" else " OR "
        return "(" + joiner.join(a.render() for a in self.args) + ")"


# --------------------------------------------------------------------------- interventions & queries

INTERVENTION_KINDS = ("none", "initial_edit", "persistent_clamp")


@dataclass(frozen=True)
class Intervention:
    kind: str = "none"
    assign: tuple[tuple[int, int], ...] = ()

    def __post_init__(self):
        if self.kind not in INTERVENTION_KINDS:
            raise SemanticsError(f"unsupported intervention kind {self.kind!r}")
        a = tuple(sorted((int(i), int(v)) for i, v in (self.assign.items() if isinstance(self.assign, dict) else self.assign)))
        object.__setattr__(self, "assign", a)
        nodes = [i for i, _ in a]
        if len(set(nodes)) != len(nodes):
            raise SemanticsError("intervention assigns a node twice")
        if any(v not in (0, 1) or i < 0 for i, v in a):
            raise SemanticsError("intervention values must be binary, nodes nonnegative")
        if self.kind == "none" and a:
            raise SemanticsError("'none' intervention cannot carry assignments")
        if self.kind != "none" and not a:
            raise SemanticsError(f"{self.kind} needs at least one assignment")

    @property
    def masks(self) -> tuple[int, int]:
        """(mask of clamped nodes, values on those nodes) as int bitmasks."""
        m = v = 0
        for i, b in self.assign:
            m |= 1 << i
            v |= b << i
        return m, v

    def to_json(self) -> dict:
        return {"kind": self.kind, "assign": [[i, v] for i, v in self.assign]}

    @staticmethod
    def from_json(d: dict) -> "Intervention":
        return Intervention(d["kind"], tuple((int(i), int(v)) for i, v in d.get("assign", [])))


QUANTIFIERS = ("exists", "forall")


@dataclass(frozen=True)
class Query:
    """q(M) over admissible initial states S = {s : domain(s)}.

    exists: some s in S has target(state_h(s)); forall: every s in S does.
    state_h applies ``intervention`` per docs/SEMANTICS.md, h = number of updates.
    """
    quantifier: str
    domain: Pred
    intervention: Intervention
    horizon: int
    target: Pred

    def __post_init__(self):
        if self.quantifier not in QUANTIFIERS:
            raise SemanticsError(f"unsupported quantifier {self.quantifier!r}")
        if isinstance(self.horizon, bool) or not isinstance(self.horizon, int) or self.horizon < 0:
            raise SemanticsError("horizon must be a nonnegative int")

    def check_against(self, n: int) -> None:
        mx = max(self.domain.max_node(), self.target.max_node(),
                 max((i for i, _ in self.intervention.assign), default=-1))
        if mx >= n:
            raise SemanticsError(f"query references node {mx} >= n={n}")

    @staticmethod
    def point(state: int, n: int, intervention: Intervention, horizon: int, target: Pred) -> "Query":
        return Query("exists", Pred.cube({i: b for i, b in enumerate(bits_of(state, n))}),
                     intervention, horizon, target)

    def to_json(self) -> dict:
        return {"quantifier": self.quantifier, "domain": self.domain.to_json(),
                "intervention": self.intervention.to_json(), "horizon": self.horizon,
                "target": self.target.to_json()}

    @staticmethod
    def from_json(d: dict) -> "Query":
        return Query(d["quantifier"], Pred.from_json(d["domain"]), Intervention.from_json(d["intervention"]),
                     int(d["horizon"]), Pred.from_json(d["target"]))

    def digest(self) -> str:
        return content_hash(self.to_json())


# --------------------------------------------------------------------------- evidence

@dataclass(frozen=True)
class Observation:
    """One measurement: from full input state ``state`` apply ``intervention``,
    run ``horizon`` updates, observe the listed output coordinates."""
    state: int
    intervention: Intervention
    horizon: int
    observed: tuple[tuple[int, int], ...]

    def __post_init__(self):
        obs = tuple(sorted((int(i), int(v)) for i, v in (self.observed.items() if isinstance(self.observed, dict) else self.observed)))
        object.__setattr__(self, "observed", obs)
        if len({i for i, _ in obs}) != len(obs):
            raise SemanticsError("coordinate observed twice in one observation")
        if any(v not in (0, 1) for _, v in obs):
            raise SemanticsError("observed values must be binary")
        if isinstance(self.horizon, bool) or self.horizon < 0:
            raise SemanticsError("observation horizon must be >= 0")
        if not obs:
            raise SemanticsError("an observation must observe at least one coordinate")

    def key(self) -> tuple:
        """(input, intervention, horizon) tuple used for holdout disjointness."""
        return (self.state, self.intervention.kind, self.intervention.assign, self.horizon)

    def to_json(self) -> dict:
        return {"state": self.state, "intervention": self.intervention.to_json(),
                "horizon": self.horizon, "observed": [[i, v] for i, v in self.observed]}

    @staticmethod
    def from_json(d: dict) -> "Observation":
        return Observation(int(d["state"]), Intervention.from_json(d["intervention"]), int(d["horizon"]),
                           tuple((int(i), int(v)) for i, v in d["observed"]))


@dataclass(frozen=True)
class Evidence:
    n: int
    observations: tuple[Observation, ...]
    regime: str = "unspecified"

    def __post_init__(self):
        if not isinstance(self.observations, tuple):
            object.__setattr__(self, "observations", tuple(self.observations))
        for o in self.observations:
            _check_state(o.state, self.n)
            if any(i >= self.n for i, _ in o.observed) or any(i >= self.n for i, _ in o.intervention.assign):
                raise SemanticsError("observation references node >= n")

    def prefix(self, k: int) -> "Evidence":
        return Evidence(self.n, self.observations[:k], self.regime)

    def keys(self) -> set:
        return {o.key() for o in self.observations}

    def to_json(self) -> dict:
        return {"n": self.n, "regime": self.regime, "observations": [o.to_json() for o in self.observations]}

    @staticmethod
    def from_json(d: dict) -> "Evidence":
        return Evidence(int(d["n"]), tuple(Observation.from_json(o) for o in d["observations"]), d.get("regime", "unspecified"))

    def digest(self) -> str:
        return content_hash(self.to_json())


@dataclass(frozen=True)
class HypothesisClass:
    """Declared hypothesis class H.

    kind='bounded_indegree': every network on n nodes whose node functions each
    depend on at most ``max_indegree`` nodes (all Boolean functions, all input
    sets, constants included).  This class is enumerated completely per node.
    """
    n: int
    max_indegree: int
    kind: str = "bounded_indegree"

    def __post_init__(self):
        if self.kind != "bounded_indegree":
            raise SemanticsError(f"unsupported hypothesis class {self.kind!r}")
        if not (0 <= self.max_indegree <= self.n):
            raise SemanticsError("max_indegree out of range")

    def to_json(self) -> dict:
        return {"kind": self.kind, "n": self.n, "max_indegree": self.max_indegree}


# --------------------------------------------------------------------------- certificates & results

@dataclass(frozen=True)
class Certificate:
    scope: str                      # e.g. "model", "version_space:bounded_indegree(n=6,k=3)"
    level: VerificationLevel
    model_hash: str | None = None
    evidence_hash: str | None = None
    query_hash: str | None = None
    witness_state: int | None = None
    witness_trace: tuple[int, ...] = ()
    witness_models: tuple[dict, ...] = ()   # serialized networks (e.g. M+ / M-)
    domain_size: int | None = None          # exhaustive domain size if enumerated
    detail: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return {"scope": self.scope, "level": self.level.value, "model_hash": self.model_hash,
                "evidence_hash": self.evidence_hash, "query_hash": self.query_hash,
                "witness_state": self.witness_state, "witness_trace": list(self.witness_trace),
                "witness_models": list(self.witness_models), "domain_size": self.domain_size,
                "detail": self.detail}


@dataclass(frozen=True)
class ModelResult:
    answer: ModelAnswer
    certificate: Certificate
    backend: str

    def to_json(self) -> dict:
        return {"answer": self.answer.value, "backend": self.backend, "certificate": self.certificate.to_json()}


@dataclass(frozen=True)
class VerdictResult:
    verdict: Verdict
    certificate: Certificate
    candidate_set_complete: bool
    candidate_count: int | None

    def to_json(self) -> dict:
        return {"verdict": self.verdict.value, "candidate_set_complete": self.candidate_set_complete,
                "candidate_count": self.candidate_count, "certificate": self.certificate.to_json()}


# --------------------------------------------------------------------------- hashing

def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def content_hash(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode()).hexdigest()
