"""Independent direct-rule reference simulator and exhaustive query evaluator.

DELIBERATE INDEPENDENCE (declared exception to the one-owner rule): this module
re-implements the dynamics, intervention and predicate semantics of
docs/SEMANTICS.md in a different style (explicit bit lists, direct local-table
lookup) and MUST NOT import causalguard.semantics, index_repr, query, codec,
versionspace or any production engine.  tests/test_structure.py enforces this.
It may import only the passive data types of causalguard.schema.

It is intentionally slow and simple.  It is the oracle for small domains and
the replay checker for every witness produced elsewhere.
"""
from __future__ import annotations

import itertools

from .schema import (
    Certificate,
    ModelAnswer,
    ModelResult,
    Network,
    Pred,
    Query,
    Rule,
    SemanticsError,
    Verdict,
    VerificationLevel,
    content_hash,
)

REFERENCE_ID = "causalguard.reference/direct-rule-v1"


def to_bits(x: int, n: int) -> list[int]:
    return [(x >> i) & 1 for i in range(n)]


def from_bits(b: list[int]) -> int:
    return sum(v << i for i, v in enumerate(b))


def node_output(net: Network, j: int, bits: list[int]) -> int:
    rule = net.rules[j]
    y = 0
    for t, src in enumerate(rule.inputs):
        y += bits[src] * (2 ** t)
    return (rule.table // (2 ** y)) % 2


def step_bits(net: Network, bits: list[int]) -> list[int]:
    """Synchronous update: every node reads the OLD state."""
    old = list(bits)
    return [node_output(net, j, old) for j in range(net.n)]


def step_bits_sequential(net: Network, bits: list[int]) -> list[int]:
    """A DIFFERENT convention (in-place, node order 0..n-1).  Fixture use only."""
    cur = list(bits)
    for j in range(net.n):
        cur[j] = node_output(net, j, cur)
    return cur


def holds(p: Pred, bits: list[int]) -> bool:
    if p.op == "lit":
        return bits[p.node] == p.value
    if p.op == "true":
        return True
    if p.op == "false":
        return False
    if p.op == "not":
        return not holds(p.args[0], bits)
    if p.op == "and":
        for a in p.args:
            if not holds(a, bits):
                return False
        return True
    if p.op == "or":
        for a in p.args:
            if holds(a, bits):
                return True
        return False
    raise SemanticsError(f"reference: unsupported operator {p.op!r}")


def run(net: Network, x: int, intervention, horizon: int) -> list[int]:
    """Trace of integer states s_0..s_h under the intervention semantics."""
    bits = to_bits(x, net.n)
    forced = dict(intervention.assign)
    if intervention.kind in ("initial_edit", "persistent_clamp"):
        for i, v in forced.items():
            bits[i] = v
    trace = [from_bits(bits)]
    for _ in range(horizon):
        bits = step_bits(net, bits)
        if intervention.kind == "persistent_clamp":
            for i, v in forced.items():
                bits[i] = v
        trace.append(from_bits(bits))
    return trace


MAX_REFERENCE_N = 22


def evaluate(net: Network, q: Query) -> ModelResult:
    """Exhaustive evaluation of q(M) over every admissible initial state."""
    n = net.n
    q.check_against(n)
    if n > MAX_REFERENCE_N:
        return ModelResult(ModelAnswer.UNKNOWN_RESOURCE,
                           Certificate("model", VerificationLevel.NONE, detail={"reason": f"n>{MAX_REFERENCE_N}"}),
                           REFERENCE_ID)
    admissible = 0
    witness = None
    witness_trace = None
    for x in range(2 ** n):
        if not holds(q.domain, to_bits(x, n)):
            continue
        admissible += 1
        tr = run(net, x, q.intervention, q.horizon)
        ok = holds(q.target, to_bits(tr[-1], n))
        if q.quantifier == "exists" and ok:
            witness, witness_trace = x, tr
            break
        if q.quantifier == "forall" and not ok:
            witness, witness_trace = x, tr
            break
    mh, qh = content_hash(net.canonical().to_json()), q.digest()
    if admissible == 0:
        return ModelResult(ModelAnswer.INVALID_DOMAIN,
                           Certificate("model", VerificationLevel.EXHAUSTIVE, mh, None, qh, domain_size=0),
                           REFERENCE_ID)
    if witness is not None:
        ans = ModelAnswer.TRUE if q.quantifier == "exists" else ModelAnswer.FALSE
        return ModelResult(ans, Certificate("model", VerificationLevel.WITNESS_REPLAYED, mh, None, qh,
                                            witness_state=witness, witness_trace=tuple(witness_trace)),
                           REFERENCE_ID)
    ans = ModelAnswer.FALSE if q.quantifier == "exists" else ModelAnswer.TRUE
    # exhaustive: count the full admissible set (search stopped only on witness)
    return ModelResult(ans, Certificate("model", VerificationLevel.EXHAUSTIVE, mh, None, qh,
                                        domain_size=admissible), REFERENCE_ID)


def replay_witness(net: Network, q: Query, state: int, trace: tuple[int, ...] | list[int]) -> bool:
    """Independently check a claimed witness (state + trace) for q on net.

    For exists: the state must be admissible and reach the target.  For forall
    the witness is a counterexample: admissible and NOT reaching the target.
    The full trace must match the reference replay exactly.
    """
    n = net.n
    if not (0 <= state < 2 ** n) or not holds(q.domain, to_bits(state, n)):
        return False
    tr = run(net, state, q.intervention, q.horizon)
    if list(trace) != tr:
        return False
    ok = holds(q.target, to_bits(tr[-1], n))
    return ok if q.quantifier == "exists" else (not ok)


def consistent(net: Network, evidence) -> bool:
    for o in evidence.observations:
        final = to_bits(run(net, o.state, o.intervention, o.horizon)[-1], net.n)
        for i, v in o.observed:
            if final[i] != v:
                return False
    return True


def all_bounded_networks(n: int, k: int):
    """Every network on n nodes with each node depending on <= k inputs.

    Enumerated by (input set of size exactly k-or-less, every table) and
    deduplicated by canonical form; exponential, small n only (fixtures)."""
    seen = set()
    rules = []
    for size in range(k + 1):
        for ins in itertools.combinations(range(n), size):
            for table in range(2 ** (2 ** size)):
                r = Rule(ins, table).canonical()
                key = (r.inputs, r.table)
                if key not in seen:
                    seen.add(key)
                    rules.append(r)
    per_node = [rules] * n
    for combo in itertools.product(*per_node):
        yield Network(n, tuple(combo))


def version_space_verdict(candidates, evidence, q: Query) -> tuple[Verdict, int]:
    """Exhaustive evidence-relative verdict over an explicit candidate iterable."""
    vals = set()
    count = 0
    for m in candidates:
        if not consistent(m, evidence):
            continue
        count += 1
        r = evaluate(m, q)
        if not r.answer.is_truth_value():
            return Verdict.INVALID_DOMAIN if r.answer is ModelAnswer.INVALID_DOMAIN else Verdict.UNKNOWN_RESOURCE, count
        vals.add(r.answer is ModelAnswer.TRUE)
    if count == 0:
        return Verdict.INCONSISTENT, 0
    if vals == {True}:
        return Verdict.ENTAILED, count
    if vals == {False}:
        return Verdict.REFUTED, count
    return Verdict.UNDERDETERMINED, count
