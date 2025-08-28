from typing import TYPE_CHECKING, Iterable


if TYPE_CHECKING:
    from openhands.core.agent import AgentBase

from openhands.core.llm import Message
from openhands.core.logger import get_logger

from .state import ConversationState
from .types import ConversationCallbackReturnType, ConversationCallbackType
from .visualizer import ConversationVisualizer


logger = get_logger(__name__)


def compose_callbacks(callbacks: Iterable[ConversationCallbackType]) -> ConversationCallbackType:
    def composed(event) -> ConversationCallbackReturnType:
        ret: bool = False
        for cb in callbacks:
            if cb:
                # If any of the callbacks return True, the composed callback should return True
                # but we should still finish running the remaining callbacks
                ret |= bool(cb(event))
        return ret
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

        self.state = ConversationState()

    def send_message(self, message: Message) -> None:
        """Sending messages to the agent."""
        with self.state:
            if not self.state.agent_initialized:
                # mutate in place; agent must follow this contract
                self.agent.init_state(
                    self.state,
                    initial_user_message=message,
                    on_event=self._on_event,
                )
                self.state.agent_initialized = True
            else:
                self.state.history.messages.append(message)
                if self._on_event:
                    self._on_event(message)

    def run(self) -> None:
        """Runs the conversation until the agent finishes."""
        iteration = 0
        while not self.state.agent_finished:
            logger.debug(f"Conversation run iteration {iteration}")
            # TODO(openhands): we should add a testcase that test IF:
            # 1. a loop is running
            # 2. in a separate thread .send_message is called
            # and check will we be able to execute .send_message
            # BEFORE the .run loop finishes?
            with self.state:
                # step must mutate the SAME state object
                self.agent.step(self.state, on_event=self._on_event)
            iteration += 1
            if iteration >= self.max_iteration_per_run:
                break
