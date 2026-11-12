"""R7 sprint benchmark populations (pre-sprint): worlds, designs, exact reference, and the hash assignment.

World = a hidden mechanism in H(8, 3) + the S4 exogenous evidence/claim design (``s4.tasks.make_design``: budget
12/16/24 one-step observations, a quarter of them with a persistent clamp; eight claims on never-observed start
states, initial edit or persistent clamp of 1-2 nodes, horizon 1-3, asserted value drawn independently of the
mechanism).  This is the design the S4 unaided arm (``s4/pilot.py``, arm A) already renders.

Mechanisms come from two populations (DECISIONS D70):
  synthetic   the locked R5 G generators (``r5.data``; eight strata) on fresh R7 salts (splits ``sprint_*``)
  published   eight-node backward fragments of published Boolean models (``r5.external``, Biodivine pinned commit;
              the R5/R6 transformed panel).  No published fragment was ever shown to a model before R7.  Source
              groups are split between train / smoke / pilot / main by sha256 order of ('r7-sprint', group);
              one fragment per group, chosen by sha256 order.

The exact reference (status, p* = num/den, hidden truth) is the S4 evaluator's: explicit version-space counts must
equal the independent D engine's counts and the SAT verdict, else the item FAILS (``Evaluator.reference``).
Assignment of the follow-up condition, wording and named claims is a function of the world key and the split salt
only (never of any model answer).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..generators import World, opaque_id, world_seed
from ..s4.evaluator import Evaluator
from ..s4.tasks import make_design

REPO = Path(__file__).resolve().parents[3]
SPLITS = ("train", "smoke", "pilot", "main", "pilot2", "pilot3", "pilot4")
R5_SPLIT = {s: f"sprint_{s}" for s in SPLITS}
DESIGN_SALT = {s: f"r7-sprint-{s}-design-v1" for s in SPLITS}
ASSIGN_SALT = {s: f"r7-sprint-{s}-assign-v1" for s in SPLITS}
# published source groups per split (by sha256 rank); 'train' takes every remaining group
PUBLISHED_GROUPS = {"smoke": 0, "pilot": 8, "main": 32}
CONDITIONS = ("P0", "P1", "P2", "P3")
N_NAMED = 4
POP_VERSION = "r7-sprint-population-v1"


def _h(*parts) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


@dataclass(frozen=True)
class WorldKey:
    split: str
    population: str          # 'synthetic' | 'published'
    stratum: str             # R5 stratum, or 'published'
    index: int               # synthetic index; published: rank within the split's groups
    source_key: str          # '' (synthetic) or the external instance key 'sub:<model_dir>:<root_hash>'
    group: str               # source group (cluster for the bootstrap)

    @property
    def wkey(self) -> str:
        return f"{self.split}|{self.population}|{self.stratum}|{self.index}|{self.source_key}"

    def to_json(self) -> dict:
        return {"split": self.split, "population": self.population, "stratum": self.stratum, "index": self.index,
                "source_key": self.source_key, "group": self.group, "wkey": self.wkey}

    @classmethod
    def from_json(cls, d: dict) -> "WorldKey":
        return cls(d["split"], d["population"], d["stratum"], int(d["index"]), d["source_key"], d["group"])


# --------------------------------------------------------------------------- published fragments

@lru_cache(maxsize=1)
def published_pool() -> dict[str, list[dict]]:
    """Every R5/R6 transformed-panel fragment (8 nodes, k <= 3), by source group.  Read from the committed source
    manifests (the inventory itself is not rerun)."""
    pool: dict[str, dict] = {}
    for p in ("artifacts/r5_source_manifest.json", "artifacts/r6_source_manifest.json"):
        for x in json.loads((REPO / p).read_text())["transformed"]:
            pool.setdefault(x["group"], {})[x["key"]] = x
    return {g: sorted(v.values(), key=lambda x: x["key"]) for g, v in pool.items()}


def published_split() -> dict[str, list[str]]:
    groups = sorted(published_pool(), key=lambda g: _h("r7-sprint", g))
    out, i = {}, 0
    for s in ("smoke", "pilot", "main"):
        out[s] = groups[i:i + PUBLISHED_GROUPS[s]]
        i += PUBLISHED_GROUPS[s]
    out["train"] = groups[i:]
    out["pilot2"] = []                    # revision-1 pilot (D76): synthetic worlds only
    out["pilot3"] = []                    # revision-2 pilot (D78): synthetic worlds only
    out["pilot4"] = []                    # R7b pilot (D79): synthetic worlds only
    return out


# --------------------------------------------------------------------------- keys

def world_keys(split: str, published: bool = True) -> list[WorldKey]:
    from ..r5 import data as D
    keys = []
    for s in D.STRATA:
        for i in range(D.SPLITS[R5_SPLIT[split]]["per_stratum"]):
            inst = D.make_instance(R5_SPLIT[split], s, i)
            keys.append(WorldKey(split, "synthetic", s, i, "", inst.source_group_id))
    if published:
        pool = published_pool()
        for r, g in enumerate(published_split()[split]):
            x = min(pool[g], key=lambda x: _h("r7-sprint-frag", x["key"]))
            keys.append(WorldKey(split, "published", "published", r, x["key"], g))
    return keys


def build_world(k: WorldKey) -> World:
    if k.population == "synthetic":
        from ..r5 import data as D
        inst = D.make_instance(R5_SPLIT[k.split], k.stratum, k.index)
        return World(opaque_id("r7w", world_seed(k.split, "R7W", k.index, k.wkey)), "R7", k.stratum, "realizable",
                     world_seed(k.split, "R7W", k.index, k.wkey), inst.net, 3)
    from ..r5.external import load_instance
    net = load_instance(k.source_key)
    seed = world_seed(k.split, "R7W", k.index, k.wkey)
    return World(opaque_id("r7w", seed), "R7", "published", "realizable", seed, net, 3)


def evaluator(k: WorldKey) -> Evaluator:
    """Hidden world + exogenous design (the design stream never touches the mechanism)."""
    w = build_world(k)
    if not w.realizable():
        raise AssertionError(f"{k.wkey} leaves H(8, 3)")
    return Evaluator.from_world(w, make_design(DESIGN_SALT[k.split], k.index, f"r7|{k.population}|{k.stratum}|"
                                                                               f"{k.source_key}"))


def reference(ev: Evaluator, crosscheck_sat: bool = True) -> dict:
    """Exact reference per claim: status, p* (exact rational, as num/den strings and a float), hidden truth.
    Raises if the two exact engines (or SAT) disagree on any claim: a disagreement fails the item."""
    out = {}
    for r in ev.reference(crosscheck_sat=crosscheck_sat):
        out[r.cid] = {"status": r.verdict, "num": str(r.num), "den": str(r.den), "p_star": r.num / r.den,
                      "truth": r.truth_holds, "h": r.h, "iv": r.kind}
    return out


# --------------------------------------------------------------------------- hash assignment

def assign(keys: list[WorldKey], cids: tuple[str, ...] = tuple(f"c{i}" for i in range(8))) -> dict[str, dict]:
    """Condition, wording and named claims per world, from the world key and the split's assignment salt only.

    Balanced: strata in name order (published counts as one stratum), worlds within a stratum sorted by
    sha256(salt, wkey); ONE round-robin over P0..P3 runs through this sequence (it does not restart per stratum),
    the wording alternating per full round.  Named claims (4 of 8): the claims with
    the smallest sha256(salt, wkey, cid).  Every world gets a named set, including P0/P2 where it is not shown
    (the like-for-like baseline set)."""
    by: dict[str, list[WorldKey]] = {}
    for k in keys:
        by.setdefault(k.stratum, []).append(k)
    out, i = {}, 0
    for s in sorted(by):
        for k in sorted(by[s], key=lambda k: _h(ASSIGN_SALT[k.split], "order", k.wkey)):
            named = sorted(sorted(cids, key=lambda c: _h(ASSIGN_SALT[k.split], "named", k.wkey, c))[:N_NAMED],
                           key=lambda c: int(c[1:]))
            out[k.wkey] = {"condition": CONDITIONS[i % 4], "wording": 1 + (i // 4) % 2, "named": named}
            i += 1
    return out


def manifest(split: str) -> dict:
    keys = world_keys(split)
    a = assign(keys)
    items = []
    for k in keys:
        ev = evaluator(k)
        pub = ev.public()
        items.append({**k.to_json(), **a[k.wkey], "task_id": pub["task_id"], "world_id": ev.world.world_id,
                      "mechanism_sha256": hashlib.sha256(json.dumps(ev.world.net.canonical().to_json(),
                                                                    sort_keys=True).encode()).hexdigest(),
                      "public_sha256": hashlib.sha256(json.dumps(pub, sort_keys=True).encode()).hexdigest(),
                      "budget": ev.design.budget})
    return {"version": POP_VERSION, "split": split, "r5_split": R5_SPLIT[split], "design_salt": DESIGN_SALT[split],
            "assign_salt": ASSIGN_SALT[split], "n_worlds": len(items), "items": items}


# =========================================================================== R7b: two tiers, five conditions (D79)

TIERW_DESIGN_SALT = {s: f"r7b-sprint-{s}-W-design-v1" for s in SPLITS}
ASSIGN_SALT_R7B = {s: f"r7b-sprint-{s}-assign-v1" for s in SPLITS}
TIERW_BUDGETS = (6, 8)       # calibrated on train worlds with no model (D80)
CONDITIONS_R7B = ("P0", "P1", "P2", "P3", "P4")
TIERS = ("W", "H")
POP_VERSION_R7B = "r7b-sprint-population-v1"
# main panel: per synthetic stratum (26 worlds) the first 13 by sha256 are Tier W, the next 6 Tier H; published
# (32 fragments): first 16 Tier W, next 12 Tier H.  120 W + 60 H; the remaining 60 main worlds stay unshown.
MAIN_TIER_COUNTS = {"synthetic": (13, 6), "published": (16, 12)}
# pilot 4: per stratum (4 worlds) 3 Tier W, 1 Tier H (P4 only); 24 W + 8 H
PILOT4_TIER_COUNTS = {"synthetic": (3, 1), "published": (0, 0)}


def evaluator_w(k: WorldKey, budgets: tuple[int, ...] = TIERW_BUDGETS) -> Evaluator:
    """Tier W world: the SAME hidden mechanism as Tier H, the same evidence/claim design procedure on its own design
    stream, with a smaller budget drawn by hash (the design never touches the mechanism)."""
    w = build_world(k)
    if not w.realizable():
        raise AssertionError(f"{k.wkey} leaves H(8, 3)")
    B = budgets[int(_h(TIERW_DESIGN_SALT[k.split], "budget", k.wkey), 16) % len(budgets)]
    return Evaluator.from_world(w, make_design(TIERW_DESIGN_SALT[k.split], k.index,
                                               f"r7b|W|{k.population}|{k.stratum}|{k.source_key}", budget=B))


def public_w(ev: Evaluator) -> dict:
    """Tier W public task = the Tier H public payload + each node's listed inputs (essential inputs of the hidden
    rule).  Nothing else about the mechanism."""
    from .tierw import wiring_of
    pub = ev.public()
    pub["wiring"] = wiring_of(ev.world.net)
    pub["tier"] = "W"
    return pub


def tier_public(k: WorldKey, tier: str) -> tuple[Evaluator, dict]:
    if tier == "W":
        ev = evaluator_w(k)
        return ev, public_w(ev)
    ev = evaluator(k)
    return ev, ev.public()


def tier_reference(ev: Evaluator, pub: dict, tier: str, crosscheck_sat: bool = True) -> dict:
    if tier == "W":
        from .tierw import reference_w
        return reference_w(pub, ev.world.net, sat=crosscheck_sat)
    return reference(ev, crosscheck_sat=crosscheck_sat)


def split_tiers(keys: list[WorldKey], counts: dict) -> dict[str, str | None]:
    """Tier per world by sha256 within stratum (published counts as one stratum); None = not in the panel."""
    by: dict[str, list[WorldKey]] = {}
    for k in keys:
        by.setdefault(k.stratum, []).append(k)
    out = {}
    for s, ks in by.items():
        nw, nh = counts["published" if s == "published" else "synthetic"]
        for i, k in enumerate(sorted(ks, key=lambda k: _h("r7b-tier", k.split, k.wkey))):
            out[k.wkey] = "W" if i < nw else "H" if i < nw + nh else None
    return out


def named_claims(k: WorldKey, eligible: list[str]) -> list[str]:
    """4 named claims: the smallest sha256(salt, wkey, cid) among the ELIGIBLE claims (a property of the public
    evidence: derivation and forged derivation within the cap, a forgery exists)."""
    salt = ASSIGN_SALT_R7B[k.split]
    return sorted(sorted(eligible, key=lambda c: _h(salt, "named", k.wkey, c))[:N_NAMED], key=lambda c: int(c[1:]))


def assign_r7b(keys: list[WorldKey], tiers: dict[str, str], eligible: dict[str, list[str]],
               conditions: tuple[str, ...] = CONDITIONS_R7B, fixed: dict[str, str] | None = None) -> dict[str, dict]:
    """Condition, wording and named claims per world, from the world key, the split's R7b salt and the public
    eligibility only.  Within each tier: strata in name order, worlds by sha256(salt, wkey), ONE round-robin over
    ``conditions``, wording alternating per full round.  ``fixed``: tier -> condition for every world of that tier
    (pilot 4: Tier H is P4 only)."""
    out = {}
    for tier in TIERS:
        ks = [k for k in keys if tiers.get(k.wkey) == tier]
        by: dict[str, list[WorldKey]] = {}
        for k in ks:
            by.setdefault(k.stratum, []).append(k)
        i = 0
        for s in sorted(by):
            for k in sorted(by[s], key=lambda k: _h(ASSIGN_SALT_R7B[k.split], "order", k.wkey)):
                cond = fixed[tier] if fixed and tier in fixed else conditions[i % len(conditions)]
                out[k.wkey] = {"tier": tier, "condition": cond, "wording": 1 + (i // len(conditions)) % 2,
                               "named": named_claims(k, eligible[k.wkey])}
                i += 1
    return out


def checks_for(pub: dict, tier: str, named: list[str], salt: str) -> dict:
    """Checker status and forged status of every named claim (defined for every world whatever its condition)."""
    from . import tasks as T
    return T.check_statuses(pub, tier, named, salt)


def manifest_r7b(split: str, counts: dict, fixed: dict | None = None) -> dict:
    from . import tierw as TW
    keys = world_keys(split)
    tiers = split_tiers(keys, counts)
    pubs, evs, elig, nelig = {}, {}, {}, {}
    for k in keys:
        if tiers[k.wkey] is None:
            continue
        ev, pub = tier_public(k, tiers[k.wkey])
        evs[k.wkey], pubs[k.wkey] = ev, pub
        if tiers[k.wkey] == "W":
            tab = TW.Table.from_public(pub)
            el = [c["cid"] for c in pub["claims"]
                  if TW.claim_package(pub, c["cid"], ASSIGN_SALT_R7B[split], tab)["eligible"]]
        else:
            el = [c["cid"] for c in pub["claims"]]
        elig[k.wkey] = el
        nelig[k.wkey] = len(el)
    a = assign_r7b([k for k in keys if tiers[k.wkey]], tiers, elig, fixed=fixed)
    items = []
    for k in keys:
        if tiers[k.wkey] is None:
            continue
        ev, pub = evs[k.wkey], pubs[k.wkey]
        x = a[k.wkey]
        items.append({**k.to_json(), **x, "task_id": pub["task_id"], "world_id": ev.world.world_id,
                      "mechanism_sha256": hashlib.sha256(json.dumps(ev.world.net.canonical().to_json(),
                                                                    sort_keys=True).encode()).hexdigest(),
                      "public_sha256": hashlib.sha256(json.dumps(pub, sort_keys=True).encode()).hexdigest(),
                      "budget": ev.design.budget, "eligible_claims": nelig[k.wkey],
                      **checks_for(pub, x["tier"], x["named"], ASSIGN_SALT_R7B[split])})
    return {"version": POP_VERSION_R7B, "split": split, "r5_split": R5_SPLIT[split],
            "design_salt": {"H": DESIGN_SALT[split], "W": TIERW_DESIGN_SALT[split]},
            "assign_salt": ASSIGN_SALT_R7B[split], "tierw_budgets": list(TIERW_BUDGETS),
            "tier_counts": {"W": sum(x["tier"] == "W" for x in items), "H": sum(x["tier"] == "H" for x in items)},
            "n_worlds": len(items), "items": items}
