from openai.types.chat import ChatCompletionToolParam
from pydantic import Field

from openhands.core.llm import Message, TextContent
from openhands.core.tool import ActionBase, ObservationBase

from .base import LLMConvertibleEvent
from .types import EventType, SourceType


class SystemPromptEvent(LLMConvertibleEvent):
    """System prompt added by the agent."""
    kind: EventType = "system_prompt"
    source: SourceType = "agent"
    system_prompt: TextContent = Field(..., description="The system prompt text")
    tools: list[ChatCompletionToolParam] = Field(..., description="List of tools in OpenAI tool format")

    def to_llm_message(self) -> Message:
        return Message(
            role="system",
            content=[self.system_prompt]
        )


class ActionEvent(LLMConvertibleEvent):
    kind: EventType = "action"
    source: SourceType = "agent"
    thought: list[TextContent] = Field(..., description="The thought process of the agent before taking this action")
    actions: list[ActionBase] = Field(..., description="One (tool call) or a list of action (parallel tool call) returned by LLM")
    # TODO: we could also do .tool_calls, and then piece it back to llm_message, but just felt a bit risky
    # since there could be missing fields.
    llm_message: Message = Field(..., description="The exact LLM message that produced this action")
    
    def to_llm_message(self) -> Message:
        return self.llm_message

class ObservationEvent(LLMConvertibleEvent):
    kind: EventType = "observation"
    source: SourceType = "environment"
    observation: ObservationBase = Field(..., description="The observation (tool call) sent to LLM")
    
    action_id: str = Field(..., description="The action id that this observation is responding to")
    tool_name: str = Field(..., description="The tool name that this observation is responding to")
    tool_call_id: str = Field(..., description="The tool call id that this observation is responding to")
    
    def to_llm_message(self) -> Message:
        return Message(
            role="tool",
            content=[TextContent(text=self.observation.agent_observation)],
            name=self.tool_name,
            tool_call_id=self.tool_call_id
        )

class MessageEvent(LLMConvertibleEvent):
    """Message from either agent or user.

    This is originally the "MessageAction", but it suppose not to be tool call."""
    kind: EventType = "message"
    source: SourceType
    llm_message: Message = Field(..., description="The exact LLM message for this message event")

    # context extensions stuff / microagent can go here
    activated_microagents: list[str] = Field(default_factory=list, description="List of activated microagent name")

    def to_llm_message(self) -> Message:
        return self.llm_message 

class AgentErrorEvent(LLMConvertibleEvent):
    """Error triggered by the agent."""
    kind: EventType = "agent_error"
    source: SourceType = "agent"
    error: str = Field(..., description="The error message from the scaffold")

    def to_llm_message(self) -> Message:
        return Message(role="user", content=[TextContent(text=self.error)])
