"""Track G external-model adapter: Biodivine Boolean Models (BBM), pinned commit, opaque labels.

Source: https://github.com/sybila/biodivine-boolean-models (retrieved locally; NOT redistributed).  Each model is
read from ``model.bnet`` with an independent recursive-descent parser (no eval).  Semantics: synchronous update of
every bnet target; an identifier used in a factor but never a target is a free INPUT and becomes a self-memory node
(x := x), which is declared in the manifest (it is not a simplification of a published update function).

Panels (never pooled with synthetic worlds, never with each other):
  intact       whole model, 6 <= n <= 10 total nodes, every essential indegree <= 3 (no other change)
  transformed  fixed deterministic subnetwork + boundary clamping: candidate roots in sha256 order of
               (model id, node name); backward BFS over regulators (sorted names) until 8 nodes; every regulator
               outside the subnetwork is clamped to constant 0 (declared); a root whose subnetwork has < 8 nodes or
               any node with essential indegree > 3 after substitution is EXCLUDED (logged), never simplified.  At
               most 4 accepted roots (distinct node sets) per model.
Source groups: models sharing a normalized publication URL/DOI are one lineage group; all derivatives of a model
belong to its group.  Group selection (cap 40 per panel) is by sha256 order of the group id, never by scores.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from ..schema import Network, Rule

BBM_REPO = "https://github.com/sybila/biodivine-boolean-models"
BBM_COMMIT = "314b2fed94689c38d3aaaf8101ed622b3501c7f7"
DEFAULT_ROOT = Path.home() / ".cache/causalguard/ext/biodivine-boolean-models"
INTACT_N = (6, 10)
SUB_N = 8
K = 3
MAX_ROOTS = 4
MAX_GROUPS = 40
MAX_FACTOR_INPUTS = 16           # refuse to tabulate a factor with more distinct regulators (logged)

_TOK = re.compile(r"\s*(?:([A-Za-z_][A-Za-z0-9_.:\-]*)|(\()|(\))|(&)|(\|)|(!))")


class ParseError(ValueError):
    pass


def _tokens(s: str) -> list[tuple[str, str]]:
    out, pos = [], 0
    s = s.strip()
    while pos < len(s):
        m = _TOK.match(s, pos)
        if not m or m.end() == pos:
            raise ParseError(f"bad token at {s[pos:pos + 20]!r}")
        pos = m.end()
        for kind, g in zip(("id", "(", ")", "&", "|", "!"), m.groups()):
            if g is not None:
                out.append((kind, g))
    return out


def parse_expr(s: str):
    """Iterative shunting-yard parse to RPN (deeply nested published factors exceed recursion limits).
    RPN items: ('var', name) | ('const', 0/1) | ('not',) | ('and',) | ('or',).  Precedence: ! > & > |."""
    prec = {"!": 3, "&": 2, "|": 1}
    name = {"!": ("not",), "&": ("and",), "|": ("or",)}
    out, ops = [], []
    expect_operand = True
    for kind, g in _tokens(s):
        if kind == "id":
            if not expect_operand:
                raise ParseError("missing operator")
            low = g.lower()
            out.append(("const", 1) if low in ("true", "1") else ("const", 0) if low in ("false", "0") else ("var", g))
            expect_operand = False
        elif kind in ("!", "("):
            if not expect_operand:
                raise ParseError(f"misplaced {kind}")
            ops.append(kind)
        elif kind == ")":
            if expect_operand:
                raise ParseError("empty parenthesis")
            while ops and ops[-1] != "(":
                out.append(name[ops.pop()])
            if not ops:
                raise ParseError("unbalanced )")
            ops.pop()
            while ops and ops[-1] == "!":            # a prefix ! applies to the closed group
                out.append(name[ops.pop()])
        else:                                       # binary & |
            if expect_operand:
                raise ParseError("misplaced binary operator")
            while ops and ops[-1] != "(" and prec[ops[-1]] >= prec[kind]:
                out.append(name[ops.pop()])
            ops.append(kind)
            expect_operand = True
            continue
        if kind == "id":
            while ops and ops[-1] == "!":            # prefix ! applies to the operand just read
                out.append(name[ops.pop()])
    if expect_operand:
        raise ParseError("incomplete expression")
    while ops:
        o = ops.pop()
        if o == "(":
            raise ParseError("unbalanced (")
        out.append(name[o])
    depth = 0
    for it in out:
        depth += 1 if it[0] in ("var", "const") else 0 if it[0] == "not" else -1
        if depth < 1:
            raise ParseError("malformed expression")
    if depth != 1:
        raise ParseError("malformed expression")
    return tuple(out)


def variables(e) -> set[str]:
    return {it[1] for it in e if it[0] == "var"}


def evaluate(e, env: dict[str, int]) -> int:
    st = []
    for it in e:
        op = it[0]
        if op == "var":
            st.append(env[it[1]])
        elif op == "const":
            st.append(it[1])
        elif op == "not":
            st.append(1 - st.pop())
        else:
            b, a = st.pop(), st.pop()
            st.append(a & b if op == "and" else a | b)
    return st[0]


def read_bnet(path: Path) -> dict[str, tuple]:
    funcs = {}
    for line in Path(path).read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.lower().startswith("targets"):
            continue
        tgt, _, fac = line.partition(",")
        tgt = tgt.strip()
        if tgt in funcs:
            raise ParseError(f"duplicate target {tgt}")
        funcs[tgt] = parse_expr(fac)
    return funcs


def close_inputs(funcs: dict[str, tuple]) -> tuple[dict[str, tuple], list[str]]:
    """Free inputs (used but never targets) become self-memory nodes."""
    used = set().union(*(variables(e) for e in funcs.values())) if funcs else set()
    free = sorted(used - set(funcs))
    out = dict(funcs)
    for x in free:
        out[x] = (("var", x),)
    return out, free


def _tabulate(e, regs: list[str], clamp0) -> int:
    """Truth table of factor e over ``regs`` (local bit t = regs[t]), clamped names = 0: the same values as
    ``evaluate`` at every assignment, computed for all 2^len(regs) assignments at once (numpy, R6)."""
    import numpy as np
    m = len(regs)
    y = np.arange(1 << m, dtype=np.int64)
    env = {r: ((y >> t) & 1).astype(bool) for t, r in enumerate(regs)}
    zero = np.zeros(1 << m, dtype=bool)
    st = []
    for it in e:
        op = it[0]
        if op == "var":
            st.append(env.get(it[1], zero) if it[1] not in clamp0 else zero)
        elif op == "const":
            st.append(np.full(1 << m, bool(it[1])))
        elif op == "not":
            st.append(~st.pop())
        else:
            b, a = st.pop(), st.pop()
            st.append(a & b if op == "and" else a | b)
    bits = np.broadcast_to(st[0], (1 << m,))
    return int(sum(1 << int(i) for i in np.nonzero(bits)[0]))


def to_network(funcs: dict[str, tuple], order: list[str], clamp0: set[str] = frozenset(),
               cache: dict | None = None) -> tuple[Network, list[int]]:
    """Network over ``order`` (node i = order[i]); names in ``clamp0`` are constant 0 inside factors.  Returns the
    canonical network and the essential indegree per node (canonicalization removes inessential regulators).
    ``cache`` (R6, optional, one dict per model): memo of each factor's table keyed by (node, clamped regulators);
    valid because ``order`` is always sorted by name, so the local input order of a factor never changes."""
    idx = {nm: i for i, nm in enumerate(order)}
    rules = []
    for nm in order:
        e = funcs[nm]
        ck = (nm, frozenset(variables(e) & set(clamp0)))
        if cache is not None and ck in cache:
            regs, table = cache[ck]
        else:
            regs = sorted((variables(e) - set(clamp0)), key=lambda x: idx[x])
            if len(regs) > MAX_FACTOR_INPUTS:
                raise ParseError(f"factor of {nm} has {len(regs)} regulators")
            table = _tabulate(e, regs, clamp0)
            if cache is not None:
                if order != sorted(order):
                    raise ValueError("to_network cache requires name-sorted order")
                cache[ck] = (regs, table)
        rules.append(Rule(tuple(idx[r] for r in regs), table).canonical())
    net = Network(len(order), tuple(rules))
    return net, [r.arity for r in net.rules]


def _group_id(meta: dict, model_dir: str) -> str:
    url = (meta.get("url-publication") or "").strip().lower()
    url = re.sub(r"^https?://(dx\.)?doi\.org/", "doi:", url).rstrip("/")
    key = url or f"model:{model_dir}"
    return "xg-" + hashlib.sha256(key.encode()).hexdigest()[:16]


def _h(*parts) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()


def backward_subnetwork(funcs: dict, root_nm: str, size: int = SUB_N) -> list[str]:
    """Backward BFS over regulators (sorted names) from root until ``size`` nodes (the R5 procedure; one owner)."""
    regs = {nm: sorted(variables(e)) for nm, e in funcs.items()}
    sub, frontier = [root_nm], [root_nm]
    while frontier and len(sub) < size:
        nxt = []
        for x in frontier:
            for r in regs[x]:
                if r not in sub and len(sub) < size:
                    sub.append(r)
                    nxt.append(r)
        frontier = nxt
    return sub


def inventory(root: Path = DEFAULT_ROOT, transformed_groups: tuple = (0, MAX_GROUPS)) -> dict:
    """Full inclusion/exclusion inventory (every model logged) and the selected panels."""
    models = sorted(p for p in (Path(root) / "models").iterdir() if p.is_dir())
    rows, intact, transformed = [], [], []
    for d in models:
        meta = json.loads((d / "metadata.json").read_text()) if (d / "metadata.json").exists() else {}
        bnet = d / "model.bnet"
        row = {"model_dir": d.name, "model_id": meta.get("id"), "group": _group_id(meta, d.name),
               "url_publication": meta.get("url-publication"), "url_model": meta.get("url-model"),
               "bnet_sha256": hashlib.sha256(bnet.read_bytes()).hexdigest() if bnet.exists() else None}
        try:
            funcs, free = close_inputs(read_bnet(bnet))
        except (ParseError, FileNotFoundError) as e:
            row.update(status="excluded", reason=f"parse:{e}"[:200])
            rows.append(row)
            continue
        names = sorted(funcs)
        row.update(n_total=len(names), free_inputs=len(free))
        if INTACT_N[0] <= len(names) <= INTACT_N[1]:
            try:
                net, deg = to_network(funcs, names)
                if max(deg) <= K:
                    row["intact"] = "eligible"
                    intact.append({"key": f"intact:{d.name}", "model_dir": d.name, "group": row["group"],
                                   "n": len(names), "transformation": "identity+free_inputs_self_memory"})
                else:
                    row["intact"] = f"excluded:indegree {max(deg)} > {K}"
            except ParseError as e:
                row["intact"] = f"excluded:{e}"[:200]
        else:
            row["intact"] = f"excluded:n={len(names)} outside {INTACT_N}"
        # transformed panel (every model with >= 8 nodes, including intact-eligible ones of size >= 9)
        acc, rej = [], {}
        if len(names) > SUB_N:
            seen_sets = set()
            for root_nm in sorted(names, key=lambda nm: _h(d.name, nm)):
                if len(acc) >= MAX_ROOTS:
                    break
                sub = backward_subnetwork(funcs, root_nm, SUB_N)
                if len(sub) < SUB_N:
                    rej["component_too_small"] = rej.get("component_too_small", 0) + 1
                    continue
                key_set = frozenset(sub)
                if key_set in seen_sets:
                    rej["duplicate_node_set"] = rej.get("duplicate_node_set", 0) + 1
                    continue
                order = sorted(sub)
                outside = set().union(*(variables(funcs[x]) for x in order)) - set(order)
                try:
                    net, deg = to_network(funcs, order, clamp0=outside)
                except ParseError:
                    rej["factor_too_large"] = rej.get("factor_too_large", 0) + 1
                    continue
                if max(deg) > K:
                    rej["indegree_gt_k"] = rej.get("indegree_gt_k", 0) + 1
                    continue
                seen_sets.add(key_set)
                acc.append({"key": f"sub:{d.name}:{_h(d.name, root_nm)[:12]}", "model_dir": d.name,
                            "group": row["group"], "n": SUB_N, "root_hash": _h(d.name, root_nm)[:12],
                            "transformation": "backward_bfs_8_clamp_outside_0", "clamped_regulators": len(outside)})
        row["transformed_accepted"] = len(acc)
        row["transformed_rejections"] = rej
        transformed += acc
        row["status"] = "inventoried"
        rows.append(row)

    def select(insts, lo=0, hi=MAX_GROUPS):
        """Groups lo..hi of the fixed hash ordering (R5: the first MAX_GROUPS; R6: the groups R5 never used)."""
        groups = sorted({x["group"] for x in insts}, key=lambda g: _h("select", g))
        chosen = set(groups[lo:hi])
        per: dict[str, list] = {}
        for x in sorted(insts, key=lambda x: _h("inst", x["key"])):
            if x["group"] in chosen and len(per.setdefault(x["group"], [])) < MAX_ROOTS:
                per[x["group"]].append(x)
        sel = sorted((x for v in per.values() for x in v), key=lambda x: x["key"])
        return sel, {"eligible_groups": len(groups), "selected_groups": len(chosen),
                     "eligible_instances": len(insts), "selected_instances": len(sel),
                     "max_instances_per_group": MAX_ROOTS}
    si, ci = select(intact)
    st, ct = select(transformed, *transformed_groups)
    if tuple(transformed_groups) != (0, MAX_GROUPS):
        ct["group_rank_slice"] = list(transformed_groups)
    return {"source": {"repository": BBM_REPO, "commit": BBM_COMMIT,
                       "citation": "Pastva et al., Repository of logically consistent real-world Boolean network "
                                   "models, bioRxiv 2023, doi:10.1101/2023.06.12.544361",
                       "rights": "Third-party published models with per-model provenance; NOT redistributed here. "
                                 "Retrieve the pinned commit; per-model citations are in each model's metadata."},
            "rules": {"intact_n": INTACT_N, "k": K, "sub_n": SUB_N, "max_roots": MAX_ROOTS, "max_groups": MAX_GROUPS,
                      "boundary_clamp": 0, "free_inputs": "self-memory node"},
            "models": rows, "intact": si, "intact_selection": ci, "transformed": st, "transformed_selection": ct}


def load_instance(key: str, root: Path = DEFAULT_ROOT) -> Network:
    """Rebuild the hidden network of an inventoried external instance (evaluator side only)."""
    kind, model_dir, *rest = key.split(":")
    funcs, _ = close_inputs(read_bnet(Path(root) / "models" / model_dir / "model.bnet"))
    names = sorted(funcs)
    if kind == "intact":
        return to_network(funcs, names)[0]
    want = rest[0]
    size = SUB_N if kind == "sub" else int(kind[3:])          # 'sub' (R5, 8 nodes) or 'sub<size>' (R6 Track S)
    for root_nm in names:
        if _h(model_dir, root_nm)[:12] != want:
            continue
        order = sorted(backward_subnetwork(funcs, root_nm, size))
        outside = set().union(*(variables(funcs[x]) for x in order)) - set(order)
        return to_network(funcs, order, clamp0=outside)[0]
    raise KeyError(key)
