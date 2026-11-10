"""Diagnostic of reviewed-code nested timer cancellation; no scientific runs.
Run from the project root: .venv/bin/python reports/review_r1/repro_timeout.py
This deliberately describes old behavior; after repair cap_enforced should be true.
"""
import json
import time
from causalguard.runner import _call
from causalguard.experiments.s1 import _with_timeout

def inner(_):
    _with_timeout(lambda: None, 0.01)
    time.sleep(0.12)
    return {"inner": "completed"}

status, result, elapsed = _call(inner, {}, 0.03)
print(json.dumps({"outer_cap_s": 0.03, "status": status,
                  "elapsed_s": elapsed, "cap_enforced": status == "timeout"}, indent=2))
