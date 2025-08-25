from openhands.core.llm import LLM
from openhands.core.runtime import Tool
from openhands.core.context.env_context import EnvContext
from openhands.core.llm.message import Message
from openhands.core.logger import get_logger

logger = get_logger(__name__)


class AgentBase:
    def __init__(
        self,
        llm: LLM,
        tools: list[Tool],
        env_context: EnvContext | None = None,
    ) -> None:
        """Initializes a new instance of the Agent class."""
        self._llm = llm
        self._tools = tools
        self._name_to_tool: dict[str, Tool] = {}
        for tool in tools:
            if tool.name in self._name_to_tool:
                raise ValueError(f"Duplicate tool name: {tool.name}")
            logger.debug(f"Registering tool: {tool}")
            self._name_to_tool[tool.name] = tool
        self._env_context = env_context

    @property
    def name(self) -> str:
        """Returns the name of the Agent."""
        return self.__class__.__name__

    @property
    def llm(self) -> LLM:
        """Returns the LLM instance used by the Agent."""
        return self._llm

    @property
    def tools(self) -> list[Tool]:
        """Returns the list of tools available to the Agent."""
        return self._tools

    def get_tool(self, name: str) -> Tool | None:
        """Returns the tool with the given name, or None if not found."""
        return self._name_to_tool.get(name)

    @property
    def env_context(self) -> EnvContext | None:
        """Returns the environment context used by the Agent."""
        return self._env_context

    def reset(self) -> None:
        """Resets the Agent's internal state."""
        pass

    def run(self, user_input: Message) -> None:
        """Runs the Agent with the given input and returns the output.

        The agent will stop when it reaches a terminal state, such as
        completing its task by calling "finish" or messaging the user by calling "message".
        """
        raise NotImplementedError("Subclasses must implement this method.")
