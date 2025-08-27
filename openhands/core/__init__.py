from importlib.metadata import PackageNotFoundError, version

from .agenthub import AgentBase, CodeActAgent
from .config import LLMConfig, MCPConfig, OpenHandsConfig
from .conversation import Conversation
from .llm import LLM, ImageContent, Message, TextContent
from .logger import ENV_LOG_DIR, get_logger
from .tool import ActionBase, ObservationBase, Tool


try:
    __version__ = version("openhands-core")
except PackageNotFoundError:
    __version__ = "0.0.0"  # fallback for editable/unbuilt environments

__all__ = [
    "LLM",
    "Message",
    "TextContent",
    "ImageContent",
    "Tool",
    "AgentBase",
    "CodeActAgent",
    "ActionBase",
    "ObservationBase",
    "OpenHandsConfig",
    "LLMConfig",
    "MCPConfig",
    "get_logger",
    "ENV_LOG_DIR",
    "Conversation",
    "__version__",
]
