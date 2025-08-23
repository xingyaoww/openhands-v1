"""Test the StrReplaceEditorTool integration."""

import tempfile
from pathlib import Path


from openhands.runtime.tools.str_replace_editor import (
    StrReplaceEditorAction,
    _execute_str_replace_editor,
    create_str_replace_editor_tool,
)


def test_create_str_replace_editor_tool():
    """Test that the tool can be created successfully."""
    tool = create_str_replace_editor_tool()
    assert tool.name == "str_replace_editor"
    assert "Custom editing tool" in tool.description
    assert tool.input_schema is not None
    assert tool.execute_fn is not None


def test_str_replace_editor_action_schema():
    """Test that the action schema is valid."""
    action = StrReplaceEditorAction(
        command="view", path="/tmp/test.txt", security_risk="LOW"
    )
    assert action.command == "view"
    assert action.path == "/tmp/test.txt"
    assert action.security_risk == "LOW"


def test_execute_str_replace_editor_view():
    """Test viewing a file through the tool."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Hello, World!\nThis is a test file.")
        temp_path = f.name

    try:
        action = StrReplaceEditorAction(
            command="view", path=temp_path, security_risk="LOW"
        )

        result = _execute_str_replace_editor(action)

        assert "output" in result
        assert "Hello, World!" in result["output"]
        assert "This is a test file." in result["output"]

    finally:
        Path(temp_path).unlink()


def test_execute_str_replace_editor_create():
    """Test creating a file through the tool."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / "new_file.txt"

        action = StrReplaceEditorAction(
            command="create",
            path=str(temp_path),
            file_text="New file content\nSecond line",
            security_risk="LOW",
        )

        result = _execute_str_replace_editor(action)

        assert "output" in result
        assert "File created successfully" in result["output"]
        assert temp_path.exists()
        assert temp_path.read_text() == "New file content\nSecond line"


def test_execute_str_replace_editor_str_replace():
    """Test string replacement through the tool."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Hello, World!\nThis is a test file.")
        temp_path = f.name

    try:
        action = StrReplaceEditorAction(
            command="str_replace",
            path=temp_path,
            old_str="Hello, World!",
            new_str="Hello, Universe!",
            security_risk="LOW",
        )

        result = _execute_str_replace_editor(action)

        assert "output" in result
        assert "has been edited" in result["output"]

        # Verify the file was actually changed
        content = Path(temp_path).read_text()
        assert "Hello, Universe!" in content
        assert "Hello, World!" not in content

    finally:
        Path(temp_path).unlink()


def test_execute_str_replace_editor_error_handling():
    """Test error handling in the tool."""
    action = StrReplaceEditorAction(
        command="view", path="/nonexistent/file.txt", security_risk="LOW"
    )

    result = _execute_str_replace_editor(action)

    assert "output" in result
    assert "ERROR:" in result["output"]
