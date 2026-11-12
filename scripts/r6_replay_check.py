"""R6 replay check: recompute stored items of earlier runs with the CURRENT code and compare outputs exactly.

Wall-clock fields (any key named ``cost_s``, ``seconds``, ``build_s``, ``done_s``, ``wall_s``) are removed before
comparison.  ``predictions_sha256`` is a digest OVER the predictions including their ``cost_s`` timings, so it differs
on every rerun by construction; it is excluded from the comparison and instead checked against the stored predictions
it digests (integrity).  Everything else (probabilities, identities, outcomes) must match as canonical JSON.  Items are a deterministic
sample: every ``stride``-th planned item.  Usage: scripts/r6_replay_check.py OUT.json STRIDE RUN_DIR ...
"""
import hashlib
import json
import sys
from multiprocessing import Pool
from pathlib import Path

from causalguard.__main__ import _fn_for

WALL = {"cost_s", "seconds", "build_s", "done_s", "wall_s", "predictions_sha256"}


def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if k not in WALL}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x


def check(arg):
    run, study, item_id, payload, stored = arg
    new = _fn_for(study)(payload)
    a = json.dumps(strip(stored), sort_keys=True, default=float)
    b = json.dumps(strip(json.loads(json.dumps(new, default=float))), sort_keys=True, default=float)
    ok_digest = ("predictions_sha256" not in stored or stored["predictions_sha256"]
                 == hashlib.sha256(json.dumps(stored["predictions"], sort_keys=True).encode()).hexdigest())
    return run, item_id, a == b and ok_digest


def jobs(run_dir, stride):
    plan = json.loads((Path(run_dir) / "plan.json").read_text())
    stored = {}
    for f in sorted((Path(run_dir) / "attempts").glob("*/*.json")):
        a = json.loads(f.read_text())
        if a.get("status") == "ok":
            stored[a["item_id"]] = a["output"]
    for it in plan["items"][::stride]:
        if it["item_id"] in stored:
            yield Path(run_dir).name, plan["study"], it["item_id"], it["payload"], stored[it["item_id"]]


def main(out, stride, runs):
    todo = [j for r in runs for j in jobs(r, stride)]
    with Pool(4) as pool:
        res = pool.map(check, todo, chunksize=1)
    summ = {}
    for run, item, same in res:
        s = summ.setdefault(run, {"compared": 0, "identical": 0, "different": []})
        s["compared"] += 1
        s["identical"] += same
        if not same:
            s["different"].append(item)
    Path(out).write_text(json.dumps({"stride": stride, "runs": summ}, indent=1, sort_keys=True) + "\n")
    for run, s in summ.items():
        print(f"{run}: {s['identical']}/{s['compared']} identical")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3:])
