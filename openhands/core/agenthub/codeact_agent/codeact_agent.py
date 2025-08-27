import json
import os
from typing import Callable

from litellm.types.utils import (
    ChatCompletionMessageToolCall,
    Choices,
    Message as LiteLLMMessage,
    ModelResponse,
)
from pydantic import Field

from openhands.core.agenthub.agent import AgentBase
from openhands.core.agenthub.history import AgentHistory
from openhands.core.context.env_context import EnvContext
from openhands.core.context.prompt import PromptManager
from openhands.core.llm import LLM, Message, TextContent, get_llm_metadata
from openhands.core.logger import get_logger
from openhands.core.tool import ActionBase, ObservationBase, Tool, ToolAnnotations


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


finish_tool = Tool(
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
        super().__init__(llm=llm, tools=tools + [finish_tool], env_context=env_context)
        self.prompt_manager = PromptManager(
            prompt_dir=os.path.join(os.path.dirname(__file__), "prompts"),
            system_prompt_filename=system_prompt_filename,
        )
        self.system_message: TextContent = self.prompt_manager.get_system_message(cli_mode=cli_mode)
        self.history: AgentHistory = AgentHistory()
        self.max_iterations: int = 10

    def reset(self) -> None:
        super().reset()
        self.history.clear()

    def run(
        self,
        user_input: Message,
        on_event: Callable[[Message | ActionBase | ObservationBase], None] | None = None,
    ) -> None:
        assert user_input.role == "user", "Input message must have role 'user'"

        if len(self.history) == 0:
            sys_msg = Message(role="system", content=[self.system_message])
            self.history.messages.append(sys_msg)
            if on_event:
                on_event(sys_msg)
            content = user_input.content
            if self.env_context:
                initial_env_context: list[TextContent] = self.env_context.render(self.prompt_manager)
                content += initial_env_context
            user_msg = Message(role="user", content=content)
            self.history.messages.append(user_msg)
            if on_event:
                on_event(user_msg)

            if self.env_context and self.env_context.activated_microagents:
                for microagent in self.env_context.activated_microagents:
                    self.history.microagent_activations.append((microagent.name, len(self.history.messages) - 1))

        else:
            self.history.messages.append(user_input)
            if on_event:
                on_event(user_input)

        for i in range(self.max_iterations):
            logger.info(f"Agent Iteration {i + 1}/{self.max_iterations}")
            logger.debug(f"Agent History: {self.history}")
            response: ModelResponse = self.llm.completion(
                messages=self.llm.format_messages_for_llm(self.history.messages),
                tools=[tool.to_openai_tool() for tool in self.tools],
                extra_body={"metadata": get_llm_metadata(model_name=self.llm.config.model, agent_name=self.name)},
            )
            assert len(response.choices) == 1 and isinstance(response.choices[0], Choices)
            llm_message: LiteLLMMessage = response.choices[0].message  # type: ignore
            message = Message.from_litellm_message(llm_message)
            self.history.messages.append(message)
            if on_event:
                on_event(message)

            if message.tool_calls and len(message.tool_calls) > 0:
                assert len(message.tool_calls) == 1, "Only one tool call is supported"
                tool_call = message.tool_calls[0]
                assert isinstance(tool_call, ChatCompletionMessageToolCall)

                if tool_call.function.name == finish_tool.name:
                    try:
                        action = FinishAction.model_validate(json.loads(tool_call.function.arguments))
                        if on_event:
                            on_event(action)
                    finally:
                        return
                else:
                    observation_message = self._execute_tool_call(tool_call, on_event)
                    self.history.messages.append(observation_message)
                    if on_event:
                        on_event(observation_message)
            else:
                logger.info("LLM produced a message response - awaits user input")
                return

    def _execute_tool_call(
        self,
        tool_call: ChatCompletionMessageToolCall,
        on_event: Callable[[Message | ActionBase | ObservationBase], None] | None = None,
    ) -> Message:
        tool_name = tool_call.function.name
        assert tool_name is not None, "Tool call must have a name"
        tool = self.get_tool(tool_name)
        if tool is None:
            raise ValueError(f"Tool '{tool_name}' called by LLM is not found")

        action: ActionBase = tool.action_type.model_validate(json.loads(tool_call.function.arguments))
        if on_event:
            on_event(action)
        if tool.executor is None:
            raise ValueError(f"Tool '{tool.name}' has no executor")
        observation: ObservationBase = tool.executor(action)
        if on_event:
            on_event(observation)
        return Message(
            role="tool",
            name=tool.name,
            tool_call_id=tool_call.id,
            content=[TextContent(text=observation.agent_observation)],
        )
