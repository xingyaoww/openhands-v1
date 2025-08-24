import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        yield Path(f.name)
        try:
            Path(f.name).unlink()
        except FileNotFoundError:
            pass


def parse_result(result: str) -> dict:
    """Parse the JSON result from file_editor."""
    return json.loads(result[result.find("{") : result.rfind("}") + 1])
