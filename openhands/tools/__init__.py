"""Runtime tools package."""

from .execute_bash import (
    BashExecutor,
    ExecuteBashAction,
    ExecuteBashObservation,
    execute_bash_tool,
)
from .str_replace_editor import (
    FileEditorExecutor,
    StrReplaceEditorAction,
    StrReplaceEditorObservation,
    str_replace_editor_tool,
)


__all__ = [
    "execute_bash_tool",
    "ExecuteBashAction",
    "ExecuteBashObservation",
    "BashExecutor",
    "str_replace_editor_tool",
    "StrReplaceEditorAction",
    "StrReplaceEditorObservation",
    "FileEditorExecutor",
]

from importlib.metadata import PackageNotFoundError, version


try:
    __version__ = version("openhands-core")
except PackageNotFoundError:
    __version__ = "0.0.0"  # fallback for editable/unbuilt environments
