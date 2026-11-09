"""Structural guards: declared independence and one owner per concept (verified by planting)."""
import ast
import re
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "src" / "causalguard"

INDEPENDENT = {
    "reference.py": {"semantics", "index_repr", "query", "codec", "versionspace", "proofcheck", "bdd_ref"},
    "bdd_ref.py": {"semantics", "index_repr", "query", "codec", "versionspace", "proofcheck"},
    "proofcheck.py": {"semantics", "index_repr", "query", "codec", "versionspace", "bdd_ref", "reference"},
}

# (concept, regex for the DEFINING occurrence, owner path relative to src/causalguard)
OWNERS = [
    ("prime implicants", r"def prime_implicants\(", "index_repr.py"),
    ("overlap-aware union count", r"def union_count\(", "index_repr.py"),
    ("schema family membership", r"class Family\b", "index_repr.py"),
    ("archive CRC framing", r"zlib\.crc32\(", "codec.py"),
    ("Elias gamma writer", r"def gamma\(self, x", "codec.py"),
    ("version space construction", r"def build_version_space\(", "versionspace.py"),
    ("min-code selection", r"def select_min_code\(", "versionspace.py"),
    ("cluster bootstrap", r"def paired_cluster_bootstrap\(", "stats.py"),
    ("intervention semantics (production)", r"def trajectory\(", "semantics.py"),
]


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            mods.add(mod.split(".")[-1])
            for a in node.names:
                mods.add(a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                mods.add(a.name.split(".")[-1])
    return mods


def check_independence(pkg: Path) -> list[str]:
    errs = []
    for fname, banned in INDEPENDENT.items():
        p = pkg / fname
        if not p.exists():
            errs.append(f"missing {fname}")
            continue
        bad = imported_modules(p) & banned
        if bad:
            errs.append(f"{fname} imports {sorted(bad)}")
    return errs


def check_owners(pkg: Path) -> list[str]:
    errs = []
    files = sorted(pkg.rglob("*.py"))
    if not files:
        return ["no source files scanned"]
    for concept, rx, owner in OWNERS:
        hits = [f.relative_to(pkg).as_posix() for f in files if re.search(rx, f.read_text())]
        if hits != [owner]:
            errs.append(f"{concept}: defined in {hits}, owner must be exactly [{owner}]")
    return errs


def test_reference_independence():
    assert check_independence(PKG) == []


def test_single_owner_per_concept():
    n_files = len(list(PKG.rglob("*.py")))
    assert n_files > 10
    assert check_owners(PKG) == []


@pytest.mark.parametrize("plant", ["copy_owner", "import_into_reference"])
def test_guards_fire_when_defect_planted(tmp_path, plant):
    pkg = tmp_path / "causalguard"
    shutil.copytree(PKG, pkg)
    if plant == "copy_owner":
        (pkg / "planted.py").write_text("def union_count(fams, n):\n    return 0\n")
        assert any("union count" in e for e in check_owners(pkg))
    else:
        p = pkg / "reference.py"
        p.write_text("from .index_repr import from_rule\n" + p.read_text())
        assert any("reference.py imports" in e for e in check_independence(pkg))
