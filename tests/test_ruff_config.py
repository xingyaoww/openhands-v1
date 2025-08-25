"""Test that ruff configuration is properly set up for import sorting."""

import subprocess
import tempfile
from pathlib import Path


def test_ruff_import_sorting_config():
    """Test that ruff is configured to sort imports correctly."""
    # Create a temporary Python file with unsorted imports
    test_content = """import os
from pathlib import Path
import sys

from openhands.core.logger import get_logger
from openhands.core.config import LLMConfig

import json
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_content)
        temp_file = Path(f.name)

    try:
        # Run ruff check on the file to see if it detects import sorting issues
        result = subprocess.run(
            ["uv", "run", "ruff", "check", "--select", "I", str(temp_file)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        # If imports are not sorted, ruff should return non-zero exit code
        assert result.returncode != 0, "Ruff should detect unsorted imports"
        assert "I001" in result.stdout, "Should detect unsorted imports (I001)"

        # Now fix the imports
        subprocess.run(
            ["uv", "run", "ruff", "check", "--select", "I", "--fix", str(temp_file)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        # After fixing, check should pass
        check_result = subprocess.run(
            ["uv", "run", "ruff", "check", "--select", "I", str(temp_file)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert check_result.returncode == 0, "Ruff should pass after fixing imports"

        # Verify the fixed content has proper import order
        fixed_content = temp_file.read_text()

        # Should have standard library imports first, then third-party, then first-party
        assert "import json" in fixed_content
        assert "import os" in fixed_content
        assert "import sys" in fixed_content
        assert "from pathlib import Path" in fixed_content
        assert "from openhands.core.config import LLMConfig" in fixed_content
        assert "from openhands.core.logger import get_logger" in fixed_content

    finally:
        # Clean up
        temp_file.unlink()


def test_ruff_format_config():
    """Test that ruff format configuration is working."""
    # Create a temporary Python file with formatting issues
    test_content = """import os
def test_function( ):
    x=1
    y = 2
    return x+y
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_content)
        temp_file = Path(f.name)

    try:
        # Run ruff format
        result = subprocess.run(
            ["uv", "run", "ruff", "format", str(temp_file)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0, "Ruff format should succeed"

        # Check that formatting was applied
        formatted_content = temp_file.read_text()

        # Should use double quotes (as configured)
        # Should have proper spacing
        assert "def test_function():" in formatted_content
        assert "x = 1" in formatted_content
        assert "return x + y" in formatted_content

    finally:
        # Clean up
        temp_file.unlink()
