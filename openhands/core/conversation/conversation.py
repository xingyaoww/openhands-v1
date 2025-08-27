from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from openhands.core.agent import AgentBase
from threading import RLock

from openhands.core.llm import Message
from openhands.core.logger import get_logger

from .state import ConversationState
from .types import ConversationCallbackType
from .visualizer import ConversationVisualizer


logger = get_logger(__name__)


class Conversation:
    def __init__(self, agent: "AgentBase", on_event: ConversationCallbackType | None = None, max_iteration_per_run: int = 500):
        self._visualizer = ConversationVisualizer()
        self._on_event: ConversationCallbackType = on_event or self._visualizer.on_event
        self.max_iteration_per_run = max_iteration_per_run

        self.agent = agent

        # Guarding the conversation state to prevent multiple
        # writers modify it at the same time
        self._lock = RLock()
        self.state = ConversationState()

        with self._lock:
            # will modify self.state in place
            self.state = self.agent.init_state(self.state, on_event=self._on_event)

    def send_message(self, message: Message) -> None:
        """Sending messages to the agent."""
        with self._lock:
            messages = self.state.history.messages
            messages.append(message)
            if self._on_event:
                self._on_event(message)

    def run(self) -> None:
        """Runs the conversation until the agent finishes."""
        iteration = 0
        while not self.state.agent_finished:
            logger.debug(f"Conversation run iteration {iteration}")
            with self._lock:
                self.state = self.agent.step(self.state, on_event=self._on_event)
            iteration += 1
            if iteration >= self.max_iteration_per_run:
                break
