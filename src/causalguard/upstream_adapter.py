"""Pinned, read-only adapter to the upstream CausalBool implementation (parity checks only).

The upstream monorepo (https://github.com/albertoHdzE/CausalBool) has no top-level
license, so no upstream code is vendored or redistributed here.  This adapter
imports the upstream modules from a user-supplied checkout at the pinned revision,
verifies the revision and file hashes, and exposes the owners we compare against:

  index-deconvolution/src/causalbool.py    forward method (repertoire, step)
  index-deconvolution/src/deconvolution.py minimal_dnf (Quine-McCluskey + greedy cover)

Obtain a checkout with ``scripts/fetch_upstream.sh <dir>`` and set CAUSALBOOL_ROOT.
The core package never requires it; tests marked ``upstream`` are skipped without it.

Convention note (checked by tests): upstream ``evolve_network(net, x, steps)`` returns
``steps`` ROWS, i.e. ``steps - 1`` updates; CausalGuard horizons count UPDATES.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

PINNED_REVISION = "376a11ddf25063d49dc8f6cd98bbb3baf2e1cc43"
PINNED_REMOTE = "https://github.com/albertoHdzE/CausalBool"
PINNED_FILES = {
    "index-deconvolution/src/causalbool.py": "856cd0f29549f49685de43cc8bfe0796f96ca91457d649d97275b74fdafb1100",
    "index-deconvolution/src/deconvolution.py": "4e49c064fe60396a883e8ca42c676f890fa2c9ef3ec5aa3b42720d9bebd05fbb",
    "src/description_lengths.py": "9edabfa43576b7a1b9ededfdb850e2fa327917c9faf6fa296f3efc4d9020da4e",
    "GOVERNANCE/GLOSSARY.md": "c3d0402150fefcb1e72339ef986e9f124754c2370c0c55f3c741b311795b2b3e",
    "GOVERNANCE/ORDERING.md": "808c2810aabe064746bcaddd1a896aed3eca60688d037f5038cc0b4bf414bf07",
    "GOVERNANCE/DESCRIPTION_LENGTHS.md": "d8619dd1d6e032c33f6735cc939d7db46f9af57ab8d32a6f16473c30e40597e7",
    "papers/method/manuscript_formal/method_paper.tex": "04ea352c0aff664180d68a395b09bd7311e634d1e975ab7edf3531b08b029366",
}


class UpstreamUnavailable(RuntimeError):
    pass


def locate(root: str | os.PathLike | None = None) -> Path:
    root = root or os.environ.get("CAUSALBOOL_ROOT")
    if not root:
        raise UpstreamUnavailable("set CAUSALBOOL_ROOT to a checkout at " + PINNED_REVISION)
    p = Path(root)
    if not p.exists():
        raise UpstreamUnavailable(f"{p} does not exist")
    return p


def verify(root: Path) -> dict:
    """Check revision and pinned file hashes; returns a provenance record."""
    try:
        rev = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        rev = None
    files = {}
    for rel, want in PINNED_FILES.items():
        f = root / rel
        got = hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None
        files[rel] = {"expected": want, "actual": got, "ok": got == want}
    ok = rev == PINNED_REVISION and all(v["ok"] for v in files.values())
    return {"root_is_user_supplied": True, "revision": rev, "revision_ok": rev == PINNED_REVISION,
            "files": files, "ok": ok}


def _load(root: Path, name: str):
    src = root / "index-deconvolution" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))  # upstream modules import each other by bare name
    spec = importlib.util.spec_from_file_location(f"_upstream_{name}", src / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses need the module registered
    spec.loader.exec_module(mod)
    return mod


class Upstream:
    def __init__(self, root: str | os.PathLike | None = None, require_pinned: bool = True):
        self.root = locate(root)
        self.provenance = verify(self.root)
        if require_pinned and not self.provenance["ok"]:
            raise UpstreamUnavailable(f"upstream checkout is not the pinned revision/files: {self.provenance}")
        self.cb = _load(self.root, "causalbool")
        self.dec = _load(self.root, "deconvolution")

    def minimal_dnf(self, local_table: list[int]) -> list[dict]:
        return self.dec.minimal_dnf(list(local_table))

    def to_upstream_network(self, net):
        """CausalGuard Network -> upstream Network using the upstream LUT extension gate
        (LSB-first local tables, identical convention)."""
        n = net.n
        C = [[0] * n for _ in range(n)]
        gates, params = [], []
        for k, r in enumerate(net.rules):
            for i in r.inputs:
                C[k][i] = 1
            if not r.inputs:
                gates.append("TRUE" if r.table & 1 else "FALSE")
                params.append({})
            else:
                gates.append("LUT")
                params.append({"table": [(r.table >> y) & 1 for y in range(1 << r.arity)]})
        return self.cb.Network(n, C, gates, params)

    def repertoire(self, net) -> list[list[int]]:
        return self.cb.repertoire(self.to_upstream_network(net))

    def evolve_rows(self, net, initial_bits: list[int], rows: int) -> list[list[int]]:
        return self.cb.evolve_network(self.to_upstream_network(net), list(initial_bits), rows)
