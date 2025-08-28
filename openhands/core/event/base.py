import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from openhands.core.llm import Message

from .types import SourceType


class EventBase(BaseModel, ABC):
    """Base class for all events: timestamped envelope with media."""
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique event id (ULID/UUID)")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Event timestamp") # consistent with V1
    source: SourceType = Field(..., description="The source of this event")

class LLMConvertibleEvent(EventBase, ABC):
    """Base class for events that can be converted to LLM messages."""
    @abstractmethod
    def to_llm_message(self) -> Message:
        raise NotImplementedError()

