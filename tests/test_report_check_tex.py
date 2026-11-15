"""report/check_tex.py keeps the no-hand-typed-number guarantee on a hand-edited report.tex (iteration 13, D135)."""
import importlib.util
from pathlib import Path

import pytest

REPORT = Path(__file__).resolve().parents[1] / "report"
spec = importlib.util.spec_from_file_location("check_tex", REPORT / "check_tex.py")
check_tex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_tex)

pytestmark = pytest.mark.skipif(not (REPORT / "report.tex").exists(), reason="report.tex not built")


def _run(tmp_path, tex: str) -> int:
    p = tmp_path / "report.tex"
    p.write_text(tex)
    return check_tex.main(["--md", str(REPORT / "report.md"), "--tex", str(p)])


def test_committed_tex_matches_markdown(tmp_path):
    assert _run(tmp_path, (REPORT / "report.tex").read_text()) == 0


def test_changed_number_fails(tmp_path):
    tex = (REPORT / "report.tex").read_text()
    body = tex.index(check_tex.MARKER)
    i = body + tex[body:].index("Claude Opus 5.5 1.000")
    assert _run(tmp_path, tex[:i] + tex[i:].replace("5.5 1.000", "5.5 0.999", 1)) == 1


def test_dropped_number_fails(tmp_path):
    tex = (REPORT / "report.tex").read_text()
    assert _run(tmp_path, tex.replace("Claude Opus 5.5 1.000", "Claude Opus 5.5", 1)) == 1


def test_prose_edit_passes(tmp_path):
    tex = (REPORT / "report.tex").read_text()
    old = "Who checks the check depends on the model."
    assert old in tex
    edited = tex.replace(old, "Which model checks the check is what decides it.", 1)
    assert edited != tex
    assert _run(tmp_path, edited) == 0


def test_missing_marker_fails(tmp_path):
    tex = (REPORT / "report.tex").read_text().replace(check_tex.MARKER, "% body", 1)
    with pytest.raises(SystemExit):
        _run(tmp_path, tex)
