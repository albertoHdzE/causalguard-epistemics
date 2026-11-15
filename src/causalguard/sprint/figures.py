"""SPRINT report figures 1-4, drawn from ``analysis.json`` and ``p5_analysis.json`` (no number computed here).

Dot plots, one row per model (names on the axis, so no label collides), 95 % intervals as thin lines.  Categorical
slots 1-3 of the dataviz reference palette (validated: CVD worst adjacent dE 9.2; the aqua slot's contrast warning
is relieved by distinct marker shapes and the legend; every figure has a table in the report).  A cell below the
D102(d) minimum is drawn hollow and its row label carries n finished / n planned.

  Fig 1  Task P: adoption of the true status under P3, of the forged status under P4 and under P5f; Tier W, Tier H
  Fig 2  Task S: overclaim and underclaim per model, Tier W and Tier H, with the surface rule as a reference row
  Fig 3  P5: exact and lenient detection of the forged line (P5f) and false alarm (P5v)
  Fig 4  Appendix E.1 (D128): Rule 110 and the worked-example world against the behaviour they generate (no run read)
"""
from __future__ import annotations

import json
from pathlib import Path

BLUE, ORANGE, AQUA, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#1baf7a", "#0b0b0b", "#52514e", "#e4e3df"
SHORT = {"google/gemma-3-4b": "gemma-3-4b", "qwen2.5:7b": "qwen2.5-7b", "gemma-4-12b-it-mlx": "gemma-4-12b (half)",
         "mistral-small-3.2-24b-instruct-2506-mlx": "mistral-small-24b",
         "deepseek-r1-distill-qwen-32b": "r1-distill-32b (half)", "llama-3.3-70b-instruct": "llama-3.3-70b",
         "claude-opus-5-5": "Claude Opus 5.5", "deepseek-v4-pro": "DeepSeek V4-Pro (effort low)"}
ORDER = list(SHORT)
SUPPLEMENT_SUFFIX = "-v2-b4"     # amendment v2-a4: Claude's Tier H block, a post-freeze supplement (D118)


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                         "ytick.color": INK, "axes.spines.top": False, "axes.spines.right": False,
                         "savefig.dpi": 200, "font.family": "DejaVu Sans"})
    return plt


def _models(names) -> list[str]:
    return [m for m in ORDER if m in names] + sorted(m for m in names if m not in ORDER)


def _dot(ax, y, b, color, marker, hollow=False, label=None):
    if not b or b.get("est") is None:
        return
    if b.get("lo") is not None:
        ax.plot([b["lo"], b["hi"]], [y, y], color=color, linewidth=1.2, alpha=0.55, zorder=2, solid_capstyle="round")
    ax.scatter([b["est"]], [y], s=34, marker=marker, zorder=3, linewidths=1.3, label=label,
               facecolors="white" if hollow else color, edgecolors=color)


def _frame(ax, labels, xlabel):
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_ylim(len(labels) - 0.4, -0.6)
    ax.set_xlim(-0.03, 1.03)
    ax.grid(axis="x", color=GRID, linewidth=0.6, zorder=0)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel(xlabel)


def _label(m, cells: dict | None) -> str:
    s = SHORT.get(m, m)
    if cells and any(c["finished"] < c["planned"] for c in cells.values()):
        s += f"  [n {sum(c['finished'] for c in cells.values())}/{sum(c['planned'] for c in cells.values())}]"
    return s


def fig_task_p(A: dict, P5: dict, path: Path, SUP: dict | None = None):
    plt = _plt()
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 3.9), sharex=True)
    for ax, tier in zip(axs, ("W", "H")):
        ms = [m for m in _models(A["models"]) if tier in A["models"][m]["tiers"]]
        src = {m: A for m in ms}
        if tier == "H" and SUP:              # v2-a4 (D118): the post-freeze supplement row, marked, drawn last
            for m in _models(SUP["models"]):
                if "H" in SUP["models"][m]["tiers"] and m not in src:
                    ms.append(m)
                    src[m] = SUP
        labels = []
        for y, m in enumerate(ms):
            D = src[m]
            t = D["models"][m]["tiers"][tier]
            sup = tier == "H" and any(r.endswith(SUPPLEMENT_SUFFIX) for r in D["models"][m].get("run_ids") or [])
            # the supplement planned only P3 + P4 (v2-a4): its n counts those cells
            labels.append(_label(m, {c: t["cells"][c] for c in ("P3", "P4")}) + " (post-freeze suppl.)" if sup
                          else _label(m, t["cells"]))
            _dot(ax, y - 0.16, t["C"]["adopt_check"]["P3"], BLUE, "o", t["cells"]["P3"]["below_min"],
                 "true status adopted, valid check (P3)" if y == 0 else None)
            _dot(ax, y, t["C"]["adopt_forged"]["P4"], ORANGE, "s", t["cells"]["P4"]["below_min"],
                 "forged status adopted, forged check (P4)" if y == 0 else None)
            p = P5["models"].get(m) if tier == "W" else None
            if p:
                _dot(ax, y + 0.16, p["adopt_forged_P5f"], AQUA, "D", p["cells"]["P5f"]["below_min"],
                     "forged status adopted, forged check + verify instruction (P5f)" if y == 0 else None)
        _frame(ax, labels, "share of named claims")
        ax.set_title("Tier W (wiring given)" if tier == "W" else "Tier H (wiring hidden; no P5)", loc="left",
                     fontsize=9)
    h, lab = axs[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", ncol=3, frameon=False, fontsize=7.5, bbox_to_anchor=(0.5, 1.03))
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def fig_task_s(A: dict, path: Path):
    plt = _plt()
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 3.6), sharex=True)
    for ax, tier in zip(axs, ("W", "H")):
        ms = [m for m in _models(A["models"]) if tier in A["models"][m]["tiers"]]
        ref = next(A["models"][m]["tiers"][tier]["reference_rows"] for m in ms
                   if A["models"][m]["tiers"][tier]["reference_rows"])
        labels = ["surface rule (reference)"]
        _dot(ax, -0.1, ref["surface_rule"]["overclaim"], MUTED, "s", True)
        _dot(ax, 0.1, ref["surface_rule"]["underclaim"], MUTED, "o", True)
        for y, m in enumerate(ms, start=1):
            t = A["models"][m]["tiers"][tier]
            labels.append(_label(m, t["cells"]))
            _dot(ax, y - 0.1, t["S"]["overclaim"], ORANGE, "s", label="overclaim: open claims given a definite "
                 "verdict" if y == 1 else None)
            _dot(ax, y + 0.1, t["S"]["underclaim"], BLUE, "o", label="underclaim: settled claims answered 'not "
                 "settled'" if y == 1 else None)
        _frame(ax, labels, "share of claims")
        ax.set_title("Tier W (wiring given)" if tier == "W" else "Tier H (wiring hidden)", loc="left", fontsize=9)
    h, lab = axs[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", ncol=2, frameon=False, fontsize=7.5, bbox_to_anchor=(0.5, 1.03))
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def fig_p5(P5: dict, path: Path):
    plt = _plt()
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ms = _models(P5["models"])
    labels = []
    for y, m in enumerate(ms):
        v = P5["models"][m]
        labels.append(_label(m, v["cells"]))
        _dot(ax, y - 0.16, v["exact"], AQUA, "D", v["cells"]["P5f"]["below_min"],
             "forged line quoted exactly (P5f)" if y == 0 else None)
        _dot(ax, y, v["lenient"], BLUE, "o", v["cells"]["P5f"]["below_min"],
             "forged line named, lenient (P5f)" if y == 0 else None)
        _dot(ax, y + 0.16, v["false_alarm"], ORANGE, "s", v["cells"]["P5v"]["below_min"],
             "false alarm on a valid check (P5v)" if y == 0 else None)
    _frame(ax, labels, "share of named claims")
    h, lab = ax.get_legend_handles_labels()       # R9: outside the data area (it covered the online rows)
    fig.legend(h, lab, loc="upper center", ncol=2, frameon=False, fontsize=7, bbox_to_anchor=(0.5, 1.08))
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


WORKED_WORLD = "pilot4|synthetic|rewired_control|0|"     # the worked example's world (Appendix C), never main panel
CA_STEPS = 64


def background_data() -> dict:
    """Figure 4 (Appendix E.1, D128): short rules against the behaviour they generate, from the repository's own
    objects and owners only (no dynamics re-implemented here).

    (a) Rule 110 = the semantics fixture ``Rule((0, 1, 2), 110)`` (docs/CODEC.md; tests/test_index_repr.py: inputs
        (right, centre, left), so the local table IS the Wolfram number), placed on a line of cells whose two end
        cells are constant 0; one seed cell at the right; stepped by ``index_repr.from_network(...).step`` through
        ``semantics.trajectory``.  The line is wide enough that the pattern never reaches an end cell (asserted),
        so every interior cell runs Rule 110 unmodified.
    (b) the worked-example world's canonical rules (``population.tier_public``; hidden mechanism, canonical form).
    (c) its whole behaviour: F(x) for all 2^n states, stepped by the same owner."""
    from ..index_repr import from_network
    from ..schema import Intervention, Network, Rule
    from ..semantics import trajectory
    from . import population as P

    r110 = Rule((0, 1, 2), 110)
    w = CA_STEPS + 4
    net = Network(w, (Rule((), 0),) + tuple(Rule((i - 1, i, i + 1), r110.table) for i in range(1, w - 1))
                  + (Rule((), 0),))
    ca = trajectory(from_network(net).step, 1 << 1, Intervention(), CA_STEPS)
    if any((s >> (w - 2)) & 1 for s in ca):
        raise AssertionError("Rule 110 pattern reached the constant end cell")
    m = json.loads((Path(__file__).resolve().parents[3] / "artifacts" / "sprint_pilot4_manifest.json").read_text())
    x = next(x for x in m["items"] if x["wkey"] == WORKED_WORLD and x["tier"] == "W")
    ev, pub = P.tier_public(P.WorldKey.from_json(x), "W")
    wn = ev.world.net.canonical()
    step = from_network(wn).step
    n = wn.n
    return {"rule110": {"rule_bits": 1 << r110.arity, "table": r110.table, "cells": w, "steps": CA_STEPS,
                        "diagram_bits": w * (CA_STEPS + 1), "rows": [format(s, f"0{w}b") for s in ca]},
            "world": {"wkey": WORKED_WORLD, "n": n, "labels": pub["node_labels"],
                      "rules": [r.to_json() for r in wn.rules],
                      "arity": sorted({r.arity for r in wn.rules}),
                      "table_bits": sum(1 << r.arity for r in wn.rules), "states": 1 << n,
                      "behaviour_bits": n << n, "successor": [step(s) for s in range(1 << n)]}}


def fig_background(B: dict, path: Path):
    plt = _plt()
    import numpy as np
    from matplotlib.colors import ListedColormap
    cm = ListedColormap(["white", INK])
    fig = plt.figure(figsize=(7.2, 2.8))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 0.5, 1.45], wspace=0.75)
    r = B["rule110"]
    a = fig.add_subplot(gs[0])
    img = np.array([[int(c) for c in row] for row in r["rows"]])        # string MSB first = leftmost = highest node
    a.imshow(img, cmap=cm, interpolation="nearest", aspect="auto")
    a.set_title(f"(a) Rule 110: {r['rule_bits']}-bit rule,\n{r['steps']} steps from one cell", fontsize=8)
    a.set_xticks([])
    a.set_ylabel("time step")
    W = B["world"]
    b = fig.add_subplot(gs[1])
    tab = np.array([[(ru["table"] >> y) & 1 for y in range(1 << max(W["arity"]))] for ru in W["rules"]])
    b.imshow(tab, cmap=cm, interpolation="nearest", aspect="auto", vmin=0, vmax=1)
    b.set_yticks(range(W["n"]))
    b.set_yticklabels([f"{W['labels'][j]} ← {','.join(W['labels'][i] for i in ru['inputs'])}"
                       for j, ru in enumerate(W["rules"])], fontsize=6.5)
    b.set_xticks(range(tab.shape[1]))
    b.set_xticklabels([format(y, f"0{max(W['arity'])}b")[::-1] for y in range(tab.shape[1])], fontsize=6.5)
    b.set_xticks(np.arange(-0.5, tab.shape[1]), minor=True)
    b.set_yticks(np.arange(-0.5, W["n"]), minor=True)
    b.grid(which="minor", color=MUTED, linewidth=0.4)
    b.tick_params(which="minor", length=0)
    b.set_xlabel("input values", fontsize=7)
    b.set_title(f"(b) world: {len(W['rules'])} tables,\n{W['table_bits']} bits", fontsize=8)
    c = fig.add_subplot(gs[2])
    beh = np.array([[(s >> j) & 1 for s in W["successor"]] for j in range(W["n"])])
    c.imshow(beh, cmap=cm, interpolation="nearest", aspect="auto")
    c.set_yticks(range(W["n"]))
    c.set_yticklabels(W["labels"], fontsize=6.5)
    c.set_xticks([0, W["states"] - 1])
    c.set_xlabel("state x (all of them)", fontsize=7)
    c.set_title(f"(c) its behaviour: next state of\nall {W['states']} states, {W['behaviour_bits']} bits",
                fontsize=8)
    for ax in (a, b, c):
        for s in ax.spines.values():
            s.set_visible(True)
            s.set_color(MUTED)
            s.set_linewidth(0.5)
        ax.tick_params(length=0)
    fig.savefig(path, bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)


def draw_background(out: str) -> None:
    """Figure 4 and its numbers (fig4_background.json, read by report/fill.py as root F)."""
    o = Path(out)
    B = background_data()
    (o / "fig4_background.json").write_text(json.dumps(B, indent=1, sort_keys=True) + "\n")
    fig_background(B, o / "fig4_background.png")
    print(f"figure 4 -> {o}")


def draw(out: str) -> None:
    o = Path(out)
    A = json.loads((o / "analysis.json").read_text())
    P5 = json.loads((o / "p5_analysis.json").read_text())
    sp = o / "supplement" / "analysis.json"
    fig_task_p(A, P5, o / "fig1_task_p.png", json.loads(sp.read_text()) if sp.exists() else None)
    fig_task_s(A, o / "fig2_task_s.png")
    fig_p5(P5, o / "fig3_p5.png")
    print(f"figures 1-3 -> {o}")
    draw_background(out)


if __name__ == "__main__":     # Figure 4 alone (it reads no run): python -m causalguard.sprint.figures [out]
    import sys
    draw_background(sys.argv[1] if len(sys.argv) > 1 else "reports/sprint_all")
