import json
import os
from typing import Callable

from litellm.types.utils import (
    ChatCompletionMessageToolCall,
    Choices,
    Message as LiteLLMMessage,
    ModelResponse,
)
from pydantic import Field, ValidationError

from openhands.core.context import EnvContext, PromptManager
from openhands.core.conversation import ConversationCallbackType, ConversationState
from openhands.core.llm import LLM, Message, TextContent, get_llm_metadata
from openhands.core.logger import get_logger
from openhands.core.tool import ActionBase, ObservationBase, Tool, ToolAnnotations

from ..base import AgentBase


logger = get_logger(__name__)

"""Finish tool implementation."""


class FinishAction(ActionBase):
    message: str = Field(description="Final message to send to the user.")


TOOL_DESCRIPTION = """Signals the completion of the current task or conversation.

Use this tool when:
- You have successfully completed the user's requested task
- You cannot proceed further due to technical limitations or missing information

The message should include:
- A clear summary of actions taken and their results
- Any next steps for the user
- Explanation if you're unable to complete the task
- Any follow-up questions if more information is needed
"""


FINISH_TOOL = Tool(
    name="finish",
    input_schema=FinishAction,
    description=TOOL_DESCRIPTION,
    annotations=ToolAnnotations(
        title="finish",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)


class CodeActAgent(AgentBase):
    def __init__(
        self,
        llm: LLM,
        tools: list[Tool],
        env_context: EnvContext | None = None,
        system_prompt_filename: str = "system_prompt.j2",
        cli_mode: bool = True,
    ) -> None:
        assert FINISH_TOOL not in tools, "Finish tool is automatically included and should not be provided."
        super().__init__(llm=llm, tools=tools + [FINISH_TOOL], env_context=env_context)
        self.prompt_manager = PromptManager(
            prompt_dir=os.path.join(os.path.dirname(__file__), "prompts"),
            system_prompt_filename=system_prompt_filename,
        )
        self.system_message: TextContent = self.prompt_manager.get_system_message(cli_mode=cli_mode)
        self.max_iterations: int = 10

    def init_state(
        self,
        state: ConversationState,
        initial_user_message: Message | None = None,
        on_event: ConversationCallbackType | None = None,
    ) -> ConversationState:
        # TODO(openhands): we should add test to test this init_state will actually modify state in-place
        messages = state.history.messages
        if len(messages) == 0:
            # Prepare system message
            sys_msg = Message(role="system", content=[self.system_message])
            messages.append(sys_msg)
            if on_event:
                on_event(sys_msg)
            if initial_user_message is None:
                raise ValueError("initial_user_message must be provided in init_state for CodeActAgent")
            
            # Prepare user message
            content = initial_user_message.content
            # TODO: think about this - we might want to handle this outside Agent but inside Conversation (e.g., in send_messages)
            # downside of handling them inside Conversation would be: conversation don't have access
            # to *any* action execution runtime information
            if self.env_context:
                initial_env_context: list[TextContent] = self.env_context.render(self.prompt_manager)
                content += initial_env_context
            user_msg = Message(role="user", content=content)
            messages.append(user_msg)
            if on_event:
                on_event(user_msg)
            if self.env_context and self.env_context.activated_microagents:
                for microagent in self.env_context.activated_microagents:
                    state.history.microagent_activations.append((microagent.name, len(messages) - 1))
        return state

    def step(
        self,
        state: ConversationState,
        on_event: ConversationCallbackType | None = None,
    ) -> ConversationState:
        # Get LLM Response (Action)
        _messages = self.llm.format_messages_for_llm(state.history.messages)
        logger.debug(f"Sending messages to LLM: {json.dumps(_messages, indent=2)}")
        response: ModelResponse = self.llm.completion(
            messages=_messages,
            tools=[tool.to_openai_tool() for tool in self.tools.values()],
            extra_body={"metadata": get_llm_metadata(model_name=self.llm.config.model, agent_name=self.name)},
        )
        assert len(response.choices) == 1 and isinstance(response.choices[0], Choices)
        llm_message: LiteLLMMessage = response.choices[0].message  # type: ignore

        message = Message.from_litellm_message(llm_message)
        state.history.messages.append(message)
        if on_event:
            on_event(message)

        if message.tool_calls and len(message.tool_calls) > 0:
            tool_call: ChatCompletionMessageToolCall
            tool_calls = [tool_call for tool_call in message.tool_calls if tool_call.type == "function"]
            assert len(tool_calls) > 0, "LLM returned tool calls but none are of type 'function'"
            for tool_call in tool_calls:
                state = self._handle_tool_call(tool_call, state, on_event)
        else:
            logger.info("LLM produced a message response - awaits user input")
            state.agent_finished = True
        return state

    def _handle_tool_call(
        self,
        tool_call: ChatCompletionMessageToolCall,
        state: ConversationState,
        on_event: Callable[[Message | ActionBase | ObservationBase], None] | None = None,
    ) -> ConversationState:
        assert tool_call.type == "function"
        tool_name = tool_call.function.name
        assert tool_name is not None, "Tool call must have a name"
        tool = self.tools.get(tool_name, None)
        # Handle non-existing tools
        if tool is None:
            err = f"Tool '{tool_name}' not found. Available: {list(self.tools.keys())}"
            logger.error(err)
            state.history.messages.append(Message(role="user", content=[TextContent(text=err)]))
            state.agent_finished = True
            return state

        # Validate arguments
        try:
            action: ActionBase = tool.action_type.model_validate(json.loads(tool_call.function.arguments))
            if on_event:
                on_event(action)
        except (json.JSONDecodeError, ValidationError) as e:
            err = f"Error validating args {tool_call.function.arguments} for tool '{tool.name}': {e}"
            logger.error(err)
            state.history.messages.append(Message(role="tool", name=tool.name, tool_call_id=tool_call.id, content=[TextContent(text=err)]))
            return state

        # Early return for finish action (no need for tool execution)
        if isinstance(action, FinishAction):
            assert tool.name == FINISH_TOOL.name, "FinishAction must be used with the finish tool"
            state.agent_finished = True
            return state

        # Execute actions!
        if tool.executor is None:
            raise RuntimeError(f"Tool '{tool.name}' has no executor")
        observation: ObservationBase = tool.executor(action)
        tool_msg = Message(
            role="tool",
            name=tool.name,
            tool_call_id=tool_call.id,
            content=[TextContent(text=observation.agent_observation)],
        )
        state.history.messages.append(tool_msg)
        if on_event:
            on_event(observation)
        return state
