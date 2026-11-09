"""Structural duplicate audit: exact isomorphism (node relabelling) of networks.

Hash identity is insufficient (a renamed copy hashes differently).  ``canonical_form``
minimizes the canonical serialization over all n! relabellings (exact; n <= 8 by
default), after a relabelling-invariant prefilter so the factorial search only runs on
invariant collisions.  Above ``max_exact_n`` only the invariant is available and the
audit reports that exact deduplication was infeasible.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from collections import defaultdict

from .schema import Network, Rule


def relabel(net: Network, perm: tuple[int, ...]) -> Network:
    """perm[old] = new label."""
    n = net.n
    rules: list[Rule | None] = [None] * n
    for j, r in enumerate(net.rules):
        new_inputs = sorted(perm[i] for i in r.inputs)
        pos_of = {perm[i]: t for t, i in enumerate(r.inputs)}  # new label -> old local position
        table = 0
        for z in range(1 << len(new_inputs)):
            y = 0
            for u, lab in enumerate(new_inputs):
                if (z >> u) & 1:
                    y |= 1 << pos_of[lab]
            table |= ((r.table >> y) & 1) << z
        rules[perm[j]] = Rule(tuple(new_inputs), table).canonical()
    return Network(n, tuple(rules))


def _ser(net: Network) -> str:
    return json.dumps([[list(r.inputs), r.table] for r in net.canonical().rules], separators=(",", ":"))


def invariant(net: Network) -> str:
    c = net.canonical()
    indeg = [len(r.inputs) for r in c.rules]
    outdeg = [0] * c.n
    for r in c.rules:
        for i in r.inputs:
            outdeg[i] += 1
    ones = [bin(r.table).count("1") for r in c.rules]
    selfloop = [int(j in r.inputs) for j, r in enumerate(c.rules)]
    sig = sorted(zip(indeg, outdeg, ones, selfloop))
    return hashlib.sha256(json.dumps(sig).encode()).hexdigest()[:20]


def canonical_form(net: Network, max_exact_n: int = 8) -> str | None:
    if net.n > max_exact_n:
        return None
    best = None
    for perm in itertools.permutations(range(net.n)):
        s = _ser(relabel(net, perm))
        if best is None or s < best:
            best = s
    return hashlib.sha256(best.encode()).hexdigest()


def audit(named_nets: list[tuple[str, str, Network]], max_exact_n: int = 8) -> dict:
    """named_nets: (split, id, network).  Returns duplicate groups within and across splits."""
    by_inv = defaultdict(list)
    for split, wid, net in named_nets:
        by_inv[invariant(net)].append((split, wid, net))
    groups = []
    infeasible = 0
    exact_checked = 0
    for items in by_inv.values():
        if len(items) < 2:
            continue
        by_canon = defaultdict(list)
        for split, wid, net in items:
            cf = canonical_form(net, max_exact_n)
            if cf is None:
                infeasible += 1
                continue
            exact_checked += 1
            by_canon[cf].append((split, wid))
        for cf, members in by_canon.items():
            if len(members) > 1:
                groups.append({"canonical": cf, "members": members,
                               "cross_split": len({s for s, _ in members}) > 1})
    return {"networks": len(named_nets), "invariant_classes": len(by_inv),
            "exact_isomorphism_checks": exact_checked, "exact_infeasible": infeasible,
            "duplicate_groups": groups, "cross_split_duplicates": sum(g["cross_split"] for g in groups),
            "method": f"invariant prefilter + exact minimum over all n! relabellings (n <= {max_exact_n})"}
