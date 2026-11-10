"""CausalGuard command line.

  python -m causalguard run --config configs/s2_dev.json [--run-id ID] [--workers N] [--quiet]
  python -m causalguard analyze-s2 --run-id ID [--out reports/development]
  python -m causalguard analyze-s1 --run-id ID [--out reports/development]
  python -m causalguard fixtures     # print the semantic fixture table
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _items_from_config(cfg: dict):
    """Planned items of a development config (runner v2).  v1 S2 configs are historical (tag v0.1.0-dev)."""
    study = cfg["study"]
    if study == "S2":
        if cfg.get("design_version") != "s2-design-v2":
            raise SystemExit("S2 v1 configs are historical: reproduce them from tag v0.1.0-dev")
        for pop in cfg["populations"]:
            label = pop.get("label", pop["population"])
            for fam in pop["families"]:
                for i in range(pop["start"], pop["start"] + pop["worlds_per_family"]):
                    payload = {"salt": cfg["salt"], "index": i, "family": fam, "population": pop["population"],
                               "label": label, "design_version": cfg["design_version"], "n": cfg["n"],
                               "kmax": cfg["kmax"], "budgets": cfg["budgets"],
                               "regimes": pop.get("regimes", cfg["regimes"]),
                               "noise_rates": pop.get("noise_rates", []),
                               "noise_budgets": pop.get("noise_budgets", [16, 32, 64]),
                               "verdicts": pop.get("verdicts", True)}
                    yield f"{label}|{fam}|{i}", payload
    elif study == "S2-MCDIAG":
        for pop in cfg["populations"]:
            for fam in pop["families"]:
                for i in range(pop["start"], pop["start"] + pop["worlds_per_family"]):
                    yield (f"mcdiag|{pop['population']}|{fam}|{i}",
                           {"salt": cfg["salt"], "index": i, "family": fam, "population": pop["population"],
                            "design_version": cfg["design_version"], "n": cfg["n"], "kmax": cfg["kmax"],
                            "budget": cfg["budget"], "mc_budgets": cfg["mc_budgets"], "mc_reps": cfg["mc_reps"]})
    elif study == "S1":
        for cell in cfg["cells"]:
            for i in range(cell.get("start", 0), cell.get("start", 0) + cell["seeds"]):
                for backend in cfg["backends"]:
                    yield (f"{cell['family']}|n{cell['n']}|{i}|{backend}",
                           {"salt": cfg["salt"], "index": i, "family": cell["family"], "n": cell["n"],
                            "backend": backend, "query_timeout_s": cfg["query_timeout_s"],
                            "limits": cfg["limits"]})
    else:
        raise SystemExit(f"unknown study {study}")


def _strata(payload: dict) -> dict:
    return {k: payload[k] for k in ("family", "population", "label", "n", "backend", "index") if k in payload}


def _fn_for(study: str):
    if study == "S2":
        from .experiments.s2 import run_world_v2
        return run_world_v2
    if study == "S2-MCDIAG":
        from .experiments.s2 import mc_diagnostic_world
        return mc_diagnostic_world
    if study == "S1":
        from .experiments.s1 import run_item
        return run_item
    raise SystemExit(study)


def build_plan(cfg: dict, run_id: str) -> dict:
    from .runner import make_plan
    extra = {}
    if cfg.get("endpoint"):
        root = Path(__file__).resolve().parents[2]
        ep = (root / cfg["endpoint"]).read_bytes()
        import hashlib
        extra["endpoint"] = {"path": cfg["endpoint"], "sha256": hashlib.sha256(ep).hexdigest(),
                             "spec": json.loads(ep)}
    return make_plan(run_id, cfg["study"], cfg, list(_items_from_config(cfg)), strata_fn=_strata, extra=extra)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="causalguard")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--config", required=True)
    r.add_argument("--run-id")
    r.add_argument("--workers", type=int, default=None)
    r.add_argument("--quiet", action="store_true")
    r.add_argument("--resume", action="store_true", help="continue an existing run under its identical plan")
    r.add_argument("--retry-failed", action="store_true", help="re-run failed items (old attempts are kept)")
    r.add_argument("--runs-root", default=None)
    for name in ("analyze-s2", "analyze-s1"):
        a = sub.add_parser(name)
        a.add_argument("--run-id", required=True, action="append")
        a.add_argument("--out", default="reports/development")
    sub.add_parser("fixtures")
    args = ap.parse_args(argv)

    if args.cmd == "run":
        from .runner import Run
        cfg = json.loads(Path(args.config).read_text())
        if cfg.get("mode") != "development":
            raise SystemExit("only development configs run here; confirmatory runs need scripts/run_confirmatory.py")
        run_id = args.run_id or cfg["run_id"]
        run = Run(run_id, build_plan(cfg, run_id), runs_root=Path(args.runs_root) if args.runs_root else None,
                  resume=args.resume)
        end = run.execute(_fn_for(cfg["study"]), workers=args.workers or cfg.get("workers", 4),
                          timeout_s=cfg.get("item_timeout_s", 900), quiet=args.quiet, retry_failed=args.retry_failed,
                          mode="development", maxtasks=cfg.get("maxtasks", 50))
        print(json.dumps(end, sort_keys=True))
        return 0 if end["status"] == "complete" else 3
    if args.cmd == "analyze-s2":
        from .analysis.s2_analysis import analyze
        print(json.dumps(analyze(args.run_id, Path(args.out)), indent=1)[:4000])
        return 0
    if args.cmd == "analyze-s1":
        from .analysis.s1_analysis import analyze
        print(json.dumps(analyze(args.run_id, Path(args.out)), indent=1)[:4000])
        return 0
    if args.cmd == "fixtures":
        root = Path(__file__).resolve().parents[2]
        fx = json.loads((root / "data/fixtures/semantic_fixtures.json").read_text())
        for c in fx["model_fixtures"] + fx["evidence_fixtures"]:
            print(f"{c['id']:40s} {c['expected']:32s} {c['explanation']}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
