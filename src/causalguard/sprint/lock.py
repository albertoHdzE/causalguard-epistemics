"""R7 sprint design lock writer (pre-sprint).  Assembles ``docs/SPRINT_DESIGN_LOCK.json`` from the committed design
objects (hashes recomputed from the files, never typed in) plus the decisions passed in ``lock_inputs.json``.

  python -m causalguard.sprint.lock <lock_inputs.json>
"""
from __future__ import annotations

import hashlib
import json
import sys

from . import population as P
from . import scoring as S
from . import surface
from . import tasks as T
from .models import LOCAL


def _sha(path: str) -> str:
    return hashlib.sha256((P.REPO / path).read_bytes()).hexdigest()


def build(inputs: dict) -> dict:
    main = json.loads((P.REPO / "artifacts/sprint_main_manifest.json").read_text())
    lock = {
        "lock_version": "r7-sprint-lock-v1",
        "label": "PRE-SPRINT (R7, 2026-11-12). Locked before the first main-panel request.",
        "tasks": {"task_version": T.TASK_VERSION, "template_sha256": T.template_hashes(),
                  "tasks_doc": "docs/SPRINT_TASKS.md", "verdicts": ["true", "false", "not settled"],
                  "answer_validity": "verdict valid => answer valid; probability kept if in [0, 1] (D73)"},
        "conditions": {"P0": "neutral", "P1": "empty disagreement on 4 named claims",
                       "P2": "demand to commit", "P3": "exact checker result with witnesses on 4 named claims",
                       "assignment": "one balanced round-robin over strata in sha256 order (D72); wording "
                                     "alternates per full round; named claims = 4 smallest sha256(salt, wkey, cid)"},
        "populations": {"version": P.POP_VERSION, "splits": {s: {"r5_split": P.R5_SPLIT[s], "design_salt":
                                                                 P.DESIGN_SALT[s], "assign_salt": P.ASSIGN_SALT[s]}
                                                             for s in P.SPLITS},
                        "published_groups": P.PUBLISHED_GROUPS,
                        "manifests_sha256": {f"artifacts/sprint_{s}_manifest.json":
                                             _sha(f"artifacts/sprint_{s}_manifest.json")
                                             for s in ("smoke", "pilot", "main")},
                        "main_panel_worlds": main["n_worlds"]},
        "surface_rule": {"version": surface.RULE_VERSION, "file": "artifacts/sprint_surface_rule.json",
                         "sha256_field": json.loads((P.REPO / "artifacts/sprint_surface_rule.json").read_text())
                         ["sha256"]},
        "scores": {"task_s": ["overclaim", "underclaim", "wrong_settled", "accuracy", "balanced_accuracy",
                              "prob_mae", "brier", "brier_pstar", "incoherent (strict)", "incoherent_tol05"],
                   "task_p": ["capitulation_named (P0, P1)", "capitulation_all (P0, P2)",
                              "forced_overclaim (P0, P2)", "repair_named (P0, P3)", "collateral (P0, P1, P3)",
                              "changed_any", "overclaim_t2"],
                   "gate_remedy": "turn-1 answers with every settled verdict passed through the exact check",
                   "unit": "world; per-world rates, worlds with an empty denominator undefined (counted)",
                   "intervals": f"95 % percentile, {S.B_DEFAULT} cluster-bootstrap replicates (source groups), "
                                f"seed {S.SEED}; contrasts across conditions resample within condition",
                   "multiplicity": "Holm across models for 'differs from zero' claims on discernment"},
        "analysis_command": "python -m causalguard sprint-analyze --run-dir runs/<run> ... --out reports/sprint_local",
        "models": inputs["models"],
        "online_models_planned": inputs.get("online_models_planned"),
        "panel": inputs["panel"],
        "contrasts": inputs["contrasts"],
        "exclusions": inputs["exclusions"],
        "predictions": inputs["predictions"],
        "seen_before_lock": inputs["seen_before_lock"],
        "local_ladder_candidates": [m["model"] for m in LOCAL],
    }
    return lock


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    inputs = json.loads(open(argv[0]).read())
    lock = build(inputs)
    (P.REPO / "docs/SPRINT_DESIGN_LOCK.json").write_text(json.dumps(lock, indent=1, sort_keys=True) + "\n")
    print("wrote docs/SPRINT_DESIGN_LOCK.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
