from enum import Enum
from typing import Any, Literal, cast

from litellm import ChatCompletionMessageToolCall
from litellm.types.utils import Message as LiteLLMMessage
from pydantic import BaseModel, Field, field_validator, model_serializer


class ContentType(Enum):
    TEXT = "text"
    IMAGE_URL = "image_url"


class Content(BaseModel):
    type: str
    cache_prompt: bool = False

    @model_serializer(mode="plain")
    def serialize_model(
        self,
    ) -> dict[str, str | dict[str, str]] | list[dict[str, str | dict[str, str]]]:
        raise NotImplementedError("Subclasses should implement this method.")


class TextContent(Content):
    type: str = ContentType.TEXT.value
    text: str

    @model_serializer(mode="plain")
    def serialize_model(self) -> dict[str, str | dict[str, str]]:
        data: dict[str, str | dict[str, str]] = {
            "type": self.type,
            "text": self.text,
        }
        if self.cache_prompt:
            data["cache_control"] = {"type": "ephemeral"}
        return data


class ImageContent(Content):
    type: str = ContentType.IMAGE_URL.value
    image_urls: list[str]

    @model_serializer(mode="plain")
    def serialize_model(self) -> list[dict[str, str | dict[str, str]]]:
        images: list[dict[str, str | dict[str, str]]] = []
        for url in self.image_urls:
            images.append({"type": self.type, "image_url": {"url": url}})
        if self.cache_prompt and images:
            images[-1]["cache_control"] = {"type": "ephemeral"}
        return images


class Message(BaseModel):
    # NOTE: this is not the same as EventSource
    # These are the roles in the LLM's APIs
    role: Literal["user", "system", "assistant", "tool"]
    content: list[TextContent | ImageContent] = Field(default_factory=list)
    cache_enabled: bool = False
    vision_enabled: bool = False
    # function calling
    function_calling_enabled: bool = False
    # - tool calls (from LLM)
    tool_calls: list[ChatCompletionMessageToolCall] | None = None
    # - tool execution result (to LLM)
    tool_call_id: str | None = None
    name: str | None = None  # name of the tool
    # force string serializer
    force_string_serializer: bool = False

    @property
    def contains_image(self) -> bool:
        return any(isinstance(content, ImageContent) for content in self.content)


    @field_validator("content", mode="before")
    @classmethod
    def _coerce_content(cls, v: Any) -> list[TextContent | ImageContent] | Any:
        # Accept None → []
        if v is None:
            return []
        # Accept a single string → [TextContent(...)]
        if isinstance(v, str):
            return [TextContent(text=v)]
        return v


    @model_serializer(mode="plain")
    def serialize_model(self) -> dict[str, Any]:
        content: list[dict[str, Any]] = []
        role_tool_with_prompt_caching = False

        for item in self.content:
            # Serialize with the subclass-specific return type
            raw = item.model_dump()
            # We have to remove cache_prompt for tool content and move it up to the message level
            # See discussion here for details: https://github.com/BerriAI/litellm/issues/6422#issuecomment-2438765472
            if isinstance(item, TextContent):
                d = cast(dict[str, Any], raw)
                if self.role == "tool" and item.cache_prompt:
                    role_tool_with_prompt_caching = True
                    d.pop("cache_control", None)
                content.append(d)

            elif isinstance(item, ImageContent) and self.vision_enabled:
                # ImageContent.model_dump() always returns a list of dicts
                d_list = cast(list[dict[str, Any]], raw)
                if self.role == "tool" and item.cache_prompt:
                    role_tool_with_prompt_caching = True
                    for elem in d_list:
                        elem.pop("cache_control", None)
                content.extend(d_list)

        message_dict: dict[str, Any] = {"content": content, "role": self.role}
        if role_tool_with_prompt_caching:
            message_dict["cache_control"] = {"type": "ephemeral"}

        return self._add_tool_call_keys(message_dict)

    def _add_tool_call_keys(self, message_dict: dict[str, Any]) -> dict[str, Any]:
        """Add tool call keys if we have a tool call or response.

        NOTE: this is necessary for both native and non-native tool calling
        """
        # an assistant message calling a tool
        if self.tool_calls is not None:
            message_dict["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in self.tool_calls
            ]

        # an observation message with tool response
        if self.tool_call_id is not None:
            assert self.name is not None, "name is required when tool_call_id is not None"
            message_dict["tool_call_id"] = self.tool_call_id
            message_dict["name"] = self.name

        return message_dict

    @classmethod
    def from_litellm_message(cls, message: LiteLLMMessage) -> "Message":
        """Convert a litellm LiteLLMMessage to our Message class."""
        assert message.role != "function", "Function role is not supported"
        return Message(
            role=message.role,
            content=[TextContent(text=message.content)] if isinstance(message.content, str) else [],
            tool_calls=message.tool_calls,
        )
