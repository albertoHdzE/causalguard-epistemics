"""R6 Track S populations: intact published models and large backward subnetworks (Biodivine, pinned commit).

Uses the R5 external owners (parser, input closing, canonical network, group ids, backward BFS); adds only the
Track S selection rules:
  intact      every model with 9 <= n <= 64 (after free inputs become self-memory nodes) and every essential
              indegree <= 3; no clamping, no other change
  sub<m>      for each model with more than m nodes: roots in sha256 order of (model, node), backward BFS to m nodes,
              regulators outside the subnetwork clamped to 0, excluded (logged) if smaller than m or any essential
              indegree > 3 after substitution; at most MAX_ROOTS accepted distinct node sets per model.  m = 24 is
              the protocol's large-subnetwork panel; m = 12 and m = 48 are a declared size ladder (secondary).
Group split (before any score): all eligible groups of all panels in sha256 order of ('r6s-split', group); the
first quarter (rounded up) is calibration, the rest evaluation.  Groups used in any R5/R6 n = 8 panel are flagged.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from ..r5.external import (
    BBM_COMMIT,
    BBM_REPO,
    DEFAULT_ROOT,
    MAX_ROOTS,
    K,
    ParseError,
    _group_id,
    _h,
    backward_subnetwork,
    close_inputs,
    read_bnet,
    to_network,
    variables,
)

INTACT_RANGE = (9, 64)
SUB_SIZES = (12, 24, 48)
PRIMARY_SUB = 24
MIN_INTACT_GROUPS = 20


def _prior_groups(root: Path) -> set:
    out = set()
    for p in ("artifacts/r5_source_manifest.json", "artifacts/r6_source_manifest.json"):
        m = json.loads((root / p).read_text())
        for pan in ("intact", "transformed"):
            out |= {x["group"] for x in m.get(pan, [])}
    return out


def inventory_s(root: Path = DEFAULT_ROOT, repo: Path | None = None) -> dict:
    repo = repo or Path(__file__).resolve().parents[3]
    prior = _prior_groups(repo)
    models = sorted(p for p in (Path(root) / "models").iterdir() if p.is_dir())
    rows, panels = [], {"intact": [], **{f"sub{m}": [] for m in SUB_SIZES}}
    for d in models:
        meta = json.loads((d / "metadata.json").read_text()) if (d / "metadata.json").exists() else {}
        bnet = d / "model.bnet"
        row = {"model_dir": d.name, "group": _group_id(meta, d.name),
               "bnet_sha256": hashlib.sha256(bnet.read_bytes()).hexdigest() if bnet.exists() else None}
        try:
            funcs, free = close_inputs(read_bnet(bnet))
        except (ParseError, FileNotFoundError) as e:
            row.update(status="excluded", reason=f"parse:{e}"[:200])
            rows.append(row)
            continue
        names = sorted(funcs)
        n = len(names)
        row.update(n_total=n, free_inputs=len(free))
        if INTACT_RANGE[0] <= n <= INTACT_RANGE[1]:
            try:
                net, deg = to_network(funcs, names)
                if max(deg) <= K:
                    row["intact"] = "eligible"
                    panels["intact"].append({"key": f"intact:{d.name}", "model_dir": d.name, "group": row["group"],
                                             "n": n, "free_inputs": len(free), "clamped_edge_fraction": 0.0,
                                             "transformation": "identity+free_inputs_self_memory"})
                else:
                    row["intact"] = f"excluded:indegree {max(deg)} > {K}"
            except ParseError as e:
                row["intact"] = f"excluded:{e}"[:200]
        else:
            row["intact"] = f"excluded:n={n} outside {INTACT_RANGE}"
        memo: dict = {}
        for m in SUB_SIZES:
            acc, rej, seen = [], {}, set()
            if n > m:
                for root_nm in sorted(names, key=lambda nm: _h(d.name, nm)):
                    if len(acc) >= MAX_ROOTS:
                        break
                    sub = backward_subnetwork(funcs, root_nm, m)
                    if len(sub) < m:
                        rej["component_too_small"] = rej.get("component_too_small", 0) + 1
                        continue
                    ks = frozenset(sub)
                    if ks in seen:
                        rej["duplicate_node_set"] = rej.get("duplicate_node_set", 0) + 1
                        continue
                    order = sorted(sub)
                    outside = set().union(*(variables(funcs[x]) for x in order)) - set(order)
                    edges = sum(len(variables(funcs[x])) for x in order)
                    out_edges = sum(len(variables(funcs[x]) & outside) for x in order)
                    try:
                        net, deg = to_network(funcs, order, clamp0=outside, cache=memo)
                    except ParseError:
                        rej["factor_too_large"] = rej.get("factor_too_large", 0) + 1
                        continue
                    if max(deg) > K:
                        rej["indegree_gt_k"] = rej.get("indegree_gt_k", 0) + 1
                        continue
                    seen.add(ks)
                    acc.append({"key": f"sub{m}:{d.name}:{_h(d.name, root_nm)[:12]}", "model_dir": d.name,
                                "group": row["group"], "n": m, "root_hash": _h(d.name, root_nm)[:12],
                                "transformation": f"backward_bfs_{m}_clamp_outside_0",
                                "clamped_regulators": len(outside),
                                "clamped_edge_fraction": out_edges / edges if edges else 0.0})
            row[f"sub{m}_accepted"] = len(acc)
            row[f"sub{m}_rejections"] = rej
            panels[f"sub{m}"] += acc
        row["status"] = "inventoried"
        rows.append(row)
    groups = sorted({x["group"] for v in panels.values() for x in v}, key=lambda g: _h("r6s-split", g))
    n_cal = math.ceil(len(groups) / 4)
    split = {g: ("calibration" if i < n_cal else "evaluation") for i, g in enumerate(groups)}
    for v in panels.values():
        for x in v:
            x["split"] = split[x["group"]]
            x["group_seen_in_n8_panels"] = x["group"] in prior
    intact_groups = {x["group"] for x in panels["intact"]}
    primary = "intact" if len(intact_groups) >= MIN_INTACT_GROUPS else f"sub{PRIMARY_SUB}"

    def summ(v):
        return {"instances": len(v), "groups": len({x["group"] for x in v}),
                "calibration_groups": len({x["group"] for x in v if x["split"] == "calibration"}),
                "evaluation_groups": len({x["group"] for x in v if x["split"] == "evaluation"}),
                "evaluation_groups_seen_in_n8": len({x["group"] for x in v if x["split"] == "evaluation"
                                                     and x["group_seen_in_n8_panels"]})}
    return {"source": {"repository": BBM_REPO, "commit": BBM_COMMIT,
                       "rights": "Third-party published models; NOT redistributed here."},
            "rules": {"intact_n": list(INTACT_RANGE), "k": K, "sub_sizes": list(SUB_SIZES), "max_roots": MAX_ROOTS,
                      "boundary_clamp": 0, "free_inputs": "self-memory node", "min_intact_groups": MIN_INTACT_GROUPS,
                      "split": "sha256('r6s-split|'+group) order; first ceil(G/4) calibration"},
            "primary_panel": primary,
            "primary_rule": f"intact if >= {MIN_INTACT_GROUPS} eligible intact groups, else sub{PRIMARY_SUB} "
                            f"(protocol S2 fallback); intact has {len(intact_groups)} groups",
            "group_split": split, "summary": {k: summ(v) for k, v in panels.items()},
            "models": rows, **panels}
