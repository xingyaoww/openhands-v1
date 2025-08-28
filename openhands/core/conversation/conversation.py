from typing import TYPE_CHECKING, Iterable


if TYPE_CHECKING:
    from openhands.core.agent import AgentBase
from threading import RLock

from openhands.core.llm import Message
from openhands.core.logger import get_logger

from .state import ConversationState
from .types import ConversationCallbackType
from .visualizer import ConversationVisualizer


logger = get_logger(__name__)


def compose_callbacks(callbacks: Iterable[ConversationCallbackType]) -> ConversationCallbackType:
    def composed(event) -> None:
        for cb in callbacks:
            if cb:
                cb(event)
    return composed

class Conversation:
    def __init__(
        self,
        agent: "AgentBase",
        callbacks: list[ConversationCallbackType] | None = None,
        max_iteration_per_run: int = 500,
    ):
        """Initialize the conversation."""
        self._visualizer = ConversationVisualizer()
        # Compose multiple callbacks if a list is provided
        self._on_event = compose_callbacks(
            [self._visualizer.on_event] + (callbacks if callbacks else [])
        )
        self.max_iteration_per_run = max_iteration_per_run

        self.agent = agent
        self._agent_initialized = False

        # Guarding the conversation state to prevent multiple
        # writers modify it at the same time
        self._lock = RLock()
        self.state = ConversationState()

    def send_message(self, message: Message) -> None:
        """Sending messages to the agent."""
        with self._lock:
            if not self._agent_initialized:
                # Prepare initial state
                self.state = self.agent.init_state(
                    self.state,
                    initial_user_message=message,
                    on_event=self._on_event,
                )
                self._agent_initialized = True
            else:
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
