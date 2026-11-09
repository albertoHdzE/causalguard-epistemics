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
    study = cfg["study"]
    if study == "S2":
        for pop in cfg["populations"]:
            for fam in pop["families"]:
                for i in range(pop["start"], pop["start"] + pop["worlds_per_family"]):
                    payload = {"salt": cfg["salt"], "index": i, "family": fam, "population": pop["population"],
                               "n": cfg["n"], "kmax": cfg["kmax"], "budgets": cfg["budgets"],
                               "regimes": pop.get("regimes", cfg["regimes"]), "mc_samples": cfg["mc_samples"],
                               "noise_rates": pop.get("noise_rates", []),
                               "noise_budgets": pop.get("noise_budgets", [16, 32, 64]),
                               "verdicts": pop.get("verdicts", True)}
                    yield f"{pop['population']}|{fam}|{i}", payload
    elif study == "S1":
        for cell in cfg["cells"]:
            for i in range(cell["seeds"]):
                for backend in cfg["backends"]:
                    yield (f"{cell['family']}|n{cell['n']}|{i}|{backend}",
                           {"salt": cfg["salt"], "index": i, "family": cell["family"], "n": cell["n"],
                            "backend": backend, "query_timeout_s": cfg["query_timeout_s"],
                            "limits": cfg["limits"]})
    else:
        raise SystemExit(f"unknown study {study}")


def _fn_for(study: str):
    if study == "S2":
        from .experiments.s2 import run_world
        return run_world
    if study == "S1":
        from .experiments.s1 import run_item
        return run_item
    raise SystemExit(study)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="causalguard")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--config", required=True)
    r.add_argument("--run-id")
    r.add_argument("--workers", type=int, default=None)
    r.add_argument("--quiet", action="store_true")
    r.add_argument("--limit", type=int, default=None, help="only the first N items (smoke path)")
    for name in ("analyze-s2", "analyze-s1"):
        a = sub.add_parser(name)
        a.add_argument("--run-id", required=True, action="append")
        a.add_argument("--out", default="reports/development")
    sub.add_parser("fixtures")
    args = ap.parse_args(argv)

    if args.cmd == "run":
        from .runner import Run
        cfg = json.loads(Path(args.config).read_text())
        if cfg.get("mode") == "confirmatory":
            raise SystemExit("confirmatory configs must be run with scripts/run_confirmatory.py (freeze checks)")
        run_id = args.run_id or cfg["run_id"]
        items = list(_items_from_config(cfg))
        if args.limit:
            items = items[: args.limit]
        run = Run(run_id, cfg)
        end = run.execute(items, _fn_for(cfg["study"]), workers=args.workers or cfg.get("workers", 4),
                          timeout_s=cfg.get("item_timeout_s", 900), quiet=args.quiet,
                          mode=cfg.get("mode", "development"), maxtasks=cfg.get("maxtasks", 50))
        print(json.dumps(end, sort_keys=True))
        return 0 if end["failed"] == 0 else 3
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
