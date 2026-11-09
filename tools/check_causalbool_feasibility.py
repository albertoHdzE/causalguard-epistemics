"""Pre-sprint integration probe, not an LLM experiment or a clinical model.

Usage: python3 tools/check_causalbool_feasibility.py --causalbool-root PATH
Uses the upstream implementation without copying or modifying it.
"""
import argparse
import itertools
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--causalbool-root', type=Path, required=True)
    args = parser.parse_args()
    root = args.causalbool_root.resolve()
    sys.path.insert(0, str(root / 'index-deconvolution' / 'src'))
    from causalbool import Network, input_vector, repertoire, step
    from network_generator import random_network

    # Independent truth functions, deliberately not upstream apply_gate.
    functions = {
        'AND': lambda v: int(all(v)),
        'OR': lambda v: int(any(v)),
        'XOR': lambda v: sum(v) % 2,
        'NAND': lambda v: int(not all(v)),
        'NOR': lambda v: int(not any(v)),
        'XNOR': lambda v: 1 - sum(v) % 2,
        'NOT': lambda v: 1 - v[0],
        'IMPLIES': lambda v: int(not v[0] or v[1]),
        'NIMPLIES': lambda v: int(v[0] and not v[1]),
        'MAJORITY': lambda v: int(sum(v) > len(v) // 2),
    }
    networks = states = 0
    for n in range(3, 9):
        for seed in range(10):
            net = random_network(n, seed, max_arity=3, gate_pool='core')
            table = repertoire(net)
            for x in range(2 ** n):
                state = input_vector(x, n)
                expected = []
                for k, gate in enumerate(net.gates):
                    v = [state[i] for i in range(n) if net.C[k][i]]
                    value = (int(sum(v) >= net.params[k]['k']) if gate == 'KOFN'
                             else functions[gate](v))
                    expected.append(value)
                assert step(net, state) == table[x] == expected, (n, seed, x)
                states += 1
            networks += 1

    # Fully specified toy system A'=A, B'=B, C'=A AND B.
    net = Network(3, [[1, 0, 0], [0, 1, 0], [1, 1, 0]], ['OR', 'OR', 'AND'])
    # Claim: setting A to 1 always makes C equal 1 after one update.
    witnesses = []
    for state in itertools.product((0, 1), repeat=3):
        intervened = [1, state[1], state[2]]
        if step(net, intervened)[2] != 1:
            witnesses.append({'initial': list(state), 'after_setting_A': intervened,
                              'next': step(net, intervened)})
    assert len(witnesses) == 4

    # Partial information: AND and OR both fit observations 00->0, 11->1.
    # A=1, B=0 distinguishes them; the given observations cannot decide it.
    compatible = [g for g in ('AND', 'OR')
                  if functions[g]([0, 0]) == 0 and functions[g]([1, 1]) == 1]
    possible = sorted({functions[g]([1, 0]) for g in compatible})
    assert possible == [0, 1]
    revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    print(json.dumps({
        'status': 'pre_sprint_feasibility_only', 'upstream_revision': revision,
        'networks_checked': networks, 'states_checked': states,
        'oracle_parity': 'passed for sampled networks and every state within each',
        'false_universal_claim': {'verdict': 'refuted', 'counterexample': witnesses[0]},
        'partial_information_claim': {'verdict': 'underdetermined',
                                      'compatible_gate_models': compatible,
                                      'possible_outputs': possible},
        'limitations': ['No LLM evaluated', 'No weights edited',
                        'No clinical claim', 'Not a full upstream validation']
    }, indent=2))


if __name__ == '__main__':
    main()
