import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def fixtures():
    return json.loads((ROOT / "data/fixtures/semantic_fixtures.json").read_text())
