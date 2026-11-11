"""Read-only R2 diagnostics. Run with project .venv Python from project root."""
import json
from pathlib import Path
from collections import Counter, defaultdict
from causalguard.runner import load_run
from causalguard.schema import Query
from causalguard.s3_tasks import point_state


def semantic_key(it):
    q = Query.from_json(it['query'])
    x = point_state(q)
    for j, value in q.intervention.assign:
        x = (x & ~(1 << j)) | (value << j)
    persistent = q.intervention.assign if q.intervention.kind == 'persistent_clamp' else ()
    return (x, q.horizon, q.target.node, persistent, q.target.value)

out = {}
for rid in ('s3v2-diag-qwen25_7b-dev', 's3v2-diag-gemma3_12b-dev', 's3v2-heldout-qwen25_7b-dev'):
    records = list(load_run(Path('runs') / rid)['results'].values())
    truth_by_budget = defaultdict(Counter)
    paths = Counter()
    c_valid, c_actual, c_flagged = 0, 0, 0
    duplicates = []
    for record in records:
        private = record['task_private']
        items = private['items']
        truth_by_budget[private['budget']][items[4]['verdict']] += 1
        if semantic_key(items[0]) == semantic_key(items[4]):
            duplicates.append(record['world_index'])
        for i in range(3):
            first, second = record['arms']['D_label'][str(i)]['rounds']
            paths['|'.join((items[i]['verdict'], first['answer']['verdict'] or 'invalid', second['answer']['verdict'] or 'invalid'))] += 1
            final = record['arms']['C'][str(i)]['final']
            if final['probs_valid'] and final['verdict_valid']:
                c_valid += 1
                c_actual += final['probabilities'][final['verdict']] < max(final['probabilities'].values())
                c_flagged += 'verdict_prob_mismatch' in final['flags']
    out[rid] = {
        'n_worlds': len(records),
        'budget_target_truth': dict(truth_by_budget),
        'design_known_budget_only_target_correct': sum(record['task_private']['items'][4]['verdict'] == {3: 'entailed', 5: 'refuted', 8: 'underdetermined'}[record['task_private']['budget']] for record in records),
        'D_label_paths_truth_round1_round2': dict(paths),
        'C_balanced_aggregates': {'valid_verdict_and_vector': c_valid, 'actual_argmax_mismatch': c_actual, 'flagged_mismatch': c_flagged},
        'source_target_identical_claim_after_initial_edit_normalization': duplicates,
    }
assert out['s3v2-heldout-qwen25_7b-dev']['design_known_budget_only_target_correct'] == 80
assert out['s3v2-heldout-qwen25_7b-dev']['C_balanced_aggregates'] == {'valid_verdict_and_vector': 297, 'actual_argmax_mismatch': 134, 'flagged_mismatch': 0}
assert out['s3v2-heldout-qwen25_7b-dev']['D_label_paths_truth_round1_round2']['entailed|entailed|underdetermined'] == 98
print(json.dumps(out, indent=2, sort_keys=True))
