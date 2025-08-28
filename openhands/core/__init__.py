from importlib.metadata import PackageNotFoundError, version

from .agent import AgentBase, CodeActAgent
from .config import LLMConfig, MCPConfig
from .conversation import Conversation, ConversationCallbackType, ConversationEventType
from .llm import LLM, ImageContent, Message, TextContent
from .logger import get_logger
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
    "LLMConfig",
    "MCPConfig",
    "get_logger",
    "Conversation",
    "ConversationCallbackType",
    "ConversationEventType",
    "__version__",
]
