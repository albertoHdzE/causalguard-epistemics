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
    elif study in ("S4-MAP", "S4-ACTIVE", "S4-MISSPEC"):
        for fam in cfg["families"]:
            for i in range(cfg.get("start", 0), cfg.get("start", 0) + cfg["worlds_per_family"]):
                yield f"{fam}|{i}", {"salt": cfg["salt"], "index": i, "family": fam, **cfg.get("payload", {})}
    elif study == "S4-PILOT":
        for fam in cfg["families"]:
            for i in range(cfg.get("start", 0), cfg.get("start", 0) + cfg["worlds_per_family"]):
                yield f"{fam}|{i}", {"salt": cfg["salt"], "index": i, "family": fam, "provider": cfg["provider"],
                                     "global_cap": cfg["global_cap"], "call_ledger": cfg["call_ledger"],
                                     "world_cap": cfg["world_cap"]}
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
    elif study == "R5-G":
        from .r5 import data as D
        if cfg.get("external_panel"):
            man = json.loads((Path(__file__).resolve().parents[2] / cfg["source_manifest"]).read_text())
            for x in man[cfg["external_panel"]]:
                yield (f"{cfg['external_panel']}|{x['key']}",
                       {"external_key": x["key"], "panel": cfg["external_panel"], "group": x["group"],
                        "transformation": x["transformation"], "design_salt": cfg["design_salt"],
                        **({"xdc_bases": cfg["xdc_bases"]} if cfg.get("xdc_bases") else {})})
        else:
            for s in D.STRATA:
                for i in range(D.SPLITS[cfg["split"]]["per_stratum"]):
                    yield f"{cfg['split']}|{s}|{i}", {"split": cfg["split"], "stratum": s, "index": i,
                                                      "design_salt": cfg["design_salt"],
                                                      **({"xdc_bases": cfg["xdc_bases"]} if cfg.get("xdc_bases") else {})}
    elif study == "R6-S":
        man = json.loads(Path(cfg["source_manifest"]).read_text())
        for pan in cfg["panels"]:
            for x in man[pan]:
                if x["split"] != cfg["split"]:
                    continue
                yield (f"{pan}|{x['key']}",
                       {"key": x["key"], "panel": pan, "group": x["group"], "split": x["split"],
                        "design_salt": cfg["design_salt"], "budgets": cfg["budgets"], "max_budget": cfg["max_budget"],
                        "clamped_edge_fraction": x["clamped_edge_fraction"],
                        "group_seen_in_n8": x["group_seen_in_n8_panels"]})
    elif study == "R5-M":
        from .r5.misspec import PANELS, panel_members
        for pan in PANELS:
            mem, _ = panel_members(pan, cfg["per_panel"], cfg["salt"])
            for m in mem:
                yield f"{pan}|{m['index']}", m
    elif study == "R5-C":
        import random as _r

        from .r5.benchmark import BACKENDS, REPEAT_SUBSET, SIZES
        items = [(f"n{n}|b{b}|{be}|r0", {"n": n, "base": b, "backend": be, "rep": 0})
                 for n in SIZES for b in range(8) for be in BACKENDS]
        items += [(f"n{n}|b{b}|{be}|r{r}", {"n": n, "base": b, "backend": be, "rep": r})
                  for (n, b) in REPEAT_SUBSET for be in BACKENDS for r in (1, 2)]
        if cfg.get("only"):                                    # supplementary rerun of named cells (R5-04)
            items = [it for it in items if it[1]["n"] in cfg["only"]["sizes"] and
                     it[1]["backend"] in cfg["only"]["backends"]]
        _r.Random(cfg["order_seed"]).shuffle(items)           # randomized backend/instance order (serial run)
        yield from items
    elif study in ("R5-A-DET", "R5-A-AI"):
        from .r5.investigation import population
        keys, _ = population(cfg["split"], cfg["per_stratum"])
        if cfg.get("max_items"):                                  # R6 A2 smoke: first worlds of the order only
            keys = keys[:cfg["max_items"]]
        for k in keys:
            pl = dict(k)
            if study == "R5-A-AI":
                pl.update({"provider": cfg["provider"], "global_cap": cfg["global_cap"],
                           "call_ledger": cfg["call_ledger"], "phase": cfg["phase"], "phase_cap": cfg["phase_cap"],
                           "arms": cfg.get("arms", ["D", "B"]),
                           **({"gate_loop": True} if cfg.get("gate_loop") else {})})
            yield f"{k['split']}|{k['stratum']}|{k['index']}", pl
    elif study == "SPRINT":
        # R7 sprint benchmark: items from a committed manifest, run in sha256 order of the world key (a model on a
        # half panel runs the first ``max_items`` of this order; decided in the lock before its run)
        import hashlib
        root = Path(__file__).resolve().parents[2]
        man = json.loads((root / cfg["manifest"]).read_text())
        items = sorted(man["items"], key=lambda x: hashlib.sha256(f"r7-run-order|{x['wkey']}".encode()).hexdigest())
        if cfg.get("tiers"):                # R7b pilot: restrict a model to some tiers
            items = [x for x in items if x.get("tier") in cfg["tiers"]]
        if cfg.get("per_tier"):             # R7b online smoke: the first k worlds per tier in run order
            cnt: dict = {}
            keep = []
            for x in items:
                t = x.get("tier")
                if cnt.get(t, 0) < cfg["per_tier"]:
                    keep.append(x)
                cnt[t] = cnt.get(t, 0) + 1
            items = keep
        if cfg.get("half_panel"):           # R7b (D79): the first half by run order within (tier, condition)
            seen: dict = {}
            tot: dict = {}
            for x in items:
                g = (x.get("tier"), x["condition"])
                tot[g] = tot.get(g, 0) + 1
            keep = []
            for x in items:
                g = (x.get("tier"), x["condition"])
                if seen.get(g, 0) < (tot[g] + 1) // 2:
                    keep.append(x)
                seen[g] = seen.get(g, 0) + 1
            items = keep
        if cfg.get("max_items"):
            items = items[:cfg["max_items"]]
        for x in items:
            world = {k: x[k] for k in ("split", "population", "stratum", "index", "source_key", "group")}
            yield x["wkey"], {"world": world, "condition": x["condition"], "wording": x["wording"],
                              "named": x["named"], "public_sha256": x["public_sha256"], "provider": cfg["provider"],
                              "global_cap": cfg["global_cap"], "call_ledger": cfg["call_ledger"],
                              "phase": cfg.get("phase", "SPRINT"), "phase_cap": cfg.get("phase_cap"),
                              "world_cap": cfg.get("world_cap", 4), "two_turns": cfg.get("two_turns", True),
                              **({"task_wording": cfg["task_wording"]} if cfg.get("task_wording") else {}),
                              **{f: x[f] for f in ("tier", "checker_status", "forged_status", "forgery_kind")
                                 if f in x},
                              **({"salt": man["assign_salt"]} if "tier" in x else {}),
                              "stratum": x["stratum"], "population": x["population"]}
    else:
        raise SystemExit(f"unknown study {study}")


def _strata(payload: dict) -> dict:
    return {k: payload[k] for k in ("family", "population", "label", "n", "backend", "index", "stratum", "split",
                                    "panel", "base") if k in payload}


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
    if study.startswith("R5-"):
        if study == "R5-G":
            from .r5.forecast import g_world
            return g_world
        if study == "R5-M":
            from .r5.misspec import m_world
            return m_world
        if study == "R5-C":
            from .r5.benchmark import c_item
            return c_item
        from .r5.investigation import a_ai_item, a_det_item
        return a_det_item if study == "R5-A-DET" else a_ai_item
    if study == "R6-S":
        from .r6.scale import s_world
        return s_world
    if study == "SPRINT":
        from .sprint.episode import sprint_world
        return sprint_world
    if study.startswith("S4-"):
        from .s4 import offline
        if study == "S4-PILOT":
            from .s4.pilot import pilot_world
            return pilot_world
        return {"S4-MAP": offline.map_world, "S4-ACTIVE": offline.active_world, "S4-STRESS": offline.stress_item,
                "S4-KNOWN": offline.known_item, "S4-MISSPEC": offline.misspec_world}[study]
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


SPRINT_COMMANDS = {"sprint-build": "build", "sprint-analyze": "analysis", "sprint-gates": "gates",
                   "sprint-online": "online"}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] in SPRINT_COMMANDS:            # R7 sprint commands own their argument parsers
        import importlib
        return importlib.import_module(f".sprint.{SPRINT_COMMANDS[argv[0]]}", __package__).main(argv[1:])
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
    sub.add_parser("r5-demo", help="R5 integrated demonstration (illustration, not evidence)")
    inv = sub.add_parser("r5-inventory", help="write the external-model source manifest (no evaluation)")
    inv.add_argument("--out", default="artifacts/r5_source_manifest.json")
    inv.add_argument("--transformed-groups", nargs=2, type=int, default=None,
                     help="rank slice lo hi of the fixed group hash ordering (R6 fresh panel: 40 162)")
    ar = sub.add_parser("analyze-r5", help="R5 track analyses (no model calls)")
    ar.add_argument("--track", required=True, choices=["g-champion", "g", "g-external", "m", "a-det", "a-select",
                                                       "a-ai", "c", "g-r6", "g-r6-extras", "s-cal", "s", "a2"])
    ar.add_argument("--method", default="xdc[cgh_flat]")
    ar.add_argument("--external", action="store_true")
    ar.add_argument("--run", action="append", required=True)
    ar.add_argument("--det-run")
    ar.add_argument("--champion")
    ar.add_argument("--selected")
    ar.add_argument("--out", required=True)
    dm = sub.add_parser("s4-demo")
    dm.add_argument("--live", default=None, help="provider config JSON for a local model (optional)")
    a4 = sub.add_parser("analyze-s4")
    a4.add_argument("--map", default=None)
    a4.add_argument("--active", default=None)
    a4.add_argument("--known", default=None)
    a4.add_argument("--misspec", default=None)
    a4.add_argument("--stress", action="append", default=[])
    a4.add_argument("--pilot", action="append", default=[])
    a4.add_argument("--baselines", default="reports/development_r4/s4_surface_baselines.json")
    a4.add_argument("--out", default="reports/development_r4")
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
    if args.cmd == "r5-demo":
        from .r5.demo import run_demo
        run_demo()
        return 0
    if args.cmd == "r5-inventory":
        from .r5.external import inventory
        kw = {"transformed_groups": tuple(args.transformed_groups)} if args.transformed_groups else {}
        Path(args.out).write_text(json.dumps(inventory(**kw), indent=1, sort_keys=True) + "\n")
        return 0
    if args.cmd == "analyze-r5":
        from .analysis import r5_analysis as R
        t = args.track
        if t == "g-champion":
            obj = R.select_champion(args.run[0])
        elif t == "g":
            obj = R.analyze_g(args.run[0], args.champion)
        elif t == "g-external":
            obj = R.analyze_g_external(args.run[0], args.champion)
        elif t == "g-r6":
            obj = R.analyze_g_r6(args.run[0], args.champion, args.method, external=args.external)
        elif t == "a2":                                       # --run control loop [control loop ...] --det-run
            obj = R.analyze_a2(list(zip(args.run[0::2], args.run[1::2])), args.det_run)
        elif t == "s-cal":
            obj = R.analyze_s_calibration(args.run[0])
        elif t == "s":
            lock = json.loads(Path("docs/R6S_DESIGN_LOCK.json").read_text())
            obj = {pan: R.analyze_s(args.run[0], lock["flat"], lock["method"], pan, tuple(lock["budgets"]),
                                    lock["primary_budget"]) for pan in lock["report_panels"]}
        elif t == "g-r6-extras":
            obj = R.analyze_g_r6_extras(args.run[0], args.champion, args.method, external=args.external)
        elif t == "m":
            obj = R.analyze_m(args.run[0])
        elif t == "a-det":
            obj = R.analyze_a_det(args.run[0])
        elif t == "a-select":
            obj = R.select_det_policy(args.run[0])
        elif t == "a-ai":
            obj = R.analyze_a_ai(args.run, args.det_run, args.selected)
        else:
            obj = R.analyze_c(args.run[0])
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(obj, indent=1, sort_keys=True, default=float) + "\n")
        return 0
    if args.cmd == "s4-demo":
        from .s4.demo import run_demo
        cfg = json.loads(Path(args.live).read_text())["provider"] if args.live else None
        log = run_demo(cfg)
        print("\n" + json.dumps({k: v for k, v in log.items() if k != "steps"}))
        return 0
    if args.cmd == "analyze-s4":
        from .analysis import s4_analysis as A
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        res = {}
        if args.map:
            res["map"] = A.summarize_map(args.map)
        if args.active:
            res["active"] = A.summarize_active(args.active)
        if args.known:
            res["known"] = A.summarize_known(args.known)
        if args.misspec:
            res["misspec"] = A.summarize_misspec(args.misspec)
        for s in args.stress:
            res.setdefault("stress", {})[Path(s).name] = A.summarize_stress(s)
        for k, v in res.items():
            (out / f"s4_{k}_summary.json").write_text(json.dumps(v, indent=1, default=float) + "\n")
        if args.pilot:
            rep = A.analyze_pilot(args.pilot, args.baselines, out)
            (out / "s4_sizing.json").write_text(json.dumps(A.sizing(rep), indent=1, default=float) + "\n")
            res["pilot"] = {m: {"arm_means": x["arm_means"], "contrasts": x["contrasts_verdict_acc"]}
                            for m, x in rep["models"].items()}
        print(json.dumps(res, indent=1, default=float)[:6000])
        return 0
    if args.cmd == "fixtures":
        root = Path(__file__).resolve().parents[2]
        fx = json.loads((root / "data/fixtures/semantic_fixtures.json").read_text())
        for c in fx["model_fixtures"] + fx["evidence_fixtures"]:
            print(f"{c['id']:40s} {c['expected']:32s} {c['explanation']}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
