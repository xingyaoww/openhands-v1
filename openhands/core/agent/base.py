from abc import ABC, abstractmethod

from openhands.core.context.env_context import EnvContext
from openhands.core.conversation import ConversationCallbackType, ConversationState
from openhands.core.llm import LLM
from openhands.core.logger import get_logger
from openhands.core.tool import Tool


logger = get_logger(__name__)


class AgentBase(ABC):
    def __init__(
        self,
        llm: LLM,
        tools: list[Tool],
        env_context: EnvContext | None = None,
    ) -> None:
        """Initializes a new instance of the Agent class.
        
        Agent should be Stateless: every step only relies on:
        1. input ConversationState
        2. LLM/tools/env_context that were given in __init__
        """
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

    @abstractmethod
    def init_state(
        self,
        state: ConversationState,
        on_event: ConversationCallbackType | None = None,
    ) -> ConversationState:
        """Initialize the empty conversation state to prepare the agent for user messages.

        Typically this involves:
        1. Adding system message
        2. Adding initial user messages with environment context
            (e.g., microagents, current working dir, etc)
        """
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def step(
        self,
        state: ConversationState,
        on_event: ConversationCallbackType | None = None,
    ) -> ConversationState:
        """Taking a step in the conversation.

        Typically this involves:
        1. Making a LLM call
        2. Executing the tool
        3. Updating the conversation state with the LLM calls and tool results
        """
        raise NotImplementedError("Subclasses must implement this method.")
