import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from openhands.core.llm import ImageContent, Message, TextContent

from .types import SourceType


class EventBase(BaseModel, ABC):
    """Base class for all events: timestamped envelope with media."""
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique event id (ULID/UUID)")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Event timestamp") # consistent with V1
    source: SourceType = Field(..., description="The source of this event")

    def __str__(self) -> str:
        """Plain text string representation for display."""
        return f"{self.__class__.__name__} ({self.source})"
    
    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"{self.__class__.__name__}(id='{self.id[:8]}...', source='{self.source}', timestamp='{self.timestamp}')"


class LLMConvertibleEvent(EventBase, ABC):
    """Base class for events that can be converted to LLM messages."""
    @abstractmethod
    def to_llm_message(self) -> Message:
        raise NotImplementedError()
    
    def __str__(self) -> str:
        """Plain text string representation showing LLM message content."""
        base_str = super().__str__()
        try:
            llm_message = self.to_llm_message()
            # Extract text content from the message
            text_parts = []
            for content in llm_message.content:
                if isinstance(content, TextContent):
                    text_parts.append(content.text)
                elif isinstance(content, ImageContent):
                    text_parts.append(f"[Image: {len(content.image_urls)} URLs]")
            
            if text_parts:
                content_preview = " ".join(text_parts)
                # Truncate long content for display
                if len(content_preview) > 100:
                    content_preview = content_preview[:97] + "..."
                return f"{base_str}\n  {llm_message.role}: {content_preview}"
            else:
                return f"{base_str}\n  {llm_message.role}: [no text content]"
        except Exception:
            # Fallback to base representation if LLM message conversion fails
            return base_str