"""S3 task objects: the same structured evidence/verdict semantics as S2, rendered for LLMs.

Owner of: S3 world/task generation, public (model-facing) payloads, private
oracle records, symbolic-solver answers (arm E) and witness feedback (arm D).

Public payload: class description, observations, query, required output
format.  It contains NO verdict, no hidden network and no hidden answer.
Private record: network, evidence-relative verdict, hidden-world answer and the
replayed witness mechanisms used for D feedback.

D feedback never states a verdict label.  It shows a compatible mechanism
(checked against every observation by the independent reference) that
contradicts the model's claim when one exists, otherwise one that supports it.
Such a witness CAN reveal the answer implicitly (e.g. if only supporting
witnesses are ever shown); D is therefore 'witness-assisted correction', not
label-free learning.  D-label states the verdict and is a privileged control.
"""
from __future__ import annotations

import random

from . import reference
from .generators import World, make_s3_world, world_seed
from .schema import Evidence, HypothesisClass, Intervention, Network, Observation, Pred, Query
from .versionspace import build_version_space, predict, verdict

VERDICT_LABELS = ("entailed", "refuted", "underdetermined")
S3_BUDGETS = (3, 5, 8)


def _state_str(x: int, n: int) -> str:
    return "(" + ",".join(str((x >> i) & 1) for i in range(n)) + ")"


def describe_class(n: int, k: int) -> str:
    names = ", ".join(f"x{i}" for i in range(n))
    return (f"A system has {n} binary variables ({names}). Time advances in discrete updates. At every "
            f"update ALL variables change simultaneously: each variable's next value is a fixed, unknown "
            f"Boolean function of the CURRENT values of at most {k} variables (any such function is allowed, "
            f"including constants, copying, negation, AND, OR, XOR, implications; a variable may read itself). "
            f"The functions never change. States are written as (x0,...,x{n-1}).")


def describe_observation(o: Observation, n: int) -> str:
    fin = ", ".join(f"x{i}={v}" for i, v in o.observed)
    if o.intervention.kind == "none":
        return f"From state {_state_str(o.state, n)}, after 1 update: {fin}."
    a = ", ".join(f"x{i}={v}" for i, v in o.intervention.assign)
    return (f"From state {_state_str(o.state, n)} with {a} held fixed (clamped), after 1 update: {fin}.")


def describe_query(q: Query, n: int) -> str:
    from .semantics import pred_to_cubes
    x0 = pred_to_cubes(q.domain)[0][1]
    t = q.target
    tgt = f"x{t.node}={t.value}"
    h = q.horizon
    upd = f"{h} update{'s' if h != 1 else ''}"
    if q.intervention.kind == "none":
        how = f"Start from state {_state_str(x0, n)} and run {upd}."
    elif q.intervention.kind == "initial_edit":
        a = ", ".join(f"x{i}={v}" for i, v in q.intervention.assign)
        how = (f"Start from state {_state_str(x0, n)}, set {a} once at time 0 (after that the variable evolves "
               f"normally), then run {upd}.")
    else:
        a = ", ".join(f"x{i}={v}" for i, v in q.intervention.assign)
        how = (f"Start from state {_state_str(x0, n)}, clamp {a} permanently (it is forced back to that value "
               f"after every update), then run {upd}.")
    return f"{how} Claim: after the {upd}, {tgt}."


INSTRUCTIONS = (
    "Decide the status of the claim RELATIVE TO THE OBSERVATIONS AND THE STATED CLASS of possible systems:\n"
    "- entailed: the claim is true for EVERY system in the class that is consistent with all observations;\n"
    "- refuted: the claim is false for EVERY such system;\n"
    "- underdetermined: some consistent systems make it true and others make it false.\n"
    "Respond with ONLY a JSON object: {\"verdict\": \"entailed\"|\"refuted\"|\"underdetermined\", "
    "\"probabilities\": {\"entailed\": p1, \"refuted\": p2, \"underdetermined\": p3}, \"reason\": \"<one short "
    "sentence>\"} where the probabilities are your confidence and sum to 1.")


def describe_network(net: Network) -> str:
    lines = []
    for j, r in enumerate(net.rules):
        if not r.inputs:
            lines.append(f"x{j} next = {r.table & 1} (constant)")
            continue
        ins = ",".join(f"x{i}" for i in r.inputs)
        entries = []
        for y in range(1 << r.arity):
            vals = ",".join(str((y >> t) & 1) for t in range(r.arity))
            entries.append(f"({vals})->{(r.table >> y) & 1}")
        lines.append(f"x{j} next = f({ins}) with table " + " ".join(entries))
    return "\n".join(lines)


def make_s3_items(salt: str, index: int, n: int = 4, k: int = 2, items_per_world: int = 4) -> dict:
    world: World = make_s3_world(salt, index, n=n, kmax=k)
    rng = random.Random(world_seed(salt, "S3-items", index))
    B = S3_BUDGETS[index % len(S3_BUDGETS)]
    states = rng.sample(range(1 << n), B)
    obs = []
    for x in states:
        fin = reference.run(world.net, x, Intervention(), 1)[-1]
        obs.append(Observation(x, Intervention(), 1, tuple((i, (fin >> i) & 1) for i in range(n))))
    ev = Evidence(n, tuple(obs), "uniform_states")
    vs = build_version_space(ev, HypothesisClass(n, k))
    keys = ev.keys()
    items = []
    tries = 0
    while len(items) < items_per_world and tries < 1000:
        tries += 1
        kind = rng.choice(["none", "initial_edit", "persistent_clamp"])
        h = rng.choice([1, 2])
        iv = Intervention() if kind == "none" else Intervention(kind, ((rng.randrange(n), rng.randint(0, 1)),))
        x = rng.randrange(1 << n)
        b = rng.choice([i for i in range(n) if not (kind == "persistent_clamp" and i == iv.assign[0][0])])
        q = Query.point(x, n, iv, h, Pred.lit(b, 1))
        key = (x, iv.kind, iv.assign, h)
        if key in keys:
            continue
        keys.add(key)
        vr = verdict(vs, q)
        items.append({"query": q, "verdict": vr.verdict.value, "witnesses": list(vr.certificate.witness_models),
                      "hidden_answer": int(predict(world.net, q))})
    world_id = world.world_id
    public = {"world_id": world_id, "n": n, "k": k, "class_text": describe_class(n, k),
              "observations_text": [describe_observation(o, n) for o in obs],
              "items": [{"item_id": f"{world_id}-q{i}", "query_text": describe_query(it["query"], n)}
                        for i, it in enumerate(items)]}
    private = {"world": world.to_private_json(), "evidence": ev.to_json(),
               "items": [{"item_id": f"{world_id}-q{i}", "query": it["query"].to_json(), "verdict": it["verdict"],
                          "hidden_answer": it["hidden_answer"], "witnesses": it["witnesses"]}
                         for i, it in enumerate(items)],
               "version_space_counts": vs.counts(), "budget": B}
    return {"public": public, "private": private}


def render_item_prompt(public: dict, item_index: int) -> str:
    obs = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(public["observations_text"]))
    return (f"{public['class_text']}\n\nObservations:\n{obs}\n\nQuestion: {public['items'][item_index]['query_text']}"
            f"\n\n{INSTRUCTIONS}")


def witness_feedback(private: dict, item_index: int, claimed: str | None) -> tuple[str, dict]:
    """Feedback for arm D: a replayed compatible mechanism, chosen against the claim.

    Returns (text, provenance).  Never contains a verdict label."""
    it = private["items"][item_index]
    q = Query.from_json(it["query"])
    ev = Evidence.from_json(private["evidence"])
    wits = [Network.from_json(w) for w in it["witnesses"]]
    for w in wits:  # every shown mechanism is re-checked independently
        assert reference.consistent(w, ev)
    by_answer = {predict(w, q): w for w in wits}
    if claimed == "entailed":
        show = [by_answer.get(False) or by_answer.get(True)]
    elif claimed == "refuted":
        show = [by_answer.get(True) or by_answer.get(False)]
    else:  # underdetermined / invalid / abstain: show what exists (one or two mechanisms)
        show = [w for w in (by_answer.get(True), by_answer.get(False)) if w is not None]
    n = q.domain.max_node() + 1
    parts = []
    for w in show:
        from .semantics import pred_to_cubes
        x0 = pred_to_cubes(q.domain)[0][1]
        tr = reference.run(w, x0, q.intervention, q.horizon)
        holds = predict(w, q)
        parts.append("A checker found this system, which reproduces EVERY observation above:\n"
                     + describe_network(w) + "\nUnder the question's procedure its trajectory is "
                     + " -> ".join(_state_str(s, n) for s in tr)
                     + f", so for this system the claim is {'TRUE' if holds else 'FALSE'}.")
    text = "\n\n".join(parts) + "\n\nReconsider the question and answer again in the same JSON format."
    prov = {"source": "symbolic_checker_witnesses", "shown_answers": [predict(w, q) for w in show],
            "n_shown": len(show), "claimed": claimed}
    return text, prov


def label_feedback(private: dict, item_index: int) -> str:
    v = private["items"][item_index]["verdict"]
    return (f"A reference solver reports that the correct status of the claim is: {v}. "
            "Answer again in the same JSON format.")


def solver_answer(private: dict, item_index: int) -> dict:
    """Arm E: exact symbolic verdict, as a one-hot probability vector."""
    v = private["items"][item_index]["verdict"]
    return {"verdict": v, "probabilities": {k: float(k == v) for k in VERDICT_LABELS}}
