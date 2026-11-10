"""Read-only reproductions for CausalGuard HEAD 967fc9c.
Run with AI-x-epistemics/.venv/bin/python /tmp/causalguard_review_s2_repro.py.
"""
from dataclasses import replace
import json
import numpy as np
from causalguard.generators import make_s2_world, make_s2_instance
from causalguard.schema import Evidence, HypothesisClass, Observation, Intervention, Pred, Query, Network, Rule
from causalguard.versionspace import build_version_space, uniform_prob_true, verdict_fast, verdict

# The OR of x0=0 and x0=1 is always true, irrespective of the other literals.
ev = Evidence(3, (
    Observation(0, Intervention(), 1, ((0, 1), (1, 1), (2, 0))),
    Observation(1, Intervention(), 1, ((0, 1), (1, 0), (2, 0))),
))
vs = build_version_space(ev, HypothesisClass(3, 2))
q = Query.point(3, 3, Intervention(), 1,
                Pred.or_(Pred.lit(0, 0), Pred.lit(0, 1), Pred.lit(1, 1), Pred.lit(2, 1)))
p, method, se = uniform_prob_true(vs, q, np.random.default_rng(0))
fast, sat = verdict_fast(vs, q), verdict(vs, q).verdict
assert fast != sat, 'Original floating-point bug no longer reproduced; investigate revision.'
print(json.dumps({'check': 'exact_verdict_roundoff', 'probability': p, 'method': method,
                  'fast': fast.value, 'sat': sat.value,
                  'expected': 'entailed', 'candidate_counts': vs.counts()}, indent=2))

# Change only the hidden network, preserving the seed and all other world metadata.
w = make_s2_world('review', 0, 'parity')
zero = replace(w, net=Network(7, tuple(Rule((), 0) for _ in range(7))))
identity = replace(w, net=Network(7, tuple(Rule((j,), 2) for j in range(7))))
a, b = make_s2_instance(zero), make_s2_instance(identity)
xs_a = [o.state for o in a.evidence['uniform_states']]
xs_b = [o.state for o in b.evidence['uniform_states']]
assert zero.seed == identity.seed
assert xs_a != xs_b, 'Original model-dependent design no longer reproduced; investigate revision.'
print(json.dumps({'check': 'hidden_world_dependent_uniform_design', 'same_seed': True,
                  'zero_holdout': a.holdout_states, 'identity_holdout': b.holdout_states,
                  'zero_first_16_measurement_inputs': xs_a[:16],
                  'identity_first_16_measurement_inputs': xs_b[:16]}, indent=2))
