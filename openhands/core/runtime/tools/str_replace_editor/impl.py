from .editor import FileEditor
from .definition import CommandLiteral, StrReplaceEditorObservation
from .exceptions import ToolError

_GLOBAL_EDITOR = FileEditor()


def file_editor(
    command: CommandLiteral,
    path: str,
    file_text: str | None = None,
    view_range: list[int] | None = None,
    old_str: str | None = None,
    new_str: str | None = None,
    insert_line: int | None = None,
) -> StrReplaceEditorObservation:
    result: StrReplaceEditorObservation | None = None
    try:
        result = _GLOBAL_EDITOR(
            command=command,
            path=path,
            file_text=file_text,
            view_range=view_range,
            old_str=old_str,
            new_str=new_str,
            insert_line=insert_line,
        )
    except ToolError as e:
        result = StrReplaceEditorObservation(error=e.message)
    assert result is not None, "file_editor should always return a result"
    return result
