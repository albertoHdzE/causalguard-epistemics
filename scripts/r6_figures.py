#!/usr/bin/env python
"""R6 figures: the objects behind the G contrasts (per-world Brier differences, theta posteriors).

  scripts/r6_figures.py <run_dir> <champion> <method> <out.png> [--external]

Left: every world's Brier(champion) - Brier(method) at B = 16, by stratum (or by source group for external
panels), with stratum means.  Right: the posterior weight of each theta component of the method in every world
(the only 'knob'; it is averaged over, not fitted) -- a world at theta = inf is using no sharing.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from causalguard.analysis.r5_analysis import _world_brier, g_table

run, champion, method, out = sys.argv[1:5]
external = "--external" in sys.argv
base = method[method.index("[") + 1:method.index("]")]
rows = g_table(Path(run), "16")["rows"]
if not rows:
    raise SystemExit("no rows loaded: refusing to draw an empty figure")
lab = [("external" if external else r["stratum"]) for r in rows]
d = np.array([_world_brier(r["cell"]["queries"], r["outcomes"], champion)[0] -
              _world_brier(r["cell"]["queries"], r["outcomes"], method)[0] for r in rows])
post = np.array([[np.mean([q["xdc_theta_posterior"][base][k] for q in r["cell"]["queries"]])
                  for k in sorted(r["cell"]["queries"][0]["xdc_theta_posterior"][base])] for r in rows])
tn = sorted(rows[0]["cell"]["queries"][0]["xdc_theta_posterior"][base])
fig, ax = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [2, 1]})
rng = np.random.default_rng(0)
labs = sorted(set(lab))
for i, s in enumerate(labs):
    v = d[[x == s for x in lab]]
    ax[0].scatter(i + rng.uniform(-0.3, 0.3, len(v)), v, s=9, alpha=0.55, color="#3b6ea5")
    ax[0].hlines(v.mean(), i - 0.4, i + 0.4, color="#c0392b", lw=2)
    ax[0].text(i, ax[0].get_ylim()[1], f"n={len(v)}", ha="center", va="bottom", fontsize=7)
ax[0].axhline(0, color="k", lw=0.8)
ax[0].set_xticks(range(len(labs)), labs, rotation=25, ha="right", fontsize=8)
ax[0].set_ylabel(f"world Brier({champion}) − Brier({method}), B = 16   (>0: method better)")
ax[0].set_title(f"{Path(run).name}: every world ({len(d)}); red = mean")
parts = ax[1].violinplot([post[:, j] for j in range(len(tn))], showmedians=True)
ax[1].set_xticks(range(1, len(tn) + 1), [t.replace("xdc_t", "θ=") for t in tn])
ax[1].set_ylabel("posterior weight of the θ component (per world)")
ax[1].set_title("sharing strength inferred per world")
fig.tight_layout()
fig.savefig(out, dpi=130)
print(f"wrote {out}: worlds {len(d)}, mean diff {d.mean():+.4f}, theta weights mean {dict(zip(tn, post.mean(0).round(3)))}")
