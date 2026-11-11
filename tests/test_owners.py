"""Single-owner guards (one concept, one file).  Each guard asserts the OWNER PATH, fails on zero matches and
keys on a definition plus a distinctive body fragment.  Verified by planting a copy (see test_guard_fires)."""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "causalguard"
SCAN = [SRC, SRC.parents[1] / "scripts"]

GUARDS = {
    # concept: (regex over source text, owner relative path)
    "strict jsonl reader": (r"^def read_jsonl\(", "runner.py"),
    "attempt/plan store": (r"^def read_attempts\(", "runner.py"),
    "parent-enforced deadline supervisor": (r"^def supervise\(", "runner.py"),
    "exact posterior counts": (r"^def exact_query_counts\(", "versionspace.py"),
    "integer-count tie rule": (r"2 \* num == den", "versionspace.py"),
    "exogenous S2 design": (r"^def make_s2_design\(", "generators.py"),
    "freeze record schema": (r'^RECORD_SCHEMA = "causalguard-freeze-record-v2"', "freeze.py"),
    "decoder bundle measurement": (r"^def decoder_bundle\(", "codec.py"),
    "nested per-query SIGALRM (inside items only)": (r"signal\.SIGALRM", "experiments/s1.py"),
    # iteration 3
    "verdict/vector coherence rule": (r">= max\(probs\.values\(\)\)|< max\(probs\.values\(\)\)", "llm/parse.py"),
    "no-clobber attempt publication": (r"os\.link\(", "runner.py"),
    "strict attempt validator": (r"^def validate_attempt\(", "runner.py"),
    "run phase from provenance": (r"^def run_phase\(", "runner.py"),
    "S2 endpoint reconciliation": (r"^def validate_world_v2\(", "analysis/s2_analysis.py"),
}


def find(pattern: str, roots=SCAN) -> list[str]:
    rx = re.compile(pattern, re.M)
    hits = []
    for root in roots:
        for p in sorted(root.rglob("*.py")):
            if "__pycache__" in p.parts or p.name == "testing_fixtures.py":
                continue
            if rx.search(p.read_text()):
                hits.append(str(p.relative_to(SRC)) if p.is_relative_to(SRC) else str(p))
    return hits


def test_every_concept_has_exactly_its_owner():
    files = sum(1 for r in SCAN for _ in r.rglob("*.py"))
    assert files > 30, f"scan radius too small ({files} files)"
    for concept, (pat, owner) in GUARDS.items():
        hits = find(pat)
        assert hits, f"{concept}: zero matches (guard went quiet)"
        assert hits == [owner], f"{concept}: expected only {owner}, found {hits}"


def test_guard_fires_on_a_planted_copy(tmp_path):
    (tmp_path / "planted.py").write_text("def exact_query_counts(vs, q):\n    return 2 * num == den\n")
    hits = find(GUARDS["exact posterior counts"][0], roots=[SRC, tmp_path])
    assert len(hits) == 2
