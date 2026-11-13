"""SPRINT report figures 1-3, drawn from ``analysis.json`` and ``p5_analysis.json`` (no number computed here).

Dot plots, one row per model (names on the axis, so no label collides), 95 % intervals as thin lines.  Categorical
slots 1-3 of the dataviz reference palette (validated: CVD worst adjacent dE 9.2; the aqua slot's contrast warning
is relieved by distinct marker shapes and the legend; every figure has a table in the report).  A cell below the
D102(d) minimum is drawn hollow and its row label carries n finished / n planned.

  Fig 1  Task P: adoption of the true status under P3, of the forged status under P4 and under P5f; Tier W, Tier H
  Fig 2  Task S: overclaim and underclaim per model, Tier W and Tier H, with the surface rule as a reference row
  Fig 3  P5: exact and lenient detection of the forged line (P5f) and false alarm (P5v)
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


def fig_task_p(A: dict, P5: dict, path: Path):
    plt = _plt()
    fig, axs = plt.subplots(1, 2, figsize=(9.2, 3.9), sharex=True)
    for ax, tier in zip(axs, ("W", "H")):
        ms = [m for m in _models(A["models"]) if tier in A["models"][m]["tiers"]]
        labels = []
        for y, m in enumerate(ms):
            t = A["models"][m]["tiers"][tier]
            labels.append(_label(m, t["cells"]))
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
    ax.legend(loc="lower right", frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def draw(out: str) -> None:
    o = Path(out)
    A = json.loads((o / "analysis.json").read_text())
    P5 = json.loads((o / "p5_analysis.json").read_text())
    fig_task_p(A, P5, o / "fig1_task_p.png")
    fig_task_s(A, o / "fig2_task_s.png")
    fig_p5(P5, o / "fig3_p5.png")
    print(f"figures 1-3 -> {o}")
