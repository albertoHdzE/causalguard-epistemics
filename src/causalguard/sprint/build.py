"""R7 sprint build steps (no model calls): manifests, the surface rule fit, and the engine-agreement check.

  python -m causalguard sprint-build manifests            -> artifacts/sprint_{smoke,pilot,main}_manifest.json
  python -m causalguard sprint-build surface              -> artifacts/sprint_surface_rule.json (train split only)
  python -m causalguard sprint-build engines --split S    -> exact engine agreement on every claim of a split
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from . import population as P
from . import surface

ART = P.REPO / "artifacts"


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n")


def manifests(splits=("smoke", "pilot", "main")) -> dict:
    out = {}
    for s in splits:
        m = P.manifest(s)
        write_json(ART / f"sprint_{s}_manifest.json", m)
        out[s] = m
        cond = Counter(x["condition"] for x in m["items"])
        print(f"manifest {s}: {m['n_worlds']} worlds, conditions {dict(sorted(cond.items()))}")
    return out


def engines(split: str, quiet: bool = True) -> dict:
    """Every claim of every world of the split through ``Evaluator.reference`` (explicit = D counts and the SAT
    verdict); an exception on any claim is a failed item.  Prints the denominator."""
    keys = P.world_keys(split)
    if not keys:
        raise SystemExit("engines: empty split")
    ok = fail = claims = 0
    st = Counter()
    failures = []
    for k in keys:
        try:
            ref = P.reference(P.evaluator(k))
            ok += 1
            claims += len(ref)
            st.update(r["status"] for r in ref.values())
        except AssertionError as e:
            fail += 1
            failures.append({"wkey": k.wkey, "error": str(e)[:200]})
    res = {"split": split, "worlds": len(keys), "worlds_agree": ok, "worlds_fail": fail, "claims_agree": claims,
           "status_counts": dict(st), "failures": failures}
    print(f"engines {split}: {ok}/{len(keys)} worlds agree ({claims} claims); status {dict(st)}")
    return res


def fit_surface() -> dict:
    keys = P.world_keys("train")
    items = []
    for k in keys:
        ev = P.evaluator(k)
        items.append((ev.public(), P.reference(ev, crosscheck_sat=False)))
    rule = surface.fit(items)
    write_json(ART / "sprint_surface_rule.json", rule)
    print(f"surface rule fitted on {len(items)} train worlds, {rule['train_claims']} claims; "
          f"base rates {rule['base_rates']}; sha256 {rule['sha256'][:12]}")
    return rule


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="causalguard sprint-build")
    ap.add_argument("step", choices=("manifests", "surface", "engines"))
    ap.add_argument("--split", default="main")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    if a.step == "manifests":
        manifests()
    elif a.step == "surface":
        fit_surface()
    else:
        r = engines(a.split)
        if a.out:
            write_json(Path(a.out), r)
        return 0 if r["worlds_fail"] == 0 and r["worlds_agree"] > 0 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
