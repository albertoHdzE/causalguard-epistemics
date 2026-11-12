"""R6 Track S: the cost of the XDC-EB approximation at n = 8 (calibration worlds only).

On the 64 R6 calibration worlds (design salt of r6-g-cal-v1, budgets 8/16/24, all 8 queries, h = 1 and 2) compare
exact XDC (theta mixture) with XDC-EB for every declared regulariser and fit mode, bases gate and cgh_flat.
Usage: scripts/r6_eb_vs_xdc.py OUT.json [workers]
"""
import json
import sys
from multiprocessing import Pool

import numpy as np

from causalguard.r5 import data as D
from causalguard.r5.priors import XDC, XDCEB
from causalguard.r6.scale import EB_A_GRID

SALT = "r6-G-design-cal-v1"
BASES = ("gate", "cgh_flat")


def world(arg):
    stratum, i = arg
    inst = D.make_instance("calibration", stratum, i)
    key = inst.identity()["mechanism_id"]
    design = D.make_design(SALT, key, inst.net.n)
    out = []
    for B in D.BUDGETS:
        ev = D.make_evidence(inst.net, design, B)
        for b in BASES:
            x = XDC(ev, D.K, base=b)
            if x.vs.empty:
                continue
            ebs = {f"a{a:g}|{'loo' if loo else 'full'}": XDCEB(ev, D.K, base=b, vs=x.vs, a=a, loo=loo)
                   for a in EB_A_GRID for loo in (False, True)}
            for _qid, q in design.queries:
                y = D.outcome(inst.net, q)
                row = {"stratum": stratum, "i": i, "B": B, "base": b, "h": q.horizon, "y": y,
                       "xdc": x.probabilities(q)["xdc"]}
                for k, m in ebs.items():
                    pr = m.probabilities(q)
                    row[k] = pr["xdc_eb"]
                    row["gap_" + k] = pr["fit_gap"]
                out.append(row)
    return out


def main(out_path, workers=4):
    items = [(s, i) for s in D.STRATA for i in range(D.SPLITS["calibration"]["per_stratum"])]
    with Pool(workers) as pool:
        rows = [r for w in pool.map(world, items) for r in w]
    keys = [f"a{a:g}|{m}" for a in EB_A_GRID for m in ("full", "loo")]
    summ = {}
    for b in BASES:
        for B in D.BUDGETS:
            R = [r for r in rows if r["base"] == b and r["B"] == B]
            y = np.array([r["y"] for r in R], float)
            px = np.array([r["xdc"] for r in R])
            cell = {"n_queries": len(R), "brier_xdc": float(((px - y) ** 2).mean())}
            for k in keys:
                pe = np.array([r[k] for r in R])
                cell[k] = {"brier": float(((pe - y) ** 2).mean()),
                           "brier_minus_xdc": float(((pe - y) ** 2).mean() - ((px - y) ** 2).mean()),
                           "mean_abs_p_diff": float(np.abs(pe - px).mean()),
                           "max_abs_p_diff": float(np.abs(pe - px).max()),
                           "max_fit_gap": float(max(r["gap_" + k] for r in R))}
            summ[f"{b}|B{B}"] = cell
    json.dump({"worlds": len(items), "design_salt": SALT, "summary": summ}, open(out_path, "w"), indent=1,
              sort_keys=True)
    print(json.dumps({k: {"xdc": round(v["brier_xdc"], 4), **{kk: round(v[kk]["brier_minus_xdc"], 4) for kk in keys}}
                      for k, v in summ.items()}, indent=0))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4)
