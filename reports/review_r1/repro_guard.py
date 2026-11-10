#!/usr/bin/env python3
"""Read-only review reproductions. All writes are in temporary fixture directories.
Usage: PROJECT/.venv/bin/python /tmp/causalguard_review_guard_repro.py PROJECT
Does not execute a scientific study, contact a model, or create a real freeze record.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

project = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(project / 'src'))
from causalguard.runner import Run, read_jsonl
spec = importlib.util.spec_from_file_location('rc', project / 'scripts/run_confirmatory.py')
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)
findings = {}
with tempfile.TemporaryDirectory(prefix='cg-review-guard-') as t:
    p = Path(t)
    (p/'configs').mkdir()
    (p/'docs').mkdir()
    cb = b'{"S1": {}, "S2": {}}'
    (p/'configs/confirmatory.json').write_bytes(cb)
    (p/'docs/FREEZE_RECORD.json').write_text(json.dumps({
        'config_sha256': hashlib.sha256(cb).hexdigest(),
        'authorization_phrase': 'test',
        'approved_studies': ['S2']}))
    (p/'RUNS.jsonl').write_text('')
    def git(*args):
        return subprocess.check_output(['git', '-C', str(p), *args], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    git('init')
    git('add', '.')
    git('-c', 'user.name=Review', '-c', 'user.email=review@example.invalid',
        'commit', '-m', 'temporary fixture')
    rc.ROOT = p
    args = SimpleNamespace(freeze_commit=git('rev-parse', 'HEAD'),
                           authorization='test', study='S1')
    findings['preflight_accepts_S1_despite_record_approving_only_S2'] = (
        rc.preflight(args)['head'] == args.freeze_commit)
    with (p/'RUNS.jsonl').open('a') as f:
        f.write('{"event":"start"}\n')
    try:
        rc.preflight(args)
    except SystemExit as e:
        findings['preflight_after_Run_execute_registry_append'] = str(e)
with tempfile.TemporaryDirectory(prefix='cg-review-jsonl-') as t:
    p = Path(t)
    r = Run('fixture', {}, runs_root=p, registry=p/'registry.jsonl')
    r.records.write_text('{"item_id":"torn')
    r.append(r.records, {'item_id':'valid-next', 'answer':1})
    findings['torn_then_appended_bytes'] = r.records.read_text()
    findings['reader_after_appended_valid_record'] = read_jsonl(r.records)
    findings['done_ids_after_appended_valid_record'] = sorted(r.done_ids())
help_text = subprocess.check_output(
    [sys.executable, str(project/'scripts/run_confirmatory.py'), '--help'], text=True)
findings['resume_option_exists'] = '--resume' in help_text
print(json.dumps(findings, indent=2))
