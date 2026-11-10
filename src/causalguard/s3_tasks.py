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
    "sentence>\"}. The three probabilities are your confidence that each of the three STATUSES is the correct "
    "status (they are not probabilities that the claim is true or false); they must sum to 1 and the largest "
    "should correspond to your verdict.")


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


# =========================================================================== iteration 2 (task version s3-tasks-v2)
#
# Repairs R09 / P6.  Differences from v1 (v1 functions above are kept unchanged for the historical pilot):
#  * EXOGENOUS design: observation states and every query candidate are drawn from a design RNG that is
#    independent of the mechanism RNG (the mechanism is only evaluated afterwards).
#  * BALANCED challenge items: per world 3 "balanced" items whose target verdicts are a random permutation of
#    (entailed, refuted, underdetermined), each searched within one (budget, horizon, intervention) cell;
#    1 "natural" item (first draw of its cell, natural verdict); 1 fresh "transfer_target" item whose target
#    verdict rotates with the world index.  Target polarity x_b = 0/1 is drawn uniformly.
#    Rejection rule (declared): up to S3_V2_MAX_TRIES candidates per item in its cell; if none has the target
#    verdict, the FIRST candidate is used and the item is flagged balance_shortfall (never dropped).
#  * TRANSFORMED items (arm A only, clustered under the base world, never counted as new worlds): the polarity
#    complement of each balanced item (verdict entailed<->refuted), and variable renamings of balanced items 0
#    and 1 (the whole world is renamed by a design-RNG permutation; the verdict is re-derived and must agree).
#  * Feedback material: certificate+label (D-cert), label only (D-label), K=2 uniformly sampled compatible
#    mechanisms drawn once per world from public evidence (D-sample; no query, label or answer conditioning).

S3_TASK_VERSION = "s3-tasks-v2"
S3_V2_MAX_TRIES = 400
S3_V2_KINDS = ("none", "initial_edit", "persistent_clamp")
S3_V2_HORIZONS = (1, 2)
D_SAMPLE_K = 2


def _rename_state(x: int, perm: list[int]) -> int:
    return sum(((x >> i) & 1) << perm[i] for i in range(len(perm)))


def rename_query(q: Query, perm: list[int], n: int) -> Query:
    from .semantics import pred_to_cubes
    x0 = pred_to_cubes(q.domain)[0][1]
    iv = q.intervention
    iv2 = iv if iv.kind == "none" else Intervention(iv.kind, tuple((perm[a], v) for a, v in iv.assign))
    t = q.target
    return Query.point(_rename_state(x0, perm), n, iv2, q.horizon, Pred.lit(perm[t.node], t.value))


def rename_observation(o: Observation, perm: list[int]) -> Observation:
    return Observation(_rename_state(o.state, perm), o.intervention, o.horizon,
                       tuple(sorted((perm[i], v) for i, v in o.observed)))


def complement_query(q: Query, n: int) -> Query:
    from .semantics import pred_to_cubes
    x0 = pred_to_cubes(q.domain)[0][1]
    return Query.point(x0, n, q.intervention, q.horizon, Pred.lit(q.target.node, 1 - q.target.value))


COMPLEMENT_VERDICT = {"entailed": "refuted", "refuted": "entailed", "underdetermined": "underdetermined"}


def _draw_query(rng: random.Random, n: int, kind: str, h: int) -> Query:
    iv = Intervention() if kind == "none" else Intervention(kind, ((rng.randrange(n), rng.randint(0, 1)),))
    x = rng.randrange(1 << n)
    b = rng.choice([i for i in range(n) if not (kind == "persistent_clamp" and i == iv.assign[0][0])])
    return Query.point(x, n, iv, h, Pred.lit(b, rng.randint(0, 1)))


def sample_compatible_mechanisms(vs, k: int, rng: random.Random) -> list[Network]:
    """K mechanisms drawn independently and uniformly from V(D) (product of per-node uniform draws).
    Uses ONLY the public version space."""
    from .versionspace import network_from_choice
    out = []
    for _ in range(k):
        choice = [int(c[rng.randrange(len(c))]) for c in vs.compatible]
        out.append(network_from_choice(vs.cls, choice))
    return out


def make_s3_items_v2(salt: str, index: int, n: int = 4, k: int = 2) -> dict:
    world: World = make_s3_world(salt, index, n=n, kmax=k)
    drng = random.Random(world_seed(salt, "S3-design-v2", index))        # design stream (exogenous)
    srng = random.Random(world_seed(salt, "S3-dsample-v2", index))       # D-sample stream (public evidence only)
    B = S3_BUDGETS[index % len(S3_BUDGETS)]
    states = drng.sample(range(1 << n), B)
    perm = list(range(n))
    drng.shuffle(perm)
    obs = []
    for x in states:   # the mechanism is evaluated only now, after the design is fixed
        fin = reference.run(world.net, x, Intervention(), 1)[-1]
        obs.append(Observation(x, Intervention(), 1, tuple((i, (fin >> i) & 1) for i in range(n))))
    ev = Evidence(n, tuple(obs), "uniform_states")
    vs = build_version_space(ev, HypothesisClass(n, k))
    obs_keys = ev.keys()
    targets = list(VERDICT_LABELS)
    drng.shuffle(targets)
    plan = [("balanced", t) for t in targets] + [("natural", None),
                                                 ("transfer_target", VERDICT_LABELS[index % 3])]
    used = set()
    items, shortfalls = [], []
    for role, want in plan:
        kind, h = drng.choice(S3_V2_KINDS), drng.choice(S3_V2_HORIZONS)
        first = None
        chosen = None
        tries = 0
        while tries < S3_V2_MAX_TRIES:
            q = _draw_query(drng, n, kind, h)
            key = (point_state(q), q.intervention.kind, q.intervention.assign, q.horizon, q.target.node)
            if (key[:4] in obs_keys) or key in used:
                continue  # declared exogenous rule: never ask an observed transition key or a repeated query
            tries += 1
            vr = verdict(vs, q)
            cand = (q, vr)
            if first is None:
                first = cand
            if want is None or vr.verdict.value == want:
                chosen = cand
                break
        shortfall = chosen is None
        if shortfall:
            chosen = first
            shortfalls.append({"role": role, "target_verdict": want, "budget": B, "horizon": h, "kind": kind})
        q, vr = chosen
        used.add((point_state(q), q.intervention.kind, q.intervention.assign, q.horizon, q.target.node))
        items.append({"role": role, "query": q, "verdict": vr.verdict.value, "target_verdict": want,
                      "balance_shortfall": shortfall, "tries": tries, "cell": {"budget": B, "horizon": h, "kind": kind},
                      "witnesses": list(vr.certificate.witness_models), "hidden_answer": int(predict(world.net, q)),
                      "observations": None})
    base = list(items)
    # transformed items (A only)
    for bi in range(3):
        qc = complement_query(base[bi]["query"], n)
        vc = verdict(vs, qc)
        if vc.verdict.value != COMPLEMENT_VERDICT[base[bi]["verdict"]]:  # pragma: no cover - semantic invariant
            raise AssertionError("complement verdict invariant violated")
        items.append({"role": f"complement_of:{bi}", "query": qc, "verdict": vc.verdict.value, "target_verdict": None,
                      "balance_shortfall": False, "tries": 0, "cell": base[bi]["cell"],
                      "witnesses": list(vc.certificate.witness_models), "hidden_answer": int(predict(world.net, qc)),
                      "observations": None})
    obs_r = [rename_observation(o, perm) for o in obs]
    ev_r = Evidence(n, tuple(obs_r), "uniform_states")
    vs_r = build_version_space(ev_r, HypothesisClass(n, k))
    for bi in range(2):
        qr = rename_query(base[bi]["query"], perm, n)
        vr2 = verdict(vs_r, qr)
        if vr2.verdict.value != base[bi]["verdict"]:  # pragma: no cover - semantic invariant
            raise AssertionError("renaming verdict invariant violated")
        items.append({"role": f"renamed_of:{bi}", "query": qr, "verdict": vr2.verdict.value, "target_verdict": None,
                      "balance_shortfall": False, "tries": 0, "cell": base[bi]["cell"],
                      "witnesses": list(vr2.certificate.witness_models), "hidden_answer": None,
                      "observations": "renamed"})
    sampled = sample_compatible_mechanisms(vs, D_SAMPLE_K, srng)
    for s in sampled:
        assert reference.consistent(s, ev)
    world_id = world.world_id
    obs_text = [describe_observation(o, n) for o in obs]
    obs_text_r = [describe_observation(o, n) for o in obs_r]
    public = {"world_id": world_id, "task_version": S3_TASK_VERSION, "n": n, "k": k,
              "class_text": describe_class(n, k), "observations_text": obs_text,
              "observations_text_renamed": obs_text_r,
              "items": [{"item_id": f"{world_id}-q{i}", "role": it["role"],
                         "query_text": describe_query(it["query"], n), "query": it["query"].to_json(),
                         "renamed": it["observations"] == "renamed"} for i, it in enumerate(items)],
              "d_sample_mechanisms": [s.to_json() for s in sampled]}
    private = {"world": world.to_private_json(), "evidence": ev.to_json(), "evidence_renamed": ev_r.to_json(),
               "renaming_permutation": perm, "task_version": S3_TASK_VERSION,
               "items": [{"item_id": f"{world_id}-q{i}", "role": it["role"], "query": it["query"].to_json(),
                          "verdict": it["verdict"], "target_verdict": it["target_verdict"],
                          "balance_shortfall": it["balance_shortfall"], "tries": it["tries"], "cell": it["cell"],
                          "hidden_answer": it["hidden_answer"], "witnesses": it["witnesses"],
                          "renamed": it["observations"] == "renamed"} for i, it in enumerate(items)],
               "version_space_counts": vs.counts(), "budget": B, "balance_shortfalls": shortfalls,
               "seeds": {"mechanism": world.seed, "design": world_seed(salt, "S3-design-v2", index),
                         "d_sample": world_seed(salt, "S3-dsample-v2", index)}}
    return {"public": public, "private": private}


def point_state(q: Query) -> int:
    from .semantics import pred_to_cubes
    return pred_to_cubes(q.domain)[0][1]


def render_item_prompt_v2(public: dict, item_index: int) -> str:
    it = public["items"][item_index]
    texts = public["observations_text_renamed"] if it.get("renamed") else public["observations_text"]
    obs = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
    return f"{public['class_text']}\n\nObservations:\n{obs}\n\nQuestion: {it['query_text']}\n\n{INSTRUCTIONS}"


def _mechanism_block(w: Network, q: Query, n: int, intro: str) -> str:
    x0 = point_state(q)
    tr = reference.run(w, x0, q.intervention, q.horizon)
    holds = predict(w, q)
    return (intro + "\n" + describe_network(w) + "\nUnder the question's procedure its trajectory is "
            + " -> ".join(_state_str(s, n) for s in tr) + f", so for this system the claim is "
            f"{'TRUE' if holds else 'FALSE'}.")


def cert_feedback(private: dict, item_index: int) -> tuple[str, dict]:
    """D-cert: the reference verdict LABEL plus its mechanistic certificate (transparently privileged).
    underdetermined -> two replayed compatible systems with opposite answers;
    entailed/refuted -> one replayed compatible system with the claimed answer plus the statement that the
    solver proved no consistent system gives the other answer."""
    it = private["items"][item_index]
    q = Query.from_json(it["query"])
    ev = Evidence.from_json(private["evidence"])
    n = ev.n
    wits = [Network.from_json(w) for w in it["witnesses"]]
    for w in wits:
        assert reference.consistent(w, ev)
    v = it["verdict"]
    parts = [f"A reference solver reports that the correct status of the claim is: {v}. Here is its certificate."]
    for j, w in enumerate(wits):
        parts.append(_mechanism_block(w, q, n, f"Consistent system {j + 1} (it reproduces EVERY observation above):"))
    if v in ("entailed", "refuted"):
        other = "FALSE" if v == "entailed" else "TRUE"
        parts.append(f"The solver also proved that NO system in the class that reproduces every observation makes "
                     f"the claim {other}.")
    text = "\n\n".join(parts) + "\n\nReconsider the question and answer again in the same JSON format."
    return text, {"source": "reference_verdict_label_plus_certificate", "n_mechanisms": len(wits), "label": v}


def label_feedback_v2(private: dict, item_index: int) -> tuple[str, dict]:
    v = private["items"][item_index]["verdict"]
    return (f"A reference solver reports that the correct status of the claim is: {v}. "
            "Reconsider the question and answer again in the same JSON format."), {
        "source": "reference_verdict_label", "label": v}


def sample_feedback(public: dict, item_index: int) -> tuple[str, dict]:
    """D-sample: the world's K uniformly sampled compatible mechanisms (drawn from public evidence, without
    the query, the label or any previous answer) and what each implies for this question.  A finite sample's
    agreement does NOT certify universal agreement; the text says so.  Uses PUBLIC data only."""
    from .semantics import pred_to_cubes  # noqa: F401
    n = public["n"]
    it = public["items"][item_index]
    q = _public_query(public, item_index)
    parts = [f"Here are {len(public['d_sample_mechanisms'])} systems drawn at random from those in the class that "
             "reproduce every observation (a random sample; other consistent systems may behave differently)."]
    shown = []
    for j, wj in enumerate(public["d_sample_mechanisms"]):
        w = Network.from_json(wj)
        parts.append(_mechanism_block(w, q, n, f"Sampled system {j + 1}:"))
        shown.append(int(predict(w, q)))
    text = "\n\n".join(parts) + "\n\nReconsider the question and answer again in the same JSON format."
    assert not it.get("renamed")
    return text, {"source": "uniform_compatible_sample", "k": len(shown), "shown_answers": shown}


def _public_query(public: dict, item_index: int) -> Query:
    """Reconstruct the query from PUBLIC fields only (the prompt text's structured twin)."""
    return Query.from_json(public["items"][item_index]["query"])
