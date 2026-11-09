"""Production dynamics/query semantics over integer states (docs/SEMANTICS.md).

Owner of: intervention application, horizon semantics, predicate evaluation on
integer states and predicate -> cube (DNF) conversion used by the symbolic
query engines.  The *step* function is supplied by a representation backend
(index families in :mod:`causalguard.index_repr`).  The independent reference in
:mod:`causalguard.reference` deliberately re-implements these semantics without
importing this module.

Semantics
---------
initial_edit(A):     s0 = edit_A(s);  s_{t+1} = F(s_t);           answer reads s_h
persistent_clamp(A): s0 = clamp_A(s); s_{t+1} = clamp_A(F(s_t));  answer reads s_h
none:                s0 = s;          s_{t+1} = F(s_t)
h counts updates, so h=0 reads s0 (the intervened initial state).
"""
from __future__ import annotations

from typing import Callable, Iterator

from .schema import Intervention, Pred, SemanticsError

Cube = tuple[int, int]  # (mask, value): states x with x & mask == value


def eval_pred(p: Pred, x: int) -> bool:
    op = p.op
    if op == "lit":
        return ((x >> p.node) & 1) == p.value
    if op == "and":
        return all(eval_pred(a, x) for a in p.args)
    if op == "or":
        return any(eval_pred(a, x) for a in p.args)
    if op == "not":
        return not eval_pred(p.args[0], x)
    if op == "true":
        return True
    if op == "false":
        return False
    raise SemanticsError(f"unsupported operator {op!r}")


def apply_assign(x: int, interv: Intervention) -> int:
    if interv.kind == "none":
        return x
    m, v = interv.masks
    return (x & ~m) | v


def trajectory(step: Callable[[int], int], x: int, interv: Intervention, h: int) -> list[int]:
    s = apply_assign(x, interv)
    out = [s]
    clamp = interv.kind == "persistent_clamp"
    for _ in range(h):
        s = step(s)
        if clamp:
            s = apply_assign(s, interv)
        out.append(s)
    return out


# --------------------------------------------------------------------------- cube algebra

def cube_and(a: Cube, b: Cube) -> Cube | None:
    ma, va = a
    mb, vb = b
    common = ma & mb
    if (va ^ vb) & common:
        return None
    return (ma | mb, va | vb)


def pred_to_cubes(p: Pred, max_cubes: int = 1 << 16) -> list[Cube]:
    """Exact DNF of a predicate as a list of cubes (may overlap).

    Raises ResourceWarning if the DNF exceeds ``max_cubes``.
    """
    def nnf(q: Pred, neg: bool) -> list[Cube]:
        op = q.op
        if op == "not":
            return nnf(q.args[0], not neg)
        if op == "true":
            return [] if neg else [(0, 0)]
        if op == "false":
            return [(0, 0)] if neg else []
        if op == "lit":
            v = q.value ^ (1 if neg else 0)
            return [(1 << q.node, v << q.node)]
        is_and = (op == "and") ^ neg
        parts = [nnf(a, neg) for a in q.args]
        if not is_and:
            out = [c for part in parts for c in part]
        else:
            out = [(0, 0)]
            for part in parts:
                nxt = []
                for c in out:
                    for d in part:
                        e = cube_and(c, d)
                        if e is not None:
                            nxt.append(e)
                if len(nxt) > max_cubes:
                    raise ResourceWarning("predicate DNF exceeds cube budget")
                out = list(dict.fromkeys(nxt))
        if len(out) > max_cubes:
            raise ResourceWarning("predicate DNF exceeds cube budget")
        return list(dict.fromkeys(out))
    return nnf(p, False)


def iter_cube_states(c: Cube, n: int, limit: int | None = None) -> Iterator[int]:
    """Enumerate states in a cube (guarded by ``limit`` on 2**free)."""
    mask, val = c
    free = [i for i in range(n) if not (mask >> i) & 1]
    if limit is not None and len(free) > limit.bit_length() - 1 and (1 << len(free)) > limit:
        raise ResourceWarning("cube enumeration exceeds limit")
    for z in range(1 << len(free)):
        x = val
        for j, i in enumerate(free):
            if (z >> j) & 1:
                x |= 1 << i
        yield x
