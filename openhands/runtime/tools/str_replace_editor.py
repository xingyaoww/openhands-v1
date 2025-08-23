"""String replace editor tool implementation."""

import json
import uuid
from pathlib import Path
from typing import Literal

from openhands_aci.editor import OHEditor, ToolError, ToolResult

from ..schema import ActionBase, ObservationBase
from ..tool import Tool


class StrReplaceEditorAction(ActionBase):
    """Action schema for the string replace editor tool."""

    command: Literal["view", "create", "str_replace", "insert", "undo_edit"]
    path: str
    file_text: str | None = None
    old_str: str | None = None
    new_str: str | None = None
    insert_line: int | None = None
    view_range: list[int] | None = None
    security_risk: Literal["LOW", "MEDIUM", "HIGH"]


class StrReplaceEditorObservation(ObservationBase):
    """Observation schema for the string replace editor tool."""

    output: str
    error: str | None = None
    path: str | None = None
    prev_exist: bool | None = None
    old_content: str | None = None
    new_content: str | None = None


def _make_api_tool_result(tool_result: ToolResult) -> str:
    """Convert an agent ToolResult to an API ToolResultBlockParam."""
    if tool_result.error:
        return f"ERROR:\n{tool_result.error}"

    assert tool_result.output, "Expected output in file_editor."
    return tool_result.output


def _execute_str_replace_editor(
    action: StrReplaceEditorAction,
) -> StrReplaceEditorObservation:
    """Execute the string replace editor tool."""

    # Create OHEditor instance with workspace root if path is absolute
    path_obj = Path(action.path)
    if path_obj.is_absolute():
        # Use the root directory as workspace root for absolute paths
        workspace_root = str(path_obj.anchor)
    else:
        # For relative paths, use current working directory
        workspace_root = str(Path.cwd())

    editor = OHEditor(workspace_root=workspace_root)

    result: ToolResult | None = None
    try:
        result = editor(
            command=action.command,
            path=action.path,
            file_text=action.file_text,
            view_range=action.view_range,
            old_str=action.old_str,
            new_str=action.new_str,
            insert_line=action.insert_line,
            enable_linting=False,  # Disable linting for now
        )
    except ToolError as e:
        result = ToolResult(error=e.message)
    except Exception as e:
        result = ToolResult(error=str(e))

    # Format the output similar to the original file_editor function
    formatted_output_and_error = _make_api_tool_result(result)
    marker_id = uuid.uuid4().hex

    def json_generator():
        yield "{"
        first = True
        for key, value in result.to_dict().items():
            if not first:
                yield ","
            first = False
            yield f'"{key}": {json.dumps(value)}'
        yield f', "formatted_output_and_error": {json.dumps(formatted_output_and_error)}'
        yield "}"

    final_output = (
        f"<oh_aci_output_{marker_id}>\n"
        + "".join(json_generator())
        + f"\n</oh_aci_output_{marker_id}>"
    )

    # Create observation with the formatted output
    observation_data = {
        "output": final_output,
        "error": result.error,
    }

    # Add additional fields if available
    if hasattr(result, "path") and result.path:
        observation_data["path"] = result.path
    if hasattr(result, "prev_exist"):
        observation_data["prev_exist"] = result.prev_exist
    if hasattr(result, "old_content") and result.old_content:
        observation_data["old_content"] = result.old_content
    if hasattr(result, "new_content") and result.new_content:
        observation_data["new_content"] = result.new_content

    return StrReplaceEditorObservation(**observation_data)


# Tool schema based on the OpenHands str_replace_editor.py
STR_REPLACE_EDITOR_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {
            "description": "The commands to run. Allowed options are: `view`, `create`, `str_replace`, `insert`, `undo_edit`.",
            "enum": ["view", "create", "str_replace", "insert", "undo_edit"],
            "type": "string",
        },
        "path": {
            "description": "Absolute path to file or directory, e.g. `/workspace/file.py` or `/workspace`.",
            "type": "string",
        },
        "file_text": {
            "description": "Required parameter of `create` command, with the content of the file to be created.",
            "type": "string",
        },
        "old_str": {
            "description": "Required parameter of `str_replace` command containing the string in `path` to replace.",
            "type": "string",
        },
        "new_str": {
            "description": "Optional parameter of `str_replace` command containing the new string (if not given, no string will be added). Required parameter of `insert` command containing the string to insert.",
            "type": "string",
        },
        "insert_line": {
            "description": "Required parameter of `insert` command. The `new_str` will be inserted AFTER the line `insert_line` of `path`.",
            "type": "integer",
        },
        "view_range": {
            "description": "Optional parameter of `view` command when `path` points to a file. If none is given, the full file is shown. If provided, the file will be shown in the indicated line number range, e.g. [11, 12] will show lines 11 and 12. Indexing at 1 to start. Setting `[start_line, -1]` shows all lines from `start_line` to the end of the file.",
            "items": {"type": "integer"},
            "type": "array",
        },
        "security_risk": {
            "type": "string",
            "description": "The LLM's assessment of the safety risk of this action. See the SECURITY_RISK_ASSESSMENT section in the system prompt for risk level definitions.",
            "enum": ["LOW", "MEDIUM", "HIGH"],
        },
    },
    "required": ["command", "path", "security_risk"],
}

# Tool description based on the OpenHands str_replace_editor.py
STR_REPLACE_EDITOR_DESCRIPTION = """Custom editing tool for viewing, creating and editing files in plain-text format
* State is persistent across command calls and discussions with the user
* If `path` is a text file, `view` displays the result of applying `cat -n`. If `path` is a directory, `view` lists non-hidden files and directories up to 2 levels deep
* The following binary file extensions can be viewed in Markdown format: [".xlsx", ".pptx", ".wav", ".mp3", ".m4a", ".flac", ".pdf", ".docx"]. IT DOES NOT HANDLE IMAGES.
* The `create` command cannot be used if the specified `path` already exists as a file
* If a `command` generates a long output, it will be truncated and marked with `<response clipped>`
* The `undo_edit` command will revert the last edit made to the file at `path`
* This tool can be used for creating and editing files in plain-text format.


Before using this tool:
1. Use the view tool to understand the file's contents and context
2. Verify the directory path is correct (only applicable when creating new files):
   - Use the view tool to verify the parent directory exists and is the correct location

When making edits:
   - Ensure the edit results in idiomatic, correct code
   - Do not leave the code in a broken state
   - Always use absolute file paths (starting with /)

CRITICAL REQUIREMENTS FOR USING THIS TOOL:

1. EXACT MATCHING: The `old_str` parameter must match EXACTLY one or more consecutive lines from the file, including all whitespace and indentation. The tool will fail if `old_str` matches multiple locations or doesn't match exactly with the file content.

2. UNIQUENESS: The `old_str` must uniquely identify a single instance in the file:
   - Include sufficient context before and after the change point (3-5 lines recommended)
   - If not unique, the replacement will not be performed

3. REPLACEMENT: The `new_str` parameter should contain the edited lines that replace the `old_str`. Both strings must be different.

Remember: when making multiple file edits in a row to the same file, you should prefer to send all edits in a single message with multiple calls to this tool, rather than multiple messages with a single call each.
"""


def create_str_replace_editor_tool() -> Tool:
    """Create the string replace editor tool."""
    return Tool(
        name="str_replace_editor",
        description=STR_REPLACE_EDITOR_DESCRIPTION,
        input_schema=STR_REPLACE_EDITOR_SCHEMA,
        output_schema=StrReplaceEditorObservation,
        execute_fn=_execute_str_replace_editor,
    )
