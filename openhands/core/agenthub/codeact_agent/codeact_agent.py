import os

from openhands.core.logger import get_logger
from openhands.core.context.prompt import PromptManager
from openhands.core.context.env_context import EnvContext
from openhands.core.llm import LLM, Message, TextContent, get_llm_metadata
from openhands.core.runtime import Tool

from openhands.core.agenthub.agent import AgentBase
from openhands.core.agenthub.history import AgentHistory

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
        super().__init__(llm=llm, tools=tools, env_context=env_context)
        self.prompt_manager = PromptManager(
            prompt_dir=os.path.join(os.path.dirname(__file__), "prompts"),
            system_prompt_filename=system_prompt_filename,
        )
        self.system_message: TextContent = self.prompt_manager.get_system_message(
            cli_mode=cli_mode
        )
        self.history: AgentHistory = AgentHistory()

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

        response = self.llm.completion(
            messages=self.llm.format_messages_for_llm(self.history.messages),
            tools=[tool.to_openai_tool() for tool in self.tools],
            extra_body={
                "metadata": get_llm_metadata(
                    model_name=self.llm.config.model, agent_name=self.name
                )
            },
        )
        logger.debug(f"Response from LLM: {response}")
        import pdb

        pdb.set_trace()
