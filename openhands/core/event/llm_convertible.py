from openai.types.chat import ChatCompletionToolParam
from pydantic import Field

from openhands.core.llm import ImageContent, Message, TextContent
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
    
    def __str__(self) -> str:
        """Plain text string representation for SystemPromptEvent."""
        base_str = f"{self.__class__.__name__} ({self.source})"
        prompt_preview = self.system_prompt.text[:100] + "..." if len(self.system_prompt.text) > 100 else self.system_prompt.text
        tool_count = len(self.tools)
        return f"{base_str}\n  System: {prompt_preview}\n  Tools: {tool_count} available"


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
    
    def __str__(self) -> str:
        """Plain text string representation for ActionEvent."""
        base_str = f"{self.__class__.__name__} ({self.source})"
        thought_text = " ".join([t.text for t in self.thought])
        thought_preview = thought_text[:80] + "..." if len(thought_text) > 80 else thought_text
        action_names = [action.__class__.__name__ for action in self.actions]
        return f"{base_str}\n  Thought: {thought_preview}\n  Actions: {', '.join(action_names)}"


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
    
    def __str__(self) -> str:
        """Plain text string representation for ObservationEvent."""
        base_str = f"{self.__class__.__name__} ({self.source})"
        obs_preview = self.observation.agent_observation[:100] + "..." if len(self.observation.agent_observation) > 100 else self.observation.agent_observation
        return f"{base_str}\n  Tool: {self.tool_name}\n  Result: {obs_preview}"


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
    
    def __str__(self) -> str:
        """Plain text string representation for MessageEvent."""
        base_str = f"{self.__class__.__name__} ({self.source})"
        # Extract text content from the message
        text_parts = []
        for content in self.llm_message.content:
            if isinstance(content, TextContent):
                text_parts.append(content.text)
            elif isinstance(content, ImageContent):
                text_parts.append(f"[Image: {len(content.image_urls)} URLs]")
        
        if text_parts:
            content_preview = " ".join(text_parts)
            if len(content_preview) > 100:
                content_preview = content_preview[:97] + "..."
            microagent_info = f" [Microagents: {', '.join(self.activated_microagents)}]" if self.activated_microagents else ""
            return f"{base_str}\n  {self.llm_message.role}: {content_preview}{microagent_info}"
        else:
            return f"{base_str}\n  {self.llm_message.role}: [no text content]"


class AgentErrorEvent(LLMConvertibleEvent):
    """Error triggered by the agent."""
    kind: EventType = "agent_error"
    source: SourceType = "agent"
    error: str = Field(..., description="The error message from the scaffold")

    def to_llm_message(self) -> Message:
        return Message(role="user", content=[TextContent(text=self.error)])
    
    def __str__(self) -> str:
        """Plain text string representation for AgentErrorEvent."""
        base_str = f"{self.__class__.__name__} ({self.source})"
        error_preview = self.error[:100] + "..." if len(self.error) > 100 else self.error
        return f"{base_str}\n  Error: {error_preview}"