"""Support-schema representation of the COMPLETE compatible-mechanism set V(D) (arm D's symbolic core).

Encoded object.  H = all networks on n nodes whose node functions have <= k essential inputs (the same complete
bounded class as S2; HypothesisClass(n, k)).  D = one-step observations (horizon 1; interventions none /
initial_edit / persistent_clamp).  V(D) = {M in H : M agrees with every observed coordinate}.  Under one-step
evidence V(D) is exactly a product of per-node sets V_j (docs/SEMANTICS.md §5; multi-step EVIDENCE is refused).

Per node j and per support F (|F| <= k, ascending, LSB local order: input F[t] is local bit t), the observations
of node j project to fixed addresses of the local repertoire {0..2^|F|-1}: a SCHEMA over the local truth table
(fixed rows = observed local patterns with their values, free rows = never-observed patterns).  This is the
index-set idea applied to the space of mechanisms instead of the space of states:

    g_j(F) = #tables on F consistent with the evidence = 2^(2^|F| - #observed patterns)  (0 on a conflict).

Multiplicity.  A function depending on fewer inputs is consistent on every superset support, so supports
OVERLAP.  Distinct mechanisms are counted by their unique essential support E via Moebius inversion,
    e_j(E) = sum_{F subset E} (-1)^{|E-F|} g_j(F),      |V_j| = sum_{|E|<=k} e_j(E) = sum_F g_j(F) mu(|F|),
    mu(f) = sum_{m=0}^{k-f} (-1)^m C(n-f, m).
These are counts of DISTINCT canonical functions (equal to the candidate-class count), never of (support,
table) encodings or SAT assignments.

Queries.  For a point claim (start state, intervention, horizon h <= 3, single-node literal target), exact counts
#{M in V(D): q(M)} are computed support-locally (formal paper, Proposition "Support Locality", transported to
the unknown-mechanism setting): the target's step-h value depends on the step-(h-1) state only through its
essential support E, so for h = 2 the enumeration is over at most 2^(|E u {t}|) <= 2^(k+1) local assignments
per support, and all other nodes contribute closed-form factors.  For h = 3 the intermediate state s1 is
ENUMERATED over its possible values (a metered fallback, capped; exceeding the cap returns a resource refusal,
never a sampled answer).  Every evaluation is metered.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

from ..schema import Evidence, Intervention, Network, Observation, Pred, Query, Rule, SemanticsError

MAX_ENUM_DEFAULT = 1 << 14


class ResourceLimit(Exception):
    """The requested exact computation exceeded its declared bound (not a proof, not underdetermination)."""


class UnsupportedClaim(SemanticsError):
    pass


@dataclass
class Meter:
    g_evals: int = 0
    support_terms: int = 0
    enumerated_states: int = 0          # h = 3 fallback enumeration (reported separately)
    witnesses_built: int = 0

    def to_json(self) -> dict:
        return dict(self.__dict__)


def _supports(n: int, k: int) -> list[tuple[int, ...]]:
    return [S for d in range(min(k, n) + 1) for S in itertools.combinations(range(n), d)]


def _proj(x: int, F: tuple[int, ...]) -> int:
    y = 0
    for t, i in enumerate(F):
        y |= ((x >> i) & 1) << t
    return y


class NodeSpace:
    """V_j for one node: base constraints (full input state -> value) and their per-support local schemas."""

    def __init__(self, n: int, k: int, j: int, cons: dict[int, int], consistent: bool, meter: Meter):
        self.n, self.k, self.j = n, k, j
        self.cons = cons
        self.meter = meter
        self.supports = _supports(n, k)
        self.base: dict[tuple[int, ...], dict[int, int] | None] = {}
        for F in self.supports:
            m: dict[int, int] | None = {} if consistent else None
            if m is not None:
                for x, v in cons.items():
                    y = _proj(x, F)
                    if m.get(y, v) != v:
                        m = None
                        break
                    m[y] = v
            self.base[F] = m
        self.mu = {f: sum((-1) ** m * math.comb(n - f, m) for m in range(k - f + 1)) for f in range(k + 1)}
        self.total = self.count(())

    # ---- local schema counts
    def g(self, F: tuple[int, ...], extra: tuple[tuple[int, int], ...]) -> int:
        self.meter.g_evals += 1
        m = self.base[F]
        if m is None:
            return 0
        add: dict[int, int] = {}
        for x, v in extra:
            y = _proj(x, F)
            w = m.get(y, add.get(y))
            if w is None:
                add[y] = v
            elif w != v:
                return 0
        return 1 << ((1 << len(F)) - len(m) - len(add))

    def exact(self, E: tuple[int, ...], extra) -> int:
        """Distinct functions with essential support exactly E consistent with evidence + extra."""
        tot = 0
        for r in range(len(E) + 1):
            for F in itertools.combinations(E, r):
                tot += (-1) ** (len(E) - r) * self.g(F, extra)
        return tot

    def count(self, extra) -> int:
        return sum(self.g(F, extra) * self.mu[len(F)] for F in self.supports)

    def schema(self, F: tuple[int, ...]) -> dict | None:
        """The local index-set schema on support F: fixed addresses and their values, LSB local order."""
        m = self.base[F]
        if m is None:
            return None
        return {"support": list(F), "fixed": {int(y): int(v) for y, v in sorted(m.items())},
                "free_addresses": (1 << len(F)) - len(m)}

    def construct(self, extra) -> Rule:
        """Some function in V_j satisfying ``extra`` (smallest support first; free rows 0)."""
        self.meter.witnesses_built += 1
        for F in self.supports:
            if self.g(F, extra) == 0:
                continue
            table = 0
            req = dict(self.base[F])
            for x, v in extra:
                req[_proj(x, F)] = v
            for y, v in req.items():
                table |= v << y
            return Rule(F, table).canonical()
        raise ValueError("no function satisfies the constraints")

    def construct_on(self, E: tuple[int, ...], extra) -> Rule:
        if self.g(E, extra) == 0:
            raise ValueError("support has no consistent table")
        req = dict(self.base[E])
        for x, v in extra:
            req[_proj(x, E)] = v
        return Rule(E, sum(v << y for y, v in req.items())).canonical()


def node_constraints_d(evidence: Evidence) -> tuple[list[dict[int, int]], list[bool]]:
    """Per node: dict(full effective input state -> required output) and a consistency flag.  Same semantics as
    versionspace.node_constraints (independently written); multi-step evidence is unsupported."""
    n = evidence.n
    cons: list[dict[int, int]] = [{} for _ in range(n)]
    ok = [True] * n
    for o in evidence.observations:
        if o.horizon != 1:
            raise UnsupportedClaim("mechanism space supports one-step observations only")
        m, v = o.intervention.masks
        x = (o.state & ~m) | v if o.intervention.kind != "none" else o.state
        for j, val in o.observed:
            if o.intervention.kind == "persistent_clamp" and (m >> j) & 1:
                if ((v >> j) & 1) != val:
                    ok = [False] * n          # impossible for every model: the whole space is empty
                continue
            if cons[j].get(x, val) != val:
                ok[j] = False
            cons[j][x] = val
    return cons, ok


@dataclass
class ClaimCounts:
    num: int
    den: int
    meter: dict
    path: str


class MechanismSpace:
    """Arm D's workspace object.  Built from PUBLIC (H, D) only."""

    def __init__(self, evidence: Evidence, k: int, max_enum: int = MAX_ENUM_DEFAULT):
        self.evidence = evidence
        self.n, self.k = evidence.n, k
        self.max_enum = max_enum
        self.meter = Meter()
        cons, ok = node_constraints_d(evidence)
        self.nodes = [NodeSpace(self.n, k, j, cons[j], ok[j], self.meter) for j in range(self.n)]

    @property
    def empty(self) -> bool:
        return any(nd.total == 0 for nd in self.nodes)

    def counts(self) -> list[int]:
        return [nd.total for nd in self.nodes]

    def size(self) -> int:
        return math.prod(self.counts())

    def update(self, obs: list[Observation]) -> "MechanismSpace":
        return MechanismSpace(Evidence(self.n, tuple(self.evidence.observations) + tuple(obs), self.evidence.regime),
                              self.k, self.max_enum)

    # ---- claims
    @staticmethod
    def parse(q: Query, n: int) -> tuple[int, int, set[int], dict[int, int], int, int, int]:
        from ..versionspace import point_query_parts
        try:
            x0 = point_query_parts(q, n)
        except SemanticsError as e:
            raise UnsupportedClaim(str(e)) from None
        if q.target.op != "lit":
            raise UnsupportedClaim("mechanism space claims: single-node literal targets")
        t, c = q.target.node, q.target.value
        m, v = q.intervention.masks
        s0 = (x0 & ~m) | v if q.intervention.kind != "none" else x0
        clamp = {i for i in range(n) if q.intervention.kind == "persistent_clamp" and (m >> i) & 1}
        cval = {i: (v >> i) & 1 for i in clamp}
        if q.horizon > 3:
            raise UnsupportedClaim("exact claim counts implemented for h <= 3")
        return s0, q.horizon, clamp, cval, t, c, x0

    def claim_counts(self, q: Query) -> ClaimCounts:
        if self.empty:
            raise SemanticsError("empty version space")
        n = self.n
        s0, h, clamp, cval, t, c, _ = self.parse(q, n)
        before = self.meter.to_json()
        den = self.size()
        tot = {j: nd.total for j, nd in enumerate(self.nodes)}
        if h == 0:
            num = den if ((s0 >> t) & 1) == c else 0
            return ClaimCounts(num, den, self._delta(before), "h0")
        if t in clamp:
            return ClaimCounts(den if cval[t] == c else 0, den, self._delta(before), "clamped_target")
        others = math.prod(tot[j] for j in range(n) if j != t)
        if h == 1:
            num = others * self.nodes[t].count(((s0, c),))
            return ClaimCounts(num, den, self._delta(before), "h1_closed_form")

        def A1(j, b):            # node j's factor for s1[j] = b
            if j in clamp:
                return tot[j] if b == cval[j] else 0
            return self.nodes[j].count(((s0, b),))
        if h == 2:
            a = {j: (A1(j, 0), A1(j, 1)) for j in range(n) if j != t}
            num = 0
            for E in self.nodes[t].supports:
                self.meter.support_terms += 1
                W = sorted(set(E) | {t})
                rest = math.prod(a[j][0] + a[j][1] for j in range(n) if j != t and j not in W)
                if rest == 0:
                    continue
                sub = 0
                for assign in itertools.product((0, 1), repeat=len(W)):
                    s1 = 0
                    w = 1
                    for i, b in zip(W, assign):
                        s1 |= b << i
                        if i != t:
                            w *= a[i][b]
                    if w == 0:
                        continue
                    sub += w * self.nodes[t].exact(E, ((s0, (s1 >> t) & 1), (s1, c)))
                num += rest * sub
            return ClaimCounts(num, den, self._delta(before), "h2_support_local")
        # h == 3: enumerate s1 over its possible values (metered fallback)
        poss = {}
        for j in range(n):
            poss[j] = [b for b in (0, 1) if A1(j, b) > 0] if j != t else [0, 1]
        space = math.prod(len(p) for p in poss.values())
        if space > self.max_enum:
            raise ResourceLimit(f"h=3 fallback would enumerate {space} intermediate states (cap {self.max_enum})")
        num = 0
        order = list(range(n))
        for vals in itertools.product(*[poss[j] for j in order]):
            self.meter.enumerated_states += 1
            s1 = sum(b << j for j, b in zip(order, vals))

            def A2(j, b2):
                if j in clamp:
                    return tot[j] if (b2 == cval[j] and ((s1 >> j) & 1) == cval[j]) else 0
                return self.nodes[j].count(((s0, (s1 >> j) & 1), (s1, b2)))
            a2 = {j: (A2(j, 0), A2(j, 1)) for j in range(n) if j != t}
            if any(x == (0, 0) for x in a2.values()):
                continue
            for E in self.nodes[t].supports:
                self.meter.support_terms += 1
                W = sorted(set(E) | {t})
                rest = math.prod(a2[j][0] + a2[j][1] for j in range(n) if j != t and j not in W)
                sub = 0
                for assign in itertools.product((0, 1), repeat=len(W)):
                    s2 = 0
                    w = 1
                    for i, b in zip(W, assign):
                        s2 |= b << i
                        if i != t:
                            w *= a2[i][b]
                    if w == 0:
                        continue
                    sub += w * self.nodes[t].exact(E, ((s0, (s1 >> t) & 1), (s1, (s2 >> t) & 1), (s2, c)))
                num += rest * sub
        return ClaimCounts(num, den, self._delta(before), "h3_enumerated_s1")

    def _delta(self, before: dict) -> dict:
        now = self.meter.to_json()
        return {k: now[k] - before[k] for k in now}

    # ---- witnesses: an explicit network in V(D) giving the requested target value
    def witness(self, q: Query, want: int) -> Network | None:
        """Constructive witness with target value ``want`` (None if no compatible model gives it)."""
        n = self.n
        s0, h, clamp, cval, t, c, _ = self.parse(q, n)
        target = c if want else 1 - c
        tq = Query(q.quantifier, q.domain, q.intervention, q.horizon, Pred.lit(t, target))
        cc = self.claim_counts(tq)
        if cc.num == 0:
            return None
        free = lambda j: self.nodes[j].construct(())          # noqa: E731
        if h == 0 or t in clamp:
            return Network(n, tuple(free(j) for j in range(n)))
        if h == 1:
            return Network(n, tuple(self.nodes[j].construct(((s0, target),)) if j == t else free(j) for j in range(n)))
        if h == 2:
            return self._witness_local(s0, None, clamp, cval, t, target, free)
        # h == 3: s1 by the metered enumeration fallback, then the support-local step for s2
        for s1 in self._states(lambda j, b: (b == cval[j]) if j in clamp else self.nodes[j].count(((s0, b),)) > 0, t):
            net = self._witness_local(s0, s1, clamp, cval, t, target, free)
            if net is not None:
                return net
        raise AssertionError("positive count but no constructive witness found")

    def _witness_local(self, s0, s1, clamp, cval, t, target, free):
        """Support-local witness for the LAST step (polynomial): choose the target's essential support E and an
        assignment of the next state on E u {t}; every other node takes any feasible value.  ``s1`` None: h = 2
        (the varying state is s1); otherwise h = 3 with fixed s1 (the varying state is s2)."""
        n = self.n

        def ext(j, b):                     # constraints making node j output b at the varying step
            return ((s0, b),) if s1 is None else ((s0, (s1 >> j) & 1), (s1, b))

        def feasible(j, b):
            if j in clamp:
                return b == cval[j] and (s1 is None or ((s1 >> j) & 1) == cval[j])
            return self.nodes[j].count(ext(j, b)) > 0
        fixed = {}
        for j in range(n):
            if j != t:
                opts = [b for b in (0, 1) if feasible(j, b)]
                if not opts:
                    return None
                fixed[j] = opts
        for E in self.nodes[t].supports:
            W = sorted(set(E) | {t})
            for assign in itertools.product((0, 1), repeat=len(W)):
                a = dict(zip(W, assign))
                if any(i != t and a[i] not in fixed[i] for i in W):
                    continue
                nxt = sum(a.get(j, fixed[j][0] if j != t else 0) << j for j in range(n))
                ex = ((s0, a[t]), (nxt, target)) if s1 is None else ((s0, (s1 >> t) & 1), (s1, a[t]), (nxt, target))
                if self.nodes[t].exact(E, ex) > 0:
                    rules = []
                    for j in range(n):
                        if j == t:
                            rules.append(self.nodes[t].construct_on(E, ex))
                        elif j in clamp:
                            rules.append(free(j))
                        else:
                            rules.append(self.nodes[j].construct(ext(j, (nxt >> j) & 1)))
                    return Network(n, tuple(rules))
        return None

    def _states(self, ok, t):
        n = self.n
        poss = [[b for b in (0, 1) if (j == t or ok(j, b))] for j in range(n)]
        if math.prod(len(p) for p in poss) > self.max_enum:
            raise ResourceLimit("witness search space exceeds cap")
        for vals in itertools.product(*poss):
            self.meter.enumerated_states += 1
            yield sum(b << j for j, b in enumerate(vals))

    # ---- analytic description for the workspace (named analytic mechanisms still possible per node)
    def analytic_summary(self, max_names: int = 6) -> list[dict]:
        from .hcode import local_catalogue
        out = []
        for j, nd in enumerate(self.nodes):
            names = []
            fams: dict[str, int] = {}
            for F in nd.supports:
                if not 1 <= len(F) or nd.base[F] is None:
                    continue
                for name, table in local_catalogue(len(F)):
                    if all(((table >> y) & 1) == v for y, v in nd.base[F].items()):
                        r = Rule(F, table)
                        if r.canonical().inputs != F:
                            continue
                        fam = name.split("(")[0]
                        fams[fam] = fams.get(fam, 0) + 1
                        if len(names) < max_names:
                            names.append(f"{name}{tuple(F)}")
            out.append({"node": j, "compatible_mechanisms": nd.total, "named_analytic_rules": fams,
                        "examples": names})
        return out


def intervention_none() -> Intervention:
    return Intervention("none")
