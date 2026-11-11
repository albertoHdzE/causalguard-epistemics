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
    elif study in ("S4-MAP", "S4-ACTIVE"):
        for fam in cfg["families"]:
            for i in range(cfg.get("start", 0), cfg.get("start", 0) + cfg["worlds_per_family"]):
                yield f"{fam}|{i}", {"salt": cfg["salt"], "index": i, "family": fam, **cfg.get("payload", {})}
    elif study == "S4-STRESS":
        for cell in cfg["cells"]:
            for s in range(cell["seeds"]):
                for backend in cell["backends"]:
                    yield (f"n{cell['n']}|{s}|{backend}", {"n": cell["n"], "seed": 1000 * cell["n"] + s,
                                                           "backend": backend, "budget": cell["budget"],
                                                           **cfg.get("payload", {})})
    elif study == "S4-KNOWN":
        for n in cfg["sizes"]:
            for s in range(cfg["seeds"]):
                yield f"n{n}|{s}", {"n": n, "seed": 7919 * n + s, "queries": cfg.get("queries", 6)}
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
    if study.startswith("S4-"):
        from .s4 import offline
        return {"S4-MAP": offline.map_world, "S4-ACTIVE": offline.active_world, "S4-STRESS": offline.stress_item,
                "S4-KNOWN": offline.known_item}[study]
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
    a2 = sub.add_parser("analyze-s2-v2")
    a2.add_argument("--run-dir", required=True, action="append")
    a2.add_argument("--endpoint", default="configs/endpoints/S2-primary-v2.json")
    a2.add_argument("--mc-run-dir", default=None)
    a2.add_argument("--no-development-sizing", action="store_true", help="skip prospective sizing (development only)")
    a2.add_argument("--out", default="reports/development_r3")
    a1 = sub.add_parser("analyze-s1-v2")
    a1.add_argument("--run-dir", required=True, action="append")
    a1.add_argument("--out", default="reports/development_r3")
    a3 = sub.add_parser("analyze-s3-v2")
    a3.add_argument("--run-dir", required=True, action="append")
    a3.add_argument("--baselines", default="reports/development_r2/s3_baselines_v2.json")
    a3.add_argument("--role-baselines", default="reports/development_r3/s3_role_baselines_v3.json",
                    help="iteration-3 role-specific baselines + design-known rule ('none' = historical v2 analysis)")
    a3.add_argument("--out", default="reports/development_r3")
    sub.add_parser("fit-s3-role-baselines").add_argument("--out", default="reports/development_r3/s3_role_baselines_v3.json")
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
    if args.cmd == "analyze-s2-v2":
        from .analysis.s2_analysis import analyze_v2
        res = analyze_v2([Path(d) for d in args.run_dir], Path(args.out), Path(args.endpoint),
                         Path(args.mc_run_dir) if args.mc_run_dir else None,
                         development_sizing=False if args.no_development_sizing else None)
        print(json.dumps(res, indent=1, default=float)[:4000])
        return 0
    if args.cmd == "analyze-s1-v2":
        from .analysis.s1_analysis import analyze_v2 as s1v2
        print(json.dumps(s1v2([Path(d) for d in args.run_dir], Path(args.out)), indent=1, default=str)[:4000])
        return 0
    if args.cmd == "analyze-s3-v2":
        from .analysis.s3_analysis import analyze_v2 as s3v2
        rb = None if args.role_baselines == "none" else Path(args.role_baselines)
        print(json.dumps(s3v2([Path(d) for d in args.run_dir], Path(args.out), Path(args.baselines),
                              role_baselines_path=rb), indent=1, default=float)[:4000])
        return 0
    if args.cmd == "fit-s3-role-baselines":
        from .analysis.s3_analysis import fit_role_baselines
        art = fit_role_baselines(Path(args.out))
        print(json.dumps({"out": args.out, "sha256": art["sha256"]}))
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
