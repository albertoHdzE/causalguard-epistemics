"""Read-only takeover audits. Run from any directory after installing causalguard.

Example: .venv/bin/python reports/takeover_r4/audit_takeover.py \
  --analysis-dir /tmp/causalguard-successor-analysis --out /tmp/successor-audit
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from causalguard.runner import load_run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--analysis-dir', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    args.out.mkdir(parents=True, exist_ok=True)
    comparison = []
    names = ('active_summary', 'known_summary', 'map_summary', 'misspec_summary',
             'pilot_summary', 'sizing', 'stress_summary')
    for name in names:
        filename = f's4_{name}.json'
        generated = (args.analysis_dir / filename).read_bytes()
        committed = (root / 'reports/development_r4' / filename).read_bytes()
        comparison.append({'file': filename, 'byte_identical': generated == committed,
                           'sha256': hashlib.sha256(generated).hexdigest()})
    counts = {}
    for run in ('s4-pilot-qwen25_7b-v1', 's4-pilot-mistral_small_24b-v1'):
        loaded = load_run(root / 'runs' / run)
        counter = Counter()
        for record in loaded['results'].values():
            for cid, answer in record['episodes']['A']['final'].items():
                expected = record['reference'][cid]['verdict']
                asserted = answer['verdict']
                counter['total'] += 1
                if asserted != expected:
                    counter['wrong_total'] += 1
                    counter['wrong_asserted_' + asserted] += 1
                    counter[f'wrong_transition_{asserted}_to_{expected}'] += 1
        counts[run] = dict(counter)
    for filename, value in [('summary_comparison.json', comparison), ('error_type_audit.json', counts)]:
        (args.out / filename).write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({'all_seven_summaries_match': all(x['byte_identical'] for x in comparison),
                      'initial_errors': counts}, indent=2))


if __name__ == '__main__':
    main()
