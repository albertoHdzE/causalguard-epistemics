"""Reproducible check-before-release demonstration (P5).

    python -m causalguard s4-demo [--live MODEL_CONFIG.json]

1. The public task is shown (the mechanism stays hidden).
2. An AI proposes conclusions.  Default: a fixed, labelled "naive proposer" (observed-majority rule asserting
   certainty), so the demo is reproducible without a model; --live uses a local model through the pilot harness.
3. The checker returns verified / refuted-with-replayable-counterexample / forecast-only BEFORE release.
4. The uncertainty of an underdetermined claim is inspected (exact counts, opposing mechanisms).
5. A permitted experiment is chosen by exact expected information (the claim's own experiment is excluded).
6. The purchased observation updates V(D); the claim is re-checked and its verified conclusion is committed.
   A stale decision (pre-measurement) is refused.
7. The hidden mechanism is revealed last.

The demo world is the first index (fixed search order over salt "demo-s4-v1", ordered_motif family) whose
first underdetermined claim is resolved by one menu measurement; this selection is for illustration only and
is disclosed in the output.
"""
from __future__ import annotations

import json

from ..schema import Evidence, Intervention, Observation, Query
from .checking import CommitRefused, check, commit, validate_proposal
from .evaluator import Evaluator
from .offline import _menu, _x0
from .pilot import render_claim, render_task
from .workspace import make_workspace

SALT = "demo-s4-v1"


def _naive(pub):
    ev = Evidence.from_json(pub["evidence"])
    out = {}
    for c in pub["claims"]:
        q = Query.from_json(c["query"])
        vals = [v for o in ev.observations for j, v in o.observed if j == q.target.node]
        maj = int(2 * sum(vals) > len(vals))
        out[c["cid"]] = {"verdict": "entailed" if maj == q.target.value else "refuted", "forecast": maj}
    return out


def find_demo_world(family="ordered_motif", max_index=60):
    import random
    for i in range(max_index):
        ev = Evaluator(SALT, i, family, budget=12)
        pub = ev.public()
        refs = ev.reference(crosscheck_sat=False)
        und = [(c, r) for c, r in zip(pub["claims"], refs) if r.verdict == "underdetermined"]
        if not und:
            continue
        c, r = und[0]
        q = Query.from_json(c["query"])
        s0 = _x0(q, pub["n"])
        m, v = q.intervention.masks
        menu = _menu(random.Random(f"{SALT}|menu|{i}"), pub["n"], 12, {((s0 & ~m) | v, q.target.node)})
        ws = make_workspace("D", pub)
        vals = ws.measurement_values(c, menu)
        best = max(range(len(menu)), key=lambda t: (vals[t]["eig_bits"] or 0, -t))
        it = menu[best]
        iv = Intervention.from_json(it["intervention"])
        val = ev.observe(it["state"], iv, it["node"])
        ws2 = ws.update([Observation(it["state"], iv, 1, ((it["node"], val),))])
        if ws2.check(c)["verdict"] in ("entailed", "refuted"):
            return i, ev, pub, c, menu, best, vals
    raise RuntimeError("no demo world found in the fixed search range")


def run_demo(live_cfg: dict | None = None, out=print) -> dict:
    i, ev, pub, claim, menu, best, vals = find_demo_world()
    L = pub["node_labels"]
    log = {"demo_world_index": i, "salt": SALT, "steps": []}
    out(f"== 1. Public task (world index {i} of salt {SALT}; chosen as the first world whose first "
        "underdetermined claim one permitted measurement resolves; illustration only)")
    out(render_task(pub))
    ws = make_workspace("D", pub)
    cby = {c["cid"]: c for c in pub["claims"]}
    if live_cfg:
        from ..llm.harness import CallBudget
        from ..llm.providers import make_provider
        from .pilot import run_episode
        ep = run_episode("A", pub, make_provider(live_cfg), CallBudget(1, None), 0, pub["task_id"])
        proposals, who = ep["final"], f"live model {live_cfg.get('model')}"
    else:
        proposals, who = _naive(pub), "fixed naive proposer (asserts certainty from the target's observed majority)"
    out(f"\n== 2. Proposed conclusions ({who})")
    decisions = {}
    for cid, a in proposals.items():
        p = validate_proposal({"cid": cid, "asserted": a["verdict"], "forecast": a["forecast"]}, cby)
        d = check(p, ws)
        decisions[cid] = (p, d)
        out(f"  {render_claim(cby[cid], pub)}\n     proposed {a['verdict']:<15} -> check: {d.proposal_check_status:<16}"
            f" (claim status: {d.epistemic_verdict})")
        log["steps"].append({"cid": cid, "proposed": a["verdict"], "status": d.proposal_check_status,
                             "claim_status": d.epistemic_verdict})
    blocked = [cid for cid, (p, d) in decisions.items() if d.proposal_check_status != "verified"]
    out(f"\n== 3. Before release: {len(blocked)} of {len(decisions)} proposals blocked; released as verified: "
        f"{[cid for cid in decisions if cid not in blocked]}")
    if blocked:
        p, d = decisions[blocked[0]]
        out(f"  counterexample for {blocked[0]}: {json.dumps(d.counterexample, indent=None)[:900]}")
    cid = claim["cid"]
    r = ws.check(claim)
    num, den = int(r["counts"]["num"]), int(r["counts"]["den"])
    out(f"\n== 4. Uncertainty of {cid}: {num} of {den} consistent mechanisms make it true (p = {num / den:.3f}); "
        "opposing example mechanisms:")
    for h, w in r["witnesses"].items():
        out(f"  claim {'true ' if h == '1' else 'false'}: " + "; ".join(w[:-1]))
    out("\n== 5. Permitted experiments (the claim's own experiment excluded), exact expected information about "
        f"{cid}:")
    for t, v in sorted(enumerate(vals), key=lambda tv: -(tv[1]["eig_bits"] or 0))[:5]:
        it = menu[t]
        ivs = Intervention.from_json(it["intervention"])
        how = "" if ivs.kind == "none" else " clamp " + ",".join(f"{L[j]}={b}" for j, b in ivs.assign)
        out(f"  #{t:02d} observe {L[it['node']]} after one step from {''.join(str((it['state'] >> j) & 1) for j in range(pub['n']))}"
            f"{how}: EIG {v['eig_bits']:.3f} bits")
    it = menu[best]
    iv = Intervention.from_json(it["intervention"])
    val = ev.observe(it["state"], iv, it["node"])          # the evaluator answers only the purchased measurement
    out(f"  -> buy #{best:02d}; observed {L[it['node']]} = {val}")
    old_p = validate_proposal({"cid": cid, "asserted": "underdetermined", "forecast": None}, cby)
    old_d = check(old_p, ws)
    ws2 = ws.update([Observation(it["state"], iv, 1, ((it["node"], val),))])
    r2 = ws2.check(claim)
    out(f"\n== 6. Re-check {cid} with the new observation: {r2['verdict']} (counts {r2['counts']['num']}/{r2['counts']['den']})")
    p2 = validate_proposal({"cid": cid, "asserted": r2["verdict"], "forecast": None}, cby)
    d2 = check(p2, ws2)
    rel = commit(p2, d2, ws2)
    out(f"  commit of the verified conclusion: released={rel['released']} verified={rel['verified']}")
    try:
        commit(old_p, old_d, ws2)
        stale = "ACCEPTED (bug)"
    except CommitRefused as e:
        stale = f"refused ({e})"
    out(f"  the pre-measurement decision re-used after the update: {stale}")
    from .hcode import describe
    from .workspace import render_analytic
    out("\n== 7. Reveal (evaluator): hidden mechanism")
    for line in render_analytic(ev.world.net, L, pub["k"]):
        out("  " + line)
    truth = ev.truth_holds(Query.from_json(claim["query"]))
    out(f"  {cid} in the hidden system: {'true' if truth else 'false'}; checked conclusion: {r2['verdict']}")
    log.update(final_verdict=r2["verdict"], truth_holds=truth, stale_commit=stale,
               hidden_cgh_bits=describe(ev.world.net, pub["k"])[0])
    return log
