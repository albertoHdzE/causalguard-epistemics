"""R5 integrated demonstration (illustration only; NOT evaluation evidence; worlds are fixed, not selected by
outcome).  Prints: public evidence -> unknown target -> investigation (exact-EIG proposal) -> purchased observation
-> checked conclusion -> assumption challenge, and the n = 2 branch where a model-relative proof is false in the
simulator and the expanded-class policy abstains.  Every hidden value is printed only after the decision it scores."""
from __future__ import annotations

from ..s4.workspace import make_workspace
from . import investigation as I
from .misspec import and_counterexample


def run_demo(print_fn=print) -> dict:
    w = I.world("calibration", "template_exceptions", 0)            # fixed calibration world (index 0)
    pub = w["pub"]
    ws = make_workspace("D", pub)
    L = pub["node_labels"]
    print_fn("== 1. Public evidence and an unknown target (simulation; declared class: <= 3 inputs per node)")
    print_fn(I.render(pub, ws, I.readout(ws, pub["menu"], list(range(16))), "D", list(range(16)), 4, [])
             .split("Available measurements")[0])
    out = {"steps": []}
    avail = list(range(16))
    for step in range(4):
        ro = I.readout(ws, pub["menu"], avail)
        if ro["status"] in ("entailed", "refuted"):
            break
        pick = I.choose("eig", ro, avail, None)
        val = I._observe(w["net"], pub["menu"][pick])                  # evaluator outcome, after the choice
        avail.remove(pick)
        ws = I._purchase(ws, pub["menu"][pick], val)
        it = pub["menu"][pick]
        print_fn(f"== 2.{step + 1} Proposed measurement (exact EIG): item {pick}: {I._desc(it, L, 8)} -> observed {val}")
        out["steps"].append({"item": pick, "value": val})
    from ..s4.checking import check, validate_proposal
    r = ws.check(pub["claims"][0])
    print_fn(f"== 3. Exact status after purchases: {r['verdict']} ({r['counts']})")
    if r["verdict"] in ("entailed", "refuted"):
        d = check(validate_proposal({"cid": "target", "asserted": r["verdict"]}, {"target": pub["claims"][0]}), ws)
        print_fn(f"   checked conclusion: {d.proposal_check_status}; certificate: SAT cross-check of the impossible side"
                 f" ({[v for k, v in d.certificate.items() if k.startswith('side')]}) + witness replay. Relative to the "
                 "declared class and the evidence only.")
        out["checked"] = d.proposal_check_status
    print_fn(f"   simulator value (revealed after the decision): {I._truth(w['net'], ws)}")
    print_fn("== 4. Assumption challenge: the same kind of proof when the world is OUTSIDE the class (n = 2)")
    ce = and_counterexample()
    print_fn(f"   declared indegree <= 1: x0 after one step from 11 is {ce['k1']['verdict']} for 'x0 = 1' "
             f"(verified 0; counts {ce['k1']['num']}/{ce['k1']['den']})")
    print_fn(f"   hidden simulator: x0 = x0 AND x1 gives {ce['hidden_target_value']}  -> the model-relative proof is false "
             "in the world; no solver erred")
    print_fn(f"   expanded class indegree <= 2: {ce['k2']['verdict']} ({ce['k2']['num']}/{ce['k2']['den']}) -> the "
             "class-robust policy abstains instead of releasing")
    out["counterexample"] = ce
    return out
