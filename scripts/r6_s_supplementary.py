"""R6 Track S supplementary analysis (written AFTER the evaluation; labelled post hoc in R6_SCALE.md).

The locked analysis builds the exact-XDC contrast only for the method's base (circuit), but exact XDC was computed
only for the gate and cgh_flat bases (n <= 12, panel sub12).  This reports, on sub12, the gap between XDC-EB and
exact XDC on the same base, plus fit certificates and cost over the whole evaluation run.  It changes no locked number.
Usage: scripts/r6_s_supplementary.py RUN_DIR OUT.json
"""
import json
import sys
from collections import defaultdict

import numpy as np

from causalguard.analysis.r5_analysis import REPS, _contrast, _load, _ok, _s_rows

SUFFIX = "|a16|loo"
BASES = ("cgh_flat", "gate")


def main(run_dir, out_path):
    out = {"panel": "sub12", "post_hoc": True, "budgets": {}}
    for B in ("4", "8", "16"):
        rows, _ = _s_rows(run_dir, B, "sub12")
        cell = {}
        for b in BASES:
            eb, ex, fl = f"xdc_eb[{b}]{SUFFIX}", f"xdc[{b}]", f"flat[{b}]"
            cell[b] = {"flat_minus_exact_xdc": _contrast(rows, fl, ex, REPS),
                       "flat_minus_xdc_eb": _contrast(rows, fl, eb, REPS),
                       "xdc_eb_minus_exact_xdc": _contrast(rows, eb, ex, REPS)}
        cell["flat_circuit_minus_exact_xdc_gate"] = _contrast(rows, "flat[circuit]", "xdc[gate]", REPS)
        out["budgets"][B] = cell
    res = _ok(_load(run_dir))[0]
    gaps, cert, cost = [], [], defaultdict(list)
    for r in res.values():
        for c in r["predictions"].values():
            for f in c.get("fits", {}).values():
                gaps.append(f["gap"])
                cert.append(f["certified"])
            cost[r["n"]].append(c["cost_s"].get("total", 0.0))
    out["fits"] = {"n_fits": len(gaps), "all_certified": all(cert), "max_gap": max(gaps)}
    out["cost"] = {str(n): {"worlds_x_budgets": len(v), "median_s": float(np.median(v)), "max_s": float(max(v))}
                   for n, v in sorted(cost.items())}
    json.dump(out, open(out_path, "w"), indent=1, sort_keys=True, default=float)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
