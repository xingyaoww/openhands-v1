import os
import rich
import json

from openhands.core.logger import get_logger
from openhands.core.context.prompt import PromptManager
from openhands.core.context.env_context import EnvContext
from openhands.core.llm import LLM, Message, TextContent, get_llm_metadata
from openhands.core.runtime import Tool, ObservationBase, ActionBase
from openhands.core.runtime.tools import finish_tool
from openhands.core.agenthub.agent import AgentBase
from openhands.core.agenthub.history import AgentHistory
from litellm.types.utils import (
    ChatCompletionMessageToolCall,
    Message as LiteLLMMessage,
    ModelResponse,
    Choices,
)

logger = get_logger(__name__)


class CodeActAgent(AgentBase):
    def __init__(
        self,
        llm: LLM,
        tools: list[Tool],
        env_context: EnvContext | None = None,
        system_prompt_filename: str = "system_prompt.j2",
        cli_mode: bool = True,
    ) -> None:
        """Initializes a new instance of the CodeActAgent class.

        Parameters:
        - config (AgentConfig): The configuration for this agent
        """
        super().__init__(llm=llm, tools=tools + [finish_tool], env_context=env_context)
        self.prompt_manager = PromptManager(
            prompt_dir=os.path.join(os.path.dirname(__file__), "prompts"),
            system_prompt_filename=system_prompt_filename,
        )
        self.system_message: TextContent = self.prompt_manager.get_system_message(
            cli_mode=cli_mode
        )
        self.history: AgentHistory = AgentHistory()
        self.max_iterations: int = 10

    def reset(self) -> None:
        """Resets the CodeAct Agent's internal state."""
        super().reset()
        self.history.clear()

    def run(self, user_input: Message) -> None:
        """Runs the Agent with the given input and returns the output.

        The agent will stop when it reaches a terminal state, such as
        completing its task by calling "finish" or messaging the user by calling "message".
        """
        assert user_input.role == "user", "Input message must have role 'user'"

        # Initialize history with system message and initial env context if empty
        if len(self.history) == 0:
            self.history.messages.append(
                Message(role="system", content=[self.system_message])
            )
            content = user_input.content
            if self.env_context:
                initial_env_context: list[TextContent] = self.env_context.render(
                    self.prompt_manager
                )
                content += initial_env_context
            self.history.messages.append(Message(role="user", content=content))

            # Track activated microagents in the history
            if self.env_context and self.env_context.activated_microagents:
                for microagent in self.env_context.activated_microagents:
                    self.history.microagent_activations.append(
                        (microagent.name, len(self.history.messages) - 1)
                    )

        # For subsequent messages, just append the user input
        else:
            # TODO: Trigger microagents based on user input and use MessageContext
            # then track it in self.history.microagent_activations
            self.history.messages.append(user_input)

        for i in range(self.max_iterations):
            logger.info(f"Agent Iteration {i + 1}/{self.max_iterations}")
            logger.debug(f"Agent History: {self.history}")
            # Get next action from LLM
            response: ModelResponse = self.llm.completion(
                messages=self.llm.format_messages_for_llm(self.history.messages),
                tools=[tool.to_openai_tool() for tool in self.tools],
                extra_body={
                    "metadata": get_llm_metadata(
                        model_name=self.llm.config.model, agent_name=self.name
                    )
                },
            )
            assert len(response.choices) == 1 and isinstance(
                response.choices[0], Choices
            )
            llm_message: LiteLLMMessage = response.choices[0].message  # type: ignore
            message = Message.from_litellm_message(llm_message)
            self.history.messages.append(message)  # Add LLM message to history

            if message.tool_calls and len(message.tool_calls) > 0:
                # Execute tool call
                assert len(message.tool_calls) == 1, "Only one tool call is supported"
                tool_call = message.tool_calls[0]
                assert isinstance(tool_call, ChatCompletionMessageToolCall)
                rich.print(
                    f"[bold blue]LLM called tool:[/bold blue]\n{json.dumps(tool_call.model_dump(), indent=2)}"
                )
                # Handle finish tool separately
                if tool_call.function.name == finish_tool.name:
                    rich.print(
                        f"[bold magenta]Agent finished its task.[/bold magenta]\ncontent={message.content}\narguments={tool_call.function.arguments}"
                    )
                    return

                # Execute the tool and get observation and continue
                else:
                    observation_message = self._execute_tool_call(tool_call)
                    self.history.messages.append(observation_message)
            else:
                logger.info("LLM produced a message response - awaits user input")
                # logger.info(f"Response: {message.content}")
                rich.print(
                    f"[bold green]Await User Input:[/bold green]\n{message.content}"
                )
                return

    def _execute_tool_call(self, tool_call: ChatCompletionMessageToolCall) -> Message:
        tool_name = tool_call.function.name
        assert tool_name is not None, "Tool call must have a name"
        tool = self.get_tool(tool_name)
        if tool is None:
            raise ValueError(f"Tool '{tool_name}' called by LLM is not found")

        action: ActionBase = tool.action_type.model_validate(
            json.loads(tool_call.function.arguments)
        )
        if tool.executor is None:
            raise ValueError(f"Tool '{tool.name}' has no executor")
        observation: ObservationBase = tool.executor(action)
        rich.print(
            f"[bold yellow]Tool '{tool.name}' executed.[/bold yellow]\nAction: {action.model_dump()}\nObservation: {observation.model_dump()}"
        )
        return Message(
            role="tool",
            name=tool.name,
            tool_call_id=tool_call.id,
            content=[TextContent(text=observation.agent_observation)],
        )
