"""The measured decoder bundle is complete: it decodes archives in an isolated interpreter with only the
standard library (R10: the v1 charge measured codec.py alone although it imports other local modules)."""
import shutil
import subprocess
import sys
from pathlib import Path

from causalguard.codec import ALL_NODE_CODECS, decoder_bundle, encode_network
from causalguard.generators import make_s1_world

SRC = Path(__file__).resolve().parents[1] / "src" / "causalguard"


def test_bundle_is_complete_and_runs_isolated(tmp_path):
    b = decoder_bundle()
    assert b["modules"] == ["codec.py", "index_repr.py", "schema.py"]
    pkg = tmp_path / "cgdec"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    for m in b["modules"]:
        shutil.copy(SRC / m, pkg / m)
    net = make_s1_world("bundle", 0, "modular", 8).net
    for cd in ALL_NODE_CODECS:
        data = encode_network(net, cd).data
        f = tmp_path / f"{cd}.bin"
        f.write_bytes(data)
        code = ("import sys, json; sys.path.insert(0, sys.argv[1]); from cgdec.codec import decode_network; "
                "n = decode_network(open(sys.argv[2], 'rb').read()); print(json.dumps(n.canonical().to_json(), sort_keys=True))")
        out = subprocess.run([sys.executable, "-I", "-S", "-c", code, str(tmp_path), str(f)], capture_output=True,
                             text=True, check=True).stdout.strip()
        import json
        assert out == json.dumps(net.canonical().to_json(), sort_keys=True), cd
