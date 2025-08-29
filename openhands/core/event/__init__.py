from .base import EventBase, LLMConvertibleEvent
from .llm_convertible import (
    ActionEvent,
    AgentErrorEvent,
    MessageEvent,
    ObservationEvent,
    SystemPromptEvent,
)


EventType = ActionEvent | ObservationEvent | MessageEvent | SystemPromptEvent | AgentErrorEvent

__all__ = [
    "EventBase",
    "LLMConvertibleEvent",
    "SystemPromptEvent",
    "ActionEvent",
    "ObservationEvent",
    "MessageEvent",
    "AgentErrorEvent",
    "EventType"
]
