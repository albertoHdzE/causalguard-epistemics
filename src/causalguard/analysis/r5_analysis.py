"""R5 analyses (no model calls).  One function per track; every planned item is accounted for.

G  champion selection on CALIBRATION (B = 16, equal stratum weights, fixed tie order), the primary contrast
   Brier(champion) - Brier(full CGH) on evaluation (positive favours full CGH) with a source-group cluster
   bootstrap, worst-case missingness bounds, ablations, budget curves, per-stratum tables, determined /
   underdetermined strata, accuracy, reliability bins, refusal/cost; external panels separately.
M  per panel x policy rates with base-world cluster intervals; tradeoff table.
A  deterministic-policy selection on calibration; AI pilot resolved@4 contrast vs the selected policy (paired by
   world), curves, invalid actions, wrong definite verdicts, Brier, calls/tokens/latency, AI-copied-EIG rate.
C  exactness agreement, censored checkpoint curves, reuse, workspace vs full release, memory.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from ..stats import cluster_bootstrap

REPS = 10000
SEED = 20261111


def _load(run_dir):
    from ..runner import load_run
    return load_run(Path(run_dir))


def _ok(lr) -> tuple[dict, list[str]]:
    planned = [e["item_id"] for e in lr["plan"]["items"]]
    return lr["results"], [i for i in planned if i not in lr["results"]]


# =========================================================================== G

def _world_brier(row_preds, outcomes, name):
    """(point, lower, upper) world Brier over ALL scheduled queries; missing predictions bounded by [0, 1]."""
    pts, lo, hi = [], [], []
    for q in row_preds:
        y = outcomes[q["query_id"]]
        pr = q["predictions"].get(name)
        if pr is None or pr["p"] is None:
            pts.append(np.nan)
            lo.append(0.0)
            hi.append(1.0)
        else:
            b = (pr["p"] - y) ** 2
            pts.append(b)
            lo.append(b)
            hi.append(b)
    return float(np.mean(pts)), float(np.mean(lo)), float(np.mean(hi))


def g_table(run_dir, budget="16") -> dict:
    lr = _load(run_dir)
    res, missing = _ok(lr)
    rows = []
    for iid, r in res.items():
        ident = r["identity"]
        cell = r["predictions"].get(budget)
        rows.append({"item": iid, "stratum": ident.get("stratum", ident.get("panel")),
                     "group": ident["source_group_id"], "cell": cell, "outcomes": r["outcomes"]})
    return {"rows": rows, "missing_items": missing, "planned": len(lr["plan"]["items"])}


def _names(rows):
    return sorted(rows[0]["cell"]["queries"][0]["predictions"]) if rows else []


def _strat_mean(vals, strata):
    labs = sorted(set(strata))
    return float(np.mean([np.mean([v for v, s in zip(vals, strata) if s == lab]) for lab in labs]))


def select_champion(cal_run, budget="16") -> dict:
    from ..r5.priors import CHAMPION_CANDIDATES
    t = g_table(cal_run, budget)
    rows = t["rows"]
    strata = [r["stratum"] for r in rows]
    scores = {}
    for c in CHAMPION_CANDIDATES:
        b = [_world_brier(r["cell"]["queries"], r["outcomes"], c)[0] for r in rows]
        if any(np.isnan(x) for x in b):
            scores[c] = None
            continue
        scores[c] = _strat_mean(b, strata)
    elig = [(scores[c], i, c) for i, c in enumerate(CHAMPION_CANDIDATES) if scores[c] is not None]
    champ = min(elig)[2]
    ref = {c: _strat_mean([_world_brier(r["cell"]["queries"], r["outcomes"], c)[0] for r in rows], strata)
           for c in ("cgh_prior", "cgh_flat")}
    diffs = [(_world_brier(r["cell"]["queries"], r["outcomes"], champ)[0] -
              _world_brier(r["cell"]["queries"], r["outcomes"], "cgh_prior")[0]) for r in rows]
    sd = float(np.nanstd(diffs, ddof=1))
    n_eval_groups = 280
    return {"budget": budget, "candidates": list(CHAMPION_CANDIDATES), "tie_order": list(CHAMPION_CANDIDATES),
            "calibration_brier": scores, "champion": champ, "calibration_worlds": len(rows),
            "missing_calibration_items": t["missing_items"], "reference_brier_not_used_for_selection": ref,
            "precision_planning": {"world_sd_of_difference": sd, "approx_se_at_280_groups": sd / np.sqrt(n_eval_groups),
                                   "practical_target": 0.02,
                                   "note": "planning only, from calibration; the evaluation size is fixed"}}


def _contrast(rows, a, b, reps=REPS, seed=SEED, by="stratum"):
    """Stratum-weighted mean of world Brier(a) - Brier(b) with a source-group cluster bootstrap + bounds."""
    groups = sorted({r["group"] for r in rows})
    gidx = {g: i for i, g in enumerate(groups)}
    pa = [_world_brier(r["cell"]["queries"], r["outcomes"], a) for r in rows]
    pb = [_world_brier(r["cell"]["queries"], r["outcomes"], b) for r in rows]
    strata = [r[by] for r in rows]
    gw = defaultdict(list)
    for i, r in enumerate(rows):
        gw[gidx[r["group"]]].append(i)
    complete = all(not np.isnan(x[0]) for x in pa + pb)
    d = np.array([x[0] - y[0] for x, y in zip(pa, pb)])
    worst_lo = np.array([x[1] - y[2] for x, y in zip(pa, pb)])     # most favourable to b
    worst_hi = np.array([x[2] - y[1] for x, y in zip(pa, pb)])

    def est(vals, idx_groups):
        ws = [w for g in idx_groups for w in gw[g]]
        st = [strata[w] for w in ws]
        return _strat_mean([vals[w] for w in ws], st)
    out = {"a": a, "b": b, "n_worlds": len(rows), "n_groups": len(groups),
           "complete_predictions": complete, "worst_case_bounds": [est(worst_lo, range(len(groups))),
                                                                  est(worst_hi, range(len(groups)))]}
    if complete:
        bs = cluster_bootstrap(lambda ix: est(d, ix), len(groups), replicates=reps, seed=seed)
        out.update(estimate=bs["estimate"], ci95=bs["ci95"], se=bs["se"])
    else:
        out.update(estimate=None, ci95=None, note="incomplete predictions: report bounds only")
    return out


def analyze_g(eval_run, champion: str, budgets=("8", "16", "24"), reps=REPS) -> dict:
    out = {"champion": champion, "primary": None, "budgets": {}, "per_stratum": {}, "logical_strata": {}}
    for B in budgets:
        t = g_table(eval_run, B)
        rows = t["rows"]
        names = _names(rows)
        strata = [r["stratum"] for r in rows]
        cell = {"planned": t["planned"], "missing_items": t["missing_items"], "mean_brier": {}, "accuracy": {},
                "refusals": {}}
        for nm in names:
            wb = [_world_brier(r["cell"]["queries"], r["outcomes"], nm) for r in rows]
            if not any(np.isnan(x[0]) for x in wb):
                cell["mean_brier"][nm] = _strat_mean([x[0] for x in wb], strata)
            cell["refusals"][nm] = sum(1 for r in rows for q in r["cell"]["queries"]
                                       if q["predictions"][nm]["p"] is None)
            acc = []
            for r in rows:
                a = []
                for q in r["cell"]["queries"]:
                    p = q["predictions"][nm]["p"]
                    y = r["outcomes"][q["query_id"]]
                    a.append(np.nan if p is None else 0.5 if p == 0.5 else float((p > 0.5) == bool(y)))
                acc.append(np.nanmean(a) if not all(np.isnan(a)) else np.nan)
            if not any(np.isnan(acc)):
                cell["accuracy"][nm] = _strat_mean(acc, strata)
        cell["contrasts"] = {
            "primary_champion_minus_full_cgh": _contrast(rows, champion, "cgh_prior", reps),
            "hierarchy_ablation_cgh_flat_minus_cgh_prior": _contrast(rows, "cgh_flat", "cgh_prior", reps),
            "uniform_minus_full_cgh": _contrast(rows, "uniform", "cgh_prior", reps),
            "analytic_vocab_cgh_flat_noanalytic_minus_cgh_flat": _contrast(rows, "cgh_flat_noanalytic", "cgh_flat", reps),
            "shortest_cgh_prior_minus_full_cgh": _contrast(rows, "shortest_cgh_prior", "cgh_prior", reps),
        }
        out["budgets"][B] = cell
        if B == "16":
            out["primary"] = cell["contrasts"]["primary_champion_minus_full_cgh"]
            per = {}
            for s in sorted(set(strata)):
                sub = [r for r in rows if r["stratum"] == s]
                per[s] = {nm: float(np.mean([_world_brier(r["cell"]["queries"], r["outcomes"], nm)[0] for r in sub]))
                          for nm in names}
                per[s]["n_worlds"] = len(sub)
                d = [(_world_brier(r["cell"]["queries"], r["outcomes"], champion)[0] -
                      _world_brier(r["cell"]["queries"], r["outcomes"], "cgh_prior")[0]) for r in sub]
                per[s]["champion_minus_cgh_prior_mean"] = float(np.mean(d))
            out["per_stratum"] = per
            for lab in ("determined", "underdetermined"):
                vals = defaultdict(list)
                n = 0
                for r in rows:
                    for q in r["cell"]["queries"]:
                        if q["logical"] != lab:
                            continue
                        n += 1
                        y = r["outcomes"][q["query_id"]]
                        for nm in (champion, "cgh_prior", "cgh_flat", "uniform"):
                            p = q["predictions"][nm]["p"]
                            vals[nm].append(np.nan if p is None else (p - y) ** 2)
                out["logical_strata"][lab] = {"queries": n, **{nm: float(np.nanmean(v)) if v else None
                                                               for nm, v in vals.items()}}
            bins = np.linspace(0, 1, 11)
            rel = {}
            for nm in (champion, "cgh_prior", "uniform"):
                ps, ys = [], []
                for r in rows:
                    for q in r["cell"]["queries"]:
                        p = q["predictions"][nm]["p"]
                        if p is not None and q["logical"] == "underdetermined":
                            ps.append(p)
                            ys.append(r["outcomes"][q["query_id"]])
                ps, ys = np.array(ps), np.array(ys)
                idx = np.clip(np.digitize(ps, bins) - 1, 0, 9)
                rel[nm] = [{"bin": [float(bins[i]), float(bins[i + 1])], "n": int((idx == i).sum()),
                            "mean_p": float(ps[idx == i].mean()) if (idx == i).any() else None,
                            "freq": float(ys[idx == i].mean()) if (idx == i).any() else None} for i in range(10)]
            out["reliability_underdetermined_B16"] = rel
            costs = defaultdict(float)
            for r in rows:
                for k, v in r["cell"]["cost_s"].items():
                    costs[k] += v
            out["cost_s_total_B16"] = dict(costs)
            out["struct_refusals_B16"] = sum(1 for r in rows if "None" in str(r["cell"]["struct_status"].get("cgh_prior")))
    return out


def analyze_g_external(run_dir, champion: str, reps=REPS) -> dict:
    t = g_table(run_dir, "16")
    rows = t["rows"]
    for r in rows:
        r["stratum"] = "external"
    groups = sorted({r["group"] for r in rows})
    out = {"planned": t["planned"], "missing_items": t["missing_items"], "n_instances": len(rows),
           "n_groups": len(groups), "names": _names(rows)}
    if not rows:
        return out
    gm = {}
    for g in groups:
        sub = [r for r in rows if r["group"] == g]
        gm[g] = {nm: float(np.mean([_world_brier(r["cell"]["queries"], r["outcomes"], nm)[0] for r in sub]))
                 for nm in (champion, "cgh_prior", "cgh_flat", "uniform")}
    out["group_means"] = gm
    diffs = [gm[g][champion] - gm[g]["cgh_prior"] for g in groups]
    out["group_diff_champion_minus_cgh_prior"] = {"mean": float(np.mean(diffs)), "min": float(np.min(diffs)),
                                                   "max": float(np.max(diffs))}
    out["leave_one_source_out"] = [float(np.mean([d for j, d in enumerate(diffs) if j != i])) for i in range(len(diffs))] \
        if len(diffs) > 1 else []
    if len(groups) >= 10:
        out["primary_like"] = _contrast(rows, champion, "cgh_prior", reps)
        out["hierarchy_ablation"] = _contrast(rows, "cgh_flat", "cgh_prior", reps)
        out["uniform_minus_cgh"] = _contrast(rows, "uniform", "cgh_prior", reps)
    else:
        out["note"] = "fewer than 10 source groups: descriptive range and leave-one-source-out only"
    return out


def analyze_g_r6(run_dir, champion: str, method: str, external: bool = False, budgets=("8", "16", "24"),
                 reps=REPS) -> dict:
    """R6: dictionary-sharing prior ``method`` (default xdc[cgh_flat]) against the R5-locked generic champion.
    Primary: Brier(champion) - Brier(method) at B = 16 (positive favours the method); same estimator, clustering
    and missingness bounds as the R5 primary (``_contrast``).  Attribution contrasts are prespecified:
    sharing = flat base - method; vocabulary = xdc[gate] - method.  ``external``: one population, source-group
    clusters.  Dose-response uses the evaluator-side hidden rule reuse (n - distinct order-free rule types)."""
    base = method[method.index("[") + 1:method.index("]")]
    out = {"champion": champion, "method": method, "base": base, "external": external, "budgets": {}}
    for B in budgets:
        t = g_table(run_dir, B)
        rows = t["rows"]
        if external:
            for r in rows:
                r["stratum"] = "external"
        names = _names(rows)
        strata = [r["stratum"] for r in rows]
        cell = {"planned": t["planned"], "missing_items": t["missing_items"], "n_worlds": len(rows),
                "n_groups": len({r["group"] for r in rows}), "mean_brier": {}}
        wb = {nm: [_world_brier(r["cell"]["queries"], r["outcomes"], nm)[0] for r in rows] for nm in names}
        for nm in names:
            if not any(np.isnan(x) for x in wb[nm]):
                cell["mean_brier"][nm] = _strat_mean(wb[nm], strata)
        cell["contrasts"] = {
            "primary_champion_minus_method": _contrast(rows, champion, method, reps),
            "sharing_flat_base_minus_method": _contrast(rows, base, method, reps),
            "vocabulary_xdc_gate_minus_method": _contrast(rows, "xdc[gate]", method, reps),
            "generic_sharing_gate_minus_xdc_gate": _contrast(rows, "gate", "xdc[gate]", reps),
            "uniform_minus_method": _contrast(rows, "uniform", method, reps),
            "gsr_a50_minus_method": _contrast(rows, "gsr_a50", method, reps),
        }
        d = np.array(wb[champion]) - np.array(wb[method])
        cell["world_sign_counts"] = {"method_better": int((d > 1e-12).sum()), "champion_better": int((d < -1e-12).sum()),
                                     "equal": int((np.abs(d) <= 1e-12).sum())}
        cell["world_diff_quantiles"] = {str(q): float(np.quantile(d, q)) for q in (0, 0.05, 0.25, 0.5, 0.75, 0.95, 1)}
        per = {}
        for s in sorted(set(strata)):
            ix = [i for i, x in enumerate(strata) if x == s]
            per[s] = {"n_worlds": len(ix), **{nm: float(np.mean([wb[nm][i] for i in ix]))
                                              for nm in (champion, method, base, "xdc[gate]", "uniform", "gsr_a50")},
                      "champion_minus_method": float(np.mean(d[ix]))}
        cell["per_stratum"] = per
        out["budgets"][B] = cell
    # dose-response at the primary budget (identity carries hidden_rule_reuse, evaluator side)
    res = _ok(_load(run_dir))[0]
    t = g_table(run_dir, "16")
    by = defaultdict(list)
    for r in t["rows"]:
        k = res[r["item"]]["identity"].get("hidden_rule_reuse")
        dv = (_world_brier(r["cell"]["queries"], r["outcomes"], champion)[0] -
              _world_brier(r["cell"]["queries"], r["outcomes"], method)[0])
        by["unknown" if k is None else str(min(k, 6)) + ("+" if k is not None and k >= 6 else "")].append(dv)
    out["budgets"]["16"]["by_hidden_rule_reuse"] = {k: {"n_worlds": len(v), "champion_minus_method": float(np.mean(v))}
                                                    for k, v in sorted(by.items())}
    out["primary"] = out["budgets"]["16"]["contrasts"]["primary_champion_minus_method"]
    return out


REUSE_BY_CONSTRUCTION = ("template_exceptions", "imperfect_modules", "shared_motifs", "rewired_control")


def analyze_g_r6_extras(run_dir, champion: str, method: str, external: bool = False, budget: str = "16",
                        reps=REPS) -> dict:
    """R6 supplementary reporting required by the R6 assignment (NOT in the design lock; labelled post hoc):
    the primary contrast without the two strata richest in hidden rule reuse (ranked by mean reuse on this run),
    without all four reuse-by-construction strata, the reuse distribution per stratum, per-world difference
    quantiles with a cluster-bootstrap interval for the median, and the reliability of both predictors on
    underdetermined queries (the R5 'uniform' prediction strictly inside (0, 1), i.e. V(D) does not fix the answer)."""
    res = _ok(_load(run_dir))[0]
    t = g_table(run_dir, budget)
    rows = t["rows"]
    if not rows:
        raise ValueError("no completed worlds")
    for r in rows:
        r["reuse"] = res[r["item"]]["identity"].get("hidden_rule_reuse")
        if external:
            r["stratum"] = "external"
    strata = sorted({r["stratum"] for r in rows})
    reuse = {s: [r["reuse"] for r in rows if r["stratum"] == s] for s in strata}
    out = {"label": "post hoc supplementary (not locked)", "budget": budget, "n_worlds": len(rows),
           "n_groups": len({r["group"] for r in rows}),
           "reuse_by_stratum": {s: {"mean": float(np.mean(v)), "min": int(min(v)), "max": int(max(v)),
                                    "share_ge_6": float(np.mean([x >= 6 for x in v]))} for s, v in reuse.items()}}
    d = np.array([_world_brier(r["cell"]["queries"], r["outcomes"], champion)[0] -
                  _world_brier(r["cell"]["queries"], r["outcomes"], method)[0] for r in rows])
    groups = sorted({r["group"] for r in rows})
    gw = defaultdict(list)
    for i, r in enumerate(rows):
        gw[groups.index(r["group"])].append(i)
    med = cluster_bootstrap(lambda ix: float(np.median(d[[w for g in ix for w in gw[g]]])), len(groups),
                            replicates=min(reps, 2000), seed=SEED)
    out["world_diff"] = {"n": int(d.size), "mean_unweighted": float(d.mean()),
                         "median": med["estimate"], "median_ci95": med["ci95"],
                         "quartiles": [float(np.quantile(d, 0.25)), float(np.quantile(d, 0.75))],
                         "share_method_better": float((d > 1e-12).mean()),
                         "share_champion_better": float((d < -1e-12).mean()),
                         "share_of_total_gain_from_top_10pct_worlds":
                             float(np.sort(d)[::-1][:max(1, d.size // 10)].sum() / d.sum()) if d.sum() > 0 else None}
    if not external:
        top2 = sorted(strata, key=lambda s: (-np.mean(reuse[s]), s))[:2]
        keep = [r for r in rows if r["stratum"] not in top2]
        keep4 = [r for r in rows if r["stratum"] not in REUSE_BY_CONSTRUCTION]
        out["without_top2_reuse_strata"] = {"dropped": top2, **_contrast(keep, champion, method, reps)}
        out["without_reuse_by_construction_strata"] = {"dropped": list(REUSE_BY_CONSTRUCTION),
                                                       **_contrast(keep4, champion, method, reps)}
        out["only_reuse_by_construction_strata"] = _contrast(
            [r for r in rows if r["stratum"] in REUSE_BY_CONSTRUCTION], champion, method, reps)
    bins = np.linspace(0, 1, 11)
    rel = {}
    for nm in (champion, method):
        ps, ys = [], []
        for r in rows:
            for q in r["cell"]["queries"]:
                u = q["predictions"].get("uniform")
                pr = q["predictions"].get(nm)
                if u is None or u["p"] is None or not (0 < u["p"] < 1) or pr is None or pr["p"] is None:
                    continue
                ps.append(pr["p"])
                ys.append(r["outcomes"][q["query_id"]])
        ps, ys = np.array(ps), np.array(ys, dtype=float)
        if ps.size == 0:
            rel[nm] = {"n_queries": 0}
            continue
        ix = np.clip(np.digitize(ps, bins) - 1, 0, 9)
        table = [{"bin": [float(bins[b]), float(bins[b + 1])], "n": int((ix == b).sum()),
                  "mean_p": float(ps[ix == b].mean()), "freq": float(ys[ix == b].mean())}
                 for b in range(10) if (ix == b).any()]
        rel[nm] = {"n_queries": int(ps.size), "brier": float(((ps - ys) ** 2).mean()),
                   "ece": float(sum(c["n"] * abs(c["mean_p"] - c["freq"]) for c in table) / ps.size),
                   "mean_p": float(ps.mean()), "base_rate": float(ys.mean()), "bins": table}
    out["reliability_underdetermined"] = rel
    return out


# =========================================================================== M

def analyze_m(run_dir) -> dict:
    from ..r5.misspec import POLICIES
    lr = _load(run_dir)
    res, missing = _ok(lr)
    out = {"planned": len(lr["plan"]["items"]), "missing_items": missing, "panels": {}}
    by = defaultdict(list)
    for r in res.values():
        by[r["panel"]].append(r)
    for pan, rows in sorted(by.items()):
        cell = {"worlds": len(rows), "queries": 8 * len(rows), "declared_consistent": sum(r["declared_consistent"] for r in rows)}
        for pol in POLICIES:
            keys = ("released", "false_verified", "correct_release", "unnecessary_block", "false_uncertainty",
                    "measurements", "class_changes")
            tot = {k: sum(r["score"][pol][k] for r in rows) for k in keys}
            q = 8 * len(rows)
            fv = np.array([r["score"][pol]["false_verified"] / 8 for r in rows])
            ci = cluster_bootstrap(lambda ix: float(fv[ix].mean()), len(rows), replicates=4000, seed=SEED)["ci95"] \
                if len(rows) > 1 else None
            cell[pol] = {**tot, "coverage_correct_release": tot["correct_release"] / q,
                         "false_verified_rate": tot["false_verified"] / q, "false_verified_ci95": ci,
                         "false_verified_given_release": tot["false_verified"] / tot["released"] if tot["released"] else None,
                         "worlds_with_false_verified": sum(1 for r in rows if r["score"][pol]["false_verified"]),
                         "cost_s": sum(r["score"][pol]["cost_s"] for r in rows)}
        out["panels"][pan] = cell
    return out


# =========================================================================== A

def analyze_a_det(run_dir) -> dict:
    lr = _load(run_dir)
    res, missing = _ok(lr)
    curves = defaultdict(lambda: defaultdict(list))
    agree_backend = {"pairs": 0, "identical_purchases_and_verdicts": 0}
    for r in res.values():
        if r.get("excluded"):
            continue
        eps = {(e["policy"], e["backend"]): e for e in r["episodes"]}
        for (pol, be), e in eps.items():
            for b, c in e["curve"].items():
                curves[f"{pol}|{be}"][b].append(int(c["verdict"] in ("entailed", "refuted")))
        for pol in ("random", "eig", "disagreement"):
            a, b = eps.get((pol, "D")), eps.get((pol, "B"))
            if a and b:
                agree_backend["pairs"] += 1
                same = [s["purchased"] for s in a["steps"]] == [s["purchased"] for s in b["steps"]] and \
                    {k: v["verdict"] for k, v in a["curve"].items()} == {k: v["verdict"] for k, v in b["curve"].items()}
                agree_backend["identical_purchases_and_verdicts"] += same
    tab = {k: {b: float(np.mean(v)) for b, v in d.items()} for k, d in curves.items()}
    return {"planned": len(lr["plan"]["items"]), "missing_items": missing,
            "worlds": sum(1 for r in res.values() if not r.get("excluded")), "resolved_curves": tab,
            "backend_replay": agree_backend}


def select_det_policy(cal_det_run) -> dict:
    a = analyze_a_det(cal_det_run)
    order = ("eig", "disagreement", "random")
    sc = {p: a["resolved_curves"][f"{p}|D"]["4"] for p in order}
    best = max(order, key=lambda p: (sc[p], -order.index(p)))
    return {"resolved_at_4_on_calibration": sc, "selected": best, "tie_order": list(order),
            "calibration_worlds": a["worlds"]}


def analyze_a_ai(ai_runs: list, det_run, selected: str, reps=REPS) -> dict:
    det = _load(det_run)["results"]
    out = {"selected_policy": selected, "models": {}}
    for run in ai_runs:
        lr = _load(run)
        res, missing = _ok(lr)
        model = lr["plan"]["config"]["provider"]["model"]
        m = {"planned": len(lr["plan"]["items"]), "missing_items": missing, "arms": {}}
        for arm in ("D", "B"):
            rows = []
            for iid, r in res.items():
                if r.get("excluded") or arm not in r["episodes"]:
                    continue
                e = r["episodes"][arm]
                d = det.get(iid)
                dep = next(x for x in d["episodes"] if x["policy"] == selected and x["backend"] == "D")
                res_b = {b: int(e["gate"].get(b, {}).get("check") == "verified") for b in ("0", "1", "2", "4")}
                det_b = {b: int(dep["curve"][b]["verdict"] in ("entailed", "refuted")) for b in ("0", "1", "2", "4")}
                wrong_def = sum(1 for g in e["gate"].values() if g["asserted"] in ("entailed", "refuted")
                                and g["check"] != "verified")
                false_unc = sum(1 for b, g in e["gate"].items() if g["asserted"] == "underdetermined"
                                and e["per_turn"][b]["readout_status"] in ("entailed", "refuted"))
                pt = e["per_turn"].get("4", {}).get("p_target")
                rows.append({"res": res_b, "det": det_b, "wrong_definite": wrong_def, "false_uncertainty": false_unc,
                             "invalid": len(e["invalid"]), "attempts": e["n_attempts"], "status": e["status"],
                             "copied_eig": sum(p["menu_index"] == p["eig_argmax"] for p in e["purchases"]),
                             "purchases": len(e["purchases"]), "latency": e["server_latency_s"], "tokens": e["tokens"],
                             "brier_final": None if pt is None else (pt - r["truth"]) ** 2,
                             "brier_readout": (e["per_turn"].get("4", {}).get("readout_p", np.nan) - r["truth"]) ** 2
                             if e["per_turn"].get("4", {}).get("readout_p") is not None else None})
            if not rows:
                continue
            diff = np.array([x["res"]["4"] - x["det"]["4"] for x in rows], float)
            bs = cluster_bootstrap(lambda ix: float(diff[ix].mean()), len(rows), replicates=reps, seed=SEED)
            m["arms"][arm] = {
                "worlds": len(rows), "primary_resolved4_ai_minus_selected": bs,
                "ai_resolved_curve": {b: float(np.mean([x["res"][b] for x in rows])) for b in ("0", "1", "2", "4")},
                "selected_policy_curve": {b: float(np.mean([x["det"][b] for x in rows])) for b in ("0", "1", "2", "4")},
                "wrong_definite_verdicts": sum(x["wrong_definite"] for x in rows),
                "false_uncertainty_turns": sum(x["false_uncertainty"] for x in rows),
                "invalid_actions": sum(x["invalid"] for x in rows), "attempts": sum(x["attempts"] for x in rows),
                "valid_action_rate": 1 - sum(x["invalid"] for x in rows) / max(1, sum(x["attempts"] for x in rows)),
                "status": dict(__import__("collections").Counter(x["status"] for x in rows)),
                "purchases_copying_eig_argmax": [sum(x["copied_eig"] for x in rows), sum(x["purchases"] for x in rows)],
                "mean_brier_final_ai": float(np.mean([x["brier_final"] for x in rows if x["brier_final"] is not None]))
                if any(x["brier_final"] is not None for x in rows) else None,
                "mean_brier_readout": float(np.mean([x["brier_readout"] for x in rows if x["brier_readout"] is not None]))
                if any(x["brier_readout"] is not None for x in rows) else None,
                "server_latency_s": sum(x["latency"] for x in rows), "tokens": sum(x["tokens"] for x in rows)}
        if "D" in m["arms"] and "B" in m["arms"]:
            dd = []
            for r in res.values():
                if r.get("excluded"):
                    continue
                g = {a: int(r["episodes"][a]["gate"].get("4", {}).get("check") == "verified") for a in ("D", "B")}
                dd.append(g["D"] - g["B"])
            dd = np.array(dd, float)
            m["secondary_D_minus_generic_resolved4"] = cluster_bootstrap(lambda ix: float(dd[ix].mean()), len(dd),
                                                                         replicates=reps, seed=SEED)
        out["models"][model] = m
    return out


# =========================================================================== C

def analyze_c(run_dir) -> dict:
    lr = _load(run_dir)
    res, missing = _ok(lr)
    by = defaultdict(list)
    for r in res.values():
        by[(r["n"], r["backend"])].append(r)
    agree = {"compared": 0, "mismatch": 0}
    inst = defaultdict(dict)
    for r in res.values():
        if r["rep"] != 0:
            continue
        cnt = {e["info"]["i"]: (e["info"].get("num"), e["info"].get("den"))
               for e in r["workspace"]["events"] if e.get("kind") == "q" and e.get("info")}
        inst[(r["n"], r["base"])][r["backend"]] = cnt
    for d in inst.values():
        for i in range(16):
            vals = {b: d[b].get(i) for b in d if d[b].get(i) and d[b][i][0] is not None}
            if len(vals) >= 2:
                agree["compared"] += 1
                agree["mismatch"] += len(set(vals.values())) > 1
    table = {}
    for (n, be), rows in sorted(by.items()):
        r0 = [r for r in rows if r["rep"] == 0]
        ws = [r["workspace"] for r in r0]
        cell = {"items": len(r0), "status": dict(__import__("collections").Counter(w["status"] for w in ws)),
                "queries_done_by_checkpoint": {c: int(sum(w["checkpoints"][c] for w in ws)) for c in ("1", "10", "60", "300")},
                "queries_planned": 16 * len(r0),
                "median_build_s": float(np.median([w["build_s"] for w in ws if w["build_s"] is not None]))
                if any(w["build_s"] is not None for w in ws) else None,
                "median_reuse_s": {m: (float(np.median([r["reuse_s"][m] for r in r0 if r["reuse_s"][m] is not None]))
                                       if any(r["reuse_s"][m] is not None for r in r0) else None) for m in ("1", "4", "16")},
                "max_peak_rss_bytes": max((w["peak_rss_bytes"] or 0) for w in ws) if ws else None,
                "by_kind": {k: {"done": sum(1 for r in r0 if r["kind"] == k and r["workspace"]["status"] == "done"),
                                "items": sum(1 for r in r0 if r["kind"] == k)} for k in ("matched", "rewired")}}
        rel = [r["release"] for r in r0 if "release" in r]
        if rel:
            levels = defaultdict(int)
            for x in rel:
                for e in x["events"]:
                    for v in (e.get("info", {}).get("side_checks") or {}).values():
                        levels[v] += 1
            cell["release"] = {"status": dict(__import__("collections").Counter(x["status"] for x in rel)),
                               "queries_done_by_checkpoint": {c: int(sum(x["checkpoints"][c] for x in rel))
                                                              for c in ("1", "10", "60", "300")},
                               "queries_planned": 4 * len(rel),
                               "median_done_s": float(np.median([x["done_s"] for x in rel if x["done_s"] is not None]))
                               if any(x["done_s"] is not None for x in rel) else None,
                               "side_check_levels": dict(levels),
                               "max_peak_rss_bytes": max((x["peak_rss_bytes"] or 0) for x in rel)}
        reps = [r for r in rows if r["rep"] > 0]
        if reps:
            cell["repetitions"] = [{"base": r["base"], "rep": r["rep"], "build_s": r["workspace"]["build_s"],
                                    "done_s": r["workspace"]["done_s"]} for r in reps]
        table[f"n{n}|{be}"] = cell
    return {"planned": len(lr["plan"]["items"]), "missing_items": missing, "count_agreement": agree, "table": table}


def write(out_dir, name, obj):
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    (p / name).write_text(json.dumps(obj, indent=1, sort_keys=True, default=float) + "\n")


# =========================================================================== R6 Track S

S_FLAT_CANDIDATES = ("flat[gate]", "flat[cgh_flat]", "flat[circuit]", "flat[index]")      # fixed tie order


def _s_rows(run_dir, budget: str, panel: str | None = None, split: str | None = None) -> tuple[list, dict]:
    res = _ok(_load(run_dir))[0]
    t = g_table(run_dir, budget)
    rows = []
    for r in t["rows"]:
        ident = res[r["item"]]["identity"]
        if (panel and ident["panel"] != panel) or (split and ident["split"] != split) or r["cell"] is None:
            continue
        r.update(ident=ident, stratum=ident["panel"])
        rows.append(r)
    return rows, t


def _mean_brier(rows, name):
    vals = [_world_brier(r["cell"]["queries"], r["outcomes"], name)[0] for r in rows]
    return None if not vals or any(np.isnan(v) for v in vals) else float(np.mean(vals))


def analyze_s_calibration(run_dir, budgets=("4", "8", "16", "32", "64")) -> dict:
    """Track S calibration summary (calibration groups only): mean Brier of every predictor per panel and budget,
    fit certificates, cost and signature counts against n.  Used to choose budgets, the best flat code and the
    XDC-EB regulariser/fit mode BEFORE the Track S lock; never run on evaluation groups before the lock."""
    out = {"budgets": {}, "fits": {}, "cost": {}}
    res = _ok(_load(run_dir))[0]
    if any(r["identity"]["split"] != "calibration" for r in res.values()):
        raise ValueError("calibration analysis received a non-calibration world")
    for B in budgets:
        cell = {}
        for pan in sorted({r["identity"]["panel"] for r in res.values()}):
            rows, _ = _s_rows(run_dir, B, pan)
            if not rows:
                continue
            names = sorted({nm for r in rows for q in r["cell"]["queries"] for nm in q["predictions"]})
            cell[pan] = {"n_worlds": len(rows), "n_groups": len({r["group"] for r in rows}),
                         "mean_brier": {nm: _mean_brier(rows, nm) for nm in names}}
        out["budgets"][B] = cell
    gaps, iters, cert, cost = [], [], [], defaultdict(list)
    for r in res.values():
        for c in r["predictions"].values():
            for f in c.get("fits", {}).values():
                gaps.append(f["gap"])
                iters.append(f["iterations"])
                cert.append(f["certified"])
            cost[r["n"]].append(c["cost_s"].get("total", 0.0))
    out["fits"] = {"n_fits": len(gaps), "all_certified": all(cert), "max_gap": max(gaps) if gaps else None,
                   "max_iterations": max(iters) if iters else None}
    out["cost"] = {str(n): {"worlds_x_budgets": len(v), "median_s": float(np.median(v)), "max_s": float(max(v))}
                   for n, v in sorted(cost.items())}
    return out


def analyze_s(run_dir, flat: str, method: str, panel: str, budgets=("8", "16", "32"), primary_budget="16",
              reps=REPS) -> dict:
    """Track S evaluation: Brier(flat) - Brier(method) per budget on one panel (positive favours the method; with
    the method = XDC-EB over the same base this IS the sharing attribution),
    source-group cluster bootstrap and missingness bounds (``_contrast``); attribution and dose-response."""
    base = flat[flat.index("[") + 1:flat.index("]")]
    suffix = method[method.index("]") + 1:]
    out = {"flat": flat, "method": method, "panel": panel, "budgets": {}}
    for B in budgets:
        rows, t = _s_rows(run_dir, B, panel, "evaluation")
        if not rows:
            raise ValueError(f"no evaluation worlds for {panel} at B={B}")
        names = sorted({nm for r in rows for q in r["cell"]["queries"] for nm in q["predictions"]})
        cell = {"planned_items_in_run": t["planned"], "missing_items_in_run": t["missing_items"],
                "n_worlds": len(rows), "n_groups": len({r["group"] for r in rows}),
                "mean_brier": {nm: _mean_brier(rows, nm) for nm in names}}
        con = {"primary_flat_minus_method": _contrast(rows, flat, method, reps),
               "vocabulary_eb_gate_minus_eb_cgh_flat": _contrast(rows, f"xdc_eb[gate]{suffix}",
                                                                 f"xdc_eb[cgh_flat]{suffix}", reps),
               "uniform_minus_method": _contrast(rows, "flat[uniform]", method, reps)}
        if all(f"xdc[{base}]" in q["predictions"] for r in rows for q in r["cell"]["queries"]):
            con["exact_xdc_minus_method"] = _contrast(rows, f"xdc[{base}]", method, reps)
        unseen = [r for r in rows if not r["ident"].get("group_seen_in_n8")]
        if unseen and len(unseen) < len(rows):
            con["primary_without_groups_seen_in_n8"] = _contrast(unseen, flat, method, reps)
        cell["contrasts"] = con
        d = np.array([_world_brier(r["cell"]["queries"], r["outcomes"], flat)[0] -
                      _world_brier(r["cell"]["queries"], r["outcomes"], method)[0] for r in rows])
        cell["world_diff"] = {"median": float(np.median(d)), "quartiles": [float(np.quantile(d, .25)),
                                                                           float(np.quantile(d, .75))],
                              "share_method_better": float((d > 1e-12).mean()),
                              "share_flat_better": float((d < -1e-12).mean())}
        by = {"n": defaultdict(list), "reuse_nonconstant": defaultdict(list), "clamped_edge_fraction": defaultdict(list)}
        for r, dv in zip(rows, d):
            i = r["ident"]
            by["n"][str(i["n"])].append(dv)
            by["reuse_nonconstant"][str(min(i["reuse_nonconstant"], 12)) + ("+" if i["reuse_nonconstant"] >= 12 else "")].append(dv)
            cf = i.get("clamped_edge_fraction") or 0.0
            by["clamped_edge_fraction"]["<0.1" if cf < .1 else "0.1-0.3" if cf < .3 else ">=0.3"].append(dv)
        cell["by"] = {k: {kk: {"n_worlds": len(vv), "mean": float(np.mean(vv))} for kk, vv in sorted(v.items())}
                      for k, v in by.items()}
        x = np.array([r["ident"]["reuse_nonconstant"] / r["ident"]["n"] for r in rows])
        cell["corr_diff_vs_reuse_share"] = float(np.corrcoef(x, d)[0, 1]) if x.std() > 0 and d.std() > 0 else None
        if panel == "intact":
            nn = np.array([r["ident"]["n"] for r in rows], dtype=float)
            cell["corr_diff_vs_n"] = float(np.corrcoef(nn, d)[0, 1]) if nn.std() > 0 and d.std() > 0 else None
        out["budgets"][B] = cell
    out["primary"] = out["budgets"][primary_budget]["contrasts"]["primary_flat_minus_method"]
    return out
